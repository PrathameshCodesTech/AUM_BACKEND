# partners/models.py
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User, TimestampedModel, SoftDeleteModel
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers



# ============================================
# CHANNEL PARTNER PROFILE (UPDATED)
# ============================================

class ChannelPartner(TimestampedModel, SoftDeleteModel):
    """
    Channel Partner profile with hierarchy support and complete business fields
    """

    # ============================================
    # 1. BASIC RELATIONSHIP
    # ============================================
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='cp_profile'
    )

    # Hierarchy - for sub-CP structure
    parent_cp = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_cps',
        help_text="Parent Channel Partner (for sub-CP structure)"
    )

    # ============================================
    # 2. CHANNEL PARTNER IDENTITY
    # ============================================
    
    # CP Code (unique identifier)
    cp_code = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Auto-generated unique CP code (e.g., CP001234)"
    )

    # Agent Type
    AGENT_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('franchise', 'Franchise'),
    ]
    agent_type = models.CharField(
        max_length=20,
        choices=AGENT_TYPE_CHOICES,
        default='individual'
    )

    # Source of CP
    SOURCE_CHOICES = [
        ('direct', 'Direct'),
        ('referral', 'Referral'),
        ('website', 'Website'),
        ('advertisement', 'Advertisement'),
        ('event', 'Event'),
        ('other', 'Other'),
    ]
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='direct',
        help_text="How did this CP come to us?"
    )

    # Company Details
    company_name = models.CharField(max_length=255, blank=True)
    
    # Legal Documents
    pan_number = models.CharField(
        max_length=10, 
        blank=True,
        help_text="PAN Card Number"
    )
    gst_number = models.CharField(
        max_length=15, 
        blank=True,
        help_text="GST Number (GSTIN)"
    )
    rera_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="RERA Registration Number (Required for real estate)"
    )

    # Address
    business_address = models.TextField(
        blank=True,
        help_text="Business/Office address (separate from personal)"
    )

    # Bank details for commission payout
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=11, blank=True)
    account_holder_name = models.CharField(max_length=255, blank=True)

    # Commission Notes
    commission_notes = models.TextField(
        blank=True,
        help_text="Custom commission terms, notes (e.g., '5% on first 50L, 7% thereafter')"
    )

    # ============================================
    # 3. PROGRAM ENROLMENT
    # ============================================
    
    # Partner Tier
    PARTNER_TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    partner_tier = models.CharField(
        max_length=20,
        choices=PARTNER_TIER_CHOICES,
        default='bronze',
        help_text="Partner tier based on performance"
    )

    program_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when CP program started"
    )
    
    program_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when CP program ends (null = ongoing)"
    )

    # ============================================
    # 4. COMPLIANCE AND DOCUMENTS
    # ============================================
    
    regulatory_compliance_approved = models.BooleanField(
        default=False,
        help_text="Has regulatory compliance been approved by admin?"
    )

    # ============================================
    # 5. OPERATIONAL SETUP
    # ============================================
    
    # Onboarding Status
    ONBOARDING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    onboarding_status = models.CharField(
        max_length=20,
        choices=ONBOARDING_STATUS_CHOICES,
        default='pending',
        help_text="Current onboarding status"
    )

    dedicated_support_contact = models.CharField(
        max_length=255,
        blank=True,
        help_text="Dedicated support person name/phone for this CP"
    )

    technical_setup_notes = models.TextField(
        blank=True,
        help_text="Technical setup notes, onboarding instructions"
    )

    # ============================================
    # 6. TARGETS & PERFORMANCE
    # ============================================
    
    # Monthly/Quarterly/Yearly Targets
    monthly_target = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Monthly revenue target"
    )
    quarterly_target = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Quarterly revenue target"
    )
    yearly_target = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Yearly revenue target"
    )
    annual_revenue_target = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Annual revenue target (USD or INR)"
    )

    # Quarterly Performance Tracking
    q1_performance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Q1 (Jan-Mar) performance"
    )
    q2_performance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Q2 (Apr-Jun) performance"
    )
    q3_performance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Q3 (Jul-Sep) performance"
    )
    q4_performance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Q4 (Oct-Dec) performance"
    )

    # ============================================
    # 7. STATUS & VERIFICATION
    # ============================================
    
    is_active = models.BooleanField(
        default=False,
        help_text="Is CP active and can operate?"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Has admin verified and approved this CP?"
    )
    verified_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When was CP verified?"
    )
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_cps',
        help_text="Admin who verified this CP"
    )

    # Onboarded by
    onboarded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='onboarded_cps',
        help_text="Admin/User who onboarded this CP"
    )

    # ============================================
    # 8. SYSTEM AUDIT FIELDS
    # ============================================
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_cps',
        help_text="User who created this CP record"
    )
    
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_cps',
        help_text="User who last modified this CP record"
    )
    
    last_modified_date = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp"
    )
    
    # Note: created_at and updated_at inherited from TimestampedModel
    # Note: is_deleted, deleted_at, deleted_by inherited from SoftDeleteModel

    class Meta:
        db_table = 'channel_partners'
        verbose_name = 'Channel Partner'
        verbose_name_plural = 'Channel Partners'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['parent_cp']),
            models.Index(fields=['cp_code']),
            models.Index(fields=['onboarding_status']),
            models.Index(fields=['partner_tier']),
            models.Index(fields=['agent_type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.cp_code})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

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

    def is_program_active(self):
        """Check if CP program is currently active"""
        if not self.program_start_date:
            return False
        
        today = timezone.now().date()
        
        # Check start date
        if today < self.program_start_date:
            return False
        
        # Check end date (if set)
        if self.program_end_date and today > self.program_end_date:
            return False
        
        return True


# ============================================
# CP-CUSTOMER RELATIONSHIP (UPDATED WITH EXPIRY)
# ============================================

class CPCustomerRelation(TimestampedModel):
    """
    Track which CP brought which customer
    NOW WITH EXPIRY - Relationship is time-bound
    """

    cp = models.ForeignKey(
        ChannelPartner, 
        on_delete=models.CASCADE, 
        related_name='customers'
    )
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='referred_by_cp'
    )

    # Referral tracking
    referral_code = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Referral code used by customer"
    )
    referral_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When customer was referred"
    )

    # ============================================
    # TIME-BOUND RELATIONSHIP (NEW)
    # ============================================
    
    validity_days = models.IntegerField(
        default=90,
        help_text="Number of days this relationship is valid"
    )
    
    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when this relationship expires"
    )
    
    is_expired = models.BooleanField(
        default=False,
        help_text="Has this relationship expired?"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Is this relationship currently active?"
    )

    class Meta:
        db_table = 'cp_customer_relations'
        verbose_name = 'CP-Customer Relation'
        verbose_name_plural = 'CP-Customer Relations'
        unique_together = ('cp', 'customer')
        indexes = [
            models.Index(fields=['cp', 'is_active']),
            models.Index(fields=['customer']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['is_expired']),
        ]
        ordering = ['-referral_date']

    def __str__(self):
        return f"{self.customer.username} → {self.cp.cp_code}"

    def save(self, *args, **kwargs):
        # Auto-calculate expiry_date if not set
        if self.expiry_date is None:
            self.expiry_date = timezone.now() + timedelta(days=self.validity_days)

        # Auto-update is_expired based on current date
        if self.expiry_date and timezone.now() > self.expiry_date:
            self.is_expired = True
            self.is_active = False
        
        super().save(*args, **kwargs)

    def check_and_update_expiry(self):
        """
        Check if relationship has expired and update status
        Call this in cron jobs or before commission calculations
        """
        if timezone.now() > self.expiry_date:
            self.is_expired = True
            self.is_active = False
            self.save()
            return True
        return False

    def extend_validity(self, additional_days):
        """
        Extend the validity period
        Used when CP performance is good or admin manually extends
        """
        self.expiry_date = self.expiry_date + timedelta(days=additional_days)
        self.is_expired = False
        self.is_active = True
        self.save()


# ============================================
# PROPERTY AUTHORIZATION (NEW MODEL)
# ============================================

class CPPropertyAuthorization(TimestampedModel):
    """
    Defines which properties a CP is authorized to sell
    Each CP can only share links for authorized properties
    """

    cp = models.ForeignKey(
        ChannelPartner,
        on_delete=models.CASCADE,
        related_name='property_authorizations'
    )
    
    property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        related_name='cp_authorizations'
    )

    # Authorization Status
    is_authorized = models.BooleanField(
        default=True,
        help_text="Is CP authorized to sell this property?"
    )

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revoked', 'Revoked'),
    ]
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='approved'
    )

    # Referral Link (auto-generated)
    referral_link = models.CharField(
        max_length=500,
        blank=True,
        help_text="Unique referral link for this CP + Property combination"
    )

    # Brochure/Marketing Materials
    custom_brochure = models.FileField(
        upload_to='cp_brochures/',
        null=True,
        blank=True,
        help_text="Custom brochure for this CP (optional)"
    )

    # Audit Fields
    authorized_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authorized_cp_properties',
        help_text="Admin who authorized this"
    )
    
    authorized_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When was authorization granted?"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Admin notes about this authorization"
    )

    class Meta:
        db_table = 'cp_property_authorizations'
        verbose_name = 'CP Property Authorization'
        verbose_name_plural = 'CP Property Authorizations'
        unique_together = ('cp', 'property')
        indexes = [
            models.Index(fields=['cp', 'is_authorized']),
            models.Index(fields=['property', 'is_authorized']),
            models.Index(fields=['approval_status']),
        ]
        ordering = ['-authorized_at']

    def __str__(self):
        return f"{self.cp.cp_code} → {self.property.name}"

    def generate_referral_link(self):
        """
        Generate unique referral link for this CP + Property
        Format: https://assetkart.com/property/{property_id}?ref={cp_code}
        """
        if not self.referral_link:
            base_url = "https://assetkart.com"  # Replace with actual domain
            self.referral_link = f"{base_url}/property/{self.property.id}?ref={self.cp.cp_code}"
            self.save()
        return self.referral_link


# ============================================
# LEAD MANAGEMENT (NEW MODEL)
# ============================================

class CPLead(TimestampedModel, SoftDeleteModel):
    """
    Leads added by Channel Partners
    Track potential customers before they sign up
    """

    cp = models.ForeignKey(
        ChannelPartner,
        on_delete=models.CASCADE,
        related_name='leads'
    )

    # Lead Information
    customer_name = models.CharField(
        max_length=255,
        help_text="Name of potential customer"
    )
    
    phone = models.CharField(
        max_length=15,
        help_text="Phone number of lead"
    )
    
    email = models.EmailField(
        blank=True,
        help_text="Email of lead (optional)"
    )

    # Interested Property
    interested_property = models.ForeignKey(
        'properties.Property',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cp_leads',
        help_text="Which property is lead interested in?"
    )

    # Lead Status
    LEAD_STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('interested', 'Interested'),
        ('site_visit_scheduled', 'Site Visit Scheduled'),
        ('site_visit_done', 'Site Visit Done'),
        ('negotiation', 'Negotiation'),
        ('converted', 'Converted'),
        ('lost', 'Lost'),
        ('not_interested', 'Not Interested'),
    ]
    lead_status = models.CharField(
        max_length=30,
        choices=LEAD_STATUS_CHOICES,
        default='new'
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="CP notes about this lead"
    )

    # Follow-up
    next_follow_up_date = models.DateField(
        null=True,
        blank=True,
        help_text="When to follow up next?"
    )

    # Conversion Tracking
    converted_customer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='converted_from_lead',
        help_text="User account created when lead converted"
    )
    
    converted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When did lead convert to customer?"
    )

    # Source tracking
    lead_source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Where did this lead come from? (Facebook, WhatsApp, etc.)"
    )

    class Meta:
        db_table = 'cp_leads'
        verbose_name = 'CP Lead'
        verbose_name_plural = 'CP Leads'
        indexes = [
            models.Index(fields=['cp', 'lead_status']),
            models.Index(fields=['phone']),
            models.Index(fields=['lead_status']),
            models.Index(fields=['converted_customer']),
            models.Index(fields=['next_follow_up_date']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} ({self.phone}) - {self.lead_status}"

    def convert_to_customer(self, user):
        """
        Mark lead as converted when customer signs up
        """
        self.lead_status = 'converted'
        self.converted_customer = user
        self.converted_at = timezone.now()
        self.save()

        # Auto-create CP-Customer relationship
        CPCustomerRelation.objects.get_or_create(
            cp=self.cp,
            customer=user,
            defaults={
                'referral_code': self.cp.cp_code,
                'is_active': True,
            }
        )


# ============================================
# CP INVITE SYSTEM (NEW MODEL)
# ============================================

class CPInvite(TimestampedModel):
    """
    CP can send personalized invite links to potential customers
    When customer signs up via invite, auto-link to CP
    """

    cp = models.ForeignKey(
        ChannelPartner,
        on_delete=models.CASCADE,
        related_name='invites'
    )

    # Invite Code (unique)
    invite_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique invite code (auto-generated)"
    )

    # Who was invited?
    phone = models.CharField(
        max_length=15,
        help_text="Phone number invited"
    )
    
    email = models.EmailField(
        blank=True,
        help_text="Email invited (optional)"
    )
    
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of person invited (optional)"
    )

    # Invite Status
    is_used = models.BooleanField(
        default=False,
        help_text="Has invite been used?"
    )
    
    used_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invites',
        help_text="User who used this invite"
    )
    
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was invite used?"
    )

    # Expiry
    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Invite expires after this date"
    )
    
    is_expired = models.BooleanField(
        default=False,
        help_text="Has invite expired?"
    )

    # Message/Notes
    message = models.TextField(
        blank=True,
        help_text="Personalized message from CP to invitee"
    )

    class Meta:
        db_table = 'cp_invites'
        verbose_name = 'CP Invite'
        verbose_name_plural = 'CP Invites'
        indexes = [
            models.Index(fields=['cp', 'is_used']),
            models.Index(fields=['invite_code']),
            models.Index(fields=['phone']),
            models.Index(fields=['is_expired']),
            models.Index(fields=['expiry_date']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.cp.cp_code} → {self.phone} ({self.invite_code})"

    def save(self, *args, **kwargs):
        # Auto-generate invite code if not set
        if not self.invite_code:
            import uuid
            self.invite_code = f"INV{uuid.uuid4().hex[:8].upper()}"

        # Auto-set expiry if not set (default 30 days)
        if self.expiry_date is None:
            self.expiry_date = timezone.now() + timedelta(days=30)
        
        # Check if expired
        if self.expiry_date and timezone.now() > self.expiry_date:
            self.is_expired = True
        
        super().save(*args, **kwargs)

    def mark_as_used(self, user):
        """Mark invite as used when customer signs up"""
        self.is_used = True
        self.used_by = user
        self.used_at = timezone.now()
        self.save()

        # Auto-create CP-Customer relationship
        CPCustomerRelation.objects.get_or_create(
            cp=self.cp,
            customer=user,
            defaults={
                'referral_code': self.invite_code,
                'is_active': True,
            }
        )


# ============================================
# CP DOCUMENTS (NEW MODEL)
# ============================================

class CPDocument(TimestampedModel, SoftDeleteModel):
    """
    Document uploads for Channel Partner compliance
    PAN, RERA, GST, Business License, etc.
    """

    cp = models.ForeignKey(
        ChannelPartner,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    # Document Type
    DOCUMENT_TYPE_CHOICES = [
        ('pan_card', 'PAN Card'),
        ('rera_certificate', 'RERA Certificate'),
        ('gst_certificate', 'GST Certificate'),
        ('business_license', 'Business License'),
        ('bank_proof', 'Bank Account Proof'),
        ('address_proof', 'Address Proof'),
        ('id_proof', 'ID Proof'),
        ('agreement', 'Agreement'),
        ('other', 'Other'),
    ]
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES
    )

    # Document Details
    description = models.TextField(
        blank=True,
        help_text="Description of document"
    )

    file = models.FileField(
        upload_to='cp_documents/%Y/%m/',
        help_text="Upload document file"
    )

    # Verification Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Verification Audit
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_cp_documents',
        help_text="Admin who verified this document"
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was document verified?"
    )

    # Rejection reason
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection (if rejected)"
    )

    class Meta:
        db_table = 'cp_documents'
        verbose_name = 'CP Document'
        verbose_name_plural = 'CP Documents'
        indexes = [
            models.Index(fields=['cp', 'document_type']),
            models.Index(fields=['status']),
            models.Index(fields=['document_type']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.cp.cp_code} - {self.get_document_type_display()}"

    def approve_document(self, admin_user):
        """Approve document"""
        self.status = 'approved'
        self.verified_by = admin_user
        self.verified_at = timezone.now()
        self.save()

    def reject_document(self, admin_user, reason):
        """Reject document with reason"""
        self.status = 'rejected'
        self.verified_by = admin_user
        self.verified_at = timezone.now()
        self.rejection_reason = reason
        self.save()


# ============================================
# COMMISSION RULES (EXISTING - NO CHANGES)
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
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Effective dates
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'commission_rules'
        verbose_name = 'Commission Rule'
        verbose_name_plural = 'Commission Rules'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class CPCommissionRule(TimestampedModel):
    """Assign commission rules to specific CPs"""

    cp = models.ForeignKey(
        ChannelPartner, 
        on_delete=models.CASCADE, 
        related_name='commission_rules'
    )
    commission_rule = models.ForeignKey(
        CommissionRule, 
        on_delete=models.CASCADE
    )

    # Can apply to specific property or all
    property = models.ForeignKey(
        'properties.Property', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Specific property (null = applies to all properties)"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_commission_rules',
        help_text="Admin who assigned this rule"
    )

    class Meta:
        db_table = 'cp_commission_rules'
        verbose_name = 'CP Commission Rule'
        verbose_name_plural = 'CP Commission Rules'
        unique_together = ('cp', 'commission_rule', 'property')
        indexes = [
            models.Index(fields=['cp']),
            models.Index(fields=['property']),
        ]

    def __str__(self):
        if self.property:
            return f"{self.cp.cp_code} → {self.commission_rule.name} (Property: {self.property.name})"
        return f"{self.cp.cp_code} → {self.commission_rule.name} (All Properties)"


# ============================================
# ADMIN CP CREATION SERIALIZER (NEW)
# ============================================

class AdminCreateCPSerializer(serializers.ModelSerializer):
    """
    Admin manually creates CP on behalf
    Uses ChannelPartner model + creates user account
    """
    
    # ============================================
    # NESTED USER FIELDS (Write-Only)
    # ============================================
    first_name = serializers.CharField(max_length=150, write_only=True, required=True)
    last_name = serializers.CharField(max_length=150, write_only=True, required=True)
    email = serializers.EmailField(write_only=True, required=True)
    phone = serializers.CharField(max_length=15, write_only=True, required=True)
    password = serializers.CharField(
        write_only=True, 
        required=False, 
        allow_blank=True,
        help_text="Auto-generated if not provided"
    )
    
    # ============================================
    # PROPERTY AUTHORIZATION (Optional)
    # ============================================
    property_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="List of property IDs to authorize"
    )
    
    # ============================================
    # AUTO-APPROVE FLAG
    # ============================================
    auto_approve = serializers.BooleanField(
        write_only=True,
        default=True,
        help_text="Auto-approve and activate CP"
    )
    
    class Meta:
        model = ChannelPartner
        fields = [
            # User fields (write-only)
            'first_name', 'last_name', 'email', 'phone', 'password',
            
            # CP Identity
            'agent_type', 'source', 'company_name',
            'pan_number', 'gst_number', 'rera_number',
            'business_address',
            
            # Program Enrolment
            'partner_tier', 'program_start_date', 'program_end_date',
            
            # Compliance
            'regulatory_compliance_approved',
            
            # Operational Setup
            'dedicated_support_contact', 'technical_setup_notes',
            
            # Targets & Performance
            'monthly_target', 'quarterly_target', 'yearly_target',
            
            # Bank Details
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
            
            # Commission
            'commission_notes',
            
            # Property Authorization
            'property_ids',
            
            # Auto-approve
            'auto_approve',
            
            # Read-only (auto-generated)
            'id', 'cp_code', 'user', 'onboarding_status', 
            'is_verified', 'is_active', 'created_at',
        ]
        read_only_fields = [
            'id', 'cp_code', 'user', 'onboarding_status', 
            'is_verified', 'is_active', 'created_at'
        ]
    
    def validate_phone(self, value):
        """Validate and normalize phone number"""
        import re
        
        # Remove any spaces, dashes, or other non-digit characters except +
        phone = re.sub(r'[^\d+]', '', value.strip())
        
        # Remove + temporarily for digit counting
        digits_only = phone.replace('+', '')
        
        # Handle different formats
        if len(digits_only) == 10:
            phone = f'+91{digits_only}'
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            phone = f'+{digits_only}'
        elif len(digits_only) == 11 and digits_only.startswith('0'):
            phone = f'+91{digits_only[1:]}'
        elif not phone.startswith('+91'):
            phone = f'+91{phone}'
        
        # Final validation
        if not re.match(r'^\+91\d{10}$', phone):
            raise serializers.ValidationError(
                "Phone must be in format +91XXXXXXXXXX (10 digits)"
            )
        
        # Check if phone already exists
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError(
                "Phone number already registered"
            )
        
        return phone
    
    def validate_email(self, value):
        """Check if email already exists"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_pan_number(self, value):
        """Validate PAN format"""
        if value:
            value = value.strip().upper()
            if len(value) != 10:
                raise serializers.ValidationError("PAN must be 10 characters")
            # Basic PAN format: ABCDE1234F
            import re
            if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', value):
                raise serializers.ValidationError("Invalid PAN format")
        return value
    
    def validate_gst_number(self, value):
        """Validate GST format"""
        if value:
            value = value.strip().upper()
            if len(value) != 15:
                raise serializers.ValidationError("GST must be 15 characters")
        return value
    
    def validate_ifsc_code(self, value):
        """Validate IFSC format"""
        if value:
            value = value.strip().upper()
            if len(value) != 11:
                raise serializers.ValidationError("IFSC must be 11 characters")
            # Basic IFSC format: ABCD0123456
            import re
            if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', value):
                raise serializers.ValidationError("Invalid IFSC format")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # If company type, require company name and GST
        if data.get('agent_type') == 'company':
            if not data.get('company_name'):
                raise serializers.ValidationError({
                    'company_name': 'Company name required for company type'
                })
        
        # If bank details provided, all fields required
        bank_fields = ['bank_name', 'account_number', 'ifsc_code', 'account_holder_name']
        bank_values = [data.get(field) for field in bank_fields]
        
        if any(bank_values):  # If any bank field is filled
            if not all(bank_values):  # All must be filled
                raise serializers.ValidationError({
                    'bank_details': 'All bank details required if providing bank information'
                })
        
        return data