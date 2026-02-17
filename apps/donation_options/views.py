from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import DonationOption
from .serializers import DonationOptionSerializer, DonationOptionListSerializer


@extend_schema_view(
    list=extend_schema(tags=['donation-options']),
    retrieve=extend_schema(tags=['donation-options']),
)
class DonationOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для типов пожертвований (только чтение)
    """
    queryset = DonationOption.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['option_type', 'status', 'is_featured']
    search_fields = ['title', 'description', 'detailed_description']
    ordering_fields = ['order', 'title', 'created_at']
    ordering = ['order', 'title']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DonationOptionListSerializer
        return DonationOptionSerializer
