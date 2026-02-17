import factory
import time
from apps.principles.models import Principle


class PrincipleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Principle

    title = factory.Faker('sentence')
    slug = factory.Sequence(lambda n: f'principle-{n}-{int(time.time() * 1000) % 100000}')
    subtitle = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    principle_type = Principle.PrincipleType.MOTHER
    order = factory.Sequence(int)
    is_active = True


