import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class TwoFactorAuth(models.Model):
    """Основная модель для управления 2FA пользователя"""
    
    class AuthMethod(models.TextChoices):
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        AUTHENTICATOR = 'authenticator', 'Authenticator App'
    
    class Status(models.TextChoices):
        DISABLED = 'disabled', 'Отключено'
        ENABLED = 'enabled', 'Включено'
        REQUIRED = 'required', 'Обязательно'
        TEMPORARILY_DISABLED = 'temporarily_disabled', 'Временно отключено'
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor_auth')
    auth_method = models.CharField(max_length=20, choices=AuthMethod.choices, default=AuthMethod.EMAIL)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.DISABLED)
    
    # Настройки безопасности
    is_required = models.BooleanField(default=False)  # Обязательно для админов и сотрудников
    backup_codes_enabled = models.BooleanField(default=False)
    
    # Статистика
    last_used_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveIntegerField(default=0)
    last_failed_attempt = models.DateTimeField(null=True, blank=True)
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Двухфакторная аутентификация'
        verbose_name_plural = 'Двухфакторная аутентификация'
    
    def __str__(self):
        return f"2FA для {self.user.email} - {self.get_status_display()}"
    
    @property
    def is_enabled(self):
        """Проверка, включена ли 2FA"""
        return self.status in [self.Status.ENABLED, self.Status.REQUIRED]
    
    @property
    def is_locked(self):
        """Проверка, заблокирована ли 2FA из-за неудачных попыток"""
        if self.failed_attempts >= 5 and self.last_failed_attempt:
            # Блокировка на 30 минут после 5 неудачных попыток
            lock_until = self.last_failed_attempt + timezone.timedelta(minutes=30)
            return timezone.now() < lock_until
        return False
    
    def reset_failed_attempts(self):
        """Сброс счетчика неудачных попыток"""
        self.failed_attempts = 0
        self.last_failed_attempt = None
        self.save(update_fields=['failed_attempts', 'last_failed_attempt'])
    
    def increment_failed_attempts(self):
        """Увеличение счетчика неудачных попыток"""
        self.failed_attempts += 1
        self.last_failed_attempt = timezone.now()
        self.save(update_fields=['failed_attempts', 'last_failed_attempt'])


class TwoFactorCode(models.Model):
    """Модель для хранения кодов подтверждения"""
    
    class CodeType(models.TextChoices):
        EMAIL = 'email', 'Email код'
        SMS = 'sms', 'SMS код'
        BACKUP = 'backup', 'Резервный код'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает подтверждения'
        USED = 'used', 'Использован'
        EXPIRED = 'expired', 'Истек'
        INVALIDATED = 'invalidated', 'Аннулирован'
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    two_factor_auth = models.ForeignKey(TwoFactorAuth, on_delete=models.CASCADE, related_name='codes')
    code_type = models.CharField(max_length=10, choices=CodeType.choices)
    
    # Код (зашифрованный)
    encrypted_code = models.CharField(max_length=255)  # Зашифрованный код
    code_hash = models.CharField(max_length=128)  # Хеш для быстрой проверки
    
    # Статус и попытки
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    attempts_used = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    
    # Временные рамки
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    
    # Метаданные
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Код двухфакторной аутентификации'
        verbose_name_plural = 'Коды двухфакторной аутентификации'
        indexes = [
            models.Index(fields=['two_factor_auth', 'status', 'expires_at']),
            models.Index(fields=['uuid']),
        ]
    
    def __str__(self):
        return f"Код {self.code_type} для {self.two_factor_auth.user.email}"
    
    @property
    def is_expired(self):
        """Проверка, истек ли код"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Проверка, действителен ли код"""
        return (
            self.status == self.Status.PENDING and 
            not self.is_expired and 
            self.attempts_used < self.max_attempts
        )
    
    def mark_as_used(self):
        """Отметить код как использованный"""
        self.status = self.Status.USED
        self.used_at = timezone.now()
        self.save(update_fields=['status', 'used_at'])
    
    def mark_as_expired(self):
        """Отметить код как истекший"""
        self.status = self.Status.EXPIRED
        self.save(update_fields=['status'])
    
    def increment_attempts(self):
        """Увеличить счетчик попыток"""
        self.attempts_used += 1
        if self.attempts_used >= self.max_attempts:
            self.status = self.Status.INVALIDATED
        self.save(update_fields=['attempts_used', 'status'])


class TwoFactorBackupCode(models.Model):
    """Модель для резервных кодов"""
    
    two_factor_auth = models.ForeignKey(TwoFactorAuth, on_delete=models.CASCADE, related_name='backup_codes')
    code_hash = models.CharField(max_length=128, unique=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Резервный код'
        verbose_name_plural = 'Резервные коды'
    
    def __str__(self):
        return f"Резервный код для {self.two_factor_auth.user.email}"
    
    def mark_as_used(self):
        """Отметить резервный код как использованный"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class TwoFactorLog(models.Model):
    """Модель для логирования всех попыток 2FA"""
    
    class LogType(models.TextChoices):
        LOGIN_ATTEMPT = 'login_attempt', 'Попытка входа'
        CODE_SENT = 'code_sent', 'Код отправлен'
        CODE_VERIFIED = 'code_verified', 'Код подтвержден'
        CODE_FAILED = 'code_failed', 'Код неверный'
        BACKUP_CODE_USED = 'backup_code_used', 'Использован резервный код'
        TWO_FACTOR_ENABLED = 'two_factor_enabled', '2FA включена'
        TWO_FACTOR_DISABLED = 'two_factor_disabled', '2FA отключена'
        ACCOUNT_LOCKED = 'account_locked', 'Аккаунт заблокирован'
        ACCOUNT_UNLOCKED = 'account_unlocked', 'Аккаунт разблокирован'
    
    class Status(models.TextChoices):
        SUCCESS = 'success', 'Успешно'
        FAILED = 'failed', 'Неудачно'
        WARNING = 'warning', 'Предупреждение'
        INFO = 'info', 'Информация'
    
    two_factor_auth = models.ForeignKey(TwoFactorAuth, on_delete=models.CASCADE, related_name='logs')
    log_type = models.CharField(max_length=25, choices=LogType.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    
    # Детали
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Лог двухфакторной аутентификации'
        verbose_name_plural = 'Логи двухфакторной аутентификации'
        indexes = [
            models.Index(fields=['two_factor_auth', 'log_type', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_log_type_display()} - {self.get_status_display()} ({self.created_at})" 