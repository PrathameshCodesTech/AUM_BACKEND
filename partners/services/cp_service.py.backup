# partners/services/cp_service.py
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from decimal import Decimal
from ..models import (
    ChannelPartner,
    CPCustomerRelation,
    CPPropertyAuthorization,
    CPLead,
    CPDocument
)
from accounts.models import User, Role
from accounts.services.permission_service import PermissionService
import random
import string


class CPService:
    """Service for Channel Partner business logic"""
    
    @staticmethod
    def generate_cp_code():
        """Generate unique CP code"""
        while True:
            # Format: CP + 6 random digits
            code = 'CP' + ''.join(random.choices(string.digits, k=6))
            if not ChannelPartner.objects.filter(cp_code=code).exists():
                return code
    
    @staticmethod
    @transaction.atomic
    def create_cp_application(user, application_data):
        """
        Create CP application
        
        Args:
            user: User applying to become CP
            application_data: Dict with CP details
        
        Returns:
            ChannelPartner instance
        """
        # Check if user already has CP profile
        if hasattr(user, 'cp_profile'):
            raise ValueError("User already has a CP profile")
        
        #! # Check if user has verified KYC
        # if not user.kyc_verified:
        #     raise ValueError("KYC verification required before applying")
        
        # Generate CP code
        cp_code = CPService.generate_cp_code()
        
        # Create CP profile
        cp = ChannelPartner.objects.create(
            user=user,
            cp_code=cp_code,
            onboarding_status='pending',
            is_active=False,
            is_verified=False,
            created_by=user,
            **application_data
        )
        
        return cp
    
    @staticmethod
    @transaction.atomic
    def approve_cp(cp, approved_by, approval_data=None):
        """
        Approve CP application
        
        Args:
            cp: ChannelPartner instance
            approved_by: Admin user approving
            approval_data: Optional dict with tier, start_date, etc.
        """
        approval_data = approval_data or {}
        
        # Update CP status
        cp.is_verified = True
        cp.is_active = True
        cp.onboarding_status = 'completed'
        cp.verified_at = timezone.now()
        cp.verified_by = approved_by
        
        # Set program dates
        if 'program_start_date' in approval_data:
            cp.program_start_date = approval_data['program_start_date']
        else:
            cp.program_start_date = timezone.now().date()
        
        # Set partner tier
        if 'partner_tier' in approval_data:
            cp.partner_tier = approval_data['partner_tier']
        
        cp.save()
        
        # Change user role to channel_partner
       # Change user role to channel_partner
        try:
            cp_role = Role.objects.get(slug='channel_partner')
            cp.user.role = cp_role
        except Role.DoesNotExist:
            pass

        # 👇 ADD THESE LINES (set CP flags on User model)
        cp.user.is_cp = True
        cp.user.cp_status = 'approved'
        cp.user.is_active_cp = True
        cp.user.save()  # 👈 Save with all fields

        # Clear permission cache
        try:
            PermissionService.clear_user_permission_cache(cp.user)
        except:
            pass
        
        return cp
    
    @staticmethod
    @transaction.atomic
    def reject_cp(cp, rejected_by, rejection_reason):
        """
        Reject CP application
        
        Args:
            cp: ChannelPartner instance
            rejected_by: Admin user rejecting
            rejection_reason: Reason for rejection
        """
        cp.onboarding_status = 'rejected'
        cp.is_verified = False
        cp.is_active = False
        cp.technical_setup_notes = f"REJECTED: {rejection_reason}"
        cp.save()
        
        return cp
    
    @staticmethod
    def get_cp_dashboard_stats(cp):
        """
        Get dashboard statistics for CP
        
        Args:
            cp: ChannelPartner instance
        
        Returns:
            Dict with dashboard stats
        """
        from investments.models import Investment
        from commissions.models import Commission
        
        # Date ranges
        today = timezone.now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Customer stats
        total_customers = cp.customers.filter(is_active=True).count()
        active_customers = cp.customers.filter(
            is_active=True,
            is_expired=False
        ).count()
        new_this_month = cp.customers.filter(
            referral_date__gte=month_start
        ).count()
        
        # Investment stats
        all_investments = Investment.objects.filter(
            referred_by_cp=cp,
            status__in=['approved', 'active', 'completed']
        )
        
        total_investment_value = all_investments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        total_investment_count = all_investments.count()
        
        month_investments = all_investments.filter(
            approved_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Commission stats
        all_commissions = Commission.objects.filter(cp=cp)
        
        total_commissions = all_commissions.aggregate(
            total=Sum('commission_amount')
        )['total'] or Decimal('0.00')
        
        pending_commissions = all_commissions.filter(
            status='pending'
        ).aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')
        
        paid_commissions = all_commissions.filter(
            status='paid'
        ).aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')
        
        month_commissions = all_commissions.filter(
            created_at__gte=month_start
        ).aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')
        
        # Lead stats
        total_leads = cp.leads.count()
        active_leads = cp.leads.filter(
            lead_status__in=['new', 'contacted', 'interested', 'negotiation']
        ).count()
        converted_leads = cp.leads.filter(lead_status='converted').count()
        
        # Target progress
        monthly_achievement = (month_investments / cp.monthly_target * 100) if cp.monthly_target > 0 else 0
        
        return {
            'cp_info': {
                'cp_code': cp.cp_code,
                'partner_tier': cp.partner_tier,
                'is_active': cp.is_active,
                'program_start_date': cp.program_start_date,
            },
            'customers': {
                'total': total_customers,
                'active': active_customers,
                'new_this_month': new_this_month,
            },
            'investments': {
                'total_value': str(total_investment_value),
                'total_count': total_investment_count,
                'this_month': str(month_investments),
            },
            'commissions': {
                'total_earned': str(total_commissions),
                'pending': str(pending_commissions),
                'paid': str(paid_commissions),
                'this_month': str(month_commissions),
            },
            'leads': {
                'total': total_leads,
                'active': active_leads,
                'converted': converted_leads,
            },
            'targets': {
                'monthly_target': str(cp.monthly_target),
                'monthly_achieved': str(month_investments),
                'achievement_percentage': float(monthly_achievement),
            },
            'performance': {
                'q1': str(cp.q1_performance),
                'q2': str(cp.q2_performance),
                'q3': str(cp.q3_performance),
                'q4': str(cp.q4_performance),
            }
        }
    
    @staticmethod
    def get_cp_customers(cp, filters=None):
        """
        Get CP's customers with optional filters
        
        Args:
            cp: ChannelPartner instance
            filters: Optional dict with filter params
        
        Returns:
            QuerySet of CPCustomerRelation
        """
        queryset = cp.customers.select_related('customer').all()
        
        if filters:
            # Filter by status
            if 'is_active' in filters:
                queryset = queryset.filter(is_active=filters['is_active'])
            
            if 'is_expired' in filters:
                queryset = queryset.filter(is_expired=filters['is_expired'])
            
            # Search by name/phone/email
            if 'search' in filters:
                search = filters['search']
                queryset = queryset.filter(
                    Q(customer__username__icontains=search) |
                    Q(customer__email__icontains=search) |
                    Q(customer__phone__icontains=search)
                )
        
        return queryset.order_by('-referral_date')
    
    @staticmethod
    def check_expired_relationships():
        """
        Cron job: Check and update expired CP-customer relationships
        
        Returns:
            Number of relationships expired
        """
        expired_count = 0
        
        # Get all active relationships with expiry in the past
        relations = CPCustomerRelation.objects.filter(
            is_active=True,
            is_expired=False,
            expiry_date__lt=timezone.now()
        )
        
        for relation in relations:
            relation.check_and_update_expiry()
            expired_count += 1
        
        return expired_count
    
    @staticmethod
    def convert_lead_to_customer(lead, user):
        """
        Convert lead to customer when they sign up
        
        Args:
            lead: CPLead instance
            user: User who signed up
        
        Returns:
            CPCustomerRelation instance
        """
        # Mark lead as converted
        lead.convert_to_customer(user)
        
        # Get the created relation
        relation = CPCustomerRelation.objects.get(
            cp=lead.cp,
            customer=user
        )
        
        return relation
    
    @staticmethod
    def update_quarterly_performance(cp, quarter, amount):
        """
        Update CP's quarterly performance
        
        Args:
            cp: ChannelPartner instance
            quarter: Quarter number (1-4)
            amount: Performance amount to add
        """
        if quarter == 1:
            cp.q1_performance += amount
        elif quarter == 2:
            cp.q2_performance += amount
        elif quarter == 3:
            cp.q3_performance += amount
        elif quarter == 4:
            cp.q4_performance += amount
        
        cp.save()
        
        return cp