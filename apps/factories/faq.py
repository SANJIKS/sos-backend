import factory
from apps.faq.models import FAQ


class FAQFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FAQ

    question = factory.Faker('sentence')
    answer = factory.Faker('paragraph')
    is_published = True
    order = factory.Sequence(int)


