import factory
import time
from apps.partners.models import Partner


class NGOPartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Partner

    name = factory.Sequence(lambda n: f'NGO Partner {n} {int(time.time() * 1000) % 100000}')
    category = Partner.CategoryChoices.ngo


class GovtPartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Partner

    name = factory.Sequence(lambda n: f'Gov Partner {n} {int(time.time() * 1000) % 100000}')
    category = Partner.CategoryChoices.government


