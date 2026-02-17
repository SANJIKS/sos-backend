import factory
import time
from apps.partners.models import Partner


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Partner

    name = factory.Sequence(lambda n: f'Partner {n} {int(time.time() * 1000) % 100000}')
    category = Partner.CategoryChoices.other_organizations


