import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from decimal import Decimal

User = get_user_model()


class F2FCoordinator(models.Model):
    """Модель F2F координатора"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Активный')
        INACTIVE = 'inactive', _('Неактивный')
        ON_LEAVE = 'on_leave', _('В отпуске')
        SUSPENDED = 'suspended', _('Приостановлен')
    
    class ExperienceLevel(models.TextChoices):
        TRAINEE = 'trainee', _('Стажер')
        JUNIOR = 'junior', _('Младший')
        MIDDLE = 'middle', _('Средний')
        SENIOR = 'senior', _('Старший')
        LEAD = 'lead', _('Ведущий')
    
    # Основная информация
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='f2f_coordinator')
    employee_id = models.CharField(max_length=20, unique=True, verbose_name=_('ID сотрудника'))
    
    # Личная информация
    full_name = models.CharField(max_length=255, verbose_name=_('ФИО'))
    phone = models.CharField(
        max_length=20, 
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        verbose_name=_('Телефон')
    )
    email = models.EmailField(verbose_name=_('Email'))
    birth_date = models.DateField(verbose_name=_('Дата рождения'))
    
    # Рабочая информация
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Статус')
    )
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.TRAINEE,
        verbose_name=_('Уровень опыта')
    )
    hire_date = models.DateField(verbose_name=_('Дата найма'))
    termination_date = models.DateField(null=True, blank=True, verbose_name=_('Дата увольнения'))
    
    # Территория работы
    assigned_regions = models.ManyToManyField(
        'F2FRegion', 
        through='F2FCoordinatorRegionAssignment',
        verbose_name=_('Назначенные регионы')
    )
    
    # Цели и показатели
    monthly_target = models.PositiveIntegerField(default=50, verbose_name=_('Месячная цель (регистраций)'))
    current_month_registrations = models.PositiveIntegerField(default=0, verbose_name=_('Регистраций в текущем месяце'))
    total_registrations = models.PositiveIntegerField(default=0, verbose_name=_('Всего регистраций'))
    success_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name=_('Коэффициент успеха (%)')
    )
    
    # Настройки устройства
    device_id = models.CharField(max_length=100, blank=True, verbose_name=_('ID устройства'))
    last_sync = models.DateTimeField(null=True, blank=True, verbose_name=_('Последняя синхронизация'))
    offline_mode_enabled = models.BooleanField(default=True, verbose_name=_('Офлайн режим включен'))
    
    # Контактная информация супервайзера
    supervisor = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='subordinates',
        verbose_name=_('Супервайзер')
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('F2F Координатор')
        verbose_name_plural = _('F2F Координаторы')
        indexes = [
            models.Index(fields=['status', 'experience_level']),
            models.Index(fields=['hire_date']),
            models.Index(fields=['device_id']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"
    
    @property
    def is_active(self):
        """Проверка активности координатора"""
        return self.status == self.Status.ACTIVE
    
    @property
    def target_completion_rate(self):
        """Процент выполнения месячной цели"""
        if self.monthly_target > 0:
            return (self.current_month_registrations / self.monthly_target) * 100
        return 0
    
    def reset_monthly_stats(self):
        """Сброс месячной статистики"""
        self.current_month_registrations = 0
        self.save(update_fields=['current_month_registrations'])
    
    def increment_registrations(self, count=1):
        """Увеличение счетчика регистраций"""
        self.current_month_registrations += count
        self.total_registrations += count
        self.save(update_fields=['current_month_registrations', 'total_registrations'])


class F2FRegion(models.Model):
    """Регионы/области для F2F работы"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Название'))
    code = models.CharField(max_length=10, unique=True, verbose_name=_('Код'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активный'))
    
    # Географические координаты центра региона
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('F2F Регион')
        verbose_name_plural = _('F2F Регионы')

    def __str__(self):
        return f"{self.name} ({self.code})"


class F2FCoordinatorRegionAssignment(models.Model):
    """Назначение координатора на регион"""
    
    coordinator = models.ForeignKey(F2FCoordinator, on_delete=models.CASCADE)
    region = models.ForeignKey(F2FRegion, on_delete=models.CASCADE)
    assigned_date = models.DateField(verbose_name=_('Дата назначения'))
    is_primary = models.BooleanField(default=False, verbose_name=_('Основной регион'))
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['coordinator', 'region']
        verbose_name = _('Назначение координатора на регион')
        verbose_name_plural = _('Назначения координаторов на регионы')

    def __str__(self):
        return f"{self.coordinator.full_name} → {self.region.name}"


class F2FLocation(models.Model):
    """Конкретные локации для F2F работы"""
    
    class LocationType(models.TextChoices):
        MALL = 'mall', _('Торговый центр')
        STREET = 'street', _('Улица')
        PARK = 'park', _('Парк')
        MARKET = 'market', _('Рынок')
        EVENT = 'event', _('Мероприятие')
        OFFICE = 'office', _('Офис')
        OTHER = 'other', _('Другое')
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Активная')
        INACTIVE = 'inactive', _('Неактивная')
        TEMPORARILY_CLOSED = 'temp_closed', _('Временно закрыта')
        UNDER_REVIEW = 'under_review', _('На рассмотрении')
    
    # Основная информация
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, verbose_name=_('Название'))
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        verbose_name=_('Тип локации')
    )
    region = models.ForeignKey(F2FRegion, on_delete=models.CASCADE, verbose_name=_('Регион'))
    
    # Адрес и координаты
    address = models.TextField(verbose_name=_('Адрес'))
    latitude = models.DecimalField(max_digits=10, decimal_places=8, verbose_name=_('Широта'))
    longitude = models.DecimalField(max_digits=11, decimal_places=8, verbose_name=_('Долгота'))
    
    # Статус и доступность
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Статус')
    )
    
    # Рабочее время
    working_hours_start = models.TimeField(verbose_name=_('Начало работы'))
    working_hours_end = models.TimeField(verbose_name=_('Конец работы'))
    working_days = models.CharField(
        max_length=20,
        default='1,2,3,4,5,6,7',  # 1=Пн, 7=Вс
        verbose_name=_('Рабочие дни')
    )
    
    # Характеристики локации
    foot_traffic_level = models.CharField(
        max_length=20,
        choices=[
            ('low', _('Низкий')),
            ('medium', _('Средний')),
            ('high', _('Высокий')),
        ],
        default='medium',
        verbose_name=_('Уровень пешеходного трафика')
    )
    
    # Контактная информация
    contact_person = models.CharField(max_length=255, blank=True, verbose_name=_('Контактное лицо'))
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name=_('Контактный телефон'))
    
    # Заметки
    notes = models.TextField(blank=True, verbose_name=_('Заметки'))
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))

    class Meta:
        ordering = ['region', 'name']
        verbose_name = _('F2F Локация')
        verbose_name_plural = _('F2F Локации')
        indexes = [
            models.Index(fields=['region', 'status']),
            models.Index(fields=['location_type']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.name} ({self.region.name})"
    
    @property
    def is_active(self):
        """Проверка активности локации"""
        return self.status == self.Status.ACTIVE
    
    def get_working_days_list(self):
        """Получение списка рабочих дней"""
        return [int(day) for day in self.working_days.split(',') if day.strip()]