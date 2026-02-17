import factory
import time
from apps.social_networks.models import SocialNetwork


class SocialNetworkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SocialNetwork

    name = factory.Sequence(lambda n: f'Network {n} {int(time.time() * 1000) % 100000}')
    network_type = SocialNetwork.NetworkType.TELEGRAM
    url = factory.Sequence(lambda n: f'https://t.me/channel{n}{int(time.time() * 1000) % 100000}')
    is_active = True
    is_featured = False
    is_verified = False
    order = factory.Sequence(int)
    followers_count = factory.Faker('random_int', min=100, max=100000)


