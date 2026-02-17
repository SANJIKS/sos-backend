from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)

from apps.partners.models import Partner



@admin.register(Partner)
class PartnerAdmin(ModelAdmin):
    list_display = ('logo_preview', 'name', 'category_display', 'created_at')
    list_filter = [
        ('category', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ('name', 'name_kg', 'name_en')
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at', 'logo_preview']
    actions = ['duplicate_partner']
    
    def logo_preview(self, obj):
        """Превью логотипа"""
        if obj.logo:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 40px; max-width: 60px; border-radius: 4px;" /></a>',
                obj.logo.url
            )
        return "—"
    logo_preview.short_description = "Логотип"
    
    def category_display(self, obj):
        """Цветное отображение категории"""
        colors = {
            'civil_organizations': '#007bff',
            'government_agencies': '#28a745',
            'international_organizations': '#6f42c1',
            'foreign_governments': '#fd7e14',
            'corporate_donors': '#20c997',
            'other_organizations': '#6c757d'
        }
        color = colors.get(obj.category, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_category_display()
        )
    category_display.short_description = "Категория"
    
    # Действия
    def duplicate_partner(self, request, queryset):
        """Дублировать партнера"""
        for partner in queryset:
            partner.pk = None
            partner.name = f"{partner.name} (копия)"
            partner.save()
        self.message_user(request, f'{queryset.count()} партнеров дублированы.')
    duplicate_partner.short_description = 'Дублировать выбранных партнеров'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('name', 'name_kg', 'name_en', 'category'),
            'description': 'Основные данные партнера'
        }),
        ('🖼️ Логотип', {
            'fields': ('logo', 'logo_preview'),
            'description': 'Логотип партнера'
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Служебная информация'
        }),
    )