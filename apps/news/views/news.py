from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta

from drf_spectacular.utils import extend_schema, extend_schema_view
from apps.news.models import News, NewsCategory, NewsTag
from apps.news.serializers import (
    NewsSerializer,
    NewsListSerializer,
    NewsDetailSerializer,
    NewsCategorySerializer,
    NewsTagSerializer,
    NewsStatsSerializer
)
from apps.news.filters import NewsFilter


@extend_schema_view(
    list=extend_schema(tags=['news']),
    retrieve=extend_schema(tags=['news']),
)
class NewsCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для управления категориями новостей"""
    
    queryset = NewsCategory.objects.all()
    serializer_class = NewsCategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        queryset = NewsCategory.objects.all()
        
        # Фильтр по активности для публичного API
        if self.action in ['list', 'retrieve'] and not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('sort_order', 'name')


@extend_schema_view(
    list=extend_schema(tags=['news']),
    retrieve=extend_schema(tags=['news']),
)
class NewsTagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для управления тегами новостей"""
    
    queryset = NewsTag.objects.all()
    serializer_class = NewsTagSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    @extend_schema(tags=['news'])
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Популярные теги по количеству новостей"""
        tags = NewsTag.objects.annotate(
            news_count=Count('news', filter=Q(news__status=News.Status.PUBLISHED))
        ).filter(news_count__gt=0).order_by('-news_count')[:10]
        
        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=['news']),
    retrieve=extend_schema(tags=['news']),
)
class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для управления новостями"""
    
    queryset = News.objects.all()
    permission_classes = [permissions.AllowAny]
    lookup_field = 'uuid'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = NewsFilter
    
    # Сортировка
    ordering_fields = ['published_at', 'created_at', 'views_count', 'title']
    ordering = ['-published_at', '-created_at']
    
    def get_queryset(self):
        queryset = News.objects.select_related('author', 'category').prefetch_related('tags')
        
        # Для публичного API показываем только опубликованные новости
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                status=News.Status.PUBLISHED,
                published_at__lte=timezone.now()
            )
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return NewsListSerializer
        elif self.action == 'retrieve':
            return NewsDetailSerializer
        return NewsSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Получение детальной информации о новости с увеличением счетчика просмотров"""
        instance = self.get_object()
        
        # Увеличиваем счетчик просмотров только для опубликованных новостей
        if instance.status == News.Status.PUBLISHED and not request.user.is_staff:
            instance.increment_views()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    
    @extend_schema(tags=['news'])
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Рекомендуемые новости"""
        featured_news = self.get_queryset().filter(is_featured=True)[:5]
        serializer = NewsListSerializer(featured_news, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['news'])
    @action(detail=False, methods=['get'])
    def breaking(self, request):
        """Срочные новости"""
        breaking_news = self.get_queryset().filter(
            status=News.Status.PUBLISHED,
            is_pinned=True
        )[:3]
        serializer = NewsListSerializer(breaking_news, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['news'])
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Последние новости"""
        latest_news = self.get_queryset()[:10]
        serializer = NewsListSerializer(latest_news, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['news'])
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Популярные новости по просмотрам"""
        # Популярные за последний месяц
        month_ago = timezone.now() - timedelta(days=30)
        popular_news = self.get_queryset().filter(
            published_at__gte=month_ago
        ).order_by('-views_count')[:10]
        
        serializer = NewsListSerializer(popular_news, many=True, context={'request': request})
        return Response(serializer.data)
    


@extend_schema_view(
    list=extend_schema(tags=['news'])
)
class NewsStatsView(viewsets.ViewSet):
    """ViewSet для статистики новостей"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """Общая статистика новостей"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Основная статистика
        total_news = News.objects.count()
        published_news = News.objects.filter(status=News.Status.PUBLISHED).count()
        draft_news = News.objects.filter(status=News.Status.DRAFT).count()
        featured_news = News.objects.filter(is_featured=True).count()
        total_views = News.objects.aggregate(total=Sum('views_count'))['total'] or 0
        
        # Статистика по категориям и тегам
        categories_count = NewsCategory.objects.count()
        tags_count = NewsTag.objects.count()
        
        # Новости по категориям
        news_by_category = {}
        for category in NewsCategory.objects.annotate(news_count=Count('news')):
            news_by_category[category.name] = category.news_count
        
        # Популярные теги
        popular_tags = []
        for tag in NewsTag.objects.annotate(news_count=Count('news')).order_by('-news_count')[:10]:
            popular_tags.append({
                'name': tag.name,
                'count': tag.news_count
            })
        
        # Последние новости
        recent_news = News.objects.order_by('-created_at')[:5]
        
        stats_data = {
            'total_news': total_news,
            'published_news': published_news,
            'draft_news': draft_news,
            'featured_news': featured_news,
            'total_views': total_views,
            'categories_count': categories_count,
            'tags_count': tags_count,
            'news_by_category': news_by_category,
            'popular_tags': popular_tags,
            'recent_news': recent_news
        }
        
        serializer = NewsStatsSerializer(stats_data)
        return Response(serializer.data)