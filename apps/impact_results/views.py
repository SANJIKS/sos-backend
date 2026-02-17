from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import ImpactResult
from .serializers import ImpactResultSerializer, ImpactResultListSerializer


@extend_schema_view(
    list=extend_schema(tags=['impact-results']),
    retrieve=extend_schema(tags=['impact-results']),
)
class ImpactResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для результатов воздействия (только чтение)
    """
    queryset = ImpactResult.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['result_type', 'is_featured']
    search_fields = ['title', 'description', 'detailed_description']
    ordering_fields = ['order', 'percentage_value', 'created_at']
    ordering = ['order', 'percentage_value']
    lookup_field = 'uuid'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ImpactResultListSerializer
        return ImpactResultSerializer
