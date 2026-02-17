"""
Расширение стандартного admin.site для поддержки ограничения доступа по правам
"""
from django.contrib import admin
from types import MethodType
from apps.users.utils.admin_permissions import (
    user_can_access_app,
    user_can_access_model,
)


# Сохраняем оригинальные методы
# Важно: сохраняем до переопределения
_original_get_app_list = admin.site.get_app_list
_original_has_permission = admin.site.has_permission


def get_app_list_with_permissions(self, request, app_label=None):
    """
    Переопределенный метод get_app_list с учетом прав доступа
    """
    # Получаем стандартный список приложений
    # _original_get_app_list уже привязан к admin.site, вызываем его напрямую
    app_list = _original_get_app_list(request, app_label)
    
    # Superuser видит все приложения
    if request.user.is_superuser:
        return app_list
    
    # Если пользователь не staff, возвращаем пустой список
    if not request.user.is_staff:
        return []
    
    # Проверяем наличие активного доступа
    if not hasattr(request.user, 'admin_access') or not request.user.admin_access.is_active:
        return []
    
    # Фильтруем приложения по правам пользователя
    filtered_app_list = []
    
    for app in app_list:
        current_app_label = app.get('app_label')
        
        # Проверяем доступ к приложению
        if not user_can_access_app(request.user, current_app_label):
            continue
        
        # Фильтруем модели внутри приложения
        filtered_models = []
        
        for model in app.get('models', []):
            model_name = model.get('object_name')
            
            # Проверяем доступ к модели
            if user_can_access_model(request.user, current_app_label, model_name):
                filtered_models.append(model)
        
        # Если есть доступные модели, добавляем приложение
        if filtered_models:
            app['models'] = filtered_models
            filtered_app_list.append(app)
    
    return filtered_app_list


def has_permission_with_access_check(self, request):
    """
    Переопределенный метод has_permission с проверкой UserAdminAccess
    """
    # Анонимные пользователи не имеют доступа
    if not request.user.is_authenticated:
        return False
    
    # Superuser всегда имеет доступ
    if request.user.is_superuser:
        return True
    
    # Проверяем стандартную логику Django (is_staff, is_active)
    # _original_has_permission уже привязан к admin.site, вызываем его напрямую
    if not _original_has_permission(request):
        return False
    
    # Если пользователь staff, проверяем наличие активного доступа
    if request.user.is_staff:
        # Если нет UserAdminAccess, доступ запрещен
        if not hasattr(request.user, 'admin_access'):
            return False
        # Проверяем, что доступ активен
        return request.user.admin_access.is_active
    
    return False


# Переопределяем методы admin.site, правильно привязывая их как методы экземпляра
admin.site.get_app_list = MethodType(get_app_list_with_permissions, admin.site)
admin.site.has_permission = MethodType(has_permission_with_access_check, admin.site)

