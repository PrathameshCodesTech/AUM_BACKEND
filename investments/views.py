from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services.wallet_service import WalletService
from .serializers import WalletSerializer, TransactionSerializer,CreateInvestmentSerializer,InvestmentSerializer 
from .models import Wallet, Investment  # 👈 ADD Investment HERE!
from decimal import Decimal  # ←
from .services.investment_service import InvestmentService
from rest_framework.decorators import api_view, permission_classes


class CreateWalletView(APIView):
    """
    POST /api/wallet/create/
    Create wallet for authenticated user
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Get or create wallet
        wallet = WalletService.create_wallet(request.user)
        serializer = WalletSerializer(wallet)
        
        # Check if it was just created or already existed
        existing = Wallet.objects.filter(user=request.user).exists()
        
        return Response({
            'success': True,
            'message': 'Digital Assets Account retrieved successfully' if existing else 'Digital Assets Account created successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK if existing else status.HTTP_201_CREATED)



class WalletBalanceView(APIView):
    """
    GET /api/wallet/balance/
    Get wallet balance
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            balance_info = WalletService.get_balance(request.user)
            return Response({
                'success': True,
                'data': balance_info
            }, status=status.HTTP_200_OK)
        except Wallet.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Wallet not found. Please create wallet first.'
            }, status=status.HTTP_404_NOT_FOUND)


class AddFundsView(APIView):
    """
    POST /api/wallet/add-funds/
    Add funds to wallet
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'razorpay')
        payment_id = request.data.get('payment_id')
        
        if not amount or float(amount) <= 0:
            return Response({
                'success': False,
                'message': 'Invalid amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            txn = WalletService.add_funds(
                request.user,
                Decimal(amount),
                payment_method,
                payment_id
            )
            
            return Response({
                'success': True,
                'message': 'Funds added successfully',
                'data': TransactionSerializer(txn).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TransactionHistoryView(APIView):
    """
    GET /api/wallet/transactions/
    Get transaction history
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        transactions = WalletService.get_transactions(request.user)
        serializer = TransactionSerializer(transactions, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
class CreateInvestmentView(APIView):
    """
    POST /api/wallet/investments/create/
    Create new investment WITH payment details (NO wallet)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        from partners.models import CPCustomerRelation
        
        logger.info(f"📥 Received investment request from: {request.user.username}")
        logger.info(f"📥 Request data: {request.data}")
        
        # ============================================
        # VALIDATION: Check CP Relation Conflict
        # ============================================
        existing_cp = CPCustomerRelation.objects.filter(
            customer=request.user,
            is_active=True,
            is_expired=False
        ).first()
        
        referral_code = request.data.get('referral_code')
        
        if existing_cp and referral_code:
            if referral_code != existing_cp.cp.cp_code:
                logger.warning(f"❌ User {request.user.phone} already linked to {existing_cp.cp.cp_code}, tried to use {referral_code}")
                return Response({
                    'success': False,
                    'error': 'invalid_referral',
                    'message': f'You are already linked to {existing_cp.cp.cp_code}. Cannot use a different referral code.'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                logger.info(f"✅ User using correct CP code: {referral_code}")
        
        # ============================================
        # VALIDATE INPUT DATA
        # ============================================
        serializer = CreateInvestmentSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"❌ Serializer validation failed: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            logger.info(f"✅ Serializer valid, creating investment...")
            
            # ============================================
            # 🆕 PREPARE PAYMENT DATA FROM VALIDATED DATA
            # ============================================
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
            
            logger.info(f"💳 Payment method: {payment_data['payment_method']}")
            
            # ============================================
            # CREATE INVESTMENT WITH PAYMENT DATA
            # ============================================
            investment = InvestmentService.create_investment(
                user=request.user,
                property_obj=serializer.validated_data['property'],
                amount=serializer.validated_data['amount'],
                units_count=serializer.validated_data['units_count'],
                referral_code=serializer.validated_data.get('referral_code'),
                payment_data=payment_data  # 🆕 PASS PAYMENT DATA
            )
            
            logger.info(f"✅ Investment created: {investment.investment_id}")
            logger.info(f"   Status: {investment.status}")
            logger.info(f"   Payment status: {investment.payment_status}")
            
            # Serialize the response
            investment_data = InvestmentSerializer(investment, context={'request': request}).data
            
            logger.info(f"✅ Sending success response")
            
            return Response({
                'success': True,
                'message': 'Investment submitted successfully. Waiting for payment approval.',
                'data': investment_data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"❌ Exception in view: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
class MyInvestmentsView(APIView):
    """
    GET /api/wallet/investments/my-investments/
    Get user's investments
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # 👇 FIXED: Query directly instead of using service method
            investments = Investment.objects.filter(
                customer=request.user,
                is_deleted=False
            ).select_related('property').order_by('-created_at')
            
            serializer = InvestmentSerializer(
                investments, 
                many=True, 
                context={'request': request}
            )
            
            return Response({
                'success': True,
                'data': serializer.data,
                'count': investments.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error fetching investments: {str(e)}")
            
            return Response({
                'success': False,
                'message': f'Failed to fetch investments: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvestmentDetailView(APIView):
    """
    GET /api/wallet/investments/{id}/details/
    Get investment details
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, investment_id):
        try:
            investment = Investment.objects.select_related('property').get(
                id=investment_id,
                customer=request.user,
                is_deleted=False
            )
            
            serializer = InvestmentSerializer(
                investment, 
                context={'request': request}
            )
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Investment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Investment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error fetching investment detail: {str(e)}")
            
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg
from decimal import Decimal
from .models import Investment
from properties.models import Property


class PortfolioAnalyticsView(APIView):
    """
    GET /api/portfolio/analytics/
    Returns aggregated portfolio analytics
    Mode: 'demo' if no investments, 'personal' if has investments
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get user's approved investments
        investments = Investment.objects.filter(
            customer=request.user,
            status='approved'
        ).select_related('property')
        
        if not investments.exists():
            # NO INVESTMENTS - Return demo/sample data
            return Response({
                'success': True,
                'mode': 'demo',
                'message': 'Start investing to see your portfolio analytics',
                'data': self._get_demo_data()
            }, status=status.HTTP_200_OK)
        
        else:
            # HAS INVESTMENTS - Return real aggregated data
            return Response({
                'success': True,
                'mode': 'personal',
                'message': 'Your live portfolio analytics',
                'data': self._get_personal_data(investments)
            }, status=status.HTTP_200_OK)
    
    def _get_demo_data(self):
        """Returns static demo data for users with no investments"""
        return {
            'total_invested': 0,
            'current_value': 5000000,  # Sample 50 lakhs
            'total_returns': 925000,    # Sample returns
            'total_roi': 18.5,
            'properties_count': 0,
            
            # ========== NEW: CASH FLOW DATA ==========
            'cash_flow': [
                {'year': 'Year 1', 'rental_income': 1.2, 'capital_appreciation': 0.3},
                {'year': 'Year 2', 'rental_income': 1.3, 'capital_appreciation': 0.4},
                {'year': 'Year 3', 'rental_income': 1.4, 'capital_appreciation': 0.5},
                {'year': 'Year 4', 'rental_income': 1.5, 'capital_appreciation': 0.6},
                {'year': 'Year 5', 'rental_income': 1.6, 'capital_appreciation': 0.8},
                {'year': 'Year 6', 'rental_income': 1.7, 'capital_appreciation': 1.0},
                {'year': 'Year 7', 'rental_income': 1.8, 'capital_appreciation': 1.2}
            ],
            
            # ========== NEW: FUNDING STATUS DATA ==========
            'entry_yield': '8.2',
            'projected_irr': '13.8% – 15.2%',
            'investment_tenure': '5–7 Years',
            'total_earnings': '8',
            'investment_amount': '25',
            'funding_percentage': 72,
            'funded_amount': '18',
            'available_amount': '7',
            'asset_grade': 'A',
            'asset_grade_description': 'Premium commercial location with strong tenant profile',
            
            # ========== EXISTING DATA ==========
            'portfolio_breakdown': [
                {
                    'property_name': 'DLF Garden City',
                    'property_id': None,
                    'invested': 2000000,
                    'current_value': 2400000,
                    'roi': 20.0,
                    'percentage': 40.0
                },
                {
                    'property_name': 'Prestige Lakeside Habitat',
                    'property_id': None,
                    'invested': 1500000,
                    'current_value': 1725000,
                    'roi': 15.0,
                    'percentage': 30.0
                },
                {
                    'property_name': 'Godrej Summit',
                    'property_id': None,
                    'invested': 1500000,
                    'current_value': 1770000,
                    'roi': 18.0,
                    'percentage': 30.0
                }
            ],
            'roi_breakdown': [
                {'name': 'Rental Yield', 'value': 6.5, 'color': '#10B981'},
                {'name': 'Capital Appreciation', 'value': 8.0, 'color': '#F59E0B'},
                {'name': 'Target IRR', 'value': 15.5, 'color': '#3B82F6'}
            ],
            'portfolio_growth': [
                {'month': 'Jan 2024', 'value': 5000000},
                {'month': 'Feb 2024', 'value': 5100000},
                {'month': 'Mar 2024', 'value': 5250000},
                {'month': 'Apr 2024', 'value': 5350000},
                {'month': 'May 2024', 'value': 5500000},
                {'month': 'Jun 2024', 'value': 5650000},
                {'month': 'Jul 2024', 'value': 5750000},
                {'month': 'Aug 2024', 'value': 5850000},
                {'month': 'Sep 2024', 'value': 5925000}
            ],
            'payout_history': [
                {'quarter': 'Q1 2024', 'amount': 75000, 'type': 'actual'},
                {'quarter': 'Q2 2024', 'amount': 85000, 'type': 'actual'},
                {'quarter': 'Q3 2024', 'amount': 95000, 'type': 'actual'},
                {'quarter': 'Q4 2024', 'amount': 105000, 'type': 'projected'},
                {'quarter': 'Q1 2025', 'amount': 120000, 'type': 'projected'}
            ],
            'property_types': [
                {'type': 'Residential', 'value': 60, 'color': '#10B981'},
                {'type': 'Commercial', 'value': 30, 'color': '#3B82F6'},
                {'type': 'Mixed-Use', 'value': 10, 'color': '#F59E0B'}
            ]
        }
    
    def _get_personal_data(self, investments):
        """Returns real aggregated data from user's investments"""
        # Calculate totals
        total_invested = sum(float(inv.amount) for inv in investments)
        total_returns = sum(float(inv.actual_return_amount or 0) for inv in investments)
        current_value = total_invested + total_returns
        total_roi = (total_returns / total_invested * 100) if total_invested > 0 else 0
        
        # Portfolio breakdown by property
        portfolio_breakdown = []
        for inv in investments:
            invested = float(inv.amount)
            returns = float(inv.actual_return_amount or 0)
            prop_current_value = invested + returns
            prop_roi = (returns / invested * 100) if invested > 0 else 0
            percentage = (invested / total_invested * 100) if total_invested > 0 else 0
            
            portfolio_breakdown.append({
                'property_name': inv.property.name,
                'property_id': inv.property.id,
                'property_slug': inv.property.slug,
                'invested': invested,
                'current_value': prop_current_value,
                'roi': round(prop_roi, 2),
                'percentage': round(percentage, 2)
            })
        
        # ROI breakdown (average from properties)
        active_investments = [inv for inv in investments if inv.property]
        avg_yield = sum(float(inv.property.gross_yield or 0) for inv in active_investments) / len(active_investments) if active_investments else 0
        avg_gain = sum(float(inv.property.potential_gain or 0) for inv in active_investments) / len(active_investments) if active_investments else 0
        avg_irr = sum(float(inv.property.expected_return_percentage or 0) for inv in active_investments) / len(active_investments) if active_investments else 0
        
        roi_breakdown = [
            {'name': 'Rental Yield', 'value': round(avg_yield, 2), 'color': '#10B981'},
            {'name': 'Capital Appreciation', 'value': round(avg_gain, 2), 'color': '#F59E0B'},
            {'name': 'Target IRR', 'value': round(avg_irr, 2), 'color': '#3B82F6'}
        ]
        
        # Portfolio growth (mock data - implement real historical tracking later)
        portfolio_growth = []
        for i in range(9):
            growth_rate = 0.015 + (i * 0.002)
            portfolio_growth.append({
                'month': f'Month {i+1}',
                'value': round(total_invested * (1 + growth_rate * i))
            })
        
        # Payout history (mock data - implement real payout tracking later)
        payout_history = [
            {'quarter': 'Q1 2024', 'amount': round(total_returns * 0.2, 2), 'type': 'actual'},
            {'quarter': 'Q2 2024', 'amount': round(total_returns * 0.25, 2), 'type': 'actual'},
            {'quarter': 'Q3 2024', 'amount': round(total_returns * 0.3, 2), 'type': 'actual'},
            {'quarter': 'Q4 2024', 'amount': round(total_returns * 0.15, 2), 'type': 'projected'},
            {'quarter': 'Q1 2025', 'amount': round(total_returns * 0.1, 2), 'type': 'projected'}
        ]
        
        # Property types distribution
        property_types_count = {}
        for inv in investments:
            prop_type = inv.property.property_type
            if prop_type not in property_types_count:
                property_types_count[prop_type] = 0
            property_types_count[prop_type] += float(inv.amount)
        
        property_types = []
        colors = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444']
        for idx, (prop_type, amount) in enumerate(property_types_count.items()):
            percentage = (amount / total_invested * 100) if total_invested > 0 else 0
            property_types.append({
                'type': prop_type.title(),
                'value': round(percentage, 1),
                'color': colors[idx % len(colors)]
            })
        
        # ========== NEW: CALCULATE CASH FLOW DATA ==========
        # Project cash flow over tenure based on average yields and appreciation
        tenure_years = 7  # Default tenure
        annual_rental_rate = avg_yield / 100 if avg_yield > 0 else 0.08  # Default 8%
        annual_appreciation_rate = avg_gain / 100 / tenure_years if avg_gain > 0 else 0.05  # Spread appreciation
        
        cash_flow = []
        base_investment_lakhs = total_invested / 100000  # Convert to lakhs
        
        for year in range(1, tenure_years + 1):
            rental_income = round(base_investment_lakhs * annual_rental_rate * year, 1)
            capital_appreciation = round(base_investment_lakhs * annual_appreciation_rate * year, 1)
            cash_flow.append({
                'year': f'Year {year}',
                'rental_income': rental_income,
                'capital_appreciation': capital_appreciation
            })
        
        # ========== NEW: CALCULATE FUNDING STATUS DATA ==========
        # Entry yield - average of all properties
        entry_yield = str(round(avg_yield, 1))
        
        # Projected IRR range - based on property IRR values
        irr_values = [float(inv.property.expected_return_percentage or 0) for inv in active_investments]
        if irr_values:
            min_irr = round(min(irr_values), 1)
            max_irr = round(max(irr_values), 1)
            projected_irr = f"{min_irr}% – {max_irr}%"
        else:
            projected_irr = "13.8% – 15.2%"
        
        # Investment tenure - get from properties or default
        investment_tenure = "5–7 Years"  # Default, can be calculated from property data
        
        # Total earnings and investment amount (in lakhs)
        total_earnings_lakhs = str(round(total_returns / 100000, 1))
        investment_amount_lakhs = str(round(total_invested / 100000, 1))
        
        # Funding status - calculate based on property funding
        # For now, using average across properties
        total_funding = 0
        total_capacity = 0
        for inv in active_investments:
            prop = inv.property
            if hasattr(prop, 'total_units') and hasattr(prop, 'available_units'):
                sold_units = prop.total_units - prop.available_units
                total_funding += sold_units
                total_capacity += prop.total_units
        
        if total_capacity > 0:
            funding_percentage = round((total_funding / total_capacity) * 100)
        else:
            funding_percentage = 72  # Default
        
        funded_amount_lakhs = str(round(total_invested * (funding_percentage / 100) / 100000, 1))
        available_amount_lakhs = str(round(total_invested * ((100 - funding_percentage) / 100) / 100000, 1))
        
        # Asset grade - can be from property or calculated
        asset_grade = "A"  # Default, enhance with actual property grade field later
        asset_grade_description = "Premium properties with strong fundamentals"
        
        return {
            'total_invested': round(total_invested, 2),
            'current_value': round(current_value, 2),
            'total_returns': round(total_returns, 2),
            'total_roi': round(total_roi, 2),
            'properties_count': investments.count(),
            
            # ========== NEW: CASH FLOW ==========
            'cash_flow': cash_flow,
            
            # ========== NEW: FUNDING STATUS ==========
            'entry_yield': entry_yield,
            'projected_irr': projected_irr,
            'investment_tenure': investment_tenure,
            'total_earnings': total_earnings_lakhs,
            'investment_amount': investment_amount_lakhs,
            'funding_percentage': funding_percentage,
            'funded_amount': funded_amount_lakhs,
            'available_amount': available_amount_lakhs,
            'asset_grade': asset_grade,
            'asset_grade_description': asset_grade_description,
            
            # ========== EXISTING DATA ==========
            'portfolio_breakdown': portfolio_breakdown,
            'roi_breakdown': roi_breakdown,
            'portfolio_growth': portfolio_growth,
            'payout_history': payout_history,
            'property_types': property_types
        }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_cp_relation(request):
    """
    GET /api/wallet/investments/check-cp-relation/
    Check if user is linked to any CP
    """
    from partners.models import CPCustomerRelation
    
    cp_relation = CPCustomerRelation.objects.filter(
        customer=request.user,
        is_active=True,
        is_expired=False
    ).first()
    
    if cp_relation:
        return Response({
            'success': True,
            'has_cp_relation': True,
            'cp_details': {
                'cp_code': cp_relation.cp.cp_code,
                'cp_name': cp_relation.cp.user.get_full_name(),
                'referral_date': cp_relation.referral_date,
                'is_active': cp_relation.is_active,
            }
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': True,
        'has_cp_relation': False
    }, status=status.HTTP_200_OK)


# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from .models import Investment
from .serializers import InvestmentSerializer
import logging

logger = logging.getLogger(__name__)


class InvestmentReceiptsView(APIView):
    """
    GET /api/wallet/investments/receipts/
    Get all approved investments as receipts
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get only approved investments (these have receipts)
            receipts = Investment.objects.filter(
                customer=request.user,
                status='approved',
                is_deleted=False
            ).select_related('property').order_by('-approved_at')
            
            # Use the same serializer but add receipt-specific fields
            serializer = InvestmentSerializer(
                receipts, 
                many=True, 
                context={'request': request}
            )
            
            return Response({
                'success': True,
                'data': serializer.data,
                'count': receipts.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error fetching receipts: {str(e)}")
            return Response({
                'success': False,
                'message': f'Failed to fetch receipts: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _amount_to_words(amount):
    """Convert a number to Indian currency words (e.g. 125000 -> 'One Lakh Twenty Five Thousand')"""
    ones = [
        '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
        'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
        'Seventeen', 'Eighteen', 'Nineteen'
    ]
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def words_below_100(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + ((' ' + ones[n % 10]) if n % 10 != 0 else '')

    def words_below_1000(n):
        if n < 100:
            return words_below_100(n)
        return ones[n // 100] + ' Hundred' + ((' ' + words_below_100(n % 100)) if n % 100 != 0 else '')

    amount = int(amount)
    if amount == 0:
        return 'Zero'

    result = ''
    if amount >= 10000000:
        result += words_below_1000(amount // 10000000) + ' Crore '
        amount %= 10000000
    if amount >= 100000:
        result += words_below_1000(amount // 100000) + ' Lakh '
        amount %= 100000
    if amount >= 1000:
        result += words_below_1000(amount // 1000) + ' Thousand '
        amount %= 1000
    if amount > 0:
        result += words_below_1000(amount)

    return result.strip()


class DownloadReceiptView(APIView):
    """
    GET /api/wallet/investments/{investment_id}/receipt/download/
    Download receipt PDF for approved investment
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, investment_id):
        try:
            investment = Investment.objects.select_related('property').get(
                id=investment_id,
                customer=request.user,
                status='approved',
                is_deleted=False
            )

            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch, mm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from io import BytesIO
            from datetime import datetime
            import os
            from django.conf import settings

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=1.2 * inch,
                rightMargin=1.2 * inch,
                topMargin=1 * inch,
                bottomMargin=1 * inch,
            )
            elements = []
            styles = getSampleStyleSheet()

            # ── Styles ──────────────────────────────────────────────────────
            title_style = ParagraphStyle(
                'ReceiptTitle',
                parent=styles['Normal'],
                fontSize=16,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER,
                spaceAfter=18,
                leading=20,
            )
            normal_style = ParagraphStyle(
                'ReceiptNormal',
                parent=styles['Normal'],
                fontSize=10,
                fontName='Helvetica',
                leading=16,
            )
            bold_style = ParagraphStyle(
                'ReceiptBold',
                parent=styles['Normal'],
                fontSize=10,
                fontName='Helvetica-Bold',
                leading=16,
            )
            footer_style = ParagraphStyle(
                'ReceiptFooter',
                parent=styles['Normal'],
                fontSize=9,
                fontName='Helvetica',
                textColor=colors.HexColor('#555555'),
                alignment=TA_CENTER,
            )

            # ── Logo ─────────────────────────────────────────────────────────
            logo_path = os.path.join(settings.BASE_DIR, 'assets', 'Alogo.png')
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=2.2 * inch, height=0.75 * inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 8))

            # ── Title ────────────────────────────────────────────────────────
            elements.append(Paragraph("PAYMENT RECEIPT", title_style))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=12))

            # ── Receipt No. + Date row ────────────────────────────────────────
            receipt_date = (
                investment.approved_at.strftime('%d-%m-%Y')
                if investment.approved_at else
                investment.investment_date.strftime('%d-%m-%Y')
            )
            header_row = Table(
                [[
                    Paragraph(f"Receipt No.: <b>{investment.investment_id}</b>", normal_style),
                    Paragraph(f"Date: <b>{receipt_date}</b>", normal_style),
                ]],
                colWidths=[3.2 * inch, 3.2 * inch],
            )
            header_row.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(header_row)
            elements.append(Spacer(1, 10))

            # ── Received from ────────────────────────────────────────────────
            customer_name = investment.customer.get_full_name() or investment.customer.username
            amount_val = investment.amount
            amount_words = _amount_to_words(amount_val)

            elements.append(Paragraph(
                f"Received with thanks from <b>Mr./Ms. {customer_name}</b> &nbsp;&nbsp; the sum of <b>Rs. {amount_val:,.2f}</b>",
                normal_style
            ))
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(
                f"<b>(Rupees {amount_words} Only)</b>",
                normal_style
            ))
            elements.append(Spacer(1, 12))

            # ── Towards + Project Name ────────────────────────────────────────
            elements.append(Paragraph(
                f"<b>Towards:</b> &nbsp; {investment.property.name}",
                normal_style
            ))
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(
                f"<b>Project Name:</b> &nbsp; {investment.property.name}",
                normal_style
            ))
            elements.append(Spacer(1, 16))

            # ── Payment Details Table (only for All Investments tab) ─────────────
            source = request.GET.get('source', 'all')

            method_map = {
                'ONLINE': 'Online / UPI',
                'POS': 'POS',
                'DRAFT_CHEQUE': 'Cheque',
                'NEFT_RTGS': 'NEFT / RTGS',
            }

            if source != 'transaction':
                # All Investments tab: show single payment details table
                payment_method_display = method_map.get(
                    investment.payment_method,
                    investment.get_payment_method_display() if investment.payment_method else 'N/A'
                )

                if investment.payment_method == 'DRAFT_CHEQUE':
                    ref_no = investment.cheque_number or 'N/A'
                elif investment.payment_method == 'NEFT_RTGS':
                    ref_no = investment.neft_rtgs_ref_no or investment.transaction_no or 'N/A'
                else:
                    ref_no = investment.transaction_no or 'N/A'

                if investment.payment_method == 'DRAFT_CHEQUE' and investment.cheque_date:
                    txn_dated = investment.cheque_date.strftime('%d-%m-%Y')
                elif investment.payment_date:
                    txn_dated = investment.payment_date.strftime('%d-%m-%Y') if hasattr(investment.payment_date, 'strftime') else str(investment.payment_date)
                else:
                    txn_dated = receipt_date

                label_bg = colors.HexColor('#f0f0f0')
                border_color = colors.black

                payment_table_data = [
                    [Paragraph('<b>Mode of Payment</b>', normal_style),
                     Paragraph(payment_method_display, normal_style)],
                    [Paragraph('<b>Transaction / Reference No.</b>', normal_style),
                     Paragraph(ref_no, normal_style)],
                    [Paragraph('<b>Dated</b>', normal_style),
                     Paragraph(txn_dated, normal_style)],
                ]

                payment_table = Table(payment_table_data, colWidths=[2.5 * inch, 3.9 * inch])
                payment_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), label_bg),
                    ('BOX', (0, 0), (-1, -1), 0.75, border_color),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                elements.append(payment_table)
                elements.append(Spacer(1, 20))

            # ── Acknowledgement text ──────────────────────────────────────────
            elements.append(Paragraph(
                "This receipt is issued as an acknowledgement of payment received.",
                normal_style
            ))
            elements.append(Spacer(1, 40))

            # ── Footer ────────────────────────────────────────────────────────
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#aaaaaa'), spaceAfter=8))
            elements.append(Paragraph("Powered by AssetKart", footer_style))

            doc.build(elements)

            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="receipt-{investment.investment_id}.pdf"'
            return response

        except Investment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Receipt not found or not available'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"❌ Error generating receipt: {str(e)}")
            return Response({
                'success': False,
                'message': f'Failed to generate receipt: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReceiptDetailView(APIView):
    """
    GET /api/wallet/investments/{investment_id}/receipt/
    Get receipt details (same as investment detail but for approved only)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, investment_id):
        try:
            investment = Investment.objects.select_related('property').get(
                id=investment_id,
                customer=request.user,
                status='approved',
                is_deleted=False
            )
            
            serializer = InvestmentSerializer(
                investment, 
                context={'request': request}
            )
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Investment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Receipt not found'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================
# INSTALMENT / PAY-REMAINING VIEWS
# ============================================================

class PayRemainingView(APIView):
    """
    POST /api/wallet/investments/{investment_id}/pay-remaining/
    Submit a remaining (instalment) payment for a partial-payment investment.
    amount can be less than the full due_amount (further partial).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, investment_id):
        from .serializers import CreateRemainingPaymentSerializer, InvestmentPaymentSerializer
        from .models import InvestmentPayment
        from decimal import Decimal

        try:
            investment = Investment.objects.select_related('property').get(
                id=investment_id,
                customer=request.user,
                is_deleted=False,
            )
        except Investment.DoesNotExist:
            return Response({'success': False, 'message': 'Investment not found'},
                            status=status.HTTP_404_NOT_FOUND)

        if investment.due_amount <= 0:
            return Response({'success': False, 'message': 'No outstanding due amount for this investment'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = CreateRemainingPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        pay_amount = Decimal(str(data['amount']))

        if pay_amount > investment.due_amount:
            return Response({
                'success': False,
                'message': f'Amount ₹{pay_amount} exceeds outstanding due ₹{investment.due_amount}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Determine payment number (existing payments + 2 because first payment is the investment itself)
        existing_count = investment.instalment_payments.count()
        payment_number = existing_count + 2  # 1 = initial investment payment

        due_before = investment.due_amount
        due_after = due_before - pay_amount

        payment = InvestmentPayment.objects.create(
            payment_id=InvestmentPayment.generate_payment_id(),
            investment=investment,
            payment_number=payment_number,
            amount=pay_amount,
            due_amount_before=due_before,
            due_amount_after=due_after,
            payment_method=data.get('payment_method', ''),
            payment_status='PENDING',
            payment_date=data.get('payment_date'),
            payment_notes=data.get('payment_notes', ''),
            payment_mode=data.get('payment_mode', ''),
            transaction_no=data.get('transaction_no', ''),
            pos_slip_image=data.get('pos_slip_image'),
            cheque_number=data.get('cheque_number', ''),
            cheque_date=data.get('cheque_date'),
            bank_name=data.get('bank_name', ''),
            ifsc_code=data.get('ifsc_code', ''),
            branch_name=data.get('branch_name', ''),
            cheque_image=data.get('cheque_image'),
            neft_rtgs_ref_no=data.get('neft_rtgs_ref_no', ''),
        )

        # Update investment due amount immediately (will be adjusted on approval/rejection)
        # We track the "pending" state — due_amount stays until admin approves
        logger.info(f"✅ Instalment payment {payment.payment_id} created for {investment.investment_id}")

        return Response({
            'success': True,
            'message': 'Payment submitted successfully. Awaiting admin approval.',
            'data': InvestmentPaymentSerializer(payment).data
        }, status=status.HTTP_201_CREATED)


class InvestmentPaymentsListView(APIView):
    """
    GET /api/wallet/investments/{investment_id}/payments/
    List all instalment payments for an investment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, investment_id):
        from .serializers import InvestmentPaymentSerializer
        from .models import InvestmentPayment

        try:
            investment = Investment.objects.get(
                id=investment_id,
                customer=request.user,
                is_deleted=False,
            )
        except Investment.DoesNotExist:
            return Response({'success': False, 'message': 'Investment not found'},
                            status=status.HTTP_404_NOT_FOUND)

        payments = investment.instalment_payments.select_related('payment_approved_by').order_by('payment_number', 'created_at')
        serializer = InvestmentPaymentSerializer(payments, many=True)

        return Response({
            'success': True,
            'data': serializer.data,
            'count': payments.count(),
        }, status=status.HTTP_200_OK)


class DownloadPaymentReceiptView(APIView):
    """
    GET /api/wallet/investments/{investment_id}/payments/{payment_id}/receipt/download/
    Download PDF receipt for a specific approved instalment payment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, investment_id, payment_id):
        from .models import InvestmentPayment

        try:
            investment = Investment.objects.select_related('property').get(
                id=investment_id,
                customer=request.user,
                is_deleted=False,
            )
        except Investment.DoesNotExist:
            return Response({'success': False, 'message': 'Investment not found'},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            payment = InvestmentPayment.objects.get(
                id=payment_id,
                investment=investment,
                payment_status='VERIFIED',
            )
        except InvestmentPayment.DoesNotExist:
            return Response({'success': False, 'message': 'Receipt not found or payment not yet verified'},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from io import BytesIO
            import os
            from django.conf import settings

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=1.2 * inch,
                rightMargin=1.2 * inch,
                topMargin=1 * inch,
                bottomMargin=1 * inch,
            )
            elements = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'ReceiptTitle', parent=styles['Normal'],
                fontSize=16, fontName='Helvetica-Bold',
                alignment=TA_CENTER, spaceAfter=18, leading=20,
            )
            normal_style = ParagraphStyle(
                'ReceiptNormal', parent=styles['Normal'],
                fontSize=10, fontName='Helvetica', leading=16,
            )
            bold_style = ParagraphStyle(
                'ReceiptBold', parent=styles['Normal'],
                fontSize=10, fontName='Helvetica-Bold', leading=16,
            )
            right_style = ParagraphStyle(
                'ReceiptRight', parent=styles['Normal'],
                fontSize=10, fontName='Helvetica', alignment=TA_RIGHT, leading=16,
            )
            footer_style = ParagraphStyle(
                'ReceiptFooter', parent=styles['Normal'],
                fontSize=8, fontName='Helvetica',
                alignment=TA_CENTER, textColor=colors.HexColor('#888888'),
            )

            # ── Logo ───────────────────────────────────────────────────────
            logo_path = os.path.join(settings.BASE_DIR, 'assets', 'Alogo.png')
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=2.2 * inch, height=0.75 * inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 8))

            # ── Title ──────────────────────────────────────────────────────
            elements.append(Paragraph("PAYMENT RECEIPT", title_style))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=12))

            # ── Receipt No + Date row ───────────────────────────────────────
            receipt_no = payment.payment_id
            approved_date = (payment.payment_approved_at or payment.created_at)
            receipt_date = approved_date.strftime('%d-%m-%Y')

            meta_data = [[
                Paragraph(f'<b>Receipt No.:</b> {receipt_no}', bold_style),
                Paragraph(f'<b>Date:</b> {receipt_date}', right_style),
            ]]
            meta_table = Table(meta_data, colWidths=[3.5 * inch, 3.5 * inch])
            meta_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 14))

            # ── Received with thanks ────────────────────────────────────────
            customer = investment.customer
            customer_name = customer.get_full_name() or customer.username
            amount_words = _amount_to_words(int(payment.amount))
            amount_formatted = f"₹{payment.amount:,.2f}"

            elements.append(Paragraph(
                f"Received with thanks from <b>Mr./Ms. {customer_name}</b> the sum of <b>{amount_formatted}</b>",
                normal_style
            ))
            elements.append(Paragraph(
                f"(Rupees {amount_words} only)",
                normal_style
            ))
            elements.append(Spacer(1, 10))

            # ── Towards / Project ──────────────────────────────────────────
            property_name = investment.property.name
            elements.append(Paragraph(f"<b>Towards:</b> {property_name}", normal_style))
            elements.append(Paragraph(f"<b>Project Name:</b> {property_name}", normal_style))
            elements.append(Paragraph(f"<b>Instalment No.:</b> {payment.payment_number}", normal_style))
            elements.append(Spacer(1, 14))

            # ── Payment Details Table ──────────────────────────────────────
            method_display = payment.get_payment_method_display() if payment.payment_method else 'N/A'
            if payment.payment_method in ('ONLINE', 'POS'):
                ref_value = payment.transaction_no or 'N/A'
                dated_value = payment.payment_date.strftime('%d-%m-%Y') if payment.payment_date else 'N/A'
                bank_value = payment.payment_mode or 'N/A'
            elif payment.payment_method == 'DRAFT_CHEQUE':
                ref_value = payment.cheque_number or 'N/A'
                dated_value = payment.cheque_date.strftime('%d-%m-%Y') if payment.cheque_date else 'N/A'
                bank_value = payment.bank_name or 'N/A'
            elif payment.payment_method == 'NEFT_RTGS':
                ref_value = payment.neft_rtgs_ref_no or 'N/A'
                dated_value = payment.payment_date.strftime('%d-%m-%Y') if payment.payment_date else 'N/A'
                bank_value = payment.bank_name or 'N/A'
            else:
                ref_value = 'N/A'
                dated_value = 'N/A'
                bank_value = 'N/A'

            payment_table_data = [
                ['Mode of Payment', method_display],
                ['Transaction / Reference No.', ref_value],
                ['Dated', dated_value],
            ]
            payment_table = Table(payment_table_data, colWidths=[2.8 * inch, 4.2 * inch])
            payment_table.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(payment_table)
            elements.append(Spacer(1, 20))

            # ── Acknowledgement ────────────────────────────────────────────
            elements.append(Paragraph(
                "This receipt is issued as an acknowledgement of payment received.",
                normal_style
            ))
            elements.append(Spacer(1, 40))

            # ── Footer ─────────────────────────────────────────────────────
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#aaaaaa'), spaceAfter=8))
            elements.append(Paragraph("Powered by AssetKart", footer_style))

            doc.build(elements)
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="receipt-{payment.payment_id}.pdf"'
            return response

        except Exception as e:
            logger.error(f"❌ Error generating payment receipt: {str(e)}")
            return Response({'success': False, 'message': f'Failed to generate receipt: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)