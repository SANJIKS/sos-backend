from apps.users.tasks import send_email_confirmation_code, send_two_factor_email


def send_confirmation_email(user, code: str):
    """Отправка кода подтверждения email через Celery"""
    send_email_confirmation_code.delay(user.id, code)


def send_email(subject: str, message: str, recipient_list: list, from_email: str = None):
    """
    Отправка email сообщения через Celery
    
    Args:
        subject: Тема письма
        message: Текст письма
        recipient_list: Список получателей
        from_email: Email отправителя (если не указан, используется DEFAULT_FROM_EMAIL)
    """
    send_two_factor_email.delay(subject, message, recipient_list, from_email)
    return True
