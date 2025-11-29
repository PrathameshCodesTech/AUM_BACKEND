# workflows/admin.py
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count, Q
from .models import ApprovalWorkflow


# ============================================
# CUSTOM FILTERS
# ============================================

class WorkflowTypeFilter(admin.SimpleListFilter):
    """Filter by workflow type"""
    title = 'workflow type'
    parameter_name = 'workflow'

    def lookups(self, request, model_admin):
        return (
            ('investment', 'Investment Approval'),
            ('property', 'Property Approval'),
            ('redemption', 'Redemption Approval'),
            ('payout', 'Payout Approval'),
            ('kyc', 'KYC Approval'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(workflow_type=self.value())


class WorkflowStatusFilter(admin.SimpleListFilter):
    """Filter by workflow status"""
    title = 'workflow status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())


class AssignedToFilter(admin.SimpleListFilter):
    """Filter workflows assigned to current user"""
    title = 'assigned to'
    parameter_name = 'assigned'

    def lookups(self, request, model_admin):
        return (
            ('me', 'My Tasks'),
            ('unassigned', 'Unassigned'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'me':
            return queryset.filter(assigned_to=request.user, status='pending')
        elif self.value() == 'unassigned':
            return queryset.filter(assigned_to__isnull=True, status='pending')


class ContentTypeFilter(admin.SimpleListFilter):
    """Filter by content type (model)"""
    title = 'entity type'
    parameter_name = 'entity'

    def lookups(self, request, model_admin):
        # Get unique content types used in workflows
        content_types = ApprovalWorkflow.objects.values_list(
            'content_type', flat=True
        ).distinct()
        
        types = []
        for ct_id in content_types:
            try:
                ct = ContentType.objects.get(id=ct_id)
                types.append((ct.id, ct.model.title()))
            except ContentType.DoesNotExist:
                pass
        
        return types

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(content_type_id=self.value())


# ============================================
# APPROVAL WORKFLOW ADMIN
# ============================================

@admin.register(ApprovalWorkflow)
class ApprovalWorkflowAdmin(admin.ModelAdmin):
    """Admin for Approval Workflow management"""
    
    list_display = [
        'workflow_id_display',
        'workflow_type_badge',
        'entity_link',
        'requested_by_link',
        'assigned_to_link',
        'status_badge',
        'pending_duration',
        'created_at',
    ]
    
    list_filter = [
        WorkflowStatusFilter,
        WorkflowTypeFilter,
        ContentTypeFilter,
        AssignedToFilter,
        'assigned_to',
        'reviewed_by',
        'created_at',
    ]
    
    search_fields = [
        'object_id',
        'requested_by__username',
        'requested_by__email',
        'assigned_to__username',
        'reviewed_by__username',
        'request_notes',
        'review_notes',
    ]
    
    ordering = ['-created_at']
    
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'reviewed_by',
        'reviewed_at',
        'content_type_display',
        'content_object_display',
        'pending_time_display',
    ]
    
    fieldsets = (
        ('Workflow Information', {
            'fields': (
                'workflow_type',
                'status',
            )
        }),
        ('Entity Details', {
            'fields': (
                'content_type',
                'object_id',
                'content_type_display',
                'content_object_display',
            ),
            'description': 'The entity this workflow is for',
        }),
        ('Request Information', {
            'fields': (
                'requested_by',
                'request_notes',
            )
        }),
        ('Assignment', {
            'fields': (
                'assigned_to',
            )
        }),
        ('Review Information', {
            'fields': (
                'reviewed_by',
                'reviewed_at',
                'review_notes',
            )
        }),
        ('Timing', {
            'fields': (
                'created_at',
                'updated_at',
                'pending_time_display',
            ),
            'classes': ('collapse',),
        }),
    )
    
    autocomplete_fields = [
        'requested_by',
        'assigned_to',
        'reviewed_by',
    ]
    
    # Limit content_type choices to relevant models
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit content_type choices to approval-enabled models"""
        if db_field.name == "content_type":
            # Define which models can have approval workflows
            kwargs["queryset"] = ContentType.objects.filter(
                model__in=[
                    'investment',
                    'property',
                    'redemptionrequest',
                    'payout',
                    'kyc',
                ]
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    # Custom display methods
    def workflow_id_display(self, obj):
        """Display workflow ID"""
        return format_html(
            'de style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">WF-{}</code>',
            str(obj.id).zfill(6)
        )
    workflow_id_display.short_description = 'Workflow ID'
    workflow_id_display.admin_order_field = 'id'
    
    def workflow_type_badge(self, obj):
        """Display workflow type badge"""
        colors = {
            'investment': '#007bff',
            'property': '#28a745',
            'redemption': '#ffc107',
            'payout': '#17a2b8',
            'kyc': '#6f42c1',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 10px; text-transform: uppercase;">{}</span>',
            colors.get(obj.workflow_type, '#6c757d'),
            obj.get_workflow_type_display()
        )
    workflow_type_badge.short_description = 'Type'
    workflow_type_badge.admin_order_field = 'workflow_type'
    
    def entity_link(self, obj):
        """Display linked entity as clickable link"""
        if not obj.content_object:
            return format_html('<span style="color: #dc3545;">Entity Deleted</span>')
        
        # Get the model name
        model_name = obj.content_type.model
        app_label = obj.content_type.app_label
        
        # Build admin URL
        try:
            url = reverse(
                f'admin:{app_label}_{model_name}_change',
                args=[obj.object_id]
            )
            
            # Get display text based on model
            if hasattr(obj.content_object, 'investment_id'):
                display = obj.content_object.investment_id
            elif hasattr(obj.content_object, 'payout_id'):
                display = obj.content_object.payout_id
            elif hasattr(obj.content_object, 'request_id'):
                display = obj.content_object.request_id
            elif hasattr(obj.content_object, 'name'):
                display = obj.content_object.name
            elif hasattr(obj.content_object, 'user'):
                display = f"{obj.content_object.user.username} KYC"
            else:
                display = f"{model_name.title()} #{obj.object_id}"
            
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                url,
                display
            )
        except:
            return format_html(
                '{} #{}',
                model_name.title(),
                obj.object_id
            )
    entity_link.short_description = 'Entity'
    
    def requested_by_link(self, obj):
        """Display requester as link"""
        url = reverse('admin:accounts_user_change', args=[obj.requested_by.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.requested_by.get_full_name() or obj.requested_by.username
        )
    requested_by_link.short_description = 'Requested By'
    
    def assigned_to_link(self, obj):
        """Display assigned user as link"""
        if obj.assigned_to:
            url = reverse('admin:accounts_user_change', args=[obj.assigned_to.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.assigned_to.get_full_name() or obj.assigned_to.username
            )
        return format_html('<span style="color: #ffc107;">⚠️ Unassigned</span>')
    assigned_to_link.short_description = 'Assigned To'
    
    def status_badge(self, obj):
        """Display workflow status badge"""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'cancelled': '#6c757d',
        }
        icons = {
            'pending': '⏳',
            'approved': '✓',
            'rejected': '❌',
            'cancelled': '○',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{} {}</span>',
            colors.get(obj.status, '#6c757d'),
            icons.get(obj.status, ''),
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def pending_duration(self, obj):
        """Display how long the workflow has been pending"""
        if obj.status == 'pending':
            duration = timezone.now() - obj.created_at
            hours = duration.total_seconds() / 3600
            
            if hours < 1:
                minutes = int(duration.total_seconds() / 60)
                return format_html(
                    '<span style="color: #28a745;">{} min</span>',
                    minutes
                )
            elif hours < 24:
                return format_html(
                    '<span style="color: #ffc107;">{} hrs</span>',
                    int(hours)
                )
            else:
                days = int(hours / 24)
                color = '#dc3545' if days > 3 else '#ffc107'
                return format_html(
                    '<span style="color: {};">{} days</span>',
                    color,
                    days
                )
        elif obj.status == 'approved' and obj.reviewed_at:
            duration = obj.reviewed_at - obj.created_at
            hours = int(duration.total_seconds() / 3600)
            if hours < 24:
                return format_html(
                    '<span style="color: #6c757d;">Took {} hrs</span>',
                    hours
                )
            else:
                return format_html(
                    '<span style="color: #6c757d;">Took {} days</span>',
                    int(hours / 24)
                )
        return format_html('<span style="color: #999;">—</span>')
    pending_duration.short_description = 'Duration'
    
    def content_type_display(self, obj):
        """Display content type in readable format"""
        return format_html(
            '<strong>{}</strong> ({})',
            obj.content_type.model.title(),
            obj.content_type.app_label
        )
    content_type_display.short_description = 'Entity Type'
    
    def content_object_display(self, obj):
        """Display content object details"""
        if not obj.content_object:
            return format_html('<span style="color: #dc3545;">❌ Entity has been deleted</span>')
        
        # Get the model instance
        instance = obj.content_object
        model_name = obj.content_type.model
        
        # Build display based on model type
        details = []
        
        if hasattr(instance, 'customer'):
            details.append(f"Customer: {instance.customer.username}")
        elif hasattr(instance, 'user'):
            details.append(f"User: {instance.user.username}")
        
        if hasattr(instance, 'amount'):
            details.append(f"Amount: ₹{instance.amount:,.2f}")
        
        if hasattr(instance, 'status'):
            details.append(f"Status: {instance.status}")
        
        html = f'<div style="padding: 10px; background: #f5f5f5; border-radius: 5px;">'
        html += f'<strong>{model_name.title()} #{obj.object_id}</strong><br>'
        
        if details:
            html += '<br>'.join(details)
        
        html += '</div>'
        
        return format_html(html)
    content_object_display.short_description = 'Entity Details'
    
    def pending_time_display(self, obj):
        """Display detailed pending time statistics"""
        if obj.status == 'pending':
            duration = timezone.now() - obj.created_at
            total_seconds = duration.total_seconds()
            
            days = int(total_seconds / 86400)
            hours = int((total_seconds % 86400) / 3600)
            minutes = int((total_seconds % 3600) / 60)
            
            return format_html(
                '<div style="font-size: 14px;">'
                '<strong>⏱️ Pending for:</strong><br>'
                '<span style="color: #dc3545; font-size: 18px;">{} days, {} hours, {} minutes</span>'
                '</div>',
                days, hours, minutes
            )
        elif obj.reviewed_at:
            duration = obj.reviewed_at - obj.created_at
            total_seconds = duration.total_seconds()
            
            days = int(total_seconds / 86400)
            hours = int((total_seconds % 86400) / 3600)
            
            return format_html(
                '<div style="font-size: 14px;">'
                '<strong>⏱️ Reviewed in:</strong><br>'
                '<span style="color: #28a745; font-size: 18px;">{} days, {} hours</span>'
                '</div>',
                days, hours
            )
        return format_html('<span style="color: #999;">Not yet reviewed</span>')
    pending_time_display.short_description = 'Time Tracking'
    
    # Bulk Actions
    actions = [
        'assign_to_me',
        'approve_workflows',
        'reject_workflows',
        'cancel_workflows',
        'reassign_workflows',
    ]
    
    def assign_to_me(self, request, queryset):
        """Assign selected workflows to current user"""
        count = queryset.filter(status='pending').update(assigned_to=request.user)
        self.message_user(request, f'{count} workflow(s) assigned to you.')
    assign_to_me.short_description = '👤 Assign to Me'
    
    def approve_workflows(self, request, queryset):
        """Approve selected workflows"""
        count = 0
        for workflow in queryset.filter(status='pending'):
            workflow.status = 'approved'
            workflow.reviewed_by = request.user
            workflow.reviewed_at = timezone.now()
            workflow.save()
            
            # Update the related object status if applicable
            if workflow.content_object and hasattr(workflow.content_object, 'status'):
                if workflow.workflow_type == 'investment':
                    workflow.content_object.status = 'approved'
                elif workflow.workflow_type == 'property':
                    workflow.content_object.status = 'approved'
                elif workflow.workflow_type == 'redemption':
                    workflow.content_object.status = 'approved'
                elif workflow.workflow_type == 'payout':
                    workflow.content_object.status = 'approved'
                elif workflow.workflow_type == 'kyc':
                    workflow.content_object.status = 'verified'
                
                workflow.content_object.save()
            
            count += 1
        
        self.message_user(
            request,
            f'{count} workflow(s) approved successfully.',
            level='SUCCESS'
        )
    approve_workflows.short_description = '✓ Approve Workflows'
    
    def reject_workflows(self, request, queryset):
        """Reject selected workflows"""
        count = 0
        for workflow in queryset.filter(status='pending'):
            workflow.status = 'rejected'
            workflow.reviewed_by = request.user
            workflow.reviewed_at = timezone.now()
            workflow.save()
            
            # Update the related object status if applicable
            if workflow.content_object and hasattr(workflow.content_object, 'status'):
                workflow.content_object.status = 'rejected'
                workflow.content_object.save()
            
            count += 1
        
        self.message_user(
            request,
            f'{count} workflow(s) rejected.',
            level='WARNING'
        )
    reject_workflows.short_description = '❌ Reject Workflows'
    
    def cancel_workflows(self, request, queryset):
        """Cancel selected workflows"""
        count = queryset.filter(status='pending').update(
            status='cancelled',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{count} workflow(s) cancelled.')
    cancel_workflows.short_description = '○ Cancel Workflows'
    
    def reassign_workflows(self, request, queryset):
        """Clear assignment for reassignment"""
        count = queryset.filter(status='pending').update(assigned_to=None)
        self.message_user(
            request,
            f'{count} workflow(s) unassigned for reassignment.',
            level='SUCCESS'
        )
    reassign_workflows.short_description = '🔄 Unassign for Reassignment'
    
    def save_model(self, request, obj, form, change):
        """Auto-set reviewed_by when status changes"""
        if change and 'status' in form.changed_data:
            if obj.status in ['approved', 'rejected']:
                if not obj.reviewed_by:
                    obj.reviewed_by = request.user
                if not obj.reviewed_at:
                    obj.reviewed_at = timezone.now()
        
        super().save_model(request, obj, form, change)
    
    # Change list customization
    def changelist_view(self, request, extra_context=None):
        """Add workflow statistics to changelist"""
        extra_context = extra_context or {}
        
        # Get statistics
        total = ApprovalWorkflow.objects.count()
        pending = ApprovalWorkflow.objects.filter(status='pending').count()
        my_tasks = ApprovalWorkflow.objects.filter(
            assigned_to=request.user,
            status='pending'
        ).count()
        
        extra_context['workflow_stats'] = {
            'total': total,
            'pending': pending,
            'my_tasks': my_tasks,
        }
        
        return super().changelist_view(request, extra_context=extra_context)
