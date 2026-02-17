"""
Permissions для работы с пожертвованиями
"""
from rest_framework import permissions


class DonationCreatePermission(permissions.BasePermission):
    """
    Кастомное разрешение для создания пожертвований:
    - Разовые пожертвования (one_time) - доступны всем (анонимным и авторизованным)
    - Рекуррентные пожертвования (monthly, quarterly, yearly) - только для авторизованных пользователей
    """
    
    message = "Для оформления подписки необходимо войти в аккаунт или зарегистрироваться"
    
    def has_permission(self, request, view):
        """
        Проверяет разрешение на основе типа пожертвования
        """
        # Для методов, отличных от POST (создание), разрешаем доступ
        if request.method != 'POST':
            return True
        
        # Получаем тип пожертвования из данных запроса
        donation_type = request.data.get('donation_type')
        
        # Если тип не указан, разрешаем (валидация произойдет в сериализаторе)
        if not donation_type:
            return True
        
        # Для разовых пожертвований разрешаем всем
        if donation_type == 'one_time':
            return True
        
        # Для рекуррентных пожертвований требуем авторизацию
        if donation_type in ['monthly', 'quarterly', 'yearly']:
            if not request.user.is_authenticated:
                self.message = (
                    f"Для оформления {'ежемесячной' if donation_type == 'monthly' else 'ежегодной' if donation_type == 'yearly' else 'ежеквартальной'} "
                    f"подписки необходимо войти в аккаунт или зарегистрироваться"
                )
                return False
            return True
        
        # По умолчанию разрешаем
        return True



