"""
KYC Views
API endpoints for KYC verification
"""
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from .models import KYC, AadhaarSession
from .serializers import (
    PANVerifySerializer,
    BankVerifySerializer,
    KYCSerializer,
    KYCStatusSerializer,
)
from accounts.permissions import IsAdmin
import logging
from .serializers import AadhaarPDFUploadSerializer
from rest_framework import serializers

logger = logging.getLogger(__name__)


# ========================================
# AADHAAR VERIFICATION APIs
# ========================================

class AadhaarDigiLockerInitView(APIView):
    """
    POST /api/kyc/aadhaar/digilocker/init/
    Initialize a DigiLocker Aadhaar session and return the redirect URL.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .services.kyc_service import SurepassKYC
        user = request.user

        # Prevent re-init if already verified
        try:
            kyc = KYC.objects.get(user=user)
            if kyc.aadhaar_verified:
                return Response({
                    'success': False,
                    'message': 'Aadhaar already verified.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except KYC.DoesNotExist:
            pass

        # Abandon any open sessions for this user before starting a new one.
        # This ensures one active attempt at a time and keeps admin/backend clean.
        abandoned = AadhaarSession.objects.filter(
            user=user,
            status__in=['initiated', 'needs_review']
        ).update(status='abandoned')
        if abandoned:
            logger.info("DigiLocker init: abandoned %d prior open session(s) for user %s", abandoned, user.id)

        try:
            result = SurepassKYC().digilocker_initialize()
        except Exception as e:
            logger.error(f"DigiLocker init error for user {user.id}: {e}")
            return Response({
                'success': False,
                'message': 'Failed to initialize DigiLocker session.'
            }, status=status.HTTP_502_BAD_GATEWAY)

        data = result.get('data', {})
        client_id = data.get('client_id') or result.get('client_id')
        # Surepass Digiboost: 'gateway' in test mode, 'url' in production
        redirect_url = data.get('gateway') or data.get('url') or result.get('url')
        # Token is used by Surepass Digiboost SDK for embedded / popup gateway auth
        token = data.get('token') or result.get('token', '')

        if not client_id or not redirect_url:
            logger.error(f"DigiLocker init unexpected response: {result}")
            return Response({
                'success': False,
                'message': 'Unexpected response from DigiLocker API.'
            }, status=status.HTTP_502_BAD_GATEWAY)

        AadhaarSession.objects.create(
            user=user,
            client_id=client_id,
            status='initiated',
            raw_init_payload=result,
        )

        return Response({
            'success': True,
            'client_id': client_id,
            'redirect_url': redirect_url,
            'token': token,
        }, status=status.HTTP_200_OK)


class AadhaarDigiLockerStatusView(APIView):
    """
    GET /api/kyc/aadhaar/digilocker/status/?client_id=<id>
    Poll the status of a DigiLocker session.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        client_id = request.query_params.get('client_id')
        if not client_id:
            return Response({
                'success': False,
                'message': 'client_id is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = AadhaarSession.objects.get(client_id=client_id, user=request.user)
        except AadhaarSession.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Session not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': True,
            'client_id': client_id,
            'status': session.status,
        }, status=status.HTTP_200_OK)


class AadhaarDigiLockerFinalizeView(APIView):
    """
    POST /api/kyc/aadhaar/digilocker/finalize/
    Download the Aadhaar XML from DigiLocker, extract data, and update KYC.
    Body: { "client_id": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .services.kyc_service import SurepassKYC

        user = request.user
        client_id = request.data.get('client_id')
        if not client_id:
            return Response({
                'success': False,
                'message': 'client_id is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = AadhaarSession.objects.get(client_id=client_id, user=user)
        except AadhaarSession.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Session not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'completed':
            return Response({
                'success': False,
                'message': 'This session has already been finalized.',
                'retry_required': True,
                'session_reusable': False,
            }, status=status.HTTP_400_BAD_REQUEST)

        if session.status in ('failed', 'expired', 'abandoned', 'needs_review'):
            return Response({
                'success': False,
                'message': 'This Aadhaar session is no longer valid. Please start a fresh DigiLocker attempt.',
                'retry_required': True,
                'session_reusable': False,
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = SurepassKYC().digilocker_download_aadhaar(client_id)
        except Exception as e:
            logger.error(f"DigiLocker download error for user {user.id}: {e}")
            session.status = 'failed'
            session.save(update_fields=['status'])
            return Response({
                'success': False,
                'message': 'Failed to download Aadhaar data from DigiLocker.',
                'retry_required': True,
                'session_reusable': False,
            }, status=status.HTTP_502_BAD_GATEWAY)

        data = result.get('data', {})
        if not data:
            session.status = 'failed'
            session.raw_result_payload = result
            session.save(update_fields=['status', 'raw_result_payload'])
            return Response({
                'success': False,
                'message': 'No Aadhaar data returned. User may not have completed DigiLocker authorization.',
                'retry_required': True,
                'session_reusable': False,
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── Step 1: Require legal profile identity before any comparison ───────
        profile_name = (user.legal_full_name or '').strip()
        profile_dob  = user.date_of_birth

        if not profile_name:
            return Response({
                'success': False,
                'message': (
                    'Your legal name is not set. Please go to your profile, enter your '
                    'first and last name exactly as they appear on your Aadhaar/PAN, '
                    'then return here to verify.'
                )
            }, status=status.HTTP_400_BAD_REQUEST)

        if not profile_dob:
            return Response({
                'success': False,
                'message': (
                    'Your date of birth is not set. Please complete your profile '
                    '(date of birth as per Aadhaar/PAN) before verifying Aadhaar.'
                )
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── Step 2: Extract fields from Surepass DigiLocker response ─────────
        digilocker_metadata = data.get('digilocker_metadata', {})
        if not isinstance(digilocker_metadata, dict):
            digilocker_metadata = {}

        aadhaar_xml_data = data.get('aadhaar_xml_data', {})
        if not isinstance(aadhaar_xml_data, dict):
            aadhaar_xml_data = {}

        full_name = (
            data.get('full_name')
            or data.get('name')
            or aadhaar_xml_data.get('full_name')
            or aadhaar_xml_data.get('name')
            or digilocker_metadata.get('full_name')
            or digilocker_metadata.get('name')
            or ''
        ).strip()
        dob_raw = (
            data.get('dob')
            or data.get('date_of_birth')
            or aadhaar_xml_data.get('dob')
            or aadhaar_xml_data.get('date_of_birth')
            or digilocker_metadata.get('dob')
            or digilocker_metadata.get('date_of_birth')
            or ''
        )
        gender_raw = (
            data.get('gender')
            or data.get('sex')
            or aadhaar_xml_data.get('gender')
            or aadhaar_xml_data.get('sex')
            or digilocker_metadata.get('gender')
            or digilocker_metadata.get('sex')
            or ''
        ).upper()
        aadhaar_number_raw = (
            data.get('aadhaar_number')
            or data.get('uid')
            or aadhaar_xml_data.get('masked_aadhaar')
            or aadhaar_xml_data.get('aadhaar_number')
            or aadhaar_xml_data.get('uid')
            or aadhaar_xml_data.get('uniqueness_id')
            or ''
        )

        # Parse DOB — try ISO (YYYY-MM-DD) then DD/MM/YYYY
        aadhaar_dob_date = None
        if dob_raw:
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    from datetime import datetime
                    aadhaar_dob_date = datetime.strptime(dob_raw, fmt).date()
                    break
                except ValueError:
                    continue

        # Build address string from dict or plain string
        addr_raw = (
            data.get('address')
            or aadhaar_xml_data.get('address')
            or aadhaar_xml_data.get('full_address')
            or ''
        )
        if isinstance(addr_raw, dict):
            parts = [
                addr_raw.get('house', ''), addr_raw.get('street', ''),
                addr_raw.get('vtc', ''), addr_raw.get('dist', ''),
                addr_raw.get('state', ''),
            ]
            pincode = addr_raw.get('zip', '') or addr_raw.get('pincode', '')
            address_str = ', '.join(p for p in parts if p)
            if pincode:
                address_str += f' - {pincode}'
            aadhaar_city    = addr_raw.get('vtc', '') or addr_raw.get('dist', '')
            aadhaar_state   = addr_raw.get('state', '')
            aadhaar_pincode = pincode
        else:
            address_str = addr_raw or ''
            aadhaar_city = aadhaar_state = aadhaar_pincode = ''

        # ── Step 3: Sanitize API response before storage ──────────────────────
        # Never persist a full Aadhaar number in JSON; keep only audit fields.
        sanitized_response = {
            'full_name':    full_name,
            'dob':          dob_raw,
            'gender':       gender_raw,
            'aadhaar_last4': aadhaar_number_raw[-4:] if len(aadhaar_number_raw) >= 4 else aadhaar_number_raw,
            'address':      addr_raw if isinstance(addr_raw, dict) else {'full': address_str},
            'client_id':    data.get('client_id', ''),
            'reference_id': data.get('reference_id', ''),
            'source': {
                'digilocker_metadata': {
                    'name': digilocker_metadata.get('name', ''),
                    'dob': digilocker_metadata.get('dob', ''),
                    'gender': digilocker_metadata.get('gender', ''),
                },
                'aadhaar_xml_data': {
                    'full_name': aadhaar_xml_data.get('full_name', ''),
                    'dob': aadhaar_xml_data.get('dob', ''),
                    'gender': aadhaar_xml_data.get('gender', ''),
                    'masked_aadhaar': aadhaar_xml_data.get('masked_aadhaar', ''),
                },
            },
        }

        # ── Step 4: Identity validation ───────────────────────────────────────
        from .utils import fuzzy_name_match, validate_dob_match

        name_validation = fuzzy_name_match(profile_name, full_name, threshold=0.75)
        # Only run DOB comparison when Surepass returned a parseable date.
        # If dob_raw is missing or could not be parsed, dob_validation stays None —
        # treated as "provider did not return DOB" which must NOT silently pass.
        dob_validation = validate_dob_match(profile_dob, dob_raw) if (profile_dob and dob_raw and aadhaar_dob_date) else None

        mismatch_errors = {}
        name_ok = name_validation['match']
        # DOB is ok only if the provider returned a parseable date AND it matched.
        # Missing DOB from provider (dob_validation is None) is treated as unverifiable,
        # not as a pass — we flag it for admin review below.
        dob_ok = dob_validation['match'] if dob_validation is not None else None  # None = no DOB from provider

        if not name_ok:
            mismatch_errors['name_mismatch'] = {
                'profile_name':  profile_name,
                'aadhaar_name':  full_name,
                'score':         round(name_validation['score'], 4),
                'reason':        name_validation.get('reason', ''),
            }
        if dob_ok is False:
            mismatch_errors['dob_mismatch'] = {
                'profile_dob': str(profile_dob),
                'aadhaar_dob': dob_raw,
                'reason':      dob_validation.get('reason', ''),
            }
        if dob_ok is None:
            mismatch_errors['dob_not_returned'] = {
                'reason': 'Surepass did not return a usable date of birth for this Aadhaar.',
            }

        # ── Step 5: Persist KYC regardless; only set verified on full match ───
        kyc, _ = KYC.objects.get_or_create(user=user)

        # Always write returned data and validation state
        kyc.aadhaar_name       = full_name
        kyc.aadhaar_dob        = aadhaar_dob_date
        kyc.aadhaar_gender     = gender_raw
        kyc.aadhaar_number     = aadhaar_number_raw[-4:] if len(aadhaar_number_raw) >= 4 else aadhaar_number_raw
        kyc.aadhaar_address    = address_str
        kyc.aadhaar_api_response = sanitized_response
        kyc.name_match_score   = round(name_validation['score'] * 100, 2)
        kyc.validation_errors  = mismatch_errors

        if aadhaar_city  and not kyc.city:    kyc.city    = aadhaar_city
        if aadhaar_state and not kyc.state:   kyc.state   = aadhaar_state
        if aadhaar_pincode and not kyc.pincode: kyc.pincode = aadhaar_pincode

        dob_provider_missing = 'dob_not_returned' in mismatch_errors
        hard_mismatch = 'name_mismatch' in mismatch_errors or 'dob_mismatch' in mismatch_errors

        if hard_mismatch:
            # Definitive identity mismatch — reject outright, do NOT mark verified
            kyc.name_validation_status = 'failed' if not name_ok else 'passed'
            kyc.dob_validation_status  = 'failed' if dob_ok is False else 'passed'
            kyc.save()

            session.status = 'failed'
            session.raw_result_payload = result
            session.save(update_fields=['status', 'raw_result_payload'])

            reasons = []
            if 'name_mismatch' in mismatch_errors:
                m = mismatch_errors['name_mismatch']
                reasons.append(
                    f"Name mismatch: your profile name '{profile_name}' does not match "
                    f"Aadhaar name '{full_name}' (score {m['score']:.0%}). "
                    "Please update your profile legal name to exactly match your Aadhaar."
                )
            if 'dob_mismatch' in mismatch_errors:
                reasons.append(
                    "Date of birth mismatch: your profile DOB does not match the DOB on your Aadhaar."
                )

            return Response({
                'success': False,
                'message': ' '.join(reasons),
                'mismatch': mismatch_errors,
                'retry_required': True,
                'session_reusable': False,
            }, status=status.HTTP_400_BAD_REQUEST)

        if dob_provider_missing:
            # Name matched but provider returned no DOB — cannot auto-verify.
            # Save what we have and route to admin review; do NOT set aadhaar_verified.
            kyc.name_validation_status = 'passed'
            kyc.dob_validation_status  = 'needs_review'
            kyc.status = 'under_review'
            kyc.save()

            session.status = 'needs_review'
            session.raw_result_payload = result
            session.save(update_fields=['status', 'raw_result_payload'])

            logger.warning(
                "DigiLocker finalize for user %s: name matched but Surepass returned no DOB. "
                "Routed to admin review without marking aadhaar_verified.",
                user.id,
            )
            return Response({
                'success': False,
                'needs_review': True,
                'message': (
                    'Your name was verified but the Aadhaar provider did not return your date of birth. '
                    'Your KYC has been sent for admin review. You will be notified once it is confirmed.'
                ),
                'retry_required': True,
                'session_reusable': False,
            }, status=status.HTTP_202_ACCEPTED)

        # Full match (name ✓ and DOB ✓) — mark verified
        kyc.aadhaar_verified    = True
        kyc.aadhaar_verified_at = timezone.now()
        kyc.name_validation_status = 'passed'
        kyc.dob_validation_status  = 'passed'
        kyc.status = 'under_review'
        kyc.save()

        # Mark session as completed
        session.status = 'completed'
        session.raw_result_payload = result
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'raw_result_payload', 'completed_at'])

        return Response({
            'success': True,
            'message': 'Aadhaar verified successfully via DigiLocker.',
            'data': {
                'full_name':     full_name,
                'dob':           dob_raw,
                'gender':        gender_raw,
                'aadhaar_last4': kyc.aadhaar_number,
            },
            'kyc_updated': True,
        }, status=status.HTTP_200_OK)


class AadhaarPDFUploadView(APIView):
    """
    POST /api/kyc/aadhaar/upload-pdf/
    Upload and verify eAadhaar PDF
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        from django.utils import timezone
        from datetime import timedelta
        from compliance.models import KYC
        
        # Check retry limits
        try:
            kyc = KYC.objects.get(user=request.user)
            
            # Check if user has exceeded retry limit
            if kyc.aadhaar_retry_count >= 5:
                # Check if 10 minutes have passed since last retry
                if kyc.aadhaar_last_retry_at:
                    time_since_retry = timezone.now() - kyc.aadhaar_last_retry_at
                    if time_since_retry < timedelta(minutes=10):
                        remaining_time = 10 - int(time_since_retry.total_seconds() / 60)
                        return Response({
                            'success': False,
                            'error': 'retry_limit_exceeded',
                            'message': f'Maximum retry limit reached. Please try again after {remaining_time} minutes.',
                            'retry_after': remaining_time
                        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                    else:
                        # Reset retry count after 10 minutes
                        kyc.aadhaar_retry_count = 0
                        kyc.save()
        except KYC.DoesNotExist:
            pass  # KYC will be created in serializer
        
        serializer = AadhaarPDFUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = serializer.verify(request.user)
            
            # Reset retry count on success
            kyc = KYC.objects.get(user=request.user)
            kyc.aadhaar_retry_count = 0
            kyc.aadhaar_last_retry_at = None
            kyc.save()
            
            return Response({
                'success': True,
                'message': 'Aadhaar verified successfully',
                'data': result['data'],
                'kyc_updated': result['kyc_updated']
            }, status=status.HTTP_200_OK)
            
        except serializers.ValidationError as e:
            # Increment retry count on failure
            try:
                kyc = KYC.objects.get(user=request.user)
                kyc.aadhaar_retry_count += 1
                kyc.aadhaar_last_retry_at = timezone.now()
                kyc.save()
                
                retries_left = 5 - kyc.aadhaar_retry_count
                
                logger.error(f"❌ Aadhaar verification error: {e.detail}")
                return Response({
                    'success': False,
                    'message': str(e.detail),
                    'retries_left': retries_left if retries_left > 0 else 0
                }, status=status.HTTP_400_BAD_REQUEST)
            except KYC.DoesNotExist:
                pass
                
            return Response({
                'success': False,
                'message': str(e.detail)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# PAN VERIFICATION APIs
# ========================================
class PANVerifyView(APIView):
    """
    POST /api/kyc/pan/verify/
    Verify PAN card details
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PANVerifySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = serializer.verify(request.user)  # ← NEW METHOD
            
            return Response({
                'success': True,
                'message': 'PAN verified successfully',
                'data': result['data'],
                'kyc_updated': result['kyc_updated']
            }, status=status.HTTP_200_OK)
            
        except serializers.ValidationError as e:
            logger.error(f"❌ PAN verification error: {e.detail}")
            return Response({
                'success': False,
                'message': str(e.detail)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# ========================================
# BANK VERIFICATION API
# ========================================

class BankVerifyView(APIView):
    """
    POST /api/kyc/bank/verify/
    
    Verify bank account details
    Stores verified bank data in KYC model
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = BankVerifySerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = serializer.save()
            
            return Response({
                'success': True,
                'data': result['data'],
                'message': result['message'],
                'kyc_updated': result.get('kyc_updated', False)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Bank verification error: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# KYC MANAGEMENT APIs
# ========================================

class MyKYCView(APIView):
    """
    GET /api/kyc/me/
    
    Get current user's KYC details
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            kyc = KYC.objects.get(user=request.user)
            serializer = KYCSerializer(kyc)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except KYC.DoesNotExist:
            return Response({
                'success': False,
                'message': 'KYC not found. Please complete KYC verification.'
            }, status=status.HTTP_404_NOT_FOUND)


class MyKYCStatusView(APIView):
    """
    GET /api/kyc/status/
    
    Get current user's KYC status
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            kyc = KYC.objects.get(user=request.user)
            serializer = KYCStatusSerializer(kyc)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except KYC.DoesNotExist:
            return Response({
                'success': True,
                'data': {
                    'status': 'pending',
                    'aadhaar_verified': False,
                    'pan_verified': False,
                    'bank_verified': False,
                    'pan_aadhaar_linked': False,
                    'is_complete': False,
                    'rejection_reason': None
                }
            }, status=status.HTTP_200_OK)


# ========================================
# ADMIN APIs
# ========================================
# ========================================
# ADMIN APIs
# ========================================

from .admin_serializers import (
    AdminKYCListSerializer,
    AdminKYCDetailSerializer,
    AdminKYCActionSerializer
)

class PendingKYCListView(generics.ListAPIView):
    """
    GET /api/admin/kyc/pending/
    List all pending KYC submissions (Admin only)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = AdminKYCListSerializer
    
    def get_queryset(self):
        return KYC.objects.filter(
            status__in=['pending', 'under_review']
        ).select_related('user').order_by('-created_at')


class AllKYCListView(generics.ListAPIView):
    """
    GET /api/admin/kyc/all/
    List all KYC submissions (Admin only)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = AdminKYCListSerializer
    
    def get_queryset(self):
        queryset = KYC.objects.all().select_related('user').order_by('-created_at')
        
        # Optional filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class KYCDetailView(APIView):
    """
    GET /api/admin/kyc/{kyc_id}/
    Get detailed KYC info (Admin only)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, kyc_id):
        try:
            kyc = KYC.objects.select_related('user', 'verified_by').get(id=kyc_id)
            serializer = AdminKYCDetailSerializer(kyc)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except KYC.DoesNotExist:
            return Response({
                'success': False,
                'message': 'KYC not found'
            }, status=status.HTTP_404_NOT_FOUND)


class KYCApprovalView(APIView):
    """
    POST /api/admin/kyc/{kyc_id}/action/
    Approve or reject KYC submission (Admin only)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, kyc_id):
        try:
            kyc = KYC.objects.get(id=kyc_id)
        except KYC.DoesNotExist:
            return Response({
                'success': False,
                'message': 'KYC not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminKYCActionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        action = serializer.validated_data['action']
        
        if action == 'approve':
            kyc.status = 'verified'
            kyc.verified_at = timezone.now()
            kyc.verified_by = request.user
            kyc.rejection_reason = None
            message = 'KYC approved successfully'
            
        else:  # reject
            kyc.status = 'rejected'
            kyc.rejection_reason = serializer.validated_data.get('rejection_reason')
            kyc.verified_by = request.user
            message = 'KYC rejected'
        
        kyc.save()
        
        logger.info(f"✅ KYC {action}d for user {kyc.user.username} by {request.user.username}")
        
        return Response({
            'success': True,
            'message': message,
            'data': AdminKYCDetailSerializer(kyc).data
        }, status=status.HTTP_200_OK)    




