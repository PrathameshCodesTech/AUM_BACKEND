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
        fields = ['id', 'username', 'email', 'phone', 'first_name', 'middle_name', 'last_name', 'legal_full_name', 'date_of_birth']


class AdminKYCListSerializer(serializers.ModelSerializer):
    """KYC list serializer for admin — includes identity match visibility"""
    user = AdminKYCUserSerializer(read_only=True)

    class Meta:
        model = KYC
        fields = [
            'id',
            'user',
            'status',

            # Aadhaar review-lock state (primary story for list)
            'aadhaar_review_status',
            'aadhaar_locked',
            'aadhaar_name',
            'aadhaar_number',

            # PAN review-lock state (primary story for list)
            'pan_review_status',
            'pan_locked',
            'pan_name',
            'pan_number',

            # Bank
            'bank_verified',
            'bank_name',
            'account_number',

            # Identity match (used for Aadhaar mismatch indicator)
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
    aadhaar_locked_by_name = serializers.CharField(source='aadhaar_locked_by.username', read_only=True)
    pan_locked_by_name = serializers.CharField(source='pan_locked_by.username', read_only=True)

    # Profile identity derived from user model
    profile_identity = serializers.SerializerMethodField()
    # Sanitized Aadhaar provider response (no full Aadhaar number)
    sanitized_aadhaar_response = serializers.SerializerMethodField()
    # PAN provider match evidence (name_status, dob_status, sanitized payload)
    pan_review_evidence = serializers.SerializerMethodField()

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

            # Aadhaar lock / review
            'aadhaar_locked',
            'aadhaar_review_status',
            'aadhaar_locked_at',
            'aadhaar_locked_by_name',
            'aadhaar_review_note',

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

            # PAN lock / review
            'pan_locked',
            'pan_review_status',
            'pan_locked_at',
            'pan_locked_by_name',
            'pan_review_note',

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
            'pan_review_evidence',

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
            'middle_name':     getattr(u, 'middle_name', '') or '',
            'last_name':       u.last_name or '',
            'date_of_birth':   str(u.date_of_birth) if u.date_of_birth else None,
        }

    def get_pan_review_evidence(self, obj):
        """
        PAN provider match evidence for admin review.
        Extracts name_status and dob_status from the stored pan_api_response,
        plus a sanitized copy of the payload (no full PAN number beyond what's
        already stored in pan_number).
        """
        raw = obj.pan_api_response
        if not raw or not isinstance(raw, dict):
            return None

        data = raw.get('data', raw)  # Surepass wraps results in 'data'
        if not isinstance(data, dict):
            data = raw

        evidence = {
            'pan_provider_status':    data.get('pan_status')              or raw.get('pan_status')              or None,
            'name_status':            data.get('name_status')             or raw.get('name_status'),
            'dob_status':             data.get('dob_status')              or raw.get('dob_status'),
            'aadhaar_seeding_status': data.get('aadhaar_seeding_status')  or raw.get('aadhaar_seeding_status')  or None,
            'pan_name':               data.get('name')                    or raw.get('name') or obj.pan_name or None,
            'pan_dob':                data.get('dob')                     or raw.get('dob')  or None,
            'pan_type':               data.get('pan_type')                or raw.get('pan_type') or None,
        }
        # Include sanitized raw payload for advanced review (strip nothing sensitive
        # since PAN number is already stored separately and raw payload has names/dob only)
        OMIT = {'pan_number', 'id_number'}
        evidence['sanitized_payload'] = {k: v for k, v in data.items() if k not in OMIT}
        return evidence

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
