from rest_framework import serializers
from apps.common.serializers import BaseContentWithChoicesSerializer, BaseContentWithChoicesListSerializer
from .models import Program, ProgramStep


class ProgramStepSerializer(serializers.ModelSerializer):
    """
    Сериализатор для этапов программы
    """
    class Meta:
        model = ProgramStep
        fields = ['uuid', 'title', 'description', 'order', 'icon']


class ProgramDetailSerializer(BaseContentWithChoicesSerializer):
    """
    Детальный сериализатор для программ с полной информацией
    """
    steps = ProgramStepSerializer(many=True, read_only=True)
    
    class Meta(BaseContentWithChoicesSerializer.Meta):
        model = Program
        fields = BaseContentWithChoicesSerializer.Meta.fields + [
            'short_description', 'program_type', 'icon', 'main_image', 
            'video_url', 'video_thumbnail', 'is_main_program', 
            'content', 'target_audience', 'duration', 
            'author_name', 'author_title', 'quote', 'steps'
        ]


class ProgramSerializer(BaseContentWithChoicesSerializer):
    """
    Сериализатор для программ
    """
    class Meta(BaseContentWithChoicesSerializer.Meta):
        model = Program
        fields = BaseContentWithChoicesSerializer.Meta.fields + [
            'short_description', 'program_type', 'icon', 'is_main_program', 
            'content', 'target_audience', 'duration'
        ]


class ProgramListSerializer(BaseContentWithChoicesListSerializer):
    """
    Сериализатор для списка программ (сокращенная версия)
    """
    class Meta(BaseContentWithChoicesListSerializer.Meta):
        model = Program
        fields = BaseContentWithChoicesListSerializer.Meta.fields + [
            'short_description', 'program_type', 'icon', 'is_main_program'
        ]
