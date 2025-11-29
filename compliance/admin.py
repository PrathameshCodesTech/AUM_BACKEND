# compliance/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count, Q
from django.forms import widgets
import json
from .models import KYC, Document, AuditLog
from django.db import models 


# ============================================
# CUSTOM WIDGETS
# ============================================

class PrettyJSONWidget(widgets.Textarea):
    """Widget for displaying formatted JSON"""
    
    def format_value(self, value):
        try:
            if isinstance(value, str):
                value = json.loads(value)
            value = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
            self.attrs['rows'] = min(value.count('\n') + 2, 20)
            return value
        except (ValueError, TypeError):
            return super().format_value(value)


# ============================================
# CUSTOM FILTERS
# ============================================

class KYCStatusFilter(admin.SimpleListFilter):
    """Filter KYC by status"""
    title = 'KYC status'
    parameter_name = 'kyc_status'

    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending'),
            ('under_review', 'Under Review'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())


class AadhaarVerificationFilter(admin.SimpleListFilter):
    """Filter by Aadhaar verification status"""
    title = 'Aadhaar verification'
    parameter_name = 'aadhaar_verified'

    def lookups(self, request, model_admin):
        return (
            ('verified', 'Verified'),
            ('unverified', 'Not Verified'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(aadhaar_verified=True)
        elif self.value() == 'unverified':
            return queryset.filter(aadhaar_verified=False)


class PANVerificationFilter(admin.SimpleListFilter):
    """Filter by PAN verification status"""
    title = 'PAN verification'
    parameter_name = 'pan_verified'

    def lookups(self, request, model_admin):
        return (
            ('verified', 'Verified'),
            ('unverified', 'Not Verified'),
            ('linked', 'PAN-Aadhaar Linked'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(pan_verified=True)
        elif self.value() == 'unverified':
            return queryset.filter(pan_verified=False)
        elif self.value() == 'linked':
            return queryset.filter(pan_aadhaar_linked=True)


class BankVerificationFilter(admin.SimpleListFilter):
    """Filter by bank verification status"""
    title = 'Bank verification'
    parameter_name = 'bank_verified'

    def lookups(self, request, model_admin):
        return (
            ('verified', 'Verified'),
            ('unverified', 'Not Verified'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'verified':
            return queryset.filter(bank_verified=True)
        elif self.value() == 'unverified':
            return queryset.filter(bank_verified=False)


class CompletionFilter(admin.SimpleListFilter):
    """Filter by KYC completion"""
    title = 'KYC completion'
    parameter_name = 'completion'

    def lookups(self, request, model_admin):
        return (
            ('complete', 'Complete'),
            ('incomplete', 'Incomplete'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'complete':
            return queryset.filter(
                aadhaar_verified=True,
                pan_verified=True,
                bank_verified=True
            )
        elif self.value() == 'incomplete':
            return queryset.filter(
                Q(aadhaar_verified=False) |
                Q(pan_verified=False) |
                Q(bank_verified=False)
            )


class SoftDeleteKYCFilter(admin.SimpleListFilter):
    """Filter for soft deleted KYC records"""
    title = 'deletion status'
    parameter_name = 'deleted_kyc'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active Only'),
            ('deleted', 'Deleted Only'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(is_deleted=False)
        elif self.value() == 'deleted':
            return queryset.filter(is_deleted=True)


class DocumentTypeFilter(admin.SimpleListFilter):
    """Filter documents by type"""
    title = 'document type'
    parameter_name = 'doc_type'

    def lookups(self, request, model_admin):
        return (
            ('aadhaar', 'Aadhaar Card'),
            ('pan', 'PAN Card'),
            ('bank', 'Bank Proof'),
            ('address', 'Address Proof'),
            ('photo', 'Photograph'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(document_type=self.value())


class AuditActionFilter(admin.SimpleListFilter):
    """Filter audit logs by action"""
    title = 'action type'
    parameter_name = 'action'

    def lookups(self, request, model_admin):
        return (
            ('kyc_submit', 'KYC Submitted'),
            ('kyc_approve', 'KYC Approved'),
            ('kyc_reject', 'KYC Rejected'),
            ('document_upload', 'Document Uploaded'),
            ('login', 'User Login'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action=self.value())


# ============================================
# KYC ADMIN
# ============================================

@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    """Admin for KYC management"""
    
    list_display = [
        'user_link',
        'verification_summary',
        'aadhaar_status',
        'pan_status',
        'bank_status',
        'completion_progress',
        'status_badge',
        'created_at',
    ]
    
    list_filter = [
        KYCStatusFilter,
        AadhaarVerificationFilter,
        PANVerificationFilter,
        BankVerificationFilter,
        CompletionFilter,
        SoftDeleteKYCFilter,
        'created_at',
        'verified_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'user__phone',
        'aadhaar_number',
        'pan_number',
        'account_number',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'verified_at',
        'verified_by',
        'aadhaar_verified_at',
        'pan_verified_at',
        'bank_verified_at',
        'deleted_at',
        'deleted_by',
        'aadhaar_front_preview',
        'aadhaar_back_preview',
        'pan_document_preview',
        'bank_proof_preview',
        'address_proof_preview',
        'aadhaar_api_response_display',
        'pan_api_response_display',
        'bank_api_response_display',
        'completion_percentage',
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'status')
        }),
        ('Aadhaar Details', {
            'fields': (
                'aadhaar_number',
                'aadhaar_name',
                'aadhaar_dob',
                'aadhaar_gender',
                'aadhaar_address',
                'aadhaar_verified',
                'aadhaar_verified_at',
                'aadhaar_front',
                'aadhaar_front_preview',
                'aadhaar_back',
                'aadhaar_back_preview',
            ),
            'classes': ('collapse',),
        }),
        ('Aadhaar API Response', {
            'fields': (
                'aadhaar_api_response',
                'aadhaar_api_response_display',
            ),
            'classes': ('collapse',),
        }),
        ('PAN Details', {
            'fields': (
                'pan_number',
                'pan_name',
                'pan_father_name',
                'pan_dob',
                'pan_verified',
                'pan_verified_at',
                'pan_aadhaar_linked',
                'pan_document',
                'pan_document_preview',
            ),
            'classes': ('collapse',),
        }),
        ('PAN API Response', {
            'fields': (
                'pan_api_response',
                'pan_api_response_display',
            ),
            'classes': ('collapse',),
        }),
        ('Bank Details', {
            'fields': (
                'bank_name',
                'account_number',
                'ifsc_code',
                'account_holder_name',
                'account_type',
                'bank_verified',
                'bank_verified_at',
                'bank_proof',
                'bank_proof_preview',
            ),
            'classes': ('collapse',),
        }),
        ('Bank API Response', {
            'fields': (
                'bank_api_response',
                'bank_api_response_display',
            ),
            'classes': ('collapse',),
        }),
        ('Address Details', {
            'fields': (
                'address_line1',
                'address_line2',
                'city',
                'state',
                'pincode',
                'address_proof',
                'address_proof_preview',
            ),
            'classes': ('collapse',),
        }),
        ('Verification', {
            'fields': (
                'verified_at',
                'verified_by',
                'rejection_reason',
            )
        }),
        ('Completion Status', {
            'fields': (
                'completion_percentage',
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
    
    autocomplete_fields = ['user', 'verified_by', 'deleted_by']
    
    # Override JSONField widget
    formfield_overrides = {
        models.JSONField: {'widget': PrettyJSONWidget}
    }
    
    # Custom display methods
    def user_link(self, obj):
        """Display user as clickable link"""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url,
            obj.user.get_full_name() or obj.user.username,
            obj.user.phone or obj.user.email
        )
    user_link.short_description = 'User'
    
    def verification_summary(self, obj):
        """Display verification summary with icons"""
        aadhaar_icon = '✅' if obj.aadhaar_verified else '❌'
        pan_icon = '✅' if obj.pan_verified else '❌'
        bank_icon = '✅' if obj.bank_verified else '❌'
        
        return format_html(
            '<div style="font-size: 20px;">'
            '<span title="Aadhaar">{}</span> '
            '<span title="PAN">{}</span> '
            '<span title="Bank">{}</span>'
            '</div>',
            aadhaar_icon,
            pan_icon,
            bank_icon
        )
    verification_summary.short_description = 'Verified'
    
    def aadhaar_status(self, obj):
        """Display Aadhaar verification status"""
        if obj.aadhaar_verified:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Verified</span><br>'
                '<small>{}</small>',
                obj.aadhaar_number or '—'
            )
        elif obj.aadhaar_number:
            return format_html(
                '<span style="color: #ffc107;">⏳ Unverified</span><br>'
                '<small>{}</small>',
                obj.aadhaar_number
            )
        return format_html('<span style="color: #999;">— Not Provided</span>')
    aadhaar_status.short_description = 'Aadhaar'
    
    def pan_status(self, obj):
        """Display PAN verification status"""
        if obj.pan_verified:
            linked_badge = ''
            if obj.pan_aadhaar_linked:
                linked_badge = '<br><span style="background: #28a745; color: white; padding: 1px 4px; border-radius: 2px; font-size: 9px;">🔗 Linked</span>'
            
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Verified</span><br>'
                '<small>{}</small>{}',
                obj.pan_number or '—',
                linked_badge
            )
        elif obj.pan_number:
            return format_html(
                '<span style="color: #ffc107;">⏳ Unverified</span><br>'
                '<small>{}</small>',
                obj.pan_number
            )
        return format_html('<span style="color: #999;">— Not Provided</span>')
    pan_status.short_description = 'PAN'
    
    def bank_status(self, obj):
        """Display bank verification status"""
        if obj.bank_verified:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Verified</span><br>'
                '<small>{}</small><br>'
                '<small style="color: #6c757d;">{}</small>',
                obj.bank_name or '—',
                obj.account_number[-4:].rjust(len(obj.account_number), '*') if obj.account_number else '—'
            )
        elif obj.account_number:
            return format_html(
                '<span style="color: #ffc107;">⏳ Unverified</span><br>'
                '<small>{}</small>',
                obj.bank_name or '—'
            )
        return format_html('<span style="color: #999;">— Not Provided</span>')
    bank_status.short_description = 'Bank'
    
    def completion_progress(self, obj):
        """Display KYC completion progress bar"""
        total_steps = 3
        completed_steps = sum([
            obj.aadhaar_verified,
            obj.pan_verified,
            obj.bank_verified
        ])
        
        percentage = (completed_steps / total_steps) * 100
        
        if percentage == 100:
            color = '#28a745'
        elif percentage >= 66:
            color = '#17a2b8'
        elif percentage >= 33:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 10px; overflow: hidden; height: 20px;">'
            '<div style="width: {}%; background-color: {}; height: 100%; display: flex; align-items: center; justify-content: center;">'
            '<small style="color: white; font-weight: bold; font-size: 10px;">{:.0f}%</small>'
            '</div></div>'
            '<small>{}/3 verified</small>',
            percentage,
            color,
            percentage,
            completed_steps
        )
    completion_progress.short_description = 'Progress'
    
    def status_badge(self, obj):
        """Display KYC status badge"""
        colors = {
            'pending': '#ffc107',
            'under_review': '#17a2b8',
            'verified': '#28a745',
            'rejected': '#dc3545',
        }
        
        if obj.is_deleted:
            return format_html(
                '<span style="background-color: #000; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 10px;">🗑️ DELETED</span>'
            )
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def completion_percentage(self, obj):
        """Display detailed completion percentage"""
        total_steps = 3
        completed = sum([obj.aadhaar_verified, obj.pan_verified, obj.bank_verified])
        percentage = (completed / total_steps) * 100
        
        return format_html(
            '<div style="font-size: 24px; font-weight: bold; color: {};">{:.0f}%</div>'
            '<div style="margin-top: 10px;">'
            '<div>Aadhaar: {}</div>'
            '<div>PAN: {}</div>'
            '<div>Bank: {}</div>'
            '</div>',
            '#28a745' if percentage == 100 else '#ffc107',
            percentage,
            '✅ Verified' if obj.aadhaar_verified else '❌ Not Verified',
            '✅ Verified' if obj.pan_verified else '❌ Not Verified',
            '✅ Verified' if obj.bank_verified else '❌ Not Verified'
        )
    completion_percentage.short_description = 'Completion Status'
    
    # Document preview methods
    def aadhaar_front_preview(self, obj):
        """Preview Aadhaar front"""
        if obj.aadhaar_front:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd;" />'
                '</a><br><a href="{}" target="_blank" class="button">View Full Size</a>',
                obj.aadhaar_front.url,
                obj.aadhaar_front.url,
                obj.aadhaar_front.url
            )
        return format_html('<span style="color: #999;">No document uploaded</span>')
    aadhaar_front_preview.short_description = 'Aadhaar Front Preview'
    
    def aadhaar_back_preview(self, obj):
        """Preview Aadhaar back"""
        if obj.aadhaar_back:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd;" />'
                '</a><br><a href="{}" target="_blank" class="button">View Full Size</a>',
                obj.aadhaar_back.url,
                obj.aadhaar_back.url,
                obj.aadhaar_back.url
            )
        return format_html('<span style="color: #999;">No document uploaded</span>')
    aadhaar_back_preview.short_description = 'Aadhaar Back Preview'
    
    def pan_document_preview(self, obj):
        """Preview PAN document"""
        if obj.pan_document:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd;" />'
                '</a><br><a href="{}" target="_blank" class="button">View Full Size</a>',
                obj.pan_document.url,
                obj.pan_document.url,
                obj.pan_document.url
            )
        return format_html('<span style="color: #999;">No document uploaded</span>')
    pan_document_preview.short_description = 'PAN Document Preview'
    
    def bank_proof_preview(self, obj):
        """Preview bank proof"""
        if obj.bank_proof:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd;" />'
                '</a><br><a href="{}" target="_blank" class="button">View Full Size</a>',
                obj.bank_proof.url,
                obj.bank_proof.url,
                obj.bank_proof.url
            )
        return format_html('<span style="color: #999;">No document uploaded</span>')
    bank_proof_preview.short_description = 'Bank Proof Preview'
    
    def address_proof_preview(self, obj):
        """Preview address proof"""
        if obj.address_proof:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd;" />'
                '</a><br><a href="{}" target="_blank" class="button">View Full Size</a>',
                obj.address_proof.url,
                obj.address_proof.url,
                obj.address_proof.url
            )
        return format_html('<span style="color: #999;">No document uploaded</span>')
    address_proof_preview.short_description = 'Address Proof Preview'
    
    # API Response displays
    def aadhaar_api_response_display(self, obj):
        """Display Aadhaar API response"""
        if obj.aadhaar_api_response:
            try:
                formatted = json.dumps(obj.aadhaar_api_response, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; '
                    'max-height: 400px; overflow: auto;">{}</pre>',
                    formatted
                )
            except:
                pass
        return format_html('<span style="color: #999;">No API response</span>')
    aadhaar_api_response_display.short_description = 'Aadhaar API Response (Formatted)'
    
    def pan_api_response_display(self, obj):
        """Display PAN API response"""
        if obj.pan_api_response:
            try:
                formatted = json.dumps(obj.pan_api_response, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; '
                    'max-height: 400px; overflow: auto;">{}</pre>',
                    formatted
                )
            except:
                pass
        return format_html('<span style="color: #999;">No API response</span>')
    pan_api_response_display.short_description = 'PAN API Response (Formatted)'
    
    def bank_api_response_display(self, obj):
        """Display Bank API response"""
        if obj.bank_api_response:
            try:
                formatted = json.dumps(obj.bank_api_response, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; '
                    'max-height: 400px; overflow: auto;">{}</pre>',
                    formatted
                )
            except:
                pass
        return format_html('<span style="color: #999;">No API response</span>')
    bank_api_response_display.short_description = 'Bank API Response (Formatted)'
    
    # Bulk Actions
    actions = [
        'mark_under_review',
        'verify_kyc',
        'reject_kyc',
        'verify_aadhaar',
        'verify_pan',
        'verify_bank',
        'soft_delete_kyc',
        'restore_kyc',
    ]
    
    def mark_under_review(self, request, queryset):
        """Mark KYC as under review"""
        count = queryset.filter(status='pending').update(status='under_review')
        self.message_user(request, f'{count} KYC record(s) marked under review.')
    mark_under_review.short_description = '🔍 Mark Under Review'
    
    def verify_kyc(self, request, queryset):
        """Verify complete KYC"""
        count = 0
        for kyc in queryset:
            if kyc.is_complete():
                kyc.status = 'verified'
                kyc.verified_at = timezone.now()
                kyc.verified_by = request.user
                kyc.save()
                
                # Update user KYC status
                kyc.user.kyc_status = 'verified'
                kyc.user.kyc_verified_at = timezone.now()
                kyc.user.save()
                
                count += 1
        
        self.message_user(
            request,
            f'{count} KYC record(s) verified successfully.',
            level='SUCCESS'
        )
    verify_kyc.short_description = '✓ Verify Complete KYC'
    
    def reject_kyc(self, request, queryset):
        """Reject KYC"""
        count = queryset.update(
            status='rejected',
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{count} KYC record(s) rejected.', level='WARNING')
    reject_kyc.short_description = '❌ Reject KYC'
    
    def verify_aadhaar(self, request, queryset):
        """Mark Aadhaar as verified"""
        count = queryset.update(
            aadhaar_verified=True,
            aadhaar_verified_at=timezone.now()
        )
        self.message_user(request, f'{count} Aadhaar verification(s) marked.')
    verify_aadhaar.short_description = '✓ Verify Aadhaar'
    
    def verify_pan(self, request, queryset):
        """Mark PAN as verified"""
        count = queryset.update(
            pan_verified=True,
            pan_verified_at=timezone.now()
        )
        self.message_user(request, f'{count} PAN verification(s) marked.')
    verify_pan.short_description = '✓ Verify PAN'
    
    def verify_bank(self, request, queryset):
        """Mark bank as verified"""
        count = queryset.update(
            bank_verified=True,
            bank_verified_at=timezone.now()
        )
        self.message_user(request, f'{count} bank verification(s) marked.')
    verify_bank.short_description = '✓ Verify Bank'
    
    def soft_delete_kyc(self, request, queryset):
        """Soft delete KYC records"""
        count = queryset.filter(is_deleted=False).update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user
        )
        self.message_user(request, f'{count} KYC record(s) soft deleted.')
    soft_delete_kyc.short_description = '🗑️ Soft Delete'
    
    def restore_kyc(self, request, queryset):
        """Restore soft deleted KYC records"""
        count = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None
        )
        self.message_user(request, f'{count} KYC record(s) restored.')
    restore_kyc.short_description = '↻ Restore'
    
    def save_model(self, request, obj, form, change):
        """Auto-set verified_by when verifying"""
        if change and 'status' in form.changed_data:
            if obj.status == 'verified':
                if not obj.verified_by:
                    obj.verified_by = request.user
                if not obj.verified_at:
                    obj.verified_at = timezone.now()
                
                # Update user KYC status
                obj.user.kyc_status = 'verified'
                obj.user.kyc_verified_at = timezone.now()
                obj.user.save()
        
        super().save_model(request, obj, form, change)


# ============================================
# DOCUMENT ADMIN
# ============================================

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for Document management"""
    
    list_display = [
        'user_link',
        'document_type_badge',
        'file_name',
        'file_size_display',
        'file_preview_thumb',
        'created_at',
    ]
    
    list_filter = [
        DocumentTypeFilter,
        SoftDeleteKYCFilter,
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'file_name',
        'description',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'file_size',
        'mime_type',
        'created_at',
        'updated_at',
        'deleted_at',
        'deleted_by',
        'file_preview',
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': (
                'user',
                'document_type',
                'file',
                'file_preview',
                'file_name',
                'file_size',
                'mime_type',
                'description',
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
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    autocomplete_fields = ['user', 'deleted_by']
    
    # Custom display methods
    def user_link(self, obj):
        """Display user as link"""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def document_type_badge(self, obj):
        """Display document type badge"""
        colors = {
            'aadhaar': '#007bff',
            'pan': '#28a745',
            'bank': '#17a2b8',
            'address': '#ffc107',
            'photo': '#6f42c1',
            'signature': '#fd7e14',
            'other': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.document_type, '#6c757d'),
            obj.get_document_type_display()
        )
    document_type_badge.short_description = 'Type'
    
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return format_html('{:.1f} {}', size, unit)
            size /= 1024.0
        return format_html('{:.1f} TB', size)
    file_size_display.short_description = 'Size'
    file_size_display.admin_order_field = 'file_size'
    
    def file_preview_thumb(self, obj):
        """Small thumbnail in list view"""
        if obj.file:
            if obj.mime_type and obj.mime_type.startswith('image/'):
                return format_html(
                    '<img src="{}" style="width: 60px; height: 40px; object-fit: cover; border-radius: 3px;" />',
                    obj.file.url
                )
            return format_html('📄 {}', obj.file_name[:20])
        return format_html('<span style="color: #999;">—</span>')
    file_preview_thumb.short_description = 'Preview'
    
    def file_preview(self, obj):
        """Full file preview"""
        if obj.file:
            if obj.mime_type and obj.mime_type.startswith('image/'):
                return format_html(
                    '<a href="{}" target="_blank">'
                    '<img src="{}" style="max-width: 400px; max-height: 300px; border: 1px solid #ddd;" />'
                    '</a><br><a href="{}" target="_blank" class="button">Download</a>',
                    obj.file.url,
                    obj.file.url,
                    obj.file.url
                )
            else:
                return format_html(
                    '<div style="padding: 10px; background: #f5f5f5; border-radius: 5px;">'
                    '<strong>File:</strong> {}<br>'
                    '<strong>Size:</strong> {}<br>'
                    '<strong>Type:</strong> {}<br>'
                    '<a href="{}" target="_blank" class="button" style="margin-top: 10px;">📄 Download</a>'
                    '</div>',
                    obj.file_name,
                    self.file_size_display(obj),
                    obj.mime_type or 'Unknown',
                    obj.file.url
                )
        return format_html('<span style="color: #999;">No file</span>')
    file_preview.short_description = 'File Preview'


# ============================================
# AUDIT LOG ADMIN (Read-Only)
# ============================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin for Audit Log - Read Only"""
    
    list_display = [
        'created_at',
        'user_link',
        'action_badge',
        'description_short',
        'ip_address',
    ]
    
    list_filter = [
        AuditActionFilter,
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'description',
        'ip_address',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'user',
        'action',
        'description',
        'ip_address',
        'user_agent',
        'metadata',
        'metadata_display',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Event Information', {
            'fields': (
                'created_at',
                'user',
                'action',
                'description',
            )
        }),
        ('Request Information', {
            'fields': (
                'ip_address',
                'user_agent',
            ),
            'classes': ('collapse',),
        }),
        ('Additional Data', {
            'fields': (
                'metadata',
                'metadata_display',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # Disable add/edit/delete
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    # Custom display methods
    def user_link(self, obj):
        """Display user as link"""
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return format_html('<span style="color: #999;">System</span>')
    user_link.short_description = 'User'
    
    def action_badge(self, obj):
        """Display action as badge"""
        colors = {
            'kyc_submit': '#007bff',
            'kyc_approve': '#28a745',
            'kyc_reject': '#dc3545',
            'document_upload': '#17a2b8',
            'document_delete': '#dc3545',
            'profile_update': '#ffc107',
            'login': '#6f42c1',
            'logout': '#6c757d',
            'password_change': '#fd7e14',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            colors.get(obj.action, '#6c757d'),
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'
    
    def description_short(self, obj):
        """Truncated description"""
        if len(obj.description) > 60:
            return format_html(
                '<span title="{}">{}</span>',
                obj.description,
                obj.description[:60] + '...'
            )
        return obj.description
    description_short.short_description = 'Description'
    
    def metadata_display(self, obj):
        """Display metadata as formatted JSON"""
        if obj.metadata:
            try:
                formatted = json.dumps(obj.metadata, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px; '
                    'max-height: 300px; overflow: auto;">{}</pre>',
                    formatted
                )
            except:
                pass
        return format_html('<span style="color: #999;">No metadata</span>')
    metadata_display.short_description = 'Metadata (Formatted)'
