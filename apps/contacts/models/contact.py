import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ContactCategory(models.Model):
    """Категории обратной связи"""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=100, verbose_name=_('Название'))
    name_kg = models.CharField(max_length=100, blank=True, verbose_name=_('Название (КГ)'))
    name_en = models.CharField(max_length=100, blank=True, verbose_name=_('Название (EN)'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    email_recipients = models.TextField(
        blank=True,
        verbose_name=_('Email получатели'),
        help_text=_('Список email через запятую для уведомлений')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Активна'))
    sort_order = models.IntegerField(default=0, verbose_name=_('Порядок сортировки'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))

    class Meta:
        verbose_name = _('Категория обратной связи')
        verbose_name_plural = _('Категории обратной связи')
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['sort_order']),
        ]

    def __str__(self):
        return self.name

    def get_name_by_language(self, language_code):
        """Получить название на определенном языке"""
        if language_code == 'kg' and self.name_kg:
            return self.name_kg
        elif language_code == 'en' and self.name_en:
            return self.name_en
        return self.name

    def get_email_recipients_list(self):
        """Получить список email получателей"""
        if not self.email_recipients:
            return []
        return [email.strip() for email in self.email_recipients.split(',') if email.strip()]


class Contact(models.Model):
    """Модель обратной связи"""
    class Status(models.TextChoices):
        NEW = 'new', _('Новое')
        IN_PROGRESS = 'in_progress', _('В обработке')
        RESPONDED = 'responded', _('Отвечено')
        CLOSED = 'closed', _('Закрыто')
        SPAM = 'spam', _('Спам')

    class Priority(models.TextChoices):
        LOW = 'low', _('Низкий')
        NORMAL = 'normal', _('Обычный')
        HIGH = 'high', _('Высокий')
        URGENT = 'urgent', _('Срочный')

    class ContactType(models.TextChoices):
        GENERAL = 'general', _('Общий вопрос')
        DONATION = 'donation', _('Вопрос о пожертвованиях')
        VOLUNTEER = 'volunteer', _('Волонтерство')
        PARTNERSHIP = 'partnership', _('Партнерство')
        COMPLAINT = 'complaint', _('Жалоба')
        SUGGESTION = 'suggestion', _('Предложение')
        OTHER = 'other', _('Другое')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    
    # Основная информация
    category = models.ForeignKey(
        ContactCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contacts',
        verbose_name=_('Категория')
    )
    contact_type = models.CharField(
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.GENERAL,
        verbose_name=_('Тип обращения')
    )
    
    # Контактная информация
    full_name = models.CharField(max_length=255, verbose_name=_('Полное имя'))
    email = models.EmailField(verbose_name=_('Email'))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Телефон'))
    
    # Содержание обращения
    subject = models.CharField(max_length=255, verbose_name=_('Тема'))
    message = models.TextField(verbose_name=_('Сообщение'))
    
    # Дополнительные поля
    company = models.CharField(max_length=255, blank=True, verbose_name=_('Компания'))
    position = models.CharField(max_length=255, blank=True, verbose_name=_('Должность'))
    city = models.CharField(max_length=100, blank=True, verbose_name=_('Город'))
    
    # Настройки
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[
            ('email', _('Email')),
            ('phone', _('Телефон')),
            ('any', _('Любой способ')),
        ],
        default='email',
        verbose_name=_('Предпочитаемый способ связи')
    )
    
    # Согласия
    consent_data_processing = models.BooleanField(
        default=False,
        verbose_name=_('Согласие на обработку данных')
    )
    consent_marketing = models.BooleanField(
        default=False,
        verbose_name=_('Согласие на маркетинг')
    )
    
    # Статус и приоритет
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name=_('Статус')
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name=_('Приоритет')
    )
    
    # Техническая информация
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP адрес')
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    referrer = models.URLField(
        blank=True,
        verbose_name=_('Источник')
    )
    
    # Защита от ботов
    captcha_token = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Токен капчи')
    )
    is_bot = models.BooleanField(
        default=False,
        verbose_name=_('Обнаружен как бот')
    )
    
    # Обработка
    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_contacts',
        verbose_name=_('Назначено')
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name=_('Внутренние заметки')
    )
    
    # Ответы
    response_message = models.TextField(
        blank=True,
        verbose_name=_('Ответ')
    )
    responded_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_contacts',
        verbose_name=_('Ответил')
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата ответа')
    )
    
    # Временные метки
    created_at = models.DateTimeField(
        default=timezone.now, 
        verbose_name=_('Создано')
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('Обновлено')
    )
    
    # Уведомления
    email_sent = models.BooleanField(
        default=False,
        verbose_name=_('Email отправлен')
    )
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Дата отправки email')
    )

    class Meta:
        verbose_name = _('Обращение')
        verbose_name_plural = _('Обращения')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['contact_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['email']),
            models.Index(fields=['is_bot']),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.subject} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Если статус изменился на "отвечено", устанавливаем дату ответа
        if self.status == self.Status.RESPONDED and not self.responded_at:
            self.responded_at = timezone.now()
        
        super().save(*args, **kwargs)

    def mark_as_responded(self, response_message, responded_by):
        """Пометить как отвеченное"""
        self.status = self.Status.RESPONDED
        self.response_message = response_message
        self.responded_by = responded_by
        self.responded_at = timezone.now()
        self.save()

    def mark_as_spam(self):
        """Пометить как спам"""
        self.status = self.Status.SPAM
        self.is_bot = True
        self.save()

    def get_priority_color(self):
        """Получить цвет приоритета для админки"""
        colors = {
            self.Priority.LOW: '#28a745',
            self.Priority.NORMAL: '#007bff',
            self.Priority.HIGH: '#ffc107',
            self.Priority.URGENT: '#dc3545',
        }
        return colors.get(self.priority, '#6c757d')

    def get_status_color(self):
        """Получить цвет статуса для админки"""
        colors = {
            self.Status.NEW: '#007bff',
            self.Status.IN_PROGRESS: '#ffc107',
            self.Status.RESPONDED: '#28a745',
            self.Status.CLOSED: '#6c757d',
            self.Status.SPAM: '#dc3545',
        }
        return colors.get(self.status, '#6c757d')

    @property
    def is_urgent(self):
        """Проверить, является ли обращение срочным"""
        return self.priority == self.Priority.URGENT

    @property
    def response_time(self):
        """Время ответа в часах"""
        if self.responded_at and self.created_at:
            delta = self.responded_at - self.created_at
            return delta.total_seconds() / 3600
        return None

    @property
    def needs_response(self):
        """Требует ли обращение ответа"""
        return self.status in [self.Status.NEW, self.Status.IN_PROGRESS]
