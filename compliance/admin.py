# compliance/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import KYC, Document, AuditLog


# ============================================
# KYC ADMIN
# ============================================
@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'full_name', 'organization', 'colored_status',
        'pan_number', 'aadhaar_number', 'document_status',
        'reviewed_by', 'created_at'
    )
    list_filter = (
        'status', 'organization', 'gender', 'country',
        'reviewed_at', 'created_at', 'expires_at'
    )
    search_fields = (
        'user__username', 'user__email', 'full_name', 'father_name',
        'pan_number', 'aadhaar_number', 'account_number'
    )
    autocomplete_fields = ['user', 'organization', 'reviewed_by']
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'organization')
        }),
        ('Personal Details', {
            'fields': ('full_name', 'father_name', 'date_of_birth', 'gender')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'pincode')
        }),
        ('Identity Documents', {
            'fields': (
                ('pan_number', 'pan_document'),
                ('aadhaar_number', 'aadhaar_front', 'aadhaar_back'),
                ('additional_document_type', 'additional_document'),
                'photo'
            ),
            'classes': ('wide',)
        }),
        ('Bank Details', {
            'fields': (
                'bank_name', 'account_number', 'ifsc_code',
                'account_holder_name', 'cancelled_cheque'
            ),
            'classes': ('collapse',)
        }),
        ('Verification Status', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'expires_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    
    list_per_page = 50
    
    actions = ['mark_submitted', 'mark_under_review', 'verify_kyc', 'reject_kyc']
    
    def colored_status(self, obj):
        colors = {
            'pending': '#6c757d',      # Gray
            'submitted': '#17a2b8',    # Cyan
            'under_review': '#ffc107', # Yellow
            'verified': '#28a745',     # Green
            'rejected': '#dc3545',     # Red
            'expired': '#6c757d',      # Gray
        }
        color = colors.get(obj.status, '#6c757d')
        
        icons = {
            'pending': '⏳',
            'submitted': '📄',
            'under_review': '🔍',
            'verified': '✓',
            'rejected': '✗',
            'expired': '⏰'
        }
        icon = icons.get(obj.status, '')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 12px; border-radius: 3px; font-size: 11px; '
            'font-weight: 600;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'
    
    def document_status(self, obj):
        docs = []
        
        if obj.pan_document:
            docs.append('<span style="background-color: #007bff; color: white; '
                       'padding: 2px 6px; border-radius: 2px; font-size: 10px;">PAN</span>')
        
        if obj.aadhaar_front and obj.aadhaar_back:
            docs.append('<span style="background-color: #28a745; color: white; '
                       'padding: 2px 6px; border-radius: 2px; font-size: 10px;">Aadhaar</span>')
        
        if obj.photo:
            docs.append('<span style="background-color: #17a2b8; color: white; '
                       'padding: 2px 6px; border-radius: 2px; font-size: 10px;">Photo</span>')
        
        if obj.cancelled_cheque:
            docs.append('<span style="background-color: #6f42c1; color: white; '
                       'padding: 2px 6px; border-radius: 2px; font-size: 10px;">Bank</span>')
        
        if not docs:
            return format_html('<span style="color: #dc3545;">No documents</span>')
        
        return format_html(' '.join(docs))
    document_status.short_description = 'Documents'
    
    # Admin Actions
    def mark_submitted(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='submitted')
        self.message_user(request, f'{updated} KYC(s) marked as submitted.')
    mark_submitted.short_description = "📄 Mark as submitted"
    
    def mark_under_review(self, request, queryset):
        updated = queryset.filter(status='submitted').update(status='under_review')
        self.message_user(request, f'{updated} KYC(s) marked under review.')
    mark_under_review.short_description = "🔍 Mark under review"
    
    def verify_kyc(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(
            status__in=['submitted', 'under_review']
        ).update(
            status='verified',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} KYC(s) verified successfully.', level='success')
    verify_kyc.short_description = "✓ Verify KYC"
    
    def reject_kyc(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(
            status__in=['submitted', 'under_review']
        ).update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} KYC(s) rejected.', level='warning')
    reject_kyc.short_description = "✗ Reject KYC"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'organization', 'reviewed_by')


# ============================================
# DOCUMENT ADMIN
# ============================================
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'colored_category', 'organization', 'uploaded_by',
        'file_size_display', 'is_public', 'created_at'
    )
    list_filter = (
        'category', 'is_public', 'organization', 'created_at'
    )
    search_fields = (
        'title', 'description', 'tags',
        'uploaded_by__username', 'organization__name'
    )
    autocomplete_fields = ['organization', 'uploaded_by']
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Document Info', {
            'fields': ('title', 'category', 'file', 'file_size')
        }),
        ('Details', {
            'fields': ('description', 'tags')
        }),
        ('Organization & Access', {
            'fields': ('organization', 'uploaded_by', 'is_public')
        }),
    )
    
    readonly_fields = ('file_size', 'created_at', 'updated_at')
    
    list_per_page = 50
    
    def colored_category(self, obj):
        colors = {
            'agreement': '#007bff',     # Blue
            'invoice': '#28a745',       # Green
            'receipt': '#17a2b8',       # Cyan
            'legal': '#dc3545',         # Red
            'compliance': '#6f42c1',    # Purple
            'report': '#fd7e14',        # Orange
            'other': '#6c757d',         # Gray
        }
        color = colors.get(obj.category, '#6c757d')
        
        icons = {
            'agreement': '📄',
            'invoice': '💰',
            'receipt': '🧾',
            'legal': '⚖️',
            'compliance': '✓',
            'report': '📊',
            'other': '📎'
        }
        icon = icons.get(obj.category, '📎')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_category_display()
        )
    colored_category.short_description = 'Category'
    colored_category.admin_order_field = 'category'
    
    def file_size_display(self, obj):
        # Convert bytes to human-readable format
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return format_html(
                    '<span style="font-weight: 600; color: #495057;">{:.1f} {}</span>',
                    size, unit
                )
            size /= 1024.0
        return format_html(
            '<span style="font-weight: 600; color: #495057;">{:.1f} TB</span>',
            size
        )
    file_size_display.short_description = 'Size'
    file_size_display.admin_order_field = 'file_size'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('organization', 'uploaded_by')


# ============================================
# AUDIT LOG ADMIN
# ============================================
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp', 'user', 'organization', 'colored_action',
        'colored_module', 'description_short', 'ip_address'
    )
    list_filter = (
        'action', 'module', 'organization', 'timestamp'
    )
    search_fields = (
        'user__username', 'description', 'module',
        'target_model', 'ip_address'
    )
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Who & When', {
            'fields': ('user', 'organization', 'timestamp')
        }),
        ('What Happened', {
            'fields': ('action', 'module', 'description')
        }),
        ('Target', {
            'fields': ('target_model', 'target_id'),
            'classes': ('collapse',)
        }),
        ('Changes', {
            'fields': ('old_value', 'new_value'),
            'classes': ('collapse',)
        }),
        ('Request Info', {
            'fields': ('ip_address', 'user_agent', 'device_type'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('timestamp',)
    
    list_per_page = 100
    
    # Make audit logs read-only (no add/edit/delete)
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def colored_action(self, obj):
        colors = {
            'create': '#28a745',      # Green
            'update': '#007bff',      # Blue
            'delete': '#dc3545',      # Red
            'approve': '#28a745',     # Green
            'reject': '#dc3545',      # Red
            'login': '#17a2b8',       # Cyan
            'logout': '#6c757d',      # Gray
            'view': '#6c757d',        # Gray
            'download': '#ffc107',    # Yellow
            'payment': '#28a745',     # Green
            'other': '#6c757d',       # Gray
        }
        color = colors.get(obj.action, '#6c757d')
        
        icons = {
            'create': '➕',
            'update': '✏️',
            'delete': '🗑️',
            'approve': '✓',
            'reject': '✗',
            'login': '🔓',
            'logout': '🔒',
            'view': '👁️',
            'download': '⬇️',
            'payment': '💰',
            'other': '•'
        }
        icon = icons.get(obj.action, '•')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_action_display()
        )
    colored_action.short_description = 'Action'
    colored_action.admin_order_field = 'action'
    
    def colored_module(self, obj):
        colors = {
            'investments': '#20c997',      # Teal
            'properties': '#fd7e14',       # Orange
            'users': '#28a745',            # Green
            'commissions': '#ffc107',      # Yellow
            'kyc': '#6f42c1',              # Purple
            'wallet': '#17a2b8',           # Cyan
            'organizations': '#007bff',    # Blue
            'partners': '#28a745',         # Green
        }
        color = colors.get(obj.module, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px; font-size: 10px;">{}</span>',
            color, obj.module.upper()
        )
    colored_module.short_description = 'Module'
    colored_module.admin_order_field = 'module'
    
    def description_short(self, obj):
        if len(obj.description) > 60:
            return format_html(
                '<span title="{}">{}</span>',
                obj.description,
                obj.description[:60] + '...'
            )
        return obj.description
    description_short.short_description = 'Description'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'organization')
    
    # Custom view for audit statistics
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response
        
        # Calculate statistics
        metrics = {
            'total_logs': qs.count(),
            'create_count': qs.filter(action='create').count(),
            'update_count': qs.filter(action='update').count(),
            'delete_count': qs.filter(action='delete').count(),
            'login_count': qs.filter(action='login').count(),
            'unique_users': qs.values('user').distinct().count(),
        }
        
        response.context_data['summary'] = metrics
        return response


# ============================================
# CUSTOM ADMIN SITE ACTIONS
# ============================================

# Add custom admin site header for compliance section
admin.site.index_template = 'admin/custom_index.html'
