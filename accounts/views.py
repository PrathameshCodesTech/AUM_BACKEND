# accounts/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView  # 
from investments.serializers import InvestmentSerializer
from accounts.serializers import (
    SendOTPSerializer,
    VerifyOTPSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    CompleteProfileSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """Send OTP to phone number"""
    serializer = SendOTPSerializer(data=request.data)

    if serializer.is_valid():
        # 👇 PASS REQUEST OBJECT FOR IP TRACKING
        result = serializer.send_otp(request=request)
        return Response(result, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """Verify OTP and login/register user"""
    # Extract referral parameters from request
    invite_code = request.data.get('invite_code') or request.query_params.get('invite')
    referral_code = request.data.get('referral_code') or request.query_params.get('ref')
    
    # Pass referral info to serializer context
    serializer = VerifyOTPSerializer(
        data=request.data,
        context={
            'invite_code': invite_code,
            'referral_code': referral_code,
        }
    )

    if serializer.is_valid():
        user, is_new = serializer.get_or_create_user()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Serialize user data
        user_serializer = UserSerializer(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user_serializer.data,
            'is_new_user': is_new,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_registration(request):
    """Complete user registration"""
    serializer = UserRegistrationSerializer(
        data=request.data,
        context={'user': request.user}
    )

    if serializer.is_valid():
        user = serializer.update_user(request.user)
        user_serializer = UserSerializer(user)

        return Response({
            'user': user_serializer.data,
            'message': 'Registration completed successfully'
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current logged-in user details"""
    # 👇 ADD THIS: Force fresh fetch from database
    from accounts.models import User
    user = User.objects.get(id=request.user.id)
    
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout user (blacklist refresh token)"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


class CompleteProfileView(APIView):
    """
    POST /api/auth/complete-profile/
    Complete user profile (Step 2 of onboarding)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CompleteProfileSerializer(
            data=request.data,
            context={'user': request.user}
        )
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.update(request.user, serializer.validated_data)
        
        # 👇 ADD THIS: Refresh from database
        user.refresh_from_db()
        
        # 👇 ADD THIS: Use UserSerializer to return complete user data
        user_serializer = UserSerializer(user)
        
        return Response({
            'success': True,
            'message': 'Profile completed successfully',
            'user': user_serializer.data,  # 👈 Changed from manual dict to full serializer
            'data': {  # Keep this for backward compatibility
                'username': user.username,
                'email': user.email,
                'date_of_birth': user.date_of_birth,
                'is_indian': user.is_indian,
                'profile_completed': user.profile_completed
            }
        }, status=status.HTTP_200_OK)
    
        

from .services.dashboard_service import DashboardService

class DashboardStatsView(APIView):
    """
    GET /api/dashboard/stats/
    Get dashboard statistics
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            stats = DashboardService.get_customer_stats(request.user)
            
            return Response({
                'success': True,
                'data': stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PortfolioView(APIView):
    """
    GET /api/portfolio/booked/
    GET /api/portfolio/available/
    Get portfolio properties
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, portfolio_type):
        status_map = {
            'booked': 'pending',
            'active': 'active',
            'completed': 'completed'
        }
        
        status_filter = status_map.get(portfolio_type)
        
        investments = DashboardService.get_portfolio(request.user, status_filter)
        serializer = InvestmentSerializer(investments, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    


@api_view(['GET'])
@permission_classes([AllowAny])  # For testing, change to IsAuthenticated later
def list_all_users(request):
    """
    GET /api/auth/users/
    List all users (for testing/admin)
    """
    from accounts.models import User
    from accounts.serializers import UserListSerializer
    
    users = User.objects.all().select_related('role').order_by('-date_joined')
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'username': user.username,
            'phone': user.phone,
            'email': user.email,
            'phone_verified': user.phone_verified,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role.display_name if user.role else 'No Role',
            'is_active': user.is_active,
            'kyc_status': user.kyc_status,
            'profile_completed': user.profile_completed,
            'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    return Response({
        'success': True,
        'count': len(users_data),
        'users': users_data
    }, status=status.HTTP_200_OK)