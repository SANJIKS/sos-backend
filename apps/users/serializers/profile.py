from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.donations.models import Donation

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для профиля пользователя (личные данные)"""
    
    class Meta:
        model = User
        fields = [
            'uuid',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'gender',
            'birth_date',
            'preferred_language',
            'city',
            'address',
            'postal_code',
            'email_notifications',
            'sms_notifications',
            'newsletter_subscription',
            'consent_data_processing',
            'consent_marketing',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'email', 'created_at', 'updated_at']

    def validate_phone(self, value):
        """Валидация номера телефона"""
        if value and not value.startswith('+'):
            raise serializers.ValidationError("Номер телефона должен начинаться с '+'")
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления профиля пользователя"""
    
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'gender',
            'birth_date',
            'preferred_language',
            'city',
            'address',
            'postal_code',
            'email_notifications',
            'sms_notifications',
            'newsletter_subscription',
            'consent_marketing',
        ]

    def validate_phone(self, value):
        """Валидация номера телефона"""
        if value and not value.startswith('+'):
            raise serializers.ValidationError("Номер телефона должен начинаться с '+'")
        return value

    def validate_first_name(self, value):
        """Валидация имени"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Имя должно содержать минимум 2 символа")
        return value.strip()

    def validate_last_name(self, value):
        """Валидация фамилии"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Фамилия должна содержать минимум 2 символа")
        return value.strip()

    def save(self, **kwargs):
        """Переопределяем save для автоматического обновления full_name"""
        instance = super().save(**kwargs)
        
        # Автоматически обновляем full_name если изменились first_name или last_name
        if 'first_name' in self.validated_data or 'last_name' in self.validated_data:
            # Обновляем full_name вручную
            instance.full_name = f"{instance.first_name} {instance.last_name}".strip()
            instance.save(update_fields=['full_name'])
        
        return instance


class DonationHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для истории пожертвований"""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    donation_type_display = serializers.CharField(source='get_donation_type_display', read_only=True)
    
    class Meta:
        model = Donation
        fields = [
            'uuid',
            'amount',
            'currency',
            'donation_type',
            'donation_type_display',
            'payment_method',
            'payment_method_display',
            'status',
            'status_display',
            'campaign_name',
            'is_recurring',
            'recurring_active',
            'next_payment_date',
            'created_at',
            'payment_completed_at',
        ]


class UserSubscriptionsSerializer(serializers.ModelSerializer):
    """Сериализатор для активных подписок пользователя"""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    donation_type_display = serializers.CharField(source='get_donation_type_display', read_only=True)
    
    class Meta:
        model = Donation
        fields = [
            'uuid',
            'amount',
            'currency',
            'donation_type',
            'donation_type_display',
            'payment_method',
            'payment_method_display',
            'campaign_name',
            'recurring_active',
            'next_payment_date',
            'created_at',
        ]


class UserStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики пользователя"""
    
    total_donated = serializers.DecimalField(max_digits=12, decimal_places=2)
    donation_count = serializers.IntegerField()
    active_subscriptions_count = serializers.IntegerField()
    first_donation_date = serializers.DateTimeField(allow_null=True)
    last_donation_date = serializers.DateTimeField(allow_null=True)
    favorite_campaign = serializers.CharField(allow_null=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля"""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Новые пароли не совпадают")
        return attrs

    def validate_new_password(self, value):
        """Валидация нового пароля"""
        if len(value) < 8:
            raise serializers.ValidationError("Пароль должен содержать минимум 8 символов")
        
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну цифру")
        
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну заглавную букву")
        
        return value

