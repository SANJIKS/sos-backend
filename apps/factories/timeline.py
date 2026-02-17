import factory
from apps.timeline.models import TimelineEvent


class TimelineEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TimelineEvent

    year = factory.Sequence(lambda n: f"{1990 + (n % 30)}")
    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    event_type = TimelineEvent.EventType.OTHER
    is_active = True
    is_featured = False
    order = factory.Sequence(int)
    location = factory.Faker('city')
    participants = factory.Faker('name')
    impact = factory.Faker('sentence')


