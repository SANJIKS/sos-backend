from django.core.exceptions import ValidationError

from apps.users.models.confirm_code import ConfirmCode


class VerifyEmailCodeUseCase:
    @staticmethod
    def execute(email: str, code: str) -> None:
        try:
            confirm = ConfirmCode.objects.select_related("user").filter(
                user__email=email,
                code=code,
                is_used=False,
                type=ConfirmCode.ConfirmCodeType.EMAIL
            ).latest("created_at")
        except ConfirmCode.DoesNotExist:
            raise ValidationError("Неверный или просроченный код")

        if confirm.is_expired():
            raise ValidationError("Код истёк")

        confirm.is_used = True
        confirm.save()

        user = confirm.user
        user.is_email_confirmed = True
        user.save()
