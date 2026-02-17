from rest_framework import serializers
from ..models.office import Office


class OfficeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для офисов и локаций
    """
    office_type_display = serializers.CharField(source='get_office_type_display', read_only=True)
    
    class Meta:
        model = Office
        fields = [
            'id', 'name', 'office_type', 'office_type_display', 'address', 
            'phone', 'email', 'working_hours', 'description', 'is_main_office',
            'is_active', 'order', 'latitude', 'longitude', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OfficeListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка офисов (сокращенная версия)
    """
    office_type_display = serializers.CharField(source='get_office_type_display', read_only=True)
    
    class Meta:
        model = Office
        fields = [
            'id', 'name', 'office_type', 'office_type_display', 'address',
            'phone', 'email', 'working_hours', 'is_main_office', 'order'
        ]
