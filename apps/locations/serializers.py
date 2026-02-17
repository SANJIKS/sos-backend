from rest_framework import serializers
from .models import MapPoint
from ..partners.mixins import BuildFullUrlToImage
from apps.common.serializers.localization import LocalizedSerializerMixin, LocalizedCharField, LocalizedTextField


class MapPointSerializer(serializers.ModelSerializer, BuildFullUrlToImage):
    image = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = MapPoint
        fields = [
            'point_id',
            'name',
            'description',
            'image',
            'x_percent',
            'y_percent'
        ]

    def get_image(self, obj):
        return self.get_full_url_to_image(obj.image) if obj.image else None
    
    def get_name(self, obj):
        """Получить локализованное название"""
        # Пробуем получить локализованное значение
        from django.utils import translation
        current_language = translation.get_language()
        
        if current_language == 'kg' and obj.name_kg:
            return obj.name_kg
        elif current_language == 'en' and obj.name_en:
            return obj.name_en
        else:
            return obj.name
    
    def get_description(self, obj):
        """Получить локализованное описание"""
        # Пробуем получить локализованное значение
        from django.utils import translation
        current_language = translation.get_language()
        
        if current_language == 'kg' and obj.description_kg:
            return obj.description_kg
        elif current_language == 'en' and obj.description_en:
            return obj.description_en
        else:
            return obj.description
