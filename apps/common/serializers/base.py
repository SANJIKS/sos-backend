"""
Базовые сериализаторы для приложения
"""
from rest_framework import serializers
from django.utils import timezone
from apps.common.serializers.localization import LocalizedSerializerMixin


class BaseModelSerializer(serializers.ModelSerializer, LocalizedSerializerMixin):
    """
    Базовый сериализатор для всех моделей
    """
    
    class Meta:
        fields = ['uuid', 'created_at', 'updated_at']
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class BaseContentSerializer(serializers.ModelSerializer, LocalizedSerializerMixin):
    """
    Базовый сериализатор для контентных моделей
    """
    
    class Meta:
        fields = [
            'uuid', 'title', 'slug', 'description', 'content', 
            'is_active', 'is_featured', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'slug', 'created_at', 'updated_at']


class BaseContentWithChoicesSerializer(BaseContentSerializer):
    """
    Базовый сериализатор для контентных моделей с выбором
    """
    
    class Meta(BaseContentSerializer.Meta):
        # Не добавляем дополнительные поля по умолчанию, так как они могут отсутствовать в моделях.
        # Наследники должны явно указывать нужные дополнительные поля в своих сериализаторах.
        fields = BaseContentSerializer.Meta.fields


class BaseContentWithChoicesListSerializer(serializers.ModelSerializer, LocalizedSerializerMixin):
    """
    Базовый сериализатор для списков контентных моделей с выбором
    """
    
    class Meta:
        fields = [
            'uuid', 'title', 'slug', 'description', 'is_active', 
            'is_featured', 'created_at'
        ]
        read_only_fields = ['uuid', 'slug', 'created_at']
