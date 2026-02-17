"""
Базовые сериализаторы для работы с локализацией
"""
from rest_framework import serializers
from django.utils import translation
from apps.common.utils.localization import get_localized_field


class LocalizedSerializerMixin:
    """
    Миксин для сериализаторов с поддержкой локализации
    """
    
    def get_localized_field(self, obj, field_name, language_code=None):
        """
        Получить локализованное поле объекта
        
        Args:
            obj: Объект модели
            field_name: Название поля (без суффикса языка)
            language_code: Код языка (если None, используется текущий язык)
        
        Returns:
            str: Локализованное значение поля
        """
        if language_code is None:
            language_code = translation.get_language()
        
        # Пробуем использовать специальный метод для локализации
        method_name = f"get_{field_name}_by_language"
        if hasattr(obj, method_name):
            method = getattr(obj, method_name)
            return str(method(language_code))
        
        # Пробуем получить локализованное поле
        localized_field = f"{field_name}_{language_code}"
        if hasattr(obj, localized_field):
            value = getattr(obj, localized_field)
            if value:  # Если есть значение на нужном языке
                return str(value)
        
        # Если нет локализованного поля или оно пустое, возвращаем основное
        return str(getattr(obj, field_name, ''))
    
    def get_localized_data(self, obj, fields, language_code=None):
        """
        Получить локализованные данные объекта
        
        Args:
            obj: Объект модели
            fields: Список полей для локализации
            language_code: Код языка
        
        Returns:
            dict: Словарь с локализованными данными
        """
        if language_code is None:
            language_code = translation.get_language()
        
        data = {}
        for field in fields:
            data[field] = self.get_localized_field(obj, field, language_code)
        
        return data


class LocalizedCharField(serializers.CharField):
    """
    Поле для локализованных строковых значений
    """
    
    def __init__(self, field_name, **kwargs):
        self.field_name = field_name
        super().__init__(**kwargs)
    
    def to_representation(self, obj):
        """
        Возвращает локализованное значение поля
        """
        if hasattr(self.parent, 'get_localized_field'):
            return self.parent.get_localized_field(obj, self.field_name)
        else:
            # Fallback к базовой логике
            language_code = translation.get_language()
            localized_field = f"{self.field_name}_{language_code}"
            if hasattr(obj, localized_field):
                value = getattr(obj, localized_field)
                if value and value.strip():
                    return str(value)
            # Получаем основное поле
            main_value = getattr(obj, self.field_name, '')
            if hasattr(main_value, '__call__'):
                # Если это метод, вызываем его
                return str(main_value())
            return str(main_value)


class LocalizedTextField(serializers.CharField):
    """
    Поле для локализованных текстовых значений
    """
    
    def __init__(self, field_name, **kwargs):
        self.field_name = field_name
        super().__init__(**kwargs)
    
    def to_representation(self, obj):
        """
        Возвращает локализованное значение поля
        """
        if hasattr(self.parent, 'get_localized_field'):
            return self.parent.get_localized_field(obj, self.field_name)
        else:
            # Fallback к базовой логике
            language_code = translation.get_language()
            localized_field = f"{self.field_name}_{language_code}"
            if hasattr(obj, localized_field):
                value = getattr(obj, localized_field)
                if value and value.strip():
                    return str(value)
            # Получаем основное поле
            main_value = getattr(obj, self.field_name, '')
            if hasattr(main_value, '__call__'):
                # Если это метод, вызываем его
                return str(main_value())
            return str(main_value)