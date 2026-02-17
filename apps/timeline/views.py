from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import TimelineEvent
from .serializers import TimelineEventSerializer, TimelineEventListSerializer


@extend_schema_view(
    list=extend_schema(tags=['timeline']),
    retrieve=extend_schema(tags=['timeline']),
)
class TimelineEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для событий временной шкалы (только чтение)
    """
    queryset = TimelineEvent.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['event_type', 'is_featured']
    search_fields = ['title', 'description', 'year']
    ordering_fields = ['order', 'year', 'created_at']
    ordering = ['order', 'year']
    lookup_field = 'uuid'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TimelineEventListSerializer
        return TimelineEventSerializer
