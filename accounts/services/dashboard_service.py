# investments/services/dashboard_service.py
from django.db.models import Sum, Count, Q, Avg
from decimal import Decimal
from investments.models import Investment, Wallet, Transaction


class DashboardService:
    """Service for dashboard statistics"""
    
    @staticmethod
    def get_customer_stats(user):
        """Get customer dashboard statistics"""
        
        # Get wallet
        try:
            wallet = Wallet.objects.get(user=user)
            wallet_balance = wallet.balance
        except Wallet.DoesNotExist:
            wallet_balance = Decimal('0.00')
        
        # Investment stats
        investments = Investment.objects.filter(
            customer=user,
            is_deleted=False
        )
        
        investment_stats = investments.aggregate(
            total_invested=Sum('amount', filter=Q(status__in=['approved', 'active', 'completed'])),
            total_investments=Count('id', filter=Q(status__in=['approved', 'active', 'completed'])),
            pending_investments=Count('id', filter=Q(status='pending')),
            active_investments=Count('id', filter=Q(status='active')),
            completed_investments=Count('id', filter=Q(status='completed')),
            total_returns=Sum('actual_return_amount'),
            expected_returns=Sum('expected_return_amount'),
        )
        
        # Transaction stats
        transactions = Transaction.objects.filter(user=user)
        
        transaction_stats = transactions.aggregate(
            total_credits=Sum('amount', filter=Q(transaction_type='credit')),
            total_debits=Sum('amount', filter=Q(transaction_type='debit')),
            transaction_count=Count('id')
        )
        
        # Calculate portfolio value (invested + returns)
        total_invested = investment_stats['total_invested'] or Decimal('0.00')
        total_returns = investment_stats['total_returns'] or Decimal('0.00')
        portfolio_value = total_invested + total_returns
        
        return {
            'wallet': {
                'balance': wallet_balance,
            },
            'investments': {
                'total_invested': total_invested,
                'total_count': investment_stats['total_investments'] or 0,
                'pending_count': investment_stats['pending_investments'] or 0,
                'active_count': investment_stats['active_investments'] or 0,
                'completed_count': investment_stats['completed_investments'] or 0,
            },
            'returns': {
                'total_earned': total_returns,
                'expected_returns': investment_stats['expected_returns'] or Decimal('0.00'),
            },
            'portfolio': {
                'total_value': portfolio_value,
                'roi_percentage': ((total_returns / total_invested * 100) if total_invested > 0 else 0),
            },
            'transactions': {
                'total_credits': transaction_stats['total_credits'] or Decimal('0.00'),
                'total_debits': transaction_stats['total_debits'] or Decimal('0.00'),
                'count': transaction_stats['transaction_count'] or 0,
            }
        }
    
    @staticmethod
    def get_portfolio(user, status_filter=None):
        """Get user's investment portfolio"""
        
        queryset = Investment.objects.filter(
            customer=user,
            is_deleted=False
        ).select_related('property', 'transaction').prefetch_related('allocated_units__unit')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_recent_transactions(user, limit=10):
        """Get recent transactions"""
        
        return Transaction.objects.filter(
            user=user
        ).select_related('wallet').order_by('-created_at')[:limit]
    
    @staticmethod
    def get_investment_summary(user):
        """Get detailed investment summary by property"""
        
        from django.db.models import F
        
        investments = Investment.objects.filter(
            customer=user,
            is_deleted=False,
            status__in=['approved', 'active', 'completed']
        ).values(
            'property__name',
            'property__id'
        ).annotate(
            total_invested=Sum('amount'),
            total_units=Sum('units_purchased'),
            total_returns=Sum('actual_return_amount'),
            investment_count=Count('id'),
            avg_return=Avg('actual_return_amount')
        ).order_by('-total_invested')
        
        return list(investments)
    
    @staticmethod
    def get_monthly_investment_trend(user, months=6):
        """Get monthly investment trend"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models.functions import TruncMonth
        
        start_date = timezone.now() - timedelta(days=months * 30)
        
        trend = Investment.objects.filter(
            customer=user,
            is_deleted=False,
            status__in=['approved', 'active', 'completed'],
            created_at__gte=start_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total_invested=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        return list(trend)
