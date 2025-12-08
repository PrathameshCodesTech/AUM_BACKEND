# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError

# ============================================
# BASE ABSTRACT MODELS
# ============================================


class TimestampedModel(models.Model):
    """Base model with timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Soft delete support - never hard delete financial records"""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted'
    )

    class Meta:
        abstract = True


# ============================================
# USER MODEL (Simplified - Single Tenant)
# ============================================
class User(AbstractUser, TimestampedModel):
    """
    Extended user model for AssetKart
    Each user has ONE role directly
    """

    # Basic info
    phone = models.CharField(max_length=15, blank=True, unique=True)
    phone_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # Role (direct relationship)
    role = models.ForeignKey(
        'Role',
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
        help_text="User's role in AssetKart"
    )

    # Personal details
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        blank=True
    )

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)

    # KYC status
    kyc_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('submitted', 'Submitted'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
        ],
        default='pending',
        help_text="LEGACY FIELD - Synced from compliance.KYC.status" 
    )
    kyc_verified_at = models.DateTimeField(null=True, blank=True)


    is_admin = models.BooleanField(
        default=False,
        help_text="Designates whether the user has admin access"
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into Django admin"
    )
    is_superuser = models.BooleanField(
        default=False,
        help_text="Designates that this user has all permissions"
    )


    # USER STATUS (ADD THESE)
    is_verified = models.BooleanField(
        default=False,
        help_text="User email/phone verified"
    )
    is_suspended = models.BooleanField(
        default=False,
        help_text="User account suspended by admin"
    )
    suspended_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for suspension"
    )
    suspended_at = models.DateTimeField(
        blank=True,
        null=True
    )
    # Account status
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_users'
    )
    date_of_birth = models.DateField(blank=True, null=True)
    is_indian = models.BooleanField(default=True)
    profile_completed = models.BooleanField(default=False)

    # Channel Partner fields
    is_cp = models.BooleanField(default=False, help_text="Is Channel Partner")
    cp_status = models.CharField(
        max_length=20,
        choices=[
            ('not_applied', 'Not Applied'),
            ('pending', 'Pending Review'),
            ('in_progress', 'In Progress'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='not_applied',
        blank=True
    )
    is_active_cp = models.BooleanField(default=False, help_text="Active CP with access")


    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['kyc_status']),
            models.Index(fields=['is_active']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return self.username

    def get_permissions(self):
        """Get all permissions for this user via their role"""
        if not self.role:
            return Permission.objects.none()

        return Permission.objects.filter(
            role_assignments__role=self.role
        ).distinct()

    def has_permission(self, permission_code):
        """Check if user has specific permission"""
        if not self.role:
            return False

        return self.get_permissions().filter(
            code_name=permission_code
        ).exists()


     
    @property
    def kyc_verified(self):
        """Check if KYC is verified (uses compliance.KYC as source of truth)"""
        try:
            return self.kyc.status == 'verified'
        except:
            return False

# ============================================
# RBAC - ROLES (Simplified - Global Only)
# ============================================
class Role(TimestampedModel):
    """
    Global roles for AssetKart
    Examples: admin, developer, channel_partner, customer
    """

    # Role identification
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Hierarchy
    level = models.IntegerField(
        default=0,
        help_text="Higher number = more authority (0-100)"
    )

    # System role protection
    is_system = models.BooleanField(
        default=False,
        help_text="System roles cannot be deleted"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Color coding (UI)
    color = models.CharField(
        max_length=7,
        default='#6c757d',
        help_text="Hex color for badges"
    )

    class Meta:
        db_table = 'roles'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_system']),
        ]
        ordering = ['-level', 'name']

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        # Auto-generate slug from name
        if not self.slug:
            self.slug = slugify(self.name)

        # Auto-generate display_name if not provided
        if not self.display_name:
            self.display_name = self.name.replace('_', ' ').title()

        super().save(*args, **kwargs)

    def clean(self):
        """Validation"""
        # Prevent deletion of system roles
        if self.pk and self.is_system:
            old_instance = Role.objects.get(pk=self.pk)
            if old_instance.is_system and not self.is_system:
                raise ValidationError("Cannot remove system role flag")


# ============================================
# PERMISSIONS (Granular)
# ============================================
class Permission(TimestampedModel):
    """
    Granular permissions for actions
    Examples: properties.create, investments.approve, users.manage
    """

    code_name = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    # properties, investments, users, etc.
    module = models.CharField(max_length=50)
    # create, read, update, delete, approve, etc.
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    # Grouping (for UI)
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text="Group related permissions"
    )

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'permissions'
        indexes = [
            models.Index(fields=['module', 'action']),
            models.Index(fields=['category']),
            models.Index(fields=['code_name']),
        ]
        ordering = ['module', 'action']

    def __str__(self):
        return self.code_name

    def save(self, *args, **kwargs):
        # Auto-generate code_name if not provided
        if not self.code_name and self.module and self.action:
            self.code_name = f"{self.module}.{self.action}"
        super().save(*args, **kwargs)


class RolePermission(TimestampedModel):
    """
    Role to Permission mapping
    Defines what each role can do
    """

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_assignments'
    )

    # Granted by (audit)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_role_permissions'
    )

    class Meta:
        db_table = 'role_permissions'
        unique_together = ('role', 'permission')
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['permission']),
        ]

    def __str__(self):
        return f"{self.role.display_name} → {self.permission.code_name}"


# ============================================
# OTP VERIFICATION MODEL
# ============================================
class OTPVerification(TimestampedModel):
    """
    Database-backed OTP verification system
    Replaces cache-based OTP storage for reliability
    """
    
    # Phone number (normalized format: +91XXXXXXXXXX)
    phone = models.CharField(
        max_length=15,
        db_index=True,
        help_text="Normalized phone number with country code"
    )
    
    # OTP code (6 digits, plain text - short lived)
    otp_code = models.CharField(
        max_length=6,
        help_text="6-digit OTP code"
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="OTP expiry time (typically 5 minutes)"
    )
    
    # Verification status
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Has this OTP been successfully verified?"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was OTP verified"
    )
    
    # Attempt tracking (prevent brute force)
    attempt_count = models.IntegerField(
        default=0,
        help_text="Number of failed verification attempts"
    )
    max_attempts = models.IntegerField(
        default=5,
        help_text="Maximum allowed attempts before blocking"
    )
    
    # Active status (only one active OTP per phone)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is this OTP still active? (invalidated when new OTP sent)"
    )
    
    # Security tracking
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address that requested OTP"
    )
    
    # SMS tracking
    sms_sent = models.BooleanField(
        default=False,
        help_text="Was SMS successfully sent?"
    )
    sms_message_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Route Mobile message ID for tracking"
    )
    
    # Purpose (signup vs login)
    purpose = models.CharField(
        max_length=20,
        choices=[
            ('signup', 'Signup'),
            ('login', 'Login'),
            ('reset_password', 'Reset Password'),
        ],
        default='login',
        help_text="Why was OTP requested?"
    )
    
    class Meta:
        db_table = 'otp_verifications'
        indexes = [
            models.Index(fields=['phone', 'is_active', 'expires_at']),
            models.Index(fields=['phone', 'is_verified']),
            models.Index(fields=['created_at']),
            models.Index(fields=['-expires_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.phone} - {'Verified' if self.is_verified else 'Pending'}"
    
    def is_expired(self):
        """Check if OTP has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if OTP is valid for verification"""
        return (
            self.is_active and 
            not self.is_verified and 
            not self.is_expired() and 
            self.attempt_count < self.max_attempts
        )
    
    def increment_attempt(self):
        """Increment failed attempt count"""
        self.attempt_count += 1
        if self.attempt_count >= self.max_attempts:
            self.is_active = False  # Block after max attempts
        self.save(update_fields=['attempt_count', 'is_active', 'updated_at'])
    
    def mark_verified(self):
        """Mark OTP as verified"""
        from django.utils import timezone
        self.is_verified = True
        self.verified_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['is_verified', 'verified_at', 'is_active', 'updated_at'])
    
    def deactivate(self):
        """Deactivate this OTP (when new OTP is sent)"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
    
    @classmethod
    def get_active_otp(cls, phone):
        """Get active OTP for phone number"""
        from django.utils import timezone
        try:
            return cls.objects.get(
                phone=phone,
                is_active=True,
                is_verified=False,
                expires_at__gt=timezone.now()
            )
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # Should not happen, but handle gracefully
            # Get the most recent one
            return cls.objects.filter(
                phone=phone,
                is_active=True,
                is_verified=False,
                expires_at__gt=timezone.now()
            ).order_by('-created_at').first()
    
    @classmethod
    def check_rate_limit(cls, phone, minutes=15, max_requests=3):
        """Check if phone has exceeded rate limit"""
        from django.utils import timezone
        from datetime import timedelta
        
        time_threshold = timezone.now() - timedelta(minutes=minutes)
        recent_count = cls.objects.filter(
            phone=phone,
            created_at__gte=time_threshold
        ).count()
        
        return recent_count < max_requests, recent_count
    
    @classmethod
    def cleanup_old_otps(cls, hours=24):
        """
        Cleanup old OTP records
        - Delete verified OTPs older than 24 hours
        - Delete expired unverified OTPs older than 1 hour
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Delete old verified OTPs (audit trail kept for 24 hours)
        verified_threshold = timezone.now() - timedelta(hours=hours)
        verified_deleted = cls.objects.filter(
            is_verified=True,
            verified_at__lt=verified_threshold
        ).delete()
        
        # Delete old expired unverified OTPs
        expired_threshold = timezone.now() - timedelta(hours=1)
        expired_deleted = cls.objects.filter(
            is_verified=False,
            expires_at__lt=expired_threshold
        ).delete()
        
        return {
            'verified_deleted': verified_deleted[0],
            'expired_deleted': expired_deleted[0]
        }
