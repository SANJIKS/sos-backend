from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)
from .models import SocialNetwork


@admin.register(SocialNetwork)
class SocialNetworkAdmin(ModelAdmin):
    list_display = ['icon_display', 'name', 'network_type_display', 'url_link', 'is_active', 'is_featured', 'order', 'created_at']
    list_filter = [
        ('network_type', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('is_featured', ChoicesDropdownFilter),
        ('is_verified', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['name', 'description', 'url']
    ordering = ['order', 'name']
    readonly_fields = ['created_at', 'updated_at', 'custom_icon_preview', 'icon_display']
    list_editable = ['is_active', 'is_featured', 'order']
    actions = ['make_active', 'make_inactive', 'make_featured', 'remove_featured']
    
    def custom_icon_preview(self, obj):
        """Превью пользовательской иконки"""
        if obj.custom_icon:
            if obj.custom_icon.name.endswith('.svg'):
                return format_html(
                    '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                    obj.custom_icon.url
                )
            else:
                return format_html(
                    '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                    obj.custom_icon.url
                )
        return "Нет иконки"
    custom_icon_preview.short_description = "Превью иконки"
    
    def icon_display(self, obj):
        """Отображение иконки в списке"""
        if obj.custom_icon:
            return format_html(
                '<img src="{}" style="max-width: 30px; max-height: 30px;" />',
                obj.custom_icon.url
            )
        elif obj.icon:
            return format_html(
                '<span style="font-size: 20px;">{}</span>',
                obj.icon
            )
        return "—"
    icon_display.short_description = "Иконка"
    
    def network_type_display(self, obj):
        """Цветное отображение типа сети"""
        colors = {
            'facebook': '#1877f2',
            'instagram': '#e4405f',
            'twitter': '#1da1f2',
            'youtube': '#ff0000',
            'telegram': '#0088cc',
            'whatsapp': '#25d366',
            'linkedin': '#0077b5',
            'tiktok': '#000000',
            'other': '#6c757d'
        }
        color = colors.get(obj.network_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_network_type_display()
        )
    network_type_display.short_description = "Тип сети"
    
    def url_link(self, obj):
        """Ссылка на URL"""
        if obj.url:
            return format_html(
                '<a href="{}" target="_blank" style="color: #007bff; text-decoration: none;">🔗 Открыть</a>',
                obj.url
            )
        return "—"
    url_link.short_description = "Ссылка"
    
    # Действия
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} социальных сетей активированы.')
    make_active.short_description = 'Активировать выбранные сети'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} социальных сетей деактивированы.')
    make_inactive.short_description = 'Деактивировать выбранные сети'
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} социальных сетей помечены как рекомендуемые.')
    make_featured.short_description = 'Пометить как рекомендуемые'
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'У {updated} социальных сетей убрана пометка рекомендуемых.')
    remove_featured.short_description = 'Убрать пометку рекомендуемых'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('name', 'network_type', 'url'),
            'description': 'Основные данные социальной сети'
        }),
        ('🖼️ Иконка', {
            'fields': ('icon', 'custom_icon', 'custom_icon_preview'),
            'description': 'Иконка социальной сети'
        }),
        ('📊 Дополнительная информация', {
            'fields': ('description', 'followers_count', 'is_verified'),
            'classes': ('collapse',),
            'description': 'Подробная информация о социальной сети'
        }),
        ('⚙️ Управление отображением', {
            'fields': ('is_active', 'is_featured', 'order'),
            'description': 'Настройки видимости и приоритета'
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Служебная информация'
        }),
    )
