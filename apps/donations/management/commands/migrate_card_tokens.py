from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.donations.models import Donation, DonationTransaction


class Command(BaseCommand):
    help = 'Migrate existing card tokens from gateway_response to current_card_token field'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Находим рекуррентные пожертвования без токена карты
        recurring_donations = Donation.objects.filter(
            is_recurring=True,
            current_card_token__isnull=True
        ).exclude(current_card_token='')
        
        migrated_count = 0
        errors_count = 0
        
        self.stdout.write(f"Found {recurring_donations.count()} recurring donations without card tokens")
        
        for donation in recurring_donations:
            try:
                # Ищем успешную транзакцию с токеном карты
                initial_transaction = donation.transactions.filter(
                    status='success',
                    transaction_type='payment'
                ).first()
                
                if initial_transaction and initial_transaction.gateway_response:
                    card_token = initial_transaction.gateway_response.get('card_token')
                    
                    if card_token:
                        if not dry_run:
                            donation.current_card_token = card_token
                            donation.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Migrated card token for donation {donation.donation_code}: {card_token}"
                            )
                        )
                        migrated_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠ No card token found in gateway_response for donation {donation.donation_code}"
                            )
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ No successful transaction found for donation {donation.donation_code}"
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Error processing donation {donation.donation_code}: {e}"
                    )
                )
                errors_count += 1
        
        # Статистика
        self.stdout.write("\n" + "="*50)
        self.stdout.write("MIGRATION SUMMARY")
        self.stdout.write("="*50)
        
        if dry_run:
            self.stdout.write(f"Would migrate: {migrated_count} donations")
        else:
            self.stdout.write(f"Successfully migrated: {migrated_count} donations")
        
        self.stdout.write(f"Errors: {errors_count}")
        
        if not dry_run and migrated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Successfully migrated {migrated_count} card tokens!"
                )
            )
        elif dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n🔍 Dry run completed. Run without --dry-run to apply changes."
                )
            )
