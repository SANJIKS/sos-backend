from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()

class Donor(models.Model):
    class PreferredLanguage(models.TextChoices):
        RU = 'ru', 'Russian'
        EN = 'en', 'English'
        KY = 'ky', 'Kyrgyz'

    class GenderChoices(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'
        PREFER_NOT_TO_SAY = 'P', 'Prefer not to say'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donors')
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20)
    gender = models.CharField(max_length=1, choices=GenderChoices.choices)
    birth_date = models.DateField()
    preferred_language = models.CharField(choices=PreferredLanguage.choices, max_length=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.full_name

