# partners/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    ChannelPartner,
    CPCustomerRelation,
    CPPropertyAuthorization,
    CPLead,
    CPInvite,
    CPDocument,
    CommissionRule,
    CPCommissionRule
)


# ============================================
# INLINE ADMINS
# ============================================

class CPDocumentInline(admin.TabularInline):
    """Show documents inline in CP admin"""
    model = CPDocument
    extra = 0
    fields = ('document_type', 'file', 'status', 'verified_by', 'verified_at')
    readonly_fields = ('verified_by', 'verified_at')
    can_delete = False


class CPPropertyAuthorizationInline(admin.TabularInline):
    """Show authorized properties inline in CP admin"""
    model = CPPropertyAuthorization
    extra = 0
    fields = ('property', 'is_authorized', 'approval_status', 'referral_link', 'authorized_by')
    readonly_fields = ('referral_link', 'authorized_by', 'authorized_at')
    can_delete = False


class CPCommissionRuleInline(admin.TabularInline):
    """Show commission rules inline in CP admin"""
    model = CPCommissionRule
    extra = 0
    fields = ('commission_rule', 'property', 'assigned_by', 'assigned_at')
    readonly_fields = ('assigned_by', 'assigned_at')
    can_delete = False


class CPCustomerRelationInline(admin.TabularInline):
    """Show customers inline in CP admin"""
    model = CPCustomerRelation
    extra = 0
    fields = ('customer', 'referral_code', 'referral_date', 'expiry_date', 'is_expired', 'is_active')
    readonly_fields = ('referral_date', 'is_expired')
    can_delete = False


# ============================================
# CHANNEL PARTNER ADMIN
# ============================================

@admin.register(ChannelPartner)
class ChannelPartnerAdmin(admin.ModelAdmin):
    list_display = (
        'cp_code',
        'user_name',
        'agent_type',
        'partner_tier',
        'onboarding_status_badge',
        'is_verified',
        'is_active',
        'total_customers',
        'created_at'
    )
    
    list_filter = (
        'agent_type',
        'partner_tier',
        'onboarding_status',
        'is_verified',
        'is_active',
        'source',
        'regulatory_compliance_approved',
        'created_at'
    )
    
    search_fields = (
        'cp_code',
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'user__phone',
        'company_name',
        'pan_number',
        'gst_number',
        'rera_number'
    )
    
    readonly_fields = (
        'cp_code',
        'created_at',
        'updated_at',
        'created_by',
        'last_modified_by',
        'last_modified_date',
        'verified_at',
        'verified_by',
        'onboarded_by',
        'hierarchy_level',
        'program_active_status'
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user',
                'cp_code',
                'parent_cp',
                'agent_type',
                'source',
                'company_name'
            )
        }),
        ('Legal Documents', {
            'fields': (
                'pan_number',
                'gst_number',
                'rera_number',
                'business_address'
            )
        }),
        ('Bank Details', {
            'fields': (
                'bank_name',
                'account_number',
                'ifsc_code',
                'account_holder_name'
            )
        }),
        ('Program Enrollment', {
            'fields': (
                'partner_tier',
                'program_start_date',
                'program_end_date',
                'program_active_status'
            )
        }),
        ('Compliance', {
            'fields': (
                'regulatory_compliance_approved',
                'onboarding_status',
                'dedicated_support_contact',
                'technical_setup_notes'
            )
        }),
        ('Targets & Performance', {
            'fields': (
                'monthly_target',
                'quarterly_target',
                'yearly_target',
                'annual_revenue_target',
                'q1_performance',
                'q2_performance',
                'q3_performance',
                'q4_performance'
            )
        }),
        ('Commission', {
            'fields': ('commission_notes',)
        }),
        ('Status & Verification', {
            'fields': (
                'is_active',
                'is_verified',
                'verified_at',
                'verified_by',
                'onboarded_by'
            )
        }),
        ('Hierarchy', {
            'fields': ('hierarchy_level',),
            'classes': ('collapse',)
        }),
        ('System Audit', {
            'fields': (
                'created_at',
                'updated_at',
                'created_by',
                'last_modified_by',
                'last_modified_date'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [
        CPDocumentInline,
        CPPropertyAuthorizationInline,
        CPCommissionRuleInline,
        CPCustomerRelationInline
    ]
    
    actions = [
        'approve_cps',
        'activate_cps',
        'deactivate_cps',
        'upgrade_to_silver',
        'upgrade_to_gold',
        'upgrade_to_platinum'
    ]
    
    def user_name(self, obj):
        """Display user's full name"""
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = 'Name'
    
    def onboarding_status_badge(self, obj):
        """Display onboarding status with color badge"""
        colors = {
            'pending': 'orange',
            'in_progress': 'blue',
            'completed': 'green',
            'rejected': 'red'
        }
        color = colors.get(obj.onboarding_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_onboarding_status_display()
        )
    onboarding_status_badge.short_description = 'Onboarding Status'
    
    def total_customers(self, obj):
        """Display total customers count"""
        count = obj.customers.filter(is_active=True).count()
        return format_html('<strong>{}</strong>', count)
    total_customers.short_description = 'Customers'
    
    def hierarchy_level(self, obj):
        """Display CP hierarchy level"""
        return f"Level {obj.get_hierarchy_level()}"
    hierarchy_level.short_description = 'Hierarchy Level'
    
    def program_active_status(self, obj):
        """Display if program is currently active"""
        is_active = obj.is_program_active()
        color = 'green' if is_active else 'red'
        status = 'Active' if is_active else 'Inactive'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    program_active_status.short_description = 'Program Status'
    
    # Admin Actions
    def approve_cps(self, request, queryset):
        """Approve selected CPs"""
        from django.utils import timezone
        from accounts.models import Role
        
        approved_count = 0
        for cp in queryset:
            if not cp.is_verified:
                cp.is_verified = True
                cp.is_active = True
                cp.onboarding_status = 'completed'
                cp.verified_at = timezone.now()
                cp.verified_by = request.user
                cp.save()
                
                # Change user role to channel_partner
                cp_role = Role.objects.get(slug='channel_partner')
                cp.user.role = cp_role
                cp.user.save()
                
                approved_count += 1
        
        self.message_user(request, f"{approved_count} CP(s) approved successfully.")
    approve_cps.short_description = "Approve selected CPs"
    
    def activate_cps(self, request, queryset):
        """Activate selected CPs"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} CP(s) activated.")
    activate_cps.short_description = "Activate selected CPs"
    
    def deactivate_cps(self, request, queryset):
        """Deactivate selected CPs"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} CP(s) deactivated.")
    deactivate_cps.short_description = "Deactivate selected CPs"
    
    def upgrade_to_silver(self, request, queryset):
        """Upgrade to Silver tier"""
        updated = queryset.update(partner_tier='silver')
        self.message_user(request, f"{updated} CP(s) upgraded to Silver.")
    upgrade_to_silver.short_description = "Upgrade to Silver"
    
    def upgrade_to_gold(self, request, queryset):
        """Upgrade to Gold tier"""
        updated = queryset.update(partner_tier='gold')
        self.message_user(request, f"{updated} CP(s) upgraded to Gold.")
    upgrade_to_gold.short_description = "Upgrade to Gold"
    
    def upgrade_to_platinum(self, request, queryset):
        """Upgrade to Platinum tier"""
        updated = queryset.update(partner_tier='platinum')
        self.message_user(request, f"{updated} CP(s) upgraded to Platinum.")
    upgrade_to_platinum.short_description = "Upgrade to Platinum"


# ============================================
# CP CUSTOMER RELATION ADMIN
# ============================================

@admin.register(CPCustomerRelation)
class CPCustomerRelationAdmin(admin.ModelAdmin):
    list_display = (
        'customer_name',
        'cp_code',
        'referral_code',
        'referral_date',
        'expiry_date',
        'days_remaining',
        'is_expired',
        'is_active'
    )
    
    list_filter = (
        'is_active',
        'is_expired',
        'referral_date',
        'expiry_date'
    )
    
    search_fields = (
        'customer__username',
        'customer__email',
        'customer__phone',
        'cp__cp_code',
        'referral_code'
    )
    
    readonly_fields = (
        'referral_date',
        'days_remaining',
        'created_at',
        'updated_at'
    )
    
    actions = ['extend_validity_30_days', 'extend_validity_90_days', 'mark_expired']
    
    def customer_name(self, obj):
        """Display customer name"""
        return obj.customer.get_full_name() or obj.customer.username
    customer_name.short_description = 'Customer'
    
    def cp_code(self, obj):
        """Display CP code"""
        return obj.cp.cp_code
    cp_code.short_description = 'CP Code'
    
    def days_remaining(self, obj):
        """Calculate days remaining until expiry"""
        from django.utils import timezone
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        
        days = (obj.expiry_date - timezone.now()).days
        if days <= 7:
            color = 'red'
        elif days <= 30:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} days</span>',
            color,
            days
        )
    days_remaining.short_description = 'Days Remaining'
    
    # Admin Actions
    def extend_validity_30_days(self, request, queryset):
        """Extend validity by 30 days"""
        for relation in queryset:
            relation.extend_validity(30)
        self.message_user(request, f"{queryset.count()} relation(s) extended by 30 days.")
    extend_validity_30_days.short_description = "Extend validity by 30 days"
    
    def extend_validity_90_days(self, request, queryset):
        """Extend validity by 90 days"""
        for relation in queryset:
            relation.extend_validity(90)
        self.message_user(request, f"{queryset.count()} relation(s) extended by 90 days.")
    extend_validity_90_days.short_description = "Extend validity by 90 days"
    
    def mark_expired(self, request, queryset):
        """Manually mark as expired"""
        updated = queryset.update(is_expired=True, is_active=False)
        self.message_user(request, f"{updated} relation(s) marked as expired.")
    mark_expired.short_description = "Mark as expired"


# ============================================
# CP PROPERTY AUTHORIZATION ADMIN
# ============================================

@admin.register(CPPropertyAuthorization)
class CPPropertyAuthorizationAdmin(admin.ModelAdmin):
    list_display = (
        'cp_code',
        'property_name',
        'is_authorized',
        'approval_status_badge',
        'referral_link_display',
        'authorized_at'
    )
    
    list_filter = (
        'is_authorized',
        'approval_status',
        'authorized_at'
    )
    
    search_fields = (
        'cp__cp_code',
        'property__name',
        'property__property_code'
    )
    
    readonly_fields = (
        'referral_link',
        'authorized_by',
        'authorized_at',
        'created_at',
        'updated_at'
    )
    
    actions = ['approve_authorizations', 'revoke_authorizations', 'generate_links']
    
    def cp_code(self, obj):
        """Display CP code"""
        return obj.cp.cp_code
    cp_code.short_description = 'CP Code'
    
    def property_name(self, obj):
        """Display property name"""
        return obj.property.name
    property_name.short_description = 'Property'
    
    def approval_status_badge(self, obj):
        """Display approval status with badge"""
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'revoked': 'gray'
        }
        color = colors.get(obj.approval_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_approval_status_display()
        )
    approval_status_badge.short_description = 'Status'
    
    def referral_link_display(self, obj):
        """Display referral link as clickable"""
        if obj.referral_link:
            return format_html(
                '<a href="{}" target="_blank">View Link</a>',
                obj.referral_link
            )
        return "—"
    referral_link_display.short_description = 'Referral Link'
    
    # Admin Actions
    def approve_authorizations(self, request, queryset):
        """Approve authorizations"""
        from django.utils import timezone
        updated = queryset.update(
            approval_status='approved',
            is_authorized=True,
            authorized_by=request.user,
            authorized_at=timezone.now()
        )
        self.message_user(request, f"{updated} authorization(s) approved.")
    approve_authorizations.short_description = "Approve authorizations"
    
    def revoke_authorizations(self, request, queryset):
        """Revoke authorizations"""
        updated = queryset.update(
            approval_status='revoked',
            is_authorized=False
        )
        self.message_user(request, f"{updated} authorization(s) revoked.")
    revoke_authorizations.short_description = "Revoke authorizations"
    
    def generate_links(self, request, queryset):
        """Generate referral links"""
        for auth in queryset:
            auth.generate_referral_link()
        self.message_user(request, f"{queryset.count()} referral link(s) generated.")
    generate_links.short_description = "Generate referral links"


# ============================================
# CP LEAD ADMIN
# ============================================

@admin.register(CPLead)
class CPLeadAdmin(admin.ModelAdmin):
    list_display = (
        'customer_name',
        'phone',
        'cp_code',
        'interested_property',
        'lead_status_badge',
        'next_follow_up_date',
        'created_at'
    )
    
    list_filter = (
        'lead_status',
        'lead_source',
        'next_follow_up_date',
        'converted_at',
        'created_at'
    )
    
    search_fields = (
        'customer_name',
        'phone',
        'email',
        'cp__cp_code'
    )
    
    readonly_fields = (
        'converted_customer',
        'converted_at',
        'created_at',
        'updated_at'
    )
    
    actions = ['mark_as_contacted', 'mark_as_interested', 'mark_as_lost']
    
    def cp_code(self, obj):
        """Display CP code"""
        return obj.cp.cp_code
    cp_code.short_description = 'CP Code'
    
    def lead_status_badge(self, obj):
        """Display lead status with badge"""
        colors = {
            'new': 'blue',
            'contacted': 'cyan',
            'interested': 'green',
            'site_visit_scheduled': 'purple',
            'site_visit_done': 'purple',
            'negotiation': 'orange',
            'converted': 'green',
            'lost': 'red',
            'not_interested': 'gray'
        }
        color = colors.get(obj.lead_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_lead_status_display()
        )
    lead_status_badge.short_description = 'Status'
    
    # Admin Actions
    def mark_as_contacted(self, request, queryset):
        """Mark leads as contacted"""
        updated = queryset.update(lead_status='contacted')
        self.message_user(request, f"{updated} lead(s) marked as contacted.")
    mark_as_contacted.short_description = "Mark as contacted"
    
    def mark_as_interested(self, request, queryset):
        """Mark leads as interested"""
        updated = queryset.update(lead_status='interested')
        self.message_user(request, f"{updated} lead(s) marked as interested.")
    mark_as_interested.short_description = "Mark as interested"
    
    def mark_as_lost(self, request, queryset):
        """Mark leads as lost"""
        updated = queryset.update(lead_status='lost')
        self.message_user(request, f"{updated} lead(s) marked as lost.")
    mark_as_lost.short_description = "Mark as lost"


# ============================================
# CP INVITE ADMIN
# ============================================

@admin.register(CPInvite)
class CPInviteAdmin(admin.ModelAdmin):
    list_display = (
        'invite_code',
        'cp_code',
        'phone',
        'name',
        'is_used',
        'is_expired',
        'expiry_date',
        'created_at'
    )
    
    list_filter = (
        'is_used',
        'is_expired',
        'expiry_date',
        'created_at'
    )
    
    search_fields = (
        'invite_code',
        'cp__cp_code',
        'phone',
        'email',
        'name'
    )
    
    readonly_fields = (
        'invite_code',
        'is_used',
        'used_by',
        'used_at',
        'created_at',
        'updated_at'
    )
    
    def cp_code(self, obj):
        """Display CP code"""
        return obj.cp.cp_code
    cp_code.short_description = 'CP Code'


# ============================================
# CP DOCUMENT ADMIN
# ============================================

@admin.register(CPDocument)
class CPDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'cp_code',
        'document_type',
        'status_badge',
        'file_link',
        'verified_by',
        'verified_at',
        'created_at'
    )
    
    list_filter = (
        'document_type',
        'status',
        'verified_at',
        'created_at'
    )
    
    search_fields = (
        'cp__cp_code',
        'description'
    )
    
    readonly_fields = (
        'verified_by',
        'verified_at',
        'created_at',
        'updated_at'
    )
    
    actions = ['approve_documents', 'reject_documents']
    
    def cp_code(self, obj):
        """Display CP code"""
        return obj.cp.cp_code
    cp_code.short_description = 'CP Code'
    
    def status_badge(self, obj):
        """Display status with badge"""
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def file_link(self, obj):
        """Display file as link"""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">View File</a>',
                obj.file.url
            )
        return "—"
    file_link.short_description = 'File'
    
    # Admin Actions
    def approve_documents(self, request, queryset):
        """Approve documents"""
        for doc in queryset:
            doc.approve_document(request.user)
        self.message_user(request, f"{queryset.count()} document(s) approved.")
    approve_documents.short_description = "Approve documents"
    
    def reject_documents(self, request, queryset):
        """Reject documents"""
        for doc in queryset:
            doc.reject_document(request.user, "Rejected by admin")
        self.message_user(request, f"{queryset.count()} document(s) rejected.")
    reject_documents.short_description = "Reject documents"


# ============================================
# COMMISSION RULE ADMIN
# ============================================

@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'commission_type',
        'percentage',
        'override_percentage',
        'is_default',
        'is_active',
        'effective_from',
        'effective_to'
    )
    
    list_filter = (
        'commission_type',
        'is_default',
        'is_active',
        'effective_from'
    )
    
    search_fields = ('name', 'description')
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CPCommissionRule)
class CPCommissionRuleAdmin(admin.ModelAdmin):
    list_display = (
        'cp_code',
        'commission_rule_name',
        'property_name',
        'assigned_by',
        'assigned_at'
    )
    
    list_filter = (
        'assigned_at',
    )
    
    search_fields = (
        'cp__cp_code',
        'commission_rule__name',
        'property__name'
    )
    
    readonly_fields = ('assigned_by', 'assigned_at', 'created_at', 'updated_at')
    
    def cp_code(self, obj):
        """Display CP code"""
        return obj.cp.cp_code
    cp_code.short_description = 'CP Code'
    
    def commission_rule_name(self, obj):
        """Display commission rule name"""
        return obj.commission_rule.name
    commission_rule_name.short_description = 'Commission Rule'
    
    def property_name(self, obj):
        """Display property name"""
        return obj.property.name if obj.property else "All Properties"
    property_name.short_description = 'Property'