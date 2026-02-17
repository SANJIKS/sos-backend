import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, EmailValidator
from decimal import Decimal
from datetime import timedelta

User = get_user_model()


class F2FRegistration(models.Model):
    """Модель регистрации донора через F2F координатора"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Ожидает обработки')
        PROCESSED = 'processed', _('Обработано')
        CONFIRMED = 'confirmed', _('Подтверждено')
        REJECTED = 'rejected', _('Отклонено')
        CANCELLED = 'cancelled', _('Отменено')
    
    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', _('Банковский перевод')
        CARD = 'card', _('Банковская карта')
        CASH = 'cash', _('Наличные')
        MOBILE_PAYMENT = 'mobile_payment', _('Мобильный платеж')
    
    class DonationType(models.TextChoices):
        MONTHLY = 'monthly', _('Ежемесячное')
        QUARTERLY = 'quarterly', _('Ежеквартальное')
        ANNUAL = 'annual', _('Ежегодное')
        ONE_TIME = 'one_time', _('Разовое')
    
    class PreferredLanguage(models.TextChoices):
        RU = 'ru', _('Русский')
        EN = 'en', _('Английский')
        KY = 'ky', _('Кыргызский')
    
    class Gender(models.TextChoices):
        MALE = 'M', _('Мужской')
        FEMALE = 'F', _('Женский')
        OTHER = 'O', _('Другой')
        PREFER_NOT_TO_SAY = 'P', _('Предпочитаю не указывать')

    # Основная информация
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    registration_number = models.CharField(max_length=20, unique=True, verbose_name=_('Номер регистрации'))
    
    # Координатор и локация
    coordinator = models.ForeignKey(
        'F2FCoordinator', 
        on_delete=models.PROTECT,
        related_name='registrations',
        verbose_name=_('Координатор')
    )
    location = models.ForeignKey(
        'F2FLocation',
        on_delete=models.PROTECT,
        related_name='registrations',
        verbose_name=_('Локация')
    )
    
    # Информация о доноре
    full_name = models.CharField(max_length=255, verbose_name=_('ФИО'))
    email = models.EmailField(
        validators=[EmailValidator()],
        verbose_name=_('Email')
    )
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        verbose_name=_('Телефон')
    )
    birth_date = models.DateField(verbose_name=_('Дата рождения'))
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        verbose_name=_('Пол')
    )
    preferred_language = models.CharField(
        max_length=2,
        choices=PreferredLanguage.choices,
        default=PreferredLanguage.RU,
        verbose_name=_('Предпочитаемый язык')
    )
    
    # Адрес донора
    city = models.CharField(max_length=100, verbose_name=_('Город'))
    address = models.TextField(blank=True, verbose_name=_('Адрес'))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_('Почтовый индекс'))
    
    # Информация о пожертвовании
    donation_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Сумма пожертвования')
    )
    donation_type = models.CharField(
        max_length=20,
        choices=DonationType.choices,
        verbose_name=_('Тип пожертвования')
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name=_('Способ оплаты')
    )
    
    # Согласия и разрешения
    consent_data_processing = models.BooleanField(default=False, verbose_name=_('Согласие на обработку данных'))
    consent_marketing = models.BooleanField(default=False, verbose_name=_('Согласие на маркетинг'))
    consent_newsletter = models.BooleanField(default=False, verbose_name=_('Согласие на рассылку'))
    
    # Статус обработки
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('Статус')
    )
    
    # Связанные объекты
    donor = models.ForeignKey(
        'Donor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='f2f_registrations',
        verbose_name=_('Связанный донор')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='f2f_registrations',
        verbose_name=_('Пользователь')
    )
    
    # Данные синхронизации
    is_synced = models.BooleanField(default=False, verbose_name=_('Синхронизировано'))
    sync_attempts = models.PositiveIntegerField(default=0, verbose_name=_('Попытки синхронизации'))
    last_sync_attempt = models.DateTimeField(null=True, blank=True, verbose_name=_('Последняя попытка синхронизации'))
    sync_error = models.TextField(blank=True, verbose_name=_('Ошибка синхронизации'))
    
    # Метаданные регистрации
    registration_source = models.CharField(max_length=50, default='f2f_mobile', verbose_name=_('Источник регистрации'))
    device_info = models.JSONField(default=dict, blank=True, verbose_name=_('Информация об устройстве'))
    gps_coordinates = models.JSONField(default=dict, blank=True, verbose_name=_('GPS координаты'))
    
    # Заметки
    coordinator_notes = models.TextField(blank=True, verbose_name=_('Заметки координатора'))
    admin_notes = models.TextField(blank=True, verbose_name=_('Заметки администратора'))
    
    # Временные метки
    registered_at = models.DateTimeField(verbose_name=_('Зарегистрировано'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))

    class Meta:
        ordering = ['-registered_at', '-created_at']
        verbose_name = _('F2F Регистрация')
        verbose_name_plural = _('F2F Регистрации')
        indexes = [
            models.Index(fields=['coordinator', 'status']),
            models.Index(fields=['location', 'registered_at']),
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['is_synced']),
            models.Index(fields=['registration_number']),
        ]

    def __str__(self):
        return f"{self.registration_number} - {self.full_name}"
    
    def save(self, *args, **kwargs):
        # Автоматическая генерация номера регистрации
        if not self.registration_number:
            from django.utils import timezone
            now = timezone.now()
            prefix = f"F2F{now.strftime('%Y%m')}"
            
            # Найти последний номер в этом месяце
            last_registration = F2FRegistration.objects.filter(
                registration_number__startswith=prefix
            ).order_by('-registration_number').first()
            
            if last_registration:
                last_number = int(last_registration.registration_number[9:])  # После префикса F2FYYYYMM
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.registration_number = f"{prefix}{new_number:04d}"
        
        super().save(*args, **kwargs)
    
    @property
    def is_pending(self):
        """Проверка статуса ожидания"""
        return self.status == self.Status.PENDING
    
    @property
    def needs_sync(self):
        """Нужна ли синхронизация"""
        return not self.is_synced and self.status != self.Status.CANCELLED
    
    def mark_as_synced(self):
        """Отметить как синхронизированное"""
        self.is_synced = True
        self.sync_error = ''
        self.save(update_fields=['is_synced', 'sync_error', 'updated_at'])
    
    def mark_sync_failed(self, error_message):
        """Отметить ошибку синхронизации"""
        self.sync_attempts += 1
        self.sync_error = error_message
        from django.utils import timezone
        self.last_sync_attempt = timezone.now()
        self.save(update_fields=['sync_attempts', 'sync_error', 'last_sync_attempt', 'updated_at'])


class F2FRegistrationDocument(models.Model):
    """Документы и подписи для F2F регистрации"""
    
    class DocumentType(models.TextChoices):
        CONSENT_FORM = 'consent_form', _('Форма согласия')
        SIGNATURE = 'signature', _('Подпись')
        ID_PHOTO = 'id_photo', _('Фото документа')
        SELFIE = 'selfie', _('Селфи с координатором')
        ADDITIONAL = 'additional', _('Дополнительный документ')
    
    registration = models.ForeignKey(
        F2FRegistration,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('Регистрация')
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        verbose_name=_('Тип документа')
    )
    file = models.FileField(
        upload_to='f2f_documents/%Y/%m/%d/',
        verbose_name=_('Файл')
    )
    file_name = models.CharField(max_length=255, verbose_name=_('Имя файла'))
    file_size = models.PositiveIntegerField(verbose_name=_('Размер файла'))
    content_type = models.CharField(max_length=100, verbose_name=_('Тип контента'))
    
    # Синхронизация
    is_synced = models.BooleanField(default=False, verbose_name=_('Синхронизировано'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))

    class Meta:
        verbose_name = _('Документ F2F регистрации')
        verbose_name_plural = _('Документы F2F регистраций')

    def __str__(self):
        return f"{self.registration.registration_number} - {self.get_document_type_display()}"


class F2FDailyReport(models.Model):
    """Ежедневный отчет координатора"""
    
    coordinator = models.ForeignKey(
        'F2FCoordinator',
        on_delete=models.CASCADE,
        related_name='daily_reports',
        verbose_name=_('Координатор')
    )
    location = models.ForeignKey(
        'F2FLocation',
        on_delete=models.CASCADE,
        verbose_name=_('Локация')
    )
    report_date = models.DateField(verbose_name=_('Дата отчета'))
    
    # Статистика за день
    total_approaches = models.PositiveIntegerField(default=0, verbose_name=_('Всего подходов'))
    successful_registrations = models.PositiveIntegerField(default=0, verbose_name=_('Успешных регистраций'))
    rejected_approaches = models.PositiveIntegerField(default=0, verbose_name=_('Отказов'))
    
    # Время работы
    start_time = models.TimeField(verbose_name=_('Время начала'))
    end_time = models.TimeField(verbose_name=_('Время окончания'))
    break_duration = models.DurationField(default=timedelta(0), verbose_name=_('Продолжительность перерывов'))
    
    # Заметки
    notes = models.TextField(blank=True, verbose_name=_('Заметки'))
    weather_conditions = models.CharField(max_length=100, blank=True, verbose_name=_('Погодные условия'))
    foot_traffic_assessment = models.CharField(
        max_length=20,
        choices=[
            ('low', _('Низкий')),
            ('medium', _('Средний')),
            ('high', _('Высокий')),
        ],
        blank=True,
        verbose_name=_('Оценка пешеходного трафика')
    )
    
    # Синхронизация
    is_synced = models.BooleanField(default=False, verbose_name=_('Синхронизировано'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))

    class Meta:
        unique_together = ['coordinator', 'location', 'report_date']
        ordering = ['-report_date']
        verbose_name = _('Ежедневный отчет F2F')
        verbose_name_plural = _('Ежедневные отчеты F2F')

    def __str__(self):
        return f"{self.coordinator.full_name} - {self.report_date}"
    
    @property
    def conversion_rate(self):
        """Коэффициент конверсии"""
        if self.total_approaches > 0:
            return (self.successful_registrations / self.total_approaches) * 100
        return 0
    
    @property
    def working_hours(self):
        """Количество рабочих часов"""
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        
        if end < start:  # Переход через полночь
            end += timedelta(days=1)
        
        working_time = end - start - self.break_duration
        return working_time.total_seconds() / 3600  # В часах