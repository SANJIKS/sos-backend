from rest_framework import serializers
from apps.common.serializers import BaseModelSerializer
from .models import SuccessStory


class SuccessStorySerializer(BaseModelSerializer):
    author_image = serializers.SerializerMethodField()
    banner_image = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = SuccessStory
        fields = BaseModelSerializer.Meta.fields + [
            'title', 'quote_text', 'author_name', 'author_position',
            'author_image', 'banner_image', 'is_active', 'is_featured',
            'order', 'description', 'full_story', 'video_url', 'story_type'
        ]

    def get_author_image(self, obj):
        if obj.author_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.author_image.url)
            return obj.author_image.url
        return None

    def get_banner_image(self, obj):
        if obj.banner_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.banner_image.url)
            return obj.banner_image.url
        return None


class SuccessStoryListSerializer(BaseModelSerializer):
    author_image = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = SuccessStory
        fields = ['uuid', 'title', 'quote_text', 'author_name', 'author_position',
                  'author_image', 'is_featured', 'order', 'story_type']

    def get_author_image(self, obj):
        if obj.author_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.author_image.url)
            return obj.author_image.url
        return None