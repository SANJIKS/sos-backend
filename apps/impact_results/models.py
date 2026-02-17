from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.mixins import BaseModel


class ImpactResult(BaseModel):
    """
    Модель для результатов воздействия/статистики
    """
    class ResultType(models.TextChoices):
        INTEGRATION = 'integration', _('Интеграция выпускников')
        VIOLENCE_PREVENTION = 'violence_prevention', _('Предотвращение насилия')
        EDUCATION = 'education', _('Образование')
        HEALTH = 'health', _('Здоровье')
        EMPLOYMENT = 'employment', _('Трудоустройство')
        FAMILY_REUNIFICATION = 'family_reunification', _('Воссоединение семьи')
        OTHER = 'other', _('Другое')

    title = models.CharField(max_length=200, verbose_name=_('Название результата'))
    percentage_value = models.PositiveIntegerField(verbose_name=_('Процентное значение'))
    description = models.CharField(max_length=300, verbose_name=_('Описание результата'))
    result_type = models.CharField(
        max_length=30,
        choices=ResultType.choices,
        verbose_name=_('Тип результата')
    )
    
    # Изображение
    image = models.ImageField(
        upload_to='impact_results/', 
        verbose_name=_('Изображение')
    )
    
    # Управление отображением
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    is_featured = models.BooleanField(default=False, verbose_name=_('Рекомендуемый'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок отображения'))
    
    # Дополнительная информация
    detailed_description = models.TextField(blank=True, verbose_name=_('Подробное описание'))
    source = models.CharField(max_length=200, blank=True, verbose_name=_('Источник данных'))
    year = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Год данных'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))

    class Meta:
        verbose_name = _('Результат воздействия')
        verbose_name_plural = _('Результаты воздействия')
        ordering = ['order', 'percentage_value']

    def __str__(self):
        return f"{self.percentage_value}% - {self.title}"
