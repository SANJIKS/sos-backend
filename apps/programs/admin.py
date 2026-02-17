from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    MultipleRelatedDropdownFilter,
    ChoicesDropdownFilter
)
from apps.common.admin import BaseContentWithChoicesAdmin
from .models import Program, ProgramStep


class ProgramStepInline(TabularInline):
    """
    Инлайн для этапов программы
    """
    model = ProgramStep
    extra = 0
    fields = ['id', 'title', 'description', 'order', 'icon', 'icon_preview']
    readonly_fields = ['icon_preview']
    
    def icon_preview(self, obj):
        """Превью иконки"""
        if obj.icon:
            if obj.icon.name.endswith('.svg'):
                return format_html(
                    '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                    obj.icon.url
                )
            else:
                return format_html(
                    '<img src="{}" style="max-width: 50px; max-height: 50px;" />',
                    obj.icon.url
                )
        return "Нет иконки"
    icon_preview.short_description = "Превью иконки"


@admin.register(Program)
class ProgramAdmin(ModelAdmin):
    """
    Админка для программ
    """
    inlines = [ProgramStepInline]
    
    # Отображение в списке
    list_display = ['id', 'main_image_preview', 'title', 'program_type_display', 'is_active', 'is_featured', 'is_main_program', 'order', 'created_at']
    list_filter = [
        ('program_type', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('is_featured', ChoicesDropdownFilter),
        ('is_main_program', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['title', 'description', 'short_description', 'author_name']
    list_editable = ['is_active', 'is_featured', 'is_main_program', 'order']
    ordering = ['order', 'title']
    readonly_fields = ['icon_preview', 'main_image_preview', 'created_at', 'updated_at']
    filter_horizontal = []
    date_hierarchy = 'created_at'
    actions = ['make_active', 'make_inactive', 'make_featured', 'remove_featured']
    
    def icon_preview(self, obj):
        """Превью иконки"""
        if obj.icon:
            if obj.icon.name.endswith('.svg'):
                return format_html(
                    '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                    obj.icon.url
                )
            else:
                return format_html(
                    '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                    obj.icon.url
                )
        return "Нет иконки"
    icon_preview.short_description = "Превью иконки"
    
    def main_image_preview(self, obj):
        """Превью главного изображения"""
        if obj.main_image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 50px; max-width: 70px; border-radius: 4px;" /></a>',
                obj.main_image.url
            )
        return "—"
    main_image_preview.short_description = "Обложка"
    
    def program_type_display(self, obj):
        """Цветное отображение типа программы"""
        colors = {
            'children_villages': '#007bff',
            'alternative_care': '#28a745',
            'family_strengthening': '#fd7e14',
            'graduate_support_direction': '#6f42c1',
            'sos_parents_training': '#20c997',
            'psychological_support': '#dc3545',
            'other': '#6c757d'
        }
        color = colors.get(obj.program_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_program_type_display()
        )
    program_type_display.short_description = "Тип программы"
    
    # Действия
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} программ(ы) активированы.')
    make_active.short_description = 'Активировать выбранные программы'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} программ(ы) деактивированы.')
    make_inactive.short_description = 'Деактивировать выбранные программы'
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} программ(ы) помечены как рекомендуемые.')
    make_featured.short_description = 'Пометить как рекомендуемые'
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'У {updated} программ(ы) убрана пометка рекомендуемых.')
    remove_featured.short_description = 'Убрать пометку рекомендуемых'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('title', 'slug', 'description', 'short_description', 'program_type'),
            'description': 'Основные данные о программе'
        }),
        ('🖼️ Изображения и медиа', {
            'fields': ('image', 'icon', 'icon_preview', 'main_image', 'video_url', 'video_thumbnail'),
            'description': 'Визуальные материалы и медиафайлы'
        }),
        ('👤 Автор и цитата', {
            'fields': ('author_name', 'author_title', 'quote'),
            'classes': ('collapse',),
            'description': 'Информация об авторе и цитата'
        }),
        ('📊 Дополнительная информация', {
            'fields': ('content', 'target_audience', 'duration'),
            'classes': ('collapse',),
            'description': 'Подробное описание программы'
        }),
        ('⚙️ Управление отображением', {
            'fields': ('is_active', 'is_featured', 'is_main_program', 'order'),
            'description': 'Настройки видимости и приоритета'
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Служебная информация'
        }),
    )


@admin.register(ProgramStep)
class ProgramStepAdmin(ModelAdmin):
    """
    Админка для этапов программ
    """
    list_display = ['program', 'title', 'order', 'icon_preview']
    list_filter = [
        ('program', MultipleRelatedDropdownFilter),
    ]
    search_fields = ['title', 'description', 'program__title']
    list_editable = ['order']
    ordering = ['program', 'order']
    readonly_fields = ['icon_preview']
    actions = ['reorder_steps']
    
    def icon_preview(self, obj):
        """Превью иконки"""
        if obj.icon:
            if obj.icon.name.endswith('.svg'):
                return format_html(
                    '<img src="{}" style="max-width: 30px; max-height: 30px;" />',
                    obj.icon.url
                )
            else:
                return format_html(
                    '<img src="{}" style="max-width: 30px; max-height: 30px;" />',
                    obj.icon.url
                )
        return "—"
    icon_preview.short_description = "Иконка"
    
    def reorder_steps(self, request, queryset):
        """Переупорядочить этапы"""
        for i, step in enumerate(queryset.order_by('program', 'order')):
            step.order = i + 1
            step.save()
        self.message_user(request, f'{queryset.count()} этапов переупорядочены.')
    reorder_steps.short_description = 'Переупорядочить этапы'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('program', 'title', 'description', 'order'),
            'description': 'Основные данные этапа программы'
        }),
        ('🖼️ Иконка', {
            'fields': ('icon', 'icon_preview'),
            'description': 'Иконка этапа программы'
        }),
    )
