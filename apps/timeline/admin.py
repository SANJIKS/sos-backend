from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)
from .models import TimelineEvent


@admin.register(TimelineEvent)
class TimelineEventAdmin(ModelAdmin):
    list_display = ['image_preview', 'year', 'title', 'event_type_display', 'is_active', 'is_featured', 'order', 'created_at']
    list_filter = [
        ('event_type', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('is_featured', ChoicesDropdownFilter),
        ('year', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['title', 'description', 'year', 'location']
    ordering = ['order', 'year']
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
    
    def event_type_display(self, obj):
        """Цветное отображение типа события"""
        colors = {
            'foundation': '#dc3545',
            'opening': '#28a745',
            'launch': '#007bff',
            'anniversary': '#ffc107',
            'program': '#6f42c1',
            'expansion': '#20c997',
            'other': '#6c757d'
        }
        color = colors.get(obj.event_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_event_type_display()
        )
    event_type_display.short_description = "Тип события"
    
    # Действия
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} событий временной шкалы активированы.')
    make_active.short_description = 'Активировать выбранные события'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} событий временной шкалы деактивированы.')
    make_inactive.short_description = 'Деактивировать выбранные события'
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} событий временной шкалы помечены как рекомендуемые.')
    make_featured.short_description = 'Пометить как рекомендуемые'
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'У {updated} событий временной шкалы убрана пометка рекомендуемых.')
    remove_featured.short_description = 'Убрать пометку рекомендуемых'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('year', 'title', 'description', 'event_type'),
            'description': 'Основные данные события временной шкалы'
        }),
        ('🖼️ Изображения', {
            'fields': ('image', 'image_preview', 'icon'),
            'description': 'Визуальные материалы события'
        }),
        ('⚙️ Управление отображением', {
            'fields': ('is_active', 'is_featured', 'order'),
            'description': 'Настройки видимости и приоритета'
        }),
        ('📊 Дополнительная информация', {
            'fields': ('location', 'participants', 'impact'),
            'classes': ('collapse',),
            'description': 'Подробная информация о событии'
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Служебная информация'
        }),
    )
