# accounts/serializers.py
from rest_framework import serializers
from accounts.models import User, Role
from accounts.services import RouteMobileSMS
from django.core.cache import cache
import random
import logging

logger = logging.getLogger(__name__)


class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15, required=True)
    is_signup = serializers.BooleanField(required=False, default=False)
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_phone(self, value):
        """Validate and normalize phone number"""
        import re
        
        # Remove any spaces, dashes, or other non-digit characters except +
        phone = re.sub(r'[^\d+]', '', value.strip())
        
        # Remove + temporarily for digit counting
        digits_only = phone.replace('+', '')
        
        # Handle different formats
        if len(digits_only) == 10:
            # 10 digits = Indian mobile (7726255555)
            phone = f'+91{digits_only}'
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            # 12 digits starting with 91 (917726255555)
            phone = f'+{digits_only}'
        elif len(digits_only) == 11 and digits_only.startswith('0'):
            # 11 digits starting with 0 (07726255555)
            phone = f'+91{digits_only[1:]}'
        elif phone.startswith('+91') and len(digits_only) == 12:
            # Already formatted correctly (+917726255555)
            pass
        else:
            raise serializers.ValidationError(
                f"Invalid phone number format. Expected 10-digit Indian mobile number. Got: {value}"
            )
        
        # Final validation: Must be +91 followed by exactly 10 digits
        if not re.match(r'^\+91\d{10}$', phone):
            raise serializers.ValidationError(
                f"Phone must be in format +91XXXXXXXXXX (10 digits). Got: {phone}"
            )
        
        return phone

    def validate(self, data):
        phone = data.get('phone')
        is_signup = data.get('is_signup', False)
        name = data.get('name', '')
        email = data.get('email', '')

        # Check if user exists
        user_exists = User.objects.filter(phone=phone).exists()

        # SIGNUP VALIDATION
        if is_signup:
            if user_exists:
                raise serializers.ValidationError({
                    'error': 'phone_exists',
                    'message': 'This phone number is already registered. Please login instead.'
                })
            
            # For signup, name and email are required
            if not name or not name.strip():
                raise serializers.ValidationError({
                    'error': 'name_required',
                    'message': 'Name is required for signup.'
                })
            
            if not email or not email.strip():
                raise serializers.ValidationError({
                    'error': 'email_required',
                    'message': 'Email is required for signup.'
                })

        # LOGIN VALIDATION
        else:
            if not user_exists:
                raise serializers.ValidationError({
                    'error': 'phone_not_found',
                    'message': 'This phone number is not registered. Please signup first.'
                })

        return data

    def send_otp(self):
        phone = self.validated_data['phone']
        is_signup = self.validated_data.get('is_signup', False)
        name = self.validated_data.get('name', '')
        email = self.validated_data.get('email', '')

        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Store OTP in cache (expires in 5 minutes)
        cache_key = f"otp_{phone}"
        cache.set(cache_key, otp, timeout=300)
        
        # Store signup data temporarily (for new users)
        if is_signup and (name or email):
            signup_data = {
                'name': name,
                'email': email,
                'is_signup': True
            }
            cache.set(f"signup_data_{phone}", signup_data, timeout=300)

        logger.info(f"Generated OTP for {phone}: {otp} (Signup: {is_signup})")

        # Send OTP via Route Mobile
        sms_service = RouteMobileSMS()
        result = sms_service.send_otp(phone, otp)

        if result['success']:
            # Store message_id for tracking (optional)
            if result.get('message_id'):
                cache.set(f"otp_msg_{phone}", result['message_id'], timeout=300)

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


# accounts/serializers.py

class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15, required=True)
    otp = serializers.CharField(max_length=6, required=True)

    def validate_phone(self, value):
        """Normalize phone number (same as SendOTP)"""
        # Remove any spaces or special characters
        phone = value.strip().replace(' ', '').replace('-', '')

        # Add +91 prefix if not present
        if not phone.startswith('+91'):
            phone = '+91' + phone.lstrip('0')

        if len(phone) < 13:  # +91 (3) + 10 digits
            raise serializers.ValidationError("Invalid phone number")

        return phone

    def validate(self, data):
        phone = data.get('phone')  # Already normalized by validate_phone
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
        phone = self.validated_data['phone']  # Already has +91
        
        # Get signup data from cache (if exists)
        signup_data = cache.get(f"signup_data_{phone}", {})
        is_signup = signup_data.get('is_signup', False)
        name = signup_data.get('name', '')
        email = signup_data.get('email', '')
        
        # Get referral codes from context
        invite_code = self.context.get('invite_code')
        referral_code = self.context.get('referral_code')

        # Check if user exists
        try:
            user = User.objects.get(phone=phone)
            created = False
            
            # If user exists, just mark phone as verified and return
            if not user.phone_verified:
                user.phone_verified = True
                user.save()
            
            logger.info(f"User logged in: {phone}")
            
        except User.DoesNotExist:
            # User doesn't exist - should only create if is_signup=True
            if not is_signup:
                raise serializers.ValidationError({
                    'error': 'user_not_found',
                    'message': 'User not found. Please signup first.'
                })
            
            # Create new user (signup flow)
            user = User.objects.create(
                phone=phone,
                username=name if name else phone,
                email=email if email else '',
                phone_verified=True,
                is_active=True,
            )
            created = True
            
            # Auto-assign customer role
            try:
                customer_role = Role.objects.get(slug='customer')
                user.role = customer_role
                user.save()
                logger.info(f"Created new user and assigned customer role: {phone}")
            except Role.DoesNotExist:
                logger.warning("Customer role not found. Creating user without role.")
            
            # Clear signup data from cache after user creation
            cache.delete(f"signup_data_{phone}")
            
            # ============================================
            # HANDLE CP REFERRAL CODES (NEW)
            # ============================================
            if created:
                try:
                    from partners.services.referral_service import ReferralService
                    from partners.models import CPCustomerRelation, CPLead, CPInvite
                    from django.utils import timezone
                    
                    # Priority 1: Handle CP Invite Code
                    if invite_code:
                        try:
                            invite = CPInvite.objects.get(
                                invite_code=invite_code,
                                is_used=False,
                                is_expired=False
                            )
                            
                            # Check expiry
                            if invite.expiry_date >= timezone.now():
                                # Mark invite as used and create CP-Customer relation
                                invite.mark_as_used(user)
                                logger.info(f"User {phone} linked to CP via invite: {invite_code}")
                            else:
                                logger.warning(f"Invite code expired: {invite_code}")
                        
                        except CPInvite.DoesNotExist:
                            logger.warning(f"Invalid invite code: {invite_code}")
                    
                    # Priority 2: Handle CP Referral Code (if no invite used)
                    elif referral_code:
                        cp = ReferralService.get_cp_from_referral_code(referral_code)
                        
                        if cp:
                            # Create CP-Customer relationship
                            CPCustomerRelation.objects.create(
                                cp=cp,
                                customer=user,
                                referral_code=referral_code,
                                is_active=True,
                            )
                            logger.info(f"User {phone} linked to CP: {cp.cp_code}")
                        else:
                            logger.warning(f"Invalid referral code: {referral_code}")
                    
                    # Priority 3: Check if user exists in any CP Lead
                    # If customer matches a lead's phone, convert lead
                    try:
                        lead = CPLead.objects.filter(
                            phone=phone,
                            lead_status__in=['new', 'contacted', 'interested', 'site_visit_scheduled', 'site_visit_done', 'negotiation']
                        ).first()
                        
                        if lead:
                            # Convert lead to customer
                            lead.convert_to_customer(user)
                            logger.info(f"Converted lead to customer: {phone} for CP: {lead.cp.cp_code}")
                    
                    except Exception as e:
                        logger.error(f"Error converting lead: {e}")
                
                except Exception as e:
                    # Don't fail user creation if CP linking fails
                    logger.error(f"Error handling CP referral for {phone}: {e}")

        return user, created


class UserRegistrationSerializer(serializers.Serializer):
    """Complete user profile after OTP verification"""
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    date_of_birth = serializers.DateField(required=True)


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
        user.save()

        return user


class RoleSerializer(serializers.ModelSerializer):
    """Role serializer"""
    class Meta:
        model = Role
        fields = ['id', 'name', 'slug', 'display_name', 'description', 'level', 'color']


class UserSerializer(serializers.ModelSerializer):
    """User details serializer"""
    role = RoleSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'phone_verified',
            'first_name', 'last_name', 'date_of_birth', 'avatar',
            'kyc_status', 'role', 'permissions',
            'is_indian',  # 👈 ADD THIS
            'profile_completed',  # 👈 ADD THIS
        ]
        read_only_fields = ['phone', 'phone_verified', 'kyc_status', 'profile_completed']

    def get_permissions(self, obj):
        """Get user's permissions via their role"""
        if not obj.role:
            return []
        
        permissions = obj.get_permissions().values_list('code_name', flat=True)
        return list(permissions)


class UserListSerializer(serializers.ModelSerializer):
    """Simplified user serializer for lists"""
    role_name = serializers.CharField(source='role.display_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 
            'first_name', 'last_name', 'role_name', 
            'is_active', 'kyc_status'
        ]



class CompleteProfileSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    date_of_birth = serializers.DateField(required=True)
    is_indian = serializers.BooleanField(required=True)
    
    
    def validate_username(self, value):
        # Check if username already exists
        if User.objects.filter(username=value).exclude(id=self.context['user'].id).exists():
            raise serializers.ValidationError("Username already taken")
        return value
    
    def validate_email(self, value):
        # Check if email already exists
        if User.objects.filter(email=value).exclude(id=self.context['user'].id).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_date_of_birth(self, value):
        # Must be 18+ years old
        from datetime import date
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise serializers.ValidationError("Must be at least 18 years old")
        return value
    
    def update(self, instance, validated_data):
        instance.username = validated_data['username']
        instance.email = validated_data['email']
        instance.date_of_birth = validated_data['date_of_birth']
        instance.is_indian = validated_data['is_indian']
        instance.profile_completed = True
        instance.save()
        return instance