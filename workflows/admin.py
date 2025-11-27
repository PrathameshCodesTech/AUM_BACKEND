# workflows/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ApprovalWorkflow


# ============================================
# APPROVAL WORKFLOW ADMIN
# ============================================
@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'colored_workflow_type', 'organization', 'requested_by',
        'colored_status', 'assigned_to', 'reviewed_by',
        'target_link', 'created_at', 'reviewed_at'
    )
    list_filter = (
        'workflow_type', 'status', 'organization',
        'created_at', 'reviewed_at'
    )
    search_fields = (
        'requested_by__username', 'reviewed_by__username',
        'assigned_to__username', 'request_notes', 'review_notes'
    )
    autocomplete_fields = ['organization', 'requested_by', 'assigned_to', 'reviewed_by']
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Workflow Info', {
            'fields': ('organization', 'workflow_type')
        }),
        ('Target Object', {
            'fields': ('content_type', 'object_id'),
            'description': 'The object being reviewed'
        }),
        ('Request Details', {
            'fields': ('requested_by', 'request_notes')
        }),
        ('Assignment & Status', {
            'fields': ('assigned_to', 'status')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    
    list_per_page = 100
    
    actions = ['approve_workflows', 'reject_workflows', 'assign_to_me']
    
    def colored_workflow_type(self, obj):
        colors = {
            'investment': '#007bff',    # Blue
            'property': '#28a745',      # Green
            'redemption': '#6f42c1',    # Purple
            'payout': '#17a2b8',        # Cyan
            'kyc': '#ffc107',           # Yellow
        }
        color = colors.get(obj.workflow_type, '#6c757d')
        
        icons = {
            'investment': '💰',
            'property': '🏠',
            'redemption': '↩️',
            'payout': '💸',
            'kyc': '✓'
        }
        icon = icons.get(obj.workflow_type, '📋')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: 600;">{} {}</span>',
            color, icon, obj.get_workflow_type_display()
        )
    colored_workflow_type.short_description = 'Type'
    colored_workflow_type.admin_order_field = 'workflow_type'
    
    def colored_status(self, obj):
        colors = {
            'pending': '#ffc107',     # Yellow
            'approved': '#28a745',    # Green
            'rejected': '#dc3545',    # Red
            'cancelled': '#6c757d',   # Gray
        }
        color = colors.get(obj.status, '#6c757d')
        
        icons = {
            'pending': '⏳',
            'approved': '✓',
            'rejected': '✗',
            'cancelled': '∅'
        }
        icon = icons.get(obj.status, '')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 4px 12px; border-radius: 3px; font-size: 11px; font-weight: 600;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'
    
    def target_link(self, obj):
        """Create a link to the target object in admin"""
        if obj.content_object:
            try:
                url = reverse(
                    f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                    args=[obj.object_id]
                )
                return format_html(
                    '<a href="{}" style="color: #007bff; text-decoration: none; '
                    'font-weight: 600;" target="_blank">'
                    '{} #{} ↗</a>',
                    url, obj.content_type.model.title(), obj.object_id
                )
            except:
                return format_html(
                    '<span style="color: #6c757d;">{} #{}</span>',
                    obj.content_type.model.title(), obj.object_id
                )
        return format_html('<span style="color: #dc3545;">Object not found</span>')
    target_link.short_description = 'Target'
    
    # Admin Actions
    def approve_workflows(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='approved',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} workflow(s) approved.', level='success')
    approve_workflows.short_description = "✓ Approve workflows"
    
    def reject_workflows(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} workflow(s) rejected.', level='warning')
    reject_workflows.short_description = "✗ Reject workflows"
    
    def assign_to_me(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            assigned_to=request.user
        )
        self.message_user(request, f'{updated} workflow(s) assigned to you.')
    assign_to_me.short_description = "👤 Assign to me"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'organization', 'requested_by', 'assigned_to',
            'reviewed_by', 'content_type'
        )
    
    # Custom view for workflow statistics
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response
        
        # Calculate statistics by type and status
        metrics = {
            'total_workflows': qs.count(),
            'pending': qs.filter(status='pending').count(),
            'approved': qs.filter(status='approved').count(),
            'rejected': qs.filter(status='rejected').count(),
            'my_assigned': qs.filter(assigned_to=request.user, status='pending').count(),
        }
        
        # Count by workflow type
        by_type = {}
        for choice in ApprovalWorkflow.WORKFLOW_TYPE_CHOICES:
            workflow_type = choice[0]
            count = qs.filter(workflow_type=workflow_type, status='pending').count()
            by_type[choice[1]] = count
        
        response.context_data['summary'] = metrics
        response.context_data['by_type'] = by_type
        return response
    
    # Custom filters for better UX
    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        
        # Add custom filter for "My Workflows"
        class MyWorkflowsFilter(admin.SimpleListFilter):
            title = 'My Workflows'
            parameter_name = 'my_workflows'
            
            def lookups(self, request, model_admin):
                return (
                    ('assigned', 'Assigned to me'),
                    ('requested', 'Requested by me'),
                    ('reviewed', 'Reviewed by me'),
                )
            
            def queryset(self, request, queryset):
                if self.value() == 'assigned':
                    return queryset.filter(assigned_to=request.user)
                if self.value() == 'requested':
                    return queryset.filter(requested_by=request.user)
                if self.value() == 'reviewed':
                    return queryset.filter(reviewed_by=request.user)
        
        list_filter.insert(0, MyWorkflowsFilter)
        return list_filter


# ============================================
# CUSTOM DASHBOARD WIDGET (Optional)
# ============================================
# Add this to your admin.py to show workflow summary on Django admin index

from django.contrib.admin import AdminSite
from django.shortcuts import render

# You can create a custom admin dashboard view
def workflow_dashboard(request):
    """Custom dashboard showing workflow statistics"""
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Get workflows from last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    recent_workflows = ApprovalWorkflow.objects.filter(
        created_at__gte=thirty_days_ago
    )
    
    stats = {
        'pending': recent_workflows.filter(status='pending').count(),
        'approved': recent_workflows.filter(status='approved').count(),
        'rejected': recent_workflows.filter(status='rejected').count(),
        'my_pending': recent_workflows.filter(
            assigned_to=request.user,
            status='pending'
        ).count(),
    }
    
    # Group by type
    by_type = recent_workflows.values('workflow_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Recent approvals
    recent_approvals = ApprovalWorkflow.objects.filter(
        status__in=['approved', 'rejected']
    ).select_related(
        'reviewed_by', 'requested_by', 'organization'
    ).order_by('-reviewed_at')[:10]
    
    context = {
        'stats': stats,
        'by_type': by_type,
        'recent_approvals': recent_approvals,
    }
    
    return render(request, 'admin/workflow_dashboard.html', context)
