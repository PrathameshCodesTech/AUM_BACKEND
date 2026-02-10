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
        
        print("Initial data:", serializer.initial_data)
        print("Validated data:", serializer.validated_data)

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
                    support_email = getattr(settings, 'SUPPORT_EMAIL', 'invest@assetkart.com')
                    
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
    
    # def get(self, request, customer_id):
    #     try:
    #         from django.contrib.auth import get_user_model
    #         from decimal import Decimal



    #         User = get_user_model()
    #         customer = User.objects.get(id=customer_id)
            
    #         investments = Investment.objects.filter(
    #             customer=customer
    #         ).select_related('property').order_by('-created_at')

    #           # 🆕 Calculate payment statistics
    #         total_investments = investments.count()
            
    #         # Total investment amount (sum of minimum_required_amount)
    #         total_amount = investments.aggregate(
    #             total=Sum('minimum_required_amount')
    #         )['total'] or Decimal('0')
            
    #         # 🆕 Total paid amount
    #         total_paid_amount = investments.aggregate(
    #             total=Sum('amount')
    #         )['total'] or Decimal('0')
            
    #         # 🆕 Total due amount (only from partial payments)
    #         total_due_amount = investments.filter(
    #             is_partial_payment=True
    #         ).aggregate(
    #             total=Sum('due_amount')
    #         )['total'] or Decimal('0')
            
    #         serializer = AdminInvestmentListSerializer(investments, many=True)
            
    #         return Response({
    #             'success': True,
    #             'customer': {
    #                 'id': customer.id,
    #                 'username': customer.username,
    #                 'email': customer.email,
    #                 'phone': customer.phone,
    #             },
    #             'total_investments': investments.count(),
    #              # 🆕 Payment breakdown
    #             'total_amount': str(total_amount),           # Total investment value
    #             'total_paid_amount': str(total_paid_amount), # Amount paid so far
    #             'total_due_amount': str(total_due_amount),   # Amount still due
    #             'data': serializer.data
    #         }, status=status.HTTP_200_OK)
            
    #     except User.DoesNotExist:
    #         return Response({
    #             'success': False,
    #             'message': 'Customer not found'
    #         }, status=status.HTTP_404_NOT_FOUND)
    def get(self, request, customer_id):
        try:
            from django.contrib.auth import get_user_model
            from decimal import Decimal

            User = get_user_model()
            customer = User.objects.get(id=customer_id)
            
            investments = Investment.objects.filter(
                customer=customer
            ).select_related('property').order_by('-created_at')

            total_investments = investments.count()
            
            # ✅ CORRECTED CALCULATIONS
            # Total Investment Amount = Sum of all minimum_required_amount (total commitments)
            total_amount = investments.aggregate(
                total=Sum('minimum_required_amount')
            )['total'] or Decimal('0')
            
            # ✅ Total Paid Amount = Sum of actual payments made (amount field)
            total_paid_amount = investments.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            # ✅ Total Due Amount = Total commitment - Total paid
            total_due_amount = total_amount - total_paid_amount
            
            # ✅ DEBUGGING: Print values to see what's happening
            print(f"""
            📊 Customer Investment Summary for {customer.username}:
            - Total Investments: {total_investments}
            - Total Commitment (minimum_required_amount): ₹{total_amount}
            - Total Paid (amount): ₹{total_paid_amount}
            - Total Due: ₹{total_due_amount}
            """)
            
            # ✅ Also print individual investment details
            for inv in investments:
                print(f"""
                Investment {inv.investment_id}:
                - minimum_required_amount: ₹{inv.minimum_required_amount}
                - amount (paid): ₹{inv.amount}
                - due_amount: ₹{inv.due_amount}
                - is_partial_payment: {inv.is_partial_payment}
                """)
            
            serializer = AdminInvestmentListSerializer(investments, many=True)
            
            return Response({
                'success': True,
                'customer': {
                    'id': customer.id,
                    'username': customer.username,
                    'email': customer.email,
                    'phone': customer.phone,
                },
                'total_investments': total_investments,
                'total_amount': str(total_amount),
                'total_paid_amount': str(total_paid_amount),
                'total_due_amount': str(total_due_amount),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)


import logging
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from partners.models import CPCustomerRelation
from .models import Investment
# ✅ Explicit import from admin_serializers
from investments.admin_serializers import CreateInvestmentSerializer
from .serializers import InvestmentSerializer
from .services.investment_service import InvestmentService


class CreateInvestmentView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        logger = logging.getLogger(__name__)

        # Properly flatten QueryDict values
        data = {}
        for key in request.data.keys():
            values = request.data.getlist(key)
            if values:
                data[key] = values[0]   # take the first value only

        serializer = CreateInvestmentSerializer(data=data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Debugging
        print("Initial data:", serializer.initial_data)
        print("Validated data:", serializer.validated_data)

        customer = serializer.validated_data.get('customer_id')
        property_obj = serializer.validated_data.get('property_id')
        referral_code = serializer.validated_data.get('referral_code')

        if not customer or not property_obj:
            return Response({
                'success': False,
                'message': 'customer_id or property_id missing after validation'
            }, status=status.HTTP_400_BAD_REQUEST)

        # CP conflict check
        existing_cp = CPCustomerRelation.objects.filter(
            customer=customer,
            is_active=True,
            is_expired=False
        ).first()
        if existing_cp and referral_code and referral_code != existing_cp.cp.cp_code:
            return Response({
                'success': False,
                'message': f'Customer already linked to {existing_cp.cp.cp_code}. Cannot use {referral_code}.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # payment_data = {k: serializer.validated_data.get(k) for k in [
        #     'payment_method', 'payment_date', 'payment_notes', 'payment_mode', 'transaction_no',
        #     'pos_slip_image', 'cheque_number', 'cheque_date', 'bank_name', 'ifsc_code',
        #     'branch_name', 'cheque_image', 'neft_rtgs_ref_no'
        # ]}
        payment_data = {
            'payment_method': serializer.validated_data.get('payment_method'),
            'payment_date': serializer.validated_data.get('payment_date'),
            'payment_notes': serializer.validated_data.get('payment_notes', ''),
            'payment_mode': serializer.validated_data.get('payment_mode', ''),
            'transaction_no': serializer.validated_data.get('transaction_no', ''),
            'pos_slip_image': serializer.validated_data.get('pos_slip_image'),
            'cheque_number': serializer.validated_data.get('cheque_number', ''),
            'cheque_date': serializer.validated_data.get('cheque_date'),
            'bank_name': serializer.validated_data.get('bank_name', ''),
            'ifsc_code': serializer.validated_data.get('ifsc_code', ''),
            'branch_name': serializer.validated_data.get('branch_name', ''),
            'cheque_image': serializer.validated_data.get('cheque_image'),
            'neft_rtgs_ref_no': serializer.validated_data.get('neft_rtgs_ref_no', ''),
        }

        try:
            investment = InvestmentService.create_investment(
                user=customer,
                # created_by=request.user,
                property_obj=property_obj,
                amount=serializer.validated_data['paid_amount'],
                units_count=serializer.validated_data['units_count'],
                referral_code=referral_code,
                payment_data=payment_data,
                 # 🆕 NEW PARAMETERS
                commitment_amount=serializer.validated_data.get('commitment_amount'),
                payment_due_date=serializer.validated_data.get('payment_due_date'),
            )

            logger.info(f"✅ Investment created by admin: {investment.investment_id}")
            logger.info(f"   Commitment: ₹{investment.minimum_required_amount}")
            logger.info(f"   Paid: ₹{investment.amount}")
            logger.info(f"   Due: ₹{investment.due_amount}")
            logger.info(f"   Due Date: {investment.payment_due_date}")

            # Set created_by after service returns
            # investment.created_by = request.user
            # investment.save(update_fields=['created_by'])

            # AUTO APPROVAL
            # now = timezone.now()
            # investment.status = 'approved'
            # investment.approved_by = request.user
            # investment.approved_at = now
            # investment.payment_status = 'VERIFIED'
            # investment.payment_approved_by = request.user
            # investment.payment_approved_at = now
            # investment.payment_completed = True
            # investment.payment_completed_at = now

            # investment.save(update_fields=[
            #     'status', 'approved_by', 'approved_at', 'payment_status',
            #     'payment_approved_by', 'payment_approved_at', 'payment_completed',
            #     'payment_completed_at'
            # ])

            return Response({
                'success': True,
                'message': 'Investment created successfully.',
                'data': InvestmentSerializer(investment, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception("Investment creation failed")
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)



"""
Add these views to your existing investments/admin_views.py file
"""

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Q
from accounts.permissions import IsAdmin
from .models import Investment
from .admin_serializers import AdminInvestmentListSerializer
import logging

logger = logging.getLogger(__name__)


class AdminInvestmentReceiptsView(APIView):
    """
    GET /api/admin/investments/receipts/
    Get all approved investments (receipts) with filters
    
    Query params:
    - search: Search by customer name, phone, receipt number
    - customer: Filter by customer ID
    - property: Filter by property ID
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        try:
            # Get only approved investments (these are receipts)
            queryset = Investment.objects.filter(
                status='approved'
            ).select_related('customer', 'property').order_by('-approved_at')
            
            # Search
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(customer__username__icontains=search) |
                    Q(customer__phone__icontains=search) |
                    Q(customer__email__icontains=search) |
                    Q(investment_id__icontains=search)
                )
            
            # Filter by customer
            customer_id = request.query_params.get('customer')
            if customer_id:
                queryset = queryset.filter(customer_id=customer_id)
            
            # Filter by property
            property_id = request.query_params.get('property')
            if property_id:
                queryset = queryset.filter(property_id=property_id)
            
            # Filter by date range
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            if date_from:
                queryset = queryset.filter(approved_at__gte=date_from)
            if date_to:
                queryset = queryset.filter(approved_at__lte=date_to)
            
            serializer = AdminInvestmentListSerializer(queryset, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error fetching receipts: {str(e)}")
            return Response({
                'success': False,
                'message': f'Failed to fetch receipts: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminDownloadReceiptView(APIView):
    """
    GET /api/admin/investments/{investment_id}/receipt/download/
    Download receipt PDF for any approved investment
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, investment_id):
        try:
            investment = Investment.objects.select_related('property', 'customer').get(
                id=investment_id,
                status='approved'
            )
            
            # Generate PDF receipt in requested layout
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            from io import BytesIO
            from datetime import datetime

            def amount_to_words(num):
                num = int(round(float(num)))
                ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
                        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
                        "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
                tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
                scales = [(10000000, "Crore"), (100000, "Lakh"), (1000, "Thousand"), (100, "Hundred")]
                words = []
                n = num
                for value, name in scales:
                    if n >= value:
                        count = n // value
                        n = n % value
                        if count >= 20:
                            words.append(tens[count // 10])
                            if count % 10:
                                words.append(ones[count % 10])
                        else:
                            words.append(ones[count])
                        words.append(name)
                if n >= 20:
                    words.append(tens[n // 10])
                    if n % 10:
                        words.append(ones[n % 10])
                elif n > 0:
                    words.append(ones[n])
                return " ".join([w for w in words if w]) or "Zero"

            payer_name = investment.customer.get_full_name() or investment.customer.username
            amount_fig = f"₹{investment.amount:,.2f}"
            amount_words = f"Rupees {amount_to_words(investment.amount)} only"
            payment_mode = investment.get_payment_method_display() if investment.payment_method else "N/A"
            txn_ref = investment.transaction_no or "N/A"
            bank_name = investment.bank_name or "N/A"
            paid_date = investment.payment_date.date() if getattr(investment, "payment_date", None) else investment.approved_at.date() if investment.approved_at else datetime.now().date()
            receipt_date = investment.approved_at.date() if investment.approved_at else datetime.now().date()

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
            styles = getSampleStyleSheet()
            normal = ParagraphStyle('normal', parent=styles['Normal'], fontSize=11, leading=14)
            title = ParagraphStyle('title', parent=styles['Heading1'], alignment=TA_CENTER, textColor=colors.black, fontSize=18, spaceAfter=12)
            label_style = ParagraphStyle('label', parent=normal, fontName='Helvetica-Bold')
            value_style = ParagraphStyle('value', parent=normal)

            elements = []
            elements.append(Paragraph("PAYMENT RECEIPT", title))
            elements.append(Spacer(1, 6*mm))

            header_table = Table([
                [Paragraph("Receipt No.:", label_style), Paragraph(str(investment.investment_id), value_style),
                 Paragraph("Date:", label_style), Paragraph(receipt_date.strftime('%d-%m-%Y'), value_style)],
            ], colWidths=[28*mm, 55*mm, 18*mm, 32*mm])
            header_table.setStyle(TableStyle([
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 4*mm))

            body_rows = [
                ("Received with thanks from", f"Mr./Ms. {payer_name}"),
                ("Amount (figures)", amount_fig),
                ("Amount (words)", amount_words),
                ("Towards", "Investment"),
                ("Project Name", investment.property.name),
            ]
            body_table = Table([[Paragraph(f"{k}:", label_style), Paragraph(v, value_style)] for k,v in body_rows],
                               colWidths=[45*mm, 98*mm])
            body_table.setStyle(TableStyle([
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            elements.append(body_table)
            elements.append(Spacer(1, 6*mm))

            pay_rows = [
                ("Mode of Payment", payment_mode),
                ("Transaction / Reference No.", txn_ref),
                ("Dated", paid_date.strftime('%d-%m-%Y')),
                ("Bank", bank_name),
            ]
            pay_table = Table([[Paragraph(f"{k}:", label_style), Paragraph(v, value_style)] for k,v in pay_rows],
                              colWidths=[45*mm, 98*mm])
            pay_table.setStyle(TableStyle([
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            elements.append(pay_table)
            elements.append(Spacer(1, 12*mm))

            elements.append(Paragraph("This receipt is issued as an acknowledgement of payment received.", normal))
            elements.append(Spacer(1, 14*mm))

            elements.append(Paragraph("For AssetKart", normal))
            elements.append(Spacer(1, 12*mm))
            elements.append(Paragraph("Authorized Signatory", normal))
            elements.append(Paragraph("Name: ________________________________", normal))
            elements.append(Paragraph("Designation: __________________________", normal))
            elements.append(Spacer(1, 12*mm))
            elements.append(Paragraph("Powered by AssetKart", ParagraphStyle('center', parent=normal, alignment=TA_CENTER)))

            doc.build(elements)
            
            # Return PDF
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="receipt-{investment.investment_id}.pdf"'
            
            return response
            
        except Investment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Receipt not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"❌ Error generating receipt: {str(e)}")
            return Response({
                'success': False,
                'message': f'Failed to generate receipt: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)      



