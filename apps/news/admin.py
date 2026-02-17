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

from apps.news.models import News, NewsCategory, NewsTag
from apps.news.models.news import NewsImage


@admin.register(NewsCategory)
class NewsCategoryAdmin(ModelAdmin):
    list_display = ('name', 'color_display', 'news_count', 'is_active', 'sort_order', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'name_kg', 'name_en', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('sort_order', 'name')
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'name_kg', 'name_en', 'description', 'description_kg', 'description_en')
        }),
        ('Настройки', {
            'fields': ('slug', 'color', 'icon', 'is_active', 'sort_order')
        }),
        ('Системная информация', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; width: 20px; height: 20px; '
            'display: inline-block; border-radius: 3px;"></span>',
            obj.color
        )
    color_display.short_description = 'Цвет'
    
    def news_count(self, obj):
        count = obj.news.count()
        url = reverse('admin:news_news_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} новост(ей)</a>', url, count)
    news_count.short_description = 'Количество новостей'


@admin.register(NewsTag)
class NewsTagAdmin(ModelAdmin):
    list_display = ('name', 'color_display', 'news_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'name_kg', 'name_en')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    readonly_fields = ['uuid', 'created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'name_kg', 'name_en', 'slug', 'color', 'is_active')
        }),
        ('Системная информация', {
            'fields': ('uuid', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; width: 20px; height: 20px; '
            'display: inline-block; border-radius: 3px;"></span>',
            obj.color
        )
    color_display.short_description = 'Цвет'
    
    def news_count(self, obj):
        count = obj.news.count()
        url = reverse('admin:news_news_changelist') + f'?tags__id__exact={obj.id}'
        return format_html('<a href="{}">{} новост(ей)</a>', url, count)
    news_count.short_description = 'Количество новостей'


class NewsImageInline(TabularInline):
    model = NewsImage
    extra = 1
    min_num = 3

    fields = ('image_preview', 'image', 'caption', 'is_main')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 80px; max-width: 100px;" /></a>',
                obj.image.url)
        return "Предпросмотр будет доступен после сохранения"

    image_preview.short_description = 'Превью'

@admin.register(News)
class NewsAdmin(ModelAdmin):
    inlines = [NewsImageInline]

    list_display = (
        'main_image_preview',
        'title', 'status_display', 'category', 'content_type_display', 
        'author', 'published_at', 'views_count', 'is_featured', 'is_pinned'
    )
    list_filter = (
        ('status', ChoicesDropdownFilter),
        ('content_type', ChoicesDropdownFilter),
        ('category', MultipleRelatedDropdownFilter),
        ('tags', MultipleRelatedDropdownFilter),
        ('author', MultipleRelatedDropdownFilter),
        'is_featured',
        'is_pinned',
        ('published_at', RangeDateFilter),
        ('created_at', RangeDateFilter),
    )
    search_fields = ('title', 'title_kg', 'title_en', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    readonly_fields = [
        'uuid', 'views_count', 'likes_count', 'created_at', 'updated_at', 
        'published_at', 'reading_time'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'uuid', 'title', 'title_kg', 'title_en', 'slug', 'excerpt', 'excerpt_kg', 'excerpt_en'
            )
        }),
        ('Контент', {
            'fields': ('content', 'content_kg', 'content_en')
        }),
        ('Медиа', {
            'fields': ('video_url', 'attachment'),
            'classes': ('collapse',)
        }),
        ('Категоризация', {
            'fields': ('category', 'tags', 'content_type', 'author')
        }),
        ('Публикация', {
            'fields': (
                'status', 'published_at', 'scheduled_at',
                'is_featured', 'is_pinned'
            )
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Социальные сети', {
            'fields': ('social_title', 'social_description', 'social_image'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('external_url',),
            'classes': ('collapse',)
        }),
        ('Статистика', {
            'fields': ('views_count', 'likes_count', 'reading_time', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ('-created_at',)
    date_hierarchy = 'published_at'
    
    actions = ['make_published', 'make_draft', 'make_featured', 'remove_featured', 'make_pinned', 'remove_pinned']
    
    def status_display(self, obj):
        colors = {
            'draft': '#6c757d',
            'published': '#28a745', 
            'archived': '#ffc107',
            'scheduled': '#17a2b8'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Статус'

    def main_image_preview(self, obj):
        if obj.featured_image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 70px;" />', obj.featured_image.url)
        return "Нет фото"
    main_image_preview.short_description = 'Обложка'
    
    def content_type_display(self, obj):
        colors = {
            'news': '#007bff',
            'article': '#28a745',
            'story': '#fd7e14',
            'announcement': '#6f42c1',
            'success_story': '#20c997'
        }
        color = colors.get(obj.content_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_content_type_display()
        )
    content_type_display.short_description = 'Тип контента'
    
    def make_published(self, request, queryset):
        updated = queryset.update(status=News.Status.PUBLISHED)
        self.message_user(request, f'{updated} новост(ей) опубликовано.')
    make_published.short_description = 'Опубликовать выбранные новости'
    
    def make_draft(self, request, queryset):
        updated = queryset.update(status=News.Status.DRAFT)
        self.message_user(request, f'{updated} новост(ей) переведено в черновики.')
    make_draft.short_description = 'Перевести в черновики'
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} новост(ей) помечено как рекомендуемые.')
    make_featured.short_description = 'Пометить как рекомендуемые'
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'У {updated} новост(ей) убрана пометка рекомендуемых.')
    remove_featured.short_description = 'Убрать пометку рекомендуемых'
    
    def make_pinned(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'{updated} новост(ей) закреплено.')
    make_pinned.short_description = 'Закрепить новости'
    
    def remove_pinned(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'У {updated} новост(ей) убрано закрепление.')
    remove_pinned.short_description = 'Убрать закрепление'
    
    def save_model(self, request, obj, form, change):
        if not change:  # При создании
            obj.author = request.user
        super().save_model(request, obj, form, change)