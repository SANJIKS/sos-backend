"""
Общие миксины для моделей
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class UUIDMixin(models.Model):
    """Миксин для добавления UUID поля"""
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        unique=True, 
        editable=False, 
        db_index=True,
        verbose_name=_('UUID')
    )
    
    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    """Миксин для добавления полей времени создания и обновления"""
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_('Дата создания')
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('Дата обновления')
    )
    
    class Meta:
        abstract = True


class StatusMixin(models.Model):
    """Миксин для добавления поля статуса"""
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_('Активен')
    )
    
    class Meta:
        abstract = True


class OrderingMixin(models.Model):
    """Миксин для добавления поля порядка отображения"""
    order = models.PositiveIntegerField(
        default=0, 
        verbose_name=_('Порядок отображения')
    )
    
    class Meta:
        abstract = True


class FeaturedMixin(models.Model):
    """Миксин для добавления поля рекомендуемости"""
    is_featured = models.BooleanField(
        default=False, 
        verbose_name=_('Рекомендуемый')
    )
    
    class Meta:
        abstract = True


class BaseContentMixin(models.Model):
    """Базовый миксин для контентных моделей"""
    title = models.CharField(
        max_length=200, 
        verbose_name=_('Название')
    )
    description = models.TextField(
        verbose_name=_('Описание')
    )
    
    class Meta:
        abstract = True


class BaseContentWithImageMixin(BaseContentMixin):
    """Базовый миксин для контентных моделей с изображением"""
    image = models.ImageField(
        upload_to='content/', 
        blank=True, 
        null=True, 
        verbose_name=_('Изображение')
    )
    
    class Meta:
        abstract = True


class BaseContentWithSlugMixin(BaseContentMixin):
    """Базовый миксин для контентных моделей со slug"""
    slug = models.SlugField(
        max_length=200, 
        unique=True, 
        blank=True,
        verbose_name=_('URL')
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Автоматически генерирует slug из title если не указан"""
        if not self.slug and self.title:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
            # Убеждаемся что slug уникален
            original_slug = self.slug
            counter = 1
            while self.__class__.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class BaseContentWithImageAndSlugMixin(BaseContentWithImageMixin, BaseContentWithSlugMixin):
    """Базовый миксин для контентных моделей с изображением и slug"""
    
    class Meta:
        abstract = True


class BaseModel(UUIDMixin, TimestampMixin, StatusMixin):
    """Базовая модель с общими полями"""
    
    class Meta:
        abstract = True


class BaseContentModel(BaseModel, BaseContentWithImageAndSlugMixin, OrderingMixin, FeaturedMixin):
    """Базовая модель для контентных объектов"""
    
    class Meta:
        abstract = True


# Локализация
class LocalizedFieldsMixin:
    """
    Миксин для добавления локализованных полей
    """
    
    def get_localized_field(self, field_name, language_code=None):
        """
        Получить локализованное поле
        
        Args:
            field_name: Название поля (без суффикса языка)
            language_code: Код языка
        
        Returns:
            str: Локализованное значение
        """
        from apps.common.utils.localization import get_localized_field
        return get_localized_field(self, field_name, language_code)
    
    def get_localized_name(self, language_code=None):
        """
        Получить локализованное название
        """
        return self.get_localized_field('name', language_code)
    
    def get_localized_description(self, language_code=None):
        """
        Получить локализованное описание
        """
        return self.get_localized_field('description', language_code)
    
    def get_localized_title(self, language_code=None):
        """
        Получить локализованный заголовок
        """
        return self.get_localized_field('title', language_code)


class LocalizedModel(LocalizedFieldsMixin, models.Model):
    """
    Базовая модель с поддержкой локализации
    """
    
    class Meta:
        abstract = True


def create_localized_fields(field_name, max_length=200, blank=True):
    """
    Создать локализованные поля для модели
    
    Args:
        field_name: Название поля
        max_length: Максимальная длина
        blank: Может ли быть пустым
    
    Returns:
        dict: Словарь с полями
    """
    return {
        field_name: models.CharField(
            max_length=max_length,
            verbose_name=_(f'{field_name.title()}'),
            blank=blank
        ),
        f'{field_name}_kg': models.CharField(
            max_length=max_length,
            blank=True,
            verbose_name=_(f'{field_name.title()} (КГ)')
        ),
        f'{field_name}_en': models.CharField(
            max_length=max_length,
            blank=True,
            verbose_name=_(f'{field_name.title()} (EN)')
        ),
    }


def create_localized_text_fields(field_name, blank=True):
    """
    Создать локализованные текстовые поля для модели
    
    Args:
        field_name: Название поля
        blank: Может ли быть пустым
    
    Returns:
        dict: Словарь с полями
    """
    return {
        field_name: models.TextField(
            verbose_name=_(f'{field_name.title()}'),
            blank=blank
        ),
        f'{field_name}_kg': models.TextField(
            blank=True,
            verbose_name=_(f'{field_name.title()} (КГ)')
        ),
        f'{field_name}_en': models.TextField(
            blank=True,
            verbose_name=_(f'{field_name.title()} (EN)')
        ),
    }
