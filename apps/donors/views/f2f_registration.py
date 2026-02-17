from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from drf_spectacular.utils import extend_schema, extend_schema_view
from apps.donors.models import (
    F2FRegistration, 
    F2FRegistrationDocument, 
    F2FDailyReport,
    F2FCoordinator,
    F2FLocation
)
from apps.donors.serializers import (
    F2FRegistrationListSerializer,
    F2FRegistrationDetailSerializer,
    F2FRegistrationSerializer,
    F2FRegistrationMobileSerializer,
    F2FRegistrationDocumentSerializer,
    F2FDailyReportSerializer,
    F2FRegistrationStatsSerializer
)


@extend_schema_view(
    list=extend_schema(tags=['donors']),
    retrieve=extend_schema(tags=['donors']),
)
class F2FRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для управления F2F регистрациями"""
    
    queryset = F2FRegistration.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = {
        'status': ['exact'],
        'donation_type': ['exact'],
        'payment_method': ['exact'],
        'is_synced': ['exact'],
        'registered_at': ['gte', 'lte'],
        'gender': ['exact'],
        'preferred_language': ['exact'],
    }
    search_fields = ['full_name', 'email', 'phone', 'registration_number']
    ordering_fields = ['registered_at', 'created_at', 'full_name', 'donation_amount']
    ordering = ['-registered_at']
    
    def get_queryset(self):
        return F2FRegistration.objects.select_related(
            'coordinator', 'location', 'donor', 'user'
        ).prefetch_related('documents')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return F2FRegistrationListSerializer
        elif self.action == 'retrieve':
            return F2FRegistrationDetailSerializer
        elif self.action == 'mobile_create':
            return F2FRegistrationMobileSerializer
        return F2FRegistrationSerializer
    
    def get_permissions(self):
        """Права доступа"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['post'])
    def mobile_create(self, request):
        """Создание регистрации через мобильное приложение"""
        serializer = F2FRegistrationMobileSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        
        return Response(
            F2FRegistrationDetailSerializer(registration, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Регистрации ожидающие обработки"""
        registrations = self.get_queryset().filter(status=F2FRegistration.Status.PENDING)
        serializer = F2FRegistrationListSerializer(registrations, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def unsynced(self, request):
        """Несинхронизированные регистрации"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        registrations = self.get_queryset().filter(is_synced=False)
        serializer = F2FRegistrationListSerializer(registrations, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def by_coordinator(self, request):
        """Регистрации по координатору"""
        coordinator_uuid = request.query_params.get('coordinator_uuid')
        if not coordinator_uuid:
            return Response(
                {'error': 'coordinator_uuid parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registrations = self.get_queryset().filter(coordinator__uuid=coordinator_uuid)
        
        page = self.paginate_queryset(registrations)
        if page is not None:
            serializer = F2FRegistrationListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = F2FRegistrationListSerializer(registrations, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def by_location(self, request):
        """Регистрации по локации"""
        location_uuid = request.query_params.get('location_uuid')
        if not location_uuid:
            return Response(
                {'error': 'location_uuid parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registrations = self.get_queryset().filter(location__uuid=location_uuid)
        serializer = F2FRegistrationListSerializer(registrations, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['post'])
    def confirm(self, request, uuid=None):
        """Подтверждение регистрации"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        registration = self.get_object()
        registration.status = F2FRegistration.Status.CONFIRMED
        registration.save(update_fields=['status'])
        
        serializer = self.get_serializer(registration)
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['post'])
    def reject(self, request, uuid=None):
        """Отклонение регистрации"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        registration = self.get_object()
        registration.status = F2FRegistration.Status.REJECTED
        registration.admin_notes = request.data.get('reason', '')
        registration.save(update_fields=['status', 'admin_notes'])
        
        serializer = self.get_serializer(registration)
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['post'])
    def process(self, request, uuid=None):
        """Обработка регистрации (создание донора и пользователя)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        registration = self.get_object()
        
        if registration.status != F2FRegistration.Status.PENDING:
            return Response(
                {'error': 'Registration is not pending'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Создаем пользователя
            from apps.users.models import User
            from apps.donors.models import Donor
            
            user, created = User.objects.get_or_create(
                email=registration.email,
                defaults={
                    'full_name': registration.full_name,
                    'phone': registration.phone,
                    'is_active': True
                }
            )
            
            # Создаем донора
            donor, created = Donor.objects.get_or_create(
                email=registration.email,
                defaults={
                    'user': user,
                    'full_name': registration.full_name,
                    'phone': registration.phone,
                    'gender': registration.gender,
                    'birth_date': registration.birth_date,
                    'preferred_language': registration.preferred_language
                }
            )
            
            # Связываем регистрацию с донором и пользователем
            registration.donor = donor
            registration.user = user
            registration.status = F2FRegistration.Status.PROCESSED
            registration.save(update_fields=['donor', 'user', 'status'])
            
            # Создаем пожертвование
            from apps.donations.models import Donation, DonationCampaign
            
            # Получаем или создаем F2F кампанию
            f2f_campaign, _ = DonationCampaign.objects.get_or_create(
                name="F2F Registrations",
                defaults={
                    'description': 'Пожертвования через F2F координаторов',
                    'target_amount': 1000000.00,  # 1 млн сом
                    'start_date': timezone.now().date(),
                    'end_date': timezone.now().date() + timedelta(days=365),
                    'is_active': True
                }
            )
            
            # Создаем пожертвование
            donation = Donation.objects.create(
                donor=donor,
                campaign=f2f_campaign,
                amount=registration.donation_amount,
                donation_type='recurring' if registration.donation_type in ['monthly', 'quarterly', 'annual'] else 'one_time',
                payment_method=registration.payment_method,
                status='completed',  # F2F регистрации считаются выполненными
                metadata={
                    'f2f_registration_id': str(registration.uuid),
                    'coordinator_id': str(registration.coordinator.uuid),
                    'location_id': str(registration.location.uuid),
                    'registration_source': 'f2f'
                }
            )
            
            return Response({
                'message': 'Registration processed successfully',
                'donor_id': donor.id,
                'user_id': user.id,
                'donation_id': donation.id
            })
            
        except Exception as e:
            return Response(
                {'error': f'Processing failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(tags=['donors'])
    @action(detail=True, methods=['post'])
    def mark_synced(self, request, uuid=None):
        """Отметить как синхронизированное"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        registration = self.get_object()
        registration.mark_as_synced()
        
        return Response({'message': 'Registration marked as synced'})
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика F2F регистраций"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        now = timezone.now()
        today = now.date()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Общая статистика
        total_registrations = F2FRegistration.objects.count()
        today_registrations = F2FRegistration.objects.filter(registered_at__date=today).count()
        monthly_registrations = F2FRegistration.objects.filter(registered_at__gte=month_start).count()
        
        # Статистика по статусам
        pending_registrations = F2FRegistration.objects.filter(status=F2FRegistration.Status.PENDING).count()
        confirmed_registrations = F2FRegistration.objects.filter(status=F2FRegistration.Status.CONFIRMED).count()
        
        # Коэффициент конверсии
        if total_registrations > 0:
            conversion_rate = (confirmed_registrations / total_registrations) * 100
        else:
            conversion_rate = 0
        
        # Топ локации
        top_locations = list(F2FLocation.objects.annotate(
            reg_count=Count('registrations')
        ).order_by('-reg_count')[:5].values('name', 'reg_count'))
        
        # Топ координаторы
        top_coordinators = list(F2FCoordinator.objects.annotate(
            reg_count=Count('registrations')
        ).order_by('-reg_count')[:5].values('full_name', 'reg_count'))
        
        # Тренды регистраций (последние 7 дней)
        registration_trends = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = F2FRegistration.objects.filter(registered_at__date=date).count()
            registration_trends.append({
                'date': date.isoformat(),
                'count': count
            })
        
        # Статус синхронизации
        sync_status = {
            'synced': F2FRegistration.objects.filter(is_synced=True).count(),
            'unsynced': F2FRegistration.objects.filter(is_synced=False).count(),
            'sync_errors': F2FRegistration.objects.exclude(sync_error='').count()
        }
        
        stats_data = {
            'total_registrations': total_registrations,
            'today_registrations': today_registrations,
            'monthly_registrations': monthly_registrations,
            'pending_registrations': pending_registrations,
            'confirmed_registrations': confirmed_registrations,
            'conversion_rate': conversion_rate,
            'top_locations': top_locations,
            'top_coordinators': top_coordinators,
            'registration_trends': registration_trends,
            'sync_status': sync_status
        }
        
        serializer = F2FRegistrationStatsSerializer(stats_data)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=['donors']),
    retrieve=extend_schema(tags=['donors']),
    create=extend_schema(tags=['donors']),
    update=extend_schema(tags=['donors']),
    partial_update=extend_schema(tags=['donors']),
    destroy=extend_schema(tags=['donors']),
)
class F2FRegistrationDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet для документов F2F регистраций"""
    
    queryset = F2FRegistrationDocument.objects.all()
    serializer_class = F2FRegistrationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['registration', 'document_type', 'is_synced']
    
    def get_queryset(self):
        return F2FRegistrationDocument.objects.select_related('registration')
    
    def perform_create(self, serializer):
        """При создании документа получаем информацию о файле"""
        file = self.request.FILES.get('file')
        if file:
            serializer.save(
                file_name=file.name,
                file_size=file.size,
                content_type=file.content_type
            )
        else:
            serializer.save()


@extend_schema_view(
    list=extend_schema(tags=['donors']),
    retrieve=extend_schema(tags=['donors']),
    create=extend_schema(tags=['donors']),
    update=extend_schema(tags=['donors']),
    partial_update=extend_schema(tags=['donors']),
    destroy=extend_schema(tags=['donors']),
)
class F2FDailyReportViewSet(viewsets.ModelViewSet):
    """ViewSet для ежедневных отчетов F2F"""
    
    queryset = F2FDailyReport.objects.all()
    serializer_class = F2FDailyReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'report_date': ['gte', 'lte', 'exact'],
        'is_synced': ['exact'],
    }
    ordering_fields = ['report_date', 'created_at']
    ordering = ['-report_date']
    
    def get_queryset(self):
        return F2FDailyReport.objects.select_related('coordinator', 'location')
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def by_coordinator(self, request):
        """Отчеты по координатору"""
        coordinator_uuid = request.query_params.get('coordinator_uuid')
        if not coordinator_uuid:
            return Response(
                {'error': 'coordinator_uuid parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reports = self.get_queryset().filter(coordinator__uuid=coordinator_uuid)
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)
    
    @extend_schema(tags=['donors'])
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Сводка по отчетам"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        queryset = self.get_queryset()
        if date_from:
            queryset = queryset.filter(report_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(report_date__lte=date_to)
        
        summary = queryset.aggregate(
            total_approaches=Sum('total_approaches'),
            total_registrations=Sum('successful_registrations'),
            total_rejections=Sum('rejected_approaches'),
            avg_conversion=Avg('conversion_rate')
        )
        
        return Response({
            'total_approaches': summary['total_approaches'] or 0,
            'total_registrations': summary['total_registrations'] or 0,
            'total_rejections': summary['total_rejections'] or 0,
            'average_conversion_rate': round(summary['avg_conversion'] or 0, 2),
            'period': {
                'from': date_from,
                'to': date_to
            }
        })