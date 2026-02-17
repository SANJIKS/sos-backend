from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import SocialNetwork
from .serializers import SocialNetworkSerializer, SocialNetworkListSerializer


@extend_schema_view(
    list=extend_schema(tags=['social-networks']),
    retrieve=extend_schema(tags=['social-networks']),
)
class SocialNetworkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для социальных сетей (только чтение)
    """
    queryset = SocialNetwork.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['network_type', 'is_featured', 'is_verified']
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'name', 'followers_count']
    ordering = ['order', 'name']
    lookup_field = 'uuid'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SocialNetworkListSerializer
        return SocialNetworkSerializer
