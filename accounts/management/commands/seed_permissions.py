# accounts/management/commands/seed_permissions.py
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Permission, Role, RolePermission, Organization


class Command(BaseCommand):
    help = 'Seed all permissions and assign to default roles'

    # Define all permissions organized by module
    PERMISSIONS = {
        'organizations': [
            ('create', 'Create Organization', 'Organization Management'),
            ('read', 'View Organization', 'Organization Management'),
            ('update', 'Update Organization', 'Organization Management'),
            ('delete', 'Delete Organization', 'Organization Management'),
            ('manage', 'Manage Organization Settings', 'Organization Management'),
            ('manage_subscription', 'Manage Subscription', 'Organization Management'),
        ],
        'users': [
            ('create', 'Create User', 'User Management'),
            ('read', 'View User', 'User Management'),
            ('update', 'Update User', 'User Management'),
            ('delete', 'Delete User', 'User Management'),
            ('manage_roles', 'Manage User Roles', 'User Management'),
            ('block', 'Block/Unblock User', 'User Management'),
            ('view_all', 'View All Users', 'User Management'),
        ],
        'roles': [
            ('create', 'Create Role', 'Role Management'),
            ('read', 'View Role', 'Role Management'),
            ('update', 'Update Role', 'Role Management'),
            ('delete', 'Delete Role', 'Role Management'),
            ('assign_permissions', 'Assign Permissions to Role', 'Role Management'),
        ],
        'properties': [
            ('create', 'Create Property', 'Property Management'),
            ('read', 'View Property', 'Property Management'),
            ('update', 'Update Property', 'Property Management'),
            ('delete', 'Delete Property', 'Property Management'),
            ('approve', 'Approve Property', 'Property Management'),
            ('reject', 'Reject Property', 'Property Management'),
            ('publish', 'Publish Property', 'Property Management'),
            ('view_all', 'View All Properties', 'Property Management'),
            ('manage_units', 'Manage Property Units', 'Property Management'),
            ('upload_documents', 'Upload Property Documents', 'Property Management'),
        ],
        'investments': [
            ('create', 'Make Investment', 'Investment Operations'),
            ('read', 'View Investment', 'Investment Operations'),
            ('update', 'Update Investment', 'Investment Operations'),
            ('delete', 'Cancel Investment', 'Investment Operations'),
            ('approve', 'Approve Investment', 'Investment Operations'),
            ('reject', 'Reject Investment', 'Investment Operations'),
            ('view_all', 'View All Investments', 'Investment Operations'),
            ('view_own', 'View Own Investments', 'Investment Operations'),
        ],
        'wallet': [
            ('view', 'View Wallet Balance', 'Wallet Management'),
            ('deposit', 'Deposit to Wallet', 'Wallet Management'),
            ('withdraw', 'Withdraw from Wallet', 'Wallet Management'),
            ('view_transactions', 'View Transactions', 'Wallet Management'),
        ],
        'commissions': [
            ('view_own', 'View Own Commissions', 'Commission Management'),
            ('view_all', 'View All Commissions', 'Commission Management'),
            ('approve', 'Approve Commission', 'Commission Management'),
            ('process_payout', 'Process Commission Payout', 'Commission Management'),
            ('configure_rules', 'Configure Commission Rules', 'Commission Management'),
        ],
        'channel_partners': [
            ('create', 'Create Channel Partner', 'CP Management'),
            ('read', 'View Channel Partner', 'CP Management'),
            ('update', 'Update Channel Partner', 'CP Management'),
            ('delete', 'Delete Channel Partner', 'CP Management'),
            ('verify', 'Verify Channel Partner', 'CP Management'),
            ('view_customers', 'View CP Customers', 'CP Management'),
            ('view_hierarchy', 'View CP Hierarchy', 'CP Management'),
        ],
        'payouts': [
            ('create', 'Create Payout', 'Payout Management'),
            ('read', 'View Payout', 'Payout Management'),
            ('approve', 'Approve Payout', 'Payout Management'),
            ('process', 'Process Payout', 'Payout Management'),
            ('view_all', 'View All Payouts', 'Payout Management'),
        ],
        'redemptions': [
            ('create', 'Request Redemption', 'Redemption Management'),
            ('read', 'View Redemption Request', 'Redemption Management'),
            ('approve', 'Approve Redemption', 'Redemption Management'),
            ('reject', 'Reject Redemption', 'Redemption Management'),
            ('process', 'Process Redemption', 'Redemption Management'),
        ],
        'kyc': [
            ('submit', 'Submit KYC', 'KYC Management'),
            ('view_own', 'View Own KYC', 'KYC Management'),
            ('view_all', 'View All KYC', 'KYC Management'),
            ('verify', 'Verify KYC', 'KYC Management'),
            ('reject', 'Reject KYC', 'KYC Management'),
        ],
        'reports': [
            ('view_dashboard', 'View Dashboard', 'Reporting'),
            ('view_financial', 'View Financial Reports', 'Reporting'),
            ('view_analytics', 'View Analytics', 'Reporting'),
            ('export', 'Export Reports', 'Reporting'),
        ],
        'teams': [
            ('create', 'Create Team', 'Team Management'),
            ('read', 'View Team', 'Team Management'),
            ('update', 'Update Team', 'Team Management'),
            ('delete', 'Delete Team', 'Team Management'),
            ('manage_members', 'Manage Team Members', 'Team Management'),
        ],
    }

    # Define which permissions each role should have
    ROLE_PERMISSIONS = {
        'superadmin': 'ALL',  # Gets all permissions
        'tenant_admin': [
            # Organization
            'organizations.read', 'organizations.update', 'organizations.manage',
            'organizations.manage_subscription',
            # Users
            'users.create', 'users.read', 'users.update', 'users.delete',
            'users.manage_roles', 'users.block', 'users.view_all',
            # Roles
            'roles.create', 'roles.read', 'roles.update', 'roles.delete',
            'roles.assign_permissions',
            # Properties
            'properties.create', 'properties.read', 'properties.update',
            'properties.delete', 'properties.approve', 'properties.reject',
            'properties.publish', 'properties.view_all', 'properties.manage_units',
            'properties.upload_documents',
            # Investments
            'investments.read', 'investments.update', 'investments.approve',
            'investments.reject', 'investments.view_all',
            # Wallet
            'wallet.view', 'wallet.view_transactions',
            # Commissions
            'commissions.view_all', 'commissions.approve', 'commissions.process_payout',
            'commissions.configure_rules',
            # Channel Partners
            'channel_partners.create', 'channel_partners.read', 'channel_partners.update',
            'channel_partners.delete', 'channel_partners.verify', 'channel_partners.view_customers',
            'channel_partners.view_hierarchy',
            # Payouts
            'payouts.create', 'payouts.read', 'payouts.approve', 'payouts.process',
            'payouts.view_all',
            # Redemptions
            'redemptions.read', 'redemptions.approve', 'redemptions.reject', 'redemptions.process',
            # KYC
            'kyc.view_all', 'kyc.verify', 'kyc.reject',
            # Reports
            'reports.view_dashboard', 'reports.view_financial', 'reports.view_analytics',
            'reports.export',
            # Teams
            'teams.create', 'teams.read', 'teams.update', 'teams.delete', 'teams.manage_members',
        ],
        'channel_partner': [
            # Users (limited)
            'users.read',
            # Properties
            'properties.read',
            # Investments (own customers)
            'investments.read',
            # Wallet
            'wallet.view', 'wallet.view_transactions',
            # Commissions
            'commissions.view_own',
            # Channel Partners
            'channel_partners.read', 'channel_partners.view_customers',
            # KYC
            'kyc.view_own',
        ],
        'developer': [
            # Properties
            'properties.create', 'properties.read', 'properties.update',
            'properties.manage_units', 'properties.upload_documents',
            # Investments (for their properties)
            'investments.read',
            # Payouts
            'payouts.read',
            # KYC
            'kyc.view_own',
        ],
        'customer': [
            # Properties (view only)
            'properties.read',
            # Investments (own)
            'investments.create', 'investments.read', 'investments.view_own',
            # Wallet
            'wallet.view', 'wallet.deposit', 'wallet.view_transactions',
            # Redemptions
            'redemptions.create', 'redemptions.read',
            # KYC
            'kyc.submit', 'kyc.view_own',
        ],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--assign',
            action='store_true',
            help='Assign permissions to roles after seeding',
        )
        parser.add_argument(
            '--org-id',
            type=int,
            help='Assign permissions for specific organization roles',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        assign = options.get('assign')
        org_id = options.get('org_id')

        # Seed all permissions
        self.stdout.write('🌱 Seeding permissions...')
        self.seed_permissions()

        if assign:
            if org_id:
                try:
                    org = Organization.objects.get(id=org_id)
                    self.assign_permissions_to_roles(org)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Assigned permissions for {org.name}')
                    )
                except Organization.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f'❌ Organization with ID {org_id} does not exist')
                    )
            else:
                # Assign to all organization roles
                orgs = Organization.objects.filter(is_active=True)
                for org in orgs:
                    self.assign_permissions_to_roles(org)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Assigned permissions for {orgs.count()} organizations')
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    'ℹ️  Use --assign to assign permissions to roles')
            )

    def seed_permissions(self):
        """Create all permissions"""
        created_count = 0
        existing_count = 0

        for module, actions in self.PERMISSIONS.items():
            for action, name, category in actions:
                code_name = f"{module}.{action}"

                permission, created = Permission.objects.get_or_create(
                    code_name=code_name,
                    defaults={
                        'name': name,
                        'module': module,
                        'action': action,
                        'category': category,
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(f"  ✓ Created: {code_name}")
                else:
                    existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Permissions seeded: {created_count} created, {existing_count} existing'
            )
        )

    def assign_permissions_to_roles(self, organization=None):
        """Assign permissions to roles"""
        for role_name, permissions in self.ROLE_PERMISSIONS.items():
            # Get roles
            if role_name == 'superadmin':
                roles = Role.objects.filter(
                    name=role_name, organization__isnull=True)
            else:
                if organization:
                    roles = Role.objects.filter(
                        name=role_name, organization=organization)
                else:
                    roles = Role.objects.filter(name=role_name)

            for role in roles:
                # Get permissions to assign
                if permissions == 'ALL':
                    perms = Permission.objects.all()
                else:
                    perms = Permission.objects.filter(
                        code_name__in=permissions)

                # Assign permissions
                for perm in perms:
                    RolePermission.objects.get_or_create(
                        role=role,
                        permission=perm
                    )

                self.stdout.write(
                    f"  ✓ Assigned {perms.count()} permissions to {role.display_name}")
