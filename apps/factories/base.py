import factory
from django.utils import timezone


class TimestampedFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


