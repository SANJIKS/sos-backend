from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    RangeDateTimeFilter,
    MultipleRelatedDropdownFilter,
    SingleNumericFilter,
)
from .models import DigitalCampaign, CampaignMetric


@admin.register(CampaignMetric)
class CampaignMetricAdmin(ModelAdmin):
    list_display = ['campaign', 'metric_type', 'name', 'value', 'unit', 'date_recorded']
    list_filter = [
        'metric_type',
        ('date_recorded', RangeDateFilter),
        ('created_at', RangeDateTimeFilter),
    ]
    search_fields = ['campaign__title', 'name', 'notes']
    ordering = ['-date_recorded']
    date_hierarchy = 'date_recorded'
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('campaign', 'metric_type', 'name', 'value', 'unit')
        }),
        (_('Дополнительно'), {
            'fields': ('date_recorded', 'notes'),
            'classes': ('collapse',)
        })
    )


class CampaignMetricInline(TabularInline):
    model = CampaignMetric
    extra = 0
    fields = ['metric_type', 'name', 'value', 'unit', 'date_recorded', 'notes']


@admin.register(DigitalCampaign)
class DigitalCampaignAdmin(ModelAdmin):
    list_display = [
        'title', 'campaign_type', 'status', 'impact_level',
        'start_date', 'end_date', 'progress_display',
        'budget_utilization_display', 'is_featured', 'is_public'
    ]
    list_filter = [
        'campaign_type', 'status', 'impact_level',
        'is_featured', 'is_public',
        ('created_at', RangeDateTimeFilter),
        ('start_date', RangeDateFilter),
        ('end_date', RangeDateFilter),
        ('budget_planned', SingleNumericFilter),
        ('budget_spent', SingleNumericFilter),
    ]
    search_fields = ['title', 'description', 'target_audience', 'short_description']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': (
                'title', 'slug', 'description', 'short_description',
                'campaign_type', 'status', 'impact_level'
            )
        }),
        (_('Временные рамки'), {
            'fields': ('start_date', 'end_date', 'planned_duration_days')
        }),
        (_('Цели и аудитория'), {
            'fields': ('goal_description', 'target_audience', 'expected_impact')
        }),
        (_('Бюджет'), {
            'fields': ('budget_planned', 'budget_spent')
        }),
        (_('Медиа'), {
            'fields': ('main_image', 'banner_image', 'video_url'),
            'classes': ('collapse',)
        }),
        (_('Цифровые метрики'), {
            'fields': (
                'website_visits', 'social_media_reach',
                'engagement_rate', 'conversion_rate'
            ),
            'classes': ('collapse',)
        }),
        (_('Результаты'), {
            'fields': (
                'actual_impact', 'lessons_learned',
                'success_factors', 'challenges_faced'
            ),
            'classes': ('collapse',)
        }),
        (_('Связи'), {
            'fields': ('related_donation_campaigns', 'related_programs'),
            'classes': ('collapse',)
        }),
        (_('Управление'), {
            'fields': ('is_featured', 'is_public', 'order', 'created_by')
        })
    )
    
    filter_horizontal = ['related_donation_campaigns', 'related_programs']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CampaignMetricInline]
    
    def progress_display(self, obj):
        """Отображение прогресса кампании"""
        progress = obj.progress_percentage
        color = 'green' if progress >= 100 else 'orange' if progress >= 50 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, progress
        )
    progress_display.short_description = _('Прогресс')
    progress_display.admin_order_field = 'start_date'
    
    def budget_utilization_display(self, obj):
        """Отображение использования бюджета"""
        utilization = obj.budget_utilization
        color = 'green' if utilization <= 100 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, utilization
        )
    budget_utilization_display.short_description = _('Использование бюджета')
    budget_utilization_display.admin_order_field = 'budget_spent'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('created_by')
    
    def save_model(self, request, obj, form, change):
        """Автоматическое назначение создателя"""
        if not change:  # Если это создание нового объекта
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_list_display(self, request):
        """Динамическое отображение полей в зависимости от прав"""
        list_display = list(super().get_list_display(request))
        if not request.user.is_superuser:
            # Убираем чувствительные поля для обычных пользователей
            if 'budget_utilization_display' in list_display:
                list_display.remove('budget_utilization_display')
        return list_display
