from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_out

from apps.users.models import TwoFactorAuth
from apps.users.services.two_factor import TwoFactorService

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile_data(sender, instance, created, **kwargs):
    """Автоматическое создание связанных объектов при создании пользователя"""
    if created:
        # Создаем объект 2FA
        TwoFactorService.get_or_create_two_factor_auth(instance)
        
        # Профиль создается автоматически через модель User
        # Дополнительные действия при создании профиля можно добавить здесь
        
        # Логируем создание пользователя
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"New user profile created: {instance.email} (UUID: {instance.uuid})")


@receiver(post_save, sender=User)
def update_two_factor_requirements(sender, instance, **kwargs):
    """Обновление требований 2FA при изменении статуса пользователя"""
    if hasattr(instance, 'two_factor_auth'):
        two_factor_auth = instance.two_factor_auth
        
        # Если пользователь стал админом, делаем 2FA обязательной
        if instance.is_staff or instance.is_superuser:
            two_factor_auth.is_required = True
            if two_factor_auth.status == TwoFactorAuth.Status.DISABLED:
                two_factor_auth.status = TwoFactorAuth.Status.REQUIRED
            two_factor_auth.save()
        
        # Если пользователь перестал быть админом, убираем обязательность
        elif not (instance.is_staff or instance.is_superuser):
            two_factor_auth.is_required = False
            if two_factor_auth.status == TwoFactorAuth.Status.REQUIRED:
                two_factor_auth.status = TwoFactorAuth.Status.DISABLED
            two_factor_auth.save()


@receiver(user_logged_out)
def clear_2fa_cookies(sender, request, user, **kwargs):
    """Очистка 2FA cookies при выходе пользователя"""
    if hasattr(request, 'response'):
        request.response.delete_cookie('2fa_verified')
        request.response.delete_cookie('2fa_verified_at') 