# commissions/services/commission_service.py
from django.db import transaction
from decimal import Decimal
from django.utils import timezone
from ..models import Commission
from partners.models import ChannelPartner, CommissionRule
import uuid


class CommissionService:
    """Service for commission calculations and management"""
    
    @staticmethod
    @transaction.atomic
    def calculate_and_create_commission(investment):
        """
        Calculate and create commission for investment
        """
        # Check if CP referral exists
        if not investment.referred_by_cp:
            return None
        
        cp = investment.referred_by_cp
        
        # Get commission rule for this CP
        commission_rule = CommissionService.get_commission_rule(cp, investment.property)
        
        if not commission_rule:
            return None
        
        # Calculate commission amount
        commission_amount = CommissionService.calculate_commission_amount(
            investment.amount,
            commission_rule
        )
        
        # Generate commission ID
        commission_id = f'COM{timezone.now().strftime("%Y%m%d")}{cp.id}{uuid.uuid4().hex[:6].upper()}'
        
        # Create commission record
        commission = Commission.objects.create(
            commission_id=commission_id,
            investment=investment,
            channel_partner=cp,
            customer=investment.customer,
            property=investment.property,
            commission_rule=commission_rule,
            investment_amount=investment.amount,
            commission_percentage=commission_rule.percentage,
            commission_amount=commission_amount,
            status='pending',
            tier_level=CommissionService.get_tier_level(investment.amount, commission_rule)
        )
        
        # If CP has parent, create override commission
        if cp.parent_cp:
            CommissionService.create_override_commission(
                investment=investment,
                parent_cp=cp.parent_cp,
                sub_cp=cp,
                commission_rule=commission_rule
            )
        
        return commission
    
    @staticmethod
    def get_commission_rule(cp, property_obj):
        """Get applicable commission rule for CP"""
        from partners.models import CPCommissionRule
        
        # Try property-specific rule first
        cp_rule = CPCommissionRule.objects.filter(
            cp=cp,
            property=property_obj,
            commission_rule__is_active=True
        ).first()
        
        if cp_rule:
            return cp_rule.commission_rule
        
        # Try CP's general rule
        cp_rule = CPCommissionRule.objects.filter(
            cp=cp,
            property__isnull=True,
            commission_rule__is_active=True
        ).first()
        
        if cp_rule:
            return cp_rule.commission_rule
        
        # Use default rule
        default_rule = CommissionRule.objects.filter(
            is_default=True,
            is_active=True
        ).first()
        
        return default_rule
    
    @staticmethod
    def calculate_commission_amount(investment_amount, commission_rule):
        """Calculate commission based on rule"""
        
        if commission_rule.commission_type == 'flat':
            # Flat percentage
            return (investment_amount * commission_rule.percentage) / 100
        
        elif commission_rule.commission_type == 'tiered':
            # Tiered commission
            if not commission_rule.tiers:
                return Decimal('0.00')
            
            for tier in commission_rule.tiers:
                min_amt = Decimal(str(tier.get('min', 0)))
                max_amt = Decimal(str(tier.get('max', float('inf'))))
                rate = Decimal(str(tier.get('rate', 0)))
                
                if min_amt <= investment_amount <= max_amt:
                    return (investment_amount * rate) / 100
            
            return Decimal('0.00')
        
        else:
            # Default flat percentage
            return (investment_amount * commission_rule.percentage) / 100
    
    @staticmethod
    def get_tier_level(investment_amount, commission_rule):
        """Get tier level for tiered commission"""
        
        if commission_rule.commission_type != 'tiered' or not commission_rule.tiers:
            return None
        
        for idx, tier in enumerate(commission_rule.tiers, 1):
            min_amt = Decimal(str(tier.get('min', 0)))
            max_amt = Decimal(str(tier.get('max', float('inf'))))
            
            if min_amt <= investment_amount <= max_amt:
                return idx
        
        return None
    
    @staticmethod
    @transaction.atomic
    def create_override_commission(investment, parent_cp, sub_cp, commission_rule):
        """Create override commission for parent CP"""
        
        if not commission_rule.override_percentage or commission_rule.override_percentage <= 0:
            return None
        
        # Calculate override amount
        override_amount = (investment.amount * commission_rule.override_percentage) / 100
        
        # Generate commission ID
        commission_id = f'COM{timezone.now().strftime("%Y%m%d")}{parent_cp.id}{uuid.uuid4().hex[:6].upper()}'
        
        # Create override commission
        commission = Commission.objects.create(
            commission_id=commission_id,
            investment=investment,
            channel_partner=parent_cp,
            customer=investment.customer,
            property=investment.property,
            commission_rule=commission_rule,
            investment_amount=investment.amount,
            commission_percentage=commission_rule.override_percentage,
            commission_amount=override_amount,
            status='pending',
            is_override=True,
            parent_commission=None  # Link to sub-CP commission if needed
        )
        
        return commission
    
    @staticmethod
    @transaction.atomic
    def approve_commission(commission, approved_by):
        """Approve commission for payout"""
        
        commission.status = 'approved'
        commission.approved_by = approved_by
        commission.approved_at = timezone.now()
        commission.save()
        
        return commission
    
    @staticmethod
    @transaction.atomic
    def pay_commission(commission, transaction_obj):
        """Mark commission as paid"""
        
        commission.status = 'paid'
        commission.paid_at = timezone.now()
        commission.transaction = transaction_obj
        commission.save()
        
        return commission
    
    @staticmethod
    def get_cp_commissions(cp, status=None):
        """Get all commissions for CP"""
        
        queryset = Commission.objects.filter(
            channel_partner=cp
        ).select_related('investment', 'property', 'customer')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_cp_total_earnings(cp):
        """Get total earnings for CP"""
        
        stats = Commission.objects.filter(
            channel_partner=cp
        ).aggregate(
            total_pending=Sum('commission_amount', filter=Q(status='pending')),
            total_approved=Sum('commission_amount', filter=Q(status='approved')),
            total_paid=Sum('commission_amount', filter=Q(status='paid')),
            total_earned=Sum('commission_amount')
        )
        
        return {
            'total_pending': stats['total_pending'] or Decimal('0.00'),
            'total_approved': stats['total_approved'] or Decimal('0.00'),
            'total_paid': stats['total_paid'] or Decimal('0.00'),
            'total_earned': stats['total_earned'] or Decimal('0.00'),
        }
