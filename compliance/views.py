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
from .models import KYC
from .serializers import (

    PANVerifySerializer,
    BankVerifySerializer,
    KYCSerializer,
    KYCStatusSerializer,
    KYCApprovalSerializer,
)
from accounts.permissions import HasPermission
import logging
from .serializers import AadhaarPDFUploadSerializer

logger = logging.getLogger(__name__)


# ========================================
# AADHAAR VERIFICATION APIs
# ========================================

class AadhaarPDFUploadView(APIView):
    """
    POST /api/kyc/aadhaar/upload-pdf/
    Upload and verify eAadhaar PDF
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = AadhaarPDFUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = serializer.verify(request.user)
            
            return Response({
                'success': True,
                'message': 'Aadhaar verified successfully',
                'data': result['data'],
                'kyc_updated': result['kyc_updated']
            }, status=status.HTTP_200_OK)
            
        except serializers.ValidationError as e:
            logger.error(f"❌ Aadhaar verification error: {e.detail}")
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

class PendingKYCListView(generics.ListAPIView):
    """
    GET /api/kyc/admin/pending/
    
    List all pending KYC submissions (Admin only)
    """
    permission_classes = [IsAuthenticated, HasPermission]
    permission_required = 'compliance.view_kyc'
    serializer_class = KYCSerializer
    
    def get_queryset(self):
        return KYC.objects.filter(
            status__in=['pending', 'under_review']
        ).order_by('-created_at')


class KYCApprovalView(APIView):
    """
    POST /api/kyc/admin/{kyc_id}/approve/
    POST /api/kyc/admin/{kyc_id}/reject/
    
    Approve or reject KYC submission (Admin only)
    """
    permission_classes = [IsAuthenticated, HasPermission]
    permission_required = 'compliance.approve_kyc'
    
    def post(self, request, kyc_id):
        try:
            kyc = KYC.objects.get(id=kyc_id)
        except KYC.DoesNotExist:
            return Response({
                'success': False,
                'message': 'KYC not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = KYCApprovalSerializer(data=request.data)
        
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
            'data': KYCSerializer(kyc).data
        }, status=status.HTTP_200_OK)


class AllKYCListView(generics.ListAPIView):
    """
    GET /api/kyc/admin/all/
    
    List all KYC submissions (Admin only)
    """
    permission_classes = [IsAuthenticated, HasPermission]
    permission_required = 'compliance.view_kyc'
    serializer_class = KYCSerializer
    
    def get_queryset(self):
        queryset = KYC.objects.all().order_by('-created_at')
        
        # Optional filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset