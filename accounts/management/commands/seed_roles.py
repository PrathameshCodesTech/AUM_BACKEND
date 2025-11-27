# accounts/management/commands/seed_roles.py
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Role, Permission, RolePermission, Organization

class Command(BaseCommand):
    help = 'Seed default roles and permissions for all organizations'
    
    # Define default roles with their properties
    DEFAULT_ROLES = [
        {
            'name': 'superadmin',
            'display_name': 'Superadmin',
            'description': 'Platform owner with full access to all organizations',
            'level': 100,
            'is_system': True,
            'color': '#dc3545',  # Red
            'organization': None,  # Global role
        },
        {
            'name': 'tenant_admin',
            'display_name': 'Tenant Admin',
            'description': 'Organization administrator with full control within their organization',
            'level': 90,
            'is_system': True,
            'color': '#007bff',  # Blue
        },
        {
            'name': 'channel_partner',
            'display_name': 'Channel Partner',
            'description': 'Brings customers and earns commissions',
            'level': 50,
            'is_system': True,
            'color': '#28a745',  # Green
        },
        {
            'name': 'developer',
            'display_name': 'Developer/Builder',
            'description': 'Creates and manages properties',
            'level': 60,
            'is_system': True,
            'color': '#ffc107',  # Yellow
        },
        {
            'name': 'customer',
            'display_name': 'Customer',
            'description': 'End investor who invests in properties',
            'level': 10,
            'is_system': True,
            'color': '#6c757d',  # Gray
        },
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--org-id',
            type=int,
            help='Seed roles for specific organization ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Seed roles for all organizations',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing roles (dangerous!)',
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        org_id = options.get('org_id')
        seed_all = options.get('all')
        reset = options.get('reset')
        
        if org_id:
            # Seed for specific org
            try:
                org = Organization.objects.get(id=org_id)
                self.seed_roles_for_org(org, reset)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully seeded roles for {org.name}')
                )
            except Organization.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Organization with ID {org_id} does not exist')
                )
        
        elif seed_all:
            # Seed for all orgs
            orgs = Organization.objects.filter(is_active=True)
            count = 0
            for org in orgs:
                self.seed_roles_for_org(org, reset)
                count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully seeded roles for {count} organizations')
            )
        
        else:
            # Seed global superadmin role only
            self.seed_global_roles(reset)
            self.stdout.write(
                self.style.SUCCESS('✅ Successfully seeded global roles')
            )
            self.stdout.write(
                self.style.WARNING('ℹ️  Use --org-id <id> or --all to seed organization roles')
            )
    
    def seed_global_roles(self, reset=False):
        """Seed global platform roles (superadmin)"""
        for role_data in self.DEFAULT_ROLES:
            # Only process superadmin role (which has organization: None)
            if role_data.get('organization') is not None:
                continue
            
            if reset:
                Role.objects.filter(
                    name=role_data['name'],
                    organization__isnull=True
                ).delete()
            
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                organization=None,
                defaults={
                    'display_name': role_data['display_name'],
                    'description': role_data['description'],
                    'level': role_data['level'],
                    'is_system': role_data['is_system'],
                    'color': role_data['color'],
                }
            )
            
            if created:
                self.stdout.write(f"  ✓ Created global role: {role.display_name}")
            else:
                self.stdout.write(f"  ✓ Global role exists: {role.display_name}")
    
    def seed_roles_for_org(self, organization, reset=False):
        """Seed default roles for specific organization"""
        for role_data in self.DEFAULT_ROLES:
            # Skip superadmin (it's global only)
            if role_data['name'] == 'superadmin':
                continue
            
            if reset:
                Role.objects.filter(
                    name=role_data['name'],
                    organization=organization
                ).delete()
            
            role, created = Role.objects.get_or_create(
                name=role_data['name'],
                organization=organization,
                defaults={
                    'display_name': role_data['display_name'],
                    'description': role_data['description'],
                    'level': role_data['level'],
                    'is_system': role_data['is_system'],
                    'color': role_data['color'],
                }
            )
            
            if created:
                self.stdout.write(f"  ✓ Created role: {role.display_name} for {organization.name}")
            else:
                self.stdout.write(f"  ✓ Role exists: {role.display_name} for {organization.name}")