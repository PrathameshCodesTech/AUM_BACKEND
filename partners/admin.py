# partners/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count, Q
from django.forms import widgets
from decimal import Decimal
import json
from .models import (
    ChannelPartner, CPCustomerRelation, CommissionRule, CPCommissionRule
)
from django.db import models



# ============================================
# CUSTOM WIDGETS
# ============================================

class TierJSONWidget(widgets.Textarea):
    """Widget for displaying tiered commission JSON"""
    
    def format_value(self, value):
        try:
            if isinstance(value, str):
                value = json.loads(value)
            # Format with indentation
            value = json.dumps(value, indent=2, sort_keys=False, ensure_ascii=False)
            self.attrs['rows'] = min(value.count('\n') + 2, 15)
            return value
        except (ValueError, TypeError):
            return super().format_value(value)


# ============================================
# CUSTOM FILTERS
# ============================================

class CPStatusFilter(admin.SimpleListFilter):
    """Filter CPs by status"""
    title = 'CP status'
    parameter_name = 'cp_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('verified', 'Verified'),
            ('unverified', 'Unverified'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_active=True)
        if self.value() == 'inactive':
            return queryset.filter(is_active=False)
        if self.value() == 'verified':
            return queryset.filter(is_verified=True)
        if self.value() == 'unverified':
            return queryset.filter(is_verified=False)


class CPHierarchyFilter(admin.SimpleListFilter):
    """Filter by hierarchy level"""
    title = 'hierarchy level'
    parameter_name = 'hierarchy'

    def lookups(self, request, model_admin):
        return (
            ('master', 'Master CP (No Parent)'),
            ('sub', 'Sub-CP (Has Parent)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'master':
            return queryset.filter(parent_cp__isnull=True)
        if self.value() == 'sub':
            return queryset.filter(parent_cp__isnull=False)


class SoftDeleteCPFilter(admin.SimpleListFilter):
    """Filter for soft deleted CPs"""
    title = 'deletion status'
    parameter_name = 'deleted_cp'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active Only'),
            ('deleted', 'Deleted Only'),
            ('all', 'All Records'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_deleted=False)
        elif self.value() == 'deleted':
            return queryset.filter(is_deleted=True)
        elif self.value() == 'all':
            return queryset


class CommissionRuleTypeFilter(admin.SimpleListFilter):
    """Filter commission rules by type"""
    title = 'commission type'
    parameter_name = 'comm_type'

    def lookups(self, request, model_admin):
        return (
            ('flat', 'Flat Percentage'),
            ('tiered', 'Tiered'),
            ('one_time', 'One-time'),
            ('recurring', 'Recurring'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(commission_type=self.value())


# ============================================
# CHANNEL PARTNER ADMIN
# ============================================

class CPCustomerRelationInline(admin.TabularInline):
    """Inline for viewing CP customers"""
    model = CPCustomerRelation
    extra = 0
    max_num = 10
    
    fields = [
        'customer',
        'referral_code',
        'referral_date',
        'is_active',
    ]
    
    readonly_fields = ['referral_date']
    
    autocomplete_fields = ['customer']
    
    verbose_name = 'Referred Customer'
    verbose_name_plural = 'Referred Customers (Last 10)'
    
    ordering = ['-referral_date']


class CPCommissionRuleInline(admin.TabularInline):
    """Inline for CP commission rules"""
    model = CPCommissionRule
    extra = 1
    
    fields = [
        'commission_rule',
        'property',
        'assigned_at',
    ]
    
    readonly_fields = ['assigned_at']
    
    autocomplete_fields = ['commission_rule', 'property']
    
    verbose_name = 'Commission Rule'
    verbose_name_plural = 'Assigned Commission Rules'


@admin.register(ChannelPartner)
class ChannelPartnerAdmin(admin.ModelAdmin):
    """Admin for Channel Partner management"""
    
    list_display = [
        'cp_code',
        'user_link',
        'hierarchy_display',
        'company_name',
        'customer_count',
        'total_referrals',
        'status_badge',
        'verification_badge',
        'created_at',
    ]
    
    list_filter = [
        CPStatusFilter,
        CPHierarchyFilter,
        SoftDeleteCPFilter,
        'is_verified',
        'verified_by',
        'created_at',
    ]
    
    search_fields = [
        'cp_code',
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'company_name',
        'pan_number',
        'gst_number',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'verified_at',
        'verified_by',
        'deleted_at',
        'deleted_by',
        'hierarchy_level',
        'sub_cp_count',
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': (
                'user',
                'cp_code',
            )
        }),
        ('Hierarchy', {
            'fields': (
                'parent_cp',
                'hierarchy_level',
                'sub_cp_count',
            )
        }),
        ('Company Details', {
            'fields': (
                'company_name',
                'pan_number',
                'gst_number',
            )
        }),
        ('Bank Details', {
            'fields': (
                'bank_name',
                'account_number',
                'ifsc_code',
                'account_holder_name',
            ),
            'classes': ('collapse',),
        }),
        ('Targets', {
            'fields': (
                'monthly_target',
                'quarterly_target',
                'yearly_target',
            ),
            'classes': ('collapse',),
        }),
        ('Status & Verification', {
            'fields': (
                'is_active',
                'is_verified',
                'verified_at',
                'verified_by',
            )
        }),
        ('Onboarding', {
            'fields': (
                'onboarded_by',
            ),
            'classes': ('collapse',),
        }),
        ('Soft Delete', {
            'fields': (
                'is_deleted',
                'deleted_at',
                'deleted_by',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [CPCustomerRelationInline, CPCommissionRuleInline]
    
    autocomplete_fields = [
        'user',
        'parent_cp',
        'verified_by',
        'onboarded_by',
        'deleted_by',
    ]
    
    # Custom display methods
    def user_link(self, obj):
        """Display user as clickable link"""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.get_full_name() or obj.user.username
        )
    user_link.short_description = 'User'
    
    def hierarchy_display(self, obj):
        """Display hierarchy level with visual indicator"""
        level = obj.get_hierarchy_level()
        
        if level == 0:
            return format_html(
                '<span style="color: #007bff; font-weight: bold;">👑 Master CP</span>'
            )
        else:
            indent = '└─' + ('─' * level)
            return format_html(
                '<span style="color: #6c757d;">{} Sub-CP (L{})</span>',
                indent,
                level
            )
    hierarchy_display.short_description = 'Hierarchy'
    
    def customer_count(self, obj):
        """Count direct customers"""
        count = obj.customers.filter(is_active=True).count()
        return format_html('<strong>{}</strong>', count)
    customer_count.short_description = 'Customers'
    
    def total_referrals(self, obj):
        """Count total referrals including sub-CPs"""
        # Direct customers
        direct = obj.customers.filter(is_active=True).count()
        
        # Sub-CP customers
        sub_cps = obj.get_all_sub_cps()
        sub_count = sum(
            sub_cp.customers.filter(is_active=True).count() 
            for sub_cp in sub_cps
        )
        
        if sub_count > 0:
            return format_html(
                '{} <small style="color: #6c757d;">(+{} via sub-CPs)</small>',
                direct,
                sub_count
            )
        return str(direct)
    total_referrals.short_description = 'Total Network'
    
    def status_badge(self, obj):
        """Display CP status"""
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: #000; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 10px;">🗑️ DELETED</span>'
            )
        elif obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Active</span>')
        else:
            return format_html('<span style="color: #999;">○ Inactive</span>')
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'is_active'
    
    def verification_badge(self, obj):
        """Display verification status"""
        if obj.is_verified:
            return format_html(
                '<span style="color: #28a745;">✓ Verified</span>'
            )
        return format_html('<span style="color: #ffc107;">⏳ Unverified</span>')
    verification_badge.short_description = 'Verification'
    verification_badge.admin_order_field = 'is_verified'
    
    def hierarchy_level(self, obj):
        """Display hierarchy level as readonly field"""
        level = obj.get_hierarchy_level()
        return format_html(
            '<strong style="font-size: 14px;">Level {}</strong> {}',
            level,
            '(Master CP)' if level == 0 else f'(Sub-CP under {obj.parent_cp.cp_code})'
        )
    hierarchy_level.short_description = 'Hierarchy Level'
    
    def sub_cp_count(self, obj):
        """Count direct sub-CPs"""
        direct_subs = obj.sub_cps.count()
        all_subs = len(obj.get_all_sub_cps())
        
        if all_subs > direct_subs:
            return format_html(
                '<strong>{}</strong> direct <small>(Total network: {})</small>',
                direct_subs,
                all_subs
            )
        return format_html('<strong>{}</strong>', direct_subs)
    sub_cp_count.short_description = 'Sub-CPs'
    
    # Bulk Actions
    actions = [
        'activate_cps',
        'deactivate_cps',
        'verify_cps',
        'unverify_cps',
        'soft_delete_cps',
        'restore_cps',
    ]
    
    def activate_cps(self, request, queryset):
        """Activate CPs"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} CP(s) activated.')
    activate_cps.short_description = '✓ Activate CPs'
    
    def deactivate_cps(self, request, queryset):
        """Deactivate CPs"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} CP(s) deactivated.')
    deactivate_cps.short_description = '○ Deactivate CPs'
    
    def verify_cps(self, request, queryset):
        """Verify CPs"""
        count = queryset.filter(is_verified=False).update(
            is_verified=True,
            verified_at=timezone.now(),
            verified_by=request.user
        )
        self.message_user(request, f'{count} CP(s) verified.')
    verify_cps.short_description = '✓ Verify CPs'
    
    def unverify_cps(self, request, queryset):
        """Unverify CPs"""
        count = queryset.filter(is_verified=True).update(
            is_verified=False,
            verified_at=None,
            verified_by=None
        )
        self.message_user(request, f'{count} CP(s) unverified.', level='WARNING')
    unverify_cps.short_description = '❌ Unverify CPs'
    
    def soft_delete_cps(self, request, queryset):
        """Soft delete CPs"""
        count = queryset.filter(is_deleted=False).update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user
        )
        self.message_user(request, f'{count} CP(s) soft deleted.')
    soft_delete_cps.short_description = '🗑️ Soft Delete CPs'
    
    def restore_cps(self, request, queryset):
        """Restore soft deleted CPs"""
        count = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None
        )
        self.message_user(request, f'{count} CP(s) restored.')
    restore_cps.short_description = '↻ Restore CPs'
    
    def save_model(self, request, obj, form, change):
        """Auto-set onboarded_by and verified_by"""
        if not change:  # New CP
            if not obj.onboarded_by:
                obj.onboarded_by = request.user
        
        # If verification status changed
        if change and 'is_verified' in form.changed_data:
            if obj.is_verified and not obj.verified_by:
                obj.verified_by = request.user
                obj.verified_at = timezone.now()
        
        super().save_model(request, obj, form, change)
    
    # Override queryset to show all by default
    def get_queryset(self, request):
        """Include soft-deleted CPs"""
        qs = super().get_queryset(request)
        return qs


# ============================================
# CP CUSTOMER RELATION ADMIN
# ============================================

@admin.register(CPCustomerRelation)
class CPCustomerRelationAdmin(admin.ModelAdmin):
    """Admin for CP-Customer relationship"""
    
    list_display = [
        'cp_link',
        'customer_link',
        'referral_code',
        'referral_date',
        'status_badge',
    ]
    
    list_filter = [
        'is_active',
        'referral_date',
    ]
    
    search_fields = [
        'cp__cp_code',
        'cp__user__username',
        'customer__username',
        'customer__email',
        'referral_code',
    ]
    
    ordering = ['-referral_date']
    
    date_hierarchy = 'referral_date'
    
    readonly_fields = ['referral_date']
    
    fieldsets = (
        ('Relationship', {
            'fields': (
                'cp',
                'customer',
            )
        }),
        ('Referral Details', {
            'fields': (
                'referral_code',
                'referral_date',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
            )
        }),
    )
    
    autocomplete_fields = ['cp', 'customer']
    
    # Custom display methods
    def cp_link(self, obj):
        """Display CP as link"""
        url = reverse('admin:partners_channelpartner_change', args=[obj.cp.id])
        return format_html(
            '<a href="{}">{} ({})</a>',
            url,
            obj.cp.user.get_full_name() or obj.cp.user.username,
            obj.cp.cp_code
        )
    cp_link.short_description = 'Channel Partner'
    
    def customer_link(self, obj):
        """Display customer as link"""
        url = reverse('admin:accounts_user_change', args=[obj.customer.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.customer.get_full_name() or obj.customer.username
        )
    customer_link.short_description = 'Customer'
    
    def status_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Active</span>')
        return format_html('<span style="color: #999;">○ Inactive</span>')
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'is_active'
    
    # Bulk Actions
    actions = ['activate_relations', 'deactivate_relations']
    
    def activate_relations(self, request, queryset):
        """Activate relations"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} relation(s) activated.')
    activate_relations.short_description = '✓ Activate Relations'
    
    def deactivate_relations(self, request, queryset):
        """Deactivate relations"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} relation(s) deactivated.')
    deactivate_relations.short_description = '○ Deactivate Relations'


# ============================================
# COMMISSION RULE ADMIN
# ============================================

@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    """Admin for Commission Rule configuration"""
    
    list_display = [
        'name',
        'type_badge',
        'percentage_display',
        'override_display',
        'default_badge',
        'status_badge',
        'effective_period',
    ]
    
    list_filter = [
        CommissionRuleTypeFilter,
        'is_default',
        'is_active',
        'effective_from',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'description',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'effective_from'
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'tier_preview',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'description',
                'commission_type',
            )
        }),
        ('Flat Percentage', {
            'fields': (
                'percentage',
            ),
            'description': 'Used for flat percentage commission type',
        }),
        ('Tiered Commission', {
            'fields': (
                'tiers',
                'tier_preview',
            ),
            'classes': ('collapse',),
            'description': 'JSON format: [{"min": 0, "max": 1000000, "rate": 1.0}, ...]',
        }),
        ('Override Commission', {
            'fields': (
                'override_percentage',
            ),
            'classes': ('collapse',),
            'description': 'Commission for parent CP (override)',
        }),
        ('Settings', {
            'fields': (
                'is_default',
                'is_active',
            )
        }),
        ('Effective Dates', {
            'fields': (
                'effective_from',
                'effective_to',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # Override JSONField widget for tiers
    formfield_overrides = {
        models.JSONField: {'widget': TierJSONWidget}
    }
    
    # Custom display methods
    def type_badge(self, obj):
        """Display commission type badge"""
        colors = {
            'flat': '#007bff',
            'tiered': '#28a745',
            'one_time': '#ffc107',
            'recurring': '#6f42c1',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px; text-transform: uppercase;">{}</span>',
            colors.get(obj.commission_type, '#6c757d'),
            obj.get_commission_type_display()
        )
    type_badge.short_description = 'Type'
    type_badge.admin_order_field = 'commission_type'
    
    def percentage_display(self, obj):
        """Display commission percentage"""
        if obj.commission_type == 'flat':
            return format_html(
                '<strong style="color: #28a745; font-size: 13px;">{}%</strong>',
                obj.percentage
            )
        elif obj.commission_type == 'tiered' and obj.tiers:
            tier_count = len(obj.tiers)
            return format_html(
                '<span style="color: #6c757d;">{} tier{}</span>',
                tier_count,
                's' if tier_count != 1 else ''
            )
        return format_html('<span style="color: #999;">—</span>')
    percentage_display.short_description = 'Rate'
    
    def override_display(self, obj):
        """Display override percentage"""
        if obj.override_percentage > 0:
            return format_html(
                '<span style="color: #6f42c1;">{}%</span>',
                obj.override_percentage
            )
        return format_html('<span style="color: #999;">—</span>')
    override_display.short_description = 'Override'
    
    def default_badge(self, obj):
        """Display default status"""
        if obj.is_default:
            return format_html(
                '<span style="background-color: #ffc107; color: white; padding: 2px 6px; '
                'border-radius: 3px; font-size: 10px;">★ DEFAULT</span>'
            )
        return format_html('<span style="color: #999;">—</span>')
    default_badge.short_description = 'Default'
    default_badge.admin_order_field = 'is_default'
    
    def status_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Active</span>')
        return format_html('<span style="color: #999;">○ Inactive</span>')
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'is_active'
    
    def effective_period(self, obj):
        """Display effective period"""
        from_date = obj.effective_from.strftime('%b %d, %Y')
        if obj.effective_to:
            to_date = obj.effective_to.strftime('%b %d, %Y')
            return format_html('{} → {}', from_date, to_date)
        return format_html('{} → <em>Ongoing</em>', from_date)
    effective_period.short_description = 'Effective Period'
    
    def tier_preview(self, obj):
        """Display tier configuration in readable format"""
        if obj.tiers and isinstance(obj.tiers, list):
            html = '<table style="border-collapse: collapse; width: 100%;">'
            html += '<thead><tr style="background: #f5f5f5;">'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Tier</th>'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Min Amount</th>'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Max Amount</th>'
            html += '<th style="padding: 8px; border: 1px solid #ddd;">Rate (%)</th>'
            html += '</tr></thead><tbody>'
            
            for idx, tier in enumerate(obj.tiers, 1):
                min_amt = tier.get('min', 0)
                max_amt = tier.get('max', 'Unlimited')
                rate = tier.get('rate', 0)
                
                html += '<tr>'
                html += f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{idx}</td>'
                html += f'<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">₹{min_amt:,.2f}</td>'
                
                if isinstance(max_amt, (int, float)):
                    html += f'<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">₹{max_amt:,.2f}</td>'
                else:
                    html += f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{max_amt}</td>'
                
                html += f'<td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #28a745; font-weight: bold;">{rate}%</td>'
                html += '</tr>'
            
            html += '</tbody></table>'
            return format_html(html)
        
        return format_html('<span style="color: #999;">No tiers configured</span>')
    tier_preview.short_description = 'Tier Configuration'
    
    # Bulk Actions
    actions = ['activate_rules', 'deactivate_rules', 'mark_as_default']
    
    def activate_rules(self, request, queryset):
        """Activate rules"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} rule(s) activated.')
    activate_rules.short_description = '✓ Activate Rules'
    
    def deactivate_rules(self, request, queryset):
        """Deactivate rules"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} rule(s) deactivated.')
    deactivate_rules.short_description = '○ Deactivate Rules'
    
    def mark_as_default(self, request, queryset):
        """Mark selected rule as default (only one can be default)"""
        if queryset.count() > 1:
            self.message_user(
                request,
                'Only one rule can be marked as default. Please select only one.',
                level='ERROR'
            )
            return
        
        # Clear all defaults first
        CommissionRule.objects.filter(is_default=True).update(is_default=False)
        
        # Set selected as default
        queryset.update(is_default=True)
        self.message_user(request, 'Default rule updated.')
    mark_as_default.short_description = '★ Mark as Default'


# ============================================
# CP COMMISSION RULE ADMIN
# ============================================

@admin.register(CPCommissionRule)
class CPCommissionRuleAdmin(admin.ModelAdmin):
    """Admin for CP Commission Rule assignments"""
    
    list_display = [
        'cp_link',
        'commission_rule_link',
        'property_link',
        'assigned_at',
    ]
    
    list_filter = [
        'commission_rule__commission_type',
        'assigned_at',
    ]
    
    search_fields = [
        'cp__cp_code',
        'cp__user__username',
        'commission_rule__name',
        'property__name',
    ]
    
    ordering = ['-assigned_at']
    
    date_hierarchy = 'assigned_at'
    
    readonly_fields = ['assigned_at']
    
    fieldsets = (
        ('Assignment', {
            'fields': (
                'cp',
                'commission_rule',
            )
        }),
        ('Property Specific', {
            'fields': (
                'property',
            ),
            'description': 'Leave blank to apply to all properties',
        }),
        ('Timestamp', {
            'fields': (
                'assigned_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    autocomplete_fields = ['cp', 'commission_rule', 'property']
    
    # Custom display methods
    def cp_link(self, obj):
        """Display CP as link"""
        url = reverse('admin:partners_channelpartner_change', args=[obj.cp.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            f'{obj.cp.user.get_full_name() or obj.cp.user.username} ({obj.cp.cp_code})'
        )
    cp_link.short_description = 'Channel Partner'
    
    def commission_rule_link(self, obj):
        """Display rule as link"""
        url = reverse('admin:partners_commissionrule_change', args=[obj.commission_rule.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.commission_rule.name
        )
    commission_rule_link.short_description = 'Commission Rule'
    
    def property_link(self, obj):
        """Display property as link"""
        if obj.property:
            url = reverse('admin:properties_property_change', args=[obj.property.id])
            return format_html('<a href="{}">{}</a>', url, obj.property.name)
        return format_html('<em style="color: #6c757d;">All Properties</em>')
    property_link.short_description = 'Property'
