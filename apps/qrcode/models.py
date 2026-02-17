from django.db import models
from .validators import SecureImageFileValidator


class QRCode(models.Model):
    """Простая модель для QR-кодов платежей"""
    qr_code = models.ImageField(
        upload_to='qr_codes/', 
        null=True, 
        blank=True,
        validators=[SecureImageFileValidator()],
        help_text="Загрузите изображение QR-кода (JPG, PNG, GIF, BMP, SVG, WebP). Максимальный размер: 5MB"
    )

    class Meta:
        verbose_name = 'QR-код'
        verbose_name_plural = 'QR-коды'