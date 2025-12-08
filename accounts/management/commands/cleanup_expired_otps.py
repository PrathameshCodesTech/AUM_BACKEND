# accounts/management/commands/cleanup_expired_otps.py
from django.core.management.base import BaseCommand
from accounts.models import OTPVerification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup expired and old OTP verification records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete verified OTPs older than this many hours (default: 24)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No records will be deleted'))
        
        self.stdout.write(f'Cleaning up OTP records older than {hours} hours...')
        
        if dry_run:
            # Count what would be deleted
            from django.utils import timezone
            from datetime import timedelta
            
            verified_threshold = timezone.now() - timedelta(hours=hours)
            verified_count = OTPVerification.objects.filter(
                is_verified=True,
                verified_at__lt=verified_threshold
            ).count()
            
            expired_threshold = timezone.now() - timedelta(hours=1)
            expired_count = OTPVerification.objects.filter(
                is_verified=False,
                expires_at__lt=expired_threshold
            ).count()
            
            self.stdout.write(f'Would delete {verified_count} verified OTPs')
            self.stdout.write(f'Would delete {expired_count} expired OTPs')
            
        else:
            # Actually delete
            result = OTPVerification.cleanup_old_otps(hours=hours)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Deleted {result["verified_deleted"]} verified OTPs'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Deleted {result["expired_deleted"]} expired OTPs'
                )
            )
            
            logger.info(f'OTP cleanup completed: {result}')
        
        self.stdout.write(self.style.SUCCESS('Done!'))