from rest_framework import serializers
from .models import SocialNetwork


class SocialNetworkSerializer(serializers.ModelSerializer):
    """
    Сериализатор для социальных сетей
    """
    network_type_display = serializers.CharField(source='get_network_type_display', read_only=True)
    
    class Meta:
        model = SocialNetwork
        fields = [
            'uuid', 'name', 'network_type', 'network_type_display', 'url',
            'icon', 'custom_icon', 'is_active', 'is_featured', 'order',
            'description', 'followers_count', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class SocialNetworkListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка социальных сетей (сокращенная версия)
    """
    network_type_display = serializers.CharField(source='get_network_type_display', read_only=True)
    
    class Meta:
        model = SocialNetwork
        fields = [
            'uuid', 'name', 'network_type', 'network_type_display', 'url',
            'icon', 'custom_icon', 'is_featured', 'order'
        ]
