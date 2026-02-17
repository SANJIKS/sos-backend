from django.core.mail import EmailMessage
from django.conf import settings
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import models
from django_celery_beat.models import PeriodicTask, IntervalSchedule

from apps.users.models.user import User
from apps.users.models.two_factor import TwoFactorAuth, TwoFactorLog
from apps.users.services.two_factor import TwoFactorCodeService, TwoFactorLogService


@shared_task(name="apps.users.tasks.send_email_confirmation_code")
def send_email_confirmation_code(user_id: int, code: str):
    user = User.objects.get(id=user_id)
    email = EmailMessage(
        subject="Подтверждение Email",
        body=f"Ваш код подтверждения: {code}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.send()


@shared_task(name="apps.users.tasks.send_two_factor_email")
def send_two_factor_email(subject: str, message: str, recipient_list: list, from_email: str = None):
    """
    Отправка email для двухфакторной аутентификации через Celery
    
    Args:
        subject: Тема письма
        message: Текст письма
        recipient_list: Список получателей
        from_email: Email отправителя
    """
    if from_email is None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
    
    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=recipient_list,
        )
        email.send()
        return f"Email отправлен на {', '.join(recipient_list)}"
    except Exception as e:
        return f"Ошибка отправки email: {str(e)}"


@shared_task(name="apps.users.tasks.cleanup_expired_two_factor_codes")
def cleanup_expired_two_factor_codes():
    """Очистка истекших кодов 2FA"""
    try:
        cleaned_count = TwoFactorCodeService.cleanup_expired_codes()
        return f"Очищено {cleaned_count} истекших кодов 2FA"
    except Exception as e:
        return f"Ошибка при очистке кодов 2FA: {str(e)}"


@shared_task(name="apps.users.tasks.cleanup_old_two_factor_logs")
def cleanup_old_two_factor_logs():
    """Очистка старых логов 2FA (старше 90 дней)"""
    try:
        cleaned_count = TwoFactorLogService.cleanup_old_logs(days=90)
        return f"Очищено {cleaned_count} старых логов 2FA"
    except Exception as e:
        return f"Ошибка при очистке логов 2FA: {str(e)}"


@shared_task(name="apps.users.tasks.send_two_factor_code_reminder")
def send_two_factor_code_reminder():
    """Отправка напоминаний о необходимости 2FA для админов"""
    # Находим админов без включенной 2FA
    admins_without_2fa = User.objects.filter(
        is_staff=True,
        is_active=True
    ).exclude(
        two_factor_auth__status__in=['enabled', 'required']
    )
    
    reminder_count = 0
    for admin in admins_without_2fa:
        try:
            send_two_factor_email.delay(
                subject="Напоминание о настройке двухфакторной аутентификации",
                message=f"""
                Уважаемый {admin.full_name},
                
                Для доступа к админ-панели необходимо включить двухфакторную аутентификацию.
                
                Перейдите по ссылке для настройки: {settings.SITE_URL}/user/admin/2fa/setup/
                
                С уважением,
                Команда SOS Детские деревни Кыргызстана
                """,
                recipient_list=[admin.email]
            )
            reminder_count += 1
        except Exception as e:
            continue
    
    return f"Отправлено {reminder_count} напоминаний о 2FA"


@shared_task(name="apps.users.tasks.check_two_factor_security")
def check_two_factor_security():
    """Проверка безопасности 2FA - поиск подозрительной активности"""
    # Проверяем пользователей с большим количеством неудачных попыток
    suspicious_users = TwoFactorAuth.objects.filter(
        failed_attempts__gte=3,
        last_failed_attempt__gte=timezone.now() - timedelta(hours=1)
    )
    
    security_issues = []
    
    for two_factor_auth in suspicious_users:
        security_issues.append({
            'user_email': two_factor_auth.user.email,
            'failed_attempts': two_factor_auth.failed_attempts,
            'last_failed_attempt': two_factor_auth.last_failed_attempt,
            'issue_type': 'multiple_failed_attempts'
        })
    
    # Проверяем необычную активность по IP
    recent_logs = TwoFactorLog.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).values('ip_address').annotate(
        count=models.Count('id')
    ).filter(count__gte=10)
    
    for log in recent_logs:
        security_issues.append({
            'ip_address': log['ip_address'],
            'activity_count': log['count'],
            'issue_type': 'high_activity_from_ip'
        })
    
    # Если найдены проблемы безопасности, отправляем уведомление администраторам
    if security_issues:
        admin_emails = User.objects.filter(
            is_superuser=True,
            is_active=True
        ).values_list('email', flat=True)
        
        if admin_emails:
            send_two_factor_email.delay(
                subject="⚠️ Обнаружены проблемы безопасности 2FA",
                message=f"""
                Обнаружены проблемы безопасности в системе двухфакторной аутентификации:
                
                Количество проблем: {len(security_issues)}
                
                Детали:
                {chr(10).join([f"- {issue.get('user_email', issue.get('ip_address', 'Unknown'))}: {issue.get('issue_type', 'Unknown issue')}" for issue in security_issues])}
                
                Проверьте логи системы для получения дополнительной информации.
                """,
                recipient_list=list(admin_emails)
            )
    
    return {
        'security_issues': security_issues,
        'total_issues': len(security_issues)
    }


def setup_periodic_tasks():
    """Настройка периодических задач для 2FA"""
    
    # Очистка истекших кодов каждые 10 минут
    cleanup_codes_task, created = PeriodicTask.objects.get_or_create(
        name='Cleanup expired 2FA codes',
        defaults={
            'task': 'apps.users.tasks.cleanup_expired_two_factor_codes',
            'interval': IntervalSchedule.objects.get_or_create(
                every=10,
                period=IntervalSchedule.MINUTES,
            )[0],
            'enabled': True,
        }
    )
    
    # Очистка старых логов каждый день
    cleanup_logs_task, created = PeriodicTask.objects.get_or_create(
        name='Cleanup old 2FA logs',
        defaults={
            'task': 'apps.users.tasks.cleanup_old_two_factor_logs',
            'interval': IntervalSchedule.objects.get_or_create(
                every=1,
                period=IntervalSchedule.DAYS,
            )[0],
            'enabled': True,
        }
    )
    
    # Проверка безопасности каждый час
    security_check_task, created = PeriodicTask.objects.get_or_create(
        name='Check 2FA security',
        defaults={
            'task': 'apps.users.tasks.check_two_factor_security',
            'interval': IntervalSchedule.objects.get_or_create(
                every=1,
                period=IntervalSchedule.HOURS,
            )[0],
            'enabled': True,
        }
    )
    
    # Напоминания админам каждую неделю
    reminder_task, created = PeriodicTask.objects.get_or_create(
        name='Send 2FA reminders to admins',
        defaults={
            'task': 'apps.users.tasks.send_two_factor_code_reminder',
            'interval': IntervalSchedule.objects.get_or_create(
                every=7,
                period=IntervalSchedule.DAYS,
            )[0],
            'enabled': True,
        }
    )
    
    return {
        'cleanup_codes': cleanup_codes_task,
        'cleanup_logs': cleanup_logs_task,
        'security_check': security_check_task,
        'reminder': reminder_task,
    }
