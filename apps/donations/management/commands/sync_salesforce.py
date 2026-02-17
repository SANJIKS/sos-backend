from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import logging

from apps.donations.models import Donation, DonationCampaign
from apps.donations.services.salesforce import SalesforceService, SalesforceException
from apps.donations.tasks import (
    sync_donation_to_salesforce,
    sync_campaign_to_salesforce,
    bulk_sync_donations_to_salesforce,
    bulk_sync_campaigns_to_salesforce
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Synchronize donations and campaigns with Salesforce'

    def add_arguments(self, parser):
        parser.add_argument(
            '--donations',
            action='store_true',
            help='Sync only donations',
        )
        parser.add_argument(
            '--campaigns',
            action='store_true',
            help='Sync only campaigns',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync both donations and campaigns',
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test Salesforce connection',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even already synced items',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Limit number of items to sync (default: 50)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Sync items from last N days (default: 7)',
        )

    def handle(self, *args, **options):
        
        if options['test_connection']:
            self.test_salesforce_connection()
            return

        if not any([options['donations'], options['campaigns'], options['all']]):
            raise CommandError('Please specify --donations, --campaigns, or --all')

        if options['all'] or options['donations']:
            self.sync_donations(
                force=options['force'],
                limit=options['limit'],
                days=options['days']
            )

        if options['all'] or options['campaigns']:
            self.sync_campaigns(
                force=options['force'],
                limit=options['limit'],
                days=options['days']
            )

    def test_salesforce_connection(self):
        """Тестирование подключения к Salesforce"""
        self.stdout.write('Testing Salesforce connection...')
        
        try:
            sf_service = SalesforceService()
            
            if sf_service.mock_mode:
                self.stdout.write(
                    self.style.WARNING('Salesforce is in MOCK mode - no real connection test performed')
                )
                return
            
            # Попробуем получить клиента
            client = sf_service._get_client()
            
            if client:
                # Простой запрос для проверки подключения
                result = client.query("SELECT Id FROM Account LIMIT 1")
                self.stdout.write(
                    self.style.SUCCESS('✓ Salesforce connection successful!')
                )
                self.stdout.write(f'Instance URL: {client.sf_instance}')
                self.stdout.write(f'Session ID: {client.session_id[:20]}...')
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Failed to establish Salesforce connection')
                )
                
        except SalesforceException as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Salesforce connection failed: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Unexpected error: {e}')
            )

    def sync_donations(self, force=False, limit=50, days=7):
        """Синхронизация пожертвований"""
        self.stdout.write('Syncing donations with Salesforce...')
        
        # Определяем фильтры
        filters = {}
        if not force:
            filters['salesforce_synced'] = False
        
        # Фильтр по дате
        since_date = timezone.now() - timedelta(days=days)
        filters['created_at__gte'] = since_date
        
        # Фильтр по статусу
        filters['status__in'] = ['completed', 'processing']
        
        donations = Donation.objects.filter(**filters)[:limit]
        
        if not donations.exists():
            self.stdout.write(
                self.style.WARNING('No donations found for sync')
            )
            return
        
        self.stdout.write(f'Found {donations.count()} donations to sync')
        
        success_count = 0
        error_count = 0
        
        for donation in donations:
            try:
                self.stdout.write(f'Syncing donation: {donation.donation_code}')
                
                # Для команды выполняем синхронизацию напрямую, без Celery
                from apps.donations.services.salesforce import SalesforceService
                
                sf_service = SalesforceService()
                donation_data = {
                    'donation_code': donation.donation_code,
                    'donor_full_name': donation.donor_full_name,
                    'donor_email': donation.donor_email,
                    'donor_phone': donation.donor_phone,
                    'amount': donation.amount,
                    'currency': donation.currency,
                    'donation_type': donation.donation_type,
                    'payment_method': donation.payment_method,
                    'donor_comment': donation.donor_comment,
                    'status': donation.status,
                    'donor_source': donation.donor_source,
                    'created_at': donation.created_at,
                    'campaign_title': donation.campaign.name if donation.campaign else None,
                    'salesforce_campaign_id': donation.campaign.salesforce_id if donation.campaign else None,
                }
                
                result = sf_service.sync_donation_to_salesforce(donation_data)
                
                if result.get('success'):
                    donation.salesforce_id = result.get('opportunity_id')
                    donation.salesforce_synced = True
                    donation.salesforce_sync_error = ''
                    donation.save()
                    task_result = f"Donation {donation.donation_code} synced successfully"
                else:
                    task_result = f"Donation sync failed: {result.get('message', 'Unknown error')}"
                
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ {task_result}')
                )
                success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error syncing {donation.donation_code}: {e}')
                )
                error_count += 1
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Donations sync completed: {success_count} success, {error_count} errors')
        )

    def sync_campaigns(self, force=False, limit=50, days=7):
        """Синхронизация кампаний"""
        self.stdout.write('Syncing campaigns with Salesforce...')
        
        # Определяем фильтры
        filters = {}
        if not force:
            filters['salesforce_synced'] = False
        
        # Фильтр по дате
        since_date = timezone.now() - timedelta(days=days)
        filters['created_at__gte'] = since_date
        
        # Фильтр по статусу
        filters['status__in'] = ['active', 'completed']
        
        campaigns = DonationCampaign.objects.filter(**filters)[:limit]
        
        if not campaigns.exists():
            self.stdout.write(
                self.style.WARNING('No campaigns found for sync')
            )
            return
        
        self.stdout.write(f'Found {campaigns.count()} campaigns to sync')
        
        success_count = 0
        error_count = 0
        
        for campaign in campaigns:
            try:
                self.stdout.write(f'Syncing campaign: {campaign.name}')
                
                # Для команды выполняем синхронизацию напрямую, без Celery
                from apps.donations.services.salesforce import SalesforceService
                
                sf_service = SalesforceService()
                campaign_data = {
                    'title': campaign.name,
                    'description': campaign.description,
                    'target_amount': campaign.goal_amount,
                    'start_date': campaign.start_date.date().isoformat(),
                    'end_date': campaign.end_date.date().isoformat() if campaign.end_date else None,
                    'is_active': campaign.status == 'active',
                }
                
                result = sf_service.create_campaign(campaign_data)
                
                if result.get('success'):
                    campaign.salesforce_id = result.get('id')
                    campaign.salesforce_synced = True
                    campaign.salesforce_sync_error = ''
                    campaign.save()
                    task_result = f"Campaign {campaign.name} synced successfully"
                else:
                    task_result = f"Campaign sync failed: {result.get('message', 'Unknown error')}"
                
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ {task_result}')
                )
                success_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error syncing {campaign.name}: {e}')
                )
                error_count += 1
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Campaigns sync completed: {success_count} success, {error_count} errors')
        )