from django.db import transaction
from decimal import Decimal
from ..models import Wallet, Transaction
from django.utils import timezone
import uuid


class WalletService:
    """Service for wallet operations"""
    
    @staticmethod
    def create_wallet(user):
        """Create wallet for user"""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={
                'balance': Decimal('0.00'),
                'ledger_balance': Decimal('0.00'),  # Changed from locked_balance
                'is_active': True,
                'is_blocked': False
            }
        )
        return wallet
    
    @staticmethod
    def get_balance(user):
        """Get wallet balance"""
        wallet = Wallet.objects.get(user=user)
        return {
            'balance': wallet.balance,
            'ledger_balance': wallet.ledger_balance,  # Changed from locked_balance
            'is_active': wallet.is_active,
            'is_blocked': wallet.is_blocked
        }
    
    @staticmethod
    @transaction.atomic
    def add_funds(user, amount, payment_method, payment_id=None):
        """Add funds to wallet"""
        wallet = Wallet.objects.select_for_update().get(user=user)
        
        # Store balance before
        balance_before = wallet.balance
        
        # Create transaction
        txn = Transaction.objects.create(
            transaction_id=payment_id or f'TXN{uuid.uuid4().hex[:12].upper()}',
            wallet=wallet,
            user=user,  # Add user field
            transaction_type='credit',
            purpose='deposit',  # Add purpose field
            amount=amount,
            balance_before=balance_before,  # Add balance tracking
            balance_after=balance_before + amount,
            status='pending',
            payment_method=payment_method,
            gateway_transaction_id=payment_id,
            description=f'Added funds via {payment_method}'
        )
        
        # Update balance
        wallet.balance += amount
        wallet.ledger_balance += amount  # Update ledger too
        wallet.save()
        
        # Mark transaction as completed
        txn.status = 'completed'
        txn.processed_at = timezone.now()
        txn.balance_after = wallet.balance
        txn.save()
        
        return txn
    
    @staticmethod
    @transaction.atomic
    def deduct_funds(user, amount, reason, purpose='withdrawal'):
        """Deduct funds from wallet"""
        wallet = Wallet.objects.select_for_update().get(user=user)
        
        if wallet.balance < amount:
            raise ValueError("Insufficient balance")
        
        balance_before = wallet.balance
        
        # Create transaction
        txn = Transaction.objects.create(
            transaction_id=f'TXN{uuid.uuid4().hex[:12].upper()}',
            wallet=wallet,
            user=user,
            transaction_type='debit',
            purpose=purpose,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_before - amount,
            status='completed',
            description=reason,
            processed_at=timezone.now()
        )
        
        # Update balance
        wallet.balance -= amount
        wallet.save()
        
        return txn
    
    @staticmethod
    def get_transactions(user, limit=20):
        """Get transaction history"""
        wallet = Wallet.objects.get(user=user)
        return Transaction.objects.filter(wallet=wallet).order_by('-created_at')[:limit]
