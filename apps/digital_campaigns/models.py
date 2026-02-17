import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class DigitalCampaign(models.Model):
    """
    Модель для цифровых кампаний и инициатив
    """
    
    class CampaignType(models.TextChoices):
        AWARENESS = 'awareness', _('Информирование')
        FUNDRAISING = 'fundraising', _('Сбор средств')
        ADVOCACY = 'advocacy', _('Адвокация')
        EDUCATION = 'education', _('Образование')
        COMMUNITY = 'community', _('Сообщество')
        RESEARCH = 'research', _('Исследование')
        INNOVATION = 'innovation', _('Инновации')
        SUSTAINABILITY = 'sustainability', _('Устойчивость')
        OTHER = 'other', _('Другое')

    class CampaignStatus(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        PLANNING = 'planning', _('Планирование')
        ACTIVE = 'active', _('Активная')
        PAUSED = 'paused', _('Приостановлена')
        COMPLETED = 'completed', _('Завершена')
        CANCELLED = 'cancelled', _('Отменена')

    class ImpactLevel(models.TextChoices):
        LOW = 'low', _('Низкий')
        MEDIUM = 'medium', _('Средний')
        HIGH = 'high', _('Высокий')
        CRITICAL = 'critical', _('Критический')

    # Основная информация
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=255, verbose_name=_('Название кампании'))
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_('URL слаг'))
    description = models.TextField(verbose_name=_('Описание'))
    short_description = models.CharField(max_length=500, verbose_name=_('Краткое описание'))
    
    # Тип и статус
    campaign_type = models.CharField(
        max_length=20,
        choices=CampaignType.choices,
        verbose_name=_('Тип кампании')
    )
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT,
        verbose_name=_('Статус')
    )
    
    # Временные рамки
    start_date = models.DateTimeField(verbose_name=_('Дата начала'))
    end_date = models.DateTimeField(blank=True, null=True, verbose_name=_('Дата окончания'))
    planned_duration_days = models.PositiveIntegerField(
        blank=True, null=True,
        verbose_name=_('Планируемая продолжительность (дни)')
    )
    
    # Цели и метрики
    goal_description = models.TextField(verbose_name=_('Описание целей'))
    target_audience = models.CharField(max_length=500, verbose_name=_('Целевая аудитория'))
    expected_impact = models.TextField(verbose_name=_('Ожидаемое воздействие'))
    impact_level = models.CharField(
        max_length=10,
        choices=ImpactLevel.choices,
        default=ImpactLevel.MEDIUM,
        verbose_name=_('Уровень воздействия')
    )
    
    # Бюджет и ресурсы
    budget_planned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True, null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Запланированный бюджет')
    )
    budget_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Потраченный бюджет')
    )
    
    # Медиа и контент
    main_image = models.ImageField(
        upload_to='digital_campaigns/',
        blank=True, null=True,
        verbose_name=_('Главное изображение')
    )
    banner_image = models.ImageField(
        upload_to='digital_campaigns/banners/',
        blank=True, null=True,
        verbose_name=_('Баннер')
    )
    video_url = models.URLField(blank=True, verbose_name=_('Ссылка на видео'))
    
    # Цифровые метрики
    website_visits = models.PositiveIntegerField(default=0, verbose_name=_('Посещения сайта'))
    social_media_reach = models.PositiveIntegerField(default=0, verbose_name=_('Охват в соцсетях'))
    engagement_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('Уровень вовлеченности (%)')
    )
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('Конверсия (%)')
    )
    
    # Результаты и воздействие
    actual_impact = models.TextField(blank=True, verbose_name=_('Фактическое воздействие'))
    lessons_learned = models.TextField(blank=True, verbose_name=_('Уроки'))
    success_factors = models.TextField(blank=True, verbose_name=_('Факторы успеха'))
    challenges_faced = models.TextField(blank=True, verbose_name=_('Вызовы'))
    
    # Связи с другими кампаниями
    related_donation_campaigns = models.ManyToManyField(
        'donations.DonationCampaign',
        blank=True,
        verbose_name=_('Связанные кампании пожертвований')
    )
    related_programs = models.ManyToManyField(
        'programs.Program',
        blank=True,
        verbose_name=_('Связанные программы')
    )
    
    # Управление отображением
    is_featured = models.BooleanField(default=False, verbose_name=_('Рекомендуемая'))
    is_public = models.BooleanField(default=True, verbose_name=_('Публичная'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок отображения'))
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Создано пользователем')
    )

    class Meta:
        verbose_name = _('Цифровая кампания')
        verbose_name_plural = _('Цифровые кампании')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def progress_percentage(self):
        """Процент выполнения кампании по времени"""
        if not self.start_date or not self.end_date:
            return 0
        
        from django.utils import timezone
        now = timezone.now()
        total_duration = self.end_date - self.start_date
        elapsed = now - self.start_date
        
        if total_duration.total_seconds() <= 0:
            return 100 if now >= self.end_date else 0
        
        progress = (elapsed.total_seconds() / total_duration.total_seconds()) * 100
        return min(max(progress, 0), 100)

    @property
    def budget_utilization(self):
        """Процент использования бюджета"""
        if not self.budget_planned or self.budget_planned == 0:
            return 0
        return min((self.budget_spent / self.budget_planned) * 100, 100)

    @property
    def is_active(self):
        """Активна ли кампания"""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.status == self.CampaignStatus.ACTIVE and
            self.start_date <= now and
            (not self.end_date or self.end_date >= now)
        )


class CampaignMetric(models.Model):
    """
    Модель для метрик цифровых кампаний
    """
    
    class MetricType(models.TextChoices):
        WEBSITE_TRAFFIC = 'website_traffic', _('Трафик сайта')
        SOCIAL_MEDIA = 'social_media', _('Социальные сети')
        EMAIL = 'email', _('Email рассылки')
        CONVERSION = 'conversion', _('Конверсия')
        ENGAGEMENT = 'engagement', _('Вовлеченность')
        REACH = 'reach', _('Охват')
        IMPRESSIONS = 'impressions', _('Показы')
        CLICKS = 'clicks', _('Клики')
        SHARES = 'shares', _('Репосты')
        COMMENTS = 'comments', _('Комментарии')
        LIKES = 'likes', _('Лайки')
        DONATIONS = 'donations', _('Пожертвования')
        REGISTRATIONS = 'registrations', _('Регистрации')
        OTHER = 'other', _('Другое')

    campaign = models.ForeignKey(
        DigitalCampaign,
        on_delete=models.CASCADE,
        related_name='metrics',
        verbose_name=_('Кампания')
    )
    metric_type = models.CharField(
        max_length=20,
        choices=MetricType.choices,
        verbose_name=_('Тип метрики')
    )
    name = models.CharField(max_length=255, verbose_name=_('Название метрики'))
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('Значение')
    )
    unit = models.CharField(max_length=50, verbose_name=_('Единица измерения'))
    date_recorded = models.DateTimeField(verbose_name=_('Дата записи'))
    notes = models.TextField(blank=True, verbose_name=_('Примечания'))
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Метрика кампании')
        verbose_name_plural = _('Метрики кампаний')
        ordering = ['-date_recorded']

    def __str__(self):
        return f"{self.campaign.title} - {self.name}: {self.value} {self.unit}"

