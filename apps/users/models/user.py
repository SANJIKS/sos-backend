from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    class UserType(models.TextChoices):
        DONOR = 'donor', _('Донор')
        STAFF = 'staff', _('Сотрудник')
        VOLUNTEER = 'volunteer', _('Волонтер')
        PARTNER = 'partner', _('Партнер')
        ADMIN = 'admin', _('Администратор')

    class Gender(models.TextChoices):
        MALE = 'male', _('Мужской')
        FEMALE = 'female', _('Женский')
        OTHER = 'other', _('Другой')

    class PreferredLanguage(models.TextChoices):
        RU = 'ru', _('Русский')
        KG = 'kg', _('Кыргызский')
        EN = 'en', _('Английский')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(unique=True, db_index=True, verbose_name=_('Email'))
    first_name = models.CharField(max_length=100, default='', verbose_name=_('Имя'))
    last_name = models.CharField(max_length=100, default='', verbose_name=_('Фамилия'))
    full_name = models.CharField(max_length=255, blank=True, verbose_name=_('Полное имя'))
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Телефон'))
    
    # Дополнительная информация
    user_type = models.CharField(
        max_length=20, 
        choices=UserType.choices, 
        default=UserType.DONOR,
        verbose_name=_('Тип пользователя')
    )
    gender = models.CharField(
        max_length=10, 
        choices=Gender.choices, 
        blank=True, 
        null=True,
        verbose_name=_('Пол')
    )
    birth_date = models.DateField(blank=True, null=True, verbose_name=_('Дата рождения'))
    preferred_language = models.CharField(
        max_length=2, 
        choices=PreferredLanguage.choices, 
        default=PreferredLanguage.RU,
        verbose_name=_('Предпочитаемый язык')
    )
    
    # Адресная информация
    city = models.CharField(max_length=100, blank=True, verbose_name=_('Город'))
    address = models.TextField(blank=True, verbose_name=_('Адрес'))
    postal_code = models.CharField(max_length=10, blank=True, verbose_name=_('Почтовый индекс'))
    
    # Настройки уведомлений
    email_notifications = models.BooleanField(default=True, verbose_name=_('Email уведомления'))
    sms_notifications = models.BooleanField(default=False, verbose_name=_('SMS уведомления'))
    newsletter_subscription = models.BooleanField(default=False, verbose_name=_('Подписка на новости'))
    
    # Согласия
    consent_data_processing = models.BooleanField(default=False, verbose_name=_('Согласие на обработку данных'))
    consent_marketing = models.BooleanField(default=False, verbose_name=_('Согласие на маркетинг'))
    
    # Системные поля
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    is_staff = models.BooleanField(default=False, verbose_name=_('Сотрудник'))
    is_verified = models.BooleanField(default=False, verbose_name=_('Email подтвержден'))
    email_verification_token = models.CharField(max_length=100, blank=True, verbose_name=_('Токен подтверждения'))
    email_verification_expires = models.DateTimeField(blank=True, null=True, verbose_name=_('Срок действия токена'))
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    last_login = models.DateTimeField(blank=True, null=True, verbose_name=_('Последний вход'))
    
    # Источник регистрации
    registration_source = models.CharField(
        max_length=20,
        choices=[
            ('website', _('Сайт')),
            ('f2f', _('Face-to-Face')),
            ('admin', _('Админка')),
            ('api', _('API')),
        ],
        default='website',
        verbose_name=_('Источник регистрации')
    )
    
    # F2F информация (если регистрация через координатора)
    # TODO: Добавить после создания F2F моделей
    # f2f_coordinator = models.ForeignKey(
    #     'donors.F2FCoordinator',
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True,
    #     verbose_name=_('F2F координатор')
    # )
    # f2f_location = models.ForeignKey(
    #     'donors.F2FLocation',
    #     on_delete=models.SET_NULL,
    #     blank=True,
    #     null=True,
    #     verbose_name=_('F2F локация')
    # )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['registration_source']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    @property
    def is_donor(self):
        return self.user_type == self.UserType.DONOR

    @property
    def is_staff_member(self):
        return self.user_type in [self.UserType.STAFF, self.UserType.ADMIN]

    def get_full_name(self):
        """Получить полное имя пользователя"""
        if self.full_name:
            return self.full_name
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Получить короткое имя пользователя"""
        return self.first_name if self.first_name else self.email

    def save(self, *args, **kwargs):
        """Автоматически заполняем full_name при сохранении"""
        if not self.full_name and self.first_name and self.last_name:
            self.full_name = f"{self.first_name} {self.last_name}"
        super().save(*args, **kwargs)

    def get_donation_count(self):
        """Получить количество пожертвований пользователя"""
        from apps.donations.models import Donation
        return Donation.objects.filter(donor_email=self.email).count()

    def get_total_donated(self):
        """Получить общую сумму пожертвований"""
        from apps.donations.models import Donation
        from django.db.models import Sum
        result = Donation.objects.filter(
            donor_email=self.email,
            status='completed'
        ).aggregate(total=Sum('amount'))
        return result['total'] or 0

    def get_active_subscriptions(self):
        """Получить активные подписки"""
        from apps.donations.models import Donation
        return Donation.objects.filter(
            donor_email=self.email,
            is_recurring=True,
            recurring_active=True
        )
