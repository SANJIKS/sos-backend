from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)
from apps.common.admin import BaseContentAdmin
from .models import Principle


@admin.register(Principle)
class PrincipleAdmin(ModelAdmin):
    """
    Админка для принципов SOS
    """
    list_display = ['icon_display', 'title', 'principle_type_display', 'is_active', 'is_featured', 'order', 'created_at']
    list_filter = [
        ('principle_type', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('is_featured', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['title', 'subtitle', 'description', 'key_points']
    ordering = ['order', 'title']
    list_editable = ['is_active', 'is_featured', 'order']
    readonly_fields = ['created_at', 'updated_at', 'icon_display']
    actions = ['make_active', 'make_inactive', 'make_featured', 'remove_featured']
    
    def icon_display(self, obj):
        """Отображение иконки"""
        if obj.icon:
            return format_html(
                '<span style="font-size: 20px;">{}</span>',
                obj.icon
            )
        return "—"
    icon_display.short_description = "Иконка"
    
    def principle_type_display(self, obj):
        """Цветное отображение типа принципа"""
        colors = {
            'mother': '#e91e63',
            'siblings': '#9c27b0',
            'home': '#3f51b5',
            'village': '#2196f3',
            'other': '#6c757d'
        }
        color = colors.get(obj.principle_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_principle_type_display()
        )
    principle_type_display.short_description = "Тип принципа"
    
    # Действия
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} принципов активированы.')
    make_active.short_description = 'Активировать выбранные принципы'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} принципов деактивированы.')
    make_inactive.short_description = 'Деактивировать выбранные принципы'
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} принципов помечены как рекомендуемые.')
    make_featured.short_description = 'Пометить как рекомендуемые'
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'У {updated} принципов убрана пометка рекомендуемых.')
    remove_featured.short_description = 'Убрать пометку рекомендуемых'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('title', 'subtitle', 'description', 'principle_type'),
            'description': 'Основные данные принципа SOS'
        }),
        ('🖼️ Изображения', {
            'fields': ('icon', 'image'),
            'description': 'Визуальные материалы принципа'
        }),
        ('📊 Дополнительная информация', {
            'fields': ('key_points', 'impact'),
            'classes': ('collapse',),
            'description': 'Ключевые моменты и влияние принципа'
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
