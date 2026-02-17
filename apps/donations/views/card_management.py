import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View

from ..models import Donation
from ..services.card_management import CardManagementService
from ..tasks import sync_donation_to_salesforce

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_donor_card(request):
    """Обновление карты донора"""
    
    try:
        donation_uuid = request.data.get('donation_uuid')
        new_card_token = request.data.get('new_card_token')
        change_reason = request.data.get('change_reason', '')
        
        if not donation_uuid or not new_card_token:
            return Response(
                {'error': 'donation_uuid and new_card_token are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Находим пожертвование
        donation = get_object_or_404(Donation, uuid=donation_uuid)
        
        # Проверяем права доступа
        if request.user != donation.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Обновляем карту
        card_service = CardManagementService()
        result = card_service.update_donor_card(
            donation=donation,
            new_card_token=new_card_token,
            change_reason=change_reason,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        if result['success']:
            # Синхронизируем с Salesforce
            sync_donation_to_salesforce.delay(donation.id)
            
            return Response({
                'success': True,
                'message': 'Card updated successfully',
                'old_token': result['old_token'],
                'new_token': result['new_token']
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error'),
                'message': result.get('message')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Failed to update donor card: {e}")
        return Response(
            {'error': 'Failed to update card'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_card_history(request, donation_uuid):
    """Получение истории изменений карты"""
    
    try:
        # Находим пожертвование
        donation = get_object_or_404(Donation, uuid=donation_uuid)
        
        # Проверяем права доступа
        if request.user != donation.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем историю
        card_service = CardManagementService()
        history = card_service.get_card_history(donation)
        
        # Форматируем данные
        history_data = []
        for record in history:
            history_data.append({
                'change_type': record.change_type,
                'old_token': record.old_card_token,
                'new_token': record.new_card_token,
                'change_reason': record.change_reason,
                'created_at': record.created_at.isoformat(),
                'salesforce_synced': record.salesforce_synced
            })
        
        return Response({
            'success': True,
            'donation_code': donation.donation_code,
            'card_history': history_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get card history: {e}")
        return Response(
            {'error': 'Failed to get card history'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_card_token(request):
    """Валидация токена карты"""
    
    try:
        card_token = request.data.get('card_token')
        
        if not card_token:
            return Response(
                {'error': 'card_token is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Валидируем токен
        card_service = CardManagementService()
        is_valid = card_service.validate_card_token(card_token)
        
        return Response({
            'success': True,
            'is_valid': is_valid,
            'message': 'Card token is valid' if is_valid else 'Card token is invalid'
        })
        
    except Exception as e:
        logger.error(f"Failed to validate card token: {e}")
        return Response(
            {'error': 'Failed to validate card token'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
