# commissions/services/commission_service.py
from django.db import transaction
from django.db.models import Sum, Q
from decimal import Decimal
from django.utils import timezone
from ..models import Commission
from partners.models import ChannelPartner, CommissionRule, CPCommissionRule
import uuid
import logging

logger = logging.getLogger(__name__)


class CommissionService:
    """Service for commission calculations and management"""
    
    @staticmethod
    @transaction.atomic
    def calculate_commission(investment):
        """
        Calculate and create commission for investment
        
        Args:
            investment: Investment instance
        
        Returns:
            Commission instance or None
        """
        # Get CP who should receive commission (uses priority logic)
        cp = investment.get_commission_cp()
        
        if not cp:
            logger.info(f"No CP linked to investment {investment.investment_id}")
            return None
        
        # Check if commission already exists
        existing = Commission.objects.filter(
            investment=investment,
            cp=cp,
            is_override=False
        ).first()
        
        if existing:
            logger.warning(f"Commission already exists for investment {investment.investment_id}")
            return existing
        
        # Get commission rule
        commission_rule = CommissionService._get_commission_rule(cp, investment.property)
        
        if not commission_rule:
            logger.warning(f"No commission rule found for CP {cp.cp_code}")
            return None
        
        # Calculate commission amount
        commission_amount = CommissionService._calculate_amount(
            investment.amount,
            commission_rule
        )
        
        if commission_amount <= 0:
            logger.warning(f"Commission amount is zero for investment {investment.investment_id}")
            return None
        
        # Calculate TDS (Tax Deducted at Source)
        tds_percentage = Decimal('10.00')  # Default 10% TDS
        tds_amount = (commission_amount * tds_percentage) / Decimal('100')
        net_amount = commission_amount - tds_amount
        
        # Generate commission ID
        commission_id = f"COM-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create commission record
        commission = Commission.objects.create(
            commission_id=commission_id,
            cp=cp,
            investment=investment,
            commission_type='direct',
            base_amount=investment.amount,
            commission_rate=commission_rule.percentage,
            commission_amount=commission_amount,
            tds_percentage=tds_percentage,
            tds_amount=tds_amount,
            net_amount=net_amount,
            commission_rule=commission_rule,
            status='pending',
            is_override=False
        )
        
        logger.info(f"✅ Commission created: {commission_id} for CP {cp.cp_code}, Amount: ₹{commission_amount}")
        
        # Handle parent CP override commission
        if cp.parent_cp and commission_rule.override_percentage > 0:
            CommissionService._calculate_parent_commission(
                parent_cp=cp.parent_cp,
                investment=investment,
                base_commission=commission,
                override_percentage=commission_rule.override_percentage
            )
        
        return commission
    
    @staticmethod
    def _get_commission_rule(cp, property_obj):
        """
        Get applicable commission rule for CP + Property
        
        Priority:
        1. Property-specific rule
        2. CP's default rule
        3. No rule
        """
        try:
            # Try property-specific rule first
            cp_rule = CPCommissionRule.objects.select_related('commission_rule').filter(
                cp=cp,
                property=property_obj,
                commission_rule__is_active=True
            ).first()
            
            if cp_rule:
                logger.info(f"Using property-specific rule for CP {cp.cp_code}")
                return cp_rule.commission_rule
        except Exception as e:
            logger.error(f"Error fetching property-specific rule: {e}")
        
        try:
            # Try CP's default rule (property=NULL)
            cp_rule = CPCommissionRule.objects.select_related('commission_rule').filter(
                cp=cp,
                property__isnull=True,
                commission_rule__is_active=True
            ).first()
            
            if cp_rule:
                logger.info(f"Using default rule for CP {cp.cp_code}")
                return cp_rule.commission_rule
        except Exception as e:
            logger.error(f"Error fetching default rule: {e}")
        
        logger.warning(f"No commission rule found for CP {cp.cp_code}")
        return None
    
    @staticmethod
    def _calculate_amount(investment_amount, commission_rule):
        """
        Calculate commission amount based on rule type
        
        Args:
            investment_amount: Investment amount (Decimal)
            commission_rule: CommissionRule instance
        
        Returns:
            Commission amount (Decimal)
        """
        investment_amount = Decimal(str(investment_amount))
        
        if commission_rule.commission_type == 'flat':
            # Flat percentage
            rate = Decimal(str(commission_rule.percentage))
            return (investment_amount * rate) / Decimal('100')
        
        elif commission_rule.commission_type == 'tiered':
            # Tiered commission
            if not commission_rule.tiers:
                return Decimal('0.00')
            
            for tier in commission_rule.tiers:
                min_amt = Decimal(str(tier.get('min', 0)))
                max_amt = Decimal(str(tier.get('max', float('inf'))))
                rate = Decimal(str(tier.get('rate', 0)))
                
                if min_amt <= investment_amount <= max_amt:
                    return (investment_amount * rate) / Decimal('100')
            
            # If amount exceeds all tiers, use last tier rate
            if commission_rule.tiers:
                last_tier = commission_rule.tiers[-1]
                rate = Decimal(str(last_tier.get('rate', 0)))
                return (investment_amount * rate) / Decimal('100')
            
            return Decimal('0.00')
        
        elif commission_rule.commission_type == 'one_time':
            # One-time flat amount (stored in percentage field)
            return Decimal(str(commission_rule.percentage))
        
        else:
            # Default: flat percentage
            rate = Decimal(str(commission_rule.percentage))
            return (investment_amount * rate) / Decimal('100')
    
    @staticmethod
    def _calculate_parent_commission(parent_cp, investment, base_commission, override_percentage):
        """
        Calculate override commission for parent CP
        
        Args:
            parent_cp: Parent ChannelPartner instance
            investment: Investment instance
            base_commission: Base commission (for sub-CP)
            override_percentage: Override percentage (Decimal)
        """
        # Calculate override amount
        override_amount = (base_commission.commission_amount * Decimal(str(override_percentage))) / Decimal('100')
        
        if override_amount <= 0:
            return None
        
        # Calculate TDS
        tds_percentage = Decimal('10.00')
        tds_amount = (override_amount * tds_percentage) / Decimal('100')
        net_amount = override_amount - tds_amount
        
        # Generate commission ID
        commission_id = f"COM-OVR-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create override commission
        override_commission = Commission.objects.create(
            commission_id=commission_id,
            cp=parent_cp,
            investment=investment,
            commission_type='override',
            base_amount=investment.amount,
            commission_rate=override_percentage,
            commission_amount=override_amount,
            tds_percentage=tds_percentage,
            tds_amount=tds_amount,
            net_amount=net_amount,
            commission_rule=base_commission.commission_rule,
            status='pending',
            is_override=True,
            parent_commission=base_commission
        )
        
        logger.info(f"✅ Override commission created: {commission_id} for parent CP {parent_cp.cp_code}, Amount: ₹{override_amount}")
        
        return override_commission
    
    @staticmethod
    @transaction.atomic
    def approve_commission(commission, approved_by):
        """
        Approve commission (when investment is approved)
        
        Args:
            commission: Commission instance
            approved_by: User approving
        """
        commission.status = 'approved'
        commission.approved_by = approved_by
        commission.approved_at = timezone.now()
        commission.save()
        
        logger.info(f"Commission {commission.commission_id} approved by {approved_by.username}")
        
        return commission
    
    @staticmethod
    @transaction.atomic
    def process_payout(commission, processed_by, payment_reference=''):
        """
        Process commission payout (mark as paid)
        
        Args:
            commission: Commission instance
            processed_by: User processing payout
            payment_reference: Payment reference/transaction ID
        """
        commission.status = 'paid'
        commission.paid_at = timezone.now()
        commission.paid_by = processed_by
        commission.payment_reference = payment_reference
        commission.save()
        
        logger.info(f"Commission {commission.commission_id} paid by {processed_by.username}")
        
        return commission
    
    @staticmethod
    def get_cp_commissions(cp, status=None):
        """
        Get all commissions for CP
        
        Args:
            cp: ChannelPartner instance
            status: Optional status filter
        
        Returns:
            QuerySet of Commission objects
        """
        queryset = Commission.objects.filter(
            cp=cp
        ).select_related('investment', 'investment__property', 'investment__customer')
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_cp_earnings_summary(cp):
        """
        Get earnings summary for CP
        
        Args:
            cp: ChannelPartner instance
        
        Returns:
            Dict with earnings breakdown
        """
        stats = Commission.objects.filter(cp=cp).aggregate(
            total_pending=Sum('net_amount', filter=Q(status='pending')),
            total_approved=Sum('net_amount', filter=Q(status='approved')),
            total_paid=Sum('net_amount', filter=Q(status='paid')),
            total_earned=Sum('net_amount')
        )
        
        return {
            'total_pending': stats['total_pending'] or Decimal('0.00'),
            'total_approved': stats['total_approved'] or Decimal('0.00'),
            'total_paid': stats['total_paid'] or Decimal('0.00'),
            'total_earned': stats['total_earned'] or Decimal('0.00'),
        }