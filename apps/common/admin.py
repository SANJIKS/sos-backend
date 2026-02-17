"""
Базовые классы для админки
"""
from django.contrib import admin
from django.utils.html import format_html


class BaseModelAdmin(admin.ModelAdmin):
    """
    Базовый класс для админки с общими настройками
    """
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    
    def get_queryset(self, request):
        """Оптимизированный queryset"""
        return super().get_queryset(request).select_related()


class BaseContentAdmin(BaseModelAdmin):
    """
    Базовый класс для админки контентных объектов
    """
    list_display = ['title', 'is_active', 'is_featured', 'order', 'created_at']
    list_filter = ['is_active', 'is_featured', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['order', 'title']
    list_editable = ['is_active', 'is_featured', 'order']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'image')
        }),
        ('Управление отображением', {
            'fields': ('is_active', 'is_featured', 'order')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class BaseContentWithSlugAdmin(BaseContentAdmin):
    """
    Базовый класс для админки контентных объектов со slug
    """
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'description', 'image')
        }),
        ('Управление отображением', {
            'fields': ('is_active', 'is_featured', 'order')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class BaseContentWithChoicesAdmin(BaseContentWithSlugAdmin):
    """
    Базовый класс для админки контентных объектов с choice полями
    """
    def get_list_display(self, request):
        """Добавляет поля типов в list_display"""
        base_display = list(super().get_list_display(request))
        # Находим choice поля и добавляем их в list_display
        choice_fields = []
        for field in self.model._meta.fields:
            if hasattr(field, 'choices') and field.choices and field.name != 'id':
                choice_fields.append(field.name)
        
        # Вставляем choice поля после title
        if choice_fields:
            base_display.insert(1, choice_fields[0])
        
        return base_display
    
    def get_list_filter(self, request):
        """Добавляет choice поля в list_filter"""
        base_filter = list(super().get_list_filter(request))
        # Находим choice поля и добавляем их в list_filter
        choice_fields = []
        for field in self.model._meta.fields:
            if hasattr(field, 'choices') and field.choices and field.name != 'id':
                choice_fields.append(field.name)
        
        base_filter.extend(choice_fields)
        return base_filter


class BaseModelAdminWithUUID(BaseModelAdmin):
    """
    Базовый класс для админки с UUID полем
    """
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    list_display = ['__str__', 'uuid', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['uuid']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('uuid',)
        }),
        ('Управление отображением', {
            'fields': ('is_active',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )