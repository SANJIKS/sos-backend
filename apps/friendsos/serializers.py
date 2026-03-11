from rest_framework import serializers
from .models import SOSFriend


class SOSFriendSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = SOSFriend
        fields = [
            'id',
            'name',
            'location',
            'photo',
            'photo_url',
            'message',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_photo_url(self, obj) -> str | None:
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None


class SOSFriendCreateSerializer(serializers.ModelSerializer):
    """Для публичной отправки отзыва"""

    class Meta:
        model = SOSFriend
        fields = ['name', 'location', 'photo', 'message']