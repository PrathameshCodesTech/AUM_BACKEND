from django.db import transaction
from decimal import Decimal
from ..models import Investment, Wallet
from properties.models import PropertyUnit
from commissions.services.commission_service import CommissionService

class InvestmentService:
    """Service for investment operations"""
    
    @staticmethod
    @transaction.atomic
    def create_investment(user, property_obj, amount, units_count):
        """Create new investment"""
        
        # 1. Check KYC
        if not hasattr(user, 'kyc') or user.kyc.status != 'verified':
            raise ValueError("KYC not verified. Please complete KYC first.")
        
        # 2. Check wallet balance
        wallet = Wallet.objects.select_for_update().get(user=user)
        if wallet.balance < amount:
            raise ValueError(f"Insufficient balance. Available: ₹{wallet.balance}")
        
        # 3. Allocate units
        available_units = PropertyUnit.objects.filter(
            property=property_obj,
            status='available'
        ).order_by('unit_number')[:units_count]
        
        if len(available_units) < units_count:
            raise ValueError("Requested units not available")
        
        # 4. Deduct from wallet
        from .wallet_service import WalletService
        WalletService.deduct_funds(user, amount, f"Investment in {property_obj.title}")
        
        # 5. Create investment
        investment = Investment.objects.create(
            wallet=wallet,
            property=property_obj,
            amount=amount,
            units_count=units_count,
            status='pending',
            expected_return=amount * (property_obj.target_irr / 100)
        )
        
        # 6. Mark units as booked
        for unit in available_units:
            unit.status = 'booked'
            unit.investment = investment
            unit.save()
        
        # 7. Calculate commission (if referred by CP)
        try:
            CommissionService.calculate_commission(investment)
        except:
            pass  # Commission optional
        
        return investment
    
    @staticmethod
    def get_user_investments(user):
        """Get all investments for user"""
        wallet = Wallet.objects.get(user=user)
        return Investment.objects.filter(wallet=wallet).order_by('-invested_at')
    
    @staticmethod
    def get_investment_detail(investment_id, user):
        """Get detailed investment information"""
        wallet = Wallet.objects.get(user=user)
        return Investment.objects.get(id=investment_id, wallet=wallet)
    
    @staticmethod
    @transaction.atomic
    def approve_investment(investment_id):
        """Admin approves investment"""
        investment = Investment.objects.select_for_update().get(id=investment_id)
        
        if investment.status != 'pending':
            raise ValueError("Investment already processed")
        
        investment.status = 'active'
        investment.save()
        
        # Mark units as sold
        investment.property.units.filter(investment=investment).update(status='sold')
        
        return investmentss