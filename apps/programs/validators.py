from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import os


def validate_svg_file(value):
    """
    Валидатор для SVG файлов
    """
    if value:
        # Проверяем расширение файла
        ext = os.path.splitext(value.name)[1].lower()
        if ext != '.svg':
            raise ValidationError(_('Поддерживаются только SVG файлы.'))
        
        # Проверяем содержимое файла
        try:
            content = value.read()
            value.seek(0)  # Возвращаем указатель в начало файла
            
            # Проверяем, что это действительно SVG
            if not content.startswith(b'<svg') and b'<svg' not in content[:100]:
                raise ValidationError(_('Файл не является корректным SVG.'))
                
        except Exception:
            raise ValidationError(_('Не удалось прочитать файл.'))
    
    return value


def validate_image_or_svg_file(value):
    """
    Валидатор для изображений и SVG файлов
    """
    if value:
        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        
        if ext not in allowed_extensions:
            raise ValidationError(_('Поддерживаются только файлы: JPG, PNG, GIF, WebP, SVG.'))
        
        # Если это SVG, проверяем содержимое
        if ext == '.svg':
            try:
                content = value.read()
                value.seek(0)
                
                if not content.startswith(b'<svg') and b'<svg' not in content[:100]:
                    raise ValidationError(_('Файл не является корректным SVG.'))
                    
            except Exception:
                raise ValidationError(_('Не удалось прочитать SVG файл.'))
    
    return value
