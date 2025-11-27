# accounts/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.serializers import (
    SendOTPSerializer,
    VerifyOTPSerializer,
    UserRegistrationSerializer,
    UserSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """
    Send OTP to phone number

    POST /api/auth/send-otp/
    Body: {
        "phone": "+919876543210"
    }
    """
    serializer = SendOTPSerializer(data=request.data)

    if serializer.is_valid():
        result = serializer.send_otp()
        return Response(result, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    Verify OTP and login/register user

    POST /api/auth/verify-otp/
    Body: {
        "phone": "+919876543210",
        "otp": "123456"
    }

    Returns: JWT tokens + user info + is_new_user flag
    """
    serializer = VerifyOTPSerializer(data=request.data)

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
    """
    Complete user registration - Step 2 in Image 3

    POST /api/auth/register/
    Headers: Authorization: Bearer <token>
    Body: {
        "username": "john_doe",
        "email": "john@example.com",
        "date_of_birth": "1990-01-15",
        "is_indian": true
    }
    """
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
    """
    Get current logged-in user details

    GET /api/auth/me/
    Headers: Authorization: Bearer <token>
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user (blacklist refresh token)

    POST /api/auth/logout/
    Headers: Authorization: Bearer <token>
    Body: {
        "refresh": "<refresh_token>"
    }
    """
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
