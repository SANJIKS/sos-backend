from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)
from .models import DonationOption


@admin.register(DonationOption)
class DonationOptionAdmin(ModelAdmin):
    list_display = ['image_preview', 'title', 'option_type_display', 'status_display', 'is_active', 'is_featured', 'order', 'created_at']
    list_display_links = ['image_preview', 'title']
    list_filter = [
        ('option_type', ChoicesDropdownFilter),
        ('status', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('is_featured', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['title', 'description', 'detailed_description']
    ordering = ['order', 'title']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']
    list_editable = ['is_active', 'is_featured', 'order']
    actions = ['make_active', 'make_inactive', 'make_featured', 'remove_featured']
    
    def image_preview(self, obj):
        """Превью изображения"""
        if obj.image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 50px; max-width: 70px; border-radius: 4px;" /></a>',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Изображение"
    
    def option_type_display(self, obj):
        """Цветное отображение типа пожертвования"""
        colors = {
            'anniversary': '#e91e63',
            'payroll': '#9c27b0',
            'non_monetary': '#3f51b5',
            'one_time': '#2196f3',
            'monthly': '#00bcd4',
            'corporate': '#4caf50',
            'volunteer': '#8bc34a',
            'other': '#6c757d'
        }
        color = colors.get(obj.option_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_option_type_display()
        )
    option_type_display.short_description = "Тип"
    
    def status_display(self, obj):
        """Цветное отображение статуса"""
        colors = {
            'active': '#28a745',
            'coming_soon': '#ffc107',
            'inactive': '#6c757d',
            'maintenance': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_status_display()
        )
    status_display.short_description = "Статус"
    
    # Действия
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} опций пожертвований активированы.')
    make_active.short_description = 'Активировать выбранные опции'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} опций пожертвований деактивированы.')
    make_inactive.short_description = 'Деактивировать выбранные опции'
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} опций пожертвований помечены как рекомендуемые.')
    make_featured.short_description = 'Пометить как рекомендуемые'
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'У {updated} опций пожертвований убрана пометка рекомендуемых.')
    remove_featured.short_description = 'Убрать пометку рекомендуемых'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('title', 'description', 'option_type', 'status'),
            'description': 'Основные данные опции пожертвования'
        }),
        ('🖼️ Изображение', {
            'fields': ('image', 'image_preview'),
            'description': 'Изображение опции пожертвования'
        }),
        ('🔘 Кнопка', {
            'fields': ('button_text', 'button_url', 'is_button_enabled'),
            'description': 'Настройки кнопки действия'
        }),
        ('⚙️ Управление отображением', {
            'fields': ('is_active', 'is_featured', 'order'),
            'description': 'Настройки видимости и приоритета'
        }),
        ('📊 Дополнительная информация', {
            'fields': ('detailed_description', 'requirements', 'benefits', 'min_amount'),
            'classes': ('collapse',),
            'description': 'Подробная информация об опции'
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Служебная информация'
        }),
    )
