"""
KYC Serializers
Handles validation and serialization for KYC APIs
"""
from rest_framework import serializers
from .models import KYC
from .services import SurepassKYC
import logging
from django.utils import timezone
from django.conf import settings


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
    pincode = serializers.CharField(required=False, max_length=6, allow_blank=True)  # 👈 ADD THIS


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
        """Verify Aadhaar PDF and update KYC with validation"""
        from .services.kyc_service import SurepassKYC
        from .utils import fuzzy_name_match, validate_dob_match
        
        pdf_file = self.validated_data['pdf_file']
        yob = self.validated_data.get('yob')
        full_name = self.validated_data.get('full_name')
        
        # Step 1: Verify with Surepass
        pincode = self.validated_data.get('pincode')
        kyc_service = SurepassKYC()
        result = kyc_service.verify_aadhaar_pdf(pdf_file, yob, full_name)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Aadhaar verification failed')
        

             # Better error messages
            if 'password' in error_msg.lower() or 'unlock' in error_msg.lower():
                raise serializers.ValidationError(
                    "Could not unlock PDF. Please ensure you entered the correct Year of Birth (YOB) "
                    "that matches your Aadhaar card. The YOB is used as the PDF password."
                )
            elif 'Invalid eAadhaar PDF' in error_msg:
                raise serializers.ValidationError(
                    "Invalid eAadhaar PDF. Please upload a valid eAadhaar PDF downloaded from "
                    "the official UIDAI website (https://myaadhaar.uidai.gov.in/). "
                    "The PDF should not be modified or corrupted."
                )
            else:
                raise serializers.ValidationError(error_msg)
        
        data = result.get('data', {})
        
        # Step 2: Get user's profile data (source of truth)
        profile_name = user.username
        profile_dob = user.date_of_birth
        
        # Step 3: Extract Aadhaar data
        # Surepass API returns name in 'full_name' field, not 'name'
        aadhaar_name = data.get('full_name') or data.get('name', '')
        aadhaar_dob_str = data.get('dob', '')  # Format: YYYY-MM-DD or DD/MM/YYYY
        
        # Step 4: Validate Name Match
        name_validation = fuzzy_name_match(profile_name, aadhaar_name, threshold=0.75)
        
        if not name_validation['match']:
            # NAME MISMATCH - REJECT
            error_msg = (
                f"Name mismatch: Your profile name '{profile_name}' doesn't match "
                f"Aadhaar name '{aadhaar_name}'. Please ensure your profile name matches your Aadhaar card."
            )
            logger.error(f"❌ {error_msg} (Score: {name_validation['score']:.2%})")
            raise serializers.ValidationError(error_msg)
        
        # Step 5: Validate DOB Match
        if profile_dob and aadhaar_dob_str:
            dob_validation = validate_dob_match(profile_dob, aadhaar_dob_str)
            
            if not dob_validation['match']:
                # DOB MISMATCH - REJECT
                error_msg = (
                    f"Date of birth mismatch: Your profile DOB doesn't match Aadhaar DOB. "
                    f"Please ensure your profile DOB is correct."
                )
                logger.error(f"❌ {error_msg}")
                raise serializers.ValidationError(error_msg)
        
        # Step 6: Validation PASSED - Save data
        kyc, created = KYC.objects.get_or_create(user=user)
        
        # Surepass doesn't always return full aadhaar_number, might return last 4 digits or reference_id
        aadhaar_num = data.get('aadhaar_number', '') or data.get('last_digits', '') or data.get('reference_id', '')
        kyc.aadhaar_number = aadhaar_num.replace(' ', '')
        kyc.aadhaar_name = aadhaar_name
        
        # Store DOB
        # Store DOB (Surepass returns YYYY-MM-DD format)
        if aadhaar_dob_str:
            try:
                from datetime import datetime
                # Try YYYY-MM-DD format first (Surepass format)
                kyc.aadhaar_dob = datetime.strptime(aadhaar_dob_str, '%Y-%m-%d').date()
            except:
                try:
                    # Fallback to DD/MM/YYYY format
                    kyc.aadhaar_dob = datetime.strptime(aadhaar_dob_str, '%d/%m/%Y').date()
                except:
                    logger.warning(f"⚠️ Could not parse DOB: {aadhaar_dob_str}")
                    pass
        
        kyc.aadhaar_gender = data.get('gender', '')
        
        # Store address
        # Store address (Surepass returns 'address' object, not 'split_address')
        address_data = data.get('address', {}) or data.get('split_address', {})
        if address_data:
            house = address_data.get('house', '')
            street = address_data.get('street', '')
            kyc.address_line1 = f"{house} {street}".strip()
            kyc.city = address_data.get('vtc', '') or address_data.get('dist', '')
            kyc.state = address_data.get('state', '')
            kyc.pincode = address_data.get('zip', '') or data.get('zip', '')
            
            # Build full address
            full_addr = address_data.get('full_address', '')
            if not full_addr:
                # Construct from parts
                addr_parts = [house, street, address_data.get('loc', ''), 
                             address_data.get('vtc', ''), address_data.get('dist', ''),
                             address_data.get('state', '')]
                full_addr = ', '.join([p for p in addr_parts if p])
            
            kyc.aadhaar_address = full_addr
        
        # Mark as verified
        kyc.aadhaar_verified = True
        kyc.aadhaar_verified_at = timezone.now()
        kyc.aadhaar_api_response = data
        
        # Store validation results
        kyc.name_validation_status = 'passed'
        kyc.dob_validation_status = 'passed' if profile_dob else 'pending'
        kyc.name_match_score = round(name_validation['score'] * 100, 2)
        kyc.validation_errors = {}
        
        kyc.status = 'under_review'
        kyc.save()
        
        logger.info(f"✅ Aadhaar verified and validated for user: {user.username} (Name match: {name_validation['score']:.2%})")
        
        return {
            'success': True,
            'data': data,
            'kyc_updated': True,
            'validation': {
                'name_match': name_validation,
                'dob_match': dob_validation if profile_dob else {'match': True, 'reason': 'No DOB in profile'}
            }
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
        """Verify PAN and validate against Aadhaar"""
        from .services.kyc_service import SurepassKYC
        from .utils import fuzzy_name_match
        
        pan_number = self.validated_data['pan_number']
        
        # Step 1: Check if Aadhaar is verified
        try:
            kyc = KYC.objects.get(user=user)
            if not kyc.aadhaar_verified:
                raise serializers.ValidationError(
                    "Please verify your Aadhaar before verifying PAN"
                )
            aadhaar_name = kyc.aadhaar_name
        except KYC.DoesNotExist:
            raise serializers.ValidationError(
                "Please complete Aadhaar verification first"
            )
        
        # Step 2: Verify PAN with Surepass
        kyc_service = SurepassKYC()
        result = kyc_service.verify_pan(pan_number)
        
        if not result.get('success'):
            raise serializers.ValidationError(result.get('error', 'PAN verification failed'))
        
        data = result.get('data', {})
        pan_name = data.get('full_name', '')
        
        # Step 3: Validate PAN name against Aadhaar name
        name_validation = fuzzy_name_match(aadhaar_name, pan_name, threshold=0.75)
        
        if not name_validation['match']:
            # NAME MISMATCH - REJECT
            error_msg = (
                f"PAN name mismatch: PAN name '{pan_name}' doesn't match "
                f"your Aadhaar name '{aadhaar_name}'. Please ensure your PAN is linked to your Aadhaar."
            )
            logger.error(f"❌ {error_msg} (Score: {name_validation['score']:.2%})")
            
            # Mark for manual review instead of hard rejection
            kyc.validation_errors['pan_name_mismatch'] = {
                'aadhaar_name': aadhaar_name,
                'pan_name': pan_name,
                'score': name_validation['score'],
                'reason': name_validation['reason']
            }
            kyc.name_validation_status = 'needs_review'
            kyc.save()
            
            raise serializers.ValidationError(error_msg)
        
        # Step 4: Validation PASSED - Save data
        kyc.pan_number = pan_number.upper()
        kyc.pan_name = pan_name
        kyc.pan_aadhaar_linked = data.get('aadhaar_linked', False)
        kyc.pan_verified = True
        kyc.pan_verified_at = timezone.now()
        kyc.pan_api_response = data
        kyc.status = 'under_review'
        kyc.save()
        
        logger.info(f"✅ PAN verified and validated for user: {user.username} (Name match: {name_validation['score']:.2%})")
        
        # Warning if PAN-Aadhaar not linked
        warning = None
        if not data.get('aadhaar_linked'):
            warning = "Your PAN is not linked with Aadhaar. Please link them for better compliance."
        
        return {
            'success': True,
            'data': data,
            'kyc_updated': True,
            'validation': {
                'name_match': name_validation
            },
            'warning': warning
        }



# ========================================
# BANK VERIFICATION SERIALIZER
# ========================================

class BankVerifySerializer(serializers.Serializer):
    """Verify bank account details"""
    id_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Bank account number (for Surepass API)"
    )
    ifsc = serializers.CharField(
        max_length=11,
        min_length=11,
        required=False,
        allow_blank=True,
        help_text="11-character IFSC code (for Surepass API)"
    )
    ifsc_details = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Get bank details from IFSC"
    )
    
    def validate_id_number(self, value):
        """Validate account number (id_number field)"""
        if value and not value.isdigit():
            raise serializers.ValidationError("Account number must contain only digits")
        return value
    
    def validate_ifsc(self, value):
        """Validate IFSC format: AAAA0999999"""
        if not value:
            return value
            
        import re
        value = value.upper()
        
        ifsc_pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
        if not re.match(ifsc_pattern, value):
            raise serializers.ValidationError(
                "Invalid IFSC format. Must be: 4 letters, 0, 6 alphanumeric (e.g., HDFC0001234)"
            )
        return value
    
    def validate(self, data):
        """Validate that both fields are provided together or both skipped"""
        id_number = data.get('id_number', '')
        ifsc = data.get('ifsc', '')
        
        # If one is provided, both must be provided
        if (id_number and not ifsc) or (ifsc and not id_number):
            raise serializers.ValidationError(
                "Both account number and IFSC code are required for bank verification"
            )
        
        return data
    
    def save(self):
        """Verify bank account and validate against Aadhaar"""
        from .utils import fuzzy_name_match  # keep if you still use later

        id_number = self.validated_data.get('id_number', '')
        ifsc = self.validated_data.get('ifsc', '')

        # If no data provided, skip bank verification
        if not id_number or not ifsc:
            return {
                'success': True,
                'message': 'Bank verification skipped',
                'data': {},
                'kyc_updated': False
            }

        user = self.context.get('request').user

        # Step 1: Check if Aadhaar is verified
        try:
            kyc = KYC.objects.get(user=user)
            if not kyc.aadhaar_verified:
                raise serializers.ValidationError(
                    "Please verify your Aadhaar before adding bank account"
                )
            aadhaar_name = kyc.aadhaar_name
        except KYC.DoesNotExist:
            raise serializers.ValidationError(
                "Please complete Aadhaar verification first"
            )

        # ✅ TEST MODE FOR BANK ONLY – NO SUREPASS CALL, NO NAME MISMATCH
        if getattr(settings, "SUREPASS_BANK_TEST_MODE", False):
            masked_acc = id_number[-4:].rjust(len(id_number), '*')
            account_holder = aadhaar_name or user.get_full_name() or user.username

            kyc.account_number = id_number
            kyc.ifsc_code = ifsc
            kyc.account_holder_name = account_holder
            kyc.bank_name = "TEST BANK (MOCK)"
            kyc.bank_verified = True
            kyc.bank_verified_at = timezone.now()
            kyc.bank_api_response = {
                "mock": True,
                "note": "Bank verification skipped in test mode"
            }
            if kyc.status == "pending":
                kyc.status = "under_review"
            kyc.save()

            return {
                "success": True,
                "message": "Bank account verified successfully (TEST MODE)",
                "data": {
                    "account_number": masked_acc,
                    "ifsc": ifsc,
                    "account_holder_name": account_holder,
                    "bank_name": kyc.bank_name,
                    "verified": True,
                },
                "kyc_updated": True,
                "validation": {
                    "name_match": {
                        "match": True,
                        "score": 1.0,
                        "reason": "Test mode - name check skipped",
                    }
                },
            }

        # =========================
        # NORMAL LIVE FLOW (SUREPASS)
        # =========================
        kyc_service = SurepassKYC()
        result = kyc_service.verify_bank_account(id_number, ifsc)

        if not result["success"]:
            raise serializers.ValidationError(result.get("error", "Bank verification failed"))

        bank_data = result.get("data", {})
        bank_name = bank_data.get("name_at_bank", "")

        # Step 3: Validate bank name against Aadhaar name
        name_validation = fuzzy_name_match(aadhaar_name, bank_name, threshold=0.70)

        if not name_validation["match"]:
            error_msg = (
                f"Bank account name mismatch: Account holder name '{bank_name}' doesn't match "
                f"your Aadhaar name '{aadhaar_name}'. Please use a bank account in your name."
            )
            logger.error(f"❌ {error_msg} (Score: {name_validation['score']:.2%})")

            kyc.validation_errors["bank_name_mismatch"] = {
                "aadhaar_name": aadhaar_name,
                "bank_name": bank_name,
                "score": name_validation["score"],
                "reason": name_validation["reason"],
            }
            kyc.name_validation_status = "needs_review"
            kyc.save()

            raise serializers.ValidationError(error_msg)

        # Step 4: Validation PASSED - Save bank details
        kyc.account_number = id_number
        kyc.ifsc_code = ifsc
        kyc.account_holder_name = bank_name
        kyc.bank_name = bank_data.get("bank_name")
        kyc.bank_verified = True
        kyc.bank_verified_at = timezone.now()
        kyc.bank_api_response = bank_data

        if kyc.status == "pending":
            kyc.status = "under_review"

        kyc.save()

        logger.info(
            f"✅ Bank account verified and validated for user: {user.username} "
            f"(Name match: {name_validation['score']:.2%})"
        )

        return {
            "success": True,
            "message": "Bank account verified successfully",
            "data": {
                "account_number": id_number[-4:].rjust(len(id_number), "*"),
                "ifsc": ifsc,
                "account_holder_name": bank_name,
                "bank_name": kyc.bank_name,
                "verified": True,
            },
            "kyc_updated": True,
            "validation": {
                "name_match": name_validation,
            },
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