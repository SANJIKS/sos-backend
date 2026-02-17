import factory
import time
from apps.success_stories.models import SuccessStory


class SuccessStoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SuccessStory

    title = factory.Faker('sentence')
    slug = factory.Sequence(lambda n: f'story-{n}-{int(time.time() * 1000) % 100000}')
    description = factory.Faker('paragraph')
    quote_text = factory.Faker('sentence')
    author_name = factory.Faker('name')
    author_position = factory.Faker('job')
    is_active = True
    is_featured = False
    order = factory.Sequence(int)


