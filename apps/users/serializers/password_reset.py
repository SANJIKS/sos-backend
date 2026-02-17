from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

User = get_user_model()


class ForgotPasswordSerializer(serializers.Serializer):
    """Сериализатор для запроса восстановления пароля"""
    
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Проверяем, что пользователь с таким email существует"""
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Введите корректный email адрес")
        
        if not User.objects.filter(email=value, is_active=True).exists():
            # Не раскрываем информацию о том, существует ли пользователь
            # Возвращаем успешный ответ в любом случае для безопасности
            pass
        
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """Сериализатор для сброса пароля по токену"""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Пароли не совпадают")
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


class VerifyResetTokenSerializer(serializers.Serializer):
    """Сериализатор для проверки токена восстановления пароля"""
    
    token = serializers.CharField(required=True)

