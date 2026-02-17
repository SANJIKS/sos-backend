"""
Веб-сервисы для WS Provider интеграции с Salesforce
"""
import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from ..models import Donation, DonationTransaction, DonationCampaign
from ..serializers.ws_provider import (
    InsertWSdataSerializer,
    InsertWSdataResponseSerializer
)
from ..services.salesforce import SalesforceService, SalesforceException
from ..tasks import sync_donation_to_salesforce

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def insert_ws_data(request):
    """
    Веб-сервис InsertWSdata
    
    Регистрирует донора и пожертвование одновременно.
    Используется WS Provider для интеграции с Salesforce.
    
    Требования:
    - Order ID используется как уникальный идентификатор для каждого пожертвования
    - Для рекуррентных пожертвований: Order ID первого платежа является родительским
    - Данные донора отправляются перед пожертвованием (иерархия Salesforce)
    
    Принимает:
    {
        "donor": {
            "full_name": "Иван Иванов",
            "email": "ivan@example.com",
            "phone": "+996555123456"
        },
        "donation": {
            "amount": "1000.00",
            "currency": "KGS",
            "donation_type": "monthly",
            "payment_method": "bank_card",
            "status": "completed",
            "order_id": "DON_ABC123_1234567890",
            "transaction_id": "FP_123456",
            "payment_date": "2025-01-27T10:00:00Z",
            "is_recurring": true,
            "parent_order_id": null
        }
    }
    
    Возвращает:
    {
        "success": true,
        "message": "Donor and donation registered successfully",
        "order_id": "DON_ABC123_1234567890",
        "donation_uuid": "uuid",
        "donor_id": 123
    }
    """
    try:
        # Валидация данных
        serializer = InsertWSdataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        donor_data = validated_data['donor']
        donation_data = validated_data['donation']
        
        with transaction.atomic():
            # Шаг 1: Регистрация/поиск донора
            # Сначала создаем или находим пользователя
            user, user_created = User.objects.get_or_create(
                email=donor_data['email'].lower(),
                defaults={
                    'full_name': donor_data['full_name'],
                    'first_name': donor_data['full_name'].split()[0] if donor_data['full_name'] else '',
                    'last_name': ' '.join(donor_data['full_name'].split()[1:]) if len(donor_data['full_name'].split()) > 1 else '',
                    'phone': donor_data['phone'],
                    'user_type': User.UserType.DONOR,
                    'registration_source': 'api',
                }
            )
            
            # Обновляем данные если пользователь уже существует
            if not user_created:
                if not user.full_name or user.full_name != donor_data['full_name']:
                    user.full_name = donor_data['full_name']
                if not user.phone or user.phone != donor_data['phone']:
                    user.phone = donor_data['phone']
                user.save(update_fields=['full_name', 'phone'])
            
            # Шаг 2: Создание пожертвования
            # Определяем тип пожертвования
            donation_type = donation_data['donation_type']
            is_recurring = donation_data.get('is_recurring', False) or donation_type in ['monthly', 'quarterly', 'yearly']
            
            # Получаем кампанию если указана
            campaign = None
            if donation_data.get('campaign_id'):
                try:
                    campaign = DonationCampaign.objects.get(id=donation_data['campaign_id'])
                except DonationCampaign.DoesNotExist:
                    pass
            
            # Определяем статус пожертвования
            donation_status = donation_data.get('status', Donation.DonationStatus.PENDING)
            
            # Генерируем Order ID если не указан
            order_id = donation_data.get('order_id')
            if not order_id:
                # Генерируем уникальный Order ID
                from django.utils import timezone
                order_id = f"DON_{Donation.generate_unique_code()}_{int(timezone.now().timestamp())}"
            
            # Проверяем parent_order_id для рекуррентных платежей
            parent_order_id = donation_data.get('parent_order_id')
            parent_donation = None
            
            if is_recurring and parent_order_id:
                # Ищем родительское пожертвование по parent_order_id
                try:
                    parent_transaction = DonationTransaction.objects.get(transaction_id=parent_order_id)
                    parent_donation = parent_transaction.donation
                except DonationTransaction.DoesNotExist:
                    logger.warning(f"Parent donation not found for order_id: {parent_order_id}")
            
            # Создаем пожертвование
            donation = Donation.objects.create(
                user=user,
                campaign=campaign,
                donor_email=donor_data['email'].lower(),
                donor_phone=donor_data['phone'],
                donor_full_name=donor_data['full_name'],
                amount=donation_data['amount'],
                currency=donation_data['currency'],
                donation_type=donation_type,
                payment_method=donation_data['payment_method'],
                status=donation_status,
                donor_source=donation_data.get('donor_source', Donation.DonorSource.ONLINE),
                is_recurring=is_recurring,
                parent_donation=parent_donation,
                parent_order_id=parent_order_id,
                donor_comment=donation_data.get('donor_comment', ''),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            
            # Если это первый платеж в рекуррентной подписке, сохраняем order_id как parent_order_id
            if is_recurring and not parent_order_id:
                donation.parent_order_id = order_id
                donation.save(update_fields=['parent_order_id'])
            
            # Шаг 3: Создание транзакции
            transaction_status = 'success' if donation_status == 'completed' else 'pending'
            if donation_status == 'failed':
                transaction_status = 'failed'
            
            donation_transaction = DonationTransaction.objects.create(
                donation=donation,
                transaction_id=order_id,
                external_transaction_id=donation_data.get('transaction_id', ''),
                amount=donation_data['amount'],
                currency=donation_data['currency'],
                status=transaction_status,
                transaction_type='payment',
                payment_gateway='freedompay',
                gateway_response={
                    'ws_provider': True,
                    'payment_date': donation_data.get('payment_date'),
                    'transaction_id': donation_data.get('transaction_id'),
                },
            )
            
            # Устанавливаем дату платежа если указана
            if donation_data.get('payment_date'):
                donation.payment_completed_at = donation_data['payment_date']
                donation.save(update_fields=['payment_completed_at'])
            
            # Шаг 4: Синхронизация с Salesforce
            # Сначала синхронизируем донора, затем пожертвование
            try:
                sf_service = SalesforceService()
                
                # Синхронизируем донора
                donor_sf_data = {
                    'donor_full_name': donor_data['full_name'],
                    'donor_email': donor_data['email'],
                    'donor_phone': donor_data['phone'],
                    'donor_source': donation_data.get('donor_source', 'Online'),
                }
                donor_result = sf_service.sync_donor_to_salesforce(donor_sf_data)
                
                # Синхронизируем пожертвование
                donation_sf_data = {
                    'donation_code': donation.donation_code,
                    'order_id': order_id,  # Передаем Order ID в Salesforce
                    'donor_full_name': donor_data['full_name'],
                    'donor_email': donor_data['email'],
                    'donor_phone': donor_data['phone'],
                    'amount': donation_data['amount'],
                    'currency': donation_data['currency'],
                    'donation_type': donation_type,
                    'payment_method': donation_data['payment_method'],
                    'donor_comment': donation_data.get('donor_comment', ''),
                    'status': donation_status,
                    'donor_source': donation_data.get('donor_source', 'Online'),
                    'created_at': donation.created_at,
                    'campaign_title': campaign.name if campaign else None,
                    'salesforce_campaign_id': campaign.salesforce_id if campaign else None,
                    'is_recurring': is_recurring,
                    'parent_order_id': parent_order_id,
                }
                
                # Синхронизируем пожертвование
                sync_result = sf_service.sync_donation_to_salesforce(donation_sf_data)
                
                if sync_result.get('success'):
                    donation.salesforce_id = sync_result.get('opportunity_id')
                    donation.salesforce_synced = True
                    donation.save(update_fields=['salesforce_id', 'salesforce_synced'])
                    logger.info(f"Successfully synced donation {donation.donation_code} to Salesforce via InsertWSdata")
                else:
                    donation.salesforce_sync_error = sync_result.get('message', 'Unknown error')
                    donation.save(update_fields=['salesforce_sync_error'])
                    logger.warning(f"Failed to sync donation {donation.donation_code} to Salesforce: {sync_result.get('message')}")
                    
            except SalesforceException as e:
                logger.error(f"Salesforce sync error for InsertWSdata: {e}")
                donation.salesforce_sync_error = str(e)
                donation.save(update_fields=['salesforce_sync_error'])
            except Exception as e:
                logger.error(f"Unexpected error during Salesforce sync in InsertWSdata: {e}")
                # Не прерываем процесс, только логируем ошибку
            
            # Возвращаем успешный ответ
            response_data = {
                'success': True,
                'message': 'Donor and donation registered successfully',
                'order_id': order_id,
                'donation_uuid': str(donation.uuid),
                'donor_id': user.id,
            }
            
            response_serializer = InsertWSdataResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"InsertWSdata error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def cancel_donation_ws(request, donation_uuid):
    """
    Отмена пожертвования через WS Dashboard
    
    При отмене немедленно уведомляет Salesforce и изменяет статус на "Closed".
    
    Принимает:
    {
        "reason": "Donor requested cancellation" (опционально)
    }
    
    Возвращает:
    {
        "success": true,
        "message": "Donation cancelled successfully",
        "order_id": "DON_ABC123_1234567890",
        "salesforce_updated": true
    }
    """
    try:
        from django.shortcuts import get_object_or_404
        from ..services.salesforce import SalesforceService
        
        # Находим пожертвование
        donation = get_object_or_404(Donation, uuid=donation_uuid)
        
        # Проверяем, что пожертвование можно отменить
        if donation.status in ['cancelled', 'refunded']:
            return Response({
                'success': False,
                'error': f'Donation already {donation.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', 'Cancelled via WS Dashboard')
        
        with transaction.atomic():
            # Отменяем пожертвование
            if donation.is_recurring:
                donation.recurring_active = False
                donation.subscription_status = Donation.SubscriptionStatus.CANCELLED
                donation.save(update_fields=['recurring_active', 'subscription_status'])
            
            donation.status = Donation.DonationStatus.CANCELLED
            donation.admin_notes = f"{donation.admin_notes}\n\nCancelled via WS Dashboard: {reason}".strip()
            donation.save(update_fields=['status', 'admin_notes'])
            
            # Немедленно уведомляем Salesforce
            salesforce_updated = False
            if donation.salesforce_synced and donation.salesforce_id:
                try:
                    sf_service = SalesforceService()
                    # Обновляем статус в Salesforce на "Closed Lost"
                    result = sf_service.update_opportunity_status(donation.salesforce_id, 'cancelled')
                    if result.get('success'):
                        salesforce_updated = True
                        logger.info(f"Successfully updated Salesforce opportunity {donation.salesforce_id} to cancelled")
                    else:
                        logger.warning(f"Failed to update Salesforce opportunity: {result.get('message')}")
                except Exception as e:
                    logger.error(f"Error updating Salesforce for cancellation: {e}")
            
            # Логируем отмену
            logger.info(f"Donation {donation.donation_code} cancelled via WS Dashboard. Reason: {reason}")
            
            return Response({
                'success': True,
                'message': 'Donation cancelled successfully',
                'order_id': donation.parent_order_id or donation.transactions.first().transaction_id if donation.transactions.exists() else None,
                'donation_uuid': str(donation.uuid),
                'salesforce_updated': salesforce_updated
            }, status=status.HTTP_200_OK)
            
    except Donation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Donation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Cancel donation WS error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def close_donation_ws(request, donation_uuid):
    """
    Ручное закрытие пожертвования через WS Dashboard
    
    Когда ответственный MA человек вручную закрывает пожертвование,
    WS немедленно уведомляет Salesforce и изменяет статус на "Closed".
    
    Принимает:
    {
        "close_reason": "Completed successfully" (опционально),
        "close_date": "2025-01-27T10:00:00Z" (опционально)
    }
    
    Возвращает:
    {
        "success": true,
        "message": "Donation closed successfully",
        "order_id": "DON_ABC123_1234567890",
        "salesforce_updated": true
    }
    """
    try:
        from django.shortcuts import get_object_or_404
        from ..services.salesforce import SalesforceService
        from datetime import datetime
        
        # Находим пожертвование
        donation = get_object_or_404(Donation, uuid=donation_uuid)
        
        # Проверяем, что пожертвование можно закрыть
        if donation.status in ['cancelled', 'refunded']:
            return Response({
                'success': False,
                'error': f'Cannot close donation with status {donation.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        close_reason = request.data.get('close_reason', 'Closed manually via WS Dashboard')
        close_date_str = request.data.get('close_date')
        
        with transaction.atomic():
            # Закрываем пожертвование
            donation.status = Donation.DonationStatus.COMPLETED
            if close_date_str:
                try:
                    close_date = datetime.fromisoformat(close_date_str.replace('Z', '+00:00'))
                    donation.payment_completed_at = close_date
                except:
                    donation.payment_completed_at = timezone.now()
            else:
                donation.payment_completed_at = timezone.now()
            
            donation.admin_notes = f"{donation.admin_notes}\n\nClosed via WS Dashboard: {close_reason}".strip()
            donation.save(update_fields=['status', 'payment_completed_at', 'admin_notes'])
            
            # Немедленно уведомляем Salesforce
            salesforce_updated = False
            if donation.salesforce_synced and donation.salesforce_id:
                try:
                    sf_service = SalesforceService()
                    # Обновляем статус в Salesforce на "Closed Won"
                    result = sf_service.update_opportunity_status(donation.salesforce_id, 'completed')
                    if result.get('success'):
                        salesforce_updated = True
                        logger.info(f"Successfully updated Salesforce opportunity {donation.salesforce_id} to closed")
                    else:
                        logger.warning(f"Failed to update Salesforce opportunity: {result.get('message')}")
                except Exception as e:
                    logger.error(f"Error updating Salesforce for closure: {e}")
            else:
                # Если еще не синхронизировано, синхронизируем
                try:
                    from ..tasks import sync_donation_to_salesforce
                    sync_donation_to_salesforce.delay(donation.id)
                    logger.info(f"Queued donation {donation.donation_code} for Salesforce sync")
                except Exception as e:
                    logger.error(f"Error queueing Salesforce sync: {e}")
            
            # Логируем закрытие
            logger.info(f"Donation {donation.donation_code} closed via WS Dashboard. Reason: {close_reason}")
            
            return Response({
                'success': True,
                'message': 'Donation closed successfully',
                'order_id': donation.parent_order_id or donation.transactions.first().transaction_id if donation.transactions.exists() else None,
                'donation_uuid': str(donation.uuid),
                'salesforce_updated': salesforce_updated
            }, status=status.HTTP_200_OK)
            
    except Donation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Donation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Close donation WS error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_recurring_donation_ws(request, donation_uuid):
    """
    Изменение суммы или карты для рекуррентного пожертвования через WS Dashboard
    
    Если банк не поддерживает изменение параметров активной подписки,
    создается новое пожертвование, а старое автоматически закрывается.
    
    Принимает:
    {
        "new_amount": "2000.00" (опционально),
        "new_card_token": "token123" (опционально),
        "reason": "Donor requested amount change" (опционально)
    }
    
    Возвращает:
    {
        "success": true,
        "message": "Recurring donation updated successfully",
        "old_donation_uuid": "uuid",
        "new_donation_uuid": "uuid",
        "old_order_id": "DON_ABC123",
        "new_order_id": "DON_XYZ789"
    }
    """
    try:
        from django.shortcuts import get_object_or_404
        from ..services.salesforce import SalesforceService
        from decimal import Decimal
        
        # Находим пожертвование
        old_donation = get_object_or_404(Donation, uuid=donation_uuid)
        
        # Проверяем, что это рекуррентное пожертвование
        if not old_donation.is_recurring:
            return Response({
                'success': False,
                'error': 'This is not a recurring donation'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что пожертвование активно
        if not old_donation.recurring_active or old_donation.status == 'cancelled':
            return Response({
                'success': False,
                'error': 'Recurring donation is not active'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        new_amount = request.data.get('new_amount')
        new_card_token = request.data.get('new_card_token')
        reason = request.data.get('reason', 'Updated via WS Dashboard')
        
        # Проверяем, что есть что изменять
        if not new_amount and not new_card_token:
            return Response({
                'success': False,
                'error': 'Either new_amount or new_card_token must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем сумму
        if new_amount:
            try:
                new_amount = Decimal(str(new_amount))
                if new_amount <= 0:
                    return Response({
                        'success': False,
                        'error': 'Amount must be greater than 0'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'Invalid amount format'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Создаем новое пожертвование с новыми параметрами
            new_donation = Donation.objects.create(
                user=old_donation.user,
                campaign=old_donation.campaign,
                donor_email=old_donation.donor_email,
                donor_phone=old_donation.donor_phone,
                donor_full_name=old_donation.donor_full_name,
                amount=new_amount if new_amount else old_donation.amount,
                currency=old_donation.currency,
                donation_type=old_donation.donation_type,
                payment_method=old_donation.payment_method,
                status=Donation.DonationStatus.PENDING,
                donor_source=old_donation.donor_source,
                is_recurring=True,
                parent_donation=None,  # Новое родительское пожертвование
                parent_order_id=None,  # Будет установлен при первом платеже
                current_card_token=new_card_token if new_card_token else old_donation.current_card_token,
                recurring_profile_id=old_donation.recurring_profile_id if not new_card_token else None,
                donor_comment=f"Updated from {old_donation.donation_code}: {reason}",
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            
            # Генерируем новый Order ID для нового пожертвования
            from django.utils import timezone
            new_order_id = f"DON_{new_donation.donation_code}_{int(timezone.now().timestamp())}"
            new_donation.parent_order_id = new_order_id
            new_donation.save(update_fields=['parent_order_id'])
            
            # Закрываем старое пожертвование
            old_donation.recurring_active = False
            old_donation.subscription_status = Donation.SubscriptionStatus.CANCELLED
            old_donation.status = Donation.DonationStatus.CANCELLED
            old_donation.admin_notes = f"{old_donation.admin_notes}\n\nCancelled due to update: {reason}. New donation: {new_donation.donation_code}".strip()
            old_donation.save(update_fields=['recurring_active', 'subscription_status', 'status', 'admin_notes'])
            
            # Уведомляем Salesforce о закрытии старого пожертвования
            if old_donation.salesforce_synced and old_donation.salesforce_id:
                try:
                    sf_service = SalesforceService()
                    result = sf_service.update_opportunity_status(old_donation.salesforce_id, 'cancelled')
                    if result.get('success'):
                        logger.info(f"Successfully closed old donation {old_donation.donation_code} in Salesforce")
                except Exception as e:
                    logger.error(f"Error closing old donation in Salesforce: {e}")
            
            # Синхронизируем новое пожертвование с Salesforce
            try:
                sf_service = SalesforceService()
                
                # Синхронизируем донора
                donor_sf_data = {
                    'donor_full_name': new_donation.donor_full_name,
                    'donor_email': new_donation.donor_email,
                    'donor_phone': new_donation.donor_phone,
                    'donor_source': new_donation.donor_source,
                }
                donor_result = sf_service.sync_donor_to_salesforce(donor_sf_data)
                
                # Синхронизируем новое пожертвование
                donation_sf_data = {
                    'donation_code': new_donation.donation_code,
                    'order_id': new_order_id,
                    'donor_full_name': new_donation.donor_full_name,
                    'donor_email': new_donation.donor_email,
                    'donor_phone': new_donation.donor_phone,
                    'amount': new_donation.amount,
                    'currency': new_donation.currency,
                    'donation_type': new_donation.donation_type,
                    'payment_method': new_donation.payment_method,
                    'donor_comment': new_donation.donor_comment,
                    'status': new_donation.status,
                    'donor_source': new_donation.donor_source,
                    'created_at': new_donation.created_at,
                    'campaign_title': new_donation.campaign.name if new_donation.campaign else None,
                    'salesforce_campaign_id': new_donation.campaign.salesforce_id if new_donation.campaign else None,
                    'is_recurring': True,
                    'parent_order_id': None,
                }
                
                sync_result = sf_service.sync_donation_to_salesforce(donation_sf_data)
                
                if sync_result.get('success'):
                    new_donation.salesforce_id = sync_result.get('opportunity_id')
                    new_donation.salesforce_synced = True
                    new_donation.save(update_fields=['salesforce_id', 'salesforce_synced'])
                    logger.info(f"Successfully synced new donation {new_donation.donation_code} to Salesforce")
            except Exception as e:
                logger.error(f"Error syncing new donation to Salesforce: {e}")
            
            # Получаем Order ID старого пожертвования
            old_order_id = old_donation.parent_order_id
            if not old_order_id and old_donation.transactions.exists():
                old_order_id = old_donation.transactions.first().transaction_id
            
            logger.info(f"Updated recurring donation: {old_donation.donation_code} -> {new_donation.donation_code}")
            
            return Response({
                'success': True,
                'message': 'Recurring donation updated successfully',
                'old_donation_uuid': str(old_donation.uuid),
                'new_donation_uuid': str(new_donation.uuid),
                'old_order_id': old_order_id,
                'new_order_id': new_order_id,
            }, status=status.HTTP_200_OK)
            
    except Donation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Donation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Update recurring donation WS error: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
