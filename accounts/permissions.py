# accounts/permissions.py
from rest_framework import permissions


class HasPermission(permissions.BasePermission):
    """
    Check if user has specific permission

    Usage in view:
        permission_classes = [HasPermission]
        required_permission = 'properties.create'
    """
    message = "You don't have permission to perform this action"
    required_permission = None  # Override in view

    def has_permission(self, request, view):
        # Get required permission from view or class attribute
        perm = getattr(view, 'required_permission', self.required_permission)

        if not perm:
            return False

        # Check if user has the permission via their role
        return request.user.has_permission(perm)


class IsAdmin(permissions.BasePermission):
    """Check if user is admin"""
    message = "Only admins can perform this action"

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and
            request.user.role.slug == 'admin'
        )


class IsDeveloper(permissions.BasePermission):
    """Check if user is developer"""
    message = "Only developers can perform this action"

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and
            request.user.role.slug == 'developer'
        )


class IsChannelPartner(permissions.BasePermission):
    """Check if user is channel partner"""
    message = "Only channel partners can perform this action"

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and
            request.user.role.slug == 'channel_partner'
        )


class IsCustomer(permissions.BasePermission):
    """Check if user is customer"""
    message = "Only customers can perform this action"

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and
            request.user.role.slug == 'customer'
        )


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
        perms = getattr(view, 'required_permissions',
                        self.required_permissions)
        if not perms:
            return False

        # Check if user has ANY of the permissions
        user_perms = request.user.get_permissions().values_list('code_name', flat=True)
        return any(perm in user_perms for perm in perms)


class HasAllPermissions(permissions.BasePermission):
    """
    Check if user has ALL of the specified permissions

    Usage:
        permission_classes = [HasAllPermissions]
        required_permissions = ['properties.create', 'properties.approve']
    """
    message = "You don't have all the required permissions"
    required_permissions = []  # Override in view

    def has_permission(self, request, view):
        perms = getattr(view, 'required_permissions',
                        self.required_permissions)
        if not perms:
            return False

        # Check if user has ALL permissions
        user_perms = set(request.user.get_permissions(
        ).values_list('code_name', flat=True))
        required_perms = set(perms)
        return required_perms.issubset(user_perms)
