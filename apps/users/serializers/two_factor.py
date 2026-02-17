from rest_framework import serializers
from apps.users.models import TwoFactorAuth, TwoFactorCode, TwoFactorBackupCode, TwoFactorLog


class TwoFactorAuthSerializer(serializers.ModelSerializer):
    """Сериализатор для основной модели 2FA"""
    
    is_enabled = serializers.ReadOnlyField()
    is_locked = serializers.ReadOnlyField()
    backup_codes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TwoFactorAuth
        fields = [
            'id', 'auth_method', 'status', 'is_required', 'backup_codes_enabled',
            'is_enabled', 'is_locked', 'backup_codes_count', 'last_used_at',
            'failed_attempts', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_required', 'backup_codes_enabled', 'is_enabled', 'is_locked',
            'backup_codes_count', 'last_used_at', 'failed_attempts', 'created_at', 'updated_at'
        ]
    
    def get_backup_codes_count(self, obj):
        """Получение количества неиспользованных резервных кодов"""
        return TwoFactorBackupCode.objects.filter(
            two_factor_auth=obj,
            is_used=False
        ).count()


class SendTwoFactorCodeSerializer(serializers.Serializer):
    """Сериализатор для отправки кода 2FA"""
    
    auth_method = serializers.ChoiceField(
        choices=TwoFactorAuth.AuthMethod.choices,
        default=TwoFactorAuth.AuthMethod.EMAIL
    )
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        if not user.is_authenticated:
            raise serializers.ValidationError("Пользователь не аутентифицирован")
        
        # Проверяем, не заблокирована ли 2FA
        two_factor_auth = user.two_factor_auth
        if two_factor_auth.is_locked:
            raise serializers.ValidationError("2FA временно заблокирована из-за неудачных попыток")
        
        # Проверяем ограничение частоты
        from apps.users.services.two_factor import TwoFactorRateLimitService
        if TwoFactorRateLimitService.is_rate_limited(user, 'send_code', max_attempts=3, window_minutes=60):
            raise serializers.ValidationError("Превышен лимит отправки кодов. Попробуйте позже")
        
        return attrs


class VerifyTwoFactorCodeSerializer(serializers.Serializer):
    """Сериализатор для проверки кода 2FA"""
    
    code = serializers.CharField(max_length=6, min_length=6)
    use_backup_code = serializers.BooleanField(default=False)
    
    def validate_code(self, value):
        """Валидация кода"""
        if not value.isdigit():
            raise serializers.ValidationError("Код должен состоять только из цифр")
        return value
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        if not user.is_authenticated:
            raise serializers.ValidationError("Пользователь не аутентифицирован")
        
        # Проверяем, не заблокирована ли 2FA
        two_factor_auth = user.two_factor_auth
        if two_factor_auth.is_locked:
            raise serializers.ValidationError("2FA временно заблокирована из-за неудачных попыток")
        
        return attrs


class EnableTwoFactorSerializer(serializers.Serializer):
    """Сериализатор для включения 2FA"""
    
    auth_method = serializers.ChoiceField(
        choices=TwoFactorAuth.AuthMethod.choices,
        default=TwoFactorAuth.AuthMethod.EMAIL
    )
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        if not user.is_authenticated:
            raise serializers.ValidationError("Пользователь не аутентифицирован")
        
        # Проверяем, не включена ли уже 2FA
        if user.two_factor_auth.is_enabled:
            raise serializers.ValidationError("2FA уже включена")
        
        return attrs


class DisableTwoFactorSerializer(serializers.Serializer):
    """Сериализатор для отключения 2FA"""
    
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        if not user.is_authenticated:
            raise serializers.ValidationError("Пользователь не аутентифицирован")
        
        # Проверяем пароль
        if not user.check_password(attrs['password']):
            raise serializers.ValidationError("Неверный пароль")
        
        # Проверяем, включена ли 2FA
        if not user.two_factor_auth.is_enabled:
            raise serializers.ValidationError("2FA не включена")
        
        # Проверяем, не обязательна ли 2FA
        if user.two_factor_auth.is_required:
            raise serializers.ValidationError("2FA обязательна для вашей роли")
        
        return attrs


class GenerateBackupCodesSerializer(serializers.Serializer):
    """Сериализатор для генерации резервных кодов"""
    
    count = serializers.IntegerField(min_value=5, max_value=20, default=10)
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        if not user.is_authenticated:
            raise serializers.ValidationError("Пользователь не аутентифицирован")
        
        # Проверяем, включена ли 2FA
        if not user.two_factor_auth.is_enabled:
            raise serializers.ValidationError("2FA должна быть включена для генерации резервных кодов")
        
        return attrs


class BackupCodesResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа с резервными кодами"""
    
    codes = serializers.ListField(child=serializers.CharField())
    warning = serializers.CharField(default="Сохраните эти коды в безопасном месте. Они показываются только один раз!")


class TwoFactorLogSerializer(serializers.ModelSerializer):
    """Сериализатор для логов 2FA"""
    
    class Meta:
        model = TwoFactorLog
        fields = [
            'id', 'log_type', 'status', 'description', 'ip_address',
            'user_agent', 'created_at'
        ]
        read_only_fields = fields


class TwoFactorStatusSerializer(serializers.Serializer):
    """Сериализатор для статуса 2FA"""
    
    is_enabled = serializers.BooleanField()
    is_required = serializers.BooleanField()
    is_locked = serializers.BooleanField()
    auth_method = serializers.CharField()
    backup_codes_enabled = serializers.BooleanField()
    backup_codes_count = serializers.IntegerField()
    failed_attempts = serializers.IntegerField()
    last_used_at = serializers.DateTimeField(allow_null=True)
    lock_until = serializers.DateTimeField(allow_null=True)


class TwoFactorSetupSerializer(serializers.Serializer):
    """Сериализатор для настройки 2FA"""
    
    step = serializers.CharField()  # 'email_verification', 'backup_codes', 'complete'
    email_verified = serializers.BooleanField()
    backup_codes_generated = serializers.BooleanField()
    setup_complete = serializers.BooleanField() 