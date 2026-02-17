import logging
from typing import Dict, Optional, Tuple
from django.utils import timezone
from django.core.cache import cache
from ..models import Donation, DonorCardHistory

logger = logging.getLogger(__name__)


class CardManagementService:
    """Сервис для управления картами доноров"""
    
    def __init__(self):
        pass
    
    def update_donor_card(
        self, 
        donation: Donation, 
        new_card_token: str, 
        change_reason: str = "",
        ip_address: str = None,
        user_agent: str = ""
    ) -> Dict:
        """Обновление карты донора с сохранением истории"""
        
        try:
            old_card_token = donation.current_card_token
            
            # Создаем запись в истории
            card_history = DonorCardHistory.objects.create(
                donation=donation,
                old_card_token=old_card_token,
                new_card_token=new_card_token,
                change_reason=change_reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Обновляем текущий токен
            donation.current_card_token = new_card_token
            donation.save()
            
            # Кэшируем информацию об обновлении для Salesforce
            cache_key = f"card_update_{donation.uuid}"
            cache.set(cache_key, {
                'old_token': old_card_token,
                'new_token': new_card_token,
                'history_id': str(card_history.uuid),
                'updated_at': timezone.now().isoformat()
            }, timeout=86400)  # 24 часа
            
            logger.info(f"Updated card token for donation {donation.donation_code}: {old_card_token} -> {new_card_token}")
            
            return {
                'success': True,
                'old_token': old_card_token,
                'new_token': new_card_token,
                'history_id': str(card_history.uuid),
                'message': 'Card token updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to update card token for donation {donation.donation_code}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to update card token'
            }
    
    def get_card_update_info(self, donation: Donation) -> Optional[Dict]:
        """Получение информации об обновлении карты для Salesforce"""
        
        cache_key = f"card_update_{donation.uuid}"
        card_info = cache.get(cache_key)
        
        if card_info:
            # Удаляем из кэша после получения
            cache.delete(cache_key)
            return card_info
        
        return None
    
    def get_card_history(self, donation: Donation) -> list:
        """Получение истории изменений карты"""
        
        return list(donation.card_history.all().order_by('-created_at'))
    
    def validate_card_token(self, card_token: str) -> bool:
        """Валидация токена карты"""
        
        if not card_token:
            return False
        
        # Базовая валидация формата токена
        if len(card_token) < 10:
            return False
        
        return True
    
    def is_card_expired(self, card_token: str) -> bool:
        """Проверка истечения срока действия карты"""
        
        # TODO: Реализовать проверку срока действия карты
        # Пока возвращаем False, так как не храним дату истечения
        return False
    
    def get_active_card_tokens(self, donor_email: str) -> list:
        """Получение активных токенов карт для донора"""
        
        active_donations = Donation.objects.filter(
            donor_email=donor_email,
            is_recurring=True,
            recurring_active=True,
            current_card_token__isnull=False
        ).exclude(current_card_token='')
        
        return [donation.current_card_token for donation in active_donations]
    
    def cleanup_expired_tokens(self) -> int:
        """Очистка истекших токенов карт"""
        
        # TODO: Реализовать очистку истекших токенов
        # Пока возвращаем 0, так как не храним дату истечения
        return 0
