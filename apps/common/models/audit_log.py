import uuid
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class AuditLog(models.Model):
    """Неизменяемый аудит-лог действий в системе"""

    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'

    class Source(models.TextChoices):
        BACKEND = 'backend', 'Backend'
        ADMIN = 'admin', 'Admin Panel'
        API = 'api', 'API'
        WORKER = 'worker', 'Worker'

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    source = models.CharField(max_length=20, choices=Source.choices, default=Source.BACKEND)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)

    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    action = models.CharField(max_length=100)
    message = models.TextField(blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user']),
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['severity']),
        ]

    def save(self, *args, **kwargs):
        # Журнал неизменяем: запрет на обновление записей
        if self.pk:
            return
        super().save(*args, **kwargs)




