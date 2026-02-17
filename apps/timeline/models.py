from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.mixins import BaseModel


class TimelineEvent(BaseModel):
    """
    Модель для ключевых событий временной шкалы
    """
    class EventType(models.TextChoices):
        FOUNDATION = 'foundation', _('Основание')
        OPENING = 'opening', _('Открытие')
        LAUNCH = 'launch', _('Запуск')
        ANNIVERSARY = 'anniversary', _('Юбилей')
        PROGRAM = 'program', _('Программа')
        EXPANSION = 'expansion', _('Расширение')
        OTHER = 'other', _('Другое')

    year = models.CharField(max_length=20, verbose_name=_('Год'))
    title = models.CharField(max_length=200, verbose_name=_('Название события'))
    description = models.TextField(verbose_name=_('Описание события'))
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.OTHER,
        verbose_name=_('Тип события')
    )
    
    # Изображения
    image = models.ImageField(
        upload_to='timeline/', 
        blank=True, 
        null=True, 
        verbose_name=_('Изображение')
    )
    icon = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name=_('Иконка'),
        help_text=_('Название иконки для отображения')
    )
    
    # Управление отображением
    is_active = models.BooleanField(default=True, verbose_name=_('Активно'))
    is_featured = models.BooleanField(default=False, verbose_name=_('Рекомендуемое'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок отображения'))
    
    # Дополнительная информация
    location = models.CharField(max_length=100, blank=True, verbose_name=_('Место'))
    participants = models.CharField(max_length=200, blank=True, verbose_name=_('Участники'))
    impact = models.TextField(blank=True, verbose_name=_('Влияние/Результат'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))

    class Meta:
        verbose_name = _('Событие временной шкалы')
        verbose_name_plural = _('События временной шкалы')
        ordering = ['order', 'year']

    def __str__(self):
        return f"{self.year} - {self.title}"
