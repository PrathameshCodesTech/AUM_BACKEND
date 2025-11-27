# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Organization, Role, OrganizationMember

# Default roles configuration
DEFAULT_ROLES = [
    {
        'name': 'tenant_admin',
        'display_name': 'Tenant Admin',
        'description': 'Organization administrator with full control',
        'level': 90,
        'is_system': True,
        'color': '#007bff',
    },
    {
        'name': 'channel_partner',
        'display_name': 'Channel Partner',
        'description': 'Brings customers and earns commissions',
        'level': 50,
        'is_system': True,
        'color': '#28a745',
    },
    {
        'name': 'developer',
        'display_name': 'Developer/Builder',
        'description': 'Creates and manages properties',
        'level': 60,
        'is_system': True,
        'color': '#ffc107',
    },
    {
        'name': 'customer',
        'display_name': 'Customer',
        'description': 'End investor',
        'level': 10,
        'is_system': True,
        'color': '#6c757d',
    },
]


@receiver(post_save, sender=Organization)
def create_default_roles(sender, instance, created, **kwargs):
    """
    Automatically create default roles when new organization is created
    """
    if created:
        # Create default roles for this organization
        for role_data in DEFAULT_ROLES:
            Role.objects.get_or_create(
                name=role_data['name'],
                organization=instance,
                defaults={
                    'display_name': role_data['display_name'],
                    'description': role_data['description'],
                    'level': role_data['level'],
                    'is_system': role_data['is_system'],
                    'color': role_data['color'],
                }
            )
        
        # Automatically assign owner as tenant_admin
        tenant_admin_role = Role.objects.get(
            name='tenant_admin',
            organization=instance
        )
        
        OrganizationMember.objects.get_or_create(
            user=instance.owner,
            organization=instance,
            defaults={
                'role': tenant_admin_role,
                'is_active': True,
                'is_primary': True,
            }
        )