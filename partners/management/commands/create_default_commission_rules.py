# partners/management/commands/create_default_commission_rules.py
from django.core.management.base import BaseCommand
from partners.models import CommissionRule
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create default commission rules'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        
        # Default flat commission rule
        rule, created = CommissionRule.objects.get_or_create(
            name='Default 2% Commission',
            defaults={
                'commission_type': 'flat',
                'percentage': 2.00,
                'is_active': True,
                'is_default': True,
                'override_percentage': 0.5,  # 0.5% for parent CP
                'description': 'Default 2% flat commission on all investments',
                'effective_from': today,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Created default commission rule (ID: {rule.id})'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️ Default rule already exists (ID: {rule.id})'))
        
        # Tiered commission rule
        tiered_rule, created = CommissionRule.objects.get_or_create(
            name='Tiered Commission (1-3%)',
            defaults={
                'commission_type': 'tiered',
                'percentage': 2.00,  # Default/fallback percentage
                'tiers': [
                    {'min': 0, 'max': 500000, 'rate': 1.0},           # 1% for ≤5L
                    {'min': 500001, 'max': 1000000, 'rate': 2.0},     # 2% for 5-10L
                    {'min': 1000001, 'max': 999999999, 'rate': 3.0}   # 3% for >10L
                ],
                'is_active': True,
                'override_percentage': 0.5,
                'description': 'Tiered commission: 1% (≤5L), 2% (5-10L), 3% (>10L)',
                'effective_from': today,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Created tiered commission rule (ID: {tiered_rule.id})'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️ Tiered rule already exists (ID: {tiered_rule.id})'))
        
        # High-value commission rule
        high_value_rule, created = CommissionRule.objects.get_or_create(
            name='High Value 3% Commission',
            defaults={
                'commission_type': 'flat',
                'percentage': 3.00,
                'is_active': True,
                'override_percentage': 1.0,  # 1% for parent CP
                'description': 'Premium 3% commission for high-value transactions',
                'effective_from': today,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Created high-value commission rule (ID: {high_value_rule.id})'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️ High-value rule already exists (ID: {high_value_rule.id})'))
        
        # Summary
        total_rules = CommissionRule.objects.count()
        active_rules = CommissionRule.objects.filter(is_active=True).count()
        
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS(f'✅ Commission Rules Setup Complete'))
        self.stdout.write(self.style.SUCCESS(f'   Total Rules: {total_rules}'))
        self.stdout.write(self.style.SUCCESS(f'   Active Rules: {active_rules}'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        
        # Display created rules
        self.stdout.write(self.style.SUCCESS('\n📋 Commission Rules:'))
        for rule in CommissionRule.objects.filter(is_active=True):
            self.stdout.write(self.style.SUCCESS(f'   • {rule.name} ({rule.percentage}%)'))