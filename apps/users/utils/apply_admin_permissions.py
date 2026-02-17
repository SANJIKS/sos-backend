"""
Автоматическое применение проверки прав доступа ко всем зарегистрированным админкам
"""
from django.contrib import admin
from apps.users.mixins.admin_permissions import AdminAccessMixin


def apply_permissions_to_admin_classes():
    """
    Автоматически применяет AdminAccessMixin ко всем зарегистрированным ModelAdmin классам
    
    Это позволяет не изменять каждую админку вручную, а автоматически
    добавить проверку прав доступа ко всем существующим админкам.
    """
    from django.apps import apps
    from unfold.admin import ModelAdmin
    
    # Получаем все зарегистрированные модели
    for model, admin_class in admin.site._registry.items():
        # Пропускаем, если это не ModelAdmin или уже имеет миксин
        if not isinstance(admin_class, ModelAdmin):
            continue
        
        if isinstance(admin_class, AdminAccessMixin):
            continue
        
        # Создаем новый класс, который наследуется от AdminAccessMixin и текущего класса
        class_name = admin_class.__class__.__name__
        base_classes = (AdminAccessMixin, admin_class.__class__)
        
        # Создаем новый класс с миксином
        new_admin_class = type(
            class_name,
            base_classes,
            {}
        )
        
        # Копируем все атрибуты из старого класса
        for attr_name in dir(admin_class):
            if not attr_name.startswith('_') and attr_name not in ['has_module_permission', 
                                                                   'has_view_permission',
                                                                   'has_add_permission',
                                                                   'has_change_permission',
                                                                   'has_delete_permission']:
                try:
                    attr_value = getattr(admin_class, attr_name)
                    if not callable(attr_value) or isinstance(attr_value, type):
                        setattr(new_admin_class, attr_name, attr_value)
                except:
                    pass
        
        # Перерегистрируем модель с новым классом
        admin.site.unregister(model)
        admin.site.register(model, new_admin_class)


# Применяем автоматически при импорте (будет вызвано в apps.py)
# apply_permissions_to_admin_classes()

