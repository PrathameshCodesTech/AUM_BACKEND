# accounts/services/permission_service.py
from django.core.cache import cache
from accounts.models import Permission


class PermissionService:
    """
    Centralized service for all permission checks (Simplified - Single Tenant)
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def get_user_permissions(user):
        """
        Get all permissions for user via their role
        Returns: QuerySet of Permission objects
        """
        if not user.is_authenticated or not user.role:
            return Permission.objects.none()
        
        cache_key = f"user_perms_{user.id}"
        
        # Try cache first
        cached_perms = cache.get(cache_key)
        if cached_perms is not None:
            return cached_perms
        
        # Get all permissions for user's role
        permissions = Permission.objects.filter(
            role_assignments__role=user.role
        ).distinct()
        
        # Cache the result
        cache.set(cache_key, permissions, PermissionService.CACHE_TIMEOUT)
        
        return permissions
    
    @staticmethod
    def has_permission(user, permission_code):
        """
        Check if user has specific permission
        
        Args:
            user: User object
            permission_code: String like 'properties.create'
        
        Returns: Boolean
        """
        if not user.is_authenticated or not user.role:
            return False
        
        cache_key = f"user_has_perm_{user.id}_{permission_code}"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Check permission
        permissions = PermissionService.get_user_permissions(user)
        has_perm = permissions.filter(code_name=permission_code).exists()
        
        # Cache the result
        cache.set(cache_key, has_perm, PermissionService.CACHE_TIMEOUT)
        
        return has_perm
    
    @staticmethod
    def has_any_permission(user, permission_codes):
        """
        Check if user has ANY of the given permissions
        
        Args:
            user: User object
            permission_codes: List of permission codes
        
        Returns: Boolean
        """
        if not user.is_authenticated or not user.role:
            return False
        
        permissions = PermissionService.get_user_permissions(user)
        return permissions.filter(code_name__in=permission_codes).exists()
    
    @staticmethod
    def has_all_permissions(user, permission_codes):
        """
        Check if user has ALL of the given permissions
        
        Args:
            user: User object
            permission_codes: List of permission codes
        
        Returns: Boolean
        """
        if not user.is_authenticated or not user.role:
            return False
        
        permissions = PermissionService.get_user_permissions(user)
        perm_codes = set(permissions.values_list('code_name', flat=True))
        return all(code in perm_codes for code in permission_codes)
    
    @staticmethod
    def get_user_role(user):
        """
        Get user's role
        
        Returns: Role object or None
        """
        if not user.is_authenticated:
            return None
        return user.role
    
    @staticmethod
    def is_admin(user):
        """
        Check if user is admin
        """
        return (
            user.is_authenticated and 
            user.role and 
            user.role.slug == 'admin'
        )
    
    @staticmethod
    def is_developer(user):
        """
        Check if user is developer
        """
        return (
            user.is_authenticated and 
            user.role and 
            user.role.slug == 'developer'
        )
    
    @staticmethod
    def is_channel_partner(user):
        """
        Check if user is channel partner
        """
        return (
            user.is_authenticated and 
            user.role and 
            user.role.slug == 'channel_partner'
        )
    
    @staticmethod
    def is_customer(user):
        """
        Check if user is customer
        """
        return (
            user.is_authenticated and 
            user.role and 
            user.role.slug == 'customer'
        )
    
    @staticmethod
    def clear_user_permission_cache(user):
        """
        Clear permission cache for user
        Call this when user's role or permissions change
        """
        cache_key = f"user_perms_{user.id}"
        cache.delete(cache_key)
        
        # Clear individual permission checks
        # Note: This requires Django cache backend that supports pattern deletion
        # For production, use Redis with django-redis
        try:
            cache.delete_pattern(f"user_has_perm_{user.id}_*")
        except AttributeError:
            # Fallback if delete_pattern not available (simple cache backend)
            pass
    
    @staticmethod
    def get_users_with_permission(permission_code):
        """
        Get all users who have a specific permission
        
        Args:
            permission_code: String like 'properties.create'
        
        Returns: QuerySet of User objects
        """
        from accounts.models import User
        
        return User.objects.filter(
            role__role_permissions__permission__code_name=permission_code
        ).distinct()
    
    @staticmethod
    def get_users_by_role(role_slug):
        """
        Get all users with specific role
        
        Args:
            role_slug: String like 'admin', 'developer', etc.
        
        Returns: QuerySet of User objects
        """
        from accounts.models import User
        
        return User.objects.filter(
            role__slug=role_slug,
            is_active=True
        )
    
    @staticmethod
    def get_permission_codes(user):
        """
        Get list of permission codes for user
        
        Returns: List of permission code strings
        """
        if not user.is_authenticated or not user.role:
            return []
        
        permissions = PermissionService.get_user_permissions(user)
        return list(permissions.values_list('code_name', flat=True))