#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
sys.path.append('/Users/alba/Projects/Sos_kg')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.qrcode.serializers import SecureQRCodeSerializer
from apps.qrcode.models import QRCode
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

def test_qr_code_serializer():
    """Тестирование сериализатора QR-кодов"""
    
    # Создаем тестовый запрос
    factory = RequestFactory()
    request = factory.get('/api/qrcodes/')
    
    # Создаем тестовый PNG файл
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    
    # Создаем объект QRCode
    qr_code = QRCode()
    qr_code.qr_code = SimpleUploadedFile('test.png', png_data, content_type='image/png')
    qr_code.save()
    
    # Создаем сериализатор с контекстом запроса
    serializer = SecureQRCodeSerializer(qr_code, context={'request': request})
    
    # Получаем сериализованные данные
    data = serializer.data
    
    print("Тестирование сериализатора QR-кодов...")
    print("=" * 50)
    
    # Проверяем структуру данных
    print(f"ID: {data.get('id')}")
    print(f"QR Code URL: {data.get('qr_code')}")
    
    # Проверяем, что URL построен правильно
    qr_url = data.get('qr_code')
    if qr_url:
        if qr_url.startswith('http'):
            print("✅ URL построен правильно (абсолютный)")
        else:
            print("⚠️ URL относительный, но это может быть нормально")
    else:
        print("❌ QR Code URL не найден")
    
    # Тестируем санитизацию
    print("\nТестирование санитизации...")
    
    # Создаем тестовые данные с потенциально опасным контентом
    test_cases = [
        ("<script>alert('xss')</script>", "HTML теги"),
        ("javascript:alert('xss')", "JavaScript URL"),
        ("vbscript:msgbox('xss')", "VBScript URL"),
        ("data:text/html,<script>alert('xss')</script>", "Data URL"),
        ("Обычный текст", "Безопасный текст"),
    ]
    
    for test_value, description in test_cases:
        sanitized = serializer._sanitize_string(test_value)
        print(f"{description}: '{test_value}' -> '{sanitized}'")
        
        # Проверяем, что опасный контент удален
        if 'script' in test_value.lower() and 'script' not in sanitized.lower():
            print("  ✅ Опасный контент удален")
        elif test_value == sanitized and 'script' not in test_value.lower():
            print("  ✅ Безопасный контент сохранен")
        else:
            print("  ⚠️ Возможная проблема с санитизацией")
    
    # Очистка
    qr_code.delete()
    
    print("\n" + "=" * 50)
    print("Тестирование завершено!")

if __name__ == '__main__':
    test_qr_code_serializer()

