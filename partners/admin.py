# partners/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ChannelPartner, CPCustomerRelation, CommissionRule, CPCommissionRule
)


# ============================================
# INLINE ADMINS
# ============================================
class CPCustomerRelationInline(admin.TabularInline):
    model = CPCustomerRelation
    extra = 0
    fields = ('customer', 'referral_code', 'referral_date', 'is_active')
    readonly_fields = ('referral_date',)
    autocomplete_fields = ['customer']


class CPCommissionRuleInline(admin.TabularInline):
    model = CPCommissionRule
    extra = 1
    fields = ('commission_rule', 'property', 'assigned_at')
    readonly_fields = ('assigned_at',)
    autocomplete_fields = ['commission_rule', 'property']


class SubCPInline(admin.TabularInline):
    model = ChannelPartner
    fk_name = 'parent_cp'
    extra = 0
    fields = ('user', 'cp_code', 'is_active', 'is_verified')
    readonly_fields = ('cp_code',)
    autocomplete_fields = ['user']
    verbose_name = "Sub Channel Partner"
    verbose_name_plural = "Sub Channel Partners"


# ============================================
# CHANNEL PARTNER ADMIN
# ============================================
@admin.register(ChannelPartner)
class ChannelPartnerAdmin(admin.ModelAdmin):
    list_display = (
        'cp_code', 'user', 'organization', 'hierarchy_badge',
        'colored_status', 'customer_count', 'commission_count',
        'target_display', 'verified_by', 'created_at'
    )
    list_filter = (
        'is_active', 'is_verified', 'organization',
        'parent_cp', 'created_at', 'verified_at'
    )
    search_fields = (
        'cp_code', 'user__username', 'user__email',
        'company_name', 'pan_number', 'gst_number'
    )
    autocomplete_fields = [
        'user', 'organization', 'parent_cp',
        'verified_by', 'onboarded_by'
    ]
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'organization', 'cp_code')
        }),
        ('Hierarchy', {
            'fields': ('parent_cp',)
        }),
        ('Company Details', {
            'fields': ('company_name', 'pan_number', 'gst_number'),
            'classes': ('collapse',)
        }),
        ('Bank Details', {
            'fields': (
                'bank_name', 'account_number', 'ifsc_code', 'account_holder_name'
            ),
            'classes': ('collapse',)
        }),
        ('Targets', {
            'fields': ('monthly_target', 'quarterly_target', 'yearly_target'),
            'classes': ('collapse',)
        }),
        ('Status & Verification', {
            'fields': ('is_active', 'is_verified', 'verified_by', 'verified_at')
        }),
        ('Onboarding', {
            'fields': ('onboarded_by',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'verified_at')

    inlines = [SubCPInline, CPCustomerRelationInline, CPCommissionRuleInline]

    list_per_page = 50

    actions = ['verify_cps', 'activate_cps', 'deactivate_cps']

    def hierarchy_badge(self, obj):
        level = obj.get_hierarchy_level()
        colors = {
            0: '#007bff',  # Blue - Master CP
            1: '#28a745',  # Green - Level 1
            2: '#ffc107',  # Yellow - Level 2
            3: '#fd7e14',  # Orange - Level 3
        }
        color = colors.get(level, '#6c757d')

        labels = {
            0: 'Master CP',
            1: 'Sub-CP L1',
            2: 'Sub-CP L2',
            3: 'Sub-CP L3',
        }
        label = labels.get(level, f'Level {level}')

        # Show parent if exists
        parent_info = ''
        if obj.parent_cp:
            parent_info = f'<br><span style="font-size: 9px; color: #6c757d;">↳ {obj.parent_cp.cp_code}</span>'

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px; '
            'font-weight: 600;">{}</span>{}',
            color, label, parent_info
        )
    hierarchy_badge.short_description = 'Hierarchy'

    def colored_status(self, obj):
        if obj.is_verified and obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">✓ Verified & Active</span>'
            )
        elif obj.is_active:
            return format_html(
                '<span style="background-color: #ffc107; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">⏳ Active</span>'
            )
        elif obj.is_verified:
            return format_html(
                '<span style="background-color: #6c757d; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">✓ Verified</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">✗ Inactive</span>'
            )
    colored_status.short_description = 'Status'

    def customer_count(self, obj):
        count = obj.customers.filter(is_active=True).count()
        return format_html(
            '<span style="background-color: #007bff; color: white; '
            'padding: 3px 10px; border-radius: 50%; font-size: 11px; '
            'font-weight: 600;">{}</span>',
            count
        )
    customer_count.short_description = 'Customers'

    def commission_count(self, obj):
        count = obj.commissions.count()
        return format_html(
            '<span style="background-color: #28a745; color: white; '
            'padding: 3px 10px; border-radius: 50%; font-size: 11px; '
            'font-weight: 600;">{}</span>',
            count
        )
    commission_count.short_description = 'Commissions'

    def target_display(self, obj):
        if obj.monthly_target > 0:
            return format_html(
                '<span style="font-weight: 600; color: #495057;">₹{:,.0f}</span>'
                '<span style="color: #6c757d; font-size: 10px;"> /month</span>',
                obj.monthly_target
            )
        return format_html('<span style="color: #6c757d;">-</span>')
    target_display.short_description = 'Monthly Target'
    target_display.admin_order_field = 'monthly_target'

    # Admin Actions
    def verify_cps(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_verified=False).update(
            is_verified=True,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} channel partner(s) verified.')
    verify_cps.short_description = "✓ Verify channel partners"

    def activate_cps(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} channel partner(s) activated.')
    activate_cps.short_description = "▶ Activate channel partners"

    def deactivate_cps(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request, f'{updated} channel partner(s) deactivated.', level='warning')
    deactivate_cps.short_description = "⏸ Deactivate channel partners"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'user', 'organization', 'parent_cp', 'verified_by', 'onboarded_by'
        ).annotate(
            _customer_count=Count(
                'customers', filter=Q(customers__is_active=True)),
            _commission_count=Count('commissions')
        )


# ============================================
# CP CUSTOMER RELATION ADMIN
# ============================================
@admin.register(CPCustomerRelation)
class CPCustomerRelationAdmin(admin.ModelAdmin):
    list_display = (
        'customer', 'cp', 'organization', 'referral_code',
        'colored_status', 'referral_date'
    )
    list_filter = (
        'is_active', 'organization', 'referral_date'
    )
    search_fields = (
        'customer__username', 'customer__email',
        'cp__user__username', 'cp__cp_code', 'referral_code'
    )
    autocomplete_fields = ['cp', 'customer', 'organization']
    ordering = ('-referral_date',)
    date_hierarchy = 'referral_date'

    fieldsets = (
        ('Relationship', {
            'fields': ('cp', 'customer', 'organization')
        }),
        ('Referral Info', {
            'fields': ('referral_code', 'referral_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    readonly_fields = ('referral_date',)

    list_per_page = 50

    def colored_status(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">● Active</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">● Inactive</span>'
        )
    colored_status.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('cp', 'cp__user', 'customer', 'organization')


# ============================================
# COMMISSION RULE ADMIN
# ============================================
@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'organization', 'colored_type', 'percentage_display',
        'override_display', 'colored_status', 'is_default',
        'effective_period', 'created_at'
    )
    list_filter = (
        'commission_type', 'is_default', 'is_active',
        'organization', 'effective_from', 'effective_to'
    )
    search_fields = (
        'name', 'description', 'organization__name'
    )
    autocomplete_fields = ['organization']
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Info', {
            'fields': ('organization', 'name', 'description')
        }),
        ('Commission Type', {
            'fields': ('commission_type', 'percentage', 'tiers')
        }),
        ('Override', {
            'fields': ('override_percentage',),
            'description': 'Commission percentage for parent/referring CP'
        }),
        ('Applicability', {
            'fields': ('is_default', 'is_active')
        }),
        ('Effective Period', {
            'fields': ('effective_from', 'effective_to')
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    list_per_page = 50

    actions = ['mark_as_default', 'activate_rules', 'deactivate_rules']

    def colored_type(self, obj):
        colors = {
            'flat': '#007bff',       # Blue
            'tiered': '#28a745',     # Green
            'one_time': '#ffc107',   # Yellow
            'recurring': '#17a2b8',  # Cyan
        }
        color = colors.get(obj.commission_type, '#6c757d')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_commission_type_display()
        )
    colored_type.short_description = 'Type'
    colored_type.admin_order_field = 'commission_type'

    def percentage_display(self, obj):
        if obj.commission_type == 'tiered' and obj.tiers:
            return format_html(
                '<span style="font-weight: 600; color: #28a745;">Tiered</span><br>'
                '<span style="font-size: 10px; color: #6c757d;">{} tier(s)</span>',
                len(obj.tiers)
            )
        return format_html(
            '<span style="font-weight: 700; color: #007bff; font-size: 13px;">{}%</span>',
            obj.percentage
        )
    percentage_display.short_description = 'Commission Rate'
    percentage_display.admin_order_field = 'percentage'

    def override_display(self, obj):
        if obj.override_percentage > 0:
            return format_html(
                '<span style="font-weight: 600; color: #6f42c1;">{}%</span>',
                obj.override_percentage
            )
        return format_html('<span style="color: #6c757d;">-</span>')
    override_display.short_description = 'Override'
    override_display.admin_order_field = 'override_percentage'

    def colored_status(self, obj):
        if obj.is_active:
            color = '#28a745'  # Green
            status = '✓ Active'
        else:
            color = '#6c757d'  # Gray
            status = 'Inactive'

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, status
        )
    colored_status.short_description = 'Status'

    def effective_period(self, obj):
        from_date = obj.effective_from.strftime('%d %b %Y')
        to_date = obj.effective_to.strftime(
            '%d %b %Y') if obj.effective_to else 'Ongoing'

        return format_html(
            '<span style="font-size: 11px; color: #495057;">{}</span><br>'
            '<span style="font-size: 10px; color: #6c757d;">to {}</span>',
            from_date, to_date
        )
    effective_period.short_description = 'Effective Period'

    # Admin Actions
    def mark_as_default(self, request, queryset):
        # First, unmark all defaults in the same organization
        for rule in queryset:
            CommissionRule.objects.filter(
                organization=rule.organization,
                is_default=True
            ).update(is_default=False)

            # Mark this rule as default
            rule.is_default = True
            rule.save()

        self.message_user(
            request, f'{queryset.count()} rule(s) set as default.')
    mark_as_default.short_description = "⭐ Set as default rule"

    def activate_rules(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} rule(s) activated.')
    activate_rules.short_description = "✓ Activate rules"

    def deactivate_rules(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request, f'{updated} rule(s) deactivated.', level='warning')
    deactivate_rules.short_description = "✗ Deactivate rules"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('organization')


# ============================================
# CP COMMISSION RULE ADMIN
# ============================================
@admin.register(CPCommissionRule)
class CPCommissionRuleAdmin(admin.ModelAdmin):
    list_display = (
        'cp', 'commission_rule', 'property', 'rule_details', 'assigned_at'
    )
    list_filter = (
        'cp__organization', 'commission_rule', 'assigned_at'
    )
    search_fields = (
        'cp__user__username', 'cp__cp_code',
        'commission_rule__name', 'property__name'
    )
    autocomplete_fields = ['cp', 'commission_rule', 'property']
    ordering = ('-assigned_at',)
    date_hierarchy = 'assigned_at'

    fieldsets = (
        ('Assignment', {
            'fields': ('cp', 'commission_rule', 'property')
        }),
    )

    readonly_fields = ('assigned_at',)

    list_per_page = 50

    def rule_details(self, obj):
        rule = obj.commission_rule

        if rule.commission_type == 'flat':
            return format_html(
                '<span style="font-weight: 600; color: #007bff;">{}%</span> '
                '<span style="font-size: 10px; color: #6c757d;">flat</span>',
                rule.percentage
            )
        elif rule.commission_type == 'tiered':
            return format_html(
                '<span style="font-weight: 600; color: #28a745;">Tiered</span> '
                '<span style="font-size: 10px; color: #6c757d;">({} tiers)</span>',
                len(rule.tiers) if rule.tiers else 0
            )
        else:
            return format_html(
                '<span style="font-size: 11px; color: #6c757d;">{}</span>',
                rule.get_commission_type_display()
            )
    rule_details.short_description = 'Rule Details'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'cp', 'cp__user', 'commission_rule',
            'commission_rule__organization', 'property'
        )
