from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter, ChoicesDropdownFilter
from .models import SuccessStory


@admin.register(SuccessStory)
class SuccessStoryAdmin(ModelAdmin):
    list_display = ['author_image_preview', 'title', 'author_name', 'story_type_display', 'is_active', 'is_featured', 'order', 'created_at']
    list_filter = [
        ('story_type', ChoicesDropdownFilter),
        ('is_active', ChoicesDropdownFilter),
        ('is_featured', ChoicesDropdownFilter),
        ('created_at', RangeDateFilter),
    ]
    search_fields = ['title', 'quote_text', 'author_name', 'author_position']
    list_editable = ['is_active', 'is_featured', 'order']
    readonly_fields = ['author_image_preview', 'banner_image_preview', 'created_at', 'updated_at']
    actions = ['make_active', 'make_inactive', 'make_featured', 'remove_featured']

    def author_image_preview(self, obj):
        if obj.author_image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 40px; max-width: 40px; border-radius: 50%;" /></a>',
                obj.author_image.url
            )
        return "—"
    author_image_preview.short_description = "Фото"

    def banner_image_preview(self, obj):
        if obj.banner_image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 120px; border-radius: 8px;" /></a>',
                obj.banner_image.url
            )
        return "—"
    banner_image_preview.short_description = "Превью баннера"

    def story_type_display(self, obj):
        colors = {
            'success': '#28a745', 'family': '#e91e63',
            'education': '#007bff', 'personal_growth': '#fd7e14',
            'community': '#6f42c1', 'other': '#6c757d'
        }
        color = colors.get(obj.story_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 4px 8px; background: {}20; border-radius: 4px;">{}</span>',
            color, color, obj.get_story_type_display()
        )
    story_type_display.short_description = "Тип истории"

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = 'Активировать'

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = 'Деактивировать'

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
    make_featured.short_description = 'Пометить как рекомендуемые'

    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
    remove_featured.short_description = 'Убрать пометку рекомендуемых'

    fieldsets = (
        ('📝 Основная информация', {
            'fields': ('title', 'quote_text', 'author_name', 'author_position', 'author_image', 'author_image_preview'),
        }),
        ('🖼️ Медиа', {
            'fields': ('banner_image', 'banner_image_preview', 'video_url'),
        }),
        ('📖 Контент', {
            'fields': ('description', 'full_story'),
        }),
        ('🏷️ Классификация', {
            'fields': ('story_type',),
        }),
        ('⚙️ Управление отображением', {
            'fields': ('is_active', 'is_featured', 'order'),
        }),
        ('🔧 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )