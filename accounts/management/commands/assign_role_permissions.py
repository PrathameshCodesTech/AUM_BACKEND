from django.core.management.base import BaseCommand
from accounts.models import Role, Permission, RolePermission, User


class Command(BaseCommand):
    help = 'Assign permissions to roles'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔗 Assigning permissions to roles...")

        # Admin - Gets ALL permissions
        admin_role = Role.objects.get(slug='admin')
        admin_perms = Permission.objects.all()
        
        for perm in admin_perms:
            RolePermission.objects.get_or_create(
                role=admin_role,
                permission=perm
            )
        
        self.stdout.write(self.style.SUCCESS(f"✅ Admin: {admin_perms.count()} permissions"))

        # Developer - Property management
        dev_role = Role.objects.get(slug='developer')
        dev_perm_codes = [
            'properties.view', 'properties.create', 'properties.update',
            'properties.manage_documents',
            'users.view',
            'investments.view',
        ]
        
        dev_count = 0
        for code in dev_perm_codes:
            try:
                perm = Permission.objects.get(code_name=code)
                RolePermission.objects.get_or_create(role=dev_role, permission=perm)
                dev_count += 1
            except Permission.DoesNotExist:
                pass
        
        self.stdout.write(self.style.SUCCESS(f"✅ Developer: {dev_count} permissions"))

        # Channel Partner - View properties, commissions
        cp_role = Role.objects.get(slug='channel_partner')
        cp_perm_codes = [
            'properties.view',
            'investments.view',
            'commissions.view',
            'channel_partners.view',
            'users.view',
        ]
        
        cp_count = 0
        for code in cp_perm_codes:
            try:
                perm = Permission.objects.get(code_name=code)
                RolePermission.objects.get_or_create(role=cp_role, permission=perm)
                cp_count += 1
            except Permission.DoesNotExist:
                pass
        
        self.stdout.write(self.style.SUCCESS(f"✅ Channel Partner: {cp_count} permissions"))

        # Customer - Basic investment permissions
        customer_role = Role.objects.get(slug='customer')
        customer_perm_codes = [
            'properties.view',
            'investments.view',
            'investments.create',
            'wallet.view',
            'wallet.add_funds',
            'transactions.view',
            'redemptions.view',
            'redemptions.create',
        ]
        
        customer_count = 0
        for code in customer_perm_codes:
            try:
                perm = Permission.objects.get(code_name=code)
                RolePermission.objects.get_or_create(role=customer_role, permission=perm)
                customer_count += 1
            except Permission.DoesNotExist:
                pass
        
        self.stdout.write(self.style.SUCCESS(f"✅ Customer: {customer_count} permissions"))

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("✅ All permissions assigned successfully!"))
        self.stdout.write("="*50 + "\n")