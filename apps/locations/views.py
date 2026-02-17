from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import MapPoint
from .serializers import MapPointSerializer


@extend_schema_view(
    list=extend_schema(tags=['locations']),
    retrieve=extend_schema(tags=['locations']),
)
class MapPointViewSet(viewsets.ReadOnlyModelViewSet):
    """API для точек карты Кыргызстана"""
    queryset = MapPoint.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = MapPointSerializer
    lookup_field = 'point_id'
    
    @extend_schema(
        summary="Получить все точки карты",
        description="Возвращает все активные точки на карте Кыргызстана с координатами",
        tags=['locations']
    )
    @action(detail=False, methods=['get'])
    def map_points(self, request):
        """Получить все точки карты"""
        points = self.get_queryset()
        serializer = self.get_serializer(points, many=True)
        return Response(serializer.data)
