"""
Миксин для ModelAdmin с проверкой прав доступа
"""
from unfold.admin import ModelAdmin
from apps.users.utils.admin_permissions import (
    user_can_access_model,
    user_can_perform_action,
    user_has_admin_access,
)


class AdminAccessMixin:
    """
    Миксин для добавления проверки прав доступа к моделям в админке
    
    Использование:
        from apps.users.mixins.admin_permissions import AdminAccessMixin
        
        class MyModelAdmin(AdminAccessMixin, ModelAdmin):
            ...
    """
    
    def has_module_permission(self, request):
        """
        Проверить доступ к модулю (приложению)
        """
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return super().has_module_permission(request)
        
        # Проверяем доступ к модели через стандартную логику
        if not super().has_module_permission(request):
            return False
        
        # Проверяем доступ через нашу систему прав
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        
        return user_can_access_model(request.user, app_label, model_name)
    
    def has_view_permission(self, request, obj=None):
        """
        Проверить право просмотра
        """
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return super().has_view_permission(request, obj)
        
        # Проверяем стандартную логику
        if not super().has_view_permission(request, obj):
            return False
        
        # Проверяем через нашу систему прав
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        
        return user_can_perform_action(request.user, app_label, model_name, 'view')
    
    def has_add_permission(self, request):
        """
        Проверить право добавления
        """
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return super().has_add_permission(request)
        
        # Проверяем стандартную логику
        if not super().has_add_permission(request):
            return False
        
        # Проверяем через нашу систему прав
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        
        return user_can_perform_action(request.user, app_label, model_name, 'add')
    
    def has_change_permission(self, request, obj=None):
        """
        Проверить право изменения
        """
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return super().has_change_permission(request, obj)
        
        # Проверяем стандартную логику
        if not super().has_change_permission(request, obj):
            return False
        
        # Проверяем через нашу систему прав
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        
        return user_can_perform_action(request.user, app_label, model_name, 'change')
    
    def has_delete_permission(self, request, obj=None):
        """
        Проверить право удаления
        """
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return super().has_delete_permission(request, obj)
        
        # Проверяем стандартную логику
        if not super().has_delete_permission(request, obj):
            return False
        
        # Проверяем через нашу систему прав
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        
        return user_can_perform_action(request.user, app_label, model_name, 'delete')


class RestrictedModelAdmin(AdminAccessMixin, ModelAdmin):
    """
    Базовый класс ModelAdmin с автоматической проверкой прав доступа
    
    Используйте этот класс вместо стандартного unfold.admin.ModelAdmin
    для автоматической проверки прав доступа.
    
    Пример:
        from apps.users.mixins.admin_permissions import RestrictedModelAdmin
        
        @admin.register(MyModel)
        class MyModelAdmin(RestrictedModelAdmin):
            ...
    """
    pass




