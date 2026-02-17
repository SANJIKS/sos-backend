from rest_framework import serializers
from .models import DonationOption


class DonationOptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для типов пожертвований
    """
    option_type_display = serializers.CharField(source='get_option_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DonationOption
        fields = [
            'id', 'title', 'description', 'option_type', 'option_type_display',
            'status', 'status_display', 'image', 'button_text', 'button_url',
            'is_button_enabled', 'is_active', 'is_featured', 'order',
            'detailed_description', 'requirements', 'benefits', 'min_amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DonationOptionListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка типов пожертвований (сокращенная версия)
    """
    option_type_display = serializers.CharField(source='get_option_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DonationOption
        fields = [
            'id', 'title', 'description', 'option_type', 'option_type_display',
            'status', 'status_display', 'image', 'button_text', 'button_url',
            'is_button_enabled', 'is_featured', 'order'
        ]
