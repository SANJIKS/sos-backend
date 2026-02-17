"""
Формы для управления правами доступа к админке
"""
import json
from django import forms
from apps.users.models import UserAdminAccess


class UserAdminAccessForm(forms.ModelForm):
    """Форма для управления правами доступа"""
    
    class Meta:
        model = UserAdminAccess
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'admin_permissions' in self.fields:
            self.fields['admin_permissions'].required = False
    
    def clean_admin_permissions(self):
        """Очистка и валидация поля admin_permissions"""
        if 'admin_permissions' not in self.cleaned_data:
            return {}
        
        permissions = self.cleaned_data['admin_permissions']
        
        # Валидация структуры
        if not isinstance(permissions, dict):
            return {}
        
        # Убеждаемся, что структура правильная
        if 'apps' not in permissions:
            permissions = {'apps': {}}
        
        # Валидируем структуру apps
        if not isinstance(permissions.get('apps'), dict):
            permissions['apps'] = {}
        
        # Валидируем каждое приложение
        for app_label, app_data in list(permissions['apps'].items()):
            if not isinstance(app_data, dict):
                permissions['apps'][app_label] = {'models': {}}
            elif 'models' not in app_data:
                app_data['models'] = {}
            elif not isinstance(app_data['models'], dict):
                app_data['models'] = {}
            
            # Валидируем каждую модель
            for model_name, actions in list(app_data.get('models', {}).items()):
                if not isinstance(actions, list):
                    app_data['models'][model_name] = []
                else:
                    # Фильтруем только валидные действия
                    valid_actions = ['view', 'add', 'change', 'delete']
                    app_data['models'][model_name] = [a for a in actions if a in valid_actions]
        
        return permissions

