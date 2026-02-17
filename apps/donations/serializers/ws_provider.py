"""
Сериализаторы для веб-сервисов WS Provider
"""
from rest_framework import serializers
from decimal import Decimal
from django.contrib.auth import get_user_model
from ..models import Donation, DonationCampaign, DonationTransaction

User = get_user_model()


class WSDonorDataSerializer(serializers.Serializer):
    """Сериализатор для данных донора в InsertWSdata"""
    full_name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Полное имя донора"
    )
    email = serializers.EmailField(
        required=True,
        help_text="Email донора"
    )
    phone = serializers.CharField(
        max_length=20,
        required=True,
        help_text="Телефон донора"
    )


class WSDonationDataSerializer(serializers.Serializer):
    """Сериализатор для данных пожертвования в InsertWSdata"""
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        required=True,
        help_text="Сумма пожертвования"
    )
    currency = serializers.ChoiceField(
        choices=Donation.Currency.choices,
        default=Donation.Currency.KGS,
        required=False,
        help_text="Валюта пожертвования"
    )
    donation_type = serializers.ChoiceField(
        choices=Donation.DonationType.choices,
        required=True,
        help_text="Тип пожертвования (one_time, monthly, quarterly, yearly)"
    )
    payment_method = serializers.ChoiceField(
        choices=Donation.PaymentMethod.choices,
        default=Donation.PaymentMethod.BANK_CARD,
        required=False,
        help_text="Способ оплаты"
    )
    status = serializers.ChoiceField(
        choices=Donation.DonationStatus.choices,
        default=Donation.DonationStatus.PENDING,
        required=False,
        help_text="Статус пожертвования (successful или unsuccessful)"
    )
    donor_source = serializers.ChoiceField(
        choices=Donation.DonorSource.choices,
        default=Donation.DonorSource.ONLINE,
        required=False,
        help_text="Источник донора"
    )
    donor_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Комментарий донора"
    )
    campaign_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID кампании (опционально)"
    )
    order_id = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=255,
        help_text="Order ID транзакции (если уже известен)"
    )
    transaction_id = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=255,
        help_text="ID транзакции от платежной системы"
    )
    payment_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Дата платежа"
    )
    is_recurring = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Является ли пожертвование рекуррентным"
    )
    parent_order_id = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=255,
        help_text="Родительский Order ID для рекуррентных платежей"
    )


class InsertWSdataSerializer(serializers.Serializer):
    """
    Сериализатор для веб-сервиса InsertWSdata
    
    Регистрирует донора и пожертвование одновременно.
    Используется WS Provider для интеграции с Salesforce.
    """
    donor = WSDonorDataSerializer(
        required=True,
        help_text="Данные донора"
    )
    donation = WSDonationDataSerializer(
        required=True,
        help_text="Данные пожертвования"
    )
    
    def validate(self, data):
        """Валидация данных"""
        donor_data = data.get('donor', {})
        donation_data = data.get('donation', {})
        
        # Проверяем кампанию если указана
        if donation_data.get('campaign_id'):
            try:
                campaign = DonationCampaign.objects.get(id=donation_data['campaign_id'])
            except DonationCampaign.DoesNotExist:
                raise serializers.ValidationError({
                    'donation': {'campaign_id': 'Кампания не найдена'}
                })
        
        return data


class InsertWSdataResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа InsertWSdata"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    order_id = serializers.CharField(
        required=False,
        help_text="Order ID пожертвования (уникальный идентификатор)"
    )
    donation_uuid = serializers.UUIDField(
        required=False,
        help_text="UUID пожертвования"
    )
    donor_id = serializers.IntegerField(
        required=False,
        help_text="ID донора (если создан)"
    )
    error = serializers.CharField(
        required=False,
        help_text="Сообщение об ошибке"
    )
