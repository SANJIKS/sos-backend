"""
Утилиты для проверки прав доступа пользователей к админке
"""
from typing import List, Optional


def user_has_admin_access(user) -> bool:
    """
    Проверить, есть ли у пользователя доступ к админке
    
    Args:
        user: Объект User
    
    Returns:
        bool: True если есть доступ
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superuser всегда имеет доступ
    if user.is_superuser:
        return True
    
    # Если is_staff = False, нет доступа
    if not user.is_staff:
        return False
    
    # Проверяем наличие UserAdminAccess
    if not hasattr(user, 'admin_access'):
        return False
    
    return user.admin_access.is_active


def user_can_access_app(user, app_label: str) -> bool:
    """
    Проверить доступ пользователя к приложению
    
    Args:
        user: Объект User
        app_label: Метка приложения (например, "news")
    
    Returns:
        bool: True если есть доступ
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superuser всегда имеет доступ
    if user.is_superuser:
        return True
    
    if not user.is_staff:
        return False
    
    if not hasattr(user, 'admin_access'):
        return False
    
    return user.admin_access.can_access_app(app_label)


def user_can_access_model(user, app_label: str, model_name: str) -> bool:
    """
    Проверить доступ пользователя к модели
    
    Args:
        user: Объект User
        app_label: Метка приложения (например, "news")
        model_name: Название модели (например, "News")
    
    Returns:
        bool: True если есть доступ
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superuser всегда имеет доступ
    if user.is_superuser:
        return True
    
    if not user.is_staff:
        return False
    
    if not hasattr(user, 'admin_access'):
        return False
    
    return user.admin_access.can_access_model(app_label, model_name)


def user_can_perform_action(user, app_label: str, model_name: str, action: str) -> bool:
    """
    Проверить право пользователя на выполнение действия
    
    Args:
        user: Объект User
        app_label: Метка приложения (например, "news")
        model_name: Название модели (например, "News")
        action: Действие ('view', 'add', 'change', 'delete')
    
    Returns:
        bool: True если действие разрешено
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superuser всегда имеет доступ
    if user.is_superuser:
        return True
    
    if not user.is_staff:
        return False
    
    if not hasattr(user, 'admin_access'):
        return False
    
    return user.admin_access.can_perform_action(app_label, model_name, action)


def get_user_allowed_apps(user) -> List[str]:
    """
    Получить список разрешенных приложений для пользователя
    
    Args:
        user: Объект User
    
    Returns:
        list: Список меток приложений
    """
    if not user or not user.is_authenticated:
        return []
    
    # Superuser имеет доступ ко всем приложениям
    # Но для обычных пользователей возвращаем пустой список
    # чтобы показать только разрешенные разделы
    if user.is_superuser:
        return []  # Пустой список означает "все приложения"
    
    if not user.is_staff:
        return []
    
    if not hasattr(user, 'admin_access'):
        return []
    
    return user.admin_access.get_allowed_apps()


def get_user_allowed_models(user, app_label: Optional[str] = None) -> List[str]:
    """
    Получить список разрешенных моделей для пользователя
    
    Args:
        user: Объект User
        app_label: Если указано, вернет только модели для этого приложения
    
    Returns:
        list: Список моделей в формате ["news.News", "faq.FAQ"]
    """
    if not user or not user.is_authenticated:
        return []
    
    # Superuser имеет доступ ко всем моделям
    if user.is_superuser:
        return []
    
    if not user.is_staff:
        return []
    
    if not hasattr(user, 'admin_access'):
        return []
    
    return user.admin_access.get_allowed_models(app_label)


def get_model_permissions(user, app_label: str, model_name: str) -> List[str]:
    """
    Получить список разрешенных действий для модели
    
    Args:
        user: Объект User
        app_label: Метка приложения
        model_name: Название модели
    
    Returns:
        list: Список разрешенных действий ['view', 'add', 'change', 'delete']
    """
    if not user or not user.is_authenticated:
        return []
    
    # Superuser имеет все права
    if user.is_superuser:
        return ['view', 'add', 'change', 'delete']
    
    if not user.is_staff:
        return []
    
    if not hasattr(user, 'admin_access'):
        return []
    
    return user.admin_access.get_model_permissions(app_label, model_name)


def get_available_admin_apps():
    """
    Получить список приложений, доступных для выбора в настройках прав
    
    Returns:
        dict: Словарь с информацией о приложениях и их моделями
        {
            'news': {
                'name': 'Новости',
                'models': ['News', 'NewsCategory', 'NewsTag']
            },
            ...
        }
    """
    from django.apps import apps
    from django.contrib import admin
    
    # Список системных приложений, которые должны быть скрыты
    SYSTEM_APPS = {
        'users',
        'donations',
        'donors',
        'qrcode',
        'common',
        'factories',
        'auth',
        'contenttypes',
        'sessions',
        'messages',
        'staticfiles',
        'admin',
        'sites',
    }
    
    # Список разрешенных приложений (контентные разделы)
    ALLOWED_APPS = {
        'news': 'Новости',
        'contacts': 'Контакты',
        'faq': 'FAQ',
        'success_stories': 'Истории успеха',
        'programs': 'Программы',
        'timeline': 'Временная линия',
        'principles': 'Принципы',
        'impact_results': 'Результаты воздействия',
        'donation_options': 'Варианты пожертвований',
        'social_networks': 'Социальные сети',
        'partners': 'Партнеры',
        'feedback': 'Отзывы',
        'locations': 'Локации',
        'vacancies': 'Вакансии',
        'banking_requisites': 'Банковские реквизиты',
        'digital_campaigns': 'Цифровые кампании',
    }
    
    available_apps = {}
    
    for app_label, app_name in ALLOWED_APPS.items():
        if app_label in SYSTEM_APPS:
            continue
        
        try:
            app_config = apps.get_app_config(app_label)
            models_list = []
            
            for model in app_config.get_models():
                # Пропускаем прокси-модели и абстрактные модели
                if model._meta.proxy or model._meta.abstract:
                    continue
                
                # Пропускаем модели без админки
                if not admin.site.is_registered(model):
                    continue
                
                models_list.append(model._meta.model_name)
            
            if models_list:
                available_apps[app_label] = {
                    'name': app_name,
                    'models': sorted(models_list)
                }
        except LookupError:
            # Приложение не найдено, пропускаем
            continue
    
    return available_apps

