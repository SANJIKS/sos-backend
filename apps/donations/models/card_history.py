import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class DonorCardHistory(models.Model):
    """История изменений карт доноров для отслеживания токенов"""
    
    class ChangeType(models.TextChoices):
        CARD_ADDED = 'card_added', _('Карта добавлена')
        CARD_UPDATED = 'card_updated', _('Карта обновлена')
        CARD_EXPIRED = 'card_expired', _('Карта истекла')
        CARD_REPLACED = 'card_replaced', _('Карта заменена')

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Связь с пожертвованием
    donation = models.ForeignKey(
        'donations.Donation', 
        on_delete=models.CASCADE, 
        related_name='card_history',
        verbose_name=_('Пожертвование')
    )
    
    # Токены карт
    old_card_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('Старый токен карты')
    )
    new_card_token = models.CharField(
        max_length=255, 
        verbose_name=_('Новый токен карты')
    )
    
    # Тип изменения
    change_type = models.CharField(
        max_length=20, 
        choices=ChangeType.choices, 
        verbose_name=_('Тип изменения')
    )
    
    # Дополнительная информация
    change_reason = models.TextField(
        blank=True, 
        verbose_name=_('Причина изменения')
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
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    
    # Salesforce синхронизация
    salesforce_synced = models.BooleanField(
        default=False, 
        verbose_name=_('Синхронизировано с Salesforce')
    )
    salesforce_sync_error = models.TextField(
        blank=True, 
        verbose_name=_('Ошибка синхронизации Salesforce')
    )

    class Meta:
        verbose_name = _('История карты донора')
        verbose_name_plural = _('История карт доноров')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['donation']),
            models.Index(fields=['change_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['salesforce_synced']),
        ]

    def __str__(self):
        return f"{self.donation.donation_code} - {self.get_change_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        # Автоматически определяем тип изменения если не указан
        if not self.change_type:
            if not self.old_card_token:
                self.change_type = self.ChangeType.CARD_ADDED
            else:
                self.change_type = self.ChangeType.CARD_UPDATED
        
        super().save(*args, **kwargs)
