from drf_spectacular.utils import extend_schema_view, extend_schema
from apps.common.views import BaseContentViewSet
from .models import SuccessStory
from .serializers import SuccessStorySerializer, SuccessStoryListSerializer


@extend_schema_view(
    list=extend_schema(tags=['success-stories']),
    retrieve=extend_schema(tags=['success-stories']),
)
class SuccessStoryViewSet(BaseContentViewSet):
    """
    ViewSet для историй успеха (только чтение)
    """
    queryset = SuccessStory.objects.all()
    serializer_class = SuccessStorySerializer
    list_serializer_class = SuccessStoryListSerializer
    filterset_fields = ['is_featured', 'story_type']
    search_fields = ['title', 'quote_text', 'author_name', 'author_position']
    lookup_field = 'uuid'


