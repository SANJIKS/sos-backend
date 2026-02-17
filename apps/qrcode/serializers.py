from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
import logging

from .models import QRCode
from ..partners.mixins import BuildFullUrlToImage

logger = logging.getLogger(__name__)


class SecureQRCodeSerializer(serializers.ModelSerializer, BuildFullUrlToImage):
    """Безопасный сериализатор для QR-кодов только для чтения"""
    qr_code = serializers.SerializerMethodField()
    
    class Meta:
        model = QRCode
        fields = ['id', 'qr_code']
    
    def to_representation(self, instance):
        """Безопасное представление данных"""
        data = super().to_representation(instance)
        
        # Очищаем данные от потенциально опасного контента
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = self._sanitize_string(value)
        
        return data

    def get_qr_code(self, obj):
        """Получение полного URL для QR-кода"""
        qr_code_field = getattr(obj, 'qr_code', None)
        return self.get_full_url_to_image(qr_code_field)
    
    def _sanitize_string(self, value):
        """Очистка строки от потенциально опасного контента"""
        if not value:
            return value
        
        # Удаляем HTML теги
        value = strip_tags(value)
        
        # Дополнительная защита от XSS
        dangerous_patterns = [
            r'javascript:',  # JavaScript URLs
            r'vbscript:',  # VBScript URLs
            r'data:text/html',  # HTML data URLs
            r'data:application/javascript',  # JS data URLs
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Potentially dangerous content detected: {pattern}")
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        return value