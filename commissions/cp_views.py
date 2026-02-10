# commissions/cp_views.py
"""
CP Commission Views - For Channel Partners to view their commissions
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.db.models import Q, Sum, Count
from .models import Commission
from .serializers import CommissionSerializer
from .services.commission_service import CommissionService
from commissions.services.commission_service import CommissionService
import logging

logger = logging.getLogger(__name__)


class CPCommissionListView(APIView):
    """
    GET /api/cp/commissions/
    List all commissions for logged-in CP
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get CP from logged-in user
            cp = request.user.cp_profile
            
            # Get commissions
            queryset = Commission.objects.filter(
                cp=cp
            ).select_related(
                'investment',
                'investment__customer',
                'investment__property',
                'commission_rule'
            ).order_by('-created_at')
            
            # Apply status filter
            status_filter = request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            serializer = CommissionSerializer(queryset, many=True, context={'request': request})
            
            return Response({
                'success': True,
                'count': queryset.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
            
        except AttributeError:
            return Response({
                'success': False,
                'error': 'User is not a Channel Partner'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"❌ Error fetching CP commissions: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to fetch commissions'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CPCommissionStatsView(APIView):
    """
    GET /api/cp/commissions/stats/
    Get commission statistics for logged-in CP
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            cp = request.user.cp_profile
            
            # Get earnings summary using existing service
            summary = CommissionService.get_cp_earnings_summary(cp)
            
            # Get count by status
            stats = Commission.objects.filter(cp=cp).aggregate(
                total_count=Count('id'),
                pending_count=Count('id', filter=Q(status='pending')),
                approved_count=Count('id', filter=Q(status='approved')),
                paid_count=Count('id', filter=Q(status='paid')),
            )
            
            return Response({
                'success': True,
                'data': {
                    'total_earned': str(summary['total_earned']),
                    'pending': str(summary['total_pending']),
                    'approved': str(summary['total_approved']),
                    'paid': str(summary['total_paid']),
                    'total_count': stats['total_count'],
                    'pending_count': stats['pending_count'],
                    'approved_count': stats['approved_count'],
                    'paid_count': stats['paid_count'],
                }
            }, status=status.HTTP_200_OK)
            
        except AttributeError:
            return Response({
                'success': False,
                'error': 'User is not a Channel Partner'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"❌ Error fetching CP commission stats: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to fetch commission statistics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cp_commission_detail(request, commission_id):
    """
    GET /api/cp/commissions/{commission_id}/
    Get detailed commission information
    """
    try:
        cp = request.user.cp_profile
        
        commission = Commission.objects.select_related(
            'investment',
            'investment__customer',
            'investment__property',
            'commission_rule',
            'approved_by',
            'paid_by'
        ).get(id=commission_id, cp=cp)
        
        serializer = CommissionSerializer(commission, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Commission.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Commission not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except AttributeError:
        return Response({
            'success': False,
            'error': 'User is not a Channel Partner'
        }, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        logger.error(f"❌ Error fetching commission detail: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to fetch commission details'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cp_dashboard_stats(request):
    """CP Dashboard Statistics"""
    try:
        cp = request.user.cp_profile
        
        # ... your existing stats code ...
        
        # Add commission stats
        commission_summary = CommissionService.get_cp_earnings_summary(cp)
        
        return Response({
            'success': True,
            'data': {
                # ... your existing data ...
                'commissions': {
                    'total_earned': str(commission_summary['total_earned']),
                    'pending': str(commission_summary['total_pending']),
                    'approved': str(commission_summary['total_approved']),
                    'paid': str(commission_summary['total_paid']),
                    'this_month': str(commission_summary.get('this_month', 0)),  # if you add this
                }
            }
        })
    except Exception as e:
        logger.error(f"Error fetching CP dashboard stats: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to fetch dashboard stats'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
