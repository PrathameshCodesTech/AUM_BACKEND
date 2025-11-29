# commissions/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from decimal import Decimal
from .models import Commission, CommissionPayout


# ============================================
# CUSTOM FILTERS
# ============================================

class CommissionStatusFilter(admin.SimpleListFilter):
    """Filter commissions by status"""
    title = 'commission status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending Approval'),
            ('approved', 'Approved (Not Paid)'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(status='pending')
        if self.value() == 'approved':
            return queryset.filter(status='approved')
        if self.value() == 'paid':
            return queryset.filter(status='paid')
        if self.value() == 'cancelled':
            return queryset.filter(status='cancelled')


class CommissionTypeFilter(admin.SimpleListFilter):
    """Filter by commission type"""
    title = 'commission type'
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return (
            ('direct', 'Direct Commission'),
            ('override', 'Override Commission'),
            ('recurring', 'Recurring Commission'),
            ('bonus', 'Bonus'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(commission_type=self.value())


class PayoutStatusFilter(admin.SimpleListFilter):
    """Filter payouts by status"""
    title = 'payout status'
    parameter_name = 'payout_status'

    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())


# ============================================
# COMMISSION ADMIN
# ============================================

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    """Admin for Commission model"""
    
    list_display = [
        'commission_id',
        'cp_link',
        'investment_link',
        'type_badge',
        'base_amount_display',
        'commission_display',
        'tds_display',
        'net_amount_display',
        'status_badge',
        'created_at',
    ]
    
    list_filter = [
        CommissionStatusFilter,
        CommissionTypeFilter,
        'approved_by',
        'created_at',
        'paid_at',
    ]
    
    search_fields = [
        'commission_id',
        'cp__user__username',
        'cp__user__email',
        'cp__user__first_name',
        'cp__user__last_name',
        'investment__investment_id',
        'payment_reference',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'commission_id',
        'created_at',
        'updated_at',
        'approved_by',
        'approved_at',
        'paid_at',
    ]
    
    fieldsets = (
        ('Commission Details', {
            'fields': (
                'commission_id',
                'cp',
                'investment',
                'commission_type',
                'commission_rule',
            )
        }),
        ('Calculation', {
            'fields': (
                'base_amount',
                'commission_rate',
                'commission_amount',
            )
        }),
        ('Tax Deduction (TDS)', {
            'fields': (
                'tds_percentage',
                'tds_amount',
                'net_amount',
            )
        }),
        ('Status & Approval', {
            'fields': (
                'status',
                'approved_by',
                'approved_at',
            )
        }),
        ('Payment Details', {
            'fields': (
                'paid_at',
                'payment_reference',
                'transaction',
            ),
            'classes': ('collapse',),
        }),
        ('Additional Information', {
            'fields': (
                'notes',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    autocomplete_fields = ['cp', 'investment', 'commission_rule', 'transaction']
    
    # Custom display methods
    def cp_link(self, obj):
        """Display CP as clickable link"""
        url = reverse('admin:partners_channelpartner_change', args=[obj.cp.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.cp.user.get_full_name() or obj.cp.user.username
        )
    cp_link.short_description = 'Channel Partner'
    
    def investment_link(self, obj):
        """Display investment as clickable link"""
        url = reverse('admin:investments_investment_change', args=[obj.investment.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.investment.investment_id
        )
    investment_link.short_description = 'Investment'
    
    def type_badge(self, obj):
        """Display commission type as badge"""
        colors = {
            'direct': '#007bff',
            'override': '#6f42c1',
            'recurring': '#28a745',
            'bonus': '#ffc107',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px; text-transform: uppercase;">{}</span>',
            colors.get(obj.commission_type, '#6c757d'),
            obj.get_commission_type_display()
        )
    type_badge.short_description = 'Type'
    
    def base_amount_display(self, obj):
        """Display base amount with currency"""
        return format_html('₹ {:,.2f}', obj.base_amount)
    base_amount_display.short_description = 'Base Amount'
    base_amount_display.admin_order_field = 'base_amount'
    
    def commission_display(self, obj):
        """Display commission with rate and amount"""
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">₹ {:,.2f}</span><br>'
            '<small style="color: #6c757d;">{}%</small>',
            obj.commission_amount,
            obj.commission_rate
        )
    commission_display.short_description = 'Commission'
    commission_display.admin_order_field = 'commission_amount'
    
    def tds_display(self, obj):
        """Display TDS with percentage"""
        if obj.tds_amount > 0:
            return format_html(
                '<span style="color: #dc3545;">₹ {:,.2f}</span><br>'
                '<small style="color: #6c757d;">{}%</small>',
                obj.tds_amount,
                obj.tds_percentage
            )
        return format_html('<span style="color: #999;">—</span>')
    tds_display.short_description = 'TDS'
    tds_display.admin_order_field = 'tds_amount'
    
    def net_amount_display(self, obj):
        """Display net payable amount"""
        return format_html(
            '<strong style="color: #007bff;">₹ {:,.2f}</strong>',
            obj.net_amount
        )
    net_amount_display.short_description = 'Net Payable'
    net_amount_display.admin_order_field = 'net_amount'
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#ffc107',
            'approved': '#17a2b8',
            'processing': '#6f42c1',
            'paid': '#28a745',
            'cancelled': '#dc3545',
        }
        icons = {
            'pending': '⏳',
            'approved': '✓',
            'processing': '⚙️',
            'paid': '💰',
            'cancelled': '❌',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{} {}</span>',
            colors.get(obj.status, '#6c757d'),
            icons.get(obj.status, ''),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    # Bulk Actions
    actions = [
        'approve_commissions',
        'mark_as_processing',
        'mark_as_paid',
        'cancel_commissions',
        'recalculate_commissions',
    ]
    
    def approve_commissions(self, request, queryset):
        """Bulk approve pending commissions"""
        pending = queryset.filter(status='pending')
        count = pending.update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(
            request,
            f'{count} commission(s) approved successfully.',
            level='SUCCESS'
        )
    approve_commissions.short_description = '✓ Approve selected commissions'
    
    def mark_as_processing(self, request, queryset):
        """Mark approved commissions as processing"""
        approved = queryset.filter(status='approved')
        count = approved.update(status='processing')
        self.message_user(
            request,
            f'{count} commission(s) marked as processing.',
            level='SUCCESS'
        )
    mark_as_processing.short_description = '⚙️ Mark as Processing'
    
    def mark_as_paid(self, request, queryset):
        """Mark commissions as paid"""
        processable = queryset.filter(status__in=['approved', 'processing'])
        count = processable.update(
            status='paid',
            paid_at=timezone.now()
        )
        self.message_user(
            request,
            f'{count} commission(s) marked as paid.',
            level='SUCCESS'
        )
    mark_as_paid.short_description = '💰 Mark as Paid'
    
    def cancel_commissions(self, request, queryset):
        """Cancel commissions"""
        cancelable = queryset.filter(status__in=['pending', 'approved'])
        count = cancelable.update(status='cancelled')
        self.message_user(
            request,
            f'{count} commission(s) cancelled.',
            level='WARNING'
        )
    cancel_commissions.short_description = '❌ Cancel selected commissions'
    
    def recalculate_commissions(self, request, queryset):
        """Recalculate net amounts for pending commissions"""
        pending = queryset.filter(status='pending')
        count = 0
        for commission in pending:
            # Recalculate TDS
            commission.tds_amount = (
                commission.commission_amount * commission.tds_percentage / Decimal('100')
            )
            # Recalculate net
            commission.net_amount = commission.commission_amount - commission.tds_amount
            commission.save(update_fields=['tds_amount', 'net_amount', 'updated_at'])
            count += 1
        
        self.message_user(
            request,
            f'{count} commission(s) recalculated.',
            level='SUCCESS'
        )
    recalculate_commissions.short_description = '🔄 Recalculate Net Amounts'
    
    def save_model(self, request, obj, form, change):
        """Auto-set approved_by when approving"""
        if not change:  # New commission
            obj.created_by = request.user
        
        # If status changed to approved
        if change and 'status' in form.changed_data:
            if obj.status == 'approved' and not obj.approved_by:
                obj.approved_by = request.user
                obj.approved_at = timezone.now()
            elif obj.status == 'paid' and not obj.paid_at:
                obj.paid_at = timezone.now()
        
        super().save_model(request, obj, form, change)


# ============================================
# COMMISSION PAYOUT ADMIN
# ============================================

class CommissionInline(admin.TabularInline):
    """Inline for viewing commissions in payout"""
    model = CommissionPayout.commissions.through
    extra = 0
    readonly_fields = ['commission']
    can_delete = False
    
    verbose_name = 'Commission'
    verbose_name_plural = 'Commissions Included'


@admin.register(CommissionPayout)
class CommissionPayoutAdmin(admin.ModelAdmin):
    """Admin for CommissionPayout model"""
    
    list_display = [
        'payout_id',
        'cp_link',
        'commission_count',
        'total_amount_display',
        'tds_display',
        'net_amount_display',
        'status_badge',
        'payment_mode',
        'paid_at',
    ]
    
    list_filter = [
        PayoutStatusFilter,
        'payment_mode',
        'paid_at',
        'created_at',
    ]
    
    search_fields = [
        'payout_id',
        'cp__user__username',
        'cp__user__email',
        'cp__user__first_name',
        'cp__user__last_name',
        'payment_reference',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'payout_id',
        'created_at',
        'updated_at',
        'processed_by',
    ]
    
    fieldsets = (
        ('Payout Details', {
            'fields': (
                'payout_id',
                'cp',
                'status',
            )
        }),
        ('Amounts', {
            'fields': (
                'total_amount',
                'tds_amount',
                'net_amount',
            )
        }),
        ('Payment Information', {
            'fields': (
                'payment_mode',
                'payment_reference',
                'paid_at',
            )
        }),
        ('Processing', {
            'fields': (
                'processed_by',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    filter_horizontal = ['commissions']
    
    autocomplete_fields = ['cp', 'processed_by']
    
    # Custom display methods
    def cp_link(self, obj):
        """Display CP as clickable link"""
        url = reverse('admin:partners_channelpartner_change', args=[obj.cp.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.cp.user.get_full_name() or obj.cp.user.username
        )
    cp_link.short_description = 'Channel Partner'
    
    def commission_count(self, obj):
        """Display number of commissions"""
        count = obj.commissions.count()
        return format_html(
            '<strong>{}</strong> commission{}',
            count,
            's' if count != 1 else ''
        )
    commission_count.short_description = 'Commissions'
    
    def total_amount_display(self, obj):
        """Display total amount with currency"""
        return format_html('₹ {:,.2f}', obj.total_amount)
    total_amount_display.short_description = 'Total Amount'
    total_amount_display.admin_order_field = 'total_amount'
    
    def tds_display(self, obj):
        """Display TDS amount"""
        if obj.tds_amount > 0:
            return format_html(
                '<span style="color: #dc3545;">₹ {:,.2f}</span>',
                obj.tds_amount
            )
        return format_html('<span style="color: #999;">—</span>')
    tds_display.short_description = 'TDS'
    tds_display.admin_order_field = 'tds_amount'
    
    def net_amount_display(self, obj):
        """Display net payable amount"""
        return format_html(
            '<strong style="color: #007bff; font-size: 14px;">₹ {:,.2f}</strong>',
            obj.net_amount
        )
    net_amount_display.short_description = 'Net Payable'
    net_amount_display.admin_order_field = 'net_amount'
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
        }
        icons = {
            'pending': '⏳',
            'processing': '⚙️',
            'completed': '✓',
            'failed': '❌',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; '
            'border-radius: 3px; font-size: 11px;">{} {}</span>',
            colors.get(obj.status, '#6c757d'),
            icons.get(obj.status, ''),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    # Bulk Actions
    actions = [
        'mark_as_processing',
        'mark_as_completed',
        'mark_as_failed',
        'retry_failed_payouts',
    ]
    
    def mark_as_processing(self, request, queryset):
        """Mark payouts as processing"""
        pending = queryset.filter(status='pending')
        count = pending.update(
            status='processing',
            processed_by=request.user
        )
        self.message_user(
            request,
            f'{count} payout(s) marked as processing.',
            level='SUCCESS'
        )
    mark_as_processing.short_description = '⚙️ Mark as Processing'
    
    def mark_as_completed(self, request, queryset):
        """Mark payouts as completed"""
        processable = queryset.filter(status__in=['pending', 'processing'])
        count = processable.update(
            status='completed',
            paid_at=timezone.now(),
            processed_by=request.user
        )
        
        # Update associated commissions
        for payout in queryset.filter(status='completed'):
            payout.commissions.update(
                status='paid',
                paid_at=payout.paid_at
            )
        
        self.message_user(
            request,
            f'{count} payout(s) completed successfully.',
            level='SUCCESS'
        )
    mark_as_completed.short_description = '✓ Mark as Completed'
    
    def mark_as_failed(self, request, queryset):
        """Mark payouts as failed"""
        processable = queryset.filter(status__in=['pending', 'processing'])
        count = processable.update(status='failed')
        self.message_user(
            request,
            f'{count} payout(s) marked as failed.',
            level='WARNING'
        )
    mark_as_failed.short_description = '❌ Mark as Failed'
    
    def retry_failed_payouts(self, request, queryset):
        """Retry failed payouts"""
        failed = queryset.filter(status='failed')
        count = failed.update(
            status='pending',
            processed_by=None,
            paid_at=None
        )
        self.message_user(
            request,
            f'{count} payout(s) reset for retry.',
            level='SUCCESS'
        )
    retry_failed_payouts.short_description = '🔄 Retry Failed Payouts'
    
    def save_model(self, request, obj, form, change):
        """Auto-set processed_by"""
        if not change:  # New payout
            obj.processed_by = request.user
        
        # If status changed to completed
        if change and 'status' in form.changed_data:
            if obj.status == 'completed' and not obj.paid_at:
                obj.paid_at = timezone.now()
                obj.processed_by = request.user
                
                # Update all associated commissions
                obj.commissions.update(
                    status='paid',
                    paid_at=obj.paid_at
                )
        
        super().save_model(request, obj, form, change)
