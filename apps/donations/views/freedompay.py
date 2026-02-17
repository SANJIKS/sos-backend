import json
import logging
from decimal import Decimal
from datetime import datetime
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.common.models import AuditLog

from ..models import Donation, DonationTransaction, DonationCampaign
from ..services.freedompay import FreedomPayService, FreedomPayRecurringService, FreedomPayException
from ..serializers.freedompay import FreedomPayCreatePaymentSerializer, FreedomPayPaymentResponseSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class FreedomPayWebhookView(View):
    """Обработка webhook уведомлений от FreedomPay"""
    
    def post(self, request):
        try:
            # FreedomPay отправляет данные как multipart/form-data
            # Преобразуем списки в строки (Django QueryDict возвращает списки)
            webhook_data = {}
            for key, value in request.POST.items():
                # Берем первое значение если это список
                webhook_data[key] = value[0] if isinstance(value, list) and len(value) > 0 else value
            logger.info(f"Received FreedomPay webhook: {webhook_data}")
            
            # Инициализируем сервис
            freedompay_service = FreedomPayService()
            
            # Обрабатываем webhook
            processed_data = freedompay_service.process_webhook(webhook_data)
            
            # Находим соответствующую транзакцию
            try:
                transaction = DonationTransaction.objects.get(
                    transaction_id=processed_data['order_id']
                )
            except DonationTransaction.DoesNotExist:
                logger.error(f"Transaction not found: {processed_data['order_id']}")
                return JsonResponse({'status': 'error', 'message': 'Transaction not found'}, status=404)
            
            # Обновляем статус транзакции
            old_status = transaction.status
            
            if processed_data.get('status') == 'ok':
                transaction.status = 'success'
                transaction.donation.status = 'completed'
                
                # Парсим дату платежа
                payment_date = processed_data.get('paid_at')
                if payment_date:
                    if isinstance(payment_date, str):
                        from dateutil import parser
                        try:
                            payment_date = parser.parse(payment_date)
                        except:
                            payment_date = timezone.now()
                    if not isinstance(payment_date, datetime):
                        payment_date = timezone.now()
                else:
                    payment_date = timezone.now()
                
                transaction.donation.payment_completed_at = payment_date
                
                # Сохраняем токен карты и recurring_profile_id если это рекуррентное пожертвование
                # Для одноразовых платежей (one_time) не устанавливаем подписку
                # Проверяем что это рекуррентное пожертвование и не one_time
                is_recurring_type = (transaction.donation.is_recurring and 
                                     transaction.donation.donation_type != 'one_time' and
                                     transaction.donation.donation_type in ['monthly', 'quarterly', 'yearly'])
                
                if is_recurring_type:
                    # Сохраняем токен карты
                    card_token = processed_data.get('card_token')
                    if card_token:
                        transaction.donation.current_card_token = card_token
                        logger.info(f"Saved card_token for donation: {transaction.donation.donation_code}")
                    
                    # Сохраняем recurring_profile_id
                    recurring_profile_id = processed_data.get('recurring_profile_id')
                    if recurring_profile_id:
                        try:
                            transaction.donation.recurring_profile_id = int(recurring_profile_id)
                            logger.info(f"Saved recurring_profile_id for donation: {transaction.donation.donation_code}")
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid recurring_profile_id: {recurring_profile_id}")
                    
                    # Устанавливаем first_payment_date только если она еще не установлена
                    # (для первого успешного платежа)
                    if not transaction.donation.first_payment_date:
                        transaction.donation.first_payment_date = payment_date
                        logger.info(f"Set first_payment_date for donation: {transaction.donation.donation_code} - {payment_date}")
                    
                    # Рассчитываем дату следующего платежа от даты первого платежа
                    recurring_service = FreedomPayRecurringService()
                    next_payment_date = recurring_service._calculate_next_payment_date(transaction.donation)
                    
                    if next_payment_date:
                        transaction.donation.next_payment_date = next_payment_date
                        logger.info(f"Calculated next_payment_date: {next_payment_date} (from first_payment_date: {transaction.donation.first_payment_date})")
                    
                    # Активируем рекуррентную подписку
                    transaction.donation.recurring_active = True
                    transaction.donation.save()
                    logger.info(f"Saved card token and recurring_profile_id for recurring donation: {transaction.donation.donation_code}")
                else:
                    # Для one_time или не рекуррентных пожертвований явно отключаем подписку
                    transaction.donation.recurring_active = False
                    transaction.donation.save()
                    logger.info(f"Disabled recurring_active for one_time donation: {transaction.donation.donation_code}")
                
                # Обновляем сумму в кампании если есть
                if transaction.donation.campaign:
                    campaign = transaction.donation.campaign
                    campaign.raised_amount += transaction.amount
                    campaign.save()
                
            elif processed_data.get('status') == 'error':
                transaction.status = 'failed'
                transaction.donation.status = 'failed'
                transaction.error_message = processed_data.get('message', 'Payment failed')
                
            elif processed_data.get('status') == 'pending':
                # Обрабатываем pending статус (pg_result = 2)
                transaction.status = 'pending'
                transaction.donation.status = 'pending'
                logger.info(f"Payment pending for transaction {transaction.transaction_id}")
                # Возвращаем XML ответ для pending статуса
                xml_response = '''<?xml version="1.0" encoding="utf-8"?>
<response>
    <pg_status>ok</pg_status>
    <pg_description>Payment pending</pg_description>
    <pg_salt>{}</pg_salt>
    <pg_sig>{}</pg_sig>
</response>'''.format(
                    webhook_data.get('pg_salt', ''),
                    webhook_data.get('pg_sig', '')
                )
                return HttpResponse(xml_response, content_type='application/xml', status=200)
            
            # Обновляем данные транзакции
            transaction.external_transaction_id = processed_data.get('payment_id', '')
            
            # Преобразуем processed_data для JSON сериализации (Decimal -> str/float)
            serializable_data = {}
            for key, value in processed_data.items():
                if isinstance(value, Decimal):
                    serializable_data[key] = str(value)
                elif isinstance(value, datetime):
                    serializable_data[key] = value.isoformat()
                else:
                    serializable_data[key] = value
            
            transaction.gateway_response.update(serializable_data)
            transaction.processed_at = timezone.now()
            
            # Сохраняем изменения
            transaction.save()
            transaction.donation.save()
            
            logger.info(f"Updated transaction {transaction.transaction_id}: {old_status} -> {transaction.status}")
            
            # Отправляем уведомления если платеж успешен
            if transaction.status == 'success':
                self._send_payment_notifications(transaction)
                # Аудит-лог успешного платежа
                AuditLog.objects.create(
                    user=transaction.donation.user,
                    source=AuditLog.Source.WORKER,
                    severity=AuditLog.Severity.INFO,
                    object_type='Donation',
                    object_id=str(transaction.donation.uuid),
                    action='payment_success',
                    message='Оплата успешно подтверждена вебхуком',
                    extra={'transaction_id': transaction.transaction_id, 'amount': str(transaction.amount)}
                )
            elif transaction.status == 'failed':
                # Аудит-лог сбоя платежа
                AuditLog.objects.create(
                    user=transaction.donation.user,
                    source=AuditLog.Source.WORKER,
                    severity=AuditLog.Severity.WARNING,
                    object_type='Donation',
                    object_id=str(transaction.donation.uuid),
                    action='payment_failed',
                    message=transaction.error_message or 'Платеж неуспешен',
                    extra={'transaction_id': transaction.transaction_id}
                )
            
            # Создаем ответ согласно рабочему коду
            response_dict = freedompay_service.make_webhook_response('ok', 'Платёж принят.')
            
            # Преобразуем в XML
            xml_response = '''<?xml version="1.0" encoding="utf-8"?>
<response>
    <pg_status>{}</pg_status>
    <pg_description>{}</pg_description>
    <pg_salt>{}</pg_salt>
    <pg_sig>{}</pg_sig>
</response>'''.format(
                response_dict['pg_status'],
                response_dict['pg_description'],
                response_dict['pg_salt'],
                response_dict['pg_sig']
            )
            
            return HttpResponse(xml_response, content_type='application/xml', status=200)
            
        except FreedomPayException as e:
            logger.error(f"FreedomPay webhook error: {e}")
            # Создаем ответ для ошибки согласно рабочему коду
            freedompay_service = FreedomPayService()
            response_dict = freedompay_service.make_webhook_response('error', str(e))
            
            xml_response = '''<?xml version="1.0" encoding="utf-8"?>
<response>
    <pg_status>{}</pg_status>
    <pg_description>{}</pg_description>
    <pg_salt>{}</pg_salt>
    <pg_sig>{}</pg_sig>
</response>'''.format(
                response_dict['pg_status'],
                response_dict['pg_description'],
                response_dict['pg_salt'],
                response_dict['pg_sig']
            )
            return HttpResponse(xml_response, content_type='application/xml', status=400)
            
        except Exception as e:
            logger.error(f"Unexpected webhook error: {e}")
            # Создаем ответ для неожиданной ошибки согласно рабочему коду
            freedompay_service = FreedomPayService()
            response_dict = freedompay_service.make_webhook_response('error', 'Internal server error')
            
            xml_response = '''<?xml version="1.0" encoding="utf-8"?>
<response>
    <pg_status>{}</pg_status>
    <pg_description>{}</pg_description>
    <pg_salt>{}</pg_salt>
    <pg_sig>{}</pg_sig>
</response>'''.format(
                response_dict['pg_status'],
                response_dict['pg_description'],
                response_dict['pg_salt'],
                response_dict['pg_sig']
            )
            return HttpResponse(xml_response, content_type='application/xml', status=500)
    
    def _send_payment_notifications(self, transaction):
        """Отправка уведомлений о успешном платеже"""
        from ..tasks import send_donation_confirmation_email, sync_donation_to_salesforce
        
        try:
            # Отправляем email донору
            send_donation_confirmation_email.delay(
                donation_id=transaction.donation.id,
                transaction_id=transaction.id
            )
            
            # Синхронизируем с Salesforce
            sync_donation_to_salesforce.delay(transaction.donation.id)
            
            logger.info(f"Scheduled notifications for transaction: {transaction.transaction_id}")
            
        except Exception as e:
            logger.error(f"Failed to schedule notifications: {e}")


@api_view(['POST'])
@permission_classes([AllowAny])
def create_freedompay_payment(request):
    """Создание платежа в FreedomPay"""
    
    try:
        donation_uuid = request.data.get('donation_uuid')
        if not donation_uuid:
            return Response(
                {'error': 'donation_uuid is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Находим пожертвование
        donation = get_object_or_404(Donation, uuid=donation_uuid)
        
        # Проверяем что платеж еще не был обработан
        if donation.status in ['completed', 'processing']:
            return Response(
                {'error': 'Payment already processed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Инициализируем сервис
        service = FreedomPayService()
        
        # Проверяем, нужна ли произвольная сумма
        any_amount = request.data.get('any_amount', False)
        
        if any_amount:
            result = service.create_any_amount_payment(donation)
        elif donation.is_recurring:
            recurring_service = FreedomPayRecurringService()
            result = recurring_service.setup_recurring_payment(donation)
        else:
            result = service.create_payment(donation)
        
        if result['success']:
            # Обновляем статус пожертвования
            donation.status = 'processing'
            donation.save()
            
            return Response({
                'success': True,
                'payment_url': result.get('payment_url'),
                'order_id': result.get('order_id'),
                'message': 'Payment created successfully'
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error'),
                'message': result.get('message')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Failed to create FreedomPay payment: {e}")
        return Response(
            {'error': 'Failed to create payment'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def check_freedompay_payment(request, order_id):
    """Проверка статуса платежа FreedomPay"""
    
    try:
        service = FreedomPayService()
        result = service.check_payment_status(order_id)
        
        if result['success']:
            # Находим транзакцию и обновляем статус
            try:
                transaction = DonationTransaction.objects.get(transaction_id=order_id)
                
                # Обновляем статус если изменился
                if result['status'] != transaction.status:
                    old_status = transaction.status
                    
                    if result['status'] == 'success':
                        transaction.status = 'success'
                        transaction.donation.status = 'completed'
                        transaction.donation.payment_completed_at = result.get('paid_at')
                    elif result['status'] == 'failed':
                        transaction.status = 'failed'
                        transaction.donation.status = 'failed'
                    elif result['status'] == 'pending':
                        transaction.status = 'pending'
                        transaction.donation.status = 'processing'
                    
                    transaction.save()
                    transaction.donation.save()
                    
                    logger.info(f"Updated payment status: {order_id} {old_status} -> {transaction.status}")
                
            except DonationTransaction.DoesNotExist:
                logger.warning(f"Transaction not found for order_id: {order_id}")
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Failed to check payment status: {e}")
        return Response(
            {'error': 'Failed to check payment status'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def process_freedompay_refund(request):
    """Обработка возврата платежа FreedomPay"""
    
    try:
        payment_id = request.data.get('payment_id')
        amount = request.data.get('amount')  # Опционально для частичного возврата
        
        if not payment_id:
            return Response(
                {'error': 'payment_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Находим транзакцию
        try:
            transaction = DonationTransaction.objects.get(external_transaction_id=payment_id)
        except DonationTransaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Инициализируем сервис
        service = FreedomPayService()
        
        refund_amount = None
        if amount:
            refund_amount = Decimal(amount)
        
        result = service.refund_payment(payment_id, refund_amount)
        
        if result['success']:
            # Создаем транзакцию возврата
            refund_transaction = DonationTransaction.objects.create(
                donation=transaction.donation,
                transaction_id=f"REF_{transaction.transaction_id}_{int(timezone.now().timestamp())}",
                external_transaction_id=result.get('refund_id', ''),
                amount=refund_amount or transaction.amount,
                currency=transaction.currency,
                status='success',
                transaction_type='refund',
                payment_gateway='freedompay',
                gateway_response=result,
            )
            
            # Обновляем статус основной транзакции
            if not refund_amount or refund_amount >= transaction.amount:
                transaction.donation.status = 'refunded'
                transaction.donation.save()
            
            logger.info(f"Processed refund: {refund_transaction.transaction_id}")
            
            return Response({
                'success': True,
                'refund_id': result.get('refund_id'),
                'message': 'Refund processed successfully'
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error'),
                'message': result.get('message')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Failed to process refund: {e}")
        return Response(
            {'error': 'Failed to process refund'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_freedompay_methods(request):
    """Получение доступных способов оплаты FreedomPay"""
    
    try:
        service = FreedomPayService()
        result = service.get_payment_methods()
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Failed to get payment methods: {e}")
        return Response(
            {'error': 'Failed to get payment methods'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




@api_view(['POST'])
@permission_classes([AllowAny])
def create_unified_freedompay_payment(request):
    """
    Единый эндпоинт для создания платежей через FreedomPay
    
    Принимает:
    - amount: сумма пожертвования
    - currency: валюта (KGS, USD, EUR, RUB)
    - type: тип платежа ('one-time', 'monthly', 'yearly')
    - user_info: данные пользователя (name, email, phone) - если не авторизован
    - user_id: ID пользователя - если авторизован
    - campaign_id: ID кампании (опционально)
    - comment: комментарий донора (опционально)
    
    Возвращает:
    - success: статус операции
    - payment_url: ссылка для оплаты
    - order_id: ID заказа
    - donation_uuid: UUID созданного пожертвования
    """
    
    try:
        # Валидация данных
        serializer = FreedomPayCreatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        # Проверяем reCAPTCHA (если токен предоставлен)
        from apps.common.utils.recaptcha import verify_recaptcha, is_recaptcha_configured
        from django.utils import timezone
        
        recaptcha_token = validated_data.get('recaptcha_token')
        
        # Проверяем reCAPTCHA только если она настроена и токен предоставлен
        if is_recaptcha_configured() and recaptcha_token:
            client_ip = request.META.get('REMOTE_ADDR')
            
            recaptcha_result = verify_recaptcha(recaptcha_token, client_ip)
            if not recaptcha_result['success']:
                logger.warning(f"reCAPTCHA verification failed: {recaptcha_result.get('error')}")
                return Response({
                    'success': False,
                    'error': 'reCAPTCHA verification failed',
                    'message': recaptcha_result.get('error', 'Invalid reCAPTCHA token')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info("reCAPTCHA verification successful")
        elif is_recaptcha_configured() and not recaptcha_token:
            logger.warning("reCAPTCHA is configured but no token provided")
            return Response({
                'success': False,
                'error': 'reCAPTCHA token is required',
                'message': 'reCAPTCHA verification is required for this endpoint'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.info("reCAPTCHA verification skipped (not configured or in debug mode)")
        
        # Получаем пользователя если указан user_id
        user = None
        if validated_data.get('user_id'):
            try:
                user = User.objects.get(id=validated_data['user_id'])
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Получаем кампанию если указана
        campaign = None
        if validated_data.get('campaign_id'):
            try:
                campaign = DonationCampaign.objects.get(id=validated_data['campaign_id'])
            except DonationCampaign.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Campaign not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Определяем тип пожертвования
        donation_type = validated_data['type']
        # Для одноразовых платежей (one_time) не устанавливаем подписку
        is_recurring = donation_type in ['monthly', 'quarterly', 'yearly']
        
        # Создаем запись пожертвования в БД
        donation = Donation.objects.create(
            user=user,
            campaign=campaign,
            donor_email=validated_data['user_info']['email'],
            donor_phone=validated_data['user_info'].get('phone', ''),
            donor_full_name=validated_data['user_info']['name'],
            amount=validated_data['amount'],
            currency=validated_data['currency'],
            donation_type=donation_type,
            payment_method=Donation.PaymentMethod.BANK_CARD,
            status=Donation.DonationStatus.PENDING,
            is_recurring=is_recurring,
            donor_comment=validated_data.get('comment', ''),
            ip_address=validated_data.get('ip_address'),
            user_agent=validated_data.get('user_agent', ''),
        )
        
        logger.info(f"Created donation: {donation.donation_code} for {donation.amount} {donation.currency}")
        
        # Примечание: first_payment_date и next_payment_date будут установлены
        # в webhook обработчике после успешного платежа, чтобы использовать
        # реальную дату первого платежа как базу для расчета следующих платежей
        
        # Инициализируем FreedomPay сервис
        freedompay_service = FreedomPayService()
        
        # Создаем платеж в зависимости от типа
        if is_recurring:
            # Для рекуррентных платежей используем специальный сервис
            recurring_service = FreedomPayRecurringService()
            result = recurring_service.setup_recurring_payment(donation)
        else:
            # Для разовых платежей
            result = freedompay_service.create_payment(donation)
        
        if result['success']:
            # Обновляем статус пожертвования
            donation.status = Donation.DonationStatus.PROCESSING
            donation.save()
            
            # Аудит-лог создания платежа
            AuditLog.objects.create(
                user=user,
                source=AuditLog.Source.API,
                severity=AuditLog.Severity.INFO,
                object_type='Donation',
                object_id=str(donation.uuid),
                action='payment_created',
                message='Создан платеж через FreedomPay',
                extra={
                    'donation_code': donation.donation_code,
                    'amount': str(donation.amount),
                    'currency': donation.currency,
                    'type': donation_type,
                    'order_id': result.get('order_id')
                }
            )
            
            return Response({
                'success': True,
                'payment_url': result.get('payment_url'),
                'donation_uuid': str(donation.uuid),
            }, status=status.HTTP_201_CREATED)
        else:
            # Обновляем статус на неудачный
            donation.status = Donation.DonationStatus.FAILED
            donation.save()
            
            # Аудит-лог ошибки
            AuditLog.objects.create(
                user=user,
                source=AuditLog.Source.API,
                severity=AuditLog.Severity.ERROR,
                object_type='Donation',
                object_id=str(donation.uuid),
                action='payment_creation_failed',
                message=f"Ошибка создания платежа: {result.get('error', 'Unknown error')}",
                extra={
                    'donation_code': donation.donation_code,
                    'error': result.get('error')
                }
            )
            
            return Response({
                'success': False,
                'error': result.get('error'),
                'message': result.get('message', 'Failed to create payment'),
                'donation_uuid': str(donation.uuid)
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Failed to create unified FreedomPay payment: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'message': 'Failed to create payment'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_recaptcha_config(request):
    """
    Получение конфигурации reCAPTCHA для фронтенда
    """
    from apps.common.utils.recaptcha import get_recaptcha_site_key, is_recaptcha_configured
    
    return Response({
        'recaptcha_site_key': get_recaptcha_site_key(),
        'recaptcha_configured': is_recaptcha_configured(),
    })