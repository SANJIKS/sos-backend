from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone
from datetime import timedelta

from drf_spectacular.utils import extend_schema, extend_schema_view
from apps.donors.models import (
    F2FCoordinator, 
    F2FRegion, 
    F2FLocation,
    F2FCoordinatorRegionAssignment
)
from apps.donors.serializers import (
    F2FRegionSerializer,
    F2FLocationSerializer,
    F2FCoordinatorListSerializer,
    F2FCoordinatorDetailSerializer,
    F2FCoordinatorSerializer,
    F2FCoordinatorStatsSerializer
)
from apps.common.models import AuditLog


@extend_schema_view(
    list=extend_schema(tags=['donors']),
    retrieve=extend_schema(tags=['donors']),
    create=extend_schema(tags=['donors']),
    update=extend_schema(tags=['donors']),
    partial_update=extend_schema(tags=['donors']),
    destroy=extend_schema(tags=['donors']),
)
class F2FRegionViewSet(viewsets.ModelViewSet):
    """ViewSet для управления F2F регионами"""
    
    queryset = F2FRegion.objects.all()
    serializer_class = F2FRegionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = F2FRegion.objects.all()
        
        # Фильтр по активности для обычных пользователей
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Активные регионы"""
        regions = F2FRegion.objects.filter(is_active=True)
        serializer = self.get_serializer(regions, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['get'])
    def coordinators(self, request, pk=None):
        """Координаторы региона"""
        region = self.get_object()
        coordinators = F2FCoordinator.objects.filter(
            f2fcoordinatorregionassignment__region=region,
            status=F2FCoordinator.Status.ACTIVE
        )
        serializer = F2FCoordinatorListSerializer(coordinators, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['get'])
    def locations(self, request, pk=None):
        """Локации региона"""
        region = self.get_object()
        locations = region.f2flocation_set.filter(status=F2FLocation.Status.ACTIVE)
        serializer = F2FLocationSerializer(locations, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=['donors']),
    retrieve=extend_schema(tags=['donors']),
    create=extend_schema(tags=['donors']),
    update=extend_schema(tags=['donors']),
    partial_update=extend_schema(tags=['donors']),
    destroy=extend_schema(tags=['donors']),
)
class F2FLocationViewSet(viewsets.ModelViewSet):
    """ViewSet для управления F2F локациями"""
    
    queryset = F2FLocation.objects.all()
    serializer_class = F2FLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'location_type': ['exact'],
        'status': ['exact'],
        'foot_traffic_level': ['exact'],
    }
    search_fields = ['name', 'address', 'contact_person']
    ordering_fields = ['name', 'region__name', 'created_at']
    ordering = ['region', 'name']
    
    def get_queryset(self):
        queryset = F2FLocation.objects.select_related('region')
        
        # Фильтр по активности для обычных пользователей
        if not self.request.user.is_staff:
            queryset = queryset.filter(status=F2FLocation.Status.ACTIVE)
        
        return queryset
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Активные локации"""
        locations = self.get_queryset().filter(status=F2FLocation.Status.ACTIVE)
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def by_region(self, request):
        """Локации по регионам"""
        region_id = request.query_params.get('region_id')
        if region_id:
            locations = self.get_queryset().filter(region_id=region_id)
        else:
            locations = self.get_queryset()
        
        serializer = self.get_serializer(locations, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['get'])
    def registrations(self, request, uuid=None):
        """Регистрации в локации"""
        from apps.donors.serializers import F2FRegistrationListSerializer
        
        location = self.get_object()
        registrations = location.registrations.order_by('-registered_at')[:20]
        serializer = F2FRegistrationListSerializer(registrations, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['get'])
    def stats(self, request, uuid=None):
        """Статистика локации"""
        location = self.get_object()
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        stats = location.registrations.aggregate(
            total=Count('id'),
            this_month=Count('id', filter=Q(registered_at__gte=month_start)),
            confirmed=Count('id', filter=Q(status='confirmed')),
        )
        
        return Response({
            'total_registrations': stats['total'],
            'monthly_registrations': stats['this_month'],
            'confirmed_registrations': stats['confirmed'],
            'location_info': self.get_serializer(location).data
        })


@extend_schema_view(
    list=extend_schema(tags=['donors']),
    retrieve=extend_schema(tags=['donors']),
)
class F2FCoordinatorViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для управления F2F координаторами"""
    
    queryset = F2FCoordinator.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'status': ['exact'],
        'experience_level': ['exact'],
    }
    search_fields = ['full_name', 'employee_id', 'email', 'phone']
    ordering_fields = ['full_name', 'hire_date', 'total_registrations', 'success_rate']
    ordering = ['-total_registrations']
    
    def get_queryset(self):
        return F2FCoordinator.objects.select_related('supervisor').prefetch_related(
            'assigned_regions',
            'f2fcoordinatorregionassignment_set__region'
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return F2FCoordinatorListSerializer
        elif self.action == 'retrieve':
            return F2FCoordinatorDetailSerializer
        return F2FCoordinatorSerializer
    
    def get_permissions(self):
        """Права доступа"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Активные координаторы"""
        coordinators = self.get_queryset().filter(status=F2FCoordinator.Status.ACTIVE)
        serializer = F2FCoordinatorListSerializer(coordinators, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def top_performers(self, request):
        """Топ координаторы по результатам"""
        limit = int(request.query_params.get('limit', 10))
        coordinators = self.get_queryset().filter(
            status=F2FCoordinator.Status.ACTIVE
        ).order_by('-success_rate', '-total_registrations')[:limit]
        
        serializer = F2FCoordinatorListSerializer(coordinators, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['get'])
    def registrations(self, request, uuid=None):
        """Регистрации координатора"""
        from apps.donors.serializers import F2FRegistrationListSerializer
        
        coordinator = self.get_object()
        registrations = coordinator.registrations.order_by('-registered_at')
        
        # Пагинация
        page = self.paginate_queryset(registrations)
        if page is not None:
            serializer = F2FRegistrationListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = F2FRegistrationListSerializer(registrations, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['get'])
    def daily_reports(self, request, uuid=None):
        """Ежедневные отчеты координатора"""
        from apps.donors.serializers import F2FDailyReportSerializer
        
        coordinator = self.get_object()
        reports = coordinator.daily_reports.order_by('-report_date')[:30]  # Последние 30 дней
        serializer = F2FDailyReportSerializer(reports, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['post'])
    def reset_monthly_stats(self, request, uuid=None):
        """Сброс месячной статистики"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        coordinator = self.get_object()
        coordinator.reset_monthly_stats()
        AuditLog.objects.create(
            user=request.user,
            source=AuditLog.Source.API,
            severity=AuditLog.Severity.INFO,
            object_type='F2FCoordinator',
            object_id=str(coordinator.uuid),
            action='reset_monthly_stats',
            message='Сброшена месячная статистика'
        )
        
        return Response({'message': 'Месячная статистика сброшена'})
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['post'])
    def change_status(self, request, uuid=None):
        """Изменение статуса координатора"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        coordinator = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(F2FCoordinator.Status.choices):
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        coordinator.status = new_status
        coordinator.save(update_fields=['status'])
        AuditLog.objects.create(
            user=request.user,
            source=AuditLog.Source.API,
            severity=AuditLog.Severity.INFO,
            object_type='F2FCoordinator',
            object_id=str(coordinator.uuid),
            action='change_status',
            message=f'Статус изменен на {new_status}'
        )
        
        serializer = self.get_serializer(coordinator)
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Общая статистика F2F координаторов"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Общая статистика
        total_coordinators = F2FCoordinator.objects.count()
        active_coordinators = F2FCoordinator.objects.filter(status=F2FCoordinator.Status.ACTIVE).count()
        
        # Статистика регистраций
        total_registrations = 0
        monthly_registrations = 0
        
        for coord in F2FCoordinator.objects.all():
            total_registrations += coord.total_registrations
            monthly_registrations += coord.current_month_registrations
        
        # Топ исполнители
        top_performers = F2FCoordinator.objects.filter(
            status=F2FCoordinator.Status.ACTIVE
        ).order_by('-success_rate')[:5]
        
        # Статистика по регионам
        regional_stats = {}
        for region in F2FRegion.objects.all():
            coords_in_region = F2FCoordinator.objects.filter(
                f2fcoordinatorregionassignment__region=region,
                status=F2FCoordinator.Status.ACTIVE
            ).count()
            regional_stats[region.name] = coords_in_region
        
        # Тренды производительности (последние 7 дней)
        performance_trends = []
        for i in range(7):
            date = (now - timedelta(days=i)).date()
            day_registrations = 0
            # Здесь можно добавить подсчет регистраций за конкретный день
            performance_trends.append({
                'date': date.isoformat(),
                'registrations': day_registrations
            })
        
        # Коэффициенты конверсии
        conversion_rates = {
            'overall': F2FCoordinator.objects.aggregate(avg_rate=Avg('success_rate'))['avg_rate'] or 0,
            'this_month': 0  # Можно добавить расчет за месяц
        }
        
        stats_data = {
            'total_coordinators': total_coordinators,
            'active_coordinators': active_coordinators,
            'total_registrations': total_registrations,
            'monthly_registrations': monthly_registrations,
            'top_performers': F2FCoordinatorListSerializer(top_performers, many=True, context={'request': request}).data,
            'regional_stats': regional_stats,
            'performance_trends': performance_trends,
            'conversion_rates': conversion_rates
        }
        
        serializer = F2FCoordinatorStatsSerializer(stats_data)
        return Response(serializer.data)