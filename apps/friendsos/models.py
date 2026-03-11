from django.db import models
from django.utils.translation import gettext_lazy as _


class SOSFriend(models.Model):
    """История друга SOS"""

    name = models.CharField(max_length=255, verbose_name=_('Имя'))
    location = models.CharField(max_length=255, blank=True, verbose_name=_('Город/Регион'))
    photo = models.ImageField(
        upload_to='friends/photos/',
        blank=True,
        null=True,
        verbose_name=_('Фото')
    )
    message = models.TextField(verbose_name=_('Сообщение/Отзыв'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активный'))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок сортировки'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))

    class Meta:
        verbose_name = _('История друга')
        verbose_name_plural = _('Истории наших друзей')
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.location})" if self.location else self.name