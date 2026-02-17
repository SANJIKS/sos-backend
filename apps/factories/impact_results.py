import factory
from apps.impact_results.models import ImpactResult


class ImpactResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ImpactResult

    title = factory.Faker('sentence')
    percentage_value = factory.Faker('pyfloat', positive=True, right_digits=2, min_value=1, max_value=100)
    description = factory.Faker('sentence')
    result_type = ImpactResult.ResultType.OTHER
    is_active = True
    is_featured = False
    order = factory.Sequence(int)
    year = 2024
    source = factory.Faker('company')


