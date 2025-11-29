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
        default='pending'
    )
    kyc_verified_at = models.DateTimeField(null=True, blank=True)

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
