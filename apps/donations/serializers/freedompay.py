from rest_framework import serializers
from decimal import Decimal
from django.contrib.auth import get_user_model
from ..models import Donation, DonationCampaign

User = get_user_model()


class UserInfoSerializer(serializers.Serializer):
    """Сериализатор для данных пользователя (если не авторизован)"""
    name = serializers.CharField(
        max_length=255, 
        required=True,
        allow_blank=False,
        help_text="ФИО донора (обязательно)"
    )
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        help_text="Email донора (обязательно)"
    )
    phone = serializers.CharField(
        max_length=20, 
        required=True,
        allow_blank=False,
        help_text="Телефон донора (обязательно)"
    )
    
    def validate_phone(self, value):
        """Валидация телефона"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Телефон обязателен для заполнения")
        
        # Базовая валидация формата (можно расширить)
        cleaned_phone = value.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if len(cleaned_phone) < 10:
            raise serializers.ValidationError("Некорректный формат телефона")
        
        return value
    
    def validate_name(self, value):
        """Валидация имени"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("ФИО обязательно для заполнения")
        
        if len(value.strip()) < 2:
            raise serializers.ValidationError("ФИО должно содержать минимум 2 символа")
        
        return value.strip()
    
    def validate_email(self, value):
        """Валидация email"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Email обязателен для заполнения")
        
        return value.strip().lower()


class FreedomPayCreatePaymentSerializer(serializers.Serializer):
    """Сериализатор для создания платежа через FreedomPay"""
    
    # Основные поля
    amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        min_value=Decimal('0.01'),
        help_text="Сумма пожертвования"
    )
    currency = serializers.ChoiceField(
        choices=Donation.Currency.choices,
        default=Donation.Currency.KGS,
        help_text="Валюта пожертвования"
    )
    
    # reCAPTCHA поле
    recaptcha_token = serializers.CharField(
        required=True,
        allow_blank=True,
        help_text="Токен reCAPTCHA v2 (опционально в режиме разработки)"
    )
    type = serializers.CharField(
        help_text="Тип пожертвования (one-time, one_time, monthly, yearly, quarterly)"
    )
    
    # Данные пользователя (если не авторизован)
    user_info = UserInfoSerializer(required=False, help_text="Данные пользователя (если не авторизован)")
    
    # ID пользователя (если авторизован)
    user_id = serializers.IntegerField(required=False, help_text="ID пользователя (если авторизован)")
    
    # Дополнительные поля
    campaign_id = serializers.IntegerField(required=False, allow_null=True, help_text="ID кампании")
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000, help_text="Комментарий донора")
    
    # Техническая информация
    ip_address = serializers.IPAddressField(required=False, help_text="IP адрес пользователя")
    user_agent = serializers.CharField(required=False, allow_blank=True, help_text="User Agent")
    
    def validate(self, data):
        """Валидация данных"""
        # Проверяем, что указаны либо user_info, либо user_id
        if not data.get('user_info') and not data.get('user_id'):
            raise serializers.ValidationError(
                "Необходимо указать либо user_info (для неавторизованных), либо user_id (для авторизованных)"
            )
        
        # Если указан user_id, проверяем что пользователь существует
        if data.get('user_id'):
            try:
                user = User.objects.get(id=data['user_id'])
                # Если пользователь авторизован, берем его данные
                if not data.get('user_info'):
                    data['user_info'] = {
                        'name': user.get_full_name() or user.username,
                        'email': user.email,
                        'phone': getattr(user, 'phone', '')
                    }
            except User.DoesNotExist:
                raise serializers.ValidationError("Пользователь с указанным ID не найден")
        
        # Проверяем кампанию если указана
        if data.get('campaign_id'):
            try:
                campaign = DonationCampaign.objects.get(id=data['campaign_id'])
                if campaign.status != DonationCampaign.CampaignStatus.ACTIVE:
                    raise serializers.ValidationError("Кампания не активна")
            except DonationCampaign.DoesNotExist:
                raise serializers.ValidationError("Кампания не найдена")
        
        return data
    
    def validate_amount(self, value):
        """Валидация суммы"""
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        
        # Максимальная сумма (можно настроить)
        max_amount = Decimal('1000000.00')
        if value > max_amount:
            raise serializers.ValidationError(f"Максимальная сумма пожертвования: {max_amount}")
        
        return value
    
    def validate_type(self, value):
        """Валидация типа пожертвования"""
        if not value:
            raise serializers.ValidationError("Тип пожертвования обязателен")
        
        # Приводим к нижнему регистру и убираем пробелы
        value_lower = value.lower().strip()
        
        # Нормализуем значение (заменяем дефис на подчеркивание для унификации)
        normalized_value = value_lower.replace('-', '_')
        
        # Получаем допустимые значения из модели
        valid_types = [choice[0] for choice in Donation.DonationType.choices]
        
        # Проверяем, что нормализованное значение есть в допустимых типах
        if normalized_value not in valid_types:
            raise serializers.ValidationError(
                f"Недопустимый тип пожертвования. Допустимые значения: {', '.join(valid_types)}"
            )
        
        # Возвращаем нормализованное значение (уже проверенное)
        return normalized_value


class FreedomPayPaymentResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа при создании платежа"""
    success = serializers.BooleanField()
    payment_url = serializers.URLField(required=False)
    order_id = serializers.CharField(required=False)
    payment_id = serializers.CharField(required=False)
    message = serializers.CharField()
    error = serializers.CharField(required=False)
    donation_uuid = serializers.UUIDField(required=False)
