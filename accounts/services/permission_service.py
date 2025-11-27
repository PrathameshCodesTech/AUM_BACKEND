# accounts/services/permission_service.py
from django.core.cache import cache
from django.db.models import Q
from accounts.models import OrganizationMember, Permission, RolePermission

class PermissionService:
    """
    Centralized service for all permission checks
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def get_user_permissions(user, organization):
        """
        Get all permissions for user in specific organization
        Returns: QuerySet of Permission objects
        """
        cache_key = f"user_perms_{user.id}_{organization.id}"
        
        # Try cache first
        cached_perms = cache.get(cache_key)
        if cached_perms is not None:
            return cached_perms
        
        # Get user's role in organization
        try:
            membership = OrganizationMember.objects.select_related('role').get(
                user=user,
                organization=organization,
                is_active=True
            )
            
            # Get all permissions for this role
            permissions = Permission.objects.filter(
                role_assignments__role=membership.role
            ).distinct()
            
            # Cache the result
            cache.set(cache_key, permissions, PermissionService.CACHE_TIMEOUT)
            
            return permissions
        
        except OrganizationMember.DoesNotExist:
            return Permission.objects.none()
    
    @staticmethod
    def has_permission(user, organization, permission_code):
        """
        Check if user has specific permission in organization
        
        Args:
            user: User object
            organization: Organization object
            permission_code: String like 'properties.create'
        
        Returns: Boolean
        """
        cache_key = f"user_has_perm_{user.id}_{organization.id}_{permission_code}"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Check permission
        permissions = PermissionService.get_user_permissions(user, organization)
        has_perm = permissions.filter(code_name=permission_code).exists()
        
        # Cache the result
        cache.set(cache_key, has_perm, PermissionService.CACHE_TIMEOUT)
        
        return has_perm
    
    @staticmethod
    def has_any_permission(user, organization, permission_codes):
        """
        Check if user has ANY of the given permissions
        
        Args:
            permission_codes: List of permission codes
        
        Returns: Boolean
        """
        permissions = PermissionService.get_user_permissions(user, organization)
        return permissions.filter(code_name__in=permission_codes).exists()
    
    @staticmethod
    def has_all_permissions(user, organization, permission_codes):
        """
        Check if user has ALL of the given permissions
        
        Args:
            permission_codes: List of permission codes
        
        Returns: Boolean
        """
        permissions = PermissionService.get_user_permissions(user, organization)
        perm_codes = set(permissions.values_list('code_name', flat=True))
        return all(code in perm_codes for code in permission_codes)
    
    @staticmethod
    def get_role_in_org(user, organization):
        """
        Get user's role in organization
        
        Returns: Role object or None
        """
        try:
            membership = OrganizationMember.objects.select_related('role').get(
                user=user,
                organization=organization,
                is_active=True
            )
            return membership.role
        except OrganizationMember.DoesNotExist:
            return None
    
    @staticmethod
    def is_superadmin(user):
        """
        Check if user is platform superadmin
        """
        # Option 1: Check if user has global superadmin role
        return OrganizationMember.objects.filter(
            user=user,
            role__name='superadmin',
            role__organization__isnull=True,
            is_active=True
        ).exists()
        
        # Option 2: Use Django's is_superuser flag
        # return user.is_superuser
    
    @staticmethod
    def is_tenant_admin(user, organization):
        """
        Check if user is tenant admin in organization
        """
        return OrganizationMember.objects.filter(
            user=user,
            organization=organization,
            role__name='tenant_admin',
            is_active=True
        ).exists()
    
    @staticmethod
    def clear_user_permission_cache(user, organization):
        """
        Clear permission cache for user in organization
        Call this when user's role or permissions change
        """
        cache_key = f"user_perms_{user.id}_{organization.id}"
        cache.delete(cache_key)
        
        # Also clear individual permission checks
        # This is a bit brute force, but ensures consistency
        cache.delete_pattern(f"user_has_perm_{user.id}_{organization.id}_*")
    
    @staticmethod
    def get_users_with_permission(organization, permission_code):
        """
        Get all users who have a specific permission in organization
        
        Returns: QuerySet of User objects
        """
        from accounts.models import User
        
        return User.objects.filter(
            memberships__organization=organization,
            memberships__is_active=True,
            memberships__role__role_permissions__permission__code_name=permission_code
        ).distinct()