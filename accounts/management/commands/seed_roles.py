# accounts/management/commands/seed_roles.py
from django.core.management.base import BaseCommand
from accounts.models import Role


class Command(BaseCommand):
    help = 'Seed global roles for AssetKart'

    def handle(self, *args, **kwargs):
        self.stdout.write("🌱 Seeding Global Roles...")

        roles_data = [
            {
                'name': 'admin',
                'slug': 'admin',
                'display_name': 'Admin',
                'description': 'Full system access - can manage everything',
                'level': 90,
                'is_system': True,
                'color': '#007bff',
            },
            {
                'name': 'developer',
                'slug': 'developer',
                'display_name': 'Developer',
                'description': 'Creates and manages properties',
                'level': 60,
                'is_system': True,
                'color': '#ffc107',
            },
            {
                'name': 'channel_partner',
                'slug': 'channel_partner',
                'display_name': 'Channel Partner',
                'description': 'Brings customers and earns commissions',
                'level': 50,
                'is_system': True,
                'color': '#28a745',
            },
            {
                'name': 'customer',
                'slug': 'customer',
                'display_name': 'Customer',
                'description': 'End investor who purchases properties',
                'level': 10,
                'is_system': True,
                'color': '#6c757d',
            },
        ]

        created_count = 0
        updated_count = 0

        for role_data in roles_data:
            role, created = Role.objects.update_or_create(
                slug=role_data['slug'],
                defaults=role_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Created role: {role.display_name}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Updated role: {role.display_name}")
                )

        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )
        self.stdout.write("="*50 + "\n")

        # Display role hierarchy
        self.stdout.write("\n📊 Role Hierarchy:")
        roles = Role.objects.all().order_by('-level')
        for role in roles:
            self.stdout.write(
                f"  [{role.level:3d}] {role.display_name:20s} ({role.slug})"
            )