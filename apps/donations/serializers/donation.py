from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal

from ..models import (
    Donation,
    DonationTransaction,
    DonationCampaign,
)

User = get_user_model()


class DonationCampaignSerializer(serializers.ModelSerializer):
    """Сериализатор для кампаний пожертвований"""
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = DonationCampaign
        fields = [
            'uuid', 'name', 'slug', 'description', 'image',
            'goal_amount', 'raised_amount', 'progress_percentage',
            'status', 'start_date', 'end_date', 'is_featured',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'raised_amount', 'created_at', 'updated_at']


class DonationCampaignListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка кампаний (краткая информация)"""
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = DonationCampaign
        fields = [
            'uuid', 'name', 'slug', 'image', 'goal_amount', 
            'raised_amount', 'progress_percentage', 'is_featured'
        ]


class DonationTransactionSerializer(serializers.ModelSerializer):
    """Сериализатор для транзакций пожертвований"""

    class Meta:
        model = DonationTransaction
        fields = [
            'uuid', 'transaction_id', 'external_transaction_id',
            'amount', 'currency', 'status', 'transaction_type',
            'payment_gateway', 'created_at', 'processed_at',
            'error_code', 'error_message'
        ]
        read_only_fields = ['uuid', 'created_at', 'processed_at']


class DonationCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пожертвования"""
    
    # Дополнительные поля для обработки
    accept_terms = serializers.BooleanField(write_only=True, help_text="Согласие с условиями")
    subscribe_newsletter = serializers.BooleanField(default=False, write_only=True, help_text="Подписка на новости")
    
    # Переопределяем поля, чтобы сделать их обязательными
    donor_email = serializers.EmailField(
        required=True,
        allow_blank=False,
        help_text="Email донора (обязательно)"
    )
    donor_phone = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=20,
        help_text="Телефон донора (обязательно)"
    )
    donor_full_name = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=255,
        help_text="ФИО донора (обязательно)"
    )
    
    class Meta:
        model = Donation
        fields = [
            'campaign', 'donor_email', 'donor_phone', 'donor_full_name',
            'amount', 'currency', 'donation_type', 'payment_method',
            'donor_comment', 'accept_terms', 'subscribe_newsletter'
        ]
        
    def validate_amount(self, value):
        """Валидация суммы пожертвования"""
        if value <= Decimal('0'):
            raise serializers.ValidationError("Сумма должна быть больше 0")
        
        # Минимальная сумма в зависимости от валюты
        min_amounts = {
            'KGS': Decimal('10.00'),
            'USD': Decimal('1.00'),
            'EUR': Decimal('1.00'),
            'RUB': Decimal('50.00'),
        }
        
        currency = self.initial_data.get('currency', 'KGS')
        min_amount = min_amounts.get(currency, Decimal('10.00'))
        
        if value < min_amount:
            raise serializers.ValidationError(
                f"Минимальная сумма для {currency}: {min_amount}"
            )
            
        return value
    
    def validate_accept_terms(self, value):
        """Валидация согласия с условиями"""
        if not value:
            raise serializers.ValidationError("Необходимо принять условия соглашения")
        return value
    
    def validate_donor_phone(self, value):
        """Валидация телефона донора"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Телефон обязателен для заполнения")
        
        # Базовая валидация формата
        cleaned_phone = value.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        if len(cleaned_phone) < 10:
            raise serializers.ValidationError("Некорректный формат телефона. Минимум 10 цифр")
        
        return value.strip()
    
    def validate_donor_full_name(self, value):
        """Валидация ФИО донора"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("ФИО обязательно для заполнения")
        
        if len(value.strip()) < 2:
            raise serializers.ValidationError("ФИО должно содержать минимум 2 символа")
        
        return value.strip()
    
    def validate_donor_email(self, value):
        """Валидация email донора"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Email обязателен для заполнения")
        
        return value.strip().lower()
    
    def validate(self, attrs):
        """Общая валидация данных пожертвования"""
        donation_type = attrs.get('donation_type')
        request = self.context.get('request')
        
        # Проверяем, что для рекуррентных подписок пользователь авторизован
        if donation_type in ['monthly', 'quarterly', 'yearly']:
            if not request or not request.user.is_authenticated:
                donation_type_display = {
                    'monthly': 'ежемесячной',
                    'quarterly': 'ежеквартальной',
                    'yearly': 'ежегодной'
                }.get(donation_type, 'рекуррентной')
                
                raise serializers.ValidationError({
                    'donation_type': f'Для оформления {donation_type_display} подписки необходимо войти в аккаунт или зарегистрироваться'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Создание пожертвования"""
        # Удаляем вспомогательные поля
        validated_data.pop('accept_terms', None)
        subscribe_newsletter = validated_data.pop('subscribe_newsletter', False)
        
        # Получаем дополнительную информацию из контекста
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            
            # Если пользователь авторизован, привязываем его
            if request.user.is_authenticated:
                validated_data['user'] = request.user
        
        # Устанавливаем рекуррентный флаг
        if validated_data['donation_type'] != 'one_time':
            validated_data['is_recurring'] = True
            # Устанавливаем дату следующего платежа
            validated_data['next_payment_date'] = self.calculate_next_payment_date(
                validated_data['donation_type']
            )
            # Устанавливаем начальный статус подписки
            validated_data['subscription_status'] = 'pending'
        
        # Создаем пожертвование
        with transaction.atomic():
            donation = Donation.objects.create(**validated_data)
            
            # Логируем согласие на рекуррентные платежи если это рекуррентное пожертвование
            if donation.is_recurring:
                self._log_recurring_consent(donation, request)
            
            # TODO: Интеграция с платежной системой
            # payment_result = self.process_payment(donation)
            
            # TODO: Подписка на новости если нужно
            # if subscribe_newsletter:
            #     self.subscribe_to_newsletter(donation.donor_email)
            
        return donation
    
    def _log_recurring_consent(self, donation, request):
        """Логирует согласие на рекуррентные платежи"""
        try:
            from ..services.consent_logger import ConsentLoggerService
            
            consent_logger = ConsentLoggerService()
            
            # Текст согласия
            consent_text = (
                f"Я соглашаюсь на ежемесячные/ежеквартальные/ежегодные автоматические списания "
                f"в размере {donation.amount} {donation.currency} для поддержки "
                f"фонда SOS Детские деревни Кыргызстана. "
                f"Я понимаю, что могу отменить подписку в любое время."
            )
            
            # Получаем ID сессии
            session_id = request.session.session_key if request.session else None
            
            consent_logger.log_recurring_consent(
                donation=donation,
                request=request,
                consent_text=consent_text,
                session_id=session_id
            )
            
        except Exception as e:
            # Логируем ошибку, но не прерываем создание пожертвования
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log recurring consent: {e}")
    
    def get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def calculate_next_payment_date(self, donation_type):
        """Расчет даты следующего платежа"""
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        
        now = datetime.now()
        
        if donation_type == 'monthly':
            return now + relativedelta(months=1)
        elif donation_type == 'quarterly':
            return now + relativedelta(months=3)
        elif donation_type == 'yearly':
            return now + relativedelta(years=1)
        
        return None


class DonationSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра пожертвований"""
    campaign = DonationCampaignListSerializer(read_only=True)
    transactions = DonationTransactionSerializer(many=True, read_only=True)
    subscription_status_display = serializers.CharField(
        source='get_subscription_status_display', 
        read_only=True
    )
    
    # Computed поля для удобства проверки на фронтенде
    is_subscription_active = serializers.SerializerMethodField()
    can_cancel_subscription = serializers.SerializerMethodField()
    can_resume_subscription = serializers.SerializerMethodField()
    can_pause_subscription = serializers.SerializerMethodField()
    
    class Meta:
        model = Donation
        fields = [
            'uuid', 'donation_code', 'campaign', 'donor_full_name',
            'donor_email', 'donor_phone', 'amount', 'currency',
            'donation_type', 'payment_method', 'status', 'donor_source',
            'is_recurring', 'next_payment_date', 'recurring_active',
            'subscription_status', 'subscription_status_display',
            'is_subscription_active', 'can_cancel_subscription',
            'can_resume_subscription', 'can_pause_subscription',
            'donor_comment', 'created_at', 'updated_at', 'payment_completed_at',
            'transactions'
        ]
        read_only_fields = [
            'uuid', 'donation_code', 'status', 'subscription_status',
            'created_at', 'updated_at', 'payment_completed_at'
        ]
    
    def get_is_subscription_active(self, obj):
        """Проверяет, активна ли подписка"""
        return (
            obj.is_recurring and 
            obj.subscription_status == Donation.SubscriptionStatus.ACTIVE
        )
    
    def get_can_cancel_subscription(self, obj):
        """Проверяет, можно ли отменить подписку"""
        return (
            obj.is_recurring and 
            obj.subscription_status in [
                Donation.SubscriptionStatus.ACTIVE,
                Donation.SubscriptionStatus.PAUSED
            ]
        )
    
    def get_can_resume_subscription(self, obj):
        """Проверяет, можно ли возобновить подписку"""
        return (
            obj.is_recurring and 
            obj.subscription_status in [
                Donation.SubscriptionStatus.PAUSED,
                Donation.SubscriptionStatus.CANCELLED
            ]
        )
    
    def get_can_pause_subscription(self, obj):
        """Проверяет, можно ли приостановить подписку"""
        return (
            obj.is_recurring and 
            obj.subscription_status == Donation.SubscriptionStatus.ACTIVE
        )


class DonationListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка пожертвований (краткая информация)"""
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    subscription_status_display = serializers.CharField(
        source='get_subscription_status_display', 
        read_only=True
    )
    
    # Computed поля для удобства проверки на фронтенде
    is_subscription_active = serializers.SerializerMethodField()
    can_cancel_subscription = serializers.SerializerMethodField()
    can_resume_subscription = serializers.SerializerMethodField()
    can_pause_subscription = serializers.SerializerMethodField()
    
    class Meta:
        model = Donation
        fields = [
            'uuid', 'donation_code', 'campaign_name', 'donor_full_name',
            'amount', 'currency', 'donation_type', 'status', 
            'is_recurring', 'subscription_status', 'subscription_status_display',
            'is_subscription_active', 'can_cancel_subscription', 
            'can_resume_subscription', 'can_pause_subscription',
            'created_at'
        ]
    
    def get_is_subscription_active(self, obj):
        """Проверяет, активна ли подписка"""
        return (
            obj.is_recurring and 
            obj.subscription_status == Donation.SubscriptionStatus.ACTIVE
        )
    
    def get_can_cancel_subscription(self, obj):
        """Проверяет, можно ли отменить подписку"""
        return (
            obj.is_recurring and 
            obj.subscription_status in [
                Donation.SubscriptionStatus.ACTIVE,
                Donation.SubscriptionStatus.PAUSED
            ]
        )
    
    def get_can_resume_subscription(self, obj):
        """Проверяет, можно ли возобновить подписку"""
        return (
            obj.is_recurring and 
            obj.subscription_status in [
                Donation.SubscriptionStatus.PAUSED,
                Donation.SubscriptionStatus.CANCELLED
            ]
        )
    
    def get_can_pause_subscription(self, obj):
        """Проверяет, можно ли приостановить подписку"""
        return (
            obj.is_recurring and 
            obj.subscription_status == Donation.SubscriptionStatus.ACTIVE
        )


class DonationStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики пожертвований"""
    total_donations = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_donors = serializers.IntegerField()
    recurring_donations = serializers.IntegerField()
    average_donation = serializers.DecimalField(max_digits=15, decimal_places=2)
    top_campaigns = serializers.ListField()
    monthly_stats = serializers.ListField()


class DonorStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики доноров"""
    total_personal_donations = serializers.IntegerField()
    total_personal_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_subscriptions = serializers.IntegerField()
    last_donation_date = serializers.DateTimeField()
    donation_history = DonationListSerializer(many=True)