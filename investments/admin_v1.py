# investments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count, Q
from decimal import Decimal
from .models import (
    Wallet, Transaction, Investment, InvestmentUnit,
    Payout, RedemptionRequest
)


# ============================================
# CUSTOM FILTERS
# ============================================

class TransactionStatusFilter(admin.SimpleListFilter):
    """Filter transactions by status"""
    title = 'transaction status'
    parameter_name = 'txn_status'

    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())


class TransactionTypeFilter(admin.SimpleListFilter):
    """Filter by transaction type"""
    title = 'transaction type'
    parameter_name = 'txn_type'

    def lookups(self, request, model_admin):
        return (
            ('credit', 'Credit'),
            ('debit', 'Debit'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(transaction_type=self.value())


class InvestmentStatusFilter(admin.SimpleListFilter):
    """Filter investments by status"""
    title = 'investment status'
    parameter_name = 'inv_status'

    def lookups(self, request, model_admin):
        return (
            ('draft', 'Draft'),
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('redeemed', 'Redeemed'),
            ('cancelled', 'Cancelled'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())


class SoftDeleteFilter(admin.SimpleListFilter):
    """Filter for soft deleted records"""
    title = 'deletion status'
    parameter_name = 'deleted'

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


# ============================================
# WALLET ADMIN
# ============================================

class TransactionInline(admin.TabularInline):
    """Inline for viewing wallet transactions"""
    model = Transaction
    extra = 0
    max_num = 10
    can_delete = False

    fields = [
        'transaction_id',
        'transaction_type',
        'purpose',
        'amount_display',
        'status',
        'created_at',
    ]

    readonly_fields = [
        'transaction_id',
        'transaction_type',
        'purpose',
        'amount_display',
        'status',
        'created_at',
    ]

    ordering = ['-created_at']

    verbose_name = 'Recent Transaction'
    verbose_name_plural = 'Recent Transactions (Last 10)'

    def amount_display(self, obj):
        """Display amount with currency"""
        color = '#28a745' if obj.transaction_type == 'credit' else '#dc3545'
        sign = '+' if obj.transaction_type == 'credit' else '-'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} ₹{:,.2f}</span>',
            color,
            sign,
            obj.amount
        )
    amount_display.short_description = 'Amount'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin for Wallet management"""

    list_display = [
        'user_link',
        'balance_display',
        'ledger_balance_display',
        'status_badge',
        'transaction_count',
        'created_at',
    ]

    list_filter = [
        'is_active',
        'is_blocked',
        'created_at',
    ]

    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
    ]

    ordering = ['-balance']

    readonly_fields = [
        'balance',
        'ledger_balance',
        'created_at',
        'updated_at',
    ]

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Balance', {
            'fields': (
                'balance',
                'ledger_balance',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'is_blocked',
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

    inlines = [TransactionInline]

    autocomplete_fields = ['user']

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

    def balance_display(self, obj):
        """Display balance with currency formatting"""
        return format_html(
            '<strong style="color: #007bff; font-size: 14px;">₹ {:,.2f}</strong>',
            obj.balance
        )
    balance_display.short_description = 'Available Balance'
    balance_display.admin_order_field = 'balance'

    def ledger_balance_display(self, obj):
        """Display ledger balance"""
        return format_html('₹ {:,.2f}', obj.ledger_balance)
    ledger_balance_display.short_description = 'Ledger Balance'
    ledger_balance_display.admin_order_field = 'ledger_balance'

    def status_badge(self, obj):
        """Display wallet status"""
        if obj.is_blocked:
            return format_html('<span style="color: #dc3545;">🚫 Blocked</span>')
        elif obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Active</span>')
        else:
            return format_html('<span style="color: #999;">○ Inactive</span>')
    status_badge.short_description = 'Status'

    def transaction_count(self, obj):
        """Count total transactions"""
        count = obj.transactions.count()
        return format_html('<strong>{}</strong>', count)
    transaction_count.short_description = 'Transactions'

    # Bulk Actions
    actions = ['activate_wallets', 'deactivate_wallets',
               'block_wallets', 'unblock_wallets']

    def activate_wallets(self, request, queryset):
        """Activate wallets"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} wallet(s) activated.')
    activate_wallets.short_description = '✓ Activate Wallets'

    def deactivate_wallets(self, request, queryset):
        """Deactivate wallets"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} wallet(s) deactivated.')
    deactivate_wallets.short_description = '○ Deactivate Wallets'

    def block_wallets(self, request, queryset):
        """Block wallets"""
        count = queryset.update(is_blocked=True)
        self.message_user(
            request, f'{count} wallet(s) blocked.', level='WARNING')
    block_wallets.short_description = '🚫 Block Wallets'

    def unblock_wallets(self, request, queryset):
        """Unblock wallets"""
        count = queryset.update(is_blocked=False)
        self.message_user(request, f'{count} wallet(s) unblocked.')
    unblock_wallets.short_description = '🔓 Unblock Wallets'


# ============================================
# TRANSACTION ADMIN
# ============================================

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin for Transaction management"""

    list_display = [
        'transaction_id',
        'user_link',
        'type_badge',
        'purpose_badge',
        'amount_display',
        'balance_change',
        'status_badge',
        'created_at',
    ]

    list_filter = [
        TransactionStatusFilter,
        TransactionTypeFilter,
        'purpose',
        'payment_gateway',
        'created_at',
    ]

    search_fields = [
        'transaction_id',
        'user__username',
        'user__email',
        'gateway_transaction_id',
        'description',
    ]

    ordering = ['-created_at']

    date_hierarchy = 'created_at'

    readonly_fields = [
        'transaction_id',
        'wallet',
        'user',
        'balance_before',
        'balance_after',
        'created_at',
        'updated_at',
        'processed_at',
        'gateway_response_display',
    ]

    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'transaction_id',
                'wallet',
                'user',
                'transaction_type',
                'purpose',
                'amount',
            )
        }),
        ('Balance Tracking', {
            'fields': (
                'balance_before',
                'balance_after',
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'processed_at',
                'processed_by',
            )
        }),
        ('Payment Gateway', {
            'fields': (
                'payment_method',
                'payment_gateway',
                'gateway_transaction_id',
                'gateway_response_display',
            ),
            'classes': ('collapse',),
        }),
        ('Reference', {
            'fields': (
                'reference_type',
                'reference_id',
            ),
            'classes': ('collapse',),
        }),
        ('Notes', {
            'fields': (
                'description',
                'internal_notes',
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

    autocomplete_fields = ['wallet', 'user', 'processed_by']

    # Custom display methods
    def user_link(self, obj):
        """Display user as link"""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.get_full_name() or obj.user.username
        )
    user_link.short_description = 'User'

    def type_badge(self, obj):
        """Display transaction type badge"""
        color = '#28a745' if obj.transaction_type == 'credit' else '#dc3545'
        icon = '↑' if obj.transaction_type == 'credit' else '↓'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{} {}</span>',
            color,
            icon,
            obj.get_transaction_type_display().upper()
        )
    type_badge.short_description = 'Type'
    type_badge.admin_order_field = 'transaction_type'

    def purpose_badge(self, obj):
        """Display purpose badge"""
        colors = {
            'deposit': '#28a745',
            'investment': '#007bff',
            'payout': '#17a2b8',
            'commission': '#6f42c1',
            'redemption': '#ffc107',
            'refund': '#fd7e14',
            'withdrawal': '#dc3545',
            'fee': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.purpose, '#6c757d'),
            obj.get_purpose_display()
        )
    purpose_badge.short_description = 'Purpose'
    purpose_badge.admin_order_field = 'purpose'

    def amount_display(self, obj):
        """Display amount with currency"""
        color = '#28a745' if obj.transaction_type == 'credit' else '#dc3545'
        sign = '+' if obj.transaction_type == 'credit' else '-'
        return format_html(
            '<strong style="color: {}; font-size: 13px;">{} ₹ {:,.2f}</strong>',
            color,
            sign,
            obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def balance_change(self, obj):
        """Show balance before and after"""
        return format_html(
            '₹{:,.2f} → ₹{:,.2f}',
            obj.balance_before,
            obj.balance_after
        )
    balance_change.short_description = 'Balance Change'

    def status_badge(self, obj):
        """Display status badge"""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
        }
        icons = {
            'pending': '⏳',
            'processing': '⚙️',
            'completed': '✓',
            'failed': '❌',
            'cancelled': '○',
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

    def gateway_response_display(self, obj):
        """Display gateway response as formatted JSON"""
        if obj.gateway_response:
            import json
            formatted = json.dumps(obj.gateway_response,
                                   indent=2, ensure_ascii=False)
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; '
                'max-height: 300px; overflow: auto;">{}</pre>',
                formatted
            )
        return format_html('<span style="color: #999;">No gateway response</span>')
    gateway_response_display.short_description = 'Gateway Response'

    # Bulk Actions
    actions = ['mark_as_completed', 'mark_as_failed', 'cancel_transactions']

    def mark_as_completed(self, request, queryset):
        """Mark transactions as completed"""
        count = queryset.filter(status='processing').update(
            status='completed',
            processed_at=timezone.now(),
            processed_by=request.user
        )
        self.message_user(
            request, f'{count} transaction(s) marked as completed.')
    mark_as_completed.short_description = '✓ Mark as Completed'

    def mark_as_failed(self, request, queryset):
        """Mark transactions as failed"""
        count = queryset.filter(status__in=['pending', 'processing']).update(
            status='failed',
            processed_at=timezone.now(),
            processed_by=request.user
        )
        self.message_user(
            request, f'{count} transaction(s) marked as failed.', level='WARNING')
    mark_as_failed.short_description = '❌ Mark as Failed'

    def cancel_transactions(self, request, queryset):
        """Cancel pending transactions"""
        count = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'{count} transaction(s) cancelled.')
    cancel_transactions.short_description = '○ Cancel Transactions'


# ============================================
# INVESTMENT ADMIN
# ============================================

class InvestmentUnitInline(admin.TabularInline):
    """Inline for viewing allocated units"""
    model = InvestmentUnit
    extra = 0
    readonly_fields = ['unit', 'allocated_at']
    can_delete = False

    verbose_name = 'Allocated Unit'
    verbose_name_plural = 'Allocated Units'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    """Admin for Investment management"""

    list_display = [
        'investment_id',
        'customer_link',
        'property_link',
        'amount_display',
        'units_purchased',
        'status_badge',
        'payment_status',
        'referred_by_display',
        'investment_date',
    ]

    list_filter = [
        InvestmentStatusFilter,
        SoftDeleteFilter,
        'payment_completed',
        'referred_by_cp',
        'approved_by',
        'investment_date',
        'created_at',
    ]

    search_fields = [
        'investment_id',
        'customer__username',
        'customer__email',
        'property__name',
        'property__property_id',
    ]

    ordering = ['-created_at']

    date_hierarchy = 'investment_date'

    readonly_fields = [
        'investment_id',
        'investment_date',
        'created_at',
        'updated_at',
        'approved_by',
        'approved_at',
        'payment_completed_at',
        'deleted_at',
        'deleted_by',
    ]

    fieldsets = (
        ('Investment Details', {
            'fields': (
                'investment_id',
                'customer',
                'property',
                'referred_by_cp',
            )
        }),
        ('Financial Details', {
            'fields': (
                'amount',
                'units_purchased',
                'price_per_unit_at_investment',
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'approved_by',
                'approved_at',
                'rejection_reason',
            )
        }),
        ('Payment', {
            'fields': (
                'payment_completed',
                'payment_completed_at',
                'transaction',
            )
        }),
        ('Returns', {
            'fields': (
                'expected_return_amount',
                'actual_return_amount',
            ),
            'classes': ('collapse',),
        }),
        ('Important Dates', {
            'fields': (
                'investment_date',
                'maturity_date',
                'lock_in_end_date',
            )
        }),
        ('Soft Delete', {
            'fields': (
                'is_deleted',
                'deleted_at',
                'deleted_by',
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

    inlines = [InvestmentUnitInline]

    autocomplete_fields = [
        'customer',
        'property',
        'referred_by_cp',
        'approved_by',
        'transaction',
        'deleted_by',
    ]

    # Override queryset to show soft-deleted by default
    def get_queryset(self, request):
        """Include soft-deleted investments"""
        qs = super().get_queryset(request)
        return qs  # Show all by default, use filter to exclude deleted

    # Custom display methods
    def customer_link(self, obj):
        """Display customer as link"""
        url = reverse('admin:accounts_user_change', args=[obj.customer.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.customer.get_full_name() or obj.customer.username
        )
    customer_link.short_description = 'Customer'

    def property_link(self, obj):
        """Display property as link"""
        url = reverse('admin:properties_property_change',
                      args=[obj.property.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.property.name
        )
    property_link.short_description = 'Property'

    def amount_display(self, obj):
        """Display investment amount"""
        return format_html(
            '<strong style="color: #007bff;">₹ {:,.2f}</strong>',
            obj.amount
        )
    amount_display.short_description = 'Investment Amount'
    amount_display.admin_order_field = 'amount'

    def status_badge(self, obj):
        """Display status badge"""
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'approved': '#17a2b8',
            'active': '#28a745',
            'completed': '#6f42c1',
            'redeemed': '#fd7e14',
            'cancelled': '#dc3545',
            'rejected': '#dc3545',
        }

        # Add deleted indicator
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: #000; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 10px;">🗑️ DELETED</span>'
            )

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def payment_status(self, obj):
        """Display payment completion status"""
        if obj.payment_completed:
            return format_html('<span style="color: #28a745;">✓ Paid</span>')
        return format_html('<span style="color: #ffc107;">⏳ Pending</span>')
    payment_status.short_description = 'Payment'
    payment_status.admin_order_field = 'payment_completed'

    def referred_by_display(self, obj):
        """Display referring CP"""
        if obj.referred_by_cp:
            return format_html(
                '<span style="color: #6f42c1;">✓ {}</span>',
                obj.referred_by_cp.user.get_full_name() or obj.referred_by_cp.user.username
            )
        return format_html('<span style="color: #999;">Direct</span>')
    referred_by_display.short_description = 'Referred By'

    # Bulk Actions
    actions = [
        'approve_investments',
        'reject_investments',
        'mark_as_active',
        'cancel_investments',
        'soft_delete_investments',
        'restore_investments',
    ]

    def approve_investments(self, request, queryset):
        """Approve pending investments"""
        count = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{count} investment(s) approved.')
    approve_investments.short_description = '✓ Approve Investments'

    def reject_investments(self, request, queryset):
        """Reject pending investments"""
        count = queryset.filter(status='pending').update(
            status='rejected',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(
            request, f'{count} investment(s) rejected.', level='WARNING')
    reject_investments.short_description = '❌ Reject Investments'

    def mark_as_active(self, request, queryset):
        """Mark approved investments as active"""
        count = queryset.filter(status='approved', payment_completed=True).update(
            status='active'
        )
        self.message_user(request, f'{count} investment(s) activated.')
    mark_as_active.short_description = '✓ Mark as Active'

    def cancel_investments(self, request, queryset):
        """Cancel investments"""
        count = queryset.filter(status__in=['draft', 'pending']).update(
            status='cancelled'
        )
        self.message_user(request, f'{count} investment(s) cancelled.')
    cancel_investments.short_description = '○ Cancel Investments'

    def soft_delete_investments(self, request, queryset):
        """Soft delete investments"""
        count = queryset.filter(is_deleted=False).update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user
        )
        self.message_user(request, f'{count} investment(s) soft deleted.')
    soft_delete_investments.short_description = '🗑️ Soft Delete'

    def restore_investments(self, request, queryset):
        """Restore soft deleted investments"""
        count = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None
        )
        self.message_user(request, f'{count} investment(s) restored.')
    restore_investments.short_description = '↻ Restore Deleted'


# ============================================
# PAYOUT ADMIN
# ============================================

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    """Admin for Payout management"""

    list_display = [
        'payout_id',
        'customer_link',
        'property_link',
        'type_badge',
        'amount_display',
        'period_display',
        'status_badge',
        'created_at',
    ]

    list_filter = [
        'status',
        'payout_type',
        'approved_by',
        'period_start',
        'created_at',
    ]

    search_fields = [
        'payout_id',
        'customer__username',
        'customer__email',
        'property__name',
        'investment__investment_id',
    ]

    ordering = ['-created_at']

    date_hierarchy = 'created_at'

    readonly_fields = [
        'payout_id',
        'created_at',
        'updated_at',
        'approved_by',
        'approved_at',
        'paid_at',
    ]

    fieldsets = (
        ('Payout Details', {
            'fields': (
                'payout_id',
                'investment',
                'customer',
                'property',
            )
        }),
        ('Payout Information', {
            'fields': (
                'payout_type',
                'amount',
                'period_start',
                'period_end',
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'approved_by',
                'approved_at',
            )
        }),
        ('Payment', {
            'fields': (
                'transaction',
                'paid_at',
            )
        }),
        ('Additional Information', {
            'fields': (
                'description',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    autocomplete_fields = [
        'investment',
        'customer',
        'property',
        'approved_by',
        'transaction',
    ]

    # Custom display methods
    def customer_link(self, obj):
        """Display customer as link"""
        url = reverse('admin:accounts_user_change', args=[obj.customer.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.customer.get_full_name() or obj.customer.username
        )
    customer_link.short_description = 'Customer'

    def property_link(self, obj):
        """Display property as link"""
        url = reverse('admin:properties_property_change',
                      args=[obj.property.id])
        return format_html('<a href="{}">{}</a>', url, obj.property.name)
    property_link.short_description = 'Property'

    def type_badge(self, obj):
        """Display payout type badge"""
        colors = {
            'rental': '#28a745',
            'profit': '#007bff',
            'capital_appreciation': '#17a2b8',
            'dividend': '#6f42c1',
            'interest': '#ffc107',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.payout_type, '#6c757d'),
            obj.get_payout_type_display()
        )
    type_badge.short_description = 'Type'

    def amount_display(self, obj):
        """Display payout amount"""
        return format_html(
            '<strong style="color: #28a745; font-size: 13px;">₹ {:,.2f}</strong>',
            obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def period_display(self, obj):
        """Display payout period"""
        if obj.period_start and obj.period_end:
            return format_html(
                '{} to {}',
                obj.period_start.strftime('%b %Y'),
                obj.period_end.strftime('%b %Y')
            )
        return format_html('<span style="color: #999;">—</span>')
    period_display.short_description = 'Period'

    def status_badge(self, obj):
        """Display status badge"""
        colors = {
            'pending': '#ffc107',
            'approved': '#17a2b8',
            'processing': '#6f42c1',
            'completed': '#28a745',
            'failed': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'

    # Bulk Actions
    actions = ['approve_payouts', 'mark_as_processing', 'mark_as_completed']

    def approve_payouts(self, request, queryset):
        """Approve pending payouts"""
        count = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{count} payout(s) approved.')
    approve_payouts.short_description = '✓ Approve Payouts'

    def mark_as_processing(self, request, queryset):
        """Mark as processing"""
        count = queryset.filter(status='approved').update(status='processing')
        self.message_user(request, f'{count} payout(s) marked as processing.')
    mark_as_processing.short_description = '⚙️ Mark as Processing'

    def mark_as_completed(self, request, queryset):
        """Mark as completed"""
        count = queryset.filter(status__in=['approved', 'processing']).update(
            status='completed',
            paid_at=timezone.now()
        )
        self.message_user(request, f'{count} payout(s) completed.')
    mark_as_completed.short_description = '✓ Mark as Completed'


# ============================================
# REDEMPTION REQUEST ADMIN
# ============================================

@admin.register(RedemptionRequest)
class RedemptionRequestAdmin(admin.ModelAdmin):
    """Admin for Redemption Request management"""

    list_display = [
        'request_id',
        'customer_link',
        'investment_link',
        'units_to_redeem',
        'requested_amount_display',
        'lock_in_indicator',
        'status_badge',
        'created_at',
    ]

    list_filter = [
        'status',
        'is_within_lockin',
        'reviewed_by',
        'created_at',
    ]

    search_fields = [
        'request_id',
        'customer__username',
        'customer__email',
        'investment__investment_id',
    ]

    ordering = ['-created_at']

    date_hierarchy = 'created_at'

    readonly_fields = [
        'request_id',
        'created_at',
        'updated_at',
        'reviewed_by',
        'reviewed_at',
        'completed_at',
    ]

    fieldsets = (
        ('Request Details', {
            'fields': (
                'request_id',
                'investment',
                'customer',
            )
        }),
        ('Redemption Information', {
            'fields': (
                'units_to_redeem',
                'requested_amount',
                'approved_amount',
            )
        }),
        ('Lock-in & Penalty', {
            'fields': (
                'is_within_lockin',
                'penalty_amount',
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'reviewed_by',
                'reviewed_at',
                'rejection_reason',
            )
        }),
        ('Completion', {
            'fields': (
                'transaction',
                'completed_at',
            )
        }),
        ('Notes', {
            'fields': (
                'customer_notes',
                'admin_notes',
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

    autocomplete_fields = [
        'investment',
        'customer',
        'reviewed_by',
        'transaction',
    ]

    # Custom display methods
    def customer_link(self, obj):
        """Display customer as link"""
        url = reverse('admin:accounts_user_change', args=[obj.customer.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.customer.get_full_name() or obj.customer.username
        )
    customer_link.short_description = 'Customer'

    def investment_link(self, obj):
        """Display investment as link"""
        url = reverse('admin:investments_investment_change',
                      args=[obj.investment.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.investment.investment_id
        )
    investment_link.short_description = 'Investment'

    def requested_amount_display(self, obj):
        """Display requested amount"""
        html = format_html(
            '<strong style="color: #007bff;">₹ {:,.2f}</strong>',
            obj.requested_amount
        )

        if obj.penalty_amount > 0:
            html += format_html(
                '<br><small style="color: #dc3545;">Penalty: ₹{:,.2f}</small>',
                obj.penalty_amount
            )

        return html
    requested_amount_display.short_description = 'Requested Amount'

    def lock_in_indicator(self, obj):
        """Display lock-in status"""
        if obj.is_within_lockin:
            return format_html(
                '<span style="color: #dc3545;">🔒 Within Lock-in</span>'
            )
        return format_html('<span style="color: #28a745;">✓ Free</span>')
    lock_in_indicator.short_description = 'Lock-in'

    def status_badge(self, obj):
        """Display status badge"""
        colors = {
            'pending': '#ffc107',
            'under_review': '#17a2b8',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'completed': '#6f42c1',
            'cancelled': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'

    # Bulk Actions
    actions = [
        'mark_under_review',
        'approve_redemptions',
        'reject_redemptions',
        'mark_as_completed',
    ]

    def mark_under_review(self, request, queryset):
        """Mark as under review"""
        count = queryset.filter(status='pending').update(
            status='under_review',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{count} request(s) marked under review.')
    mark_under_review.short_description = '🔍 Mark Under Review'

    def approve_redemptions(self, request, queryset):
        """Approve redemption requests"""
        count = queryset.filter(status__in=['pending', 'under_review']).update(
            status='approved',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{count} redemption(s) approved.')
    approve_redemptions.short_description = '✓ Approve Redemptions'

    def reject_redemptions(self, request, queryset):
        """Reject redemption requests"""
        count = queryset.filter(status__in=['pending', 'under_review']).update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(
            request, f'{count} redemption(s) rejected.', level='WARNING')
    reject_redemptions.short_description = '❌ Reject Redemptions'

    def mark_as_completed(self, request, queryset):
        """Mark as completed"""
        count = queryset.filter(status='approved').update(
            status='completed',
            completed_at=timezone.now()
        )

        # Update investment status
        for redemption in queryset.filter(status='completed'):
            redemption.investment.status = 'redeemed'
            redemption.investment.save(update_fields=['status'])

        self.message_user(request, f'{count} redemption(s) completed.')
    mark_as_completed.short_description = '✓ Mark as Completed'

    def save_model(self, request, obj, form, change):
        """Auto-set reviewed_by when status changes"""
        if change and 'status' in form.changed_data:
            if obj.status in ['under_review', 'approved', 'rejected']:
                if not obj.reviewed_by:
                    obj.reviewed_by = request.user
                if not obj.reviewed_at:
                    obj.reviewed_at = timezone.now()

            if obj.status == 'completed' and not obj.completed_at:
                obj.completed_at = timezone.now()
                # Update investment
                obj.investment.status = 'redeemed'
                obj.investment.save(update_fields=['status'])

        super().save_model(request, obj, form, change)
