import time
import logging
import re
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import SuspiciousOperation

logger = logging.getLogger(__name__)

class SecurityMiddleware(MiddlewareMixin):
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>.*?</style>',
            r'@import',
            r'url\s*\(',
            r'expression\s*\(',
            r'data:text/html',
            r'data:application/javascript',
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'<.*?>',
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.suspicious_patterns]
    
    def process_request(self, request):
        exempt_paths = [
            '/api/v1/schema/',
            '/swagger/',
            '/ckeditor5/',
            '/admin/',
            '/api/v1/auth/',
            '/api/v1/vacancies/',
            '/api/v1/news/',
            '/api/v1/faq/',
            '/api/v1/success-stories/',
            '/api/v1/programs/',
            '/api/v1/locations/',
            '/api/v1/social-networks/',
            '/api/v1/contacts/',
            '/api/v1/partners/',
            '/api/v1/timeline/',
            '/api/v1/principles/',
            '/api/v1/impact-results/',
            '/api/v1/donation-options/',
            '/api/v1/common/',
        ]
        
        if any(request.path.startswith(path) for path in exempt_paths):
            return None
            
        try:
            self._check_suspicious_patterns(request)
            self._check_path_traversal(request)
            self._check_request_size(request)
            
            if request.path.startswith('/api/'):
                self._check_rate_limit(request)
                
        except SuspiciousOperation as e:
            logger.warning(f"Suspicious request blocked: {e}")
            return JsonResponse({'error': 'Подозрительный запрос заблокирован'}, status=400)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Security middleware error: {error_msg}")
            
            if 'authentication required' in error_msg.lower():
                return JsonResponse({'error': 'Authentication required'}, status=401)
                
            return JsonResponse({'error': 'Ошибка безопасности'}, status=500)
    
    def _check_suspicious_patterns(self, request):
        url_to_check = request.get_full_path()
        
        for key, value in request.GET.items():
            if isinstance(value, str):
                url_to_check += f" {key}={value}"
        
        if request.method == 'POST':
            try:
                for key, value in request.POST.items():
                    if isinstance(value, str):
                        url_to_check += f" {key}={value}"
            except Exception:
                pass
        
        for pattern in self.compiled_patterns:
            if pattern.search(url_to_check):
                logger.warning(f"Suspicious pattern detected in request: {pattern.pattern}")
                raise SuspiciousOperation("Подозрительный паттерн обнаружен в запросе")
    
    def _check_path_traversal(self, request):
        path = request.path
        
        dangerous_patterns = [
            '../', '..\\', '%2e%2e%2f', '%2e%2e%5c',
            '..%2f', '..%5c', '%2e%2e/', '%2e%2e\\'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in path.lower():
                logger.warning(f"Path traversal attempt detected: {path}")
                raise SuspiciousOperation("Попытка path traversal атаки")
    
    def _check_request_size(self, request):
        content_length = request.META.get('CONTENT_LENGTH', 0)
        
        try:
            content_length = int(content_length)
        except (ValueError, TypeError):
            content_length = 0
        
        max_size = getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)
        
        if content_length > max_size:
            logger.warning(f"Oversized request blocked: {content_length} bytes")
            raise SuspiciousOperation("Запрос слишком большой")
    
    def _check_rate_limit(self, request):
        ip = self._get_client_ip(request)
        
        cache_key = f"rate_limit:{ip}"
        
        current_requests = cache.get(cache_key, 0)
        
        max_requests = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        
        if current_requests >= max_requests:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            raise SuspiciousOperation("Превышен лимит запросов")
        
        cache.set(cache_key, current_requests + 1, 60)
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class RequestLoggingMiddleware(MiddlewareMixin):
    
    def process_request(self, request):
        if self._should_log_request(request):
            logger.info(f"Request: {request.method} {request.path} from {self._get_client_ip(request)}")
    
    def process_response(self, request, response):
        if self._should_log_request(request) and response.status_code >= 400:
            logger.warning(f"Error response: {response.status_code} for {request.method} {request.path}")
        
        return response
    
    def _should_log_request(self, request):
        return (
            request.path.startswith('/api/') or
            request.path.startswith('/admin/') or
            request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
        )
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip