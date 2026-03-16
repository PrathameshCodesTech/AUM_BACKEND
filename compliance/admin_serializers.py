"""
Admin KYC Serializers
For admin KYC management
"""
from rest_framework import serializers
from .models import KYC
from accounts.models import User


class AdminKYCUserSerializer(serializers.ModelSerializer):
    """Minimal user info for KYC list — includes legal identity fields"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'first_name', 'last_name', 'legal_full_name', 'date_of_birth']


class AdminKYCListSerializer(serializers.ModelSerializer):
    """KYC list serializer for admin — includes identity match visibility"""
    user = AdminKYCUserSerializer(read_only=True)

    class Meta:
        model = KYC
        fields = [
            'id',
            'user',
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
            'account_number',
            'name_match_score',
            'name_validation_status',
            'dob_validation_status',
            'created_at',
            'updated_at',
            'verified_at',
        ]


class AdminKYCDetailSerializer(serializers.ModelSerializer):
    """Detailed KYC info for admin review — includes identity comparison data"""
    user = AdminKYCUserSerializer(read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.username', read_only=True)

    # Profile identity derived from user model
    profile_identity = serializers.SerializerMethodField()
    # Sanitized Aadhaar provider response (no full Aadhaar number)
    sanitized_aadhaar_response = serializers.SerializerMethodField()

    class Meta:
        model = KYC
        fields = [
            'id',
            'user',
            'status',

            # Profile identity (from user model)
            'profile_identity',

            # Aadhaar returned identity
            'aadhaar_number',
            'aadhaar_name',
            'aadhaar_dob',
            'aadhaar_gender',
            'aadhaar_address',
            'aadhaar_verified',
            'aadhaar_verified_at',
            'aadhaar_front',
            'aadhaar_back',

            # Identity validation results
            'name_match_score',
            'name_validation_status',
            'dob_validation_status',
            'validation_errors',

            # PAN
            'pan_number',
            'pan_name',
            'pan_father_name',
            'pan_dob',
            'pan_verified',
            'pan_verified_at',
            'pan_aadhaar_linked',
            'pan_document',

            # Bank
            'bank_name',
            'account_number',
            'ifsc_code',
            'account_holder_name',
            'account_type',
            'bank_verified',
            'bank_verified_at',
            'bank_proof',

            # Address
            'address_line1',
            'address_line2',
            'city',
            'state',
            'pincode',
            'address_proof',

            # Sanitized provider payloads
            'sanitized_aadhaar_response',

            # Status
            'verified_at',
            'verified_by_name',
            'rejection_reason',

            # Timestamps
            'created_at',
            'updated_at',
        ]

    def get_profile_identity(self, obj):
        """User's declared legal identity at the time of admin review."""
        u = obj.user
        return {
            'legal_full_name': u.legal_full_name or '',
            'first_name':      u.first_name or '',
            'last_name':       u.last_name or '',
            'date_of_birth':   str(u.date_of_birth) if u.date_of_birth else None,
        }

    def get_sanitized_aadhaar_response(self, obj):
        """
        Return sanitized Aadhaar API response.
        If the stored payload already went through our sanitization step it will
        have no full Aadhaar number.  For older records that may have raw data,
        we strip the sensitive fields here so the admin UI never shows a full UID.
        """
        raw = obj.aadhaar_api_response
        if not raw or not isinstance(raw, dict):
            return None

        SENSITIVE = {'aadhaar_number', 'uid', 'masked_aadhaar', 'xml_data', 'zip_data', 'file_url'}
        safe = {k: v for k, v in raw.items() if k not in SENSITIVE}

        # Ensure last4 is present for reference
        num = raw.get('aadhaar_number') or raw.get('uid', '')
        if num and len(num) >= 4:
            safe['aadhaar_last4'] = num[-4:]

        return safe


class AdminKYCActionSerializer(serializers.Serializer):
    """KYC approval/rejection action"""
    action = serializers.ChoiceField(
        choices=['approve', 'reject'],
        required=True
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate(self, attrs):
        if attrs['action'] == 'reject' and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting KYC'
            })
        return attrs
