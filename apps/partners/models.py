from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.mixins import BaseModel

# Create your models here.

class Partner(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_('Название партнера'), unique=True)
    name_kg = models.CharField(max_length=255, blank=True, verbose_name=_('Название партнера (КГ)'))
    name_en = models.CharField(max_length=255, blank=True, verbose_name=_('Название партнера (EN)'))
    logo = models.ImageField(upload_to='partners/', verbose_name=_('Логотип партнера'))
    class CategoryChoices(models.TextChoices):
        CIVIL_ORGANIZATIONS = 'civil_organizations', 'Организации Гражданского Общества'
        GOVERNMENT_AGENCIES = 'government_agencies', 'Государственные органы'
        INTERNATIONAL_ORGANIZATIONS = 'international_organizations', 'Международные Организации'
        FOREIGN_GOVERNMENTS = 'foreign_governments', 'Иностранные Правительства'
        CORPORATE_DONORS = 'corporate_donors', 'Корпоративные доноры'
        OTHER_ORGANIZATIONS = 'other_organizations', 'Другие организации'
    category = models.CharField(max_length=100, choices=CategoryChoices.choices, verbose_name=_('Категория партнера'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Партнер')
        verbose_name_plural = _('Партнеры')