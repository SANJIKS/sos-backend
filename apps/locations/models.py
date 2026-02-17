from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.mixins import LocalizedFieldsMixin


class MapPoint(LocalizedFieldsMixin, models.Model):
    """Точки на стилизованной карте Кыргызстана"""
    
    # Уникальный идентификатор
    point_id = models.CharField(max_length=50, unique=True, verbose_name=_('ID точки'))
    
    # Название
    name = models.CharField(max_length=200, verbose_name=_('Название'))
    name_kg = models.CharField(max_length=200, blank=True, verbose_name=_('Название (КГ)'))
    name_en = models.CharField(max_length=200, blank=True, verbose_name=_('Название (EN)'))
    
    # Описание для всплывающего окна
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    description_kg = models.TextField(blank=True, verbose_name=_('Описание (КГ)'))
    description_en = models.TextField(blank=True, verbose_name=_('Описание (EN)'))
    
    # URL изображения для всплывающего окна
    image = models.ImageField(upload_to='location/')
    
    # Относительные координаты (в процентах от размера карты)
    x_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name=_('X координата (%)'),
        help_text=_('Позиция по X в процентах от ширины карты (0-100)')
    )
    y_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name=_('Y координата (%)'),
        help_text=_('Позиция по Y в процентах от высоты карты (0-100)')
    )
    
    # Дополнительные поля
    is_active = models.BooleanField(default=True, verbose_name=_('Активная'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Точка карты')
        verbose_name_plural = _('Точки карты')
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.point_id} - {self.name}"
