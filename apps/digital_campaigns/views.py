from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import DigitalCampaign, CampaignMetric
from .serializers import (
    DigitalCampaignSerializer,
    DigitalCampaignListSerializer,
    DigitalCampaignStatsSerializer,
    CampaignMetricSerializer
)


@extend_schema_view(
    list=extend_schema(tags=['digital-campaigns']),
    retrieve=extend_schema(tags=['digital-campaigns']),
)
class DigitalCampaignViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для управления цифровыми кампаниями"""
    
    queryset = DigitalCampaign.objects.all()
    lookup_field = 'uuid'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['campaign_type', 'status', 'impact_level', 'is_featured', 'is_public']
    search_fields = ['title', 'description', 'short_description', 'target_audience']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'budget_planned', 'engagement_rate']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return DigitalCampaignListSerializer
        return DigitalCampaignSerializer

    def get_queryset(self):
        """Фильтрация по публичности для неавторизованных пользователей"""
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        return queryset

    @extend_schema(
        summary="Получить активные кампании",
        description="Возвращает список активных цифровых кампаний",
        tags=['digital-campaigns']
    )
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить активные кампании"""
        active_campaigns = self.get_queryset().filter(
            status='active',
            start_date__lte=timezone.now()
        ).filter(
            Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True)
        )
        
        serializer = DigitalCampaignListSerializer(active_campaigns, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить рекомендуемые кампании",
        description="Возвращает список рекомендуемых кампаний",
        tags=['digital-campaigns']
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Получить рекомендуемые кампании"""
        featured_campaigns = self.get_queryset().filter(
            is_featured=True,
            is_public=True
        )
        serializer = DigitalCampaignListSerializer(featured_campaigns, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить завершенные кампании",
        description="Возвращает список завершенных кампаний с результатами",
        tags=['digital-campaigns']
    )
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Получить завершенные кампании"""
        completed_campaigns = self.get_queryset().filter(
            status='completed',
            is_public=True
        )
        serializer = DigitalCampaignListSerializer(completed_campaigns, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Статистика цифровых кампаний",
        description="Возвращает общую статистику по цифровым кампаниям",
        tags=['digital-campaigns']
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Общая статистика цифровых кампаний"""
        queryset = self.get_queryset()
        
        # Основная статистика
        total_campaigns = queryset.count()
        active_campaigns = queryset.filter(status='active').count()
        completed_campaigns = queryset.filter(status='completed').count()
        
        # Бюджетная статистика
        budget_stats = queryset.aggregate(
            total_planned=Sum('budget_planned'),
            total_spent=Sum('budget_spent')
        )
        
        # Метрики
        metrics_stats = queryset.aggregate(
            total_visits=Sum('website_visits'),
            total_reach=Sum('social_media_reach'),
            avg_engagement=Avg('engagement_rate'),
            avg_conversion=Avg('conversion_rate')
        )
        
        # Статистика по типам
        campaigns_by_type = dict(queryset.values('campaign_type').annotate(
            count=Count('id')
        ).values_list('campaign_type', 'count'))
        
        # Статистика по статусам
        campaigns_by_status = dict(queryset.values('status').annotate(
            count=Count('id')
        ).values_list('status', 'count'))
        
        # Статистика по уровням воздействия
        campaigns_by_impact = dict(queryset.values('impact_level').annotate(
            count=Count('id')
        ).values_list('impact_level', 'count'))
        
        # Топ кампании по вовлеченности
        top_campaigns = queryset.filter(
            is_public=True
        ).order_by('-engagement_rate')[:5]
        
        # Последние кампании
        recent_campaigns = queryset.filter(
            is_public=True
        ).order_by('-created_at')[:5]
        
        stats_data = {
            'total_campaigns': total_campaigns,
            'active_campaigns': active_campaigns,
            'completed_campaigns': completed_campaigns,
            'total_budget_planned': budget_stats['total_planned'] or 0,
            'total_budget_spent': budget_stats['total_spent'] or 0,
            'total_website_visits': metrics_stats['total_visits'] or 0,
            'total_social_media_reach': metrics_stats['total_reach'] or 0,
            'average_engagement_rate': metrics_stats['avg_engagement'] or 0,
            'average_conversion_rate': metrics_stats['avg_conversion'] or 0,
            'campaigns_by_type': campaigns_by_type,
            'campaigns_by_status': campaigns_by_status,
            'campaigns_by_impact_level': campaigns_by_impact,
            'top_performing_campaigns': DigitalCampaignListSerializer(top_campaigns, many=True).data,
            'recent_campaigns': DigitalCampaignListSerializer(recent_campaigns, many=True).data,
        }
        
        serializer = DigitalCampaignStatsSerializer(stats_data)
        return Response(serializer.data)


    @extend_schema(
        summary="Получить метрики кампании",
        description="Возвращает все метрики указанной кампании",
        tags=['digital-campaigns']
    )
    @action(detail=True, methods=['get'])
    def metrics(self, request, uuid=None):
        """Получить метрики кампании"""
        campaign = self.get_object()
        metrics = campaign.metrics.all()
        serializer = CampaignMetricSerializer(metrics, many=True)
        return Response(serializer.data)


class CampaignMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра метрик кампаний"""
    
    queryset = CampaignMetric.objects.all()
    serializer_class = CampaignMetricSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Фильтрация метрик по кампании"""
        campaign_uuid = self.request.query_params.get('campaign')
        if campaign_uuid:
            return self.queryset.filter(campaign__uuid=campaign_uuid)
        return self.queryset
