# accounts/mixins.py
from django.core.exceptions import PermissionDenied
from accounts.services.permission_service import PermissionService
from accounts.models import Organization

class PermissionRequiredMixin:
    """
    Mixin for views that require specific permission
    
    Usage:
        class MyView(PermissionRequiredMixin, APIView):
            required_permission = 'properties.create'
    """
    required_permission = None
    
    def check_permission(self, request, organization):
        """Override this for custom permission logic"""
        if not self.required_permission:
            return True
        
        return PermissionService.has_permission(
            request.user,
            organization,
            self.required_permission
        )
    
    def dispatch(self, request, *args, **kwargs):
        # Get organization from kwargs
        org_slug = kwargs.get('org_slug')
        if org_slug:
            try:
                org = Organization.objects.get(slug=org_slug)
                if not self.check_permission(request, org):
                    raise PermissionDenied("You don't have permission to perform this action")
            except Organization.DoesNotExist:
                raise PermissionDenied("Organization not found")
        
        return super().dispatch(request, *args, **kwargs)


class OrganizationAccessMixin:
    """
    Ensure user has access to organization
    Adds 'organization' to view context
    """
    
    def dispatch(self, request, *args, **kwargs):
        org_slug = kwargs.get('org_slug')
        if org_slug:
            try:
                self.organization = Organization.objects.get(slug=org_slug)
                
                # Check if user is member
                if not request.user.memberships.filter(
                    organization=self.organization,
                    is_active=True
                ).exists():
                    raise PermissionDenied("You are not a member of this organization")
                
            except Organization.DoesNotExist:
                raise PermissionDenied("Organization not found")
        
        return super().dispatch(request, *args, **kwargs)