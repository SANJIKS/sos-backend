from django.core.management.base import BaseCommand

from apps.factories.news import NewsFactory, NewsCategoryFactory, NewsTagFactory
from apps.factories.partners import PartnerFactory
from apps.factories.locations import MapPointFactory
from apps.factories.principles import PrincipleFactory
from apps.factories.programs import ProgramFactory
from apps.factories.success_stories import SuccessStoryFactory
from apps.factories.impact_results import ImpactResultFactory
from apps.factories.donation_options import DonationOptionFactory
from apps.factories.social_networks import SocialNetworkFactory
from apps.factories.timeline import TimelineEventFactory
from apps.factories.contacts import ContactCategoryFactory, ContactFactory


class Command(BaseCommand):
    help = 'Seed database with sample data (excluding users and donations)'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10, help='Count per model')

    def handle(self, *args, **options):
        count = options['count']

        self.stdout.write(self.style.MIGRATE_HEADING('Seeding data...'))

        # News
        categories = [NewsCategoryFactory() for _ in range(3)]
        tags = [NewsTagFactory() for _ in range(5)]
        for _ in range(count):
            NewsFactory(tags=tags)

        # Partners
        for _ in range(count):
            PartnerFactory()

        # Locations
        for _ in range(count):
            MapPointFactory()

        # Principles
        for _ in range(5):
            PrincipleFactory()

        # Programs
        for _ in range(6):
            ProgramFactory()

        # Success Stories
        for _ in range(6):
            SuccessStoryFactory()

        # Impact Results
        for _ in range(6):
            ImpactResultFactory()

        # Donation Options
        for _ in range(4):
            DonationOptionFactory()

        # Social Networks
        for _ in range(5):
            SocialNetworkFactory()

        # Contacts
        for _ in range(5):
            ContactFactory()

        # Timeline
        for _ in range(10):
            TimelineEventFactory()

        self.stdout.write(self.style.SUCCESS('Seeding completed successfully.'))


