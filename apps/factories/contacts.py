import factory
import time
from apps.contacts.models.contact import ContactCategory, Contact


class ContactCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContactCategory

    name = factory.Sequence(lambda n: f'Категория {n}')
    description = factory.Faker('sentence', nb_words=5)
    email_recipients = 'support@sos-kg.org'
    sort_order = factory.Sequence(int)


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact

    category = factory.SubFactory(ContactCategoryFactory)
    contact_type = 'general'  # Используем строковое значение вместо enum
    full_name = factory.Faker('name')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    subject = factory.Faker('sentence', nb_words=3)
    message = factory.Faker('paragraph', nb_sentences=2)
    status = Contact.Status.NEW
    priority = Contact.Priority.NORMAL
    consent_data_processing = True


