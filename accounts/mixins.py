from django.core.exceptions import PermissionDenied


class PermissionRequiredMixin:
    """
    Mixin for views that require specific permission

    Usage:
        class MyView(PermissionRequiredMixin, APIView):
            required_permission = 'properties.create'
    """
    required_permission = None

    def check_permission(self, request):
        """Override this for custom permission logic"""
        if not self.required_permission:
            return True

        return request.user.has_permission(self.required_permission)

    def dispatch(self, request, *args, **kwargs):
        if not self.check_permission(request):
            raise PermissionDenied(
                "You don't have permission to perform this action")

        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin:
    """
    Mixin for views that require specific role

    Usage:
        class MyView(RoleRequiredMixin, APIView):
            required_role = 'admin'
    """
    required_role = None

    def check_role(self, request):
        """Check if user has required role"""
        if not self.required_role:
            return True

        return (
            request.user.is_authenticated and
            request.user.role and
            request.user.role.slug == self.required_role
        )

    def dispatch(self, request, *args, **kwargs):
        if not self.check_role(request):
            raise PermissionDenied(
                f"Only {self.required_role}s can perform this action")

        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin:
    """Shortcut mixin for admin-only views"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required")

        if not request.user.role or request.user.role.slug != 'admin':
            raise PermissionDenied("Only admins can access this")

        return super().dispatch(request, *args, **kwargs)
