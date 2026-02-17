from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
import logging

from .models import Donation, DonationCampaign
from .tasks import (
    sync_donation_to_salesforce,
    sync_campaign_to_salesforce,
    update_salesforce_opportunity_status
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Donation)
def handle_donation_save(sender, instance, created, **kwargs):
    """Обработка сохранения пожертвования"""
    
    # Пропускаем в тестовом режиме
    if getattr(settings, 'TESTING', False):
        return
    
    if created:
        # Новое пожертвование - синхронизируем с Salesforce если статус подходящий
        if instance.status in ['completed', 'processing']:
            logger.info(f"Queuing new donation {instance.donation_code} for Salesforce sync")
            sync_donation_to_salesforce.delay(instance.id)
    else:
        # Обновление существующего пожертвования
        # Проверяем изменение статуса
        if hasattr(instance, '_original_status'):
            old_status = instance._original_status
            new_status = instance.status
            
            if old_status != new_status:
                logger.info(f"Donation {instance.donation_code} status changed from {old_status} to {new_status}")
                
                # Если пожертвование уже синхронизировано, обновляем статус в Salesforce
                if instance.salesforce_synced and instance.salesforce_id:
                    update_salesforce_opportunity_status.delay(instance.id, new_status)
                # Если еще не синхронизировано, но статус подходящий - синхронизируем
                elif new_status in ['completed', 'processing']:
                    sync_donation_to_salesforce.delay(instance.id)


@receiver(post_save, sender=DonationCampaign)
def handle_campaign_save(sender, instance, created, **kwargs):
    """Обработка сохранения кампании"""
    
    # Пропускаем в тестовом режиме
    if getattr(settings, 'TESTING', False):
        return
    
    if created:
        # Новая кампания - синхронизируем с Salesforce если статус подходящий
        if instance.status in ['active']:
            logger.info(f"Queuing new campaign {instance.name} for Salesforce sync")
            sync_campaign_to_salesforce.delay(instance.id)


# Функция для отслеживания изменений статуса
def track_donation_status_changes(sender, instance, **kwargs):
    """Сохраняем оригинальный статус для отслеживания изменений"""
    try:
        instance._original_status = sender.objects.get(pk=instance.pk).status
    except sender.DoesNotExist:
        instance._original_status = None


# Подключаем pre_save сигнал для отслеживания изменений
from django.db.models.signals import pre_save

@receiver(pre_save, sender=Donation)
def donation_pre_save(sender, instance, **kwargs):
    track_donation_status_changes(sender, instance, **kwargs)