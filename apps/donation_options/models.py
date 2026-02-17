from django.db import models
from django.utils.translation import gettext_lazy as _


class DonationOption(models.Model):
    """
    Модель для типов пожертвований/способов поддержки
    """
    class OptionType(models.TextChoices):
        ANNIVERSARY = 'anniversary', _('Посвятите свой юбилей')
        PAYROLL = 'payroll', _('Пожертвование доли зарплаты')
        NON_MONETARY = 'non_monetary', _('Неденежные пожертвования')
        ONE_TIME = 'one_time', _('Разовое пожертвование')
        MONTHLY = 'monthly', _('Ежемесячное пожертвование')
        CORPORATE = 'corporate', _('Корпоративное партнерство')
        VOLUNTEER = 'volunteer', _('Волонтерство')
        OTHER = 'other', _('Другое')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Активно')
        COMING_SOON = 'coming_soon', _('Скоро')
        INACTIVE = 'inactive', _('Неактивно')
        MAINTENANCE = 'maintenance', _('На обслуживании')

    title = models.CharField(max_length=200, verbose_name=_('Название'))
    description = models.TextField(verbose_name=_('Описание'))
    option_type = models.CharField(
        max_length=30,
        choices=OptionType.choices,
        verbose_name=_('Тип пожертвования')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Статус')
    )
    
    # Изображение
    image = models.ImageField(
        upload_to='donation_options/', 
        verbose_name=_('Изображение')
    )
    
    # Кнопка
    button_text = models.CharField(max_length=100, verbose_name=_('Текст кнопки'))
    button_url = models.URLField(blank=True, verbose_name=_('Ссылка кнопки'))
    is_button_enabled = models.BooleanField(default=True, verbose_name=_('Кнопка активна'))
    
    # Управление отображением
    is_active = models.BooleanField(default=True, verbose_name=_('Активно'))
    is_featured = models.BooleanField(default=False, verbose_name=_('Рекомендуемое'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок отображения'))
    
    # Дополнительная информация
    detailed_description = models.TextField(blank=True, verbose_name=_('Подробное описание'))
    requirements = models.TextField(blank=True, verbose_name=_('Требования'))
    benefits = models.TextField(blank=True, verbose_name=_('Преимущества'))
    min_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True, 
        verbose_name=_('Минимальная сумма')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))

    class Meta:
        verbose_name = _('Тип пожертвования')
        verbose_name_plural = _('Типы пожертвований')
        ordering = ['order', 'title']

    def __str__(self):
        return self.title
