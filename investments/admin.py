# investments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q, Avg
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Wallet, Transaction, Investment, InvestmentUnit,
    Payout, RedemptionRequest
)


# ============================================
# INLINE ADMINS
# ============================================
class InvestmentUnitInline(admin.TabularInline):
    model = InvestmentUnit
    extra = 0
    fields = ('unit', 'allocated_at')
    readonly_fields = ('allocated_at',)
    autocomplete_fields = ['unit']


# ============================================
# WALLET ADMIN
# ============================================
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'organization', 'balance_display', 'ledger_balance_display',
        'colored_status', 'transaction_count', 'updated_at'
    )
    list_filter = (
        'is_active', 'is_blocked', 'organization', 'created_at'
    )
    search_fields = (
        'user__username', 'user__email', 'organization__name'
    )
    autocomplete_fields = ['user', 'organization']
    ordering = ('-balance',)

    fieldsets = (
        ('Wallet Info', {
            'fields': ('user', 'organization')
        }),
        ('Balance', {
            'fields': ('balance', 'ledger_balance')
        }),
        ('Status', {
            'fields': ('is_active', 'is_blocked')
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    list_per_page = 50

    actions = ['activate_wallets', 'block_wallets']

    def balance_display(self, obj):
        color = '#28a745' if obj.balance > 0 else '#6c757d'
        return format_html(
            '<span style="font-weight: 700; color: {}; font-size: 14px;">₹{:,.2f}</span>',
            color, obj.balance
        )
    balance_display.short_description = 'Balance'
    balance_display.admin_order_field = 'balance'

    def ledger_balance_display(self, obj):
        return format_html(
            '<span style="font-weight: 600; color: #6c757d;">₹{:,.2f}</span>',
            obj.ledger_balance
        )
    ledger_balance_display.short_description = 'Ledger Balance'
    ledger_balance_display.admin_order_field = 'ledger_balance'

    def colored_status(self, obj):
        if obj.is_blocked:
            return format_html(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">🔒 Blocked</span>'
            )
        elif obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">✓ Active</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">Inactive</span>'
        )
    colored_status.short_description = 'Status'

    def transaction_count(self, obj):
        count = obj.transactions.count()
        return format_html(
            '<span style="background-color: #007bff; color: white; '
            'padding: 3px 10px; border-radius: 50%; font-size: 11px;">{}</span>',
            count
        )
    transaction_count.short_description = 'Transactions'

    # Admin Actions
    def activate_wallets(self, request, queryset):
        updated = queryset.update(is_active=True, is_blocked=False)
        self.message_user(request, f'{updated} wallet(s) activated.')
    activate_wallets.short_description = "✓ Activate wallets"

    def block_wallets(self, request, queryset):
        updated = queryset.update(is_blocked=True)
        self.message_user(
            request, f'{updated} wallet(s) blocked.', level='warning')
    block_wallets.short_description = "🔒 Block wallets"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'organization').annotate(
            _transaction_count=Count('transactions')
        )


# ============================================
# TRANSACTION ADMIN
# ============================================
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id', 'user', 'colored_type', 'colored_purpose',
        'amount_display', 'colored_status', 'payment_method', 'created_at'
    )
    list_filter = (
        'transaction_type', 'purpose', 'status', 'payment_method',
        'organization', 'created_at'
    )
    search_fields = (
        'transaction_id', 'user__username', 'user__email',
        'gateway_transaction_id', 'description'
    )
    autocomplete_fields = ['wallet', 'user', 'organization', 'processed_by']
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Transaction Info', {
            'fields': ('transaction_id', 'wallet', 'user', 'organization')
        }),
        ('Transaction Details', {
            'fields': ('transaction_type', 'purpose', 'amount')
        }),
        ('Balance Tracking', {
            'fields': ('balance_before', 'balance_after')
        }),
        ('Status', {
            'fields': ('status', 'processed_by', 'processed_at')
        }),
        ('Payment Gateway', {
            'fields': ('payment_method', 'payment_gateway',
                       'gateway_transaction_id', 'gateway_response'),
            'classes': ('collapse',)
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('description', 'internal_notes'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'processed_at')

    list_per_page = 100

    actions = ['mark_completed', 'mark_failed']

    def colored_type(self, obj):
        colors = {
            'credit': '#28a745',  # Green
            'debit': '#dc3545',   # Red
        }
        color = colors.get(obj.transaction_type, '#6c757d')
        icon = '↑' if obj.transaction_type == 'credit' else '↓'

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: 600;">{} {}</span>',
            color, icon, obj.get_transaction_type_display()
        )
    colored_type.short_description = 'Type'
    colored_type.admin_order_field = 'transaction_type'

    def colored_purpose(self, obj):
        colors = {
            'deposit': '#28a745',       # Green
            'investment': '#007bff',    # Blue
            'payout': '#17a2b8',        # Cyan
            'commission': '#ffc107',    # Yellow
            'redemption': '#6f42c1',    # Purple
            'refund': '#fd7e14',        # Orange
            'withdrawal': '#dc3545',    # Red
            'fee': '#6c757d',           # Gray
        }
        color = colors.get(obj.purpose, '#6c757d')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px; font-size: 10px;">{}</span>',
            color, obj.get_purpose_display()
        )
    colored_purpose.short_description = 'Purpose'
    colored_purpose.admin_order_field = 'purpose'

    def amount_display(self, obj):
        color = '#28a745' if obj.transaction_type == 'credit' else '#dc3545'
        sign = '+' if obj.transaction_type == 'credit' else '-'
        return format_html(
            '<span style="font-weight: 700; color: {}; font-size: 13px;">{} ₹{:,.2f}</span>',
            color, sign, obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def colored_status(self, obj):
        colors = {
            'pending': '#6c757d',     # Gray
            'processing': '#ffc107',  # Yellow
            'completed': '#28a745',   # Green
            'failed': '#dc3545',      # Red
            'cancelled': '#6c757d',   # Gray
        }
        color = colors.get(obj.status, '#6c757d')

        icons = {
            'pending': '⏳',
            'processing': '⚙️',
            'completed': '✓',
            'failed': '✗',
            'cancelled': '∅'
        }
        icon = icons.get(obj.status, '')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    # Admin Actions
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['pending', 'processing']).update(
            status='completed',
            processed_at=timezone.now(),
            processed_by=request.user
        )
        self.message_user(
            request, f'{updated} transaction(s) marked as completed.')
    mark_completed.short_description = "✓ Mark as completed"

    def mark_failed(self, request, queryset):
        updated = queryset.filter(status__in=['pending', 'processing']).update(
            status='failed'
        )
        self.message_user(
            request, f'{updated} transaction(s) marked as failed.', level='error')
    mark_failed.short_description = "✗ Mark as failed"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('wallet', 'user', 'organization', 'processed_by')


# ============================================
# INVESTMENT ADMIN
# ============================================
@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = (
        'investment_id', 'customer', 'property', 'amount_display',
        'units_purchased', 'colored_status', 'referred_by_cp',
        'payment_completed', 'created_at'
    )
    list_filter = (
        'status', 'payment_completed', 'organization',
        'referred_by_cp', 'created_at', 'approved_at'
    )
    search_fields = (
        'investment_id', 'customer__username', 'customer__email',
        'property__name', 'referred_by_cp__user__username'
    )
    autocomplete_fields = [
        'customer', 'property', 'organization',
        'referred_by_cp', 'approved_by', 'transaction'
    ]
    ordering = ('-created_at',)
    date_hierarchy = 'investment_date'

    fieldsets = (
        ('Investment Info', {
            'fields': ('investment_id', 'customer', 'property', 'organization')
        }),
        ('Investment Details', {
            'fields': ('amount', 'units_purchased', 'price_per_unit_at_investment')
        }),
        ('Referral', {
            'fields': ('referred_by_cp',),
            'classes': ('collapse',)
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Payment', {
            'fields': ('payment_completed', 'payment_completed_at', 'transaction')
        }),
        ('Returns', {
            'fields': ('expected_return_amount', 'actual_return_amount'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('investment_date', 'maturity_date', 'lock_in_end_date'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('investment_date', 'created_at',
                       'updated_at', 'approved_at', 'payment_completed_at')

    inlines = [InvestmentUnitInline]

    list_per_page = 50

    actions = ['approve_investments', 'reject_investments', 'mark_active']

    def amount_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #007bff; font-size: 14px;">₹{:,.2f}</span>',
            obj.amount
        )
    amount_display.short_description = 'Investment Amount'
    amount_display.admin_order_field = 'amount'

    def colored_status(self, obj):
        colors = {
            'draft': '#6c757d',       # Gray
            'pending': '#ffc107',     # Yellow
            'approved': '#17a2b8',    # Cyan
            'active': '#28a745',      # Green
            'completed': '#007bff',   # Blue
            'redeemed': '#6f42c1',    # Purple
            'cancelled': '#dc3545',   # Red
            'rejected': '#dc3545',    # Red
        }
        color = colors.get(obj.status, '#6c757d')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 12px; border-radius: 3px; font-size: 11px; font-weight: 600;">{}</span>',
            color, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    # Admin Actions
    def approve_investments(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} investment(s) approved.')
    approve_investments.short_description = "✓ Approve investments"

    def reject_investments(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='rejected',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(
            request, f'{updated} investment(s) rejected.', level='warning')
    reject_investments.short_description = "✗ Reject investments"

    def mark_active(self, request, queryset):
        updated = queryset.filter(status='approved', payment_completed=True).update(
            status='active'
        )
        self.message_user(
            request, f'{updated} investment(s) marked as active.')
    mark_active.short_description = "▶ Mark as active"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'customer', 'property', 'organization',
            'referred_by_cp', 'approved_by'
        )


# ============================================
# PAYOUT ADMIN
# ============================================
@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        'payout_id', 'customer', 'property', 'colored_type',
        'amount_display', 'colored_status', 'period_display', 'created_at'
    )
    list_filter = (
        'payout_type', 'status', 'organization',
        'created_at', 'paid_at'
    )
    search_fields = (
        'payout_id', 'customer__username', 'customer__email',
        'property__name', 'description'
    )
    autocomplete_fields = [
        'investment', 'customer', 'property', 'organization',
        'approved_by', 'transaction'
    ]
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Payout Info', {
            'fields': ('payout_id', 'investment', 'customer', 'property', 'organization')
        }),
        ('Payout Details', {
            'fields': ('payout_type', 'amount', 'period_start', 'period_end')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Payment', {
            'fields': ('transaction', 'paid_at')
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'paid_at')

    list_per_page = 50

    actions = ['approve_payouts', 'mark_completed']

    def colored_type(self, obj):
        colors = {
            'rental': '#28a745',              # Green
            'profit': '#007bff',              # Blue
            'capital_appreciation': '#17a2b8',  # Cyan
            'dividend': '#ffc107',            # Yellow
            'interest': '#6f42c1',            # Purple
        }
        color = colors.get(obj.payout_type, '#6c757d')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_payout_type_display()
        )
    colored_type.short_description = 'Type'
    colored_type.admin_order_field = 'payout_type'

    def amount_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #28a745; font-size: 14px;">₹{:,.2f}</span>',
            obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def colored_status(self, obj):
        colors = {
            'pending': '#6c757d',     # Gray
            'approved': '#17a2b8',    # Cyan
            'processing': '#ffc107',  # Yellow
            'completed': '#28a745',   # Green
            'failed': '#dc3545',      # Red
        }
        color = colors.get(obj.status, '#6c757d')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def period_display(self, obj):
        if obj.period_start and obj.period_end:
            return format_html(
                '<span style="font-size: 11px; color: #6c757d;">{} to {}</span>',
                obj.period_start.strftime('%d %b %Y'),
                obj.period_end.strftime('%d %b %Y')
            )
        return '-'
    period_display.short_description = 'Period'

    # Admin Actions
    def approve_payouts(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} payout(s) approved.')
    approve_payouts.short_description = "✓ Approve payouts"

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['approved', 'processing']).update(
            status='completed',
            paid_at=timezone.now()
        )
        self.message_user(request, f'{updated} payout(s) marked as completed.')
    mark_completed.short_description = "✓ Mark as completed"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'investment', 'customer', 'property', 'organization', 'approved_by'
        )


# ============================================
# REDEMPTION REQUEST ADMIN
# ============================================
@admin.register(RedemptionRequest)
class RedemptionRequestAdmin(admin.ModelAdmin):
    list_display = (
        'request_id', 'customer', 'investment', 'units_to_redeem',
        'requested_amount_display', 'colored_status', 'lockin_badge',
        'created_at'
    )
    list_filter = (
        'status', 'is_within_lockin', 'organization',
        'created_at', 'reviewed_at'
    )
    search_fields = (
        'request_id', 'customer__username', 'customer__email',
        'investment__investment_id'
    )
    autocomplete_fields = [
        'investment', 'customer', 'organization',
        'reviewed_by', 'transaction'
    ]
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Request Info', {
            'fields': ('request_id', 'investment', 'customer', 'organization')
        }),
        ('Redemption Details', {
            'fields': ('units_to_redeem', 'requested_amount', 'approved_amount')
        }),
        ('Lock-in & Penalty', {
            'fields': ('is_within_lockin', 'penalty_amount')
        }),
        ('Status & Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'rejection_reason')
        }),
        ('Payment', {
            'fields': ('transaction', 'completed_at')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at',
                       'reviewed_at', 'completed_at')

    list_per_page = 50

    actions = ['approve_redemptions', 'reject_redemptions']

    def requested_amount_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #6f42c1; font-size: 13px;">₹{:,.2f}</span>',
            obj.requested_amount
        )
    requested_amount_display.short_description = 'Requested Amount'
    requested_amount_display.admin_order_field = 'requested_amount'

    def colored_status(self, obj):
        colors = {
            'pending': '#6c757d',       # Gray
            'under_review': '#ffc107',  # Yellow
            'approved': '#28a745',      # Green
            'rejected': '#dc3545',      # Red
            'completed': '#007bff',     # Blue
            'cancelled': '#6c757d',     # Gray
        }
        color = colors.get(obj.status, '#6c757d')

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def lockin_badge(self, obj):
        if obj.is_within_lockin:
            return format_html(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 10px;">🔒 Lock-in</span><br>'
                '<span style="color: #dc3545; font-size: 10px;">Penalty: ₹{:,.2f}</span>',
                obj.penalty_amount
            )
        return format_html(
            '<span style="color: #28a745; font-size: 11px;">✓ No lock-in</span>'
        )
    lockin_badge.short_description = 'Lock-in Status'

    # Admin Actions
    def approve_redemptions(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['pending', 'under_review']).update(
            status='approved',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} redemption(s) approved.')
    approve_redemptions.short_description = "✓ Approve redemptions"

    def reject_redemptions(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['pending', 'under_review']).update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(
            request, f'{updated} redemption(s) rejected.', level='warning')
    reject_redemptions.short_description = "✗ Reject redemptions"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'investment', 'customer', 'organization', 'reviewed_by'
        )


# ============================================
# INVESTMENT UNIT ADMIN (Optional)
# ============================================
@admin.register(InvestmentUnit)
class InvestmentUnitAdmin(admin.ModelAdmin):
    list_display = ('investment', 'unit', 'allocated_at')
    list_filter = ('allocated_at',)
    search_fields = ('investment__investment_id', 'unit__unit_number')
    autocomplete_fields = ['investment', 'unit']
    ordering = ('-allocated_at',)

    readonly_fields = ('allocated_at',)
