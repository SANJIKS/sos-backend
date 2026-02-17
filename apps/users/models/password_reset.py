import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import secrets
import string

User = get_user_model()


class PasswordResetToken(models.Model):
    """Модель для токенов восстановления пароля"""
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name=_('Пользователь')
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_('Токен')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Создан')
    )
    expires_at = models.DateTimeField(
        verbose_name=_('Истекает')
    )
    used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Использован')
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_('Использован')
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_('IP адрес')
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )

    class Meta:
        verbose_name = _('Токен восстановления пароля')
        verbose_name_plural = _('Токены восстановления пароля')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_used']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Reset token for {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        
        if not self.expires_at:
            # Токен действует 1 час
            self.expires_at = timezone.now() + timedelta(hours=1)
        
        super().save(*args, **kwargs)

    @staticmethod
    def generate_token():
        """Генерация безопасного токена"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))

    @property
    def is_expired(self):
        """Проверка, истек ли токен"""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Проверка, валиден ли токен"""
        return not self.is_used and not self.is_expired

    def mark_as_used(self):
        """Отметить токен как использованный"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])

    @classmethod
    def create_for_user(cls, user, ip_address=None, user_agent=None):
        """Создать токен для пользователя"""
        # Деактивируем все предыдущие токены пользователя
        cls.objects.filter(user=user, is_used=False).update(is_used=True, used_at=timezone.now())
        
        # Создаем новый токен
        return cls.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @classmethod
    def cleanup_expired(cls):
        """Удаление истекших токенов (для периодической очистки)"""
        expired_tokens = cls.objects.filter(expires_at__lt=timezone.now())
        count = expired_tokens.count()
        expired_tokens.delete()
        return count

