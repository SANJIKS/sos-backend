"""
Базовые классы для ViewSets
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view


class BaseReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Базовый ViewSet только для чтения с общими настройками
    """
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['order', 'title']
    
    def get_serializer_class(self):
        """Возвращает ListSerializer для списка, основной для детального просмотра"""
        if self.action == 'list':
            # Ищем ListSerializer в том же модуле
            serializer_module = self.__class__.__module__
            if hasattr(self, 'list_serializer_class'):
                return self.list_serializer_class
            # Пытаемся найти ListSerializer автоматически
            try:
                import importlib
                module = importlib.import_module(serializer_module.replace('.views', '.serializers'))
                if hasattr(module, f'{self.__class__.__name__.replace("ViewSet", "")}ListSerializer'):
                    return getattr(module, f'{self.__class__.__name__.replace("ViewSet", "")}ListSerializer')
            except (ImportError, AttributeError):
                pass
        return self.serializer_class


class BaseContentViewSet(BaseReadOnlyViewSet):
    """
    Базовый ViewSet для контентных объектов
    """
    filterset_fields = ['is_active', 'is_featured']
    search_fields = ['title', 'description']
    ordering_fields = ['order', 'title', 'created_at']
    
    def get_queryset(self):
        """Фильтрует только активные объекты"""
        return self.queryset.filter(is_active=True)


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    Базовый ViewSet с общими настройками
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор в зависимости от действия"""
        if self.action == 'list':
            if hasattr(self, 'list_serializer_class'):
                return self.list_serializer_class
        elif self.action == 'create':
            if hasattr(self, 'create_serializer_class'):
                return self.create_serializer_class
        return self.serializer_class
