# commissions/models.py
from django.db import models
from decimal import Decimal
from accounts.models import User, TimestampedModel

# ============================================
# COMMISSION
# ============================================


class Commission(TimestampedModel):
    """Commission earned by Channel Partners"""

    COMMISSION_TYPE_CHOICES = [
        ('direct', 'Direct Commission'),
        ('override', 'Override Commission'),
        ('recurring', 'Recurring Commission'),
        ('bonus', 'Bonus'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    # Commission ID
    commission_id = models.CharField(max_length=100, unique=True)

    # Parties
    # Parties
    cp = models.ForeignKey('partners.ChannelPartner',
                           on_delete=models.CASCADE, related_name='commissions')

    # Source
    investment = models.ForeignKey(
        'investments.Investment', on_delete=models.CASCADE, related_name='commissions')

    # Commission details
    commission_type = models.CharField(
        max_length=20, choices=COMMISSION_TYPE_CHOICES)

    # Calculation
    base_amount = models.DecimalField(
        max_digits=15, decimal_places=2)  # Investment amount
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2)  # Percentage
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2)

    # TDS (Tax Deducted at Source)
    tds_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'))
    tds_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Net payable
    net_amount = models.DecimalField(max_digits=15, decimal_places=2)

    # Commission rule applied
    commission_rule = models.ForeignKey(
        'partners.CommissionRule', on_delete=models.SET_NULL, null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Approval
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_commissions')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Payment
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    transaction = models.ForeignKey(
        'investments.Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='commissions')

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'commissions'
        indexes = [
            models.Index(fields=['commission_id']),
            models.Index(fields=['cp', 'status']),
            models.Index(fields=['investment']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.commission_id} - {self.cp.user.username} - ₹{self.commission_amount}"


class CommissionPayout(TimestampedModel):
    """Batch payout to CP (can include multiple commissions)"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Payout ID
    payout_id = models.CharField(max_length=100, unique=True)

    cp = models.ForeignKey('partners.ChannelPartner',
                           on_delete=models.CASCADE, related_name='commission_payouts')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    tds_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=15, decimal_places=2)

    # Commissions included (many-to-many)
    commissions = models.ManyToManyField(Commission, related_name='payouts')

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Payment details
    # Bank transfer, UPI, etc.
    payment_mode = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Processed by
    processed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_commission_payouts')

    class Meta:
        db_table = 'commission_payouts'
        indexes = [
            models.Index(fields=['payout_id']),
            models.Index(fields=['cp', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.payout_id} - {self.cp.user.username} - ₹{self.net_amount}"
