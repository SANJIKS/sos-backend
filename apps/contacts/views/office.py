from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from ..models.office import Office
from ..serializers.office import OfficeSerializer, OfficeListSerializer


@extend_schema_view(
    list=extend_schema(tags=['contacts']),
    retrieve=extend_schema(tags=['contacts']),
)
class OfficeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для офисов и локаций (только чтение)
    """
    queryset = Office.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['office_type', 'is_main_office']
    search_fields = ['name', 'address', 'description']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order', 'name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OfficeListSerializer
        return OfficeSerializer
