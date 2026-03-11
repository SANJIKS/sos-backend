from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import SOSFriend


@admin.register(SOSFriend)
class SOSFriendAdmin(ModelAdmin):
    list_display = ['name', 'location', 'photo_preview', 'short_message', 'is_active', 'sort_order', 'created_at']
    list_editable = ['is_active', 'sort_order']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'location', 'message']
    ordering = ['sort_order', '-created_at']
    readonly_fields = ['created_at', 'updated_at', 'photo_preview']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'location', 'photo', 'photo_preview', 'message')
        }),
        ('Настройки', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;" />',
                obj.photo.url
            )
        return '—'
    photo_preview.short_description = 'Фото'

    def short_message(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    short_message.short_description = 'Сообщение'