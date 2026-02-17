from rest_framework import serializers
from apps.common.serializers import BaseModelSerializer
from .models import SuccessStory


class SuccessStorySerializer(BaseModelSerializer):
    """
    Сериализатор для историй успеха
    """
    author_image = serializers.SerializerMethodField()
    
    class Meta(BaseModelSerializer.Meta):
        model = SuccessStory
        fields = BaseModelSerializer.Meta.fields + [
            'title', 'quote_text', 'author_name', 'author_position', 
            'author_image', 'is_active', 'is_featured', 'order', 'description'
        ]
    
    def get_author_image(self, obj) -> str | None:
        if obj.author_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.author_image.url)
            return obj.author_image.url
        return None


class SuccessStoryListSerializer(BaseModelSerializer):
    """
    Сериализатор для списка историй успеха (сокращенная версия)
    """
    author_image = serializers.SerializerMethodField()
    
    class Meta(BaseModelSerializer.Meta):
        model = SuccessStory
        fields = ['uuid', 'title', 'quote_text', 'author_name', 'author_position', 
                 'author_image', 'is_featured', 'order']
    
    def get_author_image(self, obj) -> str | None:
        if obj.author_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.author_image.url)
            return obj.author_image.url
        return None


