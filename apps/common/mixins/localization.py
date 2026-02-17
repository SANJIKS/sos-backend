"""
Миксины для локализации
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


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
