from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Пользователи'
    
    def ready(self):
        """Импорт сигналов и расширение admin.site при запуске приложения"""
        import apps.users.signals
        # Расширяем admin.site для поддержки прав доступа
        import apps.users.admin_site  # noqa: F401
        # Применяем патчи к ModelAdmin для автоматической проверки прав
        from apps.users.utils.patch_admin import patch_model_admin
        patch_model_admin()
