from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)
from .models import ImpactResult


@admin.register(ImpactResult)
class ImpactResultAdmin(ModelAdmin):
    list_display = ['image_preview', 'title', 'percentage_display', 'result_type_display', 'is_active', 'is_featured', 'order', 'created_at']
    list_filter = [
        ('result_type', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('is_featured', ChoicesDropdownFilter),
        ('year', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['title', 'description', 'detailed_description', 'source']
    ordering = ['order', 'percentage_value']
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
    
    def percentage_display(self, obj):
        """Цветное отображение процента"""
        if obj.percentage_value >= 80:
            color = '#28a745'  # Зеленый
        elif obj.percentage_value >= 60:
            color = '#ffc107'  # Желтый
        elif obj.percentage_value >= 40:
            color = '#fd7e14'  # Оранжевый
        else:
            color = '#dc3545'  # Красный
            
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 16px; padding: 4px 8px; background: {}20; border-radius: 4px;">{}%</span>',
            color, color, obj.percentage_value
        )
    percentage_display.short_description = "Процент"
    
    def result_type_display(self, obj):
        """Цветное отображение типа результата"""
        colors = {
            'integration': '#007bff',
            'violence_prevention': '#dc3545',
            'education': '#28a745',
            'health': '#20c997',
            'employment': '#fd7e14',
            'family_reunification': '#6f42c1',
            'other': '#6c757d'
        }
        color = colors.get(obj.result_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_result_type_display()
        )
    result_type_display.short_description = "Тип"
    
    # Действия
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} результатов воздействия активированы.')
    make_active.short_description = 'Активировать выбранные результаты'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} результатов воздействия деактивированы.')
    make_inactive.short_description = 'Деактивировать выбранные результаты'
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} результатов воздействия помечены как рекомендуемые.')
    make_featured.short_description = 'Пометить как рекомендуемые'
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'У {updated} результатов воздействия убрана пометка рекомендуемых.')
    remove_featured.short_description = 'Убрать пометку рекомендуемых'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('title', 'percentage_value', 'description', 'result_type'),
            'description': 'Основные данные результата воздействия'
        }),
        ('🖼️ Изображение', {
            'fields': ('image', 'image_preview'),
            'description': 'Изображение результата воздействия'
        }),
        ('⚙️ Управление отображением', {
            'fields': ('is_active', 'is_featured', 'order'),
            'description': 'Настройки видимости и приоритета'
        }),
        ('📊 Дополнительная информация', {
            'fields': ('detailed_description', 'source', 'year'),
            'classes': ('collapse',),
            'description': 'Подробная информация о результате'
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Служебная информация'
        }),
    )
