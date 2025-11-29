"""
KYC Serializers
Handles validation and serialization for KYC APIs
"""
from rest_framework import serializers
from .models import KYC
from .services import SurepassKYC
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


# ========================================
# AADHAAR VERIFICATION SERIALIZERS
# ========================================

# ========================================
# AADHAAR VERIFICATION (PDF UPLOAD)
# ========================================

class AadhaarPDFUploadSerializer(serializers.Serializer):
    """Serializer for Aadhaar PDF upload"""
    pdf_file = serializers.FileField(required=True)
    yob = serializers.CharField(required=False, max_length=4, allow_blank=True)
    full_name = serializers.CharField(required=False, max_length=255, allow_blank=True)
    
    def validate_pdf_file(self, value):
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are allowed")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 5MB")
        return value
    
    def validate_yob(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("Year of birth must be numeric")
        if value and (int(value) < 1900 or int(value) > 2024):
            raise serializers.ValidationError("Invalid year of birth")
        return value
    
    def verify(self, user):
        """Verify Aadhaar PDF and update KYC"""
        from .services.kyc_service import SurepassKYC
        
        pdf_file = self.validated_data['pdf_file']
        yob = self.validated_data.get('yob')
        full_name = self.validated_data.get('full_name')
        
        kyc_service = SurepassKYC()
        result = kyc_service.verify_aadhaar_pdf(pdf_file, yob, full_name)
        
        if not result.get('success'):
            raise serializers.ValidationError(result.get('error', 'Aadhaar verification failed'))
        
        data = result.get('data', {})
        kyc, created = KYC.objects.get_or_create(user=user)
        
        kyc.aadhaar_number = data.get('aadhaar_number', '').replace(' ', '')[-4:]
        kyc.aadhaar_name = data.get('name', '')
        
        dob_str = data.get('dob', '')
        if dob_str:
            try:
                from datetime import datetime
                kyc.aadhaar_dob = datetime.strptime(dob_str, '%d/%m/%Y').date()
            except:
                pass
        
        kyc.aadhaar_gender = data.get('gender', '')
        
        split_addr = data.get('split_address', {})
        if split_addr:
            kyc.address_line1 = f"{split_addr.get('house', '')} {split_addr.get('street', '')}".strip()
            kyc.city = split_addr.get('vtc', '')
            kyc.state = split_addr.get('state', '')
            kyc.pincode = split_addr.get('pincode', '')
            kyc.aadhaar_address = data.get('address', '')
        
        kyc.aadhaar_verified = True
        kyc.aadhaar_verified_at = timezone.now()
        kyc.aadhaar_api_response = data
        kyc.status = 'under_review'
        kyc.save()
        
        logger.info(f"✅ Aadhaar PDF verified for user: {user.username}")
        
        return {
            'success': True,
            'data': data,
            'kyc_updated': True
        }

# ========================================
# PAN VERIFICATION SERIALIZERS
# ========================================

class PANVerifySerializer(serializers.Serializer):
    """Verify PAN card details"""
    pan_number = serializers.CharField(
        max_length=10,
        min_length=10,
        required=True,
        help_text="10-character PAN number"
    )
    
    def validate_pan_number(self, value):
        """Validate PAN format: AAAAA9999A"""
        import re
        value = value.upper()
        
        pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        if not re.match(pan_pattern, value):
            raise serializers.ValidationError(
                "Invalid PAN format. Must be: 5 letters, 4 digits, 1 letter"
            )
        return value
    
    def verify(self, user):
        """Verify PAN and update KYC"""
        from .services.kyc_service import SurepassKYC
        
        pan_number = self.validated_data['pan_number']
        kyc_service = SurepassKYC()
        result = kyc_service.verify_pan(pan_number)
        
        if not result.get('success'):
            raise serializers.ValidationError(result.get('error', 'PAN verification failed'))
        
        data = result.get('data', {})
        kyc, created = KYC.objects.get_or_create(user=user)
        
        kyc.pan_number = pan_number.upper()
        kyc.pan_name = data.get('full_name', '')
        kyc.pan_aadhaar_linked = data.get('aadhaar_linked', False)
        kyc.pan_verified = True
        kyc.pan_verified_at = timezone.now()
        kyc.pan_api_response = data
        kyc.status = 'under_review'
        kyc.save()
        
        logger.info(f"✅ PAN verified for user: {user.username}")
        
        return {
            'success': True,
            'data': data,
            'kyc_updated': True
        }



# ========================================
# BANK VERIFICATION SERIALIZER
# ========================================

class BankVerifySerializer(serializers.Serializer):
    """Verify bank account details"""
    account_number = serializers.CharField(
        max_length=20,
        required=True,
        help_text="Bank account number"
    )
    ifsc_code = serializers.CharField(
        max_length=11,
        min_length=11,
        required=True,
        help_text="11-character IFSC code"
    )
    
    def validate_account_number(self, value):
        """Validate account number"""
        if not value.isdigit():
            raise serializers.ValidationError("Account number must contain only digits")
        return value
    
    def validate_ifsc_code(self, value):
        """Validate IFSC format: AAAA0999999"""
        import re
        value = value.upper()
        
        ifsc_pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
        if not re.match(ifsc_pattern, value):
            raise serializers.ValidationError(
                "Invalid IFSC format. Must be: 4 letters, 0, 6 alphanumeric (e.g., HDFC0001234)"
            )
        return value
    
    def create(self, validated_data):
        """Verify bank account via Surepass API"""
        account_number = validated_data['account_number']
        ifsc_code = validated_data['ifsc_code']
        
        kyc_service = SurepassKYC()
        result = kyc_service.verify_bank_account(account_number, ifsc_code)
        
        if not result['success']:
            raise serializers.ValidationError(result['message'])
        
        # Update KYC record
        user = self.context.get('request').user
        kyc, created = KYC.objects.get_or_create(user=user)
        
        bank_data = result['data']
        
        kyc.account_number = account_number
        kyc.ifsc_code = ifsc_code
        kyc.account_holder_name = bank_data.get('account_name')
        kyc.bank_name = bank_data.get('bank_name')
        kyc.account_type = bank_data.get('account_type')
        kyc.bank_verified = True
        kyc.bank_verified_at = timezone.now()
        kyc.bank_api_response = result['data']
        
        if kyc.status == 'pending':
            kyc.status = 'under_review'
        
        kyc.save()
        
        logger.info(f"✅ Bank account verified and stored for user: {user.username}")
        
        return {
            **result,
            'kyc_updated': True
        }


# ========================================
# COMPLETE KYC SERIALIZER
# ========================================

class KYCSerializer(serializers.ModelSerializer):
    """Complete KYC details serializer"""
    
    class Meta:
        model = KYC
        fields = [
            'id',
            'user',
            'aadhaar_number',
            'aadhaar_name',
            'aadhaar_verified',
            'pan_number',
            'pan_name',
            'pan_verified',
            'pan_aadhaar_linked',
            'bank_name',
            'account_number',
            'ifsc_code',
            'account_holder_name',
            'bank_verified',
            'status',
            'verified_at',
            'rejection_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'aadhaar_verified',
            'pan_verified',
            'bank_verified',
            'status',
            'verified_at',
            'created_at',
            'updated_at',
        ]


class KYCStatusSerializer(serializers.ModelSerializer):
    """KYC status for user dashboard"""
    is_complete = serializers.SerializerMethodField()
    
    class Meta:
        model = KYC
        fields = [
            'status',
            'aadhaar_verified',
            'pan_verified',
            'bank_verified',
            'pan_aadhaar_linked',
            'is_complete',
            'rejection_reason',
        ]
    
    def get_is_complete(self, obj):
        return obj.is_complete()


class KYCApprovalSerializer(serializers.Serializer):
    """Admin approval/rejection"""
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