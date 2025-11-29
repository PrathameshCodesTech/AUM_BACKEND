from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services.wallet_service import WalletService
from .serializers import WalletSerializer, TransactionSerializer,CreateInvestmentSerializer,InvestmentSerializer 
from .models import Wallet
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
    POST /api/investments/create/
    Create new investment
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CreateInvestmentSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            investment = InvestmentService.create_investment(
                user=request.user,
                property_obj=serializer.validated_data['property'],
                amount=serializer.validated_data['amount'],
                units_count=serializer.validated_data['units_count']
            )
            
            return Response({
                'success': True,
                'message': 'Investment created successfully. Pending admin approval.',
                'data': InvestmentSerializer(investment, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class MyInvestmentsView(APIView):
    """
    GET /api/investments/my-investments/
    Get user's investments
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        investments = InvestmentService.get_user_investments(request.user)
        serializer = InvestmentSerializer(investments, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class InvestmentDetailView(APIView):
    """
    GET /api/investments/{id}/details/
    Get investment details
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, investment_id):
        try:
            investment = InvestmentService.get_investment_detail(investment_id, request.user)
            serializer = InvestmentSerializer(investment, context={'request': request})
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Investment.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Investment not found'
            }, status=status.HTTP_404_NOT_FOUND)