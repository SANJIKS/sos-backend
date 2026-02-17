import uuid
import hashlib
import json
from typing import Dict, Optional
from django.utils import timezone
from django.http import HttpRequest
from ..models import RecurringConsentLog, Donation


class ConsentLoggerService:
    """Сервис для логирования согласия на рекуррентные платежи"""
    
    def __init__(self):
        pass
    
    def log_recurring_consent(
        self,
        donation: Donation,
        request: HttpRequest,
        consent_text: str,
        session_id: Optional[str] = None,
        device_info: Optional[Dict] = None
    ) -> RecurringConsentLog:
        """
        Логирует согласие на рекуррентные платежи
        
        Args:
            donation: Объект пожертвования
            request: HTTP запрос
            consent_text: Текст согласия
            session_id: ID сессии (опционально)
            device_info: Информация об устройстве (опционально)
        
        Returns:
            Созданная запись лога согласия
        """
        
        # Генерируем токен подтверждения
        confirmation_token = self._generate_confirmation_token(donation, request)
        
        # Получаем IP адрес
        ip_address = self._get_client_ip(request)
        
        # Получаем User Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Получаем реферер
        referrer = request.META.get('HTTP_REFERER', '')
        
        # Подготавливаем информацию об устройстве
        if device_info is None:
            device_info = self._extract_device_info(request)
        
        # Создаем запись лога
        consent_log = RecurringConsentLog.objects.create(
            donation=donation,
            consent_type=RecurringConsentLog.ConsentType.GRANTED,
            recurring_frequency=donation.donation_type,
            consent_text=consent_text,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id or '',
            confirmation_token=confirmation_token,
            referrer=referrer,
            device_info=device_info,
        )
        
        return consent_log
    
    def log_consent_revocation(
        self,
        donation: Donation,
        request: HttpRequest,
        reason: str = "Отозвано пользователем"
    ) -> RecurringConsentLog:
        """
        Логирует отзыв согласия на рекуррентные платежи
        
        Args:
            donation: Объект пожертвования
            request: HTTP запрос
            reason: Причина отзыва
        
        Returns:
            Созданная запись лога отзыва
        """
        
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        consent_log = RecurringConsentLog.objects.create(
            donation=donation,
            consent_type=RecurringConsentLog.ConsentType.REVOKED,
            recurring_frequency=donation.donation_type,
            consent_text=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id='',
            confirmation_token='',
            referrer='',
            device_info={},
        )
        
        return consent_log
    
    def log_consent_modification(
        self,
        donation: Donation,
        request: HttpRequest,
        old_frequency: str,
        new_frequency: str,
        reason: str = "Изменена частота платежей"
    ) -> RecurringConsentLog:
        """
        Логирует изменение согласия на рекуррентные платежи
        
        Args:
            donation: Объект пожертвования
            request: HTTP запрос
            old_frequency: Старая частота
            new_frequency: Новая частота
            reason: Причина изменения
        
        Returns:
            Созданная запись лога изменения
        """
        
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        consent_log = RecurringConsentLog.objects.create(
            donation=donation,
            consent_type=RecurringConsentLog.ConsentType.MODIFIED,
            recurring_frequency=new_frequency,
            consent_text=f"{reason}: {old_frequency} → {new_frequency}",
            ip_address=ip_address,
            user_agent=user_agent,
            session_id='',
            confirmation_token='',
            referrer='',
            device_info={},
        )
        
        return consent_log
    
    def _generate_confirmation_token(self, donation: Donation, request: HttpRequest) -> str:
        """Генерирует уникальный токен подтверждения"""
        # Создаем уникальную строку на основе данных пожертвования и времени
        unique_string = f"{donation.uuid}_{donation.donor_email}_{timezone.now().isoformat()}"
        
        # Генерируем MD5 хеш
        token = hashlib.md5(unique_string.encode('utf-8')).hexdigest()
        
        return token
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Получает IP адрес клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _extract_device_info(self, request: HttpRequest) -> Dict:
        """Извлекает информацию об устройстве из запроса"""
        device_info = {}
        
        # User Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if user_agent:
            device_info['user_agent'] = user_agent
        
        # Accept Language
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if accept_language:
            device_info['accept_language'] = accept_language
        
        # Accept Encoding
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if accept_encoding:
            device_info['accept_encoding'] = accept_encoding
        
        # DNT (Do Not Track)
        dnt = request.META.get('HTTP_DNT', '')
        if dnt:
            device_info['do_not_track'] = dnt
        
        # Sec-Fetch headers
        sec_fetch_dest = request.META.get('HTTP_SEC_FETCH_DEST', '')
        if sec_fetch_dest:
            device_info['sec_fetch_dest'] = sec_fetch_dest
        
        sec_fetch_mode = request.META.get('HTTP_SEC_FETCH_MODE', '')
        if sec_fetch_mode:
            device_info['sec_fetch_mode'] = sec_fetch_mode
        
        sec_fetch_site = request.META.get('HTTP_SEC_FETCH_SITE', '')
        if sec_fetch_site:
            device_info['sec_fetch_site'] = sec_fetch_site
        
        return device_info
    
    def get_consent_history(self, donation: Donation) -> list:
        """Получает историю согласий для пожертвования"""
        return RecurringConsentLog.objects.filter(donation=donation).order_by('-created_at')
    
    def verify_confirmation_token(self, donation: Donation, token: str) -> bool:
        """Проверяет токен подтверждения"""
        return RecurringConsentLog.objects.filter(
            donation=donation,
            confirmation_token=token,
            consent_type=RecurringConsentLog.ConsentType.GRANTED
        ).exists()
