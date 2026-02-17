import factory
import time
from apps.programs.models import Program


class ProgramFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Program

    title = factory.Faker('sentence')
    slug = factory.Sequence(lambda n: f'program-{n}-{int(time.time() * 1000) % 100000}')
    description = factory.Faker('paragraph')
    short_description = factory.Faker('sentence')
    program_type = Program.ProgramType.CHILDREN_VILLAGES
    is_active = True
    is_featured = False
    is_main_program = False
    order = factory.Sequence(int)


