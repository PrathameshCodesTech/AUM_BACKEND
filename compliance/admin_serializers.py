"""
Admin KYC Serializers
For admin KYC management
"""
from rest_framework import serializers
from .models import KYC
from accounts.models import User


class AdminKYCUserSerializer(serializers.ModelSerializer):
    """Minimal user info for KYC list"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone']


class AdminKYCListSerializer(serializers.ModelSerializer):
    """KYC list serializer for admin"""
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
            'created_at',
            'updated_at',
            'verified_at',
        ]
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Admin can see full numbers - NO masking
        return data


class AdminKYCDetailSerializer(serializers.ModelSerializer):
    """Detailed KYC info for admin review"""
    user = AdminKYCUserSerializer(read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.username', read_only=True)
    
    class Meta:
        model = KYC
        fields = [
            'id',
            'user',
            'status',
            
            # Aadhaar
            'aadhaar_number',
            'aadhaar_name',
            'aadhaar_dob',
            'aadhaar_gender',
            'aadhaar_address',
            'aadhaar_verified',
            'aadhaar_verified_at',
            'aadhaar_front',
            'aadhaar_back',
            
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
            
            # Validation
            'name_match_score',
            'name_validation_status',
            'dob_validation_status',
            'validation_errors',
            
            # Status
            'verified_at',
            'verified_by_name',
            'rejection_reason',
            
            # Timestamps
            'created_at',
            'updated_at',
        ]


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