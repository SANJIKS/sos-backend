import time
import logging
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
import re

logger = logging.getLogger(__name__)


class SecurityMiddleware(MiddlewareMixin):
    """Middleware для защиты от различных атак"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        
        # Паттерны для обнаружения атак
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',  # JavaScript injection
            r'vbscript:',  # VBScript injection
            r'onload\s*=',  # Event handlers
            r'onerror\s*=',
            r'onclick\s*=',
            r'<iframe[^>]*>',  # iframe injection
            r'<object[^>]*>',  # object injection
            r'<embed[^>]*>',  # embed injection
            r'<link[^>]*>',  # link injection
            r'<meta[^>]*>',  # meta injection
            r'<style[^>]*>.*?</style>',  # CSS injection
            r'@import',  # CSS import
            r'url\s*\(',  # CSS url
            r'expression\s*\(',  # CSS expression
            r'data:text/html',  # Data URL HTML
            r'data:application/javascript',  # Data URL JS
            r'\.\./',  # Path traversal
            r'\.\.\\',  # Path traversal Windows
            r'%2e%2e%2f',  # URL encoded path traversal
            r'%2e%2e%5c',  # URL encoded path traversal Windows
            r'<.*?>',  # HTML tags in general
        ]
        
        # Компилируем регулярные выражения
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.suspicious_patterns]
    
    def process_request(self, request):
        """Обработка входящего запроса"""
        try:
            # Проверка на подозрительные паттерны в URL
            self._check_suspicious_patterns(request)
            
            # Проверка на path traversal
            self._check_path_traversal(request)
            
            # Проверка размера запроса
            self._check_request_size(request)
            
            # Rate limiting для API
            if request.path.startswith('/api/'):
                self._check_rate_limit(request)
                
        except SuspiciousOperation as e:
            logger.warning(f"Suspicious request blocked: {e}")
            return JsonResponse({'error': 'Подозрительный запрос заблокирован'}, status=400)
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return JsonResponse({'error': 'Ошибка безопасности'}, status=500)
    
    def _check_suspicious_patterns(self, request):
        """Проверка на подозрительные паттерны"""
        # Проверяем URL
        url_to_check = request.get_full_path()
        
        # Проверяем параметры запроса
        for key, value in request.GET.items():
            if isinstance(value, str):
                url_to_check += f" {key}={value}"
        
        # Проверяем POST данные
        if request.method == 'POST':
            try:
                for key, value in request.POST.items():
                    if isinstance(value, str):
                        url_to_check += f" {key}={value}"
            except Exception:
                pass  # Игнорируем ошибки парсинга POST данных
        
        # Проверяем на подозрительные паттерны
        for pattern in self.compiled_patterns:
            if pattern.search(url_to_check):
                logger.warning(f"Suspicious pattern detected in request: {pattern.pattern}")
                raise SuspiciousOperation("Подозрительный паттерн обнаружен в запросе")
    
    def _check_path_traversal(self, request):
        """Проверка на path traversal атаки"""
        path = request.path
        
        # Проверяем на различные варианты path traversal
        dangerous_patterns = [
            '../', '..\\', '%2e%2e%2f', '%2e%2e%5c',
            '..%2f', '..%5c', '%2e%2e/', '%2e%2e\\'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in path.lower():
                logger.warning(f"Path traversal attempt detected: {path}")
                raise SuspiciousOperation("Попытка path traversal атаки")
    
    def _check_request_size(self, request):
        """Проверка размера запроса"""
        content_length = request.META.get('CONTENT_LENGTH', 0)
        
        try:
            content_length = int(content_length)
        except (ValueError, TypeError):
            content_length = 0
        
        # Максимальный размер запроса (10MB)
        max_size = getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)
        
        if content_length > max_size:
            logger.warning(f"Oversized request blocked: {content_length} bytes")
            raise SuspiciousOperation("Запрос слишком большой")
    
    def _check_rate_limit(self, request):
        """Проверка rate limiting"""
        # Получаем IP адрес клиента
        ip = self._get_client_ip(request)
        
        # Создаем ключ для кэша
        cache_key = f"rate_limit:{ip}"
        
        # Получаем текущее количество запросов
        current_requests = cache.get(cache_key, 0)
        
        # Максимальное количество запросов в минуту
        max_requests = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        
        if current_requests >= max_requests:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            raise SuspiciousOperation("Превышен лимит запросов")
        
        # Увеличиваем счетчик
        cache.set(cache_key, current_requests + 1, 60)  # 60 секунд
    
    def _get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware для логирования запросов"""
    
    def process_request(self, request):
        """Логирование входящего запроса"""
        # Логируем только подозрительные или важные запросы
        if self._should_log_request(request):
            logger.info(f"Request: {request.method} {request.path} from {self._get_client_ip(request)}")
    
    def process_response(self, request, response):
        """Логирование ответа"""
        if self._should_log_request(request) and response.status_code >= 400:
            logger.warning(f"Error response: {response.status_code} for {request.method} {request.path}")
        
        return response
    
    def _should_log_request(self, request):
        """Определение, нужно ли логировать запрос"""
        # Логируем API запросы и запросы с ошибками
        return (
            request.path.startswith('/api/') or
            request.path.startswith('/admin/') or
            request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
        )
    
    def _get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
