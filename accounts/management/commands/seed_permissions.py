# accounts/management/commands/seed_permissions.py
from django.core.management.base import BaseCommand
from accounts.models import Permission


class Command(BaseCommand):
    help = 'Seed permissions for AssetKart'

    def handle(self, *args, **kwargs):
        self.stdout.write("🌱 Seeding Permissions...")

        permissions_data = [
            # User Management
            {'code_name': 'users.view', 'name': 'View Users', 'module': 'users', 'action': 'view', 'category': 'User Management'},
            {'code_name': 'users.create', 'name': 'Create Users', 'module': 'users', 'action': 'create', 'category': 'User Management'},
            {'code_name': 'users.update', 'name': 'Update Users', 'module': 'users', 'action': 'update', 'category': 'User Management'},
            {'code_name': 'users.delete', 'name': 'Delete Users', 'module': 'users', 'action': 'delete', 'category': 'User Management'},
            {'code_name': 'users.manage_roles', 'name': 'Manage User Roles', 'module': 'users', 'action': 'manage_roles', 'category': 'User Management'},
            {'code_name': 'users.approve_kyc', 'name': 'Approve KYC', 'module': 'users', 'action': 'approve_kyc', 'category': 'User Management'},

            # Role & Permission Management
            {'code_name': 'roles.view', 'name': 'View Roles', 'module': 'roles', 'action': 'view', 'category': 'Access Control'},
            {'code_name': 'roles.create', 'name': 'Create Roles', 'module': 'roles', 'action': 'create', 'category': 'Access Control'},
            {'code_name': 'roles.update', 'name': 'Update Roles', 'module': 'roles', 'action': 'update', 'category': 'Access Control'},
            {'code_name': 'roles.delete', 'name': 'Delete Roles', 'module': 'roles', 'action': 'delete', 'category': 'Access Control'},
            {'code_name': 'permissions.manage', 'name': 'Manage Permissions', 'module': 'permissions', 'action': 'manage', 'category': 'Access Control'},

            # Property Management
            {'code_name': 'properties.view', 'name': 'View Properties', 'module': 'properties', 'action': 'view', 'category': 'Property Management'},
            {'code_name': 'properties.create', 'name': 'Create Properties', 'module': 'properties', 'action': 'create', 'category': 'Property Management'},
            {'code_name': 'properties.update', 'name': 'Update Properties', 'module': 'properties', 'action': 'update', 'category': 'Property Management'},
            {'code_name': 'properties.delete', 'name': 'Delete Properties', 'module': 'properties', 'action': 'delete', 'category': 'Property Management'},
            {'code_name': 'properties.approve', 'name': 'Approve Properties', 'module': 'properties', 'action': 'approve', 'category': 'Property Management'},
            {'code_name': 'properties.publish', 'name': 'Publish Properties', 'module': 'properties', 'action': 'publish', 'category': 'Property Management'},
            {'code_name': 'properties.manage_documents', 'name': 'Manage Property Documents', 'module': 'properties', 'action': 'manage_documents', 'category': 'Property Management'},

            # Investment Management
            {'code_name': 'investments.view', 'name': 'View Investments', 'module': 'investments', 'action': 'view', 'category': 'Investment Management'},
            {'code_name': 'investments.create', 'name': 'Create Investments', 'module': 'investments', 'action': 'create', 'category': 'Investment Management'},
            {'code_name': 'investments.approve', 'name': 'Approve Investments', 'module': 'investments', 'action': 'approve', 'category': 'Investment Management'},
            {'code_name': 'investments.cancel', 'name': 'Cancel Investments', 'module': 'investments', 'action': 'cancel', 'category': 'Investment Management'},
            {'code_name': 'investments.view_all', 'name': 'View All Investments', 'module': 'investments', 'action': 'view_all', 'category': 'Investment Management'},

            # Wallet & Transactions
            {'code_name': 'wallet.view', 'name': 'View Wallet', 'module': 'wallet', 'action': 'view', 'category': 'Financial'},
            {'code_name': 'wallet.add_funds', 'name': 'Add Funds to Wallet', 'module': 'wallet', 'action': 'add_funds', 'category': 'Financial'},
            {'code_name': 'wallet.withdraw', 'name': 'Withdraw from Wallet', 'module': 'wallet', 'action': 'withdraw', 'category': 'Financial'},
            {'code_name': 'wallet.view_all', 'name': 'View All Wallets', 'module': 'wallet', 'action': 'view_all', 'category': 'Financial'},
            {'code_name': 'transactions.view', 'name': 'View Transactions', 'module': 'transactions', 'action': 'view', 'category': 'Financial'},
            {'code_name': 'transactions.view_all', 'name': 'View All Transactions', 'module': 'transactions', 'action': 'view_all', 'category': 'Financial'},

            # Commission Management
            {'code_name': 'commissions.view', 'name': 'View Commissions', 'module': 'commissions', 'action': 'view', 'category': 'Commission Management'},
            {'code_name': 'commissions.calculate', 'name': 'Calculate Commissions', 'module': 'commissions', 'action': 'calculate', 'category': 'Commission Management'},
            {'code_name': 'commissions.approve', 'name': 'Approve Commissions', 'module': 'commissions', 'action': 'approve', 'category': 'Commission Management'},
            {'code_name': 'commissions.payout', 'name': 'Process Commission Payouts', 'module': 'commissions', 'action': 'payout', 'category': 'Commission Management'},
            {'code_name': 'commissions.view_all', 'name': 'View All Commissions', 'module': 'commissions', 'action': 'view_all', 'category': 'Commission Management'},

            # Channel Partner Management
            {'code_name': 'channel_partners.view', 'name': 'View Channel Partners', 'module': 'channel_partners', 'action': 'view', 'category': 'Partner Management'},
            {'code_name': 'channel_partners.create', 'name': 'Create Channel Partners', 'module': 'channel_partners', 'action': 'create', 'category': 'Partner Management'},
            {'code_name': 'channel_partners.update', 'name': 'Update Channel Partners', 'module': 'channel_partners', 'action': 'update', 'category': 'Partner Management'},
            {'code_name': 'channel_partners.approve', 'name': 'Approve Channel Partners', 'module': 'channel_partners', 'action': 'approve', 'category': 'Partner Management'},
            {'code_name': 'channel_partners.set_hierarchy', 'name': 'Set CP Hierarchy', 'module': 'channel_partners', 'action': 'set_hierarchy', 'category': 'Partner Management'},

            # Reports & Analytics
            {'code_name': 'reports.view', 'name': 'View Reports', 'module': 'reports', 'action': 'view', 'category': 'Reports & Analytics'},
            {'code_name': 'reports.export', 'name': 'Export Reports', 'module': 'reports', 'action': 'export', 'category': 'Reports & Analytics'},
            {'code_name': 'analytics.view', 'name': 'View Analytics', 'module': 'analytics', 'action': 'view', 'category': 'Reports & Analytics'},
            {'code_name': 'analytics.dashboard', 'name': 'View Analytics Dashboard', 'module': 'analytics', 'action': 'dashboard', 'category': 'Reports & Analytics'},

            # Compliance & KYC (UPDATED - No duplicates)
            {'code_name': 'compliance.view', 'name': 'View Compliance', 'module': 'compliance', 'action': 'view', 'category': 'Compliance'},
            {'code_name': 'compliance.manage', 'name': 'Manage Compliance', 'module': 'compliance', 'action': 'manage', 'category': 'Compliance'},
            {'code_name': 'compliance.view_kyc', 'name': 'View KYC Documents', 'module': 'compliance', 'action': 'view_kyc', 'category': 'Compliance'},
            {'code_name': 'compliance.approve_kyc', 'name': 'Approve/Reject KYC', 'module': 'compliance', 'action': 'approve_kyc', 'category': 'Compliance'},

            # Redemption Management
            {'code_name': 'redemptions.view', 'name': 'View Redemptions', 'module': 'redemptions', 'action': 'view', 'category': 'Redemption Management'},
            {'code_name': 'redemptions.create', 'name': 'Create Redemption Requests', 'module': 'redemptions', 'action': 'create', 'category': 'Redemption Management'},
            {'code_name': 'redemptions.approve', 'name': 'Approve Redemptions', 'module': 'redemptions', 'action': 'approve', 'category': 'Redemption Management'},
            {'code_name': 'redemptions.process', 'name': 'Process Redemptions', 'module': 'redemptions', 'action': 'process', 'category': 'Redemption Management'},
            {'code_name': 'redemptions.view_all', 'name': 'View All Redemptions', 'module': 'redemptions', 'action': 'view_all', 'category': 'Redemption Management'},

            # System Settings
            {'code_name': 'settings.view', 'name': 'View Settings', 'module': 'settings', 'action': 'view', 'category': 'System'},
            {'code_name': 'settings.update', 'name': 'Update Settings', 'module': 'settings', 'action': 'update', 'category': 'System'},
            {'code_name': 'system.manage', 'name': 'Manage System', 'module': 'system', 'action': 'manage', 'category': 'System'},
        ]

        created_count = 0
        updated_count = 0

        for perm_data in permissions_data:
            perm, created = Permission.objects.update_or_create(
                code_name=perm_data['code_name'],
                defaults=perm_data
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )
        self.stdout.write(f"📊 Total permissions: {Permission.objects.count()}")
        self.stdout.write("="*50 + "\n")

        # Display permissions by category
        self.stdout.write("\n📋 Permissions by Category:")
        categories = Permission.objects.values_list('category', flat=True).distinct()
        for category in sorted(categories):
            count = Permission.objects.filter(category=category).count()
            self.stdout.write(f"  {category}: {count} permissions")