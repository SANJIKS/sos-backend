from django.db import models
from django.utils.translation import gettext_lazy as _


class Office(models.Model):
    """
    Модель для контактной информации офисов и детских деревень
    """
    class OfficeType(models.TextChoices):
        MAIN_OFFICE = 'main_office', _('Главный офис')
        COORDINATION_OFFICE = 'coordination_office', _('Координационный офис')
        CHILDREN_VILLAGE = 'children_village', _('Детская деревня')
        EDUCATIONAL_COMPLEX = 'educational_complex', _('Учебно-воспитательный комплекс')
        OTHER = 'other', _('Другое')

    name = models.CharField(max_length=255, verbose_name=_('Название'))
    office_type = models.CharField(
        max_length=30,
        choices=OfficeType.choices,
        default=OfficeType.OTHER,
        verbose_name=_('Тип офиса')
    )
    address = models.CharField(max_length=500, verbose_name=_('Адрес'))
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Телефон'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    working_hours = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Время работы'))
    
    # Дополнительная информация
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    is_main_office = models.BooleanField(default=False, verbose_name=_('Главный офис'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активный'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок отображения'))
    
    # Координаты для карты (если нужно)
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True, 
        verbose_name=_('Широта')
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True, 
        verbose_name=_('Долгота')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))

    class Meta:
        verbose_name = _('Офис/Локация')
        verbose_name_plural = _('Офисы/Локации')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
