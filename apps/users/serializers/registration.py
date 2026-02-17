from apps.users.validators.registration import RegisterValidator
from rest_framework import serializers

from apps.users.models.user import User


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(min_length=2, max_length=100)
    last_name = serializers.CharField(min_length=2, max_length=100)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    consent_data_processing = serializers.BooleanField(required=True)

    def validate_email(self, value):
        RegisterValidator().validate(value)
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

    def validate_phone(self, value):
        """Валидация номера телефона"""
        if value and not value.startswith('+'):
            raise serializers.ValidationError("Номер телефона должен начинаться с '+'")
        return value

    def validate_consent_data_processing(self, value):
        """Валидация согласия на обработку данных"""
        if not value:
            raise serializers.ValidationError("Необходимо согласие на обработку персональных данных")
        return value

    def validate(self, attrs):
        """Валидация совпадения паролей"""
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Пароли не совпадают'
            })
        
        return attrs

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name", "phone", "consent_data_processing"]


