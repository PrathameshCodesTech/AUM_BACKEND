# commissions/admin_views.py
"""
Commission Admin Views
APIs for admin commission management
"""
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.db.models import Q, Sum, Count
from accounts.permissions import IsAdmin
from .models import Commission, CommissionPayout
from .serializers import CommissionSerializer, CommissionSummarySerializer
from .services.commission_service import CommissionService
import logging

logger = logging.getLogger(__name__)


# ========================================
# COMMISSION LIST & STATS
# ========================================

class AdminCommissionListView(APIView):
    """
    GET /api/admin/commissions/
    
    List all commissions with filters
    Query params:
    - status: pending/approved/paid/cancelled
    - cp_code: Filter by CP code
    - search: Search by CP name, code, or investment ID
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        queryset = Commission.objects.select_related(
            'cp', 'cp__user', 'investment', 'investment__customer', 'investment__property'
        ).order_by('-created_at')
        
        # Filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        cp_code = request.query_params.get('cp_code')
        if cp_code:
            queryset = queryset.filter(cp__cp_code__icontains=cp_code)
        
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(cp__cp_code__icontains=search) |
                Q(cp__user__username__icontains=search) |
                Q(cp__user__email__icontains=search) |
                Q(investment__investment_id__icontains=search)
            )
        
        serializer = CommissionSerializer(queryset, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class AdminCommissionStatsView(APIView):
    """
    GET /api/admin/commissions/stats/
    
    Get commission statistics
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        stats = Commission.objects.aggregate(
            total_commissions=Count('id'),
            total_pending=Sum('net_amount', filter=Q(status='pending')),
            total_approved=Sum('net_amount', filter=Q(status='approved')),
            total_paid=Sum('net_amount', filter=Q(status='paid')),
            total_cancelled=Sum('net_amount', filter=Q(status='cancelled')),
            
            count_pending=Count('id', filter=Q(status='pending')),
            count_approved=Count('id', filter=Q(status='approved')),
            count_paid=Count('id', filter=Q(status='paid')),
            count_cancelled=Count('id', filter=Q(status='cancelled')),
        )
        
        return Response({
            'success': True,
            'data': {
                'total_commissions': stats['total_commissions'],
                'pending': {
                    'count': stats['count_pending'],
                    'amount': str(stats['total_pending'] or 0)
                },
                'approved': {
                    'count': stats['count_approved'],
                    'amount': str(stats['total_approved'] or 0)
                },
                'paid': {
                    'count': stats['count_paid'],
                    'amount': str(stats['total_paid'] or 0)
                },
                'cancelled': {
                    'count': stats['count_cancelled'],
                    'amount': str(stats['total_cancelled'] or 0)
                }
            }
        }, status=status.HTTP_200_OK)


# ========================================
# COMMISSION DETAIL
# ========================================

class AdminCommissionDetailView(APIView):
    """
    GET /api/admin/commissions/{commission_id}/
    
    Get detailed commission information
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, commission_id):
        try:
            commission = Commission.objects.select_related(
                'cp', 'cp__user', 'investment', 'investment__customer', 
                'investment__property', 'approved_by', 'paid_by'
            ).get(id=commission_id)
            
            serializer = CommissionSerializer(commission, context={'request': request})
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Commission.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Commission not found'
            }, status=status.HTTP_404_NOT_FOUND)


# ========================================
# COMMISSION ACTIONS
# ========================================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def approve_commission(request, commission_id):
    """
    POST /api/admin/commissions/{commission_id}/approve/
    
    Manually approve commission
    """
    try:
        commission = Commission.objects.get(id=commission_id)
    except Commission.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Commission not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if commission.status != 'pending':
        return Response(
            {'success': False, 'message': f'Commission is already {commission.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        CommissionService.approve_commission(commission, request.user)
        
        return Response({
            'success': True,
            'message': f'Commission {commission.commission_id} approved',
            'data': CommissionSerializer(commission).data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error approving commission: {str(e)}")
        return Response(
            {'success': False, 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def process_payout(request, commission_id):
    """
    POST /api/admin/commissions/{commission_id}/payout/
    
    Process commission payout (mark as paid)
    
    Body: {"payment_reference": "TXN123456"}
    """
    try:
        commission = Commission.objects.get(id=commission_id)
    except Commission.DoesNotExist:
        return Response(
            {'success': False, 'message': 'Commission not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if commission.status != 'approved':
        return Response(
            {'success': False, 'message': 'Commission must be approved before payout'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    payment_reference = request.data.get('payment_reference', '')
    
    try:
        CommissionService.process_payout(
            commission,
            request.user,
            payment_reference
        )
        
        return Response({
            'success': True,
            'message': f'Commission {commission.commission_id} marked as paid',
            'data': {
                'commission_id': commission.commission_id,
                'net_amount': str(commission.net_amount),
                'paid_at': commission.paid_at,
                'payment_reference': payment_reference
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error processing payout: {str(e)}")
        return Response(
            {'success': False, 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def bulk_payout(request):
    """
    POST /api/admin/commissions/bulk-payout/
    
    Process bulk payout for multiple commissions
    
    Body: {
        "commission_ids": [1, 2, 3],
        "payment_reference": "BATCH-123"
    }
    """
    commission_ids = request.data.get('commission_ids', [])
    payment_reference = request.data.get('payment_reference', '')
    
    if not commission_ids:
        return Response(
            {'success': False, 'message': 'No commission IDs provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        commissions = Commission.objects.filter(
            id__in=commission_ids,
            status='approved'
        )
        
        if commissions.count() != len(commission_ids):
            return Response(
                {'success': False, 'message': 'Some commissions not found or not approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        processed = []
        total_amount = 0
        
        for commission in commissions:
            CommissionService.process_payout(
                commission,
                request.user,
                payment_reference
            )
            processed.append({
                'commission_id': commission.commission_id,
                'cp_code': commission.cp.cp_code,
                'amount': str(commission.net_amount)
            })
            total_amount += commission.net_amount
        
        return Response({
            'success': True,
            'message': f'{len(processed)} commissions paid',
            'data': {
                'processed': processed,
                'total_amount': str(total_amount),
                'payment_reference': payment_reference
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Error processing bulk payout: {str(e)}")
        return Response(
            {'success': False, 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ========================================
# COMMISSIONS BY CP
# ========================================

class AdminCommissionsByCPView(APIView):
    """
    GET /api/admin/commissions/by-cp/{cp_id}/
    
    Get all commissions for a specific CP with summary
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, cp_id):
        try:
            from partners.models import ChannelPartner
            
            cp = ChannelPartner.objects.select_related('user').get(id=cp_id)
            
            # Get commissions
            # commissions = CommissionService.get_cp_commissions(cp)
             # Get filter if provided
            
            
            # Get commissions
            commissions = Commission.objects.filter(
                cp=cp
            ).select_related(
                'investment',
                'investment__customer',
                'investment__property',
                'commission_rule',
                'approved_by',
                'paid_by'
            ).order_by('-created_at')
            
            # Apply status filter if provided
            status_filter = request.query_params.get('status')
            if status_filter:
                commissions = commissions.filter(status=status_filter)
            
            # Get summary
            summary = CommissionService.get_cp_earnings_summary(cp)
            
            serializer = CommissionSerializer(commissions, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'cp': {
                    'id': cp.id,
                    'cp_code': cp.cp_code,
                    'name': cp.user.get_full_name(),
                    'email': cp.user.email,
                    'phone': cp.user.phone,
                },
                'summary': {
                    'total_pending': str(summary['total_pending']),
                    'total_approved': str(summary['total_approved']),
                    'total_paid': str(summary['total_paid']),
                    'total_earned': str(summary['total_earned']),
                },
                'commissions': serializer.data
            }, status=status.HTTP_200_OK)
            
        except ChannelPartner.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Channel Partner not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"❌ Error fetching CP commissions: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to fetch commissions'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
