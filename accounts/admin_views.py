"""
Admin Views
APIs for admin dashboard
"""
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.mail import send_mail
from django.conf import settings
from compliance.models import KYC
from properties.models import Property
from investments.models import Investment
from .permissions import IsAdmin
from .admin_serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserActionSerializer,
    AdminDashboardStatsSerializer,
    UserCreateSerializer,
)
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


# ========================================
# ADMIN DASHBOARD STATS
# ========================================

class AdminDashboardStatsView(APIView):
    """
    GET /api/admin/dashboard/stats/
    
    Get dashboard statistics
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        try:
            # Calculate stats
            stats = {
                'total_users': User.objects.count(),
                'verified_users': User.objects.filter(is_verified=True).count(),
                'suspended_users': User.objects.filter(is_suspended=True).count(),
                'pending_kyc': KYC.objects.filter(status__in=['pending', 'under_review']).count(),
                'approved_kyc': KYC.objects.filter(status='verified').count(),
                'rejected_kyc': KYC.objects.filter(status='rejected').count(),
                'total_properties': Property.objects.count(),
                'published_properties': Property.objects.filter(status='published').count(),
                'total_investments': Investment.objects.count(),
                'total_investment_amount': Investment.objects.filter(
                    status='approved'  # 👈 Changed to match your Investment model status
                ).aggregate(total=Sum('amount'))['total'] or 0,
            }
            
            serializer = AdminDashboardStatsSerializer(stats)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error fetching admin stats: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to fetch statistics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# USER MANAGEMENT
# ========================================

class AdminUserListView(generics.ListAPIView):
    """
    GET /api/admin/users/
    
    List all users with filters
    Query params:
    - search: Search by name, email, phone
    - is_verified: Filter by verification status
    - is_suspended: Filter by suspension status
    - role: Filter by role slug
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = AdminUserListSerializer
    
    def get_queryset(self):
        queryset = User.objects.all().select_related('role').order_by('-date_joined')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Filter by verification
        is_verified = self.request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        # Filter by suspension
        is_suspended = self.request.query_params.get('is_suspended')
        if is_suspended is not None:
            queryset = queryset.filter(is_suspended=is_suspended.lower() == 'true')
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role__slug=role)
        
        return queryset


class AdminUserDetailView(APIView):
    """
    GET /api/admin/users/{user_id}/
    
    Get detailed user information
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, user_id):
        try:
            user = User.objects.select_related('role').get(id=user_id)
            serializer = AdminUserDetailSerializer(user)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminUserActionView(APIView):
    """
    POST /api/admin/users/{user_id}/action/
    
    Perform actions on user (verify, suspend, unsuspend, block, unblock)
    
    Body:
    {
        "action": "suspend",
        "reason": "Suspicious activity"
    }
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Prevent admin from acting on themselves
        if user.id == request.user.id:
            return Response({
                'success': False,
                'message': 'You cannot perform actions on your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AdminUserActionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        
        # Perform action
        if action == 'verify':
            user.is_verified = True
            user.save()
            message = f'User {user.username} verified successfully'
            
        elif action == 'suspend':
            user.is_suspended = True
            user.suspended_reason = reason
            user.suspended_at = timezone.now()
            user.save()
            message = f'User {user.username} suspended'
            
        elif action == 'unsuspend':
            user.is_suspended = False
            user.suspended_reason = None
            user.suspended_at = None
            user.save()
            message = f'User {user.username} unsuspended'
            
        elif action == 'block':
            user.is_blocked = True
            user.blocked_reason = reason
            user.blocked_at = timezone.now()
            user.blocked_by = request.user
            user.save()
            message = f'User {user.username} blocked'
            
        elif action == 'unblock':
            user.is_blocked = False
            user.blocked_reason = ''
            user.blocked_at = None
            user.blocked_by = None
            user.save()
            message = f'User {user.username} unblocked'
        
        logger.info(f"✅ Admin {request.user.username} performed '{action}' on user {user.username}")
        
        return Response({
            'success': True,
            'message': message,
            'data': AdminUserDetailSerializer(user).data
        }, status=status.HTTP_200_OK)
    
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from accounts.models import User
from accounts.admin_serializers import UserUpdateSerializer

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])  # Can restrict to admin if needed
def update_user(request, user_id):
    """
    Update user details.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"success": False, "error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UserUpdateSerializer(user, data=request.data, partial=True)  # partial=True allows PATCH
    if serializer.is_valid():
        serializer.save()
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)
    else:
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
   
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from accounts.models import User
from accounts.admin_serializers import UserUpdateSerializer

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])  # Can restrict to admin if needed
def update_user(request, user_id):
    """
    Update user details.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"success": False, "error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UserUpdateSerializer(user, data=request.data, partial=True)  # partial=True allows PATCH
    if serializer.is_valid():
        serializer.save()
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)
    else:
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



from rest_framework import status, permissions
from accounts.models import Role
from django.shortcuts import get_object_or_404

class AdminUserCreateAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = get_object_or_404(Role, id=4)
        user = serializer.save(role=role)

        # Send welcome email if email provided
        if user.email:
            try:
                name = user.first_name or user.username
                phone = user.phone or ''
                subject = "Your AssetKart account is ready"
                body = (
                    f"Hi {name},\n\n"
                    "We've created your AssetKart account.\n\n"
                    "Login steps:\n"
                    "1) Go to https://app.assetkart.com (or the mobile app)\n"
                    f"2) Enter your phone number {phone}\n"
                    "3) Use the OTP you receive to sign in\n\n"
                    "Once inside, you can complete your profile and start exploring opportunities.\n\n"
                    "If you need help, email us at invest@assetkart.com.\n\n"
                    "Best regards,\n"
                    "AssetKart Team"
                )
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                logger.info("Welcome email sent to %s for API-created user %s", user.email, user.pk)
            except Exception as exc:
                logger.error("Failed to send API-created user email for user %s: %s", user.pk, exc, exc_info=True)
        else:
            logger.warning("Welcome email skipped (no email) for API-created user %s", user.pk)

        return Response(
            {
                "success": True,
                "message": "User created successfully",
                "data": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role.name,
                }
            },
            status=status.HTTP_201_CREATED
        )
