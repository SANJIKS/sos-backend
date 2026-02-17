from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)

from apps.contacts.models.contact import Contact, ContactCategory
from apps.contacts.models.office import Office


@admin.register(ContactCategory)
class ContactCategoryAdmin(ModelAdmin):
    list_display = ['name', 'is_active', 'sort_order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'name_kg', 'name_en', 'description', 'is_active', 'sort_order')
        }),
        ('Уведомления', {
            'fields': ('email_recipients',)
        }),
        ('Системная информация', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(ModelAdmin):
    list_display = [
        'full_name', 'email', 'subject', 'contact_type', 'status_display', 
        'priority_display', 'created_at', 'needs_response'
    ]
    list_filter = [
        ('status', ChoicesDropdownFilter),
        ('priority', ChoicesDropdownFilter),
        ('contact_type', ChoicesDropdownFilter),
        ('category', admin.RelatedFieldListFilter),
        ('created_at', RangeDateFilter),
        'is_bot',
    ]
    search_fields = ['full_name', 'email', 'subject', 'message']
    ordering = ['-created_at']
    readonly_fields = [
        'uuid', 'created_at', 'updated_at', 'ip_address', 'user_agent', 
        'referrer', 'response_time'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('category', 'contact_type', 'full_name', 'email', 'phone')
        }),
        ('Содержание', {
            'fields': ('subject', 'message')
        }),
        ('Дополнительная информация', {
            'fields': ('company', 'position', 'city', 'preferred_contact_method')
        }),
        ('Согласия', {
            'fields': ('consent_data_processing', 'consent_marketing')
        }),
        ('Статус и приоритет', {
            'fields': ('status', 'priority', 'assigned_to', 'internal_notes')
        }),
        ('Ответ', {
            'fields': ('response_message', 'responded_by', 'responded_at')
        }),
        ('Техническая информация', {
            'fields': ('ip_address', 'user_agent', 'referrer', 'captcha_token', 'is_bot'),
            'classes': ('collapse',)
        }),
        ('Уведомления', {
            'fields': ('email_sent', 'email_sent_at'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_responded', 'mark_as_spam', 'assign_to_user']
    
    def status_display(self, obj):
        """Отображение статуса с цветом"""
        color = obj.get_status_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    def priority_display(self, obj):
        """Отображение приоритета с цветом"""
        color = obj.get_priority_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_display.short_description = 'Приоритет'
    
    def needs_response(self, obj):
        """Требует ли обращение ответа"""
        if obj.needs_response:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠ Требует ответа</span>'
            )
        return format_html(
            '<span style="color: #28a745;">✓ Обработано</span>'
        )
    needs_response.short_description = 'Статус обработки'
    
    def mark_as_responded(self, request, queryset):
        """Пометить как отвеченное"""
        updated = queryset.update(status=Contact.Status.RESPONDED)
        self.message_user(request, f'{updated} обращений помечено как отвеченные.')
    mark_as_responded.short_description = 'Пометить как отвеченные'
    
    def mark_as_spam(self, request, queryset):
        """Пометить как спам"""
        updated = queryset.update(status=Contact.Status.SPAM, is_bot=True)
        self.message_user(request, f'{updated} обращений помечено как спам.')
    mark_as_spam.short_description = 'Пометить как спам'
    
    def assign_to_user(self, request, queryset):
        """Назначить пользователю"""
        # TODO: Добавить форму для выбора пользователя
        self.message_user(request, 'Функция назначения в разработке.')
    assign_to_user.short_description = 'Назначить пользователю'


@admin.register(Office)
class OfficeAdmin(ModelAdmin):
    list_display = ['name', 'office_type', 'is_main_office', 'is_active', 'order', 'created_at']
    list_filter = ['office_type', 'is_main_office', 'is_active']
    search_fields = ['name', 'address', 'phone', 'email']
    ordering = ['order', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'office_type', 'address', 'phone', 'email', 'working_hours')
        }),
        ('Дополнительная информация', {
            'fields': ('description', 'is_main_office', 'is_active', 'order')
        }),
        ('Координаты', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )