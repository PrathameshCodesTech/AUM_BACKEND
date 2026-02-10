# investments/models.py
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from accounts.models import User, TimestampedModel, SoftDeleteModel

# ============================================
# WALLET
# ============================================


class Wallet(TimestampedModel):
    """User wallet for managing funds"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='wallet')

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

        indexes = [
            models.Index(fields=['user']),
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
        ('pending_payment', 'Pending Payment Approval'),  # 🆕 NEW
        ('payment_approved', 'Payment Approved'),  # 🆕 NEW
        ('payment_rejected', 'Payment Rejected'),  # 🆕 NEW
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

    # Referred by (optional)
    # Referred by (optional)
    referred_by_cp = models.ForeignKey(
        'partners.ChannelPartner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_investments',
        help_text="CP who originally brought this customer (via CPCustomerRelation)"
    )

    # Referral code entered at investment time (NEW)
    referral_code_used = models.CharField(
        max_length=50,
        blank=True,
        help_text="CP referral code entered by customer at investment time (overrides referred_by_cp)"
    )

    # Investment details
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    units_purchased = models.IntegerField(validators=[MinValueValidator(1)])

    # Pricing snapshot (at time of investment)
    price_per_unit_at_investment = models.DecimalField(
        max_digits=15, decimal_places=2)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending_payment')

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


     # Payment Method Choices
    PAYMENT_METHOD_CHOICES = [
        ('ONLINE', 'Online'),
        ('POS', 'POS'),
        ('DRAFT_CHEQUE', 'Draft / Cheque'),
        ('NEFT_RTGS', 'NEFT / RTGS'),
    ]
    
    # Payment Status Choices
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    # Core payment info
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        help_text="Payment method used by customer"
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        help_text="Payment verification status"
    )
    
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was made by customer"
    )
    
    payment_notes = models.TextField(
        blank=True,
        help_text="Customer notes about payment"
    )
    
    # Payment approval
    payment_approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_approved_investments',
        help_text="Admin who approved the payment"
    )
    
    payment_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was approved by admin"
    )
    
    payment_rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for payment rejection"
    )
    
    # ONLINE / POS common fields
    payment_mode = models.CharField(
        max_length=50,
        blank=True,
        help_text="For ONLINE/POS: UPI, Card, NetBanking, Wallet, etc."
    )
    
    transaction_no = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Payment gateway transaction ID / POS transaction no."
    )
    
    # POS only
    pos_slip_image = models.ImageField(
        upload_to='investments/pos_slips/%Y/%m/',
        null=True,
        blank=True,
        help_text="Image of POS charge slip"
    )
    
    # DRAFT / CHEQUE fields
    cheque_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Cheque/Draft number"
    )
    
    cheque_date = models.DateField(
        null=True,
        blank=True,
        help_text="Cheque date"
    )
    
    bank_name = models.CharField(
        max_length=150,
        blank=True,null=True,
        help_text="Bank name for cheque"
    )
    
    ifsc_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Bank IFSC code"
    )
    
    branch_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Bank branch name"
    )
    
    cheque_image = models.ImageField(
        upload_to='investments/cheques/%Y/%m/',
        null=True,
        blank=True,
        help_text="Scanned cheque image"
    )

        # 🆕 Partial Payment Fields
    is_partial_payment = models.BooleanField(default=False)
    minimum_required_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Total investment amount (full price)"
    )
    due_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        help_text="Remaining amount to be paid"
    )
    payment_due_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Due date for remaining payment"
    )
    
    # NEFT / RTGS fields
    neft_rtgs_ref_no = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="NEFT / RTGS reference number"
    )

    class Meta:
        db_table = 'investments'
        indexes = [
            models.Index(fields=['investment_id']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['property', 'status']),
            models.Index(fields=['referred_by_cp']),
            models.Index(fields=['referral_code_used']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['payment_method']),  # 🆕 NEW
            models.Index(fields=['payment_status']),  # 🆕 NEW
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.investment_id} - {self.customer.username} - ₹{self.amount}"

    def get_commission_cp(self):
        """
        Get the CP who should receive commission for this investment
        Priority: referral_code_used > referred_by_cp > None
        """
        from django.utils import timezone
        
        # Priority 1: Check if customer entered referral code at investment time
        if self.referral_code_used:
            try:
                from partners.models import ChannelPartner
                cp = ChannelPartner.objects.get(
                    cp_code=self.referral_code_used,
                    is_active=True,
                    is_verified=True
                )
                return cp
            except ChannelPartner.DoesNotExist:
                pass  # Invalid code, fall through
        
        # Priority 2: Check if customer has pre-linked CP relationship
        if self.referred_by_cp:
            # Verify CP relationship is still valid (not expired)
            try:
                from partners.models import CPCustomerRelation
                relation = CPCustomerRelation.objects.get(
                    cp=self.referred_by_cp,
                    customer=self.customer,
                    is_active=True,
                    is_expired=False
                )
                # Check if relationship hasn't expired
                if relation.expiry_date >= timezone.now():
                    return self.referred_by_cp
            except CPCustomerRelation.DoesNotExist:
                pass
        
        # No valid CP found
        return None


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
