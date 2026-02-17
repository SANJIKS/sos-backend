from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.conf import settings
import os
import re
import logging

logger = logging.getLogger(__name__)


class SecureImageFileValidator(FileExtensionValidator):
    """Безопасный валидатор для изображений с разумной защитой"""
    
    # Максимальный размер файла (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # Опасные паттерны в SVG (расширенный список)
    DANGEROUS_SVG_PATTERNS = [
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # JavaScript
        r'javascript:',  # JavaScript URLs
        r'vbscript:',  # VBScript URLs
        r'data:text/html',  # HTML data URLs
        r'data:application/javascript',  # JS data URLs
        r'<iframe\b',  # iframe tags
        r'<object\b',  # object tags
        r'<embed\b',  # embed tags
        r'onload\s*=',  # Event handlers
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
        r'<link\b[^>]*rel\s*=\s*["\']stylesheet["\']',  # External stylesheets
        r'@import',  # CSS imports
        r'expression\s*\(',  # CSS expressions
    ]
    
    # Подозрительные паттерны в именах файлов
    SUSPICIOUS_FILENAME_PATTERNS = [
        r'\.(php|asp|jsp|cgi|pl|py|rb|sh|bat|cmd|exe)$',  # Executable extensions
        r'\.(htaccess|htpasswd|ini|conf)$',  # Config files
        r'\.(sql|db|sqlite)$',  # Database files
        r'\.(log|txt|md)$',  # Text files that shouldn't be images
    ]
    
    def __init__(self, allowed_extensions=None, max_size=None):
        if allowed_extensions is None:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp']
        self.max_size = max_size or self.MAX_FILE_SIZE
        super().__init__(allowed_extensions)
    
    def __call__(self, value):
        # Проверка размера файла
        if hasattr(value, 'size') and value.size > self.max_size:
            logger.warning(f"Attempted upload of oversized file: {value.size} bytes")
            raise ValidationError(f'Размер файла не должен превышать {self.max_size // (1024*1024)}MB')
        
        # Проверка расширения файла
        super().__call__(value)
        
        # Проверка имени файла
        self._validate_filename(value.name)
        
        # Проверка содержимого файла
        self._validate_file_content(value)
    
    def _validate_file_content(self, value):
        """Валидация содержимого файла"""
        try:
            value.seek(0)
            
            # Для SVG файлов - полная проверка
            if value.name.lower().endswith('.svg'):
                self._validate_svg_content(value)
            
            # Для обычных изображений - проверка магических байтов
            else:
                self._validate_image_magic_bytes(value)
                
        except Exception as e:
            logger.error(f"File validation error: {e}")
            raise ValidationError('Не удалось проверить содержимое файла')
    
    def _validate_svg_content(self, value):
        """Валидация SVG содержимого"""
        try:
            value.seek(0)
            content = value.read()  # Читаем весь файл для SVG
            value.seek(0)
            
            content_str = content.decode('utf-8', errors='ignore')
            
            # Проверяем, что это действительно SVG
            if not ('<svg' in content_str.lower() or '<?xml' in content_str.lower()):
                raise ValidationError('Файл не является корректным SVG изображением')
            
            # Проверяем на опасные паттерны
            for pattern in self.DANGEROUS_SVG_PATTERNS:
                if re.search(pattern, content_str, re.IGNORECASE):
                    logger.warning(f"Malicious SVG pattern detected: {pattern}")
                    raise ValidationError('SVG файл содержит потенциально опасный код')
            
            # Проверяем на внешние ресурсы (разрешаем только безопасные)
            external_urls = re.findall(r'http[s]?://[^\s<>"\']+', content_str)
            if external_urls:
                allowed_domains = [
                    'fonts.googleapis.com', 
                    'fonts.gstatic.com',
                    'www.w3.org',
                    'www.w3.org/2000/svg'
                ]
                for url in external_urls:
                    if not any(domain in url for domain in allowed_domains):
                        logger.warning(f"SVG contains external URL: {url}")
                        raise ValidationError('SVG файл содержит неразрешенные внешние ссылки')
                
        except UnicodeDecodeError:
            raise ValidationError('SVG файл содержит некорректные символы')
        except Exception as e:
            logger.error(f"SVG validation error: {e}")
            raise ValidationError('Ошибка при проверке SVG файла')
    
    def _validate_image_magic_bytes(self, value):
        """Валидация магических байтов изображений"""
        try:
            value.seek(0)
            content = value.read(1024)  # Читаем первые 1KB
            value.seek(0)
            
            # Магические байты для различных форматов
            magic_bytes = {
                b'\xff\xd8\xff': 'JPEG',
                b'\x89PNG\r\n\x1a\n': 'PNG',
                b'GIF87a': 'GIF',
                b'GIF89a': 'GIF',
                b'BM': 'BMP',
                b'RIFF': 'WEBP',  # Упрощенная проверка для WebP
            }
            
            file_type = None
            for magic, img_type in magic_bytes.items():
                if content.startswith(magic):
                    file_type = img_type
                    break
            
            if not file_type:
                logger.warning("Unknown file type detected")
                raise ValidationError('Неизвестный тип изображения')
                
        except Exception as e:
            logger.error(f"Image validation error: {e}")
            raise ValidationError('Ошибка при проверке изображения')
    
    def _validate_filename(self, filename):
        """Валидация имени файла с защитой от атак"""
        if not filename:
            raise ValidationError('Имя файла не может быть пустым')
        
        # Проверка на опасные символы
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in filename:
                logger.warning(f"Dangerous character in filename: {char}")
                raise ValidationError(f'Имя файла содержит недопустимый символ: {char}')
        
        # Проверка длины имени файла
        if len(filename) > 255:
            raise ValidationError('Имя файла слишком длинное')
        
        # Проверка на подозрительные паттерны в имени файла
        for pattern in self.SUSPICIOUS_FILENAME_PATTERNS:
            if re.search(pattern, filename.lower()):
                logger.warning(f"Suspicious filename pattern detected: {pattern}")
                raise ValidationError('Имя файла содержит подозрительный паттерн')
        
        # Проверка на двойные расширения (кроме SVG)
        if filename.count('.') > 1 and not filename.lower().endswith('.svg'):
            logger.warning(f"Multiple extensions in filename: {filename}")
            raise ValidationError('Имя файла содержит несколько расширений')
        
        # Проверка на пустое имя файла
        if filename.strip() == '':
            raise ValidationError('Имя файла не может быть пустым')
