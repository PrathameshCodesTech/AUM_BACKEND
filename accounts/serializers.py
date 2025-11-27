# accounts/serializers.py
from rest_framework import serializers
from accounts.models import User, Organization, OrganizationMember, Role
from django.core.cache import cache
import random
# Add this import at top of serializers.py
from accounts.services import RouteMobileSMS  # ← ADD THIS LINE
import logging

logger = logging.getLogger(__name__)


class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15, required=True)

    def validate_phone(self, value):
        # Remove any spaces or special characters
        phone = value.strip().replace(' ', '').replace('-', '')

        # Basic validation - adjust according to your needs
        if not phone.startswith('+91'):
            phone = '+91' + phone.lstrip('0')

        if len(phone) < 13:  # +91 (3) + 10 digits
            raise serializers.ValidationError("Invalid phone number")

        return phone

    def send_otp(self):
        phone = self.validated_data['phone']

        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Store OTP in cache (expires in 5 minutes)
        cache_key = f"otp_{phone}"
        cache.set(cache_key, otp, timeout=300)

        logger.info(f"Generated OTP for {phone}: {otp}")

        # Send OTP via Route Mobile ✅ NEW
        sms_service = RouteMobileSMS()
        result = sms_service.send_otp(phone, otp)

        if result['success']:
            # Store message_id for tracking (optional)
            if result.get('message_id'):
                cache.set(f"otp_msg_{phone}",
                          result['message_id'], timeout=300)

            return {
                'success': True,
                'phone': phone,
                'message': 'OTP sent successfully',
                'message_id': result.get('message_id'),
                # Include OTP in test mode only
                'otp': otp if result.get('status') == 'TEST_MODE' else None
            }
        else:
            # SMS failed, but OTP is still valid (user can retry)
            raise serializers.ValidationError(
                result.get('error', 'Failed to send OTP. Please try again.')
            )


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15, required=True)
    otp = serializers.CharField(max_length=6, required=True)

    def validate(self, data):
        phone = data.get('phone')
        otp = data.get('otp')

        # Get OTP from cache
        cache_key = f"otp_{phone}"
        stored_otp = cache.get(cache_key)

        if not stored_otp:
            raise serializers.ValidationError("OTP expired or invalid")

        if stored_otp != otp:
            raise serializers.ValidationError("Invalid OTP")

        # OTP is valid, delete it from cache
        cache.delete(cache_key)

        return data

    def get_or_create_user(self):
        phone = self.validated_data['phone']

        # Check if user exists
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'username': phone,  # Use phone as username initially
                'phone_verified': True,
            }
        )

        if not created:
            # Update phone_verified if user exists
            user.phone_verified = True
            user.save()

        return user, created


class UserRegistrationSerializer(serializers.Serializer):
    """Complete user profile - connects to Image 3"""
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    date_of_birth = serializers.DateField(required=True)
    is_indian = serializers.BooleanField(required=True)

    def validate_username(self, value):
        # Check if username already exists (excluding current user)
        user = self.context.get('user')
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("Username already taken")
        return value

    def validate_email(self, value):
        # Check if email already exists (excluding current user)
        user = self.context.get('user')
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def update_user(self, user):
        user.username = self.validated_data['username']
        user.email = self.validated_data['email']
        user.date_of_birth = self.validated_data['date_of_birth']

        # Store is_indian in user or create profile if needed
        # For now, we can store in a JSON field or extend model later

        user.save()

        # Auto-assign user to AssetKart organization as Customer
        self.assign_to_organization(user)

        return user

    def assign_to_organization(self, user):
        """Automatically assign user to AssetKart as Customer"""
        try:
            # Get AssetKart organization
            org = Organization.objects.get(slug='assetkart')

            # Get customer role
            customer_role = Role.objects.get(
                name='customer',
                organization=org
            )

            # Create membership if doesn't exist
            OrganizationMember.objects.get_or_create(
                user=user,
                organization=org,
                defaults={
                    'role': customer_role,
                    'is_active': True,
                    'is_primary': True,
                }
            )
        except (Organization.DoesNotExist, Role.DoesNotExist):
            # Log error but don't fail registration
            print("⚠️ Warning: Could not assign user to organization")


class UserSerializer(serializers.ModelSerializer):
    """User details serializer"""
    organization = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'phone_verified',
            'first_name', 'last_name', 'date_of_birth', 'avatar',
            'kyc_status', 'organization', 'role', 'permissions'
        ]
        read_only_fields = ['phone', 'phone_verified', 'kyc_status']

    def get_organization(self, obj):
        """Get user's primary organization"""
        membership = obj.memberships.filter(is_primary=True).first()
        if membership:
            return {
                'id': membership.organization.id,
                'name': membership.organization.name,
                'slug': membership.organization.slug,
            }
        return None

    def get_role(self, obj):
        """Get user's role in primary organization"""
        membership = obj.memberships.filter(is_primary=True).first()
        if membership:
            return {
                'name': membership.role.name,
                'display_name': membership.role.display_name,
                'level': membership.role.level,
            }
        return None

    def get_permissions(self, obj):
        """Get user's permissions"""
        membership = obj.memberships.filter(is_primary=True).first()
        if membership:
            permissions = membership.role.role_permissions.values_list(
                'permission__code_name',
                flat=True
            )
            return list(permissions)
        return []
