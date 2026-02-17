from django.db import models
from django.utils.translation import gettext_lazy as _


class UserAdminAccess(models.Model):
    """
    Модель для управления правами доступа пользователя к разделам админки.
    
    Структура admin_permissions (JSONField):
    {
        "apps": {
            "news": {
                "models": {
                    "News": ["view", "add", "change", "delete"],
                    "NewsCategory": ["view", "change"],
                    "NewsTag": ["view", "add", "change", "delete"]
                }
            },
            "faq": {
                "models": {
                    "FAQ": ["view", "add", "change", "delete"]
                }
            },
            "contacts": {
                "models": {
                    "Contact": ["view", "change"],
                    "ContactCategory": ["view"],
                    "Office": ["view", "add", "change", "delete"]
                }
            }
        }
    }
    """
    
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='admin_access',
        verbose_name=_('Пользователь')
    )
    
    admin_permissions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Права доступа к админке'),
        help_text=_('JSON структура прав доступа. Формат: {"apps": {"app_label": {"models": {"ModelName": ["view", "add", "change", "delete"]}}}}')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активен'),
        help_text=_('Если отключено, пользователь не имеет доступа к админке')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Создано')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Обновлено')
    )
    
    class Meta:
        verbose_name = _('Доступ к админке')
        verbose_name_plural = _('Доступы к админке')
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"Доступ к админке: {self.user.email}"
    
    def get_allowed_apps(self):
        """
        Получить список разрешенных приложений
        """
        if not self.admin_permissions or not self.is_active:
            return []
        
        apps = self.admin_permissions.get('apps', {})
        return list(apps.keys())
    
    def get_allowed_models(self, app_label=None):
        """
        Получить список разрешенных моделей
        
        Args:
            app_label: Если указано, вернет только модели для этого приложения
                      В формате "app.Model"
        
        Returns:
            list: Список моделей в формате ["news.News", "faq.FAQ"]
        """
        if not self.admin_permissions or not self.is_active:
            return []
        
        apps = self.admin_permissions.get('apps', {})
        allowed_models = []
        
        for app, app_data in apps.items():
            if app_label and app != app_label:
                continue
            
            models_dict = app_data.get('models', {})
            for model_name in models_dict.keys():
                allowed_models.append(f"{app}.{model_name}")
        
        return allowed_models
    
    def can_access_app(self, app_label):
        """
        Проверить доступ к приложению
        
        Args:
            app_label: Метка приложения (например, "news")
        
        Returns:
            bool: True если есть доступ
        """
        if not self.is_active:
            return False
        
        allowed_apps = self.get_allowed_apps()
        return app_label in allowed_apps
    
    def can_access_model(self, app_label, model_name):
        """
        Проверить доступ к модели
        
        Args:
            app_label: Метка приложения (например, "news")
            model_name: Название модели (например, "News")
        
        Returns:
            bool: True если есть доступ
        """
        if not self.is_active:
            return False
        
        apps = self.admin_permissions.get('apps', {})
        app_data = apps.get(app_label, {})
        models_dict = app_data.get('models', {})
        
        return model_name in models_dict
    
    def can_perform_action(self, app_label, model_name, action):
        """
        Проверить право на выполнение действия
        
        Args:
            app_label: Метка приложения (например, "news")
            model_name: Название модели (например, "News")
            action: Действие ('view', 'add', 'change', 'delete')
        
        Returns:
            bool: True если действие разрешено
        """
        if not self.is_active:
            return False
        
        apps = self.admin_permissions.get('apps', {})
        app_data = apps.get(app_label, {})
        models_dict = app_data.get('models', {})
        
        allowed_actions = models_dict.get(model_name, [])
        return action in allowed_actions
    
    def get_model_permissions(self, app_label, model_name):
        """
        Получить список разрешенных действий для модели
        
        Args:
            app_label: Метка приложения
            model_name: Название модели
        
        Returns:
            list: Список разрешенных действий ['view', 'add', 'change', 'delete']
        """
        if not self.is_active:
            return []
        
        apps = self.admin_permissions.get('apps', {})
        app_data = apps.get(app_label, {})
        models_dict = app_data.get('models', {})
        
        return models_dict.get(model_name, [])

