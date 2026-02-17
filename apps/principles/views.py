from drf_spectacular.utils import extend_schema_view, extend_schema
from apps.common.views import BaseContentViewSet
from .models import Principle
from .serializers import PrincipleSerializer, PrincipleListSerializer


@extend_schema_view(
    list=extend_schema(tags=['principles']),
    retrieve=extend_schema(tags=['principles']),
)
class PrincipleViewSet(BaseContentViewSet):
    """
    ViewSet для принципов SOS (только чтение)
    """
    queryset = Principle.objects.all()
    serializer_class = PrincipleSerializer
    list_serializer_class = PrincipleListSerializer
    filterset_fields = ['principle_type', 'is_featured']
    search_fields = ['title', 'subtitle', 'description']
    lookup_field = 'uuid'
