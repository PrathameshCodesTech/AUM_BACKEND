# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
import logging
from .models import User, Role, Permission, RolePermission

logger = logging.getLogger(__name__)


# ============================================
# CUSTOM FILTERS
# ============================================

class ActiveFilter(admin.SimpleListFilter):
    """Filter for active/inactive users"""
    title = 'active status'
    parameter_name = 'active'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active Only'),
            ('inactive', 'Inactive Only'),
            ('blocked', 'Blocked Only'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_active=True, is_blocked=False)
        if self.value() == 'inactive':
            return queryset.filter(is_active=False)
        if self.value() == 'blocked':
            return queryset.filter(is_blocked=True)


class KYCStatusFilter(admin.SimpleListFilter):
    """Filter by KYC status"""
    title = 'KYC status'
    parameter_name = 'kyc'

    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending'),
            ('submitted', 'Submitted'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(kyc_status=self.value())


# ============================================
# USER ADMIN
# ============================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model"""

    # List display
    list_display = [
        'username',
        'email',
        'phone',
        'role_badge',
        'kyc_badge',
        'status_badge',
        'date_joined',
    ]

    list_filter = [
        'role',
        ActiveFilter,
        KYCStatusFilter,
        'phone_verified',
        'is_staff',
        'is_superuser',
        'date_joined',
    ]

    search_fields = [
        'username',
        'email',
        'phone',
        'first_name',
        'last_name',
        'city',
        'state',
    ]

    ordering = ['-date_joined']

    # Fieldsets for change form
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': (
                'first_name',
                'last_name',
                'email',
                'phone',
                'phone_verified',
                'avatar',
                'date_of_birth',
                'gender',
            )
        }),
        ('Address', {
            'fields': (
                'address',
                'city',
                'state',
                'country',
                'pincode',
            ),
            'classes': ('collapse',),
        }),
        ('Role & Permissions', {
            'fields': ('role', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('KYC Information', {
            'fields': ('kyc_status', 'kyc_verified_at'),
        }),
        ('Account Status', {
            'fields': (
                'is_active',
                'is_blocked',
                'blocked_reason',
                'blocked_at',
                'blocked_by',
            ),
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # Add fieldsets for creating new user
    add_fieldsets = (
        ('Authentication', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        ('Basic Info', {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'first_name', 'last_name'),
        }),
        ('Role', {
            'classes': ('wide',),
            'fields': ('role', 'is_staff'),
        }),
    )

    readonly_fields = [
        'created_at',
        'updated_at',
        'last_login',
        'date_joined',
        'kyc_verified_at',
        'blocked_at',
    ]

    # Custom badge methods
    def role_badge(self, obj):
        """Display role as colored badge"""
        if obj.role:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px;">{}</span>',
                obj.role.color,
                obj.role.display_name
            )
        return format_html('<span style="color: #999;">No Role</span>')
    role_badge.short_description = 'Role'

    def kyc_badge(self, obj):
        """Display KYC status as colored badge"""
        colors = {
            'pending': '#ffc107',
            'submitted': '#17a2b8',
            'verified': '#28a745',
            'rejected': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px; text-transform: uppercase;">{}</span>',
            colors.get(obj.kyc_status, '#6c757d'),
            obj.kyc_status
        )
    kyc_badge.short_description = 'KYC'

    def status_badge(self, obj):
        """Display account status"""
        if obj.is_blocked:
            return format_html(
                '<span style="color: #dc3545;">🚫 Blocked</span>'
            )
        elif obj.is_active:
            return format_html(
                '<span style="color: #28a745;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: #999;">○ Inactive</span>'
            )
    status_badge.short_description = 'Status'

    # Actions
    actions = ['verify_kyc', 'block_users', 'unblock_users',
               'activate_users', 'deactivate_users']

    def verify_kyc(self, request, queryset):
        """Bulk verify KYC"""
        updated = queryset.update(
            kyc_status='verified',
            kyc_verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} user(s) KYC verified.')
    verify_kyc.short_description = 'Verify KYC for selected users'

    def block_users(self, request, queryset):
        """Bulk block users"""
        updated = queryset.update(
            is_blocked=True,
            blocked_at=timezone.now(),
            blocked_by=request.user
        )
        self.message_user(request, f'{updated} user(s) blocked.')
    block_users.short_description = 'Block selected users'

    def unblock_users(self, request, queryset):
        """Bulk unblock users"""
        updated = queryset.update(
            is_blocked=False,
            blocked_at=None,
            blocked_by=None,
            blocked_reason=''
        )
        self.message_user(request, f'{updated} user(s) unblocked.')
    unblock_users.short_description = 'Unblock selected users'

    def activate_users(self, request, queryset):
        """Bulk activate users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) activated.')
    activate_users.short_description = 'Activate selected users'

    def deactivate_users(self, request, queryset):
        """Bulk deactivate users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) deactivated.')
    deactivate_users.short_description = 'Deactivate selected users'

    def save_model(self, request, obj, form, change):
        """Send welcome email on admin-created users"""
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new and obj.email:
            try:
                name = obj.first_name or obj.username
                phone = obj.phone or ''
                subject = "Your AssetKart account is ready"
                body = (
                    f"Hi {name},\n\n"
                    "We've created your AssetKart account.\n\n"
                    "Login steps:\n"
                    "1) Go to https://app.assetkart.com (or the mobile app)\n"
                    f"2) Enter your phone number {phone}\n"
                    "3) Use the OTP you receive to sign in\n\n"
                    "Once inside, you can complete your profile and start exploring opportunities.\n\n"
                    "If you need help, email us at invest@assetkart.com.\n\n"
                    "Best regards,\n"
                    "AssetKart Team"
                )
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.email],
                    fail_silently=False,
                )
                logger.info("Welcome email sent to %s for admin-created user %s", obj.email, obj.pk)
            except Exception as exc:
                logger.error("Failed to send admin-created user email for user %s: %s", obj.pk, exc, exc_info=True)
        else:
            logger.warning("Welcome email skipped: is_new=%s email=%s", is_new, obj.email)


# ============================================
# ROLE ADMIN
# ============================================

class RolePermissionInline(admin.TabularInline):
    """Inline for managing role permissions"""
    model = RolePermission
    extra = 1
    autocomplete_fields = ['permission']
    readonly_fields = ['created_at', 'granted_by']

    def save_model(self, request, obj, form, change):
        """Auto-set granted_by"""
        if not obj.pk:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin for Role model"""

    list_display = [
        'display_name',
        'name',
        'level_badge',
        'user_count',
        'permission_count',
        'system_badge',
        'status_badge',
    ]

    list_filter = ['is_system', 'is_active', 'level']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['-level', 'name']

    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'display_name', 'description')
        }),
        ('Hierarchy & Settings', {
            'fields': ('level', 'color', 'is_system', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    inlines = [RolePermissionInline]

    # Custom display methods
    def level_badge(self, obj):
        """Display level as badge"""
        color = '#dc3545' if obj.level >= 80 else '#17a2b8' if obj.level >= 50 else '#6c757d'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">Level {}</span>',
            color,
            obj.level
        )
    level_badge.short_description = 'Level'

    def system_badge(self, obj):
        """Display system role indicator"""
        if obj.is_system:
            return format_html('🔒 <span style="color: #dc3545;">System</span>')
        return '—'
    system_badge.short_description = 'System'

    def status_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Active</span>')
        return format_html('<span style="color: #999;">○ Inactive</span>')
    status_badge.short_description = 'Status'

    def user_count(self, obj):
        """Count users with this role"""
        count = obj.users.count()
        return format_html('<strong>{}</strong> users', count)
    user_count.short_description = 'Users'

    def permission_count(self, obj):
        """Count permissions for this role"""
        count = obj.role_permissions.count()
        return format_html('<strong>{}</strong> permissions', count)
    permission_count.short_description = 'Permissions'

    def delete_model(self, request, obj):
        """Prevent deletion of system roles"""
        if obj.is_system:
            self.message_user(
                request,
                f'Cannot delete system role: {obj.display_name}',
                level='ERROR'
            )
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Prevent bulk deletion of system roles"""
        system_roles = queryset.filter(is_system=True)
        if system_roles.exists():
            self.message_user(
                request,
                f'Cannot delete {system_roles.count()} system role(s). They were excluded.',
                level='WARNING'
            )
            queryset = queryset.filter(is_system=False)
        queryset.delete()


# ============================================
# PERMISSION ADMIN
# ============================================

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin for Permission model"""

    list_display = [
        'code_name',
        'name',
        'module_badge',
        'action_badge',
        'category',
        'role_count',
        'status_badge',
    ]

    list_filter = ['module', 'action', 'category', 'is_active']
    search_fields = ['code_name', 'name', 'description', 'module', 'action']
    ordering = ['module', 'action']

    fieldsets = (
        ('Permission Details', {
            'fields': ('code_name', 'name', 'description')
        }),
        ('Classification', {
            'fields': ('module', 'action', 'category')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    # Custom display methods
    def module_badge(self, obj):
        """Display module as badge"""
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            obj.module.upper()
        )
    module_badge.short_description = 'Module'

    def action_badge(self, obj):
        """Display action as badge"""
        colors = {
            'create': '#28a745',
            'read': '#17a2b8',
            'update': '#ffc107',
            'delete': '#dc3545',
            'approve': '#6f42c1',
        }
        color = colors.get(obj.action.lower(), '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            color,
            obj.action.upper()
        )
    action_badge.short_description = 'Action'

    def status_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Active</span>')
        return format_html('<span style="color: #999;">○ Inactive</span>')
    status_badge.short_description = 'Status'

    def role_count(self, obj):
        """Count roles with this permission"""
        count = obj.role_assignments.count()
        return format_html('<strong>{}</strong> roles', count)
    role_count.short_description = 'Assigned to'


# ============================================
# ROLE-PERMISSION ADMIN
# ============================================

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin for RolePermission mapping"""

    list_display = [
        'role',
        'permission',
        'granted_by',
        'created_at',
    ]

    list_filter = ['role', 'permission__module', 'permission__action']
    search_fields = [
        'role__name',
        'role__display_name',
        'permission__code_name',
        'permission__name',
    ]

    autocomplete_fields = ['role', 'permission', 'granted_by']

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Assignment', {
            'fields': ('role', 'permission')
        }),
        ('Audit', {
            'fields': ('granted_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """Auto-set granted_by for new assignments"""
        if not obj.pk and not obj.granted_by:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)


# ============================================
# UNREGISTER DEFAULT GROUP
# ============================================
# If you're not using Django's built-in Group model
# admin.site.unregister(Group)
