from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.mixins import BaseContentModel


class Principle(BaseContentModel):
    """
    Модель для ключевых принципов SOS
    """
    class PrincipleType(models.TextChoices):
        MOTHER = 'mother', _('Мама')
        SIBLINGS = 'siblings', _('Братья и Сестры')
        HOME = 'home', _('Дом')
        VILLAGE = 'village', _('Деревня')
        OTHER = 'other', _('Другое')

    subtitle = models.CharField(max_length=300, verbose_name=_('Подзаголовок'))
    principle_type = models.CharField(
        max_length=20,
        choices=PrincipleType.choices,
        verbose_name=_('Тип принципа')
    )
    
    # Изображения
    icon = models.CharField(
        max_length=50, 
        verbose_name=_('Иконка'),
        help_text=_('Название иконки для отображения')
    )
    
    # Дополнительная информация
    key_points = models.TextField(blank=True, verbose_name=_('Ключевые моменты'))
    impact = models.TextField(blank=True, verbose_name=_('Влияние'))

    class Meta:
        verbose_name = _('Принцип SOS')
        verbose_name_plural = _('Принципы SOS')
        ordering = ['order', 'principle_type']

    def __str__(self):
        return f"{self.title} - {self.subtitle}"
