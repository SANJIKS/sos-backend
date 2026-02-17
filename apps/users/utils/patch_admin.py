"""
Автоматическое применение проверки прав доступа ко всем ModelAdmin классам
"""


def patch_model_admin():
    """
    Автоматически применяет AdminAccessMixin ко всем ModelAdmin классам
    через monkey patching методов проверки прав
    """
    from unfold.admin import ModelAdmin
    
    # Сохраняем оригинальные методы
    _original_has_module_permission = ModelAdmin.has_module_permission
    _original_has_view_permission = ModelAdmin.has_view_permission
    _original_has_add_permission = ModelAdmin.has_add_permission
    _original_has_change_permission = ModelAdmin.has_change_permission
    _original_has_delete_permission = ModelAdmin.has_delete_permission
    
    def patched_has_module_permission(self, request):
        """Патч для has_module_permission"""
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return _original_has_module_permission(self, request)
        
        # Проверяем стандартную логику
        if not _original_has_module_permission(self, request):
            return False
        
        # Проверяем через нашу систему прав
        from apps.users.utils.admin_permissions import user_can_access_model
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return user_can_access_model(request.user, app_label, model_name)
    
    def patched_has_view_permission(self, request, obj=None):
        """Патч для has_view_permission"""
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return _original_has_view_permission(self, request, obj)
        
        # Проверяем стандартную логику
        if not _original_has_view_permission(self, request, obj):
            return False
        
        # Проверяем через нашу систему прав
        from apps.users.utils.admin_permissions import user_can_perform_action
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return user_can_perform_action(request.user, app_label, model_name, 'view')
    
    def patched_has_add_permission(self, request):
        """Патч для has_add_permission"""
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return _original_has_add_permission(self, request)
        
        # Проверяем стандартную логику
        if not _original_has_add_permission(self, request):
            return False
        
        # Проверяем через нашу систему прав
        from apps.users.utils.admin_permissions import user_can_perform_action
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return user_can_perform_action(request.user, app_label, model_name, 'add')
    
    def patched_has_change_permission(self, request, obj=None):
        """Патч для has_change_permission"""
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return _original_has_change_permission(self, request, obj)
        
        # Проверяем стандартную логику
        if not _original_has_change_permission(self, request, obj):
            return False
        
        # Проверяем через нашу систему прав
        from apps.users.utils.admin_permissions import user_can_perform_action
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return user_can_perform_action(request.user, app_label, model_name, 'change')
    
    def patched_has_delete_permission(self, request, obj=None):
        """Патч для has_delete_permission"""
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return _original_has_delete_permission(self, request, obj)
        
        # Проверяем стандартную логику
        if not _original_has_delete_permission(self, request, obj):
            return False
        
        # Проверяем через нашу систему прав
        from apps.users.utils.admin_permissions import user_can_perform_action
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return user_can_perform_action(request.user, app_label, model_name, 'delete')
    
    # Применяем патчи
    ModelAdmin.has_module_permission = patched_has_module_permission
    ModelAdmin.has_view_permission = patched_has_view_permission
    ModelAdmin.has_add_permission = patched_has_add_permission
    ModelAdmin.has_change_permission = patched_has_change_permission
    ModelAdmin.has_delete_permission = patched_has_delete_permission

