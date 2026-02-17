from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from apps.users.models import PasswordResetToken
import logging
import os

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordResetService:
    """Сервис для восстановления пароля"""

    @staticmethod
    def send_reset_email(email, ip_address=None, user_agent=None):
        """
        Отправить email с ссылкой для восстановления пароля
        """
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Для безопасности не раскрываем, что пользователь не найден
            logger.info(f"Password reset requested for non-existent email: {email}")
            return True

        # Создаем токен
        reset_token = PasswordResetToken.create_for_user(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Формируем ссылку для сброса пароля
        # Используем русскую локаль по умолчанию, так как это defaultLocale в next-intl
        frontend_base_url = settings.FRONTEND_URL.rstrip('/')
        reset_url = f"{frontend_base_url}/ru/reset-password?token={reset_token.token}"

        # Подготавливаем контекст для шаблона
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': getattr(settings, 'SITE_NAME', 'SOS Детские деревни'),
            'expires_hours': 1,
        }

        try:
            # Отправляем email
            subject = 'Восстановление пароля - SOS Детские деревни'
            
            # Логируем информацию о путях к шаблонам
            from django.template.loader import get_template
            logger.info(f"TEMPLATES setting: {settings.TEMPLATES}")
            logger.info(f"BASE_DIR: {settings.BASE_DIR}")
            
            # Проверяем, существует ли папка templates
            templates_dir = os.path.join(settings.BASE_DIR, 'templates')
            logger.info(f"Templates directory exists: {os.path.exists(templates_dir)}")
            if os.path.exists(templates_dir):
                logger.info(f"Templates directory contents: {os.listdir(templates_dir)}")
                emails_dir = os.path.join(templates_dir, 'emails')
                logger.info(f"Emails directory exists: {os.path.exists(emails_dir)}")
                if os.path.exists(emails_dir):
                    logger.info(f"Emails directory contents: {os.listdir(emails_dir)}")
            
            # HTML версия
            try:
                html_message = render_to_string('emails/password_reset.html', context)
            except Exception as e:
                logger.error(f"Failed to render HTML template: {str(e)}")
                # Попробуем найти шаблон вручную
                try:
                    template = get_template('emails/password_reset.html')
                    logger.info(f"Template found at: {template.origin}")
                    html_message = template.render(context)
                except Exception as e2:
                    logger.error(f"Template not found even with get_template: {str(e2)}")
                    # Fallback to text version if HTML fails
                    html_message = None
            
            # Текстовая версия
            try:
                text_message = render_to_string('emails/password_reset.txt', context)
            except Exception as e:
                logger.error(f"Failed to render text template: {str(e)}")
                text_message = f"Восстановление пароля для {user.full_name}\n\nСсылка: {reset_url}\n\nСсылка действительна 1 час(а)."

            send_mail(
                subject=subject,
                message=text_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            logger.info(f"Password reset email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False

    @staticmethod
    def verify_reset_token(token):
        """
        Проверить валидность токена восстановления пароля
        """
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            
            if not reset_token.is_valid:
                return None, "Токен недействителен или истек"
            
            return reset_token, None
            
        except PasswordResetToken.DoesNotExist:
            return None, "Токен не найден"

    @staticmethod
    def reset_password(token, new_password):
        """
        Сбросить пароль по токену
        """
        reset_token, error = PasswordResetService.verify_reset_token(token)
        
        if error:
            return False, error

        try:
            # Устанавливаем новый пароль
            user = reset_token.user
            user.set_password(new_password)
            user.save(update_fields=['password'])

            # Отмечаем токен как использованный
            reset_token.mark_as_used()

            # Деактивируем все остальные токены пользователя
            PasswordResetToken.objects.filter(
                user=user,
                is_used=False
            ).exclude(id=reset_token.id).update(
                is_used=True,
                used_at=timezone.now()
            )

            logger.info(f"Password reset successful for user {user.email}")
            return True, "Пароль успешно изменен"

        except Exception as e:
            logger.error(f"Failed to reset password for token {token}: {str(e)}")
            return False, "Ошибка при смене пароля"

    @staticmethod
    def cleanup_expired_tokens():
        """
        Очистка истекших токенов (для периодического запуска)
        """
        try:
            count = PasswordResetToken.cleanup_expired()
            logger.info(f"Cleaned up {count} expired password reset tokens")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {str(e)}")
            return 0

