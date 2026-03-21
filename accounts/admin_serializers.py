"""
Admin Serializers
For admin dashboard APIs
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from compliance.models import KYC
from properties.models import Property
from investments.models import Investment

User = get_user_model()


# ========================================
# DASHBOARD STATS SERIALIZER
# ========================================

class AdminDashboardStatsSerializer(serializers.Serializer):
    """Dashboard statistics"""
    total_users = serializers.IntegerField()
    verified_users = serializers.IntegerField()
    suspended_users = serializers.IntegerField()
    pending_kyc = serializers.IntegerField()
    approved_kyc = serializers.IntegerField()
    rejected_kyc = serializers.IntegerField()
    total_properties = serializers.IntegerField()
    published_properties = serializers.IntegerField()
    total_investments = serializers.IntegerField()
    total_investment_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2)


# ========================================
# USER MANAGEMENT SERIALIZERS
# ========================================

class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users in admin dashboard"""
    kyc_status = serializers.SerializerMethodField()
    total_investments = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'phone',
            'email',
            'first_name',
            'last_name',
            'username',
            'date_of_birth',
            'is_indian',
            'is_verified',
            'is_suspended',
            'is_blocked',
            'profile_completed',
            'kyc_status',
            'role_name',
            'total_investments',
            'date_joined',
            'last_login',
        ]
    
    def get_kyc_status(self, obj):
        """Get KYC status from compliance.KYC model"""
        try:
            kyc = KYC.objects.get(user=obj)
            return kyc.status
        except KYC.DoesNotExist:
            return 'not_started'
    
    def get_total_investments(self, obj):
        """Get total number of investments"""
        return Investment.objects.filter(customer=obj).count()  # 👈 CHANGED to customer
    
    def get_role_name(self, obj):
        """Get user's role display name"""
        return obj.role.display_name if obj.role else 'No Role'


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Detailed user info for admin"""
    kyc_details = serializers.SerializerMethodField()
    investments = serializers.SerializerMethodField()
    role_details = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'phone',
            'email',
            'first_name',
            'last_name',
            'username',
            'date_of_birth',
            'is_indian',
            'is_verified',
            'is_suspended',
            'suspended_reason',
            'suspended_at',
            'is_blocked',
            'blocked_reason',
            'blocked_at',
            'profile_completed',
            'role_details',
            'kyc_details',
            'investments',
            'date_joined',
            'last_login',
            'avatar',
            'address',
            'city',
            'state',
            'country',
            'pincode',
        ]
    
    def get_role_details(self, obj):
        """Get user's role information"""
        if not obj.role:
            return None
        return {
            'name': obj.role.name,
            'display_name': obj.role.display_name,
            'slug': obj.role.slug,
            'level': obj.role.level,
        }
    
    def get_kyc_details(self, obj):
        """Get COMPLETE KYC details"""
        try:
            kyc = KYC.objects.get(user=obj)
            return {
                'id': kyc.id,
                'status': kyc.status,
                
                # Aadhaar
                'aadhaar_verified': kyc.aadhaar_verified,
                'aadhaar_number': kyc.aadhaar_number,
                'aadhaar_name': kyc.aadhaar_name,
                'aadhaar_dob': kyc.aadhaar_dob,
                'aadhaar_gender': kyc.aadhaar_gender,
                'aadhaar_address': kyc.aadhaar_address,
                
                # PAN
                'pan_verified': kyc.pan_verified,
                'pan_number': kyc.pan_number,
                'pan_name': kyc.pan_name,
                'pan_dob': kyc.pan_dob,
                'pan_aadhaar_linked': kyc.pan_aadhaar_linked,
                
                # Bank
                'bank_verified': kyc.bank_verified,
                'bank_name': kyc.bank_name,
                'account_number': kyc.account_number,
                'ifsc_code': kyc.ifsc_code,
                'account_holder_name': kyc.account_holder_name,
                'account_type': kyc.account_type,
                
                # Validation
                'name_match_score': str(kyc.name_match_score) if kyc.name_match_score else None,
                'name_validation_status': kyc.name_validation_status,
                
                # Status
                'rejection_reason': kyc.rejection_reason,
                'created_at': kyc.created_at,
                'verified_at': kyc.verified_at,
            }
        except KYC.DoesNotExist:
            return None
    
    def get_investments(self, obj):
        """Get user's investments"""
        try:
            investments = Investment.objects.filter(customer=obj).select_related('property')[:10]
            return [{
                'id': inv.id,
                'property_id': inv.property.id,
                'property_name': inv.property.name,
                'amount': str(inv.amount),
                'units': inv.units_purchased,
                'status': inv.status,
                'created_at': inv.created_at,
            } for inv in investments]
        except Exception as e:
            return []

class AdminUserActionSerializer(serializers.Serializer):
    """Serializer for user actions (verify, suspend, unsuspend, block)"""
    action = serializers.ChoiceField(
        choices=['verify', 'suspend', 'unsuspend', 'block', 'unblock'],
        required=True
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required for suspend/block actions"
    )

    def validate(self, attrs):
        action = attrs['action']
        reason = attrs.get('reason', '')

        # Require reason for suspend/block
        if action in ['suspend', 'block'] and not reason:
            raise serializers.ValidationError({
                'reason': f'Reason is required when {action}ing a user'
            })

        return attrs


# ========================================
# KYC MANAGEMENT SERIALIZERS
# ========================================

class AdminKYCListSerializer(serializers.ModelSerializer):
    """Serializer for listing KYC submissions"""
    user_name = serializers.CharField(source='user.username')
    user_phone = serializers.CharField(source='user.phone')
    user_email = serializers.CharField(source='user.email')

    class Meta:
        model = KYC
        fields = [
            'id',
            'user',
            'user_name',
            'user_phone',
            'user_email',
            'status',
            'aadhaar_verified',
            'aadhaar_number',
            'aadhaar_name',
            'pan_verified',
            'pan_number',
            'pan_name',
            'pan_aadhaar_linked',
            'bank_verified',
            'bank_name',
            'name_match_score',
            'name_validation_status',
            'rejection_reason',
            'created_at',
            'updated_at',
            'verified_at',
        ]


class AdminKYCDetailSerializer(serializers.ModelSerializer):
    """Detailed KYC info for admin review"""
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = KYC
        fields = '__all__'

    def get_user_details(self, obj):
        """Get user information"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'phone': obj.user.phone,
            'email': obj.user.email,
            'date_of_birth': obj.user.date_of_birth,
            'is_indian': obj.user.is_indian,
        }


class AdminKYCActionSerializer(serializers.Serializer):
    """Serializer for KYC approval/rejection"""
    action = serializers.ChoiceField(
        choices=['approve', 'reject'],
        required=True
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required if action is 'reject'"
    )

    def validate(self, attrs):
        if attrs['action'] == 'reject' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting KYC'
            })
        return attrs

class UserUpdateSerializer(serializers.ModelSerializer):
    """Admin-only: update user with privileged fields.

    Mirrors CompleteProfileSerializer identity logic:
    - derives legal_full_name from first/middle/last name automatically
    - respects aadhaar_locked: identity fields cannot be changed after lock
    """
    middle_name     = serializers.CharField(max_length=150, required=False, allow_blank=True)
    legal_full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'middle_name',
            'last_name',
            'legal_full_name',
            'username',
            'email',
            'phone',
            'date_of_birth',
            'is_indian',
            'role',
            'profile_completed',
            'kyc_status',
            'is_verified',
            'is_suspended',
            'suspended_reason',
            'is_blocked',
            'blocked_reason',
        ]
        read_only_fields = ['is_verified', 'is_suspended', 'is_blocked']

    def update(self, instance, validated_data):
        # ── Derive canonical legal_full_name from split fields ──────────────
        new_first  = validated_data.get('first_name',  instance.first_name or '').strip()
        new_middle = validated_data.get('middle_name', getattr(instance, 'middle_name', '') or '').strip()
        new_last   = validated_data.get('last_name',   instance.last_name or '').strip()
        derived_legal = ' '.join(filter(None, [new_first, new_middle, new_last])).strip()
        if not derived_legal:
            derived_legal = (validated_data.get('legal_full_name') or '').strip()

        # ── Identity field lock — consistent with normal profile serializer ──
        try:
            from compliance.models import KYC
            kyc = KYC.objects.get(user=instance)
            if kyc.aadhaar_locked:
                locked = []
                new_dob = validated_data.get('date_of_birth')
                if derived_legal and derived_legal != (instance.legal_full_name or ''):
                    locked.extend(['first_name', 'middle_name', 'last_name', 'legal_full_name'])
                if new_dob and new_dob != instance.date_of_birth:
                    locked.append('date_of_birth')
                if locked:
                    raise serializers.ValidationError({
                        f: "Cannot change this field after Aadhaar has been approved and locked. "
                           "Use the admin KYC unlock flow if a genuine correction is needed."
                        for f in ['first_name', 'middle_name', 'last_name', 'legal_full_name', 'date_of_birth']
                        if f in locked
                    })
        except serializers.ValidationError:
            raise
        except Exception:
            pass  # KYC.DoesNotExist or import error — allow update

        # ── Persist all provided fields ──────────────────────────────────────
        for field in ['username', 'email', 'phone', 'date_of_birth', 'is_indian',
                      'role', 'profile_completed', 'kyc_status', 'suspended_reason', 'blocked_reason']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Identity split fields
        if new_first:
            instance.first_name = new_first
        instance.middle_name = new_middle  # always save (can be blank)
        if new_last:
            instance.last_name = new_last
        # Canonical compliance field — always derived from split names when available
        if derived_legal:
            instance.legal_full_name = derived_legal

        instance.save()
        return instance


def generate_unique_username(first_name):
    base_username = first_name.strip().lower().replace(" ", "")

    if not base_username:
        base_username = "user"

    username = base_username
    counter = 1

    from django.contrib.auth import get_user_model
    User = get_user_model()

    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{counter}"
        counter += 1

    return username

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value

    def create(self, validated_data):
        user = User(**validated_data)

        # Generate username from first_name
        user.username = generate_unique_username(user.first_name)

        # Derive legal_full_name from split fields
        parts = [user.first_name or '', user.last_name or '']
        derived = ' '.join(filter(None, parts)).strip()
        if derived:
            user.legal_full_name = derived

        # Password not required
        user.set_unusable_password()

        # Defaults
        user.is_active = True
        user.is_verified = False
        user.profile_completed = False

        user.save()
        return user
