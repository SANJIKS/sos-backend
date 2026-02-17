import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
import string
import random

User = get_user_model()


class DonationCampaign(models.Model):
    """Кампании пожертвований (например, Новый год, подготовка к школе)"""
    
    class CampaignStatus(models.TextChoices):
        DRAFT = 'draft', _('Черновик')
        ACTIVE = 'active', _('Активная')
        PAUSED = 'paused', _('Приостановлена')
        COMPLETED = 'completed', _('Завершена')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, verbose_name=_('Название кампании'))
    slug = models.SlugField(max_length=255, unique=True, verbose_name=_('URL слаг'))
    description = models.TextField(verbose_name=_('Описание'))
    image = models.ImageField(upload_to='campaigns/', blank=True, null=True, verbose_name=_('Изображение'))
    goal_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Цель сбора')
    )
    raised_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        verbose_name=_('Собрано средств')
    )
    status = models.CharField(
        max_length=20, 
        choices=CampaignStatus.choices, 
        default=CampaignStatus.DRAFT,
        verbose_name=_('Статус')
    )
    start_date = models.DateTimeField(verbose_name=_('Дата начала'))
    end_date = models.DateTimeField(blank=True, null=True, verbose_name=_('Дата окончания'))
    is_featured = models.BooleanField(default=False, verbose_name=_('Рекомендуемая'))
    
    # Salesforce синхронизация
    salesforce_id = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Salesforce Campaign ID'))
    salesforce_synced = models.BooleanField(default=False, verbose_name=_('Синхронизировано с Salesforce'))
    salesforce_sync_error = models.TextField(blank=True, verbose_name=_('Ошибка синхронизации Salesforce'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Кампания пожертвований')
        verbose_name_plural = _('Кампании пожертвований')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def progress_percentage(self):
        """Процент выполнения цели"""
        if self.goal_amount == 0:
            return 0
        return min((self.raised_amount / self.goal_amount) * 100, 100)


class Donation(models.Model):
    """Основная модель пожертвования"""
    
    class DonationType(models.TextChoices):
        ONE_TIME = 'one_time', _('Разовое')
        MONTHLY = 'monthly', _('Ежемесячное')
        QUARTERLY = 'quarterly', _('Ежеквартальное')
        YEARLY = 'yearly', _('Ежегодное')

    class DonationStatus(models.TextChoices):
        PENDING = 'pending', _('Ожидает оплаты')
        PROCESSING = 'processing', _('В обработке')
        COMPLETED = 'completed', _('Завершено')
        FAILED = 'failed', _('Неудачно')
        CANCELLED = 'cancelled', _('Отменено')
        REFUNDED = 'refunded', _('Возвращено')

    class SubscriptionStatus(models.TextChoices):
        ACTIVE = 'active', _('Активная')
        PAUSED = 'paused', _('Приостановлена')
        CANCELLED = 'cancelled', _('Отменена')
        PENDING = 'pending', _('Ожидает активации')
        EXPIRED = 'expired', _('Истекла')

    class PaymentMethod(models.TextChoices):
        BANK_CARD = 'bank_card', _('Банковская карта')
        BANK_TRANSFER = 'bank_transfer', _('Банковский перевод')
        MOBILE_PAYMENT = 'mobile_payment', _('Мобильный платеж')
        CRYPTO = 'crypto', _('Криптовалюта')
        CASH = 'cash', _('Наличные (F2F)')

    class Currency(models.TextChoices):
        KGS = 'KGS', _('Сом')
        USD = 'USD', _('Доллар США')
        EUR = 'EUR', _('Евро')
        RUB = 'RUB', _('Российский рубль')

    class DonorSource(models.TextChoices):
        ONLINE = 'online', _('Онлайн')
        F2F = 'f2f', _('Face-to-Face')
        PHONE = 'phone', _('По телефону')
        EMAIL = 'email', _('По email')

    # Основные поля
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    donation_code = models.CharField(max_length=12, unique=True, editable=False, verbose_name=_('Код пожертвования'))
    
    # Связи
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Пользователь'))
    campaign = models.ForeignKey(DonationCampaign, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Кампания'))
    
    # Информация о доноре (может быть без регистрации)
    donor_email = models.EmailField(verbose_name=_('Email донора'))
    donor_phone = models.CharField(max_length=20, verbose_name=_('Телефон донора'))
    donor_full_name = models.CharField(max_length=255, verbose_name=_('ФИО донора'))
    
    # Детали пожертвования
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Сумма')
    )
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.KGS, verbose_name=_('Валюта'))
    donation_type = models.CharField(max_length=20, choices=DonationType.choices, verbose_name=_('Тип пожертвования'))
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, verbose_name=_('Способ оплаты'))
    
    # Статус и обработка
    status = models.CharField(max_length=20, choices=DonationStatus.choices, default=DonationStatus.PENDING, verbose_name=_('Статус'))
    donor_source = models.CharField(max_length=20, choices=DonorSource.choices, default=DonorSource.ONLINE, verbose_name=_('Источник'))
    
    # Рекуррентные платежи
    is_recurring = models.BooleanField(default=False, verbose_name=_('Рекуррентный платеж'))
    parent_donation = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Родительское пожертвование'))
    parent_order_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('Родительский Order ID'),
        help_text=_('Order ID первого платежа в рекуррентной подписке. Используется для связи всех последующих платежей.')
    )
    first_payment_date = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата первого успешного платежа'), help_text=_('Используется для расчета следующих платежей в тот же день месяца'))
    next_payment_date = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата следующего платежа'))
    recurring_active = models.BooleanField(default=True, verbose_name=_('Рекуррентная подписка активна'))
    subscription_status = models.CharField(
        max_length=20, 
        choices=SubscriptionStatus.choices, 
        null=True, 
        blank=True,
        verbose_name=_('Статус подписки'),
        help_text=_('Применяется только для рекуррентных платежей')
    )
    
    # Токен карты для рекуррентных платежей
    current_card_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('Текущий токен карты')
    )
    
    # ID рекуррентного профиля от FreedomPay
    recurring_profile_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('ID рекуррентного профиля'),
        help_text=_('pg_recurring_profile из ответа FreedomPay')
    )
    
    # Комментарии и пожелания
    donor_comment = models.TextField(blank=True, verbose_name=_('Комментарий донора'))
    admin_notes = models.TextField(blank=True, verbose_name=_('Заметки администратора'))
    
    # F2F поля
    f2f_coordinator = models.ForeignKey('F2FCoordinator', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('F2F координатор'))
    f2f_location = models.ForeignKey('F2FLocation', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('F2F локация'))
    
    # Техническая информация
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('IP адрес'))
    user_agent = models.TextField(blank=True, verbose_name=_('User Agent'))
    
    # Salesforce синхронизация
    salesforce_id = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Salesforce ID'))
    salesforce_synced = models.BooleanField(default=False, verbose_name=_('Синхронизировано с Salesforce'))
    salesforce_sync_error = models.TextField(blank=True, verbose_name=_('Ошибка синхронизации Salesforce'))
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))
    payment_completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата завершения платежа'))

    class Meta:
        verbose_name = _('Пожертвование')
        verbose_name_plural = _('Пожертвования')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['donation_code']),
            models.Index(fields=['donor_email']),
            models.Index(fields=['status']),
            models.Index(fields=['is_recurring']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.donation_code} - {self.donor_full_name} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.donation_code:
            self.donation_code = self.generate_unique_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_unique_code():
        """Генерирует уникальный 12-символьный код пожертвования"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            if not Donation.objects.filter(donation_code=code).exists():
                return code
    
    def activate_subscription(self):
        """Активирует подписку (после успешной оплаты первого платежа)"""
        if self.is_recurring and self.status == 'completed':
            self.subscription_status = self.SubscriptionStatus.ACTIVE
            self.recurring_active = True
            self.save(update_fields=['subscription_status', 'recurring_active'])
    
    def cancel_subscription(self):
        """Отменяет подписку"""
        if self.is_recurring:
            self.subscription_status = self.SubscriptionStatus.CANCELLED
            self.recurring_active = False
            self.save(update_fields=['subscription_status', 'recurring_active'])
    
    def pause_subscription(self):
        """Приостанавливает подписку"""
        if self.is_recurring and self.subscription_status == self.SubscriptionStatus.ACTIVE:
            self.subscription_status = self.SubscriptionStatus.PAUSED
            self.save(update_fields=['subscription_status'])
    
    def resume_subscription(self):
        """Возобновляет подписку"""
        if self.is_recurring and self.subscription_status in [
            self.SubscriptionStatus.PAUSED, 
            self.SubscriptionStatus.CANCELLED
        ]:
            self.subscription_status = self.SubscriptionStatus.ACTIVE
            self.recurring_active = True
            self.save(update_fields=['subscription_status', 'recurring_active'])
    
    @property
    def is_subscription_active(self):
        """Проверяет, активна ли подписка"""
        return (
            self.is_recurring and 
            self.recurring_active and 
            self.subscription_status == self.SubscriptionStatus.ACTIVE
        )
    
    @property
    def can_download_receipt(self):
        """Проверяет, можно ли скачать квитанцию"""
        return self.status in ['completed', 'processing', 'refunded']


class DonationTransaction(models.Model):
    """Транзакции пожертвований для отслеживания платежей"""
    
    class TransactionStatus(models.TextChoices):
        PENDING = 'pending', _('Ожидает')
        PROCESSING = 'processing', _('В обработке')
        SUCCESS = 'success', _('Успешно')
        FAILED = 'failed', _('Неудачно')
        CANCELLED = 'cancelled', _('Отменено')
        REFUNDED = 'refunded', _('Возвращено')

    class TransactionType(models.TextChoices):
        PAYMENT = 'payment', _('Платеж')
        REFUND = 'refund', _('Возврат')
        CHARGEBACK = 'chargeback', _('Возвратный платеж')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='transactions', verbose_name=_('Пожертвование'))
    
    # Детали транзакции
    transaction_id = models.CharField(max_length=255, unique=True, verbose_name=_('ID транзакции'))
    external_transaction_id = models.CharField(max_length=255, blank=True, verbose_name=_('Внешний ID транзакции'))
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_('Сумма'))
    currency = models.CharField(max_length=3, verbose_name=_('Валюта'))
    
    # Статус и тип
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING, verbose_name=_('Статус'))
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, default=TransactionType.PAYMENT, verbose_name=_('Тип транзакции'))
    
    # Платежная система
    payment_gateway = models.CharField(max_length=100, verbose_name=_('Платежная система'))
    gateway_response = models.JSONField(default=dict, blank=True, verbose_name=_('Ответ платежной системы'))
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Обработано'))
    
    # Ошибки
    error_code = models.CharField(max_length=100, blank=True, verbose_name=_('Код ошибки'))
    error_message = models.TextField(blank=True, verbose_name=_('Сообщение об ошибке'))

    class Meta:
        verbose_name = _('Транзакция пожертвования')
        verbose_name_plural = _('Транзакции пожертвований')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.donation.donation_code} - {self.amount} {self.currency}"


class F2FCoordinator(models.Model):
    """Координаторы Face-to-Face регистрации"""
    
    class CoordinatorStatus(models.TextChoices):
        ACTIVE = 'active', _('Активный')
        INACTIVE = 'inactive', _('Неактивный')
        SUSPENDED = 'suspended', _('Приостановлен')

    class Position(models.TextChoices):
        VOLUNTEER = 'volunteer', _('Волонтер')
        COORDINATOR = 'coordinator', _('Координатор')
        REGIONAL_MANAGER = 'regional_manager', _('Региональный менеджер')
        SUPERVISOR = 'supervisor', _('Супервайзер')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    coordinator_id = models.CharField(max_length=20, unique=True, verbose_name=_('ID координатора'))
    
    # Личная информация
    full_name = models.CharField(max_length=255, verbose_name=_('ФИО'))
    phone = models.CharField(max_length=20, verbose_name=_('Телефон'))
    email = models.EmailField(verbose_name=_('Email'))
    
    # Должность и статус
    position = models.CharField(max_length=20, choices=Position.choices, verbose_name=_('Должность'))
    status = models.CharField(max_length=20, choices=CoordinatorStatus.choices, default=CoordinatorStatus.ACTIVE, verbose_name=_('Статус'))
    
    # Назначенные зоны
    assigned_zones = models.ManyToManyField('F2FZone', blank=True, verbose_name=_('Назначенные зоны'))
    
    # Статистика
    total_donors_registered = models.PositiveIntegerField(default=0, verbose_name=_('Всего зарегистрировано доноров'))
    total_donations_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Общая сумма пожертвований'))
    
    # Даты
    hire_date = models.DateField(verbose_name=_('Дата найма'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('F2F Координатор')
        verbose_name_plural = _('F2F Координаторы')
        ordering = ['full_name']

    def __str__(self):
        return f"{self.coordinator_id} - {self.full_name}"


class F2FZone(models.Model):
    """Географические зоны для F2F работы"""
    
    name = models.CharField(max_length=255, verbose_name=_('Название зоны'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    city = models.CharField(max_length=100, verbose_name=_('Город'))
    region = models.CharField(max_length=100, verbose_name=_('Регион'))
    
    is_active = models.BooleanField(default=True, verbose_name=_('Активная'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('F2F Зона')
        verbose_name_plural = _('F2F Зоны')
        ordering = ['city', 'name']

    def __str__(self):
        return f"{self.city} - {self.name}"


class F2FLocation(models.Model):
    """Локации для проведения F2F кампаний"""
    
    class LocationType(models.TextChoices):
        MALL = 'mall', _('Торговый центр')
        STREET = 'street', _('Улица')
        EVENT = 'event', _('Мероприятие')
        OFFICE = 'office', _('Офис')
        UNIVERSITY = 'university', _('Университет')
        OTHER = 'other', _('Другое')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, verbose_name=_('Название локации'))
    address = models.TextField(verbose_name=_('Адрес'))
    zone = models.ForeignKey(F2FZone, on_delete=models.CASCADE, verbose_name=_('Зона'))
    location_type = models.CharField(max_length=20, choices=LocationType.choices, verbose_name=_('Тип локации'))
    
    # Координаты (для карт)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_('Широта'))
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_('Долгота'))
    
    # Дополнительная информация
    contact_person = models.CharField(max_length=255, blank=True, verbose_name=_('Контактное лицо'))
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name=_('Контактный телефон'))
    notes = models.TextField(blank=True, verbose_name=_('Заметки'))
    
    is_active = models.BooleanField(default=True, verbose_name=_('Активная'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('F2F Локация')
        verbose_name_plural = _('F2F Локации')
        ordering = ['zone', 'name']

    def __str__(self):
        return f"{self.zone.city} - {self.name}"


class F2FSession(models.Model):
    """Сессии работы F2F координаторов"""
    
    class SessionStatus(models.TextChoices):
        PLANNED = 'planned', _('Запланирована')
        ACTIVE = 'active', _('Активная')
        COMPLETED = 'completed', _('Завершена')
        CANCELLED = 'cancelled', _('Отменена')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    coordinator = models.ForeignKey(F2FCoordinator, on_delete=models.CASCADE, verbose_name=_('Координатор'))
    location = models.ForeignKey(F2FLocation, on_delete=models.CASCADE, verbose_name=_('Локация'))
    
    # Время сессии
    session_date = models.DateField(verbose_name=_('Дата сессии'))
    start_time = models.TimeField(verbose_name=_('Время начала'))
    end_time = models.TimeField(verbose_name=_('Время окончания'))
    
    # Статус и результаты
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.PLANNED, verbose_name=_('Статус'))
    donors_registered = models.PositiveIntegerField(default=0, verbose_name=_('Зарегистрировано доноров'))
    total_amount_raised = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Общая сумма собранных средств'))
    
    # Заметки
    session_notes = models.TextField(blank=True, verbose_name=_('Заметки о сессии'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('F2F Сессия')
        verbose_name_plural = _('F2F Сессии')
        ordering = ['-session_date', '-start_time']

    def __str__(self):
        return f"{self.session_date} - {self.coordinator.full_name} - {self.location.name}"


class RecurringConsentLog(models.Model):
    """Лог согласия на рекуррентные платежи"""
    
    class ConsentType(models.TextChoices):
        GRANTED = 'granted', _('Предоставлено')
        REVOKED = 'revoked', _('Отозвано')
        MODIFIED = 'modified', _('Изменено')
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='consent_logs', verbose_name=_('Пожертвование'))
    
    # Тип согласия
    consent_type = models.CharField(max_length=20, choices=ConsentType.choices, verbose_name=_('Тип согласия'))
    
    # Детали согласия
    recurring_frequency = models.CharField(max_length=20, choices=Donation.DonationType.choices, verbose_name=_('Частота рекуррентных платежей'))
    consent_text = models.TextField(verbose_name=_('Текст согласия'))
    
    # Техническая информация
    ip_address = models.GenericIPAddressField(verbose_name=_('IP адрес'))
    user_agent = models.TextField(verbose_name=_('User Agent'))
    session_id = models.CharField(max_length=255, blank=True, verbose_name=_('ID сессии'))
    
    # Токен подтверждения
    confirmation_token = models.CharField(max_length=255, blank=True, verbose_name=_('Токен подтверждения'))
    
    # Дополнительные метаданные
    referrer = models.URLField(blank=True, verbose_name=_('Реферер'))
    device_info = models.JSONField(default=dict, blank=True, verbose_name=_('Информация об устройстве'))
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    
    class Meta:
        verbose_name = _('Лог согласия на рекуррентные платежи')
        verbose_name_plural = _('Логи согласий на рекуррентные платежи')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['donation']),
            models.Index(fields=['consent_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        return f"{self.donation.donation_code} - {self.get_consent_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"