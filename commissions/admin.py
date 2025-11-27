# commissions/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Commission, CommissionPayout


# ============================================
# COMMISSION ADMIN
# ============================================
@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = (
        'commission_id', 'cp', 'colored_type', 'base_amount_display',
        'commission_amount_display', 'net_amount_display',
        'colored_status', 'created_at'
    )
    list_filter = (
        'status', 'commission_type', 'organization',
        'created_at', 'approved_at', 'paid_at'
    )
    search_fields = (
        'commission_id', 'cp__user__username', 'cp__cp_code',
        'investment__investment_id', 'payment_reference'
    )
    autocomplete_fields = ['cp', 'organization',
                           'investment', 'approved_by', 'commission_rule']
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Commission Info', {
            'fields': ('commission_id', 'cp', 'organization', 'investment')
        }),
        ('Commission Details', {
            'fields': ('commission_type', 'base_amount', 'commission_rate',
                       'commission_amount', 'commission_rule')
        }),
        ('Tax Calculation', {
            'fields': ('tds_percentage', 'tds_amount', 'net_amount')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Payment Details', {
            'fields': ('paid_at', 'payment_reference', 'transaction'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'paid_at')

    list_per_page = 50

    actions = ['approve_commissions', 'mark_as_paid', 'cancel_commissions']

    def colored_type(self, obj):
        colors = {
            'direct': '#007bff',      # Blue
            'override': '#6f42c1',    # Purple
            'recurring': '#28a745',   # Green
            'bonus': '#ffc107',       # Yellow
        }
        color = colors.get(obj.commission_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px; '
            'font-weight: 500;">{}</span>',
            color, obj.get_commission_type_display()
        )
    colored_type.short_description = 'Type'
    colored_type.admin_order_field = 'commission_type'

    def colored_status(self, obj):
        colors = {
            'pending': '#6c757d',     # Gray
            'approved': '#17a2b8',    # Cyan
            'processing': '#ffc107',  # Yellow
            'paid': '#28a745',        # Green
            'cancelled': '#dc3545',   # Red
        }
        color = colors.get(obj.status, '#6c757d')

        # Add icon based on status
        icons = {
            'pending': '⏳',
            'approved': '✓',
            'processing': '⚙️',
            'paid': '✓✓',
            'cancelled': '✗'
        }
        icon = icons.get(obj.status, '')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px; '
            'font-weight: 500;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def base_amount_display(self, obj):
        return format_html(
            '<span style="font-weight: 600; color: #495057;">₹{:,.2f}</span>',
            obj.base_amount
        )
    base_amount_display.short_description = 'Base Amount'
    base_amount_display.admin_order_field = 'base_amount'

    def commission_amount_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #007bff;">₹{:,.2f}</span> '
            '<span style="color: #6c757d; font-size: 11px;">(@{}%)</span>',
            obj.commission_amount, obj.commission_rate
        )
    commission_amount_display.short_description = 'Commission'
    commission_amount_display.admin_order_field = 'commission_amount'

    def net_amount_display(self, obj):
        tds_text = f'- TDS ₹{obj.tds_amount:,.2f}' if obj.tds_amount > 0 else ''
        return format_html(
            '<span style="font-weight: 700; color: #28a745; font-size: 13px;">₹{:,.2f}</span><br>'
            '<span style="color: #dc3545; font-size: 10px;">{}</span>',
            obj.net_amount, tds_text
        )
    net_amount_display.short_description = 'Net Payable'
    net_amount_display.admin_order_field = 'net_amount'

    # Admin Actions
    def approve_commissions(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(
            request, f'{updated} commission(s) approved successfully.')
    approve_commissions.short_description = "✓ Approve selected commissions"

    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['approved', 'processing']).update(
            status='paid',
            paid_at=timezone.now()
        )
        self.message_user(request, f'{updated} commission(s) marked as paid.')
    mark_as_paid.short_description = "💰 Mark as paid"

    def cancel_commissions(self, request, queryset):
        updated = queryset.filter(status__in=['pending', 'approved']).update(
            status='cancelled'
        )
        self.message_user(
            request, f'{updated} commission(s) cancelled.', level='warning')
    cancel_commissions.short_description = "✗ Cancel selected commissions"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'cp', 'cp__user', 'organization', 'investment',
            'approved_by', 'commission_rule'
        )


# ============================================
# COMMISSION PAYOUT ADMIN
# ============================================
class CommissionInline(admin.TabularInline):
    model = CommissionPayout.commissions.through
    extra = 0
    verbose_name = "Commission"
    verbose_name_plural = "Commissions in this Payout"
    can_delete = False

    fields = ('commission', 'get_commission_amount', 'get_commission_status')
    readonly_fields = ('commission', 'get_commission_amount',
                       'get_commission_status')

    def get_commission_amount(self, obj):
        if obj.commission:
            return format_html('₹{:,.2f}', obj.commission.commission_amount)
        return '-'
    get_commission_amount.short_description = 'Amount'

    def get_commission_status(self, obj):
        if obj.commission:
            colors = {
                'pending': '#6c757d',
                'approved': '#17a2b8',
                'processing': '#ffc107',
                'paid': '#28a745',
                'cancelled': '#dc3545',
            }
            color = colors.get(obj.commission.status, '#6c757d')
            return format_html(
                '<span style="background-color: {}; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 10px;">{}</span>',
                color, obj.commission.get_status_display()
            )
        return '-'
    get_commission_status.short_description = 'Status'


@admin.register(CommissionPayout)
class CommissionPayoutAdmin(admin.ModelAdmin):
    list_display = (
        'payout_id', 'cp', 'commission_count', 'total_amount_display',
        'tds_amount_display', 'net_amount_display', 'colored_status',
        'created_at'
    )
    list_filter = (
        'status', 'organization', 'payment_mode',
        'created_at', 'paid_at'
    )
    search_fields = (
        'payout_id', 'cp__user__username', 'cp__cp_code',
        'payment_reference'
    )
    autocomplete_fields = ['cp', 'organization', 'processed_by']
    filter_horizontal = ['commissions']
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Payout Info', {
            'fields': ('payout_id', 'cp', 'organization')
        }),
        ('Amount Details', {
            'fields': ('total_amount', 'tds_amount', 'net_amount')
        }),
        ('Commissions', {
            'fields': ('commissions',),
            'classes': ('wide',)
        }),
        ('Status', {
            'fields': ('status', 'processed_by')
        }),
        ('Payment Details', {
            'fields': ('payment_mode', 'payment_reference', 'paid_at')
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'paid_at')

    list_per_page = 50

    actions = ['process_payouts', 'mark_completed', 'mark_failed']

    def colored_status(self, obj):
        colors = {
            'pending': '#6c757d',     # Gray
            'processing': '#ffc107',  # Yellow
            'completed': '#28a745',   # Green
            'failed': '#dc3545',      # Red
        }
        color = colors.get(obj.status, '#6c757d')

        icons = {
            'pending': '⏳',
            'processing': '⚙️',
            'completed': '✓',
            'failed': '✗'
        }
        icon = icons.get(obj.status, '')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 12px; border-radius: 3px; font-size: 12px; '
            'font-weight: 600;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def commission_count(self, obj):
        count = obj.commissions.count()
        return format_html(
            '<span style="background-color: #007bff; color: white; '
            'padding: 3px 10px; border-radius: 50%; font-size: 11px; '
            'font-weight: 600;">{}</span>',
            count
        )
    commission_count.short_description = 'Commissions'

    def total_amount_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #495057; font-size: 13px;">₹{:,.2f}</span>',
            obj.total_amount
        )
    total_amount_display.short_description = 'Total Amount'
    total_amount_display.admin_order_field = 'total_amount'

    def tds_amount_display(self, obj):
        if obj.tds_amount > 0:
            return format_html(
                '<span style="font-weight: 600; color: #dc3545;">-₹{:,.2f}</span>',
                obj.tds_amount
            )
        return format_html('<span style="color: #6c757d;">-</span>')
    tds_amount_display.short_description = 'TDS'
    tds_amount_display.admin_order_field = 'tds_amount'

    def net_amount_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #28a745; font-size: 14px;">₹{:,.2f}</span>',
            obj.net_amount
        )
    net_amount_display.short_description = 'Net Payable'
    net_amount_display.admin_order_field = 'net_amount'

    # Admin Actions
    def process_payouts(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='processing',
            processed_by=request.user
        )
        self.message_user(
            request, f'{updated} payout(s) marked as processing.')
    process_payouts.short_description = "⚙️ Start processing payouts"

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='processing').update(
            status='completed',
            paid_at=timezone.now()
        )
        self.message_user(
            request, f'{updated} payout(s) marked as completed.', level='success')
    mark_completed.short_description = "✓ Mark as completed"

    def mark_failed(self, request, queryset):
        updated = queryset.filter(status='processing').update(
            status='failed'
        )
        self.message_user(
            request, f'{updated} payout(s) marked as failed.', level='error')
    mark_failed.short_description = "✗ Mark as failed"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'cp', 'cp__user', 'organization', 'processed_by'
        ).prefetch_related('commissions')

    # Custom view for payout summary
    def changelist_view(self, request, extra_context=None):
        # Summary stats
        response = super().changelist_view(request, extra_context)

        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        metrics = {
            'total_pending': qs.filter(status='pending').aggregate(
                total=Sum('net_amount'))['total'] or 0,
            'total_processing': qs.filter(status='processing').aggregate(
                total=Sum('net_amount'))['total'] or 0,
            'total_completed': qs.filter(status='completed').aggregate(
                total=Sum('net_amount'))['total'] or 0,
        }

        response.context_data['summary'] = metrics
        return response
