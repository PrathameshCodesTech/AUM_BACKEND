# partners/models.py
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User, TimestampedModel, SoftDeleteModel

# ============================================
# CHANNEL PARTNER HIERARCHY
# ============================================


class ChannelPartner(TimestampedModel, SoftDeleteModel):
    """Channel Partner profile with hierarchy support"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='cp_profile')

    # Hierarchy - for sub-CP structure
    parent_cp = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_cps'
    )

    # CP Code (unique identifier)
    cp_code = models.CharField(max_length=50, unique=True)

    # CP Details
    company_name = models.CharField(max_length=255, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    gst_number = models.CharField(max_length=15, blank=True)

    # Bank details for commission payout
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=11, blank=True)
    account_holder_name = models.CharField(max_length=255, blank=True)

    # Targets & Performance
    monthly_target = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'))
    quarterly_target = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'))
    yearly_target = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_cps')

    # Onboarded by
    onboarded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='onboarded_cps')

    class Meta:
        db_table = 'channel_partners'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['parent_cp']),
            models.Index(fields=['cp_code']),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.cp_code})"

    def get_hierarchy_level(self):
        """Get CP hierarchy level (0=Master CP, 1=Sub-CP, etc.)"""
        level = 0
        current = self
        while current.parent_cp:
            level += 1
            current = current.parent_cp
        return level

    def get_all_sub_cps(self):
        """Get all sub-CPs recursively"""
        sub_cps = list(self.sub_cps.all())
        for sub_cp in list(sub_cps):
            sub_cps.extend(sub_cp.get_all_sub_cps())
        return sub_cps


class CPCustomerRelation(TimestampedModel):
    """Track which CP brought which customer"""

    cp = models.ForeignKey(
        ChannelPartner, on_delete=models.CASCADE, related_name='customers')
    customer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='referred_by_cp')

    # Referral tracking
    referral_code = models.CharField(max_length=50, blank=True)
    referral_date = models.DateTimeField(auto_now_add=True)

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'cp_customer_relations'
        unique_together = ('cp', 'customer')
        indexes = [
            models.Index(fields=['cp', 'is_active']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return f"{self.customer.username} referred by {self.cp.user.username}"


# ============================================
# COMMISSION CONFIGURATION
# ============================================
class CommissionRule(TimestampedModel):
    """Configurable commission rules"""

    COMMISSION_TYPE_CHOICES = [
        ('flat', 'Flat Percentage'),
        ('tiered', 'Tiered'),
        ('one_time', 'One-time'),
        ('recurring', 'Recurring'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    commission_type = models.CharField(
        max_length=20, choices=COMMISSION_TYPE_CHOICES)

    # For flat percentage
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(
            Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )

    # For tiered commission (store as JSON)
    # Example: [{"min": 0, "max": 1000000, "rate": 1.0}, {"min": 1000000, "max": 5000000, "rate": 1.5}]
    tiers = models.JSONField(default=list, blank=True)

    # Override commission for parent CP
    override_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(
            Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )

    # Applicability
    is_default = models.BooleanField(default=False)  # Default rule for org
    is_active = models.BooleanField(default=True)

    # Effective dates
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'commission_rules'
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class CPCommissionRule(models.Model):
    """Assign commission rules to specific CPs"""

    cp = models.ForeignKey(
        ChannelPartner, on_delete=models.CASCADE, related_name='commission_rules')
    commission_rule = models.ForeignKey(
        CommissionRule, on_delete=models.CASCADE)

    # Can apply to specific property or all
    property = models.ForeignKey(
        'properties.Property', on_delete=models.CASCADE, null=True, blank=True)

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cp_commission_rules'
