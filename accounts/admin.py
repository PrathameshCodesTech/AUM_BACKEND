# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import (
    User, Organization, Role, Permission, RolePermission,
    OrganizationMember, Team, TeamMember
)


# ============================================
# CUSTOM ADMIN SITE CONFIGURATION
# ============================================
admin.site.site_header = "AUM Management System"
admin.site.site_title = "AUM Admin"
admin.site.index_title = "Welcome to AUM Administration"


# ============================================
# INLINE ADMINS
# ============================================

# For OrganizationAdmin - shows members of an organization
class OrganizationMemberInline(admin.TabularInline):
    model = OrganizationMember
    fk_name = 'organization'
    extra = 1
    fields = ('user', 'role', 'is_active', 'is_primary', 'joined_at')
    readonly_fields = ('joined_at',)
    autocomplete_fields = ['user', 'role']


# For UserAdmin - shows which organizations a user belongs to
class UserOrganizationInline(admin.TabularInline):
    model = OrganizationMember
    fk_name = 'user'
    extra = 0
    fields = ('organization', 'role', 'is_active', 'is_primary', 'joined_at')
    readonly_fields = ('joined_at',)
    autocomplete_fields = ['organization', 'role']
    verbose_name = "Organization Membership"
    verbose_name_plural = "Organization Memberships"


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    fields = ('permission', 'granted_by', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ['permission']


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    fk_name = 'team'
    extra = 1
    fields = ('user', 'team_role', 'is_active', 'joined_at')
    readonly_fields = ('joined_at',)
    autocomplete_fields = ['user']


# ============================================
# USER ADMIN
# ============================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'phone', 'colored_kyc_status',
        'is_active', 'is_blocked', 'date_joined'
    )
    list_filter = (
        'is_active', 'is_blocked', 'kyc_status',
        'is_staff', 'is_superuser', 'date_joined'
    )
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('Account', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone', 'phone_verified',
                      'date_of_birth', 'gender', 'avatar')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'pincode'),
            'classes': ('collapse',)
        }),
        ('KYC Status', {
            'fields': ('kyc_status', 'kyc_verified_at')
        }),
        ('Account Status', {
            'fields': ('is_active', 'is_blocked', 'blocked_reason',
                      'blocked_at', 'blocked_by')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('last_login', 'date_joined', 'kyc_verified_at', 'blocked_at')
    inlines = [UserOrganizationInline]  # ← Changed to UserOrganizationInline
    
    def colored_kyc_status(self, obj):
        colors = {
            'pending': '#6c757d',    # Gray
            'submitted': '#ffc107',  # Yellow
            'verified': '#28a745',   # Green
            'rejected': '#dc3545',   # Red
        }
        color = colors.get(obj.kyc_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_kyc_status_display()
        )
    colored_kyc_status.short_description = 'KYC Status'
    colored_kyc_status.admin_order_field = 'kyc_status'


# ============================================
# ORGANIZATION ADMIN
# ============================================
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'owner', 'colored_subscription', 'member_count',
        'colored_status', 'created_at'
    )
    list_filter = (
        'subscription_plan', 'is_active', 'is_verified',
        'subscription_starts_at', 'created_at'
    )
    search_fields = ('name', 'company_name', 'email', 'phone', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'owner')
        }),
        ('Company Details', {
            'fields': ('company_name', 'company_registration_number',
                      'tax_id', 'pan_number', 'gst_number')
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'pincode'),
            'classes': ('collapse',)
        }),
        ('Branding', {
            'fields': ('logo', 'favicon', 'primary_color', 'secondary_color'),
            'classes': ('collapse',)
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'subscription_starts_at',
                      'subscription_ends_at')
        }),
        ('Settings & Features', {
            'fields': ('settings', 'features'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_verified', 'verified_at')
        }),
    )
    
    readonly_fields = ('created_at', 'verified_at')
    inlines = [OrganizationMemberInline]  # ← Stays as OrganizationMemberInline
    
    def colored_subscription(self, obj):
        colors = {
            'free': '#6c757d',       # Gray
            'basic': '#17a2b8',      # Cyan
            'pro': '#007bff',        # Blue
            'enterprise': '#6f42c1', # Purple
        }
        color = colors.get(obj.subscription_plan, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_subscription_plan_display().upper()
        )
    colored_subscription.short_description = 'Subscription'
    colored_subscription.admin_order_field = 'subscription_plan'
    
    def colored_status(self, obj):
        if obj.is_active and obj.is_verified:
            color = '#28a745'  # Green
            status = 'Active & Verified'
        elif obj.is_active:
            color = '#ffc107'  # Yellow
            status = 'Active'
        else:
            color = '#dc3545'  # Red
            status = 'Inactive'
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, status
        )
    colored_status.short_description = 'Status'
    
    def member_count(self, obj):
        count = obj.members.filter(is_active=True).count()
        return format_html('<strong>{}</strong> members', count)
    member_count.short_description = 'Members'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _member_count=Count('members', filter=Q(members__is_active=True))
        )


# ============================================
# ROLE ADMIN
# ============================================
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'display_name', 'organization', 'colored_badge', 'level',
        'permission_count', 'is_system', 'is_active'
    )
    list_filter = ('is_system', 'is_active', 'organization', 'level')
    search_fields = ('name', 'display_name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-level', 'name')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('organization', 'name', 'slug', 'display_name', 'description')
        }),
        ('Settings', {
            'fields': ('level', 'color', 'is_system', 'is_active')
        }),
    )
    
    inlines = [RolePermissionInline]
    
    def colored_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            obj.color, obj.display_name
        )
    colored_badge.short_description = 'Badge'
    
    def permission_count(self, obj):
        count = obj.role_permissions.count()
        return format_html('<strong>{}</strong> permissions', count)
    permission_count.short_description = 'Permissions'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_permission_count=Count('role_permissions'))


# ============================================
# PERMISSION ADMIN
# ============================================
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        'code_name', 'name', 'colored_module', 'action',
        'category', 'is_active'
    )
    list_filter = ('module', 'action', 'category', 'is_active')
    search_fields = ('code_name', 'name', 'module', 'action')
    ordering = ('module', 'action')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('code_name', 'name', 'description')
        }),
        ('Classification', {
            'fields': ('module', 'action', 'category')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def colored_module(self, obj):
        colors = {
            'organizations': '#007bff',    # Blue
            'users': '#28a745',            # Green
            'roles': '#6f42c1',            # Purple
            'properties': '#fd7e14',       # Orange
            'investments': '#20c997',      # Teal
            'wallet': '#17a2b8',           # Cyan
            'commissions': '#ffc107',      # Yellow
            'channel_partners': '#28a745', # Green
            'payouts': '#dc3545',          # Red
            'redemptions': '#e83e8c',      # Pink
            'kyc': '#6c757d',              # Gray
            'reports': '#007bff',          # Blue
            'teams': '#6f42c1',            # Purple
        }
        color = colors.get(obj.module, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px; font-size: 10px;">{}</span>',
            color, obj.module
        )
    colored_module.short_description = 'Module'
    colored_module.admin_order_field = 'module'


# ============================================
# ROLE PERMISSION ADMIN
# ============================================
@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission', 'granted_by', 'created_at')
    list_filter = ('role__organization', 'role', 'created_at')
    search_fields = ('role__display_name', 'permission__code_name', 'permission__name')
    autocomplete_fields = ['role', 'permission', 'granted_by']
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('role', 'permission', 'granted_by')
        }),
    )
    
    readonly_fields = ('created_at',)


# ============================================
# ORGANIZATION MEMBER ADMIN
# ============================================
@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'organization', 'colored_role', 'colored_status',
        'is_primary', 'joined_at'
    )
    list_filter = (
        'is_active', 'is_primary', 'role', 'organization', 'joined_at'
    )
    search_fields = (
        'user__username', 'user__email', 'organization__name', 'role__display_name'
    )
    autocomplete_fields = ['user', 'organization', 'role', 'invited_by']
    ordering = ('-joined_at',)
    
    fieldsets = (
        ('Membership', {
            'fields': ('user', 'organization', 'role')
        }),
        ('Status', {
            'fields': ('is_active', 'is_primary')
        }),
        ('Invitation', {
            'fields': ('invited_by', 'invitation_token', 'invitation_sent_at',
                      'invitation_accepted_at'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('joined_at', 'left_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('joined_at',)
    
    def colored_role(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            obj.role.color, obj.role.display_name
        )
    colored_role.short_description = 'Role'
    
    def colored_status(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">● Active</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">● Inactive</span>'
        )
    colored_status.short_description = 'Status'


# ============================================
# TEAM ADMIN
# ============================================
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'organization', 'lead', 'member_count',
        'parent', 'is_active', 'created_at'
    )
    list_filter = ('organization', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'organization__name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['organization', 'lead', 'parent']
    ordering = ('organization', 'name')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('organization', 'name', 'slug', 'description')
        }),
        ('Team Structure', {
            'fields': ('lead', 'parent')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    inlines = [TeamMemberInline]
    
    def member_count(self, obj):
        count = obj.team_members.filter(is_active=True).count()
        return format_html('<strong>{}</strong> members', count)
    member_count.short_description = 'Members'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _member_count=Count('team_members', filter=Q(team_members__is_active=True))
        )


# ============================================
# TEAM MEMBER ADMIN
# ============================================
@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'team', 'team_role', 'colored_status', 'joined_at'
    )
    list_filter = ('is_active', 'team__organization', 'joined_at')
    search_fields = ('user__username', 'team__name', 'team_role')
    autocomplete_fields = ['team', 'user']
    ordering = ('-joined_at',)
    
    fieldsets = (
        ('Membership', {
            'fields': ('team', 'user', 'team_role')
        }),
        ('Status', {
            'fields': ('is_active', 'joined_at', 'left_at')
        }),
    )
    
    readonly_fields = ('joined_at',)
    
    def colored_status(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">● Active</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">● Inactive</span>'
        )
    colored_status.short_description = 'Status'
