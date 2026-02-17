"""
Фильтры для новостей
"""
import django_filters
from django.db.models import Q
from .models import News


class NewsFilter(django_filters.FilterSet):
    """
    Упрощенный фильтр для новостей с кастомной сортировкой и поиском
    """
    
    # Кастомная сортировка по is_featured
    featured_sort = django_filters.BooleanFilter(
        method='filter_featured_sort',
        help_text='Сортировка: true = новые сверху (-published_at), false = старые сверху (published_at)'
    )
    
    # Поиск по тексту
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='Поиск по заголовку, подзаголовку, содержанию и краткому описанию'
    )
    
    class Meta:
        model = News
        fields = ['featured_sort', 'search']
    
    def filter_featured_sort(self, queryset, name, value):
        """
        Кастомная сортировка по is_featured
        true = сортировка по -published_at (новые сверху)
        false = сортировка по published_at (старые сверху)
        """
        if value is True:
            return queryset.order_by('-published_at')
        elif value is False:
            return queryset.order_by('published_at')
        
        return queryset
    
    def filter_search(self, queryset, name, value):
        """
        Поиск по нескольким полям
        """
        if not value:
            return queryset
        
        return queryset.filter(
            Q(title__icontains=value) |
            Q(title_kg__icontains=value) |
            Q(title_en__icontains=value) |
            Q(content__icontains=value) |
            Q(content_kg__icontains=value) |
            Q(content_en__icontains=value) |
            Q(excerpt__icontains=value) |
            Q(excerpt_kg__icontains=value) |
            Q(excerpt_en__icontains=value)
        )
    
