from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.http import FileResponse
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
# from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from ..models import (
    Donation,
    DonationTransaction,
    DonationCampaign,
)
from ..serializers import (
    DonationSerializer,
    DonationCreateSerializer,
    DonationListSerializer,
    DonationTransactionSerializer,
    DonationCampaignSerializer,
    DonationCampaignListSerializer,
    DonationStatsSerializer,
    DonorStatsSerializer,
)
from ..permissions import DonationCreatePermission


@extend_schema_view(
    list=extend_schema(tags=['donations']),
    retrieve=extend_schema(tags=['donations']),
    create=extend_schema(tags=['donations']),
    update=extend_schema(tags=['donations']),
    partial_update=extend_schema(tags=['donations']),
    destroy=extend_schema(tags=['donations']),
)
class DonationCampaignViewSet(viewsets.ModelViewSet):
    """ViewSet для управления кампаниями пожертвований"""
    queryset = DonationCampaign.objects.all()
    lookup_field = 'uuid'
    filter_backends = [SearchFilter, OrderingFilter]
    # filterset_fields = ['status', 'is_featured']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'start_date', 'goal_amount', 'raised_amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return DonationCampaignListSerializer
        return DonationCampaignSerializer

    def get_permissions(self):
        """Публичные кампании могут видеть все, создавать/редактировать только админы"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="Получить активные кампании",
        description="Возвращает список активных кампаний пожертвований",
        tags=['donations']
    )
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить активные кампании"""
        active_campaigns = self.queryset.filter(
            status='active',
            start_date__lte=timezone.now()
        ).filter(
            Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True)
        )
        
        serializer = DonationCampaignListSerializer(active_campaigns, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить рекомендуемые кампании",
        description="Возвращает список рекомендуемых кампаний",
        tags=['donations']
    )
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Получить рекомендуемые кампании"""
        featured_campaigns = self.queryset.filter(is_featured=True, status='active')
        serializer = DonationCampaignListSerializer(featured_campaigns, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=['donations']),
    retrieve=extend_schema(tags=['donations']),
    create=extend_schema(tags=['donations']),
    update=extend_schema(tags=['donations']),
    partial_update=extend_schema(tags=['donations']),
    destroy=extend_schema(tags=['donations']),
)
class DonationViewSet(viewsets.ModelViewSet):
    """ViewSet для управления пожертвованиями"""
    queryset = Donation.objects.all()
    lookup_field = 'uuid'
    filter_backends = [SearchFilter, OrderingFilter]
    # filterset_fields = [
    #     'status', 'donation_type', 'payment_method', 'currency',
    #     'donor_source', 'is_recurring', 'campaign'
    # ]
    search_fields = ['donation_code', 'donor_full_name', 'donor_email']
    ordering_fields = ['created_at', 'amount', 'payment_completed_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return DonationCreateSerializer
        elif self.action == 'list':
            return DonationListSerializer
        return DonationSerializer

    def get_permissions(self):
        """
        Создать разовое пожертвование может любой,
        для рекуррентных подписок требуется авторизация,
        остальные действия только для авторизованных
        """
        if self.action == 'create':
            return [DonationCreatePermission()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Фильтрация по пользователю для обычных пользователей"""
        queryset = self.queryset
        
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            # Фильтруем по user, если указан, ИЛИ по email пользователя
            # Это нужно потому что донаты могут создаваться без user (для неавторизованных)
            # но потом пользователь авторизуется и хочет видеть свои донаты
            user_donations = Q(user=self.request.user)
            
            # Если у пользователя есть email, ищем донаты по email донора
            if self.request.user.email:
                user_donations |= Q(donor_email__iexact=self.request.user.email)
            
            queryset = queryset.filter(user_donations)
        
        # Фильтрация по параметрам запроса
        is_recurring = self.request.query_params.get('is_recurring')
        if is_recurring is not None:
            queryset = queryset.filter(is_recurring=is_recurring.lower() in ('true', '1', 'yes'))
        
        subscription_status = self.request.query_params.get('subscription_status')
        if subscription_status:
            queryset = queryset.filter(subscription_status=subscription_status)
        
        donation_type = self.request.query_params.get('donation_type')
        if donation_type:
            queryset = queryset.filter(donation_type=donation_type)
        
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset

    @extend_schema(
        summary="Получить все подписки и пожертвования",
        description="Возвращает все подписки и пожертвования текущего пользователя с возможностью фильтрации",
        tags=['donations'],
        parameters=[
            OpenApiParameter(
                name='is_recurring',
                description='Фильтр по типу: true - только подписки, false - только разовые, не указано - все',
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name='subscription_status',
                description='Фильтр по статусу подписки: active, paused, cancelled, pending',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='donation_type',
                description='Фильтр по типу пожертвования: one_time, monthly, quarterly, yearly',
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name='status',
                description='Фильтр по статусу платежа: pending, processing, completed, failed',
                required=False,
                type=str,
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def my_donations(self, request):
        """Получение всех подписок и пожертвований пользователя"""
        # Используем get_queryset который уже отфильтрован по пользователю
        queryset = self.get_queryset()
        
        # Применяем дополнительную сортировку (новые первыми)
        queryset = queryset.order_by('-created_at')
        
        # Используем DonationListSerializer который содержит все нужные поля
        # включая can_cancel_subscription, can_resume_subscription, etc.
        serializer = DonationListSerializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    @extend_schema(
        summary="Статистика пожертвований",
        description="Возвращает общую статистику по пожертвованиям",
        tags=['donations']
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """Общая статистика пожертвований"""
        # Базовые статистики
        total_donations = self.queryset.count()
        total_amount = self.queryset.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_donors = self.queryset.values('donor_email').distinct().count()
        recurring_donations = self.queryset.filter(is_recurring=True).count()
        
        average_donation = self.queryset.aggregate(
            avg=Avg('amount')
        )['avg'] or 0

        # Топ кампании
        top_campaigns = DonationCampaign.objects.annotate(
            donations_count=Count('donation'),
            donations_sum=Sum('donation__amount')
        ).filter(donations_count__gt=0).order_by('-donations_sum')[:5]

        top_campaigns_data = [{
            'name': campaign.name,
            'donations_count': campaign.donations_count,
            'donations_sum': campaign.donations_sum,
        } for campaign in top_campaigns]

        # Месячная статистика (последние 12 месяцев)
        monthly_stats = []
        for i in range(12):
            date = timezone.now() - timedelta(days=30 * i)
            start_date = date.replace(day=1)
            if i == 0:
                end_date = timezone.now()
            else:
                end_date = (date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_donations = self.queryset.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            monthly_stats.append({
                'month': start_date.strftime('%Y-%m'),
                'donations_count': month_donations.count(),
                'donations_sum': month_donations.aggregate(Sum('amount'))['amount__sum'] or 0,
            })

        stats_data = {
            'total_donations': total_donations,
            'total_amount': total_amount,
            'total_donors': total_donors,
            'recurring_donations': recurring_donations,
            'average_donation': average_donation,
            'top_campaigns': top_campaigns_data,
            'monthly_stats': list(reversed(monthly_stats)),
        }

        serializer = DonationStatsSerializer(stats_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Личная статистика донора",
        description="Возвращает статистику пожертвований текущего пользователя",
        tags=['donations']
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_stats(self, request):
        """Статистика пожертвований текущего пользователя"""
        user_donations = self.queryset.filter(user=request.user)
        
        total_personal_donations = user_donations.count()
        total_personal_amount = user_donations.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        active_subscriptions = user_donations.filter(
            is_recurring=True, 
            recurring_active=True
        ).count()
        
        last_donation = user_donations.order_by('-created_at').first()
        last_donation_date = last_donation.created_at if last_donation else None
        
        # История пожертвований (последние 10)
        donation_history = user_donations.order_by('-created_at')[:10]

        stats_data = {
            'total_personal_donations': total_personal_donations,
            'total_personal_amount': total_personal_amount,
            'active_subscriptions': active_subscriptions,
            'last_donation_date': last_donation_date,
            'donation_history': donation_history,
        }

        serializer = DonorStatsSerializer(stats_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Отменить рекуррентную подписку",
        description="Отменяет рекуррентную подписку пожертвования",
        tags=['donations']
    )
    @action(detail=True, methods=['post'])
    def cancel_subscription(self, request, uuid=None):
        """Отмена рекуррентной подписки"""
        donation = self.get_object()
        
        if not donation.is_recurring:
            return Response(
                {'error': 'Это не рекуррентное пожертвование'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем статус подписки
        if donation.subscription_status == 'cancelled':
            return Response(
                {'error': 'Подписка уже отменена'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем права доступа
        # Проверяем по user ИЛИ по email донора (для донатов созданных без авторизации)
        has_permission = (
            request.user.is_staff or
            donation.user == request.user or
            (request.user.is_authenticated and 
             request.user.email and 
             donation.donor_email and 
             donation.donor_email.lower() == request.user.email.lower())
        )
        
        if not has_permission:
            return Response(
                {'error': 'Нет прав для отмены этой подписки'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Обновляем статусы
        donation.recurring_active = False
        donation.subscription_status = 'cancelled'
        donation.save()
        
        # Логируем отзыв согласия
        try:
            from ..services.consent_logger import ConsentLoggerService
            consent_logger = ConsentLoggerService()
            consent_logger.log_consent_revocation(
                donation=donation,
                request=request,
                reason="Подписка отменена пользователем"
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log consent revocation: {e}")
        
        # TODO: Интеграция с платежной системой для отмены подписки
        
        return Response({
            'message': 'Подписка успешно отменена',
            'subscription_status': donation.subscription_status
        })

    @extend_schema(
        summary="Возобновить рекуррентную подписку",
        description="Возобновляет рекуррентную подписку пожертвования",
        tags=['donations']
    )
    @action(detail=True, methods=['post'])
    def resume_subscription(self, request, uuid=None):
        """Возобновление рекуррентной подписки"""
        donation = self.get_object()
        
        if not donation.is_recurring:
            return Response(
                {'error': 'Это не рекуррентное пожертвование'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем статус подписки
        if donation.subscription_status == 'active':
            return Response(
                {'error': 'Подписка уже активна'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем права доступа
        # Проверяем по user ИЛИ по email донора (для донатов созданных без авторизации)
        has_permission = (
            request.user.is_staff or
            donation.user == request.user or
            (request.user.is_authenticated and 
             request.user.email and 
             donation.donor_email and 
             donation.donor_email.lower() == request.user.email.lower())
        )
        
        if not has_permission:
            return Response(
                {'error': 'Нет прав для возобновления этой подписки'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Обновляем статусы
        donation.recurring_active = True
        donation.subscription_status = 'active'
        
        # Пересчитываем дату следующего платежа
        from ..serializers.donation import DonationCreateSerializer
        serializer = DonationCreateSerializer()
        donation.next_payment_date = serializer.calculate_next_payment_date(
            donation.donation_type
        )
        donation.save()
        
        # Логируем возобновление согласия
        try:
            from ..services.consent_logger import ConsentLoggerService
            consent_logger = ConsentLoggerService()
            consent_logger.log_recurring_consent(
                donation=donation,
                request=request,
                consent_text="Подписка возобновлена пользователем"
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log consent resumption: {e}")
        
        return Response({
            'message': 'Подписка успешно возобновлена',
            'subscription_status': donation.subscription_status,
            'next_payment_date': donation.next_payment_date
        })
    
    @extend_schema(
        summary="Приостановить рекуррентную подписку",
        description="Временно приостанавливает рекуррентную подписку пожертвования",
        tags=['donations']
    )
    @action(detail=True, methods=['post'])
    def pause_subscription(self, request, uuid=None):
        """Приостановка рекуррентной подписки"""
        donation = self.get_object()
        
        if not donation.is_recurring:
            return Response(
                {'error': 'Это не рекуррентное пожертвование'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем статус подписки
        if donation.subscription_status == 'paused':
            return Response(
                {'error': 'Подписка уже приостановлена'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if donation.subscription_status == 'cancelled':
            return Response(
                {'error': 'Нельзя приостановить отменённую подписку'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем права доступа
        # Проверяем по user ИЛИ по email донора (для донатов созданных без авторизации)
        has_permission = (
            request.user.is_staff or
            donation.user == request.user or
            (request.user.is_authenticated and 
             request.user.email and 
             donation.donor_email and 
             donation.donor_email.lower() == request.user.email.lower())
        )
        
        if not has_permission:
            return Response(
                {'error': 'Нет прав для управления этой подпиской'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Обновляем статус
        donation.subscription_status = 'paused'
        donation.save()
        
        return Response({
            'message': 'Подписка приостановлена',
            'subscription_status': donation.subscription_status
        })

    @extend_schema(
        summary="Скачать квитанцию",
        description="Генерирует и возвращает PDF квитанцию для пожертвования",
        tags=['donations']
    )
    @action(detail=True, methods=['get'])
    def download_receipt(self, request, uuid=None):
        """Скачивание квитанции пожертвования в PDF"""
        donation = self.get_object()
        
        # Проверяем права доступа
        # Проверяем по user ИЛИ по email донора (для донатов созданных без авторизации)
        has_permission = (
            request.user.is_staff or
            donation.user == request.user or
            (request.user.is_authenticated and 
             request.user.email and 
             donation.donor_email and 
             donation.donor_email.lower() == request.user.email.lower())
        )
        
        if not has_permission:
            return Response(
                {'error': 'Нет прав для скачивания этой квитанции'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что у платежа есть статус (не pending)
        if donation.status == 'pending':
            return Response(
                {'error': 'Квитанция будет доступна после обработки платежа'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from ..services.receipt_generator import ReceiptGeneratorService
            
            # Генерируем квитанцию
            receipt_service = ReceiptGeneratorService()
            pdf_buffer = receipt_service.generate_receipt(donation)
            filename = receipt_service.get_receipt_filename(donation)
            
            # Возвращаем PDF файл
            response = FileResponse(
                pdf_buffer,
                as_attachment=True,
                filename=filename,
                content_type='application/pdf'
            )
            
            return response
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to generate receipt for donation {donation.uuid}: {e}")
            
            return Response(
                {'error': 'Ошибка при генерации квитанции. Попробуйте позже.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    list=extend_schema(tags=['donations']),
    retrieve=extend_schema(tags=['donations']),
)
class DonationTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра транзакций пожертвований"""
    queryset = DonationTransaction.objects.all()
    serializer_class = DonationTransactionSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    # filterset_fields = ['status', 'transaction_type', 'payment_gateway']
    search_fields = ['transaction_id', 'external_transaction_id']
    ordering = ['-created_at']

    def get_queryset(self):
        """Фильтрация по пользователю для обычных пользователей"""
        if not self.request.user.is_staff:
            return self.queryset.filter(donation__user=self.request.user)
        return self.queryset














