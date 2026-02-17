from datetime import timedelta
from django.utils import timezone
from apps.users.models.confirm_code import ConfirmCode
from apps.users.services.code_generator import generate_confirmation_code
from apps.users.services.email import send_confirmation_email


class CreateConfirmCodeUseCase:
    @staticmethod
    def execute(user) -> ConfirmCode:
        code = generate_confirmation_code()
        confirm_code = ConfirmCode.objects.create(
            user=user,
            code=code,
            type=ConfirmCode.ConfirmCodeType.EMAIL,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        send_confirmation_email(user, code)
        return confirm_code