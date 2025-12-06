# commissions/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Commission, CommissionPayout


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = [
        'commission_id',
        'cp_name',
        'investment_id',
        'commission_type',
        'commission_amount_display',
        'net_amount_display',
        'status_badge',
        'is_override',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'commission_type',
        'is_override',
        'created_at'
    ]
    
    search_fields = [
        'commission_id',
        'cp__cp_code',
        'cp__user__username',
        'investment__investment_id',
        'investment__customer__username'
    ]
    
    readonly_fields = [
        'commission_id',
        'created_at',
        'updated_at',
        'approved_at',
        'paid_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'commission_id',
                'cp',
                'investment',
                'commission_type',
                'is_override',
                'parent_commission'
            )
        }),
        ('Calculation', {
            'fields': (
                'base_amount',
                'commission_rate',
                'commission_amount',
                'tds_percentage',
                'tds_amount',
                'net_amount'
            )
        }),
        ('Rule', {
            'fields': ('commission_rule',)
        }),
        ('Status', {
            'fields': (
                'status',
                'approved_by',
                'approved_at',
                'paid_at',
                'paid_by',
                'payment_reference'
            )
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def cp_name(self, obj):
        return obj.cp.user.get_full_name() or obj.cp.user.username
    cp_name.short_description = 'Channel Partner'
    
    def investment_id(self, obj):
        return obj.investment.investment_id
    investment_id.short_description = 'Investment'
    
    def commission_amount_display(self, obj):
        return f"₹{obj.commission_amount:,.2f}"
    commission_amount_display.short_description = 'Commission'
    
    def net_amount_display(self, obj):
        return f"₹{obj.net_amount:,.2f}"
    net_amount_display.short_description = 'Net Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'approved': '#007BFF',
            'processing': '#17A2B8',
            'paid': '#28A745',
            'cancelled': '#DC3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6C757D'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    actions = ['approve_commissions', 'mark_as_paid']
    
    def approve_commissions(self, request, queryset):
        from commissions.services.commission_service import CommissionService
        count = 0
        for commission in queryset.filter(status='pending'):
            CommissionService.approve_commission(commission, request.user)
            count += 1
        self.message_user(request, f'{count} commission(s) approved successfully.')
    approve_commissions.short_description = 'Approve selected commissions'
    
    def mark_as_paid(self, request, queryset):
        from commissions.services.commission_service import CommissionService
        count = 0
        for commission in queryset.filter(status='approved'):
            CommissionService.process_payout(commission, request.user)
            count += 1
        self.message_user(request, f'{count} commission(s) marked as paid.')
    mark_as_paid.short_description = 'Mark as paid'


@admin.register(CommissionPayout)
class CommissionPayoutAdmin(admin.ModelAdmin):
    list_display = [
        'payout_id',
        'cp_name',
        'total_amount_display',
        'net_amount_display',
        'status_badge',
        'created_at'
    ]
    
    list_filter = ['status', 'created_at']
    
    search_fields = [
        'payout_id',
        'cp__cp_code',
        'cp__user__username'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'paid_at']
    
    def cp_name(self, obj):
        return obj.cp.user.get_full_name() or obj.cp.user.username
    cp_name.short_description = 'Channel Partner'
    
    def total_amount_display(self, obj):
        return f"₹{obj.total_amount:,.2f}"
    total_amount_display.short_description = 'Total'
    
    def net_amount_display(self, obj):
        return f"₹{obj.net_amount:,.2f}"
    net_amount_display.short_description = 'Net Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'processing': '#17A2B8',
            'completed': '#28A745',
            'failed': '#DC3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6C757D'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'