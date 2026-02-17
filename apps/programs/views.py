from drf_spectacular.utils import extend_schema_view, extend_schema
from apps.common.views import BaseContentViewSet
from .models import Program
from .serializers import ProgramSerializer, ProgramListSerializer, ProgramDetailSerializer


@extend_schema_view(
    list=extend_schema(tags=['programs']),
    retrieve=extend_schema(tags=['programs']),
)
class ProgramViewSet(BaseContentViewSet):
    """
    ViewSet для программ (только чтение)
    """
    queryset = Program.objects.prefetch_related('steps').all()
    serializer_class = ProgramSerializer
    list_serializer_class = ProgramListSerializer
    filterset_fields = ['program_type', 'is_featured', 'is_main_program']
    search_fields = ['title', 'description', 'short_description']
    lookup_field = 'uuid'
    
    def get_serializer_class(self):
        """
        Возвращает детальный сериализатор для детальной страницы
        """
        if self.action == 'retrieve':
            return ProgramDetailSerializer
        return super().get_serializer_class()
