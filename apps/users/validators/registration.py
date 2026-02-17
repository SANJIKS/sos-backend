from django.core.exceptions import ValidationError

from apps.users.models.user import User


class RegisterValidator:
    @staticmethod
    def validate(email: str):
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже зарегистрирован.")
