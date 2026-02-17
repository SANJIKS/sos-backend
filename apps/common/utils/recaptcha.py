"""
Утилиты для работы с Google reCAPTCHA v2
"""

import requests
import logging
from django.conf import settings
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def verify_recaptcha(recaptcha_response: str, remote_ip: str = None) -> Dict[str, bool]:
    """
    Проверка reCAPTCHA v2 токена
    
    Args:
        recaptcha_response: Токен reCAPTCHA от клиента
        remote_ip: IP адрес клиента (опционально)
    
    Returns:
        Dict с результатом проверки
    """
    # В режиме разработки можно отключить проверку reCAPTCHA
    if getattr(settings, 'DEBUG', False) and getattr(settings, 'SKIP_RECAPTCHA_IN_DEBUG', False):
        logger.info("reCAPTCHA verification skipped in DEBUG mode")
        return {
            'success': True,
            'error': None
        }
    
    if not recaptcha_response:
        return {
            'success': False,
            'error': 'reCAPTCHA token is required'
        }
    
    if not settings.RECAPTCHA_SECRET_KEY:
        logger.warning("RECAPTCHA_SECRET_KEY not configured, skipping verification")
        return {
            'success': True,
            'error': None
        }
    
    try:
        # Подготавливаем данные для запроса
        data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response,
        }
        
        if remote_ip:
            data['remoteip'] = remote_ip
        
        # Отправляем запрос к Google
        response = requests.post(
            settings.RECAPTCHA_VERIFY_URL,
            data=data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                logger.info("reCAPTCHA verification successful")
                return {
                    'success': True,
                    'error': None,
                    'score': result.get('score'),  # Для reCAPTCHA v3
                    'action': result.get('action'),  # Для reCAPTCHA v3
                }
            else:
                error_codes = result.get('error-codes', [])
                logger.warning(f"reCAPTCHA verification failed: {error_codes}")
                
                # Обрабатываем специфичные ошибки
                error_messages = {
                    'missing-input-secret': 'reCAPTCHA secret key is missing',
                    'invalid-input-secret': 'reCAPTCHA secret key is invalid',
                    'missing-input-response': 'reCAPTCHA response is missing',
                    'invalid-input-response': 'reCAPTCHA response is invalid',
                    'bad-request': 'reCAPTCHA request is malformed',
                    'timeout-or-duplicate': 'reCAPTCHA token has expired or already been used',
                }
                
                # Если это timeout-or-duplicate, это не критическая ошибка
                if 'timeout-or-duplicate' in error_codes:
                    logger.info("reCAPTCHA token expired or already used, but allowing request")
                    return {
                        'success': True,
                        'error': None,
                        'warning': 'reCAPTCHA token expired, but request allowed'
                    }
                
                error_message = ', '.join([error_messages.get(code, code) for code in error_codes])
                return {
                    'success': False,
                    'error': f"reCAPTCHA verification failed: {error_message}"
                }
        else:
            logger.error(f"reCAPTCHA verification request failed: {response.status_code}")
            return {
                'success': False,
                'error': f"reCAPTCHA service unavailable: {response.status_code}"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"reCAPTCHA verification request error: {e}")
        return {
            'success': False,
            'error': f"reCAPTCHA verification error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"reCAPTCHA verification unexpected error: {e}")
        return {
            'success': False,
            'error': f"reCAPTCHA verification error: {str(e)}"
        }


def get_recaptcha_site_key() -> str:
    """
    Получение публичного ключа reCAPTCHA для фронтенда
    
    Returns:
        Публичный ключ reCAPTCHA
    """
    return settings.RECAPTCHA_SITE_KEY


def is_recaptcha_configured() -> bool:
    """
    Проверка, настроена ли reCAPTCHA
    
    Returns:
        True если reCAPTCHA настроена
    """
    return bool(settings.RECAPTCHA_SITE_KEY and settings.RECAPTCHA_SECRET_KEY)
