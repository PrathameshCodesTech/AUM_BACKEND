# accounts/permissions.py
from rest_framework import permissions
from accounts.services.permission_service import PermissionService

class HasOrganizationAccess(permissions.BasePermission):
    """
    Check if user is member of organization
    """
    message = "You are not a member of this organization"
    
    def has_permission(self, request, view):
        org_slug = view.kwargs.get('org_slug')
        if not org_slug:
            return False
        
        from accounts.models import Organization
        try:
            org = Organization.objects.get(slug=org_slug)
            return request.user.memberships.filter(
                organization=org,
                is_active=True
            ).exists()
        except Organization.DoesNotExist:
            return False


class HasPermission(permissions.BasePermission):
    """
    Check if user has specific permission in organization
    
    Usage in view:
        permission_classes = [HasPermission]
        required_permission = 'properties.create'
    """
    message = "You don't have permission to perform this action"
    required_permission = None  # Override in view
    
    def has_permission(self, request, view):
        if not self.required_permission:
            # If no permission specified, check if view has it
            self.required_permission = getattr(view, 'required_permission', None)
        
        if not self.required_permission:
            return False
        
        org_slug = view.kwargs.get('org_slug')
        if not org_slug:
            return False
        
        from accounts.models import Organization
        try:
            org = Organization.objects.get(slug=org_slug)
            return PermissionService.has_permission(
                request.user,
                org,
                self.required_permission
            )
        except Organization.DoesNotExist:
            return False


class IsSuperadmin(permissions.BasePermission):
    """Check if user is platform superadmin"""
    message = "Only superadmins can perform this action"
    
    def has_permission(self, request, view):
        return PermissionService.is_superadmin(request.user)


class IsTenantAdmin(permissions.BasePermission):
    """Check if user is tenant admin in organization"""
    message = "Only tenant admins can perform this action"
    
    def has_permission(self, request, view):
        org_slug = view.kwargs.get('org_slug')
        if not org_slug:
            return False
        
        from accounts.models import Organization
        try:
            org = Organization.objects.get(slug=org_slug)
            return PermissionService.is_tenant_admin(request.user, org)
        except Organization.DoesNotExist:
            return False


class HasAnyPermission(permissions.BasePermission):
    """
    Check if user has ANY of the specified permissions
    
    Usage:
        permission_classes = [HasAnyPermission]
        required_permissions = ['properties.create', 'properties.update']
    """
    message = "You don't have the required permissions"
    required_permissions = []  # Override in view
    
    def has_permission(self, request, view):
        perms = getattr(view, 'required_permissions', self.required_permissions)
        if not perms:
            return False
        
        org_slug = view.kwargs.get('org_slug')
        if not org_slug:
            return False
        
        from accounts.models import Organization
        try:
            org = Organization.objects.get(slug=org_slug)
            return PermissionService.has_any_permission(request.user, org, perms)
        except Organization.DoesNotExist:
            return False