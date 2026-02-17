import factory
import time
from apps.locations.models import MapPoint


class MapPointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MapPoint

    point_id = factory.Sequence(lambda n: f'point-{n}-{int(time.time() * 1000) % 100000}')
    name = factory.Faker('city')
    name_kg = ''
    name_en = ''
    description = factory.Faker('sentence')
    description_kg = ''
    description_en = ''
    image = factory.django.ImageField(color='blue')
    x_percent = 50
    y_percent = 50


