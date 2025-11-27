# investments/models.py
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from accounts.models import User, Organization, TimestampedModel, SoftDeleteModel

# ============================================
# WALLET
# ============================================


class Wallet(TimestampedModel):
    """User wallet for managing funds"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='wallet')
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='wallets')

    # Balance
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Ledger balance (includes pending transactions)
    ledger_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)

    class Meta:
        db_table = 'wallets'
        unique_together = ('user', 'organization')
        indexes = [
            models.Index(fields=['user', 'organization']),
        ]

    def __str__(self):
        return f"{self.user.username} - Wallet (₹{self.balance})"


class Transaction(TimestampedModel):
    """All financial transactions"""

    TRANSACTION_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    TRANSACTION_PURPOSE_CHOICES = [
        ('deposit', 'Wallet Deposit'),
        ('investment', 'Investment'),
        ('payout', 'Payout'),
        ('commission', 'Commission'),
        ('redemption', 'Redemption'),
        ('refund', 'Refund'),
        ('withdrawal', 'Withdrawal'),
        ('fee', 'Fee/Charge'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Transaction ID (unique)
    transaction_id = models.CharField(max_length=100, unique=True)

    # Parties
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='transactions')
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='transactions')

    # Transaction details
    transaction_type = models.CharField(
        max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    purpose = models.CharField(
        max_length=20, choices=TRANSACTION_PURPOSE_CHOICES)

    amount = models.DecimalField(max_digits=15, decimal_places=2)

    # Balances (for audit trail)
    balance_before = models.DecimalField(max_digits=15, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Payment gateway details
    payment_method = models.CharField(
        max_length=50, blank=True)  # UPI, Card, Net Banking
    # Razorpay, Stripe, etc.
    payment_gateway = models.CharField(max_length=50, blank=True)
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)

    # Reference (link to investment, payout, etc.)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.IntegerField(null=True, blank=True)

    # Notes
    description = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # Processed
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_transactions')

    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['wallet', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.user.username} - ₹{self.amount}"


# ============================================
# INVESTMENT
# ============================================
class Investment(TimestampedModel, SoftDeleteModel):
    """Customer investment in property"""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('redeemed', 'Redeemed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]

    # Investment ID (unique)
    investment_id = models.CharField(max_length=100, unique=True)

    # Parties
    customer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='investments')
    property = models.ForeignKey(
        'properties.Property', on_delete=models.CASCADE, related_name='investments')
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='investments')

    # Referred by (optional)
    referred_by_cp = models.ForeignKey(
        'partners.ChannelPartner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_investments'
    )

    # Investment details
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    units_purchased = models.IntegerField(validators=[MinValueValidator(1)])

    # Pricing snapshot (at time of investment)
    price_per_unit_at_investment = models.DecimalField(
        max_digits=15, decimal_places=2)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft')

    # Approval
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_investments')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Payment
    payment_completed = models.BooleanField(default=False)
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='investments')

    # Returns
    expected_return_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True)
    actual_return_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Dates
    investment_date = models.DateField(auto_now_add=True)
    maturity_date = models.DateField(null=True, blank=True)

    # Lock-in
    lock_in_end_date = models.DateField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'investments'
        indexes = [
            models.Index(fields=['investment_id']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['property', 'status']),
            models.Index(fields=['referred_by_cp']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.investment_id} - {self.customer.username} - ₹{self.amount}"


class InvestmentUnit(models.Model):
    """Track specific units allocated to investment"""

    investment = models.ForeignKey(
        Investment, on_delete=models.CASCADE, related_name='allocated_units')
    unit = models.ForeignKey('properties.PropertyUnit',
                             on_delete=models.CASCADE, related_name='investments')

    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'investment_units'
        unique_together = ('investment', 'unit')


# ============================================
# PAYOUT (Returns to customers)
# ============================================
class Payout(TimestampedModel):
    """Payouts/Returns distributed to customers"""

    PAYOUT_TYPE_CHOICES = [
        ('rental', 'Rental Income'),
        ('profit', 'Profit Share'),
        ('capital_appreciation', 'Capital Appreciation'),
        ('dividend', 'Dividend'),
        ('interest', 'Interest'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Payout ID
    payout_id = models.CharField(max_length=100, unique=True)

    # Parties
    investment = models.ForeignKey(
        Investment, on_delete=models.CASCADE, related_name='payouts')
    customer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='payouts')
    property = models.ForeignKey(
        'properties.Property', on_delete=models.CASCADE, related_name='payouts')
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='payouts')

    # Payout details
    payout_type = models.CharField(max_length=30, choices=PAYOUT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    # Period (for rental income)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Approval
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payouts')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Payment
    transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='payouts')
    paid_at = models.DateTimeField(null=True, blank=True)

    # Notes
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'payouts'
        indexes = [
            models.Index(fields=['payout_id']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['investment']),
            models.Index(fields=['property', 'payout_type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.payout_id} - {self.customer.username} - ₹{self.amount}"


# ============================================
# REDEMPTION REQUEST
# ============================================
class RedemptionRequest(TimestampedModel):
    """Customer request to redeem/exit investment"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Request ID
    request_id = models.CharField(max_length=100, unique=True)

    # Parties
    investment = models.ForeignKey(
        Investment, on_delete=models.CASCADE, related_name='redemption_requests')
    customer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='redemption_requests')
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='redemption_requests')

    # Redemption details
    units_to_redeem = models.IntegerField(validators=[MinValueValidator(1)])
    requested_amount = models.DecimalField(max_digits=15, decimal_places=2)

    # Actual redemption (after approval)
    approved_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Lock-in check
    is_within_lockin = models.BooleanField(default=False)
    penalty_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'))

    # Approval/Rejection
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_redemptions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Payment
    transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='redemptions')
    completed_at = models.DateTimeField(null=True, blank=True)

    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'redemption_requests'
        indexes = [
            models.Index(fields=['request_id']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['investment']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_id} - {self.customer.username}"
