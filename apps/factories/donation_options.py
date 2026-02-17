import factory
from apps.donation_options.models import DonationOption


class DonationOptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DonationOption

    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    option_type = DonationOption.OptionType.ONE_TIME
    status = DonationOption.Status.ACTIVE
    button_text = 'Пожертвовать'
    button_url = 'https://example.com/donate'
    is_button_enabled = True
    is_active = True
    is_featured = False
    order = factory.Sequence(int)
    min_amount = 100


