from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from accounts.permissions import IsAdmin
from .models import Investment
from commissions.services.commission_service import CommissionService
from commissions.models import Commission
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def approve_investment(request, investment_id):
    """
    Approve investment and automatically approve associated commission
    
    POST /api/admin/investments/{investment_id}/approve/
    """
    try:
        investment = Investment.objects.select_related('customer', 'property').get(
            id=investment_id
        )
    except Investment.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Investment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if investment.status == 'approved':
        return Response(
            {'success': False, 'message': 'Investment already approved'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Update investment status
        investment.status = 'approved'
        investment.approved_by = request.user
        investment.approved_at = timezone.now()
        investment.save(update_fields=['status', 'approved_by', 'approved_at'])
        
        logger.info(f"✅ Investment {investment.investment_id} approved by {request.user.username}")
        
        # Auto-approve commission if exists
        commission = Commission.objects.filter(
            investment=investment,
            status='pending'
        ).first()
        
        if commission:
            CommissionService.approve_commission(commission, request.user)
            logger.info(f"✅ Commission {commission.commission_id} auto-approved")
        
        return Response({
            'success': True,
            'message': f'Investment {investment.investment_id} approved successfully',
            'data': {
                'investment_id': investment.investment_id,
                'status': investment.status,
                'commission_approved': commission is not None
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error approving investment: {str(e)}")
        return Response(
            {'success': False, 'message': f'Approval failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def reject_investment(request, investment_id):
    """
    Reject investment and cancel associated commission
    
    POST /api/admin/investments/{investment_id}/reject/
    Body: {"reason": "rejection reason"}
    """
    try:
        investment = Investment.objects.get(id=investment_id)
    except Investment.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Investment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    rejection_reason = request.data.get('reason', '')
    
    if not rejection_reason:
        return Response(
            {'success': False, 'message': 'Rejection reason is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Update investment
        investment.status = 'rejected'
        investment.rejection_reason = rejection_reason
        investment.save(update_fields=['status', 'rejection_reason'])
        
        # Refund to wallet
        from .services.wallet_service import WalletService
        WalletService.add_funds(
            investment.customer,
            investment.amount,
            f"Refund for rejected investment {investment.investment_id}"
        )
        
        # Cancel commission
        commission = Commission.objects.filter(
            investment=investment,
            status='pending'
        ).first()
        
        if commission:
            commission.status = 'cancelled'
            commission.save(update_fields=['status'])
            logger.info(f"✅ Commission {commission.commission_id} cancelled")
        
        logger.info(f"✅ Investment {investment.investment_id} rejected by {request.user.username}")
        
        return Response({
            'success': True,
            'message': f'Investment {investment.investment_id} rejected and refunded'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error rejecting investment: {str(e)}")
        return Response(
            {'success': False, 'message': f'Rejection failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )