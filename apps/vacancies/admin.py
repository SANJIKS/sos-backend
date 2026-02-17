from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)
from apps.vacancies.models import Vacancy

@admin.register(Vacancy)
class VacancyAdmin(ModelAdmin):
    list_display = ['title', 'work_schedule_display', 'address', 'deadline_display', 'is_active', 'created_at']
    list_filter = [
        ('work_schedule', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('deadline', RangeDateFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['title', 'description', 'address']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['make_active', 'make_inactive', 'extend_deadline']
    
    def work_schedule_display(self, obj):
        """Цветное отображение графика работы"""
        colors = {
            'Full time': '#28a745',
            'Part time': '#ffc107',
            'Hybrid': '#007bff'
        }
        color = colors.get(obj.work_schedule, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.work_schedule
        )
    work_schedule_display.short_description = "График"
    
    def deadline_display(self, obj):
        """Цветное отображение дедлайна"""
        from django.utils import timezone
        now = timezone.now()
        if obj.deadline < now:
            color = '#dc3545'  # Красный - просрочено
        elif (obj.deadline - now).days <= 7:
            color = '#ffc107'  # Желтый - скоро
        else:
            color = '#28a745'  # Зеленый - есть время
            
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.deadline.strftime('%d.%m.%Y')
        )
    deadline_display.short_description = "Дедлайн"
    
    # Действия
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} вакансий активированы.')
    make_active.short_description = 'Активировать выбранные вакансии'
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} вакансий деактивированы.')
    make_inactive.short_description = 'Деактивировать выбранные вакансии'
    
    def extend_deadline(self, request, queryset):
        from datetime import timedelta
        for vacancy in queryset:
            vacancy.deadline += timedelta(days=30)
            vacancy.save()
        self.message_user(request, f'Дедлайн {queryset.count()} вакансий продлен на 30 дней.')
    extend_deadline.short_description = 'Продлить дедлайн на 30 дней'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('title', 'description', 'address', 'work_schedule'),
            'description': 'Основные данные вакансии'
        }),
        ('⏰ Временные рамки', {
            'fields': ('deadline', 'is_active'),
            'description': 'Сроки и статус вакансии'
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Служебная информация'
        }),
    )
