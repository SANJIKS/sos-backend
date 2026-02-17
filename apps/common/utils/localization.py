"""
Утилиты для работы с локализацией
"""
from django.utils import translation
from django.conf import settings


def get_localized_field(obj, field_name, language_code=None):
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
    
    # Пробуем получить локализованное поле
    localized_field = f"{field_name}_{language_code}"
    if hasattr(obj, localized_field):
        value = getattr(obj, localized_field)
        if value:  # Если есть значение на нужном языке
            return value
    
    # Если нет локализованного поля или оно пустое, возвращаем основное
    return getattr(obj, field_name, '')


def get_localized_data(obj, fields, language_code=None):
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
        data[field] = get_localized_field(obj, field, language_code)
    
    return data


def get_available_languages():
    """
    Получить список доступных языков
    
    Returns:
        list: Список кортежей (код_языка, название_языка)
    """
    return settings.LANGUAGES


def is_language_supported(language_code):
    """
    Проверить, поддерживается ли язык
    
    Args:
        language_code: Код языка
    
    Returns:
        bool: True если язык поддерживается
    """
    return language_code in [code for code, _ in settings.LANGUAGES]


def get_default_language():
    """
    Получить язык по умолчанию
    
    Returns:
        str: Код языка по умолчанию
    """
    return settings.LANGUAGE_CODE
