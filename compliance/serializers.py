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
        """Verify PAN using Surepass PAN Advanced V3.

        PAN is an independent verification flow — it does not require Aadhaar
        to be submitted first. Returned provider data is stored and submitted
        for admin review/approval, same as the Aadhaar review-lock model.
        """
        from .services.kyc_service import SurepassKYC

        pan_number = self.validated_data['pan_number']

        # Get or create KYC record — PAN can be verified at any time independently.
        kyc, _ = KYC.objects.get_or_create(user=user)

        # Use best available identity data as optional input to Surepass for
        # improved server-side match quality. Aadhaar data is preferred when
        # present; falls back to user profile fields. This is NOT a hard gate —
        # PAN verification proceeds regardless of Aadhaar status.
        signer_name = kyc.aadhaar_name or user.legal_full_name or user.get_full_name() or ''
        signer_dob = ''
        if kyc.aadhaar_dob:
            signer_dob = kyc.aadhaar_dob.strftime('%Y-%m-%d')
        elif user.date_of_birth:
            signer_dob = user.date_of_birth.strftime('%Y-%m-%d')

        # Call Surepass PAN Advanced V3
        kyc_service = SurepassKYC()
        result = kyc_service.verify_pan(pan_number, name=signer_name, dob=signer_dob)

        if not result.get('success'):
            raise serializers.ValidationError(result.get('error', 'PAN verification failed'))

        data = result.get('data', {})

        # Save provider-returned PAN data — pan-adv-v3 field names
        kyc.pan_number = pan_number.upper()
        kyc.pan_name = data.get('name', '')
        pan_dob_str = data.get('dob', '')
        if pan_dob_str:
            try:
                from datetime import datetime as _dt
                kyc.pan_dob = _dt.strptime(pan_dob_str, '%Y-%m-%d').date()
            except Exception:
                pass

        # pan_aadhaar_linked is stored as optional informational metadata only.
        # It is NOT used as a business gate, compliance blocker, or approval condition.
        seeding = data.get('aadhaar_seeding_status', '')
        kyc.pan_aadhaar_linked = bool(seeding) and seeding.upper() not in ('NOT_LINKED', 'NA', 'N', 'NO', '')

        # pan_verified is NOT set here — it is set only when admin runs approve_lock.
        # This mirrors the Aadhaar model: submission ≠ verification; admin approval = verification.
        kyc.pan_api_response = data
        kyc.status = 'under_review'
        kyc.save()

        logger.info(
            f"✅ PAN submitted for review: user={user.username} "
            f"(name_status={data.get('name_status')}, dob_status={data.get('dob_status')})"
        )

        return {
            'success': True,
            'data': data,
            'kyc_updated': True,
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

    # App review / lock state  (workflow, not provider data)
    aadhaar_locked = serializers.BooleanField(read_only=True)
    aadhaar_review_status = serializers.CharField(read_only=True)
    pan_locked = serializers.BooleanField(read_only=True)
    pan_review_status = serializers.CharField(read_only=True)

    # Identity data returned by providers
    aadhaar_name = serializers.CharField(read_only=True)
    aadhaar_dob = serializers.DateField(read_only=True)
    aadhaar_gender = serializers.CharField(read_only=True)
    aadhaar_address = serializers.CharField(read_only=True)
    aadhaar_number = serializers.CharField(read_only=True)  # stored as last4 only
    pan_name = serializers.CharField(read_only=True)
    pan_dob = serializers.DateField(read_only=True)
    pan_number = serializers.CharField(read_only=True)

    # PAN provider-returned fields (Surepass PAN Advanced V3 response).
    # These are distinct from pan_review_status which is the app workflow state.
    #   pan_provider_status      ← data.pan_status       e.g. "EXISTING AND VALID"
    #   pan_name_status          ← data.name_status       e.g. "MATCHING" / "NON-MATCHING"
    #   pan_dob_status           ← data.dob_status        e.g. "MATCHING" / "NON-MATCHING"
    #   pan_aadhaar_seeding_status ← data.aadhaar_seeding_status e.g. "Operative PAN"
    pan_provider_status        = serializers.SerializerMethodField()
    pan_name_status            = serializers.SerializerMethodField()
    pan_dob_status             = serializers.SerializerMethodField()
    pan_aadhaar_seeding_status = serializers.SerializerMethodField()

    # Validation signals (Aadhaar name/DOB match)
    name_match_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    name_validation_status = serializers.CharField(read_only=True)
    dob_validation_status = serializers.CharField(read_only=True)

    # Admin notes visible to user
    aadhaar_review_note = serializers.CharField(read_only=True)
    pan_review_note = serializers.CharField(read_only=True)

    class Meta:
        model = KYC
        fields = [
            'status',
            'aadhaar_verified',
            'aadhaar_locked',
            'aadhaar_review_status',
            'aadhaar_name',
            'aadhaar_dob',
            'aadhaar_gender',
            'aadhaar_address',
            'aadhaar_number',
            'aadhaar_review_note',
            'pan_verified',
            'pan_locked',
            'pan_review_status',
            'pan_name',
            'pan_dob',
            'pan_number',
            'pan_provider_status',
            'pan_name_status',
            'pan_dob_status',
            'pan_aadhaar_seeding_status',
            'pan_review_note',
            'bank_verified',
            'pan_aadhaar_linked',
            'is_complete',
            'rejection_reason',
            'name_match_score',
            'name_validation_status',
            'dob_validation_status',
        ]

    def get_is_complete(self, obj):
        return obj.is_complete()

    def _pan_api_data(self, obj):
        """Return the data sub-object from stored pan_api_response, or {}."""
        raw = obj.pan_api_response
        if not raw or not isinstance(raw, dict):
            return {}
        # Surepass may wrap fields under 'data' or store them flat
        inner = raw.get('data', raw)
        return inner if isinstance(inner, dict) else raw

    def get_pan_provider_status(self, obj):
        """Surepass data.pan_status — e.g. 'EXISTING AND VALID'."""
        d = self._pan_api_data(obj)
        return d.get('pan_status') or None

    def get_pan_name_status(self, obj):
        """Surepass data.name_status — 'MATCHING' or 'NON-MATCHING'."""
        d = self._pan_api_data(obj)
        return d.get('name_status') or None

    def get_pan_dob_status(self, obj):
        """Surepass data.dob_status — 'MATCHING' or 'NON-MATCHING'."""
        d = self._pan_api_data(obj)
        return d.get('dob_status') or None

    def get_pan_aadhaar_seeding_status(self, obj):
        """Surepass data.aadhaar_seeding_status — e.g. 'Operative PAN'."""
        d = self._pan_api_data(obj)
        return d.get('aadhaar_seeding_status') or None


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