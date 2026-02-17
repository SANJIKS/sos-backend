import factory
import time
from django.utils import timezone

from apps.news.models import News, NewsCategory, NewsTag


class NewsCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NewsCategory

    name = factory.Sequence(lambda n: f'Category {n} {int(time.time() * 1000) % 100000}')
    slug = factory.Sequence(lambda n: f'category-{n}-{int(time.time() * 1000) % 100000}')
    description = factory.Faker('sentence')
    is_active = True
    sort_order = factory.Sequence(int)


class NewsTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NewsTag

    name = factory.Sequence(lambda n: f'Tag {n} {int(time.time() * 1000) % 100000}')
    slug = factory.Sequence(lambda n: f'tag-{n}-{int(time.time() * 1000) % 100000}')


class NewsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = News

    title = factory.Faker('sentence')
    slug = factory.Sequence(lambda n: f'news-{n}-{int(time.time() * 1000) % 100000}')
    content = factory.Faker('paragraph', nb_sentences=5)
    excerpt = factory.Faker('sentence')
    category = factory.SubFactory(NewsCategoryFactory)
    status = News.Status.PUBLISHED
    published_at = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def add_tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.tags.set(extracted)
        else:
            # Create 2 random tags for this news
            tags = [NewsTagFactory() for _ in range(2)]
            self.tags.set(tags)


