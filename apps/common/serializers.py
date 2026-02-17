"""
Базовые классы для сериализаторов
"""
from rest_framework import serializers
from django.utils import translation
from apps.common.utils.localization import get_localized_field


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор с общими полями
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        fields = ['id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class BaseContentSerializer(BaseModelSerializer):
    """
    Базовый сериализатор для контентных объектов
    """
    is_active = serializers.BooleanField(read_only=True)
    is_featured = serializers.BooleanField(read_only=True)
    order = serializers.IntegerField(read_only=True)
    
    class Meta(BaseModelSerializer.Meta):
        fields = BaseModelSerializer.Meta.fields + [
            'title', 'description', 'image', 'slug', 'is_active', 
            'is_featured', 'order'
        ]


class BaseContentListSerializer(BaseContentSerializer):
    """
    Базовый сериализатор для списка контентных объектов (сокращенная версия)
    """
    class Meta(BaseContentSerializer.Meta):
        fields = [
            'id', 'title', 'description', 'image', 'slug', 'is_featured', 'order'
        ]


class BaseChoiceFieldSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для моделей с choice полями
    """
    def to_representation(self, instance):
        """Добавляет display поля для choice полей"""
        data = super().to_representation(instance)
        
        # Автоматически добавляем display поля для choice полей
        for field in instance._meta.get_fields():
            if hasattr(field, 'choices') and field.choices and hasattr(field, 'name'):
                field_name = field.name
                display_field_name = f'{field_name}_display'
                if display_field_name not in data:
                    data[display_field_name] = getattr(instance, f'get_{field_name}_display', lambda: '')()
        
        return data


class BaseContentWithChoicesSerializer(BaseContentSerializer, BaseChoiceFieldSerializer):
    """
    Базовый сериализатор для контентных объектов с choice полями
    """
    pass


class BaseContentWithChoicesListSerializer(BaseContentListSerializer, BaseChoiceFieldSerializer):
    """
    Базовый сериализатор для списка контентных объектов с choice полями
    """
    pass


# Локализация
class LocalizedSerializerMixin:
    """
    Миксин для сериализаторов с поддержкой локализации
    """
    
    def get_localized_field(self, obj, field_name, language_code=None):
        """
        Получить локализованное поле в сериализаторе
        """
        return get_localized_field(obj, field_name, language_code)
    
    def to_representation(self, instance):
        """
        Переопределяем метод для добавления локализованных полей
        """
        data = super().to_representation(instance)
        
        # Добавляем локализованные поля
        if hasattr(instance, 'get_localized_name'):
            data['name_localized'] = instance.get_localized_name()
        
        if hasattr(instance, 'get_localized_description'):
            data['description_localized'] = instance.get_localized_description()
        
        if hasattr(instance, 'get_localized_title'):
            data['title_localized'] = instance.get_localized_title()
        
        return data


class LocalizedModelSerializer(LocalizedSerializerMixin, serializers.ModelSerializer):
    """
    Базовый сериализатор с поддержкой локализации
    """
    
    class Meta:
        abstract = True


class LocalizedField(serializers.Field):
    """
    Кастомное поле для локализованных данных
    """
    
    def __init__(self, field_name, language_code=None, **kwargs):
        self.field_name = field_name
        self.language_code = language_code
        super().__init__(**kwargs)
    
    def to_representation(self, obj):
        """
        Получить локализованное значение
        """
        return get_localized_field(obj, self.field_name, self.language_code)
    
    def to_internal_value(self, data):
        """
        Для записи локализованных данных
        """
        return data


class LocalizedNameField(LocalizedField):
    """
    Поле для локализованного названия
    """
    
    def __init__(self, **kwargs):
        super().__init__('name', **kwargs)


class LocalizedDescriptionField(LocalizedField):
    """
    Поле для локализованного описания
    """
    
    def __init__(self, **kwargs):
        super().__init__('description', **kwargs)


class LocalizedTitleField(LocalizedField):
    """
    Поле для локализованного заголовка
    """
    
    def __init__(self, **kwargs):
        super().__init__('title', **kwargs)
