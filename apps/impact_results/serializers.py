from rest_framework import serializers
from .models import ImpactResult


class ImpactResultSerializer(serializers.ModelSerializer):
    """
    Сериализатор для результатов воздействия
    """
    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)
    
    class Meta:
        model = ImpactResult
        fields = [
            'uuid', 'title', 'percentage_value', 'description', 'result_type', 'result_type_display',
            'image', 'is_active', 'is_featured', 'order', 'detailed_description',
            'source', 'year', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class ImpactResultListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка результатов (сокращенная версия)
    """
    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)
    
    class Meta:
        model = ImpactResult
        fields = [
            'uuid', 'title', 'percentage_value', 'description', 'result_type', 'result_type_display',
            'image', 'is_featured', 'order'
        ]
