import random
from datetime import timedelta

import factory
from django.utils import timezone

from apps.users.models.user import User
from apps.users.models.confirm_code import ConfirmCode
from apps.users.models.two_factor import (
    TwoFactorAuth,
    TwoFactorCode,
    TwoFactorBackupCode,
    TwoFactorLog,
)
from apps.donors.models.donor import Donor
from apps.donors.models.f2f_coordinator import (
    F2FCoordinator,
    F2FRegion,
    F2FCoordinatorRegionAssignment,
    F2FLocation,
)
from apps.donors.models.f2f_registration import (
    F2FRegistration,
    F2FRegistrationDocument,
    F2FDailyReport,
)
from apps.contacts.models.contact import ContactCategory, Contact
from apps.partners.models import Partner
from apps.news.models.news import NewsCategory, NewsTag, News
from apps.donations.models.donation import DonationCampaign, Donation, DonationTransaction
from apps.donations.models.card_history import DonorCardHistory


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda o: f"{o.full_name.lower().replace(' ', '.')}@example.com")
    full_name = factory.Faker('name')
    phone = factory.Faker('phone_number')
    user_type = User.UserType.DONOR
    is_active = True
    consent_data_processing = True

    @factory.post_generation
    def set_password(self, create, extracted, **kwargs):
        pwd = extracted or 'password123!'
        self.set_password(pwd)
        if create:
            self.save()


class ConfirmCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ConfirmCode

    user = factory.SubFactory(UserFactory)
    code = factory.Faker('bothify', text='######')
    type = ConfirmCode.ConfirmCodeType.EMAIL
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=2))
    is_used = False


class DonorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Donor

    user = factory.SubFactory(UserFactory)
    full_name = factory.Faker('name')
    email = factory.LazyAttribute(lambda o: f"{o.full_name.lower().replace(' ', '.')}@donor.com")
    phone = factory.Faker('phone_number')
    gender = Donor.GenderChoices.MALE
    birth_date = factory.Faker('date_of_birth', minimum_age=18, maximum_age=75)
    preferred_language = Donor.PreferredLanguage.RU


class TwoFactorAuthFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TwoFactorAuth

    user = factory.SubFactory(UserFactory)
    auth_method = TwoFactorAuth.AuthMethod.EMAIL
    status = TwoFactorAuth.Status.ENABLED
    is_required = False


class TwoFactorCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TwoFactorCode

    two_factor_auth = factory.SubFactory(TwoFactorAuthFactory)
    code_type = TwoFactorCode.CodeType.EMAIL
    encrypted_code = factory.Faker('password')
    code_hash = factory.Faker('md5')
    status = TwoFactorCode.Status.PENDING
    max_attempts = 5
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=5))


class TwoFactorBackupCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TwoFactorBackupCode

    two_factor_auth = factory.SubFactory(TwoFactorAuthFactory)
    code_hash = factory.Faker('md5')
    is_used = False


class TwoFactorLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TwoFactorLog

    two_factor_auth = factory.SubFactory(TwoFactorAuthFactory)
    log_type = TwoFactorLog.LogType.CODE_SENT
    status = TwoFactorLog.Status.SUCCESS
    description = factory.Faker('sentence')


class ContactCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContactCategory

    name = factory.Sequence(lambda n: f'Категория {n}')
    description = factory.Faker('sentence')
    email_recipients = 'support@sos-kg.org'
    sort_order = factory.Sequence(int)


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    category = factory.SubFactory(ContactCategoryFactory)
    contact_type = Contact.ContactType.GENERAL
    full_name = factory.Faker('name')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    subject = factory.Faker('sentence')
    message = factory.Faker('paragraph')
    status = Contact.Status.NEW
    priority = Contact.Priority.NORMAL
    consent_data_processing = True


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Partner

    name = factory.Sequence(lambda n: f'Partner {n}')
    category = Partner.CategoryChoices.other_organizations


class NewsCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NewsCategory

    name = factory.Sequence(lambda n: f'Category {n}')
    slug = factory.Sequence(lambda n: f'category-{n}')
    is_active = True
    sort_order = factory.Sequence(int)


class NewsTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NewsTag

    name = factory.Sequence(lambda n: f'Tag {n}')
    slug = factory.Sequence(lambda n: f'tag-{n}')


class NewsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = News

    title = factory.Faker('sentence')
    slug = factory.Sequence(lambda n: f'news-{n}')
    content = factory.Faker('paragraph', nb_sentences=5)
    excerpt = factory.Faker('sentence')
    category = factory.SubFactory(NewsCategoryFactory)
    status = News.Status.PUBLISHED
    published_at = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def add_tags(self, create, extracted, **kwargs):
        if not create:
            return
        tags = extracted or [NewsTagFactory() for _ in range(2)]
        for tag in tags:
            self.tags.add(tag)


class DonationCampaignFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DonationCampaign

    name = factory.Sequence(lambda n: f'Campaign {n}')
    slug = factory.Sequence(lambda n: f'campaign-{n}')
    description = factory.Faker('paragraph')
    goal_amount = 100000
    status = DonationCampaign.CampaignStatus.ACTIVE
    start_date = factory.LazyFunction(timezone.now)


class DonationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Donation

    campaign = factory.SubFactory(DonationCampaignFactory)
    donor_email = factory.Faker('email')
    donor_full_name = factory.Faker('name')
    amount = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    currency = Donation.Currency.KGS
    donation_type = Donation.DonationType.ONE_TIME
    payment_method = Donation.PaymentMethod.BANK_CARD
    status = Donation.DonationStatus.COMPLETED
    is_recurring = False


class DonationTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DonationTransaction

    donation = factory.SubFactory(DonationFactory)
    transaction_id = factory.Sequence(lambda n: f'TXN{n:06d}')
    amount = factory.SelfAttribute('donation.amount')
    currency = factory.SelfAttribute('donation.currency')
    status = DonationTransaction.TransactionStatus.SUCCESS
    transaction_type = DonationTransaction.TransactionType.PAYMENT
    payment_gateway = 'mock_gateway'


class DonorCardHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DonorCardHistory

    donation = factory.SubFactory(DonationFactory)
    old_card_token = ''
    new_card_token = factory.Faker('uuid4')
    change_type = DonorCardHistory.ChangeType.CARD_ADDED
    change_reason = factory.Faker('sentence')


class F2FRegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = F2FRegion

    name = factory.Sequence(lambda n: f'Region {n}')
    code = factory.Sequence(lambda n: f'R{n:02d}')
    is_active = True


class F2FCoordinatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = F2FCoordinator

    user = factory.SubFactory(UserFactory)
    employee_id = factory.Sequence(lambda n: f'EMP{n:04d}')
    full_name = factory.Faker('name')
    phone = factory.Faker('phone_number')
    email = factory.Faker('email')
    birth_date = factory.Faker('date_of_birth', minimum_age=20, maximum_age=60)
    status = F2FCoordinator.Status.ACTIVE
    experience_level = F2FCoordinator.ExperienceLevel.JUNIOR
    hire_date = factory.Faker('date_this_decade')

    @factory.post_generation
    def assign_regions(self, create, extracted, **kwargs):
        if not create:
            return
        regions = extracted or [F2FRegionFactory()]
        for region in regions:
            F2FCoordinatorRegionAssignment.objects.create(
                coordinator=self,
                region=region,
                assigned_date=timezone.now().date(),
                is_primary=True,
            )


class F2FLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = F2FLocation

    name = factory.Sequence(lambda n: f'Location {n}')
    location_type = F2FLocation.LocationType.MALL
    region = factory.SubFactory(F2FRegionFactory)
    address = factory.Faker('address')
    latitude = 42.8746
    longitude = 74.6122
    status = F2FLocation.Status.ACTIVE
    working_hours_start = '09:00'
    working_hours_end = '18:00'


class F2FRegistrationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = F2FRegistration

    coordinator = factory.SubFactory(F2FCoordinatorFactory)
    location = factory.SubFactory(F2FLocationFactory)
    full_name = factory.Faker('name')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    birth_date = factory.Faker('date_of_birth', minimum_age=18, maximum_age=75)
    gender = F2FRegistration.Gender.MALE
    preferred_language = F2FRegistration.PreferredLanguage.RU
    city = factory.Faker('city')
    address = factory.Faker('street_address')
    donation_amount = 500
    donation_type = F2FRegistration.DonationType.MONTHLY
    payment_method = F2FRegistration.PaymentMethod.CARD
    consent_data_processing = True
    registered_at = factory.LazyFunction(timezone.now)


class F2FRegistrationDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = F2FRegistrationDocument

    registration = factory.SubFactory(F2FRegistrationFactory)
    document_type = F2FRegistrationDocument.DocumentType.CONSENT_FORM
    file = factory.django.FileField(filename='doc.pdf')
    file_name = 'doc.pdf'
    file_size = 1024
    content_type = 'application/pdf'


class F2FDailyReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = F2FDailyReport

    coordinator = factory.SubFactory(F2FCoordinatorFactory)
    location = factory.SubFactory(F2FLocationFactory)
    report_date = factory.LazyFunction(lambda: timezone.now().date())
    total_approaches = 30
    successful_registrations = 10
    rejected_approaches = 5
    start_time = '10:00'
    end_time = '18:00'


