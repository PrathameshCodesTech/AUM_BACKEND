"""
Investment Admin Views
APIs for admin investment management
"""
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Sum, Count
from .models import Investment
from accounts.permissions import IsAdmin
from .admin_serializers import (
    AdminInvestmentListSerializer,
    AdminInvestmentDetailSerializer,
    AdminInvestmentActionSerializer,
    AdminInvestmentStatsSerializer,
)
import logging

logger = logging.getLogger(__name__)


# ========================================
# INVESTMENT STATISTICS
# ========================================

class AdminInvestmentStatsView(APIView):
    """
    GET /api/admin/investments/stats/
    
    Get investment statistics
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        try:
            stats = {
                'total_investments': Investment.objects.count(),
                'pending_investments': Investment.objects.filter(status='pending').count(),
                'approved_investments': Investment.objects.filter(status='approved').count(),
                'rejected_investments': Investment.objects.filter(status='rejected').count(),
                'total_investment_amount': Investment.objects.aggregate(
                    total=Sum('amount'))['total'] or 0,
                'total_pending_amount': Investment.objects.filter(
                    status='pending').aggregate(total=Sum('amount'))['total'] or 0,
                'total_approved_amount': Investment.objects.filter(
                    status='approved').aggregate(total=Sum('amount'))['total'] or 0,
            }
            
            serializer = AdminInvestmentStatsSerializer(stats)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error fetching investment stats: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to fetch statistics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# INVESTMENT MANAGEMENT
# ========================================

class AdminInvestmentListView(generics.ListAPIView):
    """
    GET /api/admin/investments/
    
    List all investments with filters
    Query params:
    - search: Search by customer name, phone, investment_id
    - status: Filter by status (pending, approved, rejected, cancelled)
    - property: Filter by property ID
    - customer: Filter by customer ID
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = AdminInvestmentListSerializer
    
    def get_queryset(self):
        queryset = Investment.objects.all().select_related(
            'customer', 'property', 'transaction'
        ).order_by('-created_at')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer__username__icontains=search) |
                Q(customer__phone__icontains=search) |
                Q(customer__email__icontains=search) |
                Q(investment_id__icontains=search)
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by property
        property_id = self.request.query_params.get('property')
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        
        # Filter by customer
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset


class AdminInvestmentDetailView(APIView):
    """
    GET /api/admin/investments/{investment_id}/
    
    Get detailed investment information
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, investment_id):
        try:
            investment = Investment.objects.select_related(
                'customer', 'property', 'transaction', 'approved_by'
            ).get(id=investment_id)
            
            serializer = AdminInvestmentDetailSerializer(investment)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Investment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Investment not found'
            }, status=status.HTTP_404_NOT_FOUND)

class AdminInvestmentActionView(APIView):
    """
    POST /api/admin/investments/{investment_id}/action/
    
    Perform actions on investment
    
    Actions:
    - approve_payment: Approve payment (pending_payment → payment_approved)
    - reject_payment: Reject payment (pending_payment → payment_rejected)
    - approve: Approve investment (payment_approved → approved)
    - reject: Reject investment
    - complete: Mark payment as completed
    - cancel: Cancel investment
    
    Body:
    {
        "action": "approve_payment",
        "rejection_reason": "optional reason for reject"
    }
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, investment_id):
        try:
            investment = Investment.objects.select_related('customer', 'property').get(id=investment_id)
        except Investment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Investment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminInvestmentActionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('rejection_reason', '')
        
        # ============================================
        # 🆕 ACTION: APPROVE PAYMENT
        # ============================================
        if action == 'approve_payment':
            if investment.status != 'pending_payment':
                return Response({
                    'success': False,
                    'message': f'Cannot approve payment for investment with status: {investment.status}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update payment status
            investment.payment_status = 'VERIFIED'
            investment.payment_approved_by = request.user
            investment.payment_approved_at = timezone.now()
            investment.status = 'payment_approved'
            investment.save()
            
            logger.info(f"✅ Admin {request.user.username} approved payment for {investment.investment_id}")
            
            # ============================================
            # 🆕 SEND PAYMENT APPROVED EMAIL
            # ============================================
            if investment.customer.email:
                try:
                    from accounts.services.email_service import send_dynamic_email
                    from django.conf import settings
                    
                    customer_name = investment.customer.get_full_name() or investment.customer.username
                    project_name = investment.property.name
                    dashboard_link = f"{settings.FRONTEND_BASE_URL}/dashboard"
                    support_email = getattr(settings, 'SUPPORT_EMAIL', 'support@aumcapital.com')
                    
                    send_dynamic_email(
                        email_type='payment_approved',
                        to=investment.customer.email,
                        params={
                            'name': customer_name,
                            'project_name': project_name,
                            'working_days': '7',
                            'dashboard_link': dashboard_link,
                            'support_email': support_email,
                        }
                    )
                    
                    logger.info(f"✅ Payment approved email sent to {investment.customer.email}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to send payment approved email: {str(e)}")
            
            message = 'Payment approved successfully. Investment ready for approval.'
        
        # ============================================
        # 🆕 ACTION: REJECT PAYMENT
        # ============================================
        elif action == 'reject_payment':
            if investment.status != 'pending_payment':
                return Response({
                    'success': False,
                    'message': f'Cannot reject payment for investment with status: {investment.status}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            investment.payment_status = 'FAILED'
            investment.payment_rejection_reason = reason
            investment.status = 'payment_rejected'
            investment.save()
            
            logger.info(f"✅ Admin {request.user.username} rejected payment for {investment.investment_id}")
            
            message = 'Payment rejected'
        
        # ============================================
        # 🔧 ACTION: APPROVE INVESTMENT (updated)
        # ============================================
        elif action == 'approve':
            # 🆕 NEW: Can only approve if payment is approved
            if investment.status != 'payment_approved':
                return Response({
                    'success': False,
                    'message': f'Cannot approve investment with status: {investment.status}. Payment must be approved first.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if property has available units
            if investment.property.available_units < investment.units_purchased:
                return Response({
                    'success': False,
                    'message': 'Not enough units available in property'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            investment.status = 'approved'
            investment.approved_at = timezone.now()
            investment.approved_by = request.user
            
            # 🆕 NOW deduct available units (delayed from creation)
            investment.property.available_units -= investment.units_purchased
            investment.property.save()
            
            logger.info(f"✅ Deducted {investment.units_purchased} units from property {investment.property.name}")
            
            # ============================================
            # SEND EOI APPROVED EMAIL
            # ============================================
            if investment.customer.email:
                try:
                    from accounts.services.email_service import send_dynamic_email
                    
                    customer_name = investment.customer.get_full_name() or investment.customer.username
                    project_name = investment.property.name
                    
                    send_dynamic_email(
                        email_type='eoi_approved',
                        to=investment.customer.email,
                        params={
                            'name': customer_name,
                            'project_name': project_name,
                        }
                    )
                    
                    logger.info(f"✅ EOI approved email sent to {investment.customer.email}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to send EOI approval email: {str(e)}")
            
            # ============================================
            # 🆕 NOW CALCULATE COMMISSION (delayed from creation)
            # ============================================
            try:
                from commissions.services.commission_service import CommissionService
                from commissions.models import Commission
                
                # Calculate commission for the investment
                commission = CommissionService.calculate_commission(investment)
                
                if commission:
                    # Auto-approve the commission
                    CommissionService.approve_commission(commission, request.user)
                    logger.info(f"✅ Commission {commission.commission_id} calculated and approved: ₹{commission.commission_amount}")
                else:
                    logger.info(f"ℹ️ No commission calculated (no matching rule or no CP linked)")
                    
            except Exception as e:
                logger.error(f"❌ Error calculating/approving commission: {e}")
                # Don't fail approval if commission fails
            
            message = 'Investment approved successfully'
        
        # ============================================
        # ACTION: REJECT INVESTMENT
        # ============================================
        elif action == 'reject':
            if investment.status not in ['pending_payment', 'payment_approved']:
                return Response({
                    'success': False,
                    'message': f'Cannot reject investment with status: {investment.status}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            investment.status = 'rejected'
            investment.rejection_reason = reason
            investment.approved_by = request.user
            
            # If there was a commission, cancel it
            try:
                from commissions.models import Commission
                
                commission = Commission.objects.filter(
                    investment=investment,
                    status='pending'
                ).first()
                
                if commission:
                    commission.status = 'cancelled'
                    commission.save(update_fields=['status'])
                    logger.info(f"✅ Commission {commission.commission_id} cancelled")
            except Exception as e:
                logger.error(f"❌ Error cancelling commission: {e}")
            
            message = 'Investment rejected'
        
        # ============================================
        # ACTION: COMPLETE (mark payment as completed)
        # ============================================
        elif action == 'complete':
            if investment.status != 'approved':
                return Response({
                    'success': False,
                    'message': f'Can only complete approved investments'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            investment.payment_completed = True
            investment.payment_completed_at = timezone.now()
            
            message = 'Investment marked as completed'
        
        # ============================================
        # ACTION: CANCEL
        # ============================================
        elif action == 'cancel':
            if investment.status in ['cancelled', 'completed']:
                return Response({
                    'success': False,
                    'message': f'Cannot cancel investment with status: {investment.status}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # If already approved, return units to property
            if investment.status == 'approved':
                investment.property.available_units += investment.units_purchased
                investment.property.save()
            
            investment.status = 'cancelled'
            investment.rejection_reason = reason
            
            # Cancel commission if exists
            try:
                from commissions.models import Commission
                
                commission = Commission.objects.filter(
                    investment=investment,
                    status__in=['pending', 'approved']
                ).first()
                
                if commission:
                    commission.status = 'cancelled'
                    commission.save(update_fields=['status'])
                    logger.info(f"✅ Commission {commission.commission_id} cancelled")
            except Exception as e:
                logger.error(f"❌ Error cancelling commission: {e}")
            
            message = 'Investment cancelled'
        
        else:
            return Response({
                'success': False,
                'message': f'Invalid action: {action}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        investment.save()
        
        logger.info(f"✅ Admin {request.user.username} performed '{action}' on investment {investment.investment_id}")
        
        # Get commission info if action was approve
        commission_info = None
        if action == 'approve':
            try:
                from commissions.models import Commission
                commission = Commission.objects.filter(investment=investment).first()
                if commission:
                    commission_info = {
                        'id': commission.id,
                        'cp_name': commission.cp.user.get_full_name() if commission.cp else None,
                        'cp_code': commission.cp.cp_code if commission.cp else None,
                        'amount': str(commission.commission_amount),
                        'rate': str(commission.commission_rate),
                        'status': commission.status
                    }
            except Exception as e:
                logger.warning(f"Could not fetch commission info: {e}")
        
        response_data = {
            'success': True,
            'message': message,
            'data': AdminInvestmentDetailSerializer(investment).data
        }
        
        if commission_info:
            response_data['commission'] = commission_info
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    

class AdminInvestmentsByPropertyView(APIView):
    """
    GET /api/admin/investments/by-property/{property_id}/
    
    Get all investments for a specific property
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, property_id):
        try:
            from properties.models import Property
            property_obj = Property.objects.get(id=property_id)
            
            investments = Investment.objects.filter(
                property=property_obj
            ).select_related('customer').order_by('-created_at')
            
            serializer = AdminInvestmentListSerializer(investments, many=True)
            
            return Response({
                'success': True,
                'property': {
                    'id': property_obj.id,
                    'name': property_obj.name,
                    'address': property_obj.address,  #
                },
                'total_investments': investments.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Property.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Property not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminInvestmentsByCustomerView(APIView):
    """
    GET /api/admin/investments/by-customer/{customer_id}/
    
    Get all investments for a specific customer
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, customer_id):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            customer = User.objects.get(id=customer_id)
            
            investments = Investment.objects.filter(
                customer=customer
            ).select_related('property').order_by('-created_at')
            
            serializer = AdminInvestmentListSerializer(investments, many=True)
            
            return Response({
                'success': True,
                'customer': {
                    'id': customer.id,
                    'username': customer.username,
                    'email': customer.email,
                    'phone': customer.phone,
                },
                'total_investments': investments.count(),
                'total_amount': str(investments.aggregate(total=Sum('amount'))['total'] or 0),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)