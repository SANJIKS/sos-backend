from django.db import models
from django.utils import timezone
from apps.users.models.user import User


class ConfirmCode(models.Model):
    class ConfirmCodeType(models.TextChoices):
        EMAIL = "email"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="confirm_codes")
    code = models.CharField(max_length=12)
    type = models.CharField(max_length=32, choices=ConfirmCodeType.choices, default=ConfirmCodeType.EMAIL)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at
