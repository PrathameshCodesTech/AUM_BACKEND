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
# USER MODEL (NO user_type - fully dynamic!)
# ============================================
class User(AbstractUser, TimestampedModel):
    """
    Extended user model
    User "type" is determined by their role in organization, not hardcoded field
    """

    # Basic info
    phone = models.CharField(max_length=15, blank=True)
    phone_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

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

    # KYC status (global - can be org-specific via KYC model)
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

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['kyc_status']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.username

    def get_role_in_org(self, organization):
        """Get user's role in specific organization"""
        try:
            membership = self.memberships.get(
                organization=organization,
                is_active=True
            )
            return membership.role
        except OrganizationMember.DoesNotExist:
            return None

    def has_role_in_org(self, organization, role_slug):
        """Check if user has specific role in organization"""
        return self.memberships.filter(
            organization=organization,
            role__slug=role_slug,
            is_active=True
        ).exists()

    def get_organizations(self):
        """Get all organizations user is member of"""
        return Organization.objects.filter(
            members__user=self,
            members__is_active=True
        ).distinct()


# ============================================
# ORGANIZATION (Multi-tenancy)
# ============================================
class Organization(TimestampedModel, SoftDeleteModel):
    """Tenant organizations - each client company"""

    SUBSCRIPTION_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    # Owner (first admin/creator)
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_organizations'
    )

    # Organization details
    company_name = models.CharField(max_length=255)
    company_registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    gst_number = models.CharField(max_length=15, blank=True)

    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    website = models.URLField(blank=True)

    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=10)

    # Branding (white-label)
    logo = models.ImageField(upload_to='org_logos/', null=True, blank=True)
    favicon = models.ImageField(
        upload_to='org_favicons/', null=True, blank=True)
    primary_color = models.CharField(
        max_length=7, default='#007bff')  # Hex color
    secondary_color = models.CharField(max_length=7, default='#6c757d')

    # Subscription
    subscription_plan = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_CHOICES,
        default='free'
    )
    subscription_starts_at = models.DateField(null=True, blank=True)
    subscription_ends_at = models.DateField(null=True, blank=True)

    # Settings (JSON for flexibility)
    settings = models.JSONField(default=dict, blank=True)

    # Features enabled (can be subscription-based)
    features = models.JSONField(
        default=dict,
        blank=True,
        help_text="Feature flags: {'cp_hierarchy': True, 'custom_roles': True}"
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'organizations'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_verified']),
            models.Index(fields=['subscription_plan']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ============================================
# RBAC - ROLES (Fully Dynamic!)
# ============================================
class Role(TimestampedModel):
    """
    Dynamic roles within organization
    No hardcoded choices - roles created as data, not code
    """

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='roles',
        null=True,  # Null for global platform roles
        blank=True
    )

    # Role identification
    name = models.CharField(max_length=100)  # No choices - fully dynamic!
    slug = models.SlugField(max_length=100)
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
        help_text="System roles cannot be deleted, only modified"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Color coding (UI)
    color = models.CharField(
        max_length=7, default='#6c757d', help_text="Hex color for badges")

    class Meta:
        db_table = 'roles'
        unique_together = [
            ('organization', 'slug'),  # Slug unique per org
            ('organization', 'name'),  # Name unique per org
        ]
        indexes = [
            models.Index(fields=['organization', 'slug']),
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['is_system']),
        ]
        ordering = ['-level', 'name']

    def __str__(self):
        if self.organization:
            return f"{self.organization.name} - {self.display_name}"
        return f"Platform - {self.display_name}"

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
        # Prevent deletion of system roles at model level
        if self.pk and self.is_system:
            old_instance = Role.objects.get(pk=self.pk)
            if old_instance.is_system and not self.is_system:
                raise ValidationError("Cannot remove system role flag")

        # Slug must be lowercase alphanumeric + hyphens
        if self.slug and not self.slug.replace('-', '').replace('_', '').isalnum():
            raise ValidationError(
                "Slug must contain only letters, numbers, hyphens, and underscores")


# ============================================
# PERMISSIONS (Granular)
# ============================================
class Permission(TimestampedModel):
    """
    Granular permissions for actions
    These are global - same across all orgs for consistency
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
        help_text="Group related permissions: 'Property Management', 'Financial Operations'"
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
# ORGANIZATION MEMBERSHIP
# ============================================
class OrganizationMember(TimestampedModel):
    """
    User membership in organization with role
    This is where user gets their "type" - via role
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,  # Protect to prevent accidental role deletion
        related_name='members'
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="User's primary/default organization"
    )

    # Invitation tracking
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invited_members'
    )
    invitation_token = models.CharField(
        max_length=100, blank=True, unique=True)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    invitation_accepted_at = models.DateTimeField(null=True, blank=True)

    # Dates
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'organization_members'
        unique_together = ('user', 'organization')
        indexes = [
            models.Index(fields=['user', 'organization']),
            models.Index(fields=['organization', 'role', 'is_active']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['invitation_token']),
        ]
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role.display_name})"

    def get_permissions(self):
        """Get all permissions for this membership"""
        return Permission.objects.filter(
            role_assignments__role=self.role
        ).distinct()


# ============================================
# TEAMS (Departments within org)
# ============================================
class Team(TimestampedModel, SoftDeleteModel):
    """Teams/Departments within organization"""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='teams'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)

    # Team lead
    lead = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_teams'
    )

    # Members (through table)
    members = models.ManyToManyField(
        User,
        through='TeamMember',
        related_name='teams'
    )

    # Parent team (for nested teams)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_teams'
    )

    # Status
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'teams'
        unique_together = [
            ('organization', 'slug'),
            ('organization', 'name'),
        ]
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['slug']),
        ]
        ordering = ['name']

    def __str__(self):
        return f"{self.organization.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TeamMember(TimestampedModel):
    """Team membership"""

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='team_members'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )

    # Role within team (optional - for team-specific roles)
    team_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Team-specific role like 'Team Lead', 'Coordinator'"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Dates
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'team_members'
        unique_together = ('team', 'user')
        indexes = [
            models.Index(fields=['team', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} - {self.team.name}"
