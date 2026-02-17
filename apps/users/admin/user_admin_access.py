"""
Админка для управления правами доступа UserAdminAccess
"""
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from apps.users.models import UserAdminAccess
from apps.users.forms.admin_access import UserAdminAccessForm


class AdminPermissionsDisplay:
    """
    Класс для отображения прав доступа в режиме только чтения
    """
    @staticmethod
    def render_readonly(admin_access):
        """Отображение прав в режиме только чтения"""
        if not admin_access or not admin_access.is_active:
            return format_html('<span style="color: #dc3545;">Нет доступа</span>')
        
        apps = admin_access.admin_permissions.get('apps', {})
        if not apps:
            return format_html('<span style="color: #6c757d;">Нет разрешенных разделов</span>')
        
        html_parts = ['<div style="margin-top: 10px;">']
        for app_label, app_data in apps.items():
            models_count = len(app_data.get('models', {}))
            html_parts.append(
                f'<div style="margin-bottom: 5px;">'
                f'<strong>{app_label}</strong>: {models_count} моделей'
                f'</div>'
            )
        html_parts.append('</div>')
        
        return format_html(''.join(html_parts))


@admin.register(UserAdminAccess)
class UserAdminAccessAdmin(ModelAdmin):
    """Админка для управления правами доступа"""
    
    form = UserAdminAccessForm
    
    list_display = ('user', 'is_active', 'permissions_summary', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'permissions_display')
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user', 'is_active')
        }),
        ('Права доступа', {
            'fields': ('admin_permissions',),
            'description': 'Права доступа задаются в формате JSON. Структура: {"apps": {"app_label": {"models": {"ModelName": ["view", "add", "change", "delete"]}}}}'
        }),
        ('Текущие права', {
            'fields': ('permissions_display',),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def permissions_summary(self, obj):
        """Краткая сводка прав"""
        if not obj or not obj.is_active:
            return format_html('<span style="color: #dc3545;">Неактивен</span>')
        
        apps = obj.admin_permissions.get('apps', {})
        apps_count = len(apps)
        models_count = sum(len(app_data.get('models', {})) for app_data in apps.values())
        
        return format_html(
            '<span style="color: #28a745;">{} приложений, {} моделей</span>',
            apps_count,
            models_count
        )
    permissions_summary.short_description = 'Права доступа'
    
    def permissions_display(self, obj):
        """Отображение прав в читаемом формате"""
        if not obj:
            return format_html('<p>Создайте запись для настройки прав</p>')
        
        return AdminPermissionsDisplay.render_readonly(obj)
    permissions_display.short_description = 'Текущие права'


class UserAdminAccessInline(TabularInline):
    """Inline для управления правами доступа в форме User"""
    model = UserAdminAccess
    extra = 0
    max_num = 1
    can_delete = False
    fields = ('is_active', 'admin_permissions')
    readonly_fields = ()
    verbose_name = 'Доступ к админке'
    verbose_name_plural = 'Доступ к админке'
    
    def has_add_permission(self, request, obj=None):
        """Разрешить добавление только superuser"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Разрешить изменение только superuser"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Запретить удаление"""
        return False




