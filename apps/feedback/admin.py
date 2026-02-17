from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin
from .models import Feedback, FeedbackQuestion, FeedbackSpamProtection


@admin.register(FeedbackQuestion)
class FeedbackQuestionAdmin(ModelAdmin):
    list_display = ['text', 'is_active', 'order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'order']
    search_fields = ['text']
    ordering = ['order', 'id']
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('order', 'id')
    
    def is_active(self, obj):
        if obj.is_active:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">'
                'Активен</span>'
            )
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">'
            'Неактивен</span>'
        )
    is_active.short_description = 'Статус'


@admin.register(Feedback)
class FeedbackAdmin(ModelAdmin):
    list_display = [
        'name', 'email', 'feedback_type', 'question_text', 
        'is_approved', 'created_at', 'ip_address', 'message_preview'
    ]
    list_filter = [
        'feedback_type', 'is_approved', 'is_anonymous', 
        'created_at', 'question'
    ]
    search_fields = ['name', 'email', 'message']
    list_editable = ['is_approved']
    readonly_fields = ['ip_address', 'anonymous_id', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('feedback_type', 'name', 'last_name', 'email', 'message')
        }),
        ('Дополнительные данные', {
            'fields': ('question', 'photo', 'is_anonymous'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('ip_address', 'anonymous_id', 'created_at'),
            'classes': ('collapse',)
        }),
        ('Модерация', {
            'fields': ('is_approved',)
        }),
    )
    
    def question_text(self, obj):
        """Отображает текст вопроса"""
        if obj.question:
            return format_html(
                '<span class="text-sm text-gray-600">{}</span>',
                obj.question.text
            )
        return format_html('<span class="text-gray-400">-</span>')
    question_text.short_description = 'Вопрос'
    
    def message_preview(self, obj):
        """Показывает превью сообщения"""
        if len(obj.message) > 50:
            return format_html(
                '<span class="text-sm" title="{}">{}...</span>',
                obj.message, obj.message[:50]
            )
        return format_html('<span class="text-sm">{}</span>', obj.message)
    message_preview.short_description = 'Превью сообщения'
    
    def is_approved(self, obj):
        """Отображает статус одобрения с цветовой индикацией"""
        if obj.is_approved:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">'
                '✓ Одобрен</span>'
            )
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">'
            '⏳ На модерации</span>'
        )
    is_approved.short_description = 'Статус'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('question')
    
    actions = ['approve_feedback', 'disapprove_feedback']
    
    def approve_feedback(self, request, queryset):
        """Одобрить выбранные отзывы"""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'Одобрено {updated} отзывов.')
    approve_feedback.short_description = 'Одобрить выбранные отзывы'
    
    def disapprove_feedback(self, request, queryset):
        """Отклонить выбранные отзывы"""
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'Отклонено {updated} отзывов.')
    disapprove_feedback.short_description = 'Отклонить выбранные отзывы'


@admin.register(FeedbackSpamProtection)
class FeedbackSpamProtectionAdmin(ModelAdmin):
    list_display = [
        'ip_address', 'attempts_count', 'last_attempt', 
        'is_blocked', 'blocked_until', 'status'
    ]
    list_filter = ['is_blocked', 'last_attempt']
    search_fields = ['ip_address']
    readonly_fields = ['ip_address', 'attempts_count', 'last_attempt']
    ordering = ['-last_attempt']
    
    fieldsets = (
        ('Информация о IP', {
            'fields': ('ip_address', 'attempts_count', 'last_attempt')
        }),
        ('Блокировка', {
            'fields': ('is_blocked', 'blocked_until')
        }),
    )
    
    def status(self, obj):
        """Показывает текущий статус IP"""
        if obj.is_currently_blocked():
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">'
                '🚫 ЗАБЛОКИРОВАН</span>'
            )
        elif obj.attempts_count > 3:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">'
                '⚠️ ПОДОЗРИТЕЛЬНЫЙ</span>'
            )
        else:
            return format_html(
                '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">'
                '✅ НОРМАЛЬНЫЙ</span>'
            )
    status.short_description = 'Статус'
    
    actions = ['unblock_ip', 'reset_attempts']
    
    def unblock_ip(self, request, queryset):
        """Разблокировать выбранные IP"""
        updated = queryset.update(
            is_blocked=False, 
            blocked_until=None,
            attempts_count=0
        )
        self.message_user(request, f'Разблокировано {updated} IP адресов.')
    unblock_ip.short_description = 'Разблокировать выбранные IP'
    
    def reset_attempts(self, request, queryset):
        """Сбросить счетчики попыток"""
        updated = queryset.update(attempts_count=0)
        self.message_user(request, f'Сброшены счетчики для {updated} IP адресов.')
    reset_attempts.short_description = 'Сбросить счетчики попыток'


# Настройка админки
admin.site.site_header = "Администрирование отзывов"
admin.site.site_title = "Отзывы"
admin.site.index_title = "Управление отзывами"
