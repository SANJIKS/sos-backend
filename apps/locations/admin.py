from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)
from .models import MapPoint


@admin.register(MapPoint)
class MapPointAdmin(ModelAdmin):
    list_display = ('image_preview', 'point_id_link', 'name_link', 'coordinates_display', 'is_active', 'order', 'created_at')
    list_filter = [
        ('is_active', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ('point_id', 'name', 'name_kg', 'name_en', 'description')
    ordering = ('order', 'name')
    readonly_fields = ['created_at', 'updated_at', 'image_preview', 'coordinates_display']
    actions = ['make_active', 'make_inactive', 'reorder_points']
    
    def image_preview(self, obj):
        """Превью изображения"""
        if obj.image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 40px; max-width: 60px; border-radius: 4px;" /></a>',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Изображение"
    
    def name_link(self, obj):
        """Название с ссылкой на редактирование"""
        url = reverse('admin:locations_mappoint_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="color: #007cba; text-decoration: none;">{}</a>',
            url, obj.name
        )
    name_link.short_description = "Название"
    name_link.admin_order_field = 'name'
    
    def point_id_link(self, obj):
        """ID точки с ссылкой на редактирование"""
        url = reverse('admin:locations_mappoint_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="color: #007cba; text-decoration: none; font-family: monospace;">{}</a>',
            url, obj.point_id
        )
    point_id_link.short_description = "ID точки"
    point_id_link.admin_order_field = 'point_id'
    
    def coordinates_display(self, obj):
        """Отображение координат"""
        return format_html(
            '<span style="font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 3px;">X: {}%, Y: {}%</span>',
            obj.x_percent, obj.y_percent
        )
    coordinates_display.short_description = "Координаты"
    
    # Действия
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} точек карты активированы.')
    make_active.short_description = 'Активировать выбранные точки'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} точек карты деактивированы.')
    make_inactive.short_description = 'Деактивировать выбранные точки'
    
    def reorder_points(self, request, queryset):
        """Переупорядочить точки"""
        for i, point in enumerate(queryset.order_by('order'), 1):
            point.order = i
            point.save()
        self.message_user(request, f'{queryset.count()} точек переупорядочены.')
    reorder_points.short_description = 'Переупорядочить точки'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('point_id', 'name', 'name_kg', 'name_en'),
            'description': 'Основные данные точки карты'
        }),
        ('📄 Описание', {
            'fields': ('description', 'description_kg', 'description_en'),
            'description': 'Описания на разных языках'
        }),
        ('🖼️ Изображение', {
            'fields': ('image', 'image_preview'),
            'description': 'Изображение для всплывающего окна'
        }),
        ('📍 Координаты', {
            'fields': ('x_percent', 'y_percent', 'coordinates_display'),
            'description': 'Координаты в процентах от размера карты (0-100)'
        }),
        ('⚙️ Настройки', {
            'fields': ('is_active', 'order'),
            'description': 'Настройки видимости и порядка'
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Служебная информация'
        }),
    )
