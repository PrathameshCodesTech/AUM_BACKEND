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
from compliance.models import KYC
from properties.models import Property
from investments.models import Investment
from .permissions import IsAdmin
from .admin_serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserActionSerializer,
    AdminDashboardStatsSerializer,
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