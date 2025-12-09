# accounts/serializers.py
from rest_framework import serializers
from accounts.models import User, Role
from accounts.services import RouteMobileSMS
from django.core.cache import cache
import random
from django.db import models  # Add this if not present
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

    def send_otp(self, request=None):
        """Send OTP using database model"""
        from accounts.models import OTPVerification
        from django.utils import timezone
        from datetime import timedelta
        from django.conf import settings
        import random
        
        phone = self.validated_data['phone']
        is_signup = self.validated_data.get('is_signup', False)
        name = self.validated_data.get('name', '')
        email = self.validated_data.get('email', '')
        
        # Get IP address
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        # ============================================
        # RATE LIMITING CHECK
        # ============================================
        can_send, request_count = OTPVerification.check_rate_limit(
            phone=phone,
            minutes=15,
            max_requests=3
        )
        
        if not can_send:
            raise serializers.ValidationError({
                'error': 'rate_limit_exceeded',
                'message': f'Too many OTP requests. Please try again after 15 minutes. (Attempts: {request_count}/3)'
            })
        
        # ============================================
        # CHECK FOR EXISTING ACTIVE OTP
        # ============================================
        existing_otp = OTPVerification.get_active_otp(phone)
        
        if existing_otp and not existing_otp.is_expired():
            # OTP still valid - resend same OTP
            logger.info(f"Resending existing OTP for {phone}")
            otp_code = existing_otp.otp_code
            
            # Send SMS with existing OTP
            sms_service = RouteMobileSMS()
            sms_result = sms_service.send_otp(phone, otp_code)
            
            if sms_result['success']:
                # Update SMS tracking
                existing_otp.sms_sent = True
                existing_otp.sms_message_id = sms_result.get('message_id', '')
                existing_otp.save(update_fields=['sms_sent', 'sms_message_id', 'updated_at'])
                
                time_remaining = (existing_otp.expires_at - timezone.now()).seconds // 60
                
                return {
                    'success': True,
                    'phone': phone,
                    'message': f'OTP resent successfully. Valid for {time_remaining} minutes.',
                    'message_id': sms_result.get('message_id'),
                    'otp': otp_code if sms_result.get('status') == 'TEST_MODE' else None,
                    'expires_in_minutes': time_remaining
                }
            else:
                raise serializers.ValidationError(
                    sms_result.get('error', 'Failed to send OTP. Please try again.')
                )
        
        # ============================================
        # DEACTIVATE OLD OTPs
        # ============================================
        OTPVerification.objects.filter(
            phone=phone,
            is_active=True
        ).update(is_active=False)
        
        # ============================================
        # GENERATE NEW OTP
        # ============================================
        is_test_mode = getattr(settings, 'ROUTE_MOBILE_TEST_MODE', True)
        
        if is_test_mode:
            otp_code = '123456'
        else:
            otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Set expiry (5 minutes)
        expires_at = timezone.now() + timedelta(minutes=5)
        
        # Determine purpose
        purpose = 'signup' if is_signup else 'login'
        
        # ============================================
        # CREATE OTP RECORD
        # ============================================
        otp_record = OTPVerification.objects.create(
            phone=phone,
            otp_code=otp_code,
            expires_at=expires_at,
            ip_address=ip_address,
            purpose=purpose,
            is_active=True,
            is_verified=False,
            attempt_count=0
        )
        
        logger.info(f"Generated new OTP for {phone}: {otp_code} (Purpose: {purpose})")
        
        # ============================================
        # STORE SIGNUP DATA IN CACHE (TEMPORARY)
        # ============================================
        if is_signup and (name or email):
            from django.core.cache import cache
            signup_data = {
                'name': name,
                'email': email,
                'is_signup': True
            }
            cache.set(f"signup_data_{phone}", signup_data, timeout=300)
        
        # ============================================
        # SEND SMS
        # ============================================
        sms_service = RouteMobileSMS()
        sms_result = sms_service.send_otp(phone, otp_code)
        
        if sms_result['success']:
            # Update OTP record with SMS status
            otp_record.sms_sent = True
            otp_record.sms_message_id = sms_result.get('message_id', '')
            otp_record.save(update_fields=['sms_sent', 'sms_message_id'])
            
            return {
                'success': True,
                'phone': phone,
                'message': 'OTP sent successfully',
                'message_id': sms_result.get('message_id'),
                'otp': otp_code if sms_result.get('status') == 'TEST_MODE' else None,
                'expires_in_minutes': 5
            }
        else:
            # SMS failed - mark OTP as not sent but keep it active for retry
            logger.warning(f"SMS failed for {phone}, but OTP record exists in DB")
            
            raise serializers.ValidationError(
                sms_result.get('error', 'Failed to send OTP. Please try again.')
            )

# accounts/serializers.py
class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15, required=True)
    otp = serializers.CharField(max_length=6, required=True)

    def validate_phone(self, value):
        """Normalize phone number (same as SendOTP)"""
        import re
        
        # Remove any spaces, dashes, or other non-digit characters except +
        phone = re.sub(r'[^\d+]', '', value.strip())
        
        # Remove + temporarily for digit counting
        digits_only = phone.replace('+', '')
        
        # Handle different formats
        if len(digits_only) == 10:
            phone = f'+91{digits_only}'
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            phone = f'+{digits_only}'
        elif len(digits_only) == 11 and digits_only.startswith('0'):
            phone = f'+91{digits_only[1:]}'
        elif phone.startswith('+91') and len(digits_only) == 12:
            pass
        else:
            raise serializers.ValidationError("Invalid phone number format")
        
        # Final validation
        if not re.match(r'^\+91\d{10}$', phone):
            raise serializers.ValidationError("Phone must be in format +91XXXXXXXXXX")
        
        return phone

    def validate(self, data):
        """Validate OTP against database"""
        from accounts.models import OTPVerification
        from django.utils import timezone
        
        phone = data.get('phone')
        otp_code = data.get('otp')
        
        # ============================================
        # GET ACTIVE OTP FROM DATABASE
        # ============================================
        otp_record = OTPVerification.get_active_otp(phone)
        
        if not otp_record:
            raise serializers.ValidationError({
                'error': 'otp_not_found',
                'message': 'OTP expired or not found. Please request a new OTP.'
            })
        
        # ============================================
        # CHECK IF OTP IS VALID
        # ============================================
        if not otp_record.is_valid():
            if otp_record.is_expired():
                raise serializers.ValidationError({
                    'error': 'otp_expired',
                    'message': 'OTP has expired. Please request a new OTP.'
                })
            
            if otp_record.attempt_count >= otp_record.max_attempts:
                raise serializers.ValidationError({
                    'error': 'max_attempts_exceeded',
                    'message': 'Too many failed attempts. Please request a new OTP.'
                })
            
            if otp_record.is_verified:
                raise serializers.ValidationError({
                    'error': 'otp_already_used',
                    'message': 'OTP already used. Please request a new OTP.'
                })
            
            raise serializers.ValidationError({
                'error': 'otp_invalid',
                'message': 'Invalid OTP. Please try again.'
            })
        
        # ============================================
        # VERIFY OTP CODE
        # ============================================
        if otp_record.otp_code != otp_code:
            # Increment attempt count
            otp_record.increment_attempt()
            
            attempts_remaining = otp_record.max_attempts - otp_record.attempt_count
            
            if attempts_remaining > 0:
                raise serializers.ValidationError({
                    'error': 'otp_mismatch',
                    'message': f'Invalid OTP. {attempts_remaining} attempts remaining.'
                })
            else:
                raise serializers.ValidationError({
                    'error': 'max_attempts_exceeded',
                    'message': 'Too many failed attempts. Please request a new OTP.'
                })
        
        # ============================================
        # OTP VERIFIED SUCCESSFULLY
        # ============================================
        otp_record.mark_verified()
        logger.info(f"OTP verified successfully for {phone}")
        
        # Store OTP record in validated data for later use
        data['_otp_record'] = otp_record
        
        return data

    def get_or_create_user(self):
        """Get or create user after OTP verification"""
        phone = self.validated_data['phone']
        otp_record = self.validated_data.get('_otp_record')
        
        # Get signup data from cache (if exists)
        from django.core.cache import cache
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
            


# ============================================
# 🆕 SEND SIGNUP CONFIRMATION EMAIL
# ============================================
             
            print("🔵 DEBUG: Checking email send conditions...")
            print(f"🔵 created = {created}")
            print(f"🔵 email = {email}")
            print(f"🔵 email bool = {bool(email)}")
            if created and email:
                print("🟢 DEBUG: Inside email sending block!")
                try:
                    print("🟢 Attempting to import send_dynamic_email...")
                    from accounts.services.email_service import send_dynamic_email
                    from django.conf import settings
                    
                    # Prepare email parameters
                    print("🟢 Import successful!")
                    user_name = name if name else user.username
                    print(f"🟢 user_name = {user_name}")
                    login_link = f"{settings.FRONTEND_BASE_URL}/login"  # You'll need to add FRONTEND_URL to settings
                    
                    # Send email
                    send_dynamic_email(
                        email_type='signup_confirmation',
                        to=email,
                        params={
                            'name': user_name,
                            'login_link': login_link,
                            'website': 'https://assetkart.com',
                            'support_email': 'support@assetkart.com'
                        }
                    )
                    
                    logger.info(f"✅ Signup confirmation email sent to {email}")
                    
                except Exception as e:
                    # Don't fail signup if email fails
                    logger.error(f"❌ Failed to send signup email to {email}: {str(e)}")




            # Clear signup data from cache after user creation
            cache.delete(f"signup_data_{phone}")
            
            # ============================================
            # HANDLE CP REFERRAL CODES
            # ============================================
            if created:
                try:
                    from partners.services.referral_service import ReferralService
                    from partners.models import CPCustomerRelation, CPLead, CPInvite
                    from django.utils import timezone
                    
                    # Priority 1: Handle CP Invite Code
                    # Priority 1: Handle CP Invite Code
                    if invite_code:
                        try:
                            # ✅ MODIFIED: Allow permanent invites even if "used"
                            invite = CPInvite.objects.filter(
                                invite_code=invite_code,
                                is_expired=False
                            ).filter(
                                models.Q(is_used=False) | models.Q(is_permanent=True)
                            ).first()
                            
                            if invite:
                                # Check expiry (permanent invites have no expiry)
                                if invite.is_permanent or (invite.expiry_date and invite.expiry_date >= timezone.now()):
                                    # Mark invite as used and create CP-Customer relation
                                    invite.mark_as_used(user)
                                    logger.info(f"User {phone} linked to CP via invite: {invite_code}")
                                else:
                                    logger.warning(f"Invite code expired: {invite_code}")
                            else:
                                logger.warning(f"Invalid or expired invite code: {invite_code}")
                        
                        except Exception as e:
                            logger.error(f"Error processing invite code {invite_code}: {e}")
                    
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
            'is_cp',              # NEW
            'cp_status',          # NEW
            'is_active_cp',       # NEW
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
    

class SendEmailSerializer(serializers.Serializer):
    email_type = serializers.ChoiceField(
        choices=[
            'signup_confirmation',
            'onboarding_completion',
            'eoi_approved',
            'payment_receipt',
            'feedback_request',
            'ticket_generated',
            'ticket_resolved',
            'upcoming_product',
            'new_product',
        ]
    )
    
    to = serializers.EmailField()
    params = serializers.DictField()