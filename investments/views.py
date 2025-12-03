from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services.wallet_service import WalletService
from .serializers import WalletSerializer, TransactionSerializer,CreateInvestmentSerializer,InvestmentSerializer 
from .models import Wallet, Investment  # 👈 ADD Investment HERE!
from decimal import Decimal  # ←
from .services.investment_service import InvestmentService

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
    Create new investment
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"📥 Received investment request: {request.data}")
        
        serializer = CreateInvestmentSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"❌ Serializer validation failed: {serializer.errors}")
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            logger.info(f"✅ Serializer valid, creating investment...")
            
            investment = InvestmentService.create_investment(
                user=request.user,
                property_obj=serializer.validated_data['property'],
                amount=serializer.validated_data['amount'],
                units_count=serializer.validated_data['units_count']
            )
            
            logger.info(f"✅ Investment service returned: {investment.investment_id}")
            
            # Serialize the response
            investment_data = InvestmentSerializer(investment, context={'request': request}).data
            
            logger.info(f"✅ Sending success response")
            
            return Response({
                'success': True,
                'message': 'Investment created successfully. Pending admin approval.',
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