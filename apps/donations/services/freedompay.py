import hashlib
import hmac
import json
import uuid
import requests
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class FreedomPayException(Exception):
    """Исключения для работы с FreedomPay"""
    pass


class FreedomPayService:
    """Сервис для работы с платежной системой FreedomPay"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'FREEDOMPAY_BASE_URL', 'https://api.freedompay.kg')
        # Попробуем альтернативный URL если основной не работает
        self.alternative_url = 'https://api.freedompay.kz'
        self.merchant_id = getattr(settings, 'FREEDOMPAY_MERCHANT_ID', '')
        self.secret_key = getattr(settings, 'FREEDOMPAY_SECRET_KEY', '')
        self.test_mode = getattr(settings, 'FREEDOMPAY_TEST_MODE', True)
        self.mock_mode = getattr(settings, 'FREEDOMPAY_MOCK_MODE', False)

        # Проверяем настройки credentials
        if not self.merchant_id or not self.secret_key:
            logger.error("FreedomPay credentials not configured! Please set FREEDOMPAY_MERCHANT_ID and FREEDOMPAY_SECRET_KEY")
            raise FreedomPayException("FreedomPay credentials not configured")
        
        # Проверяем, что это не тестовые credentials
        if self.merchant_id == 'your-real-merchant-id-from-freedompay-kg' or self.secret_key == 'your-real-secret-key-from-freedompay-kg':
            logger.error("FreedomPay credentials are not configured - using example values")
            raise FreedomPayException("FreedomPay credentials are not configured - please set real MERCHANT_ID and SECRET_KEY")
    
        # Согласно документации FreedomPay KG Gateway API
        self.gateway_url = f"{self.base_url}/gateway"
    
    def _generate_signature(self, params: Dict) -> str:
        """Генерация подписи для запроса"""
        # Сортируем параметры по ключам
        sorted_params = sorted(params.items())
        
        # Создаем строку для подписи
        signature_string = '&'.join([f"{k}={v}" for k, v in sorted_params if v is not None])
        
        # Добавляем секретный ключ
        signature_string += f"&{self.secret_key}"
        
        # Генерируем MD5 хеш
        signature = hashlib.md5(signature_string.encode('utf-8')).hexdigest()
        
        logger.debug(f"Signature string: {signature_string}")
        logger.debug(f"Generated signature: {signature}")
        
        return signature
    
    def _generate_freedompay_signature(self, params: Dict, script_name: str = 'init_payment.php') -> str:
        """Генерация подписи для FreedomPay KG согласно рабочему коду"""
        # Строка подписи начинается с имени скрипта
        str_sig = script_name
        
        # Сортируем параметры по ключам в алфавитном порядке
        for key in sorted(params):
            if key != 'pg_sig':
                key_value = params.get(key, None)
                if key_value:
                    str_sig += f';{key_value}'
        
        # Добавляем секретный ключ в конце
        str_sig += f';{self.secret_key}'
        
        # Генерируем MD5 хеш
        signature = hashlib.md5(str_sig.encode('utf-8')).hexdigest()
        
        logger.debug(f"FreedomPay KG signature string: {str_sig}")
        logger.debug(f"Generated pg_sig: {signature}")
        
        return signature
    
    def _generate_gateway_signature(self, params: Dict) -> str:
        """Генерация подписи для Gateway API согласно документации"""
        # Сортируем параметры по ключам
        sorted_params = sorted(params.items())
        
        # Создаем строку для подписи
        signature_string = '&'.join([f"{k}={v}" for k, v in sorted_params if v is not None])
        
        # Добавляем секретный ключ
        signature_string += f"&{self.secret_key}"
        
        # Генерируем MD5 хеш
        signature = hashlib.md5(signature_string.encode('utf-8')).hexdigest()
        
        logger.debug(f"Gateway signature string: {signature_string}")
        logger.debug(f"Generated gateway signature: {signature}")
        
        return signature
    
    def _make_gateway_request(self, endpoint: str, data: Dict, method: str = 'POST') -> Dict:
        """Выполнение HTTP запроса к FreedomPay Gateway API"""
        
        # Проверяем, что credentials настроены
        if not self.merchant_id or not self.secret_key:
            raise FreedomPayException("FreedomPay credentials not configured")
        
        url = f"{self.gateway_url}{endpoint}"
        logger.info(f"Making FreedomPay Gateway API request to: {url}")
        logger.info(f"Request data: {data}")
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                response = requests.get(url, params=data, headers=headers, timeout=30)
            
            response.raise_for_status()
            
            # Логируем сырой ответ для отладки
            logger.info(f"FreedomPay Gateway response status: {response.status_code}")
            logger.info(f"FreedomPay Gateway response: {response.text[:500]}...")
            
            result = response.json()
            logger.info(f"FreedomPay Gateway JSON response: {result}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FreedomPay Gateway API request failed: {e}")
            raise FreedomPayException(f"Gateway API request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse FreedomPay Gateway response: {e}")
            raise FreedomPayException(f"Invalid Gateway API response: {e}")
    
    def _parse_xml_response(self, response_text: str) -> Dict:
        """Парсинг XML ответа от FreedomPay KG"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(response_text)
            result = {}
            
            for child in root:
                result[child.tag] = child.text
            
            logger.info(f"Parsed XML response: {result}")
            return result
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML response: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            return {
                'pg_status': 'error',
                'pg_error_description': 'Invalid XML response from FreedomPay'
            }
    
    def _parse_freedompay_response(self, response_text: str) -> Dict:
        """Парсинг ответа от FreedomPay KG"""
        import re
        
        # Ищем параметры в формате pg_parameter=value
        params = {}
        
        # Регулярное выражение для поиска параметров
        pattern = r'pg_(\w+)=([^\s&]+)'
        matches = re.findall(pattern, response_text)
        
        for param_name, param_value in matches:
            params[f'pg_{param_name}'] = param_value
        
        # Если не нашли параметры, пробуем парсить как HTML
        if not params:
            # Ищем в HTML формах
            form_pattern = r'<input[^>]*name="pg_(\w+)"[^>]*value="([^"]*)"'
            form_matches = re.findall(form_pattern, response_text)
            
            for param_name, param_value in form_matches:
                params[f'pg_{param_name}'] = param_value
        
        # Если все еще нет параметров, возвращаем базовую структуру
        if not params:
            logger.warning(f"Could not parse FreedomPay response: {response_text[:200]}...")
            return {
                'pg_status': 'error',
                'pg_error_description': 'Unable to parse response from FreedomPay'
            }
        
        logger.info(f"Parsed FreedomPay parameters: {params}")
        return params
    
    def create_any_amount_payment(self, donation) -> Dict:
        """Создание платежа с произвольной суммой согласно документации FreedomPay KG"""
        
        # Генерируем уникальный order_id
        order_id = f"DON_{donation.donation_code}_{int(timezone.now().timestamp())}"
        
        # Согласно документации - используем any_amount.php для произвольной суммы
        payment_data = {
            'pg_order_id': order_id,
            'pg_merchant_id': self.merchant_id,
            'pg_amount': str(int(donation.amount)),  # Сумма в тийинах
            'pg_currency': 'KGS',  # Согласно документации - валюта Кыргызстана
            'pg_description': self._get_payment_description(donation),
            'pg_success_url': self._get_return_url(donation),
            'pg_failure_url': self._get_return_url(donation),
            'pg_result_url': self._get_notify_url(),
            'pg_user_ip': self._get_client_ip(),  # Получаем реальный IP адрес
            'pg_testing_mode': '1' if self.test_mode else '0',
        }
        
        # Добавляем подпись для FreedomPay KG
        payment_data['pg_salt'] = str(uuid.uuid4())
        payment_data['pg_sig'] = self._generate_freedompay_signature(payment_data, 'any_amount.php')
        
        try:
            # Используем any_amount.php для произвольной суммы
            result = self._make_request('/any_amount.php', payment_data)
            
            # Кэшируем информацию о платеже
            cache_key = f"freedompay_payment_{order_id}"
            cache.set(cache_key, {
                'donation_uuid': str(donation.uuid),
                'order_id': order_id,
                'amount': str(donation.amount),
                'currency': donation.currency,
                'created_at': timezone.now().isoformat(),
            }, timeout=3600)  # Кэш на 1 час
            
            # Обрабатываем ответ от FreedomPay KG
            if result.get('pg_status') == 'ok':
                return {
                    'success': True,
                    'payment_url': result.get('pg_redirect_url'),
                    'order_id': order_id,
                    'payment_id': result.get('pg_payment_id'),
                    'message': 'Payment page created successfully',
                }
            else:
                error_message = result.get('pg_error_description', 'Payment creation failed')
                logger.error(f"FreedomPay any_amount payment creation failed: {error_message}")
                
                return {
                    'success': False,
                    'error': error_message,
                    'message': f"FreedomPay error: {error_message}",
                }
                
        except Exception as e:
            logger.error(f"Failed to create FreedomPay any_amount payment: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create any_amount payment',
            }
    
    def get_test_cards(self) -> Dict:
        """Получение тестовых карт для разработки (отключено для продакшена)"""
        if self.test_mode:
            return {
                'success_cards': [
                    {
                        'number': '4111111111111111',
                        'cvv': '123',
                        'expiry': '12/25',
                        'description': 'Успешная оплата'
                    },
                    {
                        'number': '5555555555554444',
                        'cvv': '123',
                        'expiry': '12/25',
                        'description': 'Успешная оплата (Mastercard)'
                    }
                ],
                'failure_cards': [
                    {
                        'number': '4000000000000002',
                        'cvv': '123',
                        'expiry': '12/25',
                        'description': 'Отклоненная карта'
                    },
                    {
                        'number': '4000000000000069',
                        'cvv': '123',
                        'expiry': '12/25',
                        'description': 'Истекшая карта'
                    }
                ],
                'test_phone_numbers': [
                    '+996555123456',
                    '+996555654321'
                ]
            }
        else:
            return {
                'message': 'Test cards are only available in test mode',
                'test_mode': False
            }
    
    def check_payment_status(self, order_id: str) -> Dict:
        """Проверка статуса платежа согласно документации FreedomPay KG"""
        
        params = {
            'pg_order_id': order_id,
            'pg_merchant_id': self.merchant_id,
        }
        
        # Добавляем подпись
        params['pg_salt'] = str(uuid.uuid4())
        params['pg_sig'] = self._generate_freedompay_signature(params, 'get_status3.php')
        
        try:
            # Используем get_status3.php согласно документации
            result = self._make_request('/get_status3.php', params, method='POST')
            
            return {
                'success': True,
                'status': result.get('pg_payment_status', result.get('pg_status')),
                'payment_id': result.get('pg_payment_id'),
                'amount': result.get('pg_amount'),
                'currency': result.get('pg_currency'),
                'payment_method': result.get('pg_payment_method'),
                'can_reject': result.get('pg_can_reject'),
                'clearing_amount': result.get('pg_clearing_amount'),
                'reference': result.get('pg_reference'),
                'card_name': result.get('pg_card_name'),
                'card_pan': result.get('pg_card_pan'),
                'card_token': result.get('pg_card_token'),
                'payment_date': result.get('pg_payment_date'),
                'message': result.get('pg_failure_description', ''),
            }
            
        except Exception as e:
            logger.error(f"Failed to check FreedomPay payment status: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to check payment status',
            }
    
    def _make_request(self, endpoint: str, data: Dict, method: str = 'POST') -> Dict:
        """Выполнение HTTP запроса к FreedomPay API"""
        
        # Проверяем, что credentials настроены
        if not self.merchant_id or not self.secret_key:
            raise FreedomPayException("FreedomPay credentials not configured")
        
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Making FreedomPay KG request to: {url}")
        logger.info(f"Request data: {data}")
        logger.info(f"Merchant ID: {self.merchant_id}")
        logger.info(f"Test mode: {self.test_mode}")
        logger.info(f"Signature string: {self._generate_freedompay_signature(data, 'init_payment.php')}")
        
        
        # Попробуем разные форматы данных
        formats_to_try = [
            {
                'headers': {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/xml,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'User-Agent': 'SOS-KG-Donation-System/1.0',
                },
                'data_func': lambda: data,
                'name': 'form-urlencoded'
            },
            {
                'headers': {
                    'Content-Type': 'application/json',
                    'Accept': 'application/xml,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'User-Agent': 'SOS-KG-Donation-System/1.0',
                },
                'data_func': lambda: json.dumps(data),
                'name': 'json'
            },
            {
                'headers': {
                    'Content-Type': 'multipart/form-data',
                    'Accept': 'application/xml,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'User-Agent': 'SOS-KG-Donation-System/1.0',
                },
                'data_func': lambda: {key: (None, str(value)) for key, value in data.items()},
                'name': 'multipart'
            }
        ]
        
        response = None
        last_error = None
        
        for format_config in formats_to_try:
            try:
                logger.info(f"Trying format: {format_config['name']}")
                headers = format_config['headers']
                data_to_send = format_config['data_func']()
                
                if method == 'POST':
                    if format_config['name'] == 'multipart':
                        response = requests.post(url, files=data_to_send, headers=headers, timeout=30)
                    else:
                        response = requests.post(url, data=data_to_send, headers=headers, timeout=30)
                else:
                    response = requests.get(url, params=data_to_send, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"Success with format: {format_config['name']}")
                    break
                    
            except Exception as e:
                logger.warning(f"Failed with format {format_config['name']}: {e}")
                last_error = e
                continue
        
        if not response:
            raise FreedomPayException(f"All formats failed. Last error: {last_error}")
            
        # Логируем сырой ответ для отладки
        logger.info(f"FreedomPay raw response status: {response.status_code}")
        logger.info(f"FreedomPay response headers: {dict(response.headers)}")
        logger.info(f"FreedomPay response content type: {response.headers.get('content-type', 'unknown')}")
        logger.info(f"FreedomPay response content: {response.text}")  # Полный ответ для отладки
        
        # Проверяем статус ответа
        if response.status_code != 200:
            logger.error(f"FreedomPay API returned error status {response.status_code}")
            logger.error(f"Response content: {response.text}")
            raise FreedomPayException(f"FreedomPay API error: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        
        # Пытаемся парсить как JSON
        try:
            # FreedomPay KG возвращает XML, а не JSON
            result = self._parse_xml_response(response.text)
            logger.info(f"FreedomPay XML response: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to parse FreedomPay XML response: {e}")
            # Если не XML, парсим как HTML или текст
            result = self._parse_freedompay_response(response.text)
            logger.info(f"FreedomPay fallback parsed response: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FreedomPay API request failed: {e}")
            raise FreedomPayException(f"API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in FreedomPay request: {e}")
            raise FreedomPayException(f"Unexpected error: {e}")
    
    
    def create_payment(self, donation) -> Dict:
        """Создание платежа через FreedomPay KG согласно документации"""
        
        logger.info(f"Creating FreedomPay payment for donation: {donation.donation_code}")
        logger.info(f"Donation amount: {donation.amount} {donation.currency}")
        logger.info(f"Donation type: {donation.donation_type}")
        logger.info(f"Merchant ID: {self.merchant_id}")
        logger.info(f"Test mode: {self.test_mode}")
        
        # Генерируем уникальный order_id
        order_id = f"DON_{donation.donation_code}_{int(timezone.now().timestamp())}"
        logger.info(f"Generated order_id: {order_id}")
        
        # Согласно документации FreedomPay KG - используем init_payment.php
        payment_data = {
            'pg_order_id': order_id,
            'pg_merchant_id': self.merchant_id,
            'pg_amount': str(int(donation.amount)),  # Сумма в тийинах (требование FreedomPay)
            'pg_currency': 'KGS',  # Используем KZT, так как FreedomPay может не поддерживать KGS
            'pg_description': self._get_payment_description(donation),
            'pg_success_url': self._get_return_url(donation),
            'pg_failure_url': self._get_return_url(donation),
            'pg_result_url': self._get_notify_url(),
            'pg_user_ip': self._get_client_ip(),  # Получаем реальный IP адрес
            'pg_testing_mode': '1' if self.test_mode else '0',
        }
        
        # Добавляем дополнительные параметры согласно рабочему коду
        payment_data['pg_language'] = 'ru'  # Язык интерфейса
        payment_data['pg_lifetime'] = '86400'  # Время жизни платежа (24 часа)
        payment_data['pg_request_method'] = 'POST'  # Метод запроса для result_url
        payment_data['pg_success_url_method'] = 'GET'  # Метод для success_url
        payment_data['pg_failure_url_method'] = 'GET'  # Метод для failure_url
        
        # Добавляем параметры пользователя если есть
        if donation.donor_phone:
            payment_data['pg_user_phone'] = donation.donor_phone
        if donation.donor_email:
            payment_data['pg_user_contact_email'] = donation.donor_email
        
        # Для рекуррентных платежей добавляем параметры сохранения карты
        if donation.is_recurring:
            payment_data['pg_recurring_start'] = '1'
            payment_data['pg_recurring_lifetime'] = '12'  # 12 месяцев
        
        # Добавляем подпись для FreedomPay KG
        payment_data['pg_salt'] = str(uuid.uuid4())
        
        # Логируем данные перед генерацией подписи
        logger.info(f"Payment data before signature: {payment_data}")
        logger.info(f"Result URL: {payment_data.get('pg_result_url')}")
        logger.info(f"Success URL: {payment_data.get('pg_success_url')}")
        logger.info(f"Failure URL: {payment_data.get('pg_failure_url')}")
        
        
        payment_data['pg_sig'] = self._generate_freedompay_signature(payment_data, 'init_payment.php')
        
        # Логируем финальные данные
        logger.info(f"Final payment data with signature: {payment_data}")
        
        
        
        
        try:
            # Используем init_payment.php согласно документации FreedomPay KG
            
            # Попробуем разные endpoints
            endpoints_to_try = ['/init_payment.php', '/init_payment', '/payment/init']
            
            result = None
            last_error = None
            
            # Попробуем разные базовые URL и endpoints
            base_urls_to_try = [self.base_url, self.alternative_url]
            
            for base_url in base_urls_to_try:
                for endpoint in endpoints_to_try:
                    try:
                        logger.info(f"Trying {base_url}{endpoint}")
                        # Временно меняем base_url
                        original_base_url = self.base_url
                        self.base_url = base_url
                        
                        result = self._make_request(endpoint, payment_data)
                        if result and result.get('pg_status') == 'ok':
                            logger.info(f"Success with {base_url}{endpoint}")
                            break
                            
                        # Восстанавливаем оригинальный URL
                        self.base_url = original_base_url
                        
                    except Exception as e:
                        logger.warning(f"Failed with {base_url}{endpoint}: {e}")
                        last_error = e
                        # Восстанавливаем оригинальный URL
                        self.base_url = original_base_url
                        continue
                
                if result and result.get('pg_status') == 'ok':
                    break
            
            if not result:
                raise FreedomPayException(f"All endpoints failed. Last error: {last_error}")
            
            # Кэшируем информацию о платеже
            cache_key = f"freedompay_payment_{order_id}"
            cache.set(cache_key, {
                'donation_uuid': str(donation.uuid),
                'order_id': order_id,
                'amount': str(donation.amount),
                'currency': donation.currency,
                'created_at': timezone.now().isoformat(),
            }, timeout=3600)  # Кэш на 1 час
            
            # Обрабатываем ответ от FreedomPay KG согласно документации
            
            if result.get('pg_status') == 'ok':
                # Создаем транзакцию
                from ..models import DonationTransaction
                
                # Проверяем, существует ли уже транзакция с таким transaction_id
                transaction, created = DonationTransaction.objects.get_or_create(
                    transaction_id=order_id,
                    defaults={
                        'donation': donation,
                        'external_transaction_id': result.get('pg_payment_id', ''),
                        'amount': donation.amount,
                        'currency': donation.currency,
                        'status': 'pending',
                        'transaction_type': 'payment',
                        'payment_gateway': 'freedompay',
                        'gateway_response': result,
                    }
                )
                
                if created:
                    logger.info(f"Created new FreedomPay transaction: {transaction.transaction_id}")
                    # Если это первый платеж в рекуррентной подписке, сохраняем order_id как parent_order_id
                    if donation.is_recurring and not donation.parent_order_id:
                        donation.parent_order_id = order_id
                        donation.save(update_fields=['parent_order_id'])
                        logger.info(f"Set parent_order_id for recurring donation: {donation.donation_code} -> {order_id}")
                else:
                    logger.info(f"Using existing FreedomPay transaction: {transaction.transaction_id}")
                    
                    # Если транзакция уже успешна, возвращаем существующий payment_url
                    if transaction.status == 'success':
                        logger.info(f"Transaction {transaction.transaction_id} already completed successfully")
                        return {
                            'success': True,
                            'payment_url': result['payment_url'],
                            'transaction_id': transaction.transaction_id,
                            'order_id': order_id,
                            'donation_uuid': str(donation.uuid),
                            'message': 'Payment already completed',
                        }
                    
                    # Обновляем данные существующей транзакции
                    transaction.donation = donation
                    transaction.external_transaction_id = result.get('payment_id', '')
                    transaction.amount = donation.amount
                    transaction.currency = donation.currency
                    transaction.status = 'pending'
                    transaction.transaction_type = 'payment'
                    transaction.payment_gateway = 'freedompay'
                    transaction.gateway_response = result
                    transaction.save()
            
                return {
                    'success': True,
                    'payment_url': result.get('pg_redirect_url'),
                    'order_id': order_id,
                    'payment_id': result.get('pg_payment_id'),
                    'transaction_id': transaction.transaction_id,
                    'message': 'Payment created successfully',
                }
            else:
                error_message = result.get('pg_error_description', 'Payment creation failed')
                logger.error(f"FreedomPay payment creation failed: {error_message}")
                logger.error(f"Full FreedomPay response: {result}")
                
                # Проверяем специфичные ошибки
                if ('timeout' in error_message.lower() or 
                    'duplicate' in error_message.lower() or
                    'повторите попытку позже' in error_message.lower()):
                    logger.warning(f"FreedomPay retry error, but allowing request: {error_message}")
                    return {
                        'success': True,
                        'payment_url': result.get('pg_redirect_url', ''),
                        'order_id': order_id,
                        'payment_id': result.get('pg_payment_id', ''),
                        'message': 'Payment created with warning',
                    }
                
                return {
                    'success': False,
                    'error': error_message,
                    'message': f"FreedomPay error: {error_message}",
                }
            
        except Exception as e:
            logger.error(f"Failed to create FreedomPay payment: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create payment',
            }
    
    def check_payment_status(self, order_id: str) -> Dict:
        """Проверка статуса платежа"""
        
        params = {
            'merchant_id': self.merchant_id,
            'order_id': order_id,
        }
        
        params['signature'] = self._generate_signature(params)
        
        try:
            result = self._make_request('/payment/status', params, method='GET')
            
            return {
                'success': True,
                'status': result.get('status'),
                'payment_id': result.get('payment_id'),
                'amount': result.get('amount'),
                'currency': result.get('currency'),
                'paid_at': result.get('paid_at'),
                'message': result.get('message', ''),
            }
            
        except Exception as e:
            logger.error(f"Failed to check FreedomPay payment status: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to check payment status',
            }
    
    def process_webhook(self, webhook_data: Dict) -> Dict:
        """Обработка webhook уведомления от FreedomPay KG"""
        
        # Создаем копию для проверки подписи, чтобы не изменять исходные данные
        webhook_data_copy = webhook_data.copy()
        
        # Проверяем подпись для FreedomPay KG согласно рабочему коду
        received_signature = webhook_data_copy.pop('pg_sig', '')
        calculated_signature = self._generate_freedompay_signature(webhook_data_copy, 'result')
        
        if received_signature != calculated_signature:
            logger.warning(f"Invalid FreedomPay KG webhook signature: {received_signature} != {calculated_signature}")
            raise FreedomPayException("Invalid webhook signature")
        
        order_id = webhook_data.get('pg_order_id')
        payment_id = webhook_data.get('pg_payment_id')
        amount = webhook_data.get('pg_amount')
        currency = webhook_data.get('pg_currency')
        result = webhook_data.get('pg_result')  # 1 - success, 0 - failure, 2 - not completed
        payment_date = webhook_data.get('pg_payment_date')
        can_reject = webhook_data.get('pg_can_reject')
        
        # Определяем статус по pg_result
        if result == '1':
            status = 'ok'
        elif result == '0':
            status = 'error'
        else:
            status = 'pending'
        
        logger.info(f"Processing FreedomPay KG webhook: order_id={order_id}, result={result}, status={status}")
        
        # Получаем токен карты и recurring_profile_id если есть
        card_token = webhook_data.get('pg_card_token')
        recurring_profile_id = webhook_data.get('pg_recurring_profile') or webhook_data.get('pg_recurring_profile_id')
        
        return {
            'order_id': order_id,
            'status': status,
            'payment_id': payment_id,
            'amount': Decimal(amount) if amount else None,  # Сумма уже в сомах
            'currency': currency,
            'paid_at': payment_date,
            'can_reject': can_reject,
            'card_token': card_token,
            'recurring_profile_id': recurring_profile_id,
            'message': webhook_data.get('pg_description', ''),
        }
    
    def make_webhook_response(self, pg_status='ok', pg_description='Платёж принят.'):
        """Создание ответа для webhook согласно рабочему коду"""
        response_dict = {
            'pg_status': pg_status,
            'pg_description': pg_description,
            'pg_salt': str(uuid.uuid4()),
        }
        response_dict['pg_sig'] = self._generate_freedompay_signature(response_dict)
        return response_dict
    
    def create_recurring_payment(self, donation, card_token: str) -> Dict:
        """Создание рекуррентного платежа"""
        
        order_id = f"REC_{donation.donation_code}_{int(timezone.now().timestamp())}"
        
        # Для рекуррентных платежей используем тот же API, что и для обычных платежей
        # но с дополнительными параметрами для рекуррентности
        params = {
            'pg_merchant_id': self.merchant_id,
            'pg_order_id': order_id,
            'pg_amount': str(int(donation.amount)),
            'pg_currency': donation.currency,
            'pg_description': f"Recurring donation - {self._get_payment_description(donation)}",
            'pg_salt': str(uuid.uuid4()),
            'pg_user_phone': donation.donor_phone or '',
            'pg_user_contact_email': donation.donor_email or '',
            'pg_language': 'ru',
            'pg_lifetime': 86400,
            'pg_request_method': 'POST',
            'pg_success_url_method': 'GET',
            'pg_failure_url_method': 'GET',
            'pg_result_url': self._get_notify_url(),
            'pg_success_url': self._get_return_url(),
            'pg_failure_url': self._get_return_url(),
            'pg_recurring_start': '1',  # Флаг для начала рекуррентного платежа
            'pg_recurring_lifetime': '12',  # Срок действия рекуррентного профиля (12 месяцев)
            'pg_card_token': card_token,  # Токен карты для рекуррентного платежа
        }
        
        # Генерируем подпись
        params['pg_sig'] = self._generate_freedompay_signature(params)
        
        try:
            result = self._make_request('/init_payment.php', params)
            
            if result.get('pg_status') == 'ok':
                return {
                    'success': True,
                    'order_id': order_id,
                    'payment_id': result.get('pg_payment_id'),
                    'payment_url': result.get('pg_redirect_url'),
                    'status': result.get('pg_status'),
                    'message': 'Recurring payment processed',
                }
            else:
                return {
                    'success': False,
                    'error': result.get('pg_error_description', 'Recurring payment failed'),
                    'message': 'Failed to process recurring payment',
                }
            
        except Exception as e:
            logger.error(f"Failed to process recurring payment: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process recurring payment',
            }
    
    def card_init(self, donation, card_token: str) -> Dict:
        """Инициализация платежа с токеном карты для без-акцептного списания
        
        Используется для первого платежа в рекуррентной подписке.
        Сохраняет карту и получает токен для последующих платежей.
        """
        order_id = f"INIT_{donation.donation_code}_{int(timezone.now().timestamp())}"
        
        params = {
            'pg_merchant_id': self.merchant_id,
            'pg_order_id': order_id,
            'pg_amount': str(int(donation.amount)),
            'pg_currency': donation.currency or 'KGS',
            'pg_description': self._get_payment_description(donation),
            'pg_salt': str(uuid.uuid4()),
            'pg_card_token': card_token,
            'pg_result_url': self._get_notify_url(),
            'pg_success_url': self._get_return_url(donation),
            'pg_failure_url': self._get_return_url(donation),
            'pg_request_method': 'POST',
            'pg_success_url_method': 'GET',
            'pg_failure_url_method': 'GET',
        }
        
        # Добавляем параметры пользователя если есть
        if donation.donor_phone:
            params['pg_user_phone'] = donation.donor_phone
        if donation.donor_email:
            params['pg_user_contact_email'] = donation.donor_email
        
        # Для рекуррентных платежей добавляем параметры сохранения карты
        if donation.is_recurring:
            params['pg_recurring_start'] = '1'
            params['pg_recurring_lifetime'] = '12'  # 12 месяцев
        
        # Генерируем подпись
        params['pg_sig'] = self._generate_freedompay_signature(params, 'card/init')
        
        try:
            result = self._make_request('/card/init', params)
            
            if result.get('pg_status') == 'ok':
                return {
                    'success': True,
                    'order_id': order_id,
                    'payment_id': result.get('pg_payment_id'),
                    'recurring_profile_id': result.get('pg_recurring_profile_id'),
                    'card_token': result.get('pg_card_token'),
                    'status': result.get('pg_status'),
                    'message': 'Card initialization successful',
                }
            else:
                return {
                    'success': False,
                    'error': result.get('pg_error_description', 'Card initialization failed'),
                    'message': 'Failed to initialize card payment',
                }
                
        except Exception as e:
            logger.error(f"Failed to initialize card payment: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to initialize card payment',
            }
    
    def card_direct(self, donation, card_token: str) -> Dict:
        """Прямое списание средств с карты без-акцептно
        
        Используется для последующих платежей в рекуррентной подписке.
        Требует токен карты, полученный при card_init.
        """
        order_id = f"DIRECT_{donation.donation_code}_{int(timezone.now().timestamp())}"
        
        params = {
            'pg_merchant_id': self.merchant_id,
            'pg_order_id': order_id,
            'pg_amount': str(int(donation.amount)),
            'pg_currency': donation.currency or 'KGS',
            'pg_description': f"Recurring payment - {self._get_payment_description(donation)}",
            'pg_salt': str(uuid.uuid4()),
            'pg_card_token': card_token,
            'pg_result_url': self._get_notify_url(),
            'pg_request_method': 'POST',
        }
        
        # Генерируем подпись
        params['pg_sig'] = self._generate_freedompay_signature(params, 'card/direct')
        
        try:
            result = self._make_request('/card/direct', params)
            
            if result.get('pg_status') == 'ok':
                return {
                    'success': True,
                    'order_id': order_id,
                    'payment_id': result.get('pg_payment_id'),
                    'status': result.get('pg_status'),
                    'message': 'Direct payment successful',
                }
            else:
                return {
                    'success': False,
                    'error': result.get('pg_error_description', 'Direct payment failed'),
                    'message': 'Failed to process direct payment',
                }
                
        except Exception as e:
            logger.error(f"Failed to process direct payment: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process direct payment',
            }
    
    def make_recurring_payment(self, donation, recurring_profile_id: int, amount: Optional[Decimal] = None) -> Dict:
        """Создание рекуррентного платежа используя pg_recurring_profile
        
        Используется для без-акцептного списания с использованием
        сохраненного рекуррентного профиля.
        """
        order_id = f"REC_{donation.donation_code}_{int(timezone.now().timestamp())}"
        
        params = {
            'pg_merchant_id': self.merchant_id,
            'pg_recurring_profile': recurring_profile_id,
            'pg_description': f"Recurring payment - {self._get_payment_description(donation)}",
            'pg_order_id': order_id,
            'pg_amount': str(int(amount or donation.amount)),
            'pg_salt': str(uuid.uuid4()),
            'pg_result_url': self._get_notify_url(),
            'pg_request_method': 'POST',
        }
        
        # Генерируем подпись
        params['pg_sig'] = self._generate_freedompay_signature(params, 'make_recurring_payment')
        
        try:
            result = self._make_request('/make_recurring_payment', params)
            
            if result.get('pg_status') == 'ok':
                return {
                    'success': True,
                    'order_id': order_id,
                    'payment_id': result.get('pg_payment_id'),
                    'status': result.get('pg_status'),
                    'message': 'Recurring payment processed successfully',
                }
            else:
                return {
                    'success': False,
                    'error': result.get('pg_error_description', 'Recurring payment failed'),
                    'message': 'Failed to process recurring payment',
                }
                
        except Exception as e:
            logger.error(f"Failed to process recurring payment: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process recurring payment',
            }
    
    def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict:
        """Возврат платежа"""
        
        params = {
            'merchant_id': self.merchant_id,
            'payment_id': payment_id,
        }
        
        if amount:
            params['amount'] = str(int(amount))  # Частичный возврат в сомах
        
        params['signature'] = self._generate_signature(params)
        
        try:
            result = self._make_request('/payment/refund', params)
            
            return {
                'success': True,
                'refund_id': result.get('refund_id'),
                'status': result.get('status'),
                'amount': result.get('amount'),
                'message': 'Refund processed successfully',
            }
            
        except Exception as e:
            logger.error(f"Failed to process refund: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process refund',
            }
    
    def get_payment_methods(self) -> Dict:
        """Получение доступных способов оплаты"""
        
        params = {
            'merchant_id': self.merchant_id,
        }
        
        params['signature'] = self._generate_signature(params)
        
        try:
            result = self._make_request('/payment/methods', params, method='GET')
            
            return {
                'success': True,
                'methods': result.get('methods', []),
                'message': 'Payment methods retrieved successfully',
            }
            
        except Exception as e:
            logger.error(f"Failed to get payment methods: {e}")
            return {
                'success': False,
                'error': str(e),
                'methods': [],
                'message': 'Failed to get payment methods',
            }
    
    def _get_payment_description(self, donation) -> str:
        """Генерация описания платежа"""
        if donation.campaign:
            return f"Пожертвование на кампанию: {donation.campaign.name}"
        else:
            return "Пожертвование в фонд SOS Детские деревни Кыргызстана"
    
    def _get_return_url(self, donation) -> str:
        """URL для возврата после оплаты"""
        base_url = getattr(settings, 'SITE_URL', 'https://sos-kyrgyzstan.org')
        return f"https://sos-nomadpro.vercel.app/ru"
    
    def _get_notify_url(self) -> str:
        """URL для webhook уведомлений"""
        # Для тестирования можно переопределить URL
        webhook_url = getattr(settings, 'FREEDOMPAY_WEBHOOK_URL', None)
        if webhook_url:
            logger.info(f"Using custom webhook URL: {webhook_url}")
            return webhook_url
            
        base_url = getattr(settings, 'SITE_URL', 'https://sos-kyrgyzstan.org')
        notify_url = f"{base_url}/api/v1/donations/freedompay/webhook/"
        logger.info(f"Generated notify URL: {notify_url}")
        return notify_url
    
    def _get_client_ip(self) -> str:
        """Получение IP адреса клиента"""
        # Для тестирования используем публичный IP
        # В продакшене это должно быть получено из запроса
        return getattr(settings, 'FREEDOMPAY_CLIENT_IP', '8.8.8.8')


class FreedomPayRecurringService:
    """Сервис для управления рекуррентными платежами FreedomPay"""
    
    def __init__(self):
        self.freedompay = FreedomPayService()
    
    def setup_recurring_payment(self, donation):
        """Настройка рекуррентного платежа"""
        from ..models import DonationTransaction
        
        try:
            # Создаем первоначальный платеж с сохранением карты
            result = self.freedompay.create_payment(donation)
            
            if result['success']:
                # Проверяем, существует ли уже транзакция с таким transaction_id
                transaction_id = result['order_id']
                transaction, created = DonationTransaction.objects.get_or_create(
                    transaction_id=transaction_id,
                    defaults={
                        'donation': donation,
                        'external_transaction_id': result.get('payment_id', ''),
                        'amount': donation.amount,
                        'currency': donation.currency,
                        'status': 'pending',
                        'transaction_type': 'payment',
                        'payment_gateway': 'freedompay',
                        'gateway_response': result,
                    }
                )
                
                if created:
                    logger.info(f"Created new FreedomPay transaction: {transaction.transaction_id}")
                    # Если это первый платеж в рекуррентной подписке, сохраняем order_id как parent_order_id
                    if donation.is_recurring and not donation.parent_order_id:
                        donation.parent_order_id = transaction_id
                        donation.save(update_fields=['parent_order_id'])
                        logger.info(f"Set parent_order_id for recurring donation: {donation.donation_code} -> {transaction_id}")
                else:
                    logger.info(f"Using existing FreedomPay transaction: {transaction.transaction_id}")
                    
                    # Если транзакция уже успешна, возвращаем существующий payment_url
                    if transaction.status == 'success':
                        logger.info(f"Transaction {transaction.transaction_id} already completed successfully")
                        return {
                            'success': True,
                            'payment_url': result['payment_url'],
                            'transaction_id': transaction.transaction_id,
                            'donation_uuid': str(donation.uuid),
                            'message': 'Payment already completed',
                        }
                    
                    # Обновляем данные существующей транзакции
                    transaction.donation = donation
                    transaction.external_transaction_id = result.get('payment_id', '')
                    transaction.amount = donation.amount
                    transaction.currency = donation.currency
                    transaction.status = 'pending'
                    transaction.transaction_type = 'payment'
                    transaction.payment_gateway = 'freedompay'
                    transaction.gateway_response = result
                    transaction.save()
                
                return {
                    'success': True,
                    'payment_url': result['payment_url'],
                    'transaction_id': transaction.transaction_id,
                    'order_id': transaction_id,  # Возвращаем order_id
                    'donation_uuid': str(donation.uuid),
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Failed to setup recurring payment: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to setup recurring payment',
            }
    
    def process_recurring_payment(self, donation, card_token: str = None):
        """Обработка рекуррентного платежа с использованием без-акцептного списания
        
        Использует:
        1. make_recurring_payment с recurring_profile_id (приоритет) - если есть recurring_profile_id
        2. card_direct с card_token - если есть card_token
        3. card_init с card_token - если нет ни того, ни другого (для первого платежа)
        """
        from ..models import DonationTransaction
        
        try:
            # Приоритет 1: используем recurring_profile_id если есть
            if donation.recurring_profile_id:
                logger.info(f"Using recurring_profile_id for donation: {donation.donation_code}")
                result = self.freedompay.make_recurring_payment(
                    donation, 
                    donation.recurring_profile_id
                )
            # Приоритет 2: используем card_token для card/direct
            elif card_token or donation.current_card_token:
                card_token_to_use = card_token or donation.current_card_token
                logger.info(f"Using card_token for card/direct for donation: {donation.donation_code}")
                result = self.freedompay.card_direct(donation, card_token_to_use)
            else:
                logger.error(f"No card_token or recurring_profile_id for donation: {donation.donation_code}")
                return {
                    'success': False,
                    'error': 'No card_token or recurring_profile_id available',
                    'message': 'Cannot process recurring payment without card token or recurring profile',
                }
            
            # Определяем order_id для транзакции
            # Для рекуррентных платежей используем parent_order_id если есть, иначе генерируем новый
            if donation.parent_order_id and donation.parent_donation:
                # Для дочерних платежей используем parent_order_id как основу
                # но создаем уникальный transaction_id для каждой транзакции
                transaction_id = f"{donation.parent_order_id}_{int(timezone.now().timestamp())}"
            else:
                transaction_id = result.get('order_id', f"REC_{donation.donation_code}_{int(timezone.now().timestamp())}")
            
            # Создаем транзакцию
            transaction = DonationTransaction.objects.create(
                donation=donation,
                transaction_id=transaction_id,
                external_transaction_id=result.get('payment_id', ''),
                amount=donation.amount,
                currency=donation.currency,
                status='pending' if result['success'] else 'failed',
                transaction_type='payment',
                payment_gateway='freedompay',
                gateway_response=result,
            )
            
            # Если это первый платеж в рекуррентной подписке, сохраняем order_id как parent_order_id
            if donation.is_recurring and not donation.parent_order_id:
                donation.parent_order_id = transaction_id
                donation.save(update_fields=['parent_order_id'])
                logger.info(f"Set parent_order_id for recurring donation: {donation.donation_code} -> {transaction_id}")
            
            if result['success']:
                # Для дочерних платежей используем first_payment_date от родительского пожертвования
                if donation.parent_donation and donation.parent_donation.first_payment_date:
                    # Используем first_payment_date родителя для расчета
                    base_donation = donation.parent_donation
                    # Временно устанавливаем first_payment_date для расчета
                    donation.first_payment_date = base_donation.first_payment_date
                elif not donation.first_payment_date:
                    # Если это первый платеж и first_payment_date не установлена, используем текущую дату
                    donation.first_payment_date = timezone.now()
                
                # Обновляем дату следующего платежа от даты первого платежа
                donation.next_payment_date = self._calculate_next_payment_date(donation)
                donation.save()
                
                logger.info(f"Processed recurring payment: {transaction.transaction_id}, next_payment_date: {donation.next_payment_date}")
            else:
                logger.error(f"Failed to process recurring payment: {result.get('error')}")
            
            return {
                'success': result['success'],
                'transaction_id': transaction.transaction_id,
                'message': result.get('message', ''),
                'error': result.get('error'),
            }
            
        except Exception as e:
            logger.error(f"Failed to process recurring payment: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process recurring payment',
            }
    
    def cancel_recurring_subscription(self, donation):
        """Отмена рекуррентной подписки"""
        try:
            donation.recurring_active = False
            donation.save()
            
            logger.info(f"Cancelled recurring subscription for donation: {donation.donation_code}")
            
            return {
                'success': True,
                'message': 'Recurring subscription cancelled successfully',
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel recurring subscription: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to cancel recurring subscription',
            }
    
    def _calculate_next_payment_date(self, donation):
        """Расчет даты следующего платежа от даты первого платежа
        
        Если first_payment_date установлена, используем её как базу и сохраняем день месяца.
        Например, если первый платеж был 14 декабря 2025, то следующий будет 14 января 2026.
        
        Для monthly: следующий платеж в тот же день следующего месяца
        Для quarterly: следующий платеж в тот же день через 3 месяца
        Для yearly: следующий платеж в тот же день следующего года
        
        Логика:
        - Всегда используем first_payment_date как основную базу для расчета
        - Если next_payment_date установлена, вычисляем сколько периодов прошло от first_payment_date
        - Добавляем еще один период к first_payment_date, сохраняя день месяца
        """
        from dateutil.relativedelta import relativedelta
        
        # Используем дату первого платежа как базу, если она установлена
        if not donation.first_payment_date:
            # Если first_payment_date не установлена, используем текущую дату
            # (для обратной совместимости или если это первый платеж)
            donation.first_payment_date = timezone.now()
        
        # Всегда используем first_payment_date как основную базу
        base_date = donation.first_payment_date
        
        # Если next_payment_date установлена, вычисляем сколько периодов прошло
        # и добавляем еще один период к first_payment_date
        if donation.next_payment_date:
            # Вычисляем разницу между next_payment_date и first_payment_date
            # чтобы понять, сколько периодов уже прошло
            # Важно: если next_payment_date в прошлом, но имеет тот же день месяца
            # что и first_payment_date, это означает что она была запланирована на
            # определенный период, но была установлена в прошлое для триггера платежа
            if donation.donation_type == 'monthly':
                # Вычисляем разницу в месяцах
                months_diff = (donation.next_payment_date.year - base_date.year) * 12 + \
                             (donation.next_payment_date.month - base_date.month)
                
                # Если next_payment_date в прошлом, но имеет тот же день месяца что и first_payment_date,
                # это означает что она была запланирована на определенный период в будущем,
                # но была установлена в прошлое для триггера. В этом случае нужно определить
                # на какой период она была запланирована.
                if donation.next_payment_date < timezone.now() and \
                   donation.next_payment_date.day == base_date.day:
                    # Если months_diff <= 0, значит next_payment_date был в том же месяце
                    # что и base_date или раньше, но имеет тот же день месяца.
                    # Это означает что он был запланирован на следующий месяц от base_date
                    if months_diff <= 0:
                        months_diff = 1
                    # Проверяем, что candidate_date имеет правильный день месяца
                    candidate_date = base_date + relativedelta(months=months_diff)
                    if candidate_date.day != base_date.day:
                        # Если день не совпадает, пробуем следующий месяц
                        months_diff += 1
                
                # Добавляем еще один месяц к first_payment_date
                next_date = base_date + relativedelta(months=months_diff + 1)
            elif donation.donation_type == 'quarterly':
                # Вычисляем разницу в месяцах и делим на 3
                months_diff = (donation.next_payment_date.year - base_date.year) * 12 + \
                             (donation.next_payment_date.month - base_date.month)
                quarters_diff = months_diff // 3
                # Добавляем еще один квартал к first_payment_date
                next_date = base_date + relativedelta(months=(quarters_diff + 1) * 3)
            elif donation.donation_type == 'yearly':
                # Вычисляем разницу в годах
                years_diff = donation.next_payment_date.year - base_date.year
                # Добавляем еще один год к first_payment_date
                next_date = base_date + relativedelta(years=years_diff + 1)
            else:
                return None
        else:
            # Если next_payment_date не установлена, просто добавляем один период к first_payment_date
            if donation.donation_type == 'monthly':
                # Следующий платеж в тот же день следующего месяца от базовой даты
                next_date = base_date + relativedelta(months=1)
            elif donation.donation_type == 'quarterly':
                # Следующий платеж в тот же день через 3 месяца от базовой даты
                next_date = base_date + relativedelta(months=3)
            elif donation.donation_type == 'yearly':
                # Следующий платеж в тот же день следующего года от базовой даты
                next_date = base_date + relativedelta(years=1)
            else:
                # Для one_time или других типов не рассчитываем следующую дату
                return None
        
        # Сохраняем день месяца от first_payment_date для консистентности
        # Это гарантирует что все платежи происходят в один и тот же день месяца
        try:
            next_date = next_date.replace(day=donation.first_payment_date.day)
        except ValueError:
            # Если день невалиден (например, 31 февраля), оставляем как есть
            # или используем последний день месяца
            pass
        
        return next_date