from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    ChoicesDropdownFilter
)

from apps.faq.models import FAQ


@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ('question_preview', 'category_display', 'number_of_questions')
    list_filter = [
        ('number_of_questions', ChoicesDropdownFilter),
    ]
    search_fields = ('question', 'answer')
    ordering = ['number_of_questions', 'question']
    readonly_fields = ['question_preview']
    actions = ['reorder_questions']
    
    def question_preview(self, obj):
        """Превью вопроса"""
        if len(obj.question) > 50:
            return format_html(
                '{}...',
                obj.question[:50]
            )
        return obj.question
    question_preview.short_description = "Вопрос"
    
    def category_display(self, obj):
        """Цветное отображение номера вопроса"""
        colors = ['#007bff', '#28a745', '#fd7e14', '#6f42c1', '#20c997', '#dc3545']
        color = colors[obj.number_of_questions % len(colors)]
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">#{}</span>',
            color, color, obj.number_of_questions
        )
    category_display.short_description = "Номер"
    
    # Действия
    def reorder_questions(self, request, queryset):
        """Переупорядочить вопросы"""
        for i, faq in enumerate(queryset.order_by('number_of_questions'), 1):
            faq.number_of_questions = i
            faq.save()
        self.message_user(request, f'{queryset.count()} вопросов переупорядочены.')
    reorder_questions.short_description = 'Переупорядочить вопросы'
    
    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('question', 'answer', 'number_of_questions'),
            'description': 'Вопрос и ответ FAQ'
        }),
    )