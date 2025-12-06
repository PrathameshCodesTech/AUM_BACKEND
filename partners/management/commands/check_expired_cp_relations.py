# partners/management/commands/check_expired_cp_relations.py
from django.core.management.base import BaseCommand
from partners.services.cp_service import CPService


class Command(BaseCommand):
    help = 'Check and update expired CP-customer relationships'

    def handle(self, *args, **kwargs):
        expired_count = CPService.check_expired_relationships()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully checked relationships. {expired_count} expired.'
            )
        )