from rest_framework import serializers
from .models import BankingRequisite


class BankingRequisiteSerializer(serializers.ModelSerializer):
    """Сериализатор для банковских реквизитов"""
    
    organization_type_display = serializers.CharField(source='get_organization_type_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    
    class Meta:
        model = BankingRequisite
        fields = [
            'id',
            'title',
            'organization_type',
            'organization_type_display',
            'currency',
            'currency_display',
            'bank_name',
            'account_number',
            'bik',
            'swift',
            'inn',
            'okpo',
            'tax_office',
            'correspondent_bank',
            'correspondent_swift',
            'correspondent_address',
            'correspondent_account',
            'description',
            'is_active',
            'sort_order',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BankingRequisiteListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка банковских реквизитов"""
    
    organization_type_display = serializers.CharField(source='get_organization_type_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    
    class Meta:
        model = BankingRequisite
        fields = [
            'id',
            'title',
            'organization_type',
            'organization_type_display',
            'currency',
            'currency_display',
            'bank_name',
            'account_number',
            'is_active',
            'sort_order'
        ]
