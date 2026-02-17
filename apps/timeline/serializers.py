from rest_framework import serializers
from .models import TimelineEvent


class TimelineEventSerializer(serializers.ModelSerializer):
    """
    Сериализатор для событий временной шкалы
    """
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = TimelineEvent
        fields = [
            'uuid', 'year', 'title', 'description', 'event_type', 'event_type_display',
            'image', 'icon', 'is_active', 'is_featured', 'order', 'location',
            'participants', 'impact', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class TimelineEventListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка событий (сокращенная версия)
    """
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    
    class Meta:
        model = TimelineEvent
        fields = [
            'uuid', 'year', 'title', 'description', 'event_type', 'event_type_display',
            'image', 'icon', 'is_featured', 'order', 'location'
        ]
