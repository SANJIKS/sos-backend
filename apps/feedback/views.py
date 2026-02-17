from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from .models import Feedback, FeedbackQuestion, FeedbackSpamProtection
from .serializers import (
    FeedbackQuestionCreateSerializer, 
    FeedbackReviewCreateSerializer,
    FeedbackListSerializer,
    FeedbackQuestionSerializer,
    SpamProtectionMixin
)
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Получает IP адрес клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['GET'])
@permission_classes([AllowAny])
def get_questions(request):
    """Получить список активных вопросов для отзывов"""
    questions = FeedbackQuestion.objects.filter(is_active=True).order_by('order', 'id')
    serializer = FeedbackQuestionSerializer(questions, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_question_feedback(request):
    """Создать отзыв с вопросом"""
    try:
        # Получаем IP адрес
        ip_address = get_client_ip(request)
        
        # Проверяем защиту от спама
        spam_mixin = SpamProtectionMixin()
        spam_mixin.check_spam_protection(ip_address)
        
        # Валидируем данные
        serializer = FeedbackQuestionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Создаем отзыв
        with transaction.atomic():
            feedback = serializer.save(
                feedback_type='question',
                ip_address=ip_address,
                created_at=timezone.now()
            )
            
            # Сбрасываем счетчик попыток при успешной отправке
            try:
                spam_protection = FeedbackSpamProtection.objects.get(ip_address=ip_address)
                spam_protection.attempts_count = 0
                spam_protection.save()
            except FeedbackSpamProtection.DoesNotExist:
                pass
        
        return Response({
            'message': 'Отзыв успешно отправлен',
            'id': feedback.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Ошибка при создании отзыва с вопросом: {str(e)}")
        if isinstance(e, ValueError):
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'error': 'Произошла ошибка при отправке отзыва'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_review_feedback(request):
    """Создать отзыв-рецензию"""
    try:
        # Получаем IP адрес
        ip_address = get_client_ip(request)
        
        # Проверяем защиту от спама
        spam_mixin = SpamProtectionMixin()
        spam_mixin.check_spam_protection(ip_address)
        
        # Валидируем данные
        serializer = FeedbackReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Создаем отзыв
        with transaction.atomic():
            feedback = serializer.save(
                feedback_type='review',
                ip_address=ip_address,
                created_at=timezone.now()
            )
            
            # Сбрасываем счетчик попыток при успешной отправке
            try:
                spam_protection = FeedbackSpamProtection.objects.get(ip_address=ip_address)
                spam_protection.attempts_count = 0
                spam_protection.save()
            except FeedbackSpamProtection.DoesNotExist:
                pass
        
        return Response({
            'message': 'Отзыв успешно отправлен',
            'id': feedback.id
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Ошибка при создании отзыва-рецензии: {str(e)}")
        if isinstance(e, ValueError):
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'error': 'Произошла ошибка при отправке отзыва'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_approved_feedback(request):
    """Получить одобренные отзывы для публичного отображения"""
    feedbacks = Feedback.objects.filter(is_approved=True).order_by('-created_at')
    serializer = FeedbackListSerializer(feedbacks, many=True)
    return Response(serializer.data)
