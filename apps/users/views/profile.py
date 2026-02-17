from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.users.serializers import (
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    DonationHistorySerializer,
    UserSubscriptionsSerializer,
    UserStatsSerializer,
    ChangePasswordSerializer
)
from apps.donations.models import Donation
from apps.common.utils.pagination_page import LargeResultsSetPagination
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    tags=['users'],
    summary='Получение профиля пользователя',
    description='Получить информацию о текущем пользователе'
)
class UserProfileView(APIView):
    """Получение и обновление профиля пользователя"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        return UserProfileSerializer

    def get(self, request):
        """Получить профиль текущего пользователя"""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """Обновить профиль пользователя"""
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Возвращаем обновленный профиль
            profile_serializer = UserProfileSerializer(request.user)
            return Response(profile_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['users'],
    summary='История пожертвований',
    description='Получить историю пожертвований пользователя'
)
class UserDonationHistoryView(APIView):
    """История пожертвований пользователя"""
    
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargeResultsSetPagination

    def get(self, request):
        """Получить историю пожертвований"""
        donations = Donation.objects.filter(
            donor_email=request.user.email
        ).select_related('campaign').order_by('-created_at')

        # Фильтрация по статусу
        status_filter = request.query_params.get('status')
        if status_filter:
            donations = donations.filter(status=status_filter)

        # Фильтрация по типу пожертвования
        donation_type = request.query_params.get('type')
        if donation_type:
            donations = donations.filter(donation_type=donation_type)

        # Пагинация
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(donations, request)
        
        if page is not None:
            serializer = DonationHistorySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = DonationHistorySerializer(donations, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=['users'],
    summary='Активные подписки',
    description='Получить активные подписки пользователя'
)
class UserSubscriptionsView(APIView):
    """Активные подписки пользователя"""
    
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Получить активные подписки"""
        subscriptions = Donation.objects.filter(
            donor_email=request.user.email,
            is_recurring=True,
            recurring_active=True
        ).select_related('campaign').order_by('-created_at')

        serializer = UserSubscriptionsSerializer(subscriptions, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=['users'],
    summary='Статистика пользователя',
    description='Получить статистику пожертвований пользователя'
)
class UserStatsView(APIView):
    """Статистика пользователя"""
    
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Получить статистику пожертвований пользователя"""
        user_donations = Donation.objects.filter(
            donor_email=request.user.email,
            status='completed'
        )

        # Общая статистика
        stats = user_donations.aggregate(
            total_donated=Sum('amount'),
            donation_count=Count('id')
        )

        # Количество активных подписок
        active_subscriptions_count = Donation.objects.filter(
            donor_email=request.user.email,
            is_recurring=True,
            recurring_active=True
        ).count()

        # Даты первого и последнего пожертвования
        first_donation = user_donations.order_by('created_at').first()
        last_donation = user_donations.order_by('-created_at').first()

        # Любимая кампания (с наибольшим количеством пожертвований)
        favorite_campaign = user_donations.values('campaign__name').annotate(
            count=Count('id')
        ).order_by('-count').first()

        stats_data = {
            'total_donated': stats['total_donated'] or 0,
            'donation_count': stats['donation_count'] or 0,
            'active_subscriptions_count': active_subscriptions_count,
            'first_donation_date': first_donation.created_at if first_donation else None,
            'last_donation_date': last_donation.created_at if last_donation else None,
            'favorite_campaign': favorite_campaign['campaign__name'] if favorite_campaign else None,
        }

        serializer = UserStatsSerializer(stats_data)
        return Response(serializer.data)


@extend_schema(
    tags=['users'],
    summary='Смена пароля',
    description='Сменить пароль пользователя'
)
class ChangePasswordView(APIView):
    """Смена пароля пользователя"""
    
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Сменить пароль"""
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            # Проверяем старый пароль
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'old_password': ['Неверный пароль']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Устанавливаем новый пароль
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            
            logger.info(f"Password changed for user {user.email}")
            
            return Response({
                'message': 'Пароль успешно изменен'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['users'],
    summary='Отмена подписки',
    description='Отменить активную подписку пользователя'
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription(request, donation_uuid):
    """Отменить подписку"""
    try:
        donation = Donation.objects.get(
            uuid=donation_uuid,
            donor_email=request.user.email,
            is_recurring=True,
            recurring_active=True
        )
        
        # Отменяем подписку
        donation.recurring_active = False
        donation.cancelled_at = timezone.now()
        donation.save(update_fields=['recurring_active', 'cancelled_at'])
        
        logger.info(f"Subscription cancelled: {donation_uuid} by user {request.user.email}")
        
        return Response({
            'message': 'Подписка успешно отменена'
        })
        
    except Donation.DoesNotExist:
        return Response(
            {'error': 'Подписка не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=['users'],
    summary='Возобновление подписки',
    description='Возобновить отмененную подписку пользователя'
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reactivate_subscription(request, donation_uuid):
    """Возобновить подписку"""
    try:
        donation = Donation.objects.get(
            uuid=donation_uuid,
            donor_email=request.user.email,
            is_recurring=True,
            recurring_active=False
        )
        
        # Возобновляем подписку
        donation.recurring_active = True
        donation.cancelled_at = None
        # Устанавливаем следующую дату платежа
        if donation.donation_type == 'monthly':
            donation.next_payment_date = timezone.now() + timezone.timedelta(days=30)
        elif donation.donation_type == 'quarterly':
            donation.next_payment_date = timezone.now() + timezone.timedelta(days=90)
        elif donation.donation_type == 'yearly':
            donation.next_payment_date = timezone.now() + timezone.timedelta(days=365)
            
        donation.save(update_fields=['recurring_active', 'cancelled_at', 'next_payment_date'])
        
        logger.info(f"Subscription reactivated: {donation_uuid} by user {request.user.email}")
        
        return Response({
            'message': 'Подписка успешно возобновлена'
        })
        
    except Donation.DoesNotExist:
        return Response(
            {'error': 'Подписка не найдена'},
            status=status.HTTP_404_NOT_FOUND
        )

