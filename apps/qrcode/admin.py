from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import QRCode


@admin.register(QRCode)
class QRCodeAdmin(ModelAdmin):
    list_display = ['id', 'qr_code_preview', 'qr_code']
    list_display_links = ['id', 'qr_code_preview']
    
    def qr_code_preview(self, obj):
        """Превью QR-кода в админке"""
        if obj.qr_code:
            if obj.qr_code.name.lower().endswith('.svg'):
                # Для SVG файлов показываем ссылку
                return format_html(
                    '<a href="{}" target="_blank">SVG QR-код</a>',
                    obj.qr_code.url
                )
            else:
                # Для обычных изображений показываем превью
                return format_html(
                    '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                    obj.qr_code.url
                )
        return "Нет изображения"
    
    qr_code_preview.short_description = "Превью"