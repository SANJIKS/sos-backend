from rest_framework import serializers
from apps.common.serializers import BaseContentSerializer
from .models import Principle


class PrincipleSerializer(BaseContentSerializer):
    """
    Сериализатор для принципов SOS
    """
    class Meta(BaseContentSerializer.Meta):
        model = Principle
        # Явно перечисляем поля без "content", которого нет в модели Principle
        fields = [
            'uuid', 'title', 'slug', 'description',
            'is_active', 'is_featured', 'created_at', 'updated_at',
            'subtitle', 'principle_type', 'icon', 'key_points', 'impact'
        ]


class PrincipleListSerializer(BaseContentSerializer):
    """
    Сериализатор для списка принципов (сокращенная версия)
    """
    class Meta(BaseContentSerializer.Meta):
        model = Principle
        # Явно перечисляем поля без "content"
        fields = [
            'uuid', 'title', 'slug', 'description',
            'is_active', 'is_featured', 'created_at',
            'subtitle', 'principle_type', 'icon'
        ]
