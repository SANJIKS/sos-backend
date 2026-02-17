import logging
from celery import shared_task
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.core.cache import cache

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_donation_confirmation_email(self, donation_id, transaction_id=None):
    """Отправка email подтверждения пожертвования"""
    
    try:
        from .models import Donation, DonationTransaction
        
        donation = Donation.objects.get(id=donation_id)
        transaction = None
        
        if transaction_id:
            try:
                transaction = DonationTransaction.objects.get(id=transaction_id)
            except DonationTransaction.DoesNotExist:
                logger.warning(f"Transaction {transaction_id} not found")
        
        # Подготавливаем контекст для шаблона
        context = {
            'donation': donation,
            'transaction': transaction,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        # Рендерим шаблоны email
        subject = f"Спасибо за пожертвование! Код: {donation.donation_code}"
        
        html_message = render_to_string('emails/donation_confirmation.html', context)
        text_message = render_to_string('emails/donation_confirmation.txt', context)
        
        # Отправляем email
        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[donation.donor_email],
            fail_silently=False,
        )
        
        logger.info(f"Sent donation confirmation email for: {donation.donation_code}")
        
        return f"Email sent successfully to {donation.donor_email}"
        
    except Exception as e:
        logger.error(f"Failed to send donation confirmation email: {e}")
        
        # Повторяем задачу с экспоненциальной задержкой
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries * 60  # 1, 2, 4 минуты
            self.retry(countdown=retry_delay, exc=e)
        
        raise e


@shared_task(bind=True, max_retries=3)
def sync_donation_to_salesforce(self, donation_id):
    """Синхронизация пожертвования с Salesforce"""
    
    try:
        from .models import Donation
        # from .services.salesforce import SalesforceService  # TODO: создать сервис
        
        donation = Donation.objects.get(id=donation_id)
        
        # TODO: Реализовать синхронизацию с Salesforce
        # salesforce_service = SalesforceService()
        # result = salesforce_service.sync_donation(donation)
        
        # Временно помечаем как синхронизированное
        donation.salesforce_synced = True
        donation.salesforce_id = f"SF_{donation.donation_code}"  # Временный ID
        donation.save()
        
        logger.info(f"Synced donation to Salesforce: {donation.donation_code}")
        
        return f"Donation {donation.donation_code} synced successfully"
        
    except Exception as e:
        logger.error(f"Failed to sync donation to Salesforce: {e}")
        
        # Обновляем ошибку синхронизации
        try:
            donation = Donation.objects.get(id=donation_id)
            donation.salesforce_sync_error = str(e)
            donation.save()
        except:
            pass
        
        # Повторяем задачу
        if self.request.retries < self.max_retries:
            retry_delay = 2 ** self.request.retries * 300  # 5, 10, 20 минут
            self.retry(countdown=retry_delay, exc=e)
        
        raise e


@shared_task
def process_recurring_payments():
    """Обработка рекуррентных платежей"""
    
    try:
        from .models import Donation
        from .services.freedompay import FreedomPayRecurringService
        
        # Находим пожертвования готовые к рекуррентному платежу
        now = timezone.now()
        
        recurring_donations = Donation.objects.filter(
            is_recurring=True,
            recurring_active=True,
            next_payment_date__lte=now,
            status='completed'  # Только успешные первоначальные платежи
        )
        
        service = FreedomPayRecurringService()
        processed_count = 0
        
        for donation in recurring_donations:
            try:
                # Проверяем наличие токена карты или recurring_profile_id
                card_token = donation.current_card_token
                recurring_profile_id = donation.recurring_profile_id
                
                if not card_token and not recurring_profile_id:
                    # Пытаемся получить из первоначальной транзакции (для обратной совместимости)
                    initial_transaction = donation.transactions.filter(
                        status='success',
                        transaction_type='payment'
                    ).first()
                    
                    if initial_transaction:
                        gateway_response = initial_transaction.gateway_response or {}
                        card_token = gateway_response.get('card_token') or gateway_response.get('pg_card_token')
                        recurring_profile_id = gateway_response.get('recurring_profile_id') or gateway_response.get('pg_recurring_profile_id')
                        
                        # Сохраняем токен и профиль в модели для будущего использования
                        if card_token:
                            donation.current_card_token = card_token
                        if recurring_profile_id:
                            try:
                                donation.recurring_profile_id = int(recurring_profile_id)
                            except (ValueError, TypeError):
                                pass
                        donation.save()
                
                if not card_token and not recurring_profile_id:
                    logger.warning(f"No card token or recurring_profile_id for donation: {donation.donation_code}")
                    continue
                
                # Создаем дочернее пожертвование для рекуррентного платежа
                child_donation = Donation.objects.create(
                    user=donation.user,
                    campaign=donation.campaign,
                    donor_email=donation.donor_email,
                    donor_phone=donation.donor_phone,
                    donor_full_name=donation.donor_full_name,
                    amount=donation.amount,
                    currency=donation.currency,
                    donation_type=donation.donation_type,
                    payment_method=donation.payment_method,
                    status='processing',
                    donor_source=donation.donor_source,
                    is_recurring=False,  # Дочерний платеж не рекуррентный
                    parent_donation=donation,
                    donor_comment=f"Рекуррентный платеж от {donation.donation_code}",
                    f2f_coordinator=donation.f2f_coordinator,
                    f2f_location=donation.f2f_location,
                    # Наследуем токен, профиль и дату первого платежа от родительского пожертвования
                    current_card_token=donation.current_card_token,
                    recurring_profile_id=donation.recurring_profile_id,
                    first_payment_date=donation.first_payment_date,  # Наследуем дату первого платежа
                )
                
                # Обрабатываем платеж (card_token опционален, если есть recurring_profile_id)
                result = service.process_recurring_payment(child_donation, card_token)
                
                if result['success']:
                    processed_count += 1
                    logger.info(f"Processed recurring payment: {child_donation.donation_code}")
                else:
                    logger.error(f"Failed to process recurring payment: {result.get('message')}")
                    child_donation.status = 'failed'
                    child_donation.save()
                
            except Exception as e:
                logger.error(f"Error processing recurring donation {donation.donation_code}: {e}")
                continue
        
        logger.info(f"Processed {processed_count} recurring payments")
        
        return f"Processed {processed_count} recurring payments"
        
    except Exception as e:
        logger.error(f"Failed to process recurring payments: {e}")
        raise e


@shared_task
def cleanup_failed_transactions():
    """Очистка неудачных транзакций старше 7 дней"""
    
    try:
        from .models import DonationTransaction
        
        cutoff_date = timezone.now() - timedelta(days=7)
        
        failed_transactions = DonationTransaction.objects.filter(
            status='failed',
            created_at__lt=cutoff_date
        )
        
        count = failed_transactions.count()
        failed_transactions.delete()
        
        logger.info(f"Cleaned up {count} failed transactions")
        
        return f"Cleaned up {count} failed transactions"
        
    except Exception as e:
        logger.error(f"Failed to cleanup transactions: {e}")
        raise e


@shared_task
def send_payment_reminder_emails():
    """Отправка напоминаний о неоплаченных пожертвованиях"""
    
    try:
        from .models import Donation
        
        # Находим пожертвования в статусе pending старше 1 часа
        cutoff_time = timezone.now() - timedelta(hours=1)
        
        pending_donations = Donation.objects.filter(
            status='pending',
            created_at__lt=cutoff_time,
            created_at__gt=timezone.now() - timedelta(days=1)  # Не старше 1 дня
        )
        
        sent_count = 0
        
        for donation in pending_donations:
            try:
                # Проверяем что напоминание еще не отправлялось
                cache_key = f"payment_reminder_sent_{donation.uuid}"
                if cache.get(cache_key):
                    continue
                
                # Отправляем напоминание
                subject = f"Завершите пожертвование - Код: {donation.donation_code}"
                
                context = {
                    'donation': donation,
                    'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                }
                
                html_message = render_to_string('emails/payment_reminder.html', context)
                text_message = render_to_string('emails/payment_reminder.txt', context)
                
                send_mail(
                    subject=subject,
                    message=text_message,
                    html_message=html_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[donation.donor_email],
                    fail_silently=False,
                )
                
                # Помечаем что напоминание отправлено
                cache.set(cache_key, True, timeout=86400)  # 24 часа
                sent_count += 1
                
                logger.info(f"Sent payment reminder for: {donation.donation_code}")
                
            except Exception as e:
                logger.error(f"Failed to send payment reminder for {donation.donation_code}: {e}")
                continue
        
        logger.info(f"Sent {sent_count} payment reminder emails")
        
        return f"Sent {sent_count} payment reminder emails"
        
    except Exception as e:
        logger.error(f"Failed to send payment reminders: {e}")
        raise e


@shared_task
def update_campaign_statistics():
    """Обновление статистики кампаний"""
    
    try:
        from .models import DonationCampaign
        from django.db.models import Sum
        
        campaigns = DonationCampaign.objects.all()
        updated_count = 0
        
        for campaign in campaigns:
            # Пересчитываем собранную сумму
            raised_amount = campaign.donation_set.filter(
                status='completed'
            ).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            if campaign.raised_amount != raised_amount:
                campaign.raised_amount = raised_amount
                campaign.save()
                updated_count += 1
        
        logger.info(f"Updated {updated_count} campaign statistics")
        
        return f"Updated {updated_count} campaign statistics"
        
    except Exception as e:
        logger.error(f"Failed to update campaign statistics: {e}")
        raise e


# ==================== SALESFORCE TASKS ====================

@shared_task(bind=True, max_retries=3)
def sync_donation_to_salesforce(self, donation_id):
    """Синхронизация пожертвования с Salesforce"""
    
    try:
        from .models import Donation
        from .services.salesforce import SalesforceService, SalesforceException
        
        donation = Donation.objects.get(id=donation_id)
        
        # Проверяем, что еще не синхронизировано
        if donation.salesforce_synced:
            logger.info(f"Donation {donation.donation_code} already synced to Salesforce")
            return f"Donation {donation.donation_code} already synced"
        
        # Подготавливаем данные для Salesforce
        donation_data = {
            'donation_code': donation.donation_code,
            'donor_full_name': donation.donor_full_name,
            'donor_email': donation.donor_email,
            'donor_phone': donation.donor_phone,
            'amount': donation.amount,
            'currency': donation.currency,
            'donation_type': donation.donation_type,
            'payment_method': donation.payment_method,
            'donor_comment': donation.donor_comment,
            'status': donation.status,
            'donor_source': donation.donor_source,
            'created_at': donation.created_at,
            'campaign_title': donation.campaign.name if donation.campaign else None,
            'salesforce_campaign_id': donation.campaign.salesforce_id if donation.campaign else None,
        }
        
        # Синхронизируем с Salesforce
        sf_service = SalesforceService()
        result = sf_service.sync_donation_to_salesforce(donation_data)
        
        if result.get('success'):
            # Обновляем запись о синхронизации
            donation.salesforce_id = result.get('opportunity_id')
            donation.salesforce_synced = True
            donation.salesforce_sync_error = ''
            donation.save()
            
            logger.info(f"Successfully synced donation {donation.donation_code} to Salesforce")
            return f"Synced donation {donation.donation_code} to Salesforce"
        else:
            raise SalesforceException(f"Sync failed: {result.get('message', 'Unknown error')}")
        
    except Donation.DoesNotExist:
        logger.error(f"Donation with ID {donation_id} not found")
        raise
        
    except SalesforceException as e:
        # Записываем ошибку в базу
        try:
            donation = Donation.objects.get(id=donation_id)
            donation.salesforce_sync_error = str(e)
            donation.save()
        except:
            pass
        
        logger.error(f"Salesforce sync failed for donation {donation_id}: {e}")
        
        # Retry with exponential backoff
        raise self.retry(
            countdown=60 * (2 ** self.request.retries),
            exc=e
        )
        
    except Exception as e:
        logger.error(f"Unexpected error syncing donation {donation_id}: {e}")
        raise self.retry(
            countdown=60 * (2 ** self.request.retries),
            exc=e
        )


@shared_task(bind=True, max_retries=3)
def sync_campaign_to_salesforce(self, campaign_id):
    """Синхронизация кампании с Salesforce"""
    
    try:
        from .models import DonationCampaign
        from .services.salesforce import SalesforceService, SalesforceException
        
        campaign = DonationCampaign.objects.get(id=campaign_id)
        
        # Проверяем, что еще не синхронизировано
        if campaign.salesforce_synced:
            logger.info(f"Campaign {campaign.name} already synced to Salesforce")
            return f"Campaign {campaign.name} already synced"
        
        # Подготавливаем данные для Salesforce
        campaign_data = {
            'title': campaign.name,
            'description': campaign.description,
            'target_amount': campaign.goal_amount,
            'start_date': campaign.start_date.date().isoformat(),
            'end_date': campaign.end_date.date().isoformat() if campaign.end_date else None,
            'is_active': campaign.status == 'active',
        }
        
        # Синхронизируем с Salesforce
        sf_service = SalesforceService()
        result = sf_service.create_campaign(campaign_data)
        
        if result.get('success'):
            # Обновляем запись о синхронизации
            campaign.salesforce_id = result.get('id')
            campaign.salesforce_synced = True
            campaign.salesforce_sync_error = ''
            campaign.save()
            
            logger.info(f"Successfully synced campaign {campaign.name} to Salesforce")
            return f"Synced campaign {campaign.name} to Salesforce"
        else:
            raise SalesforceException(f"Sync failed: {result.get('message', 'Unknown error')}")
        
    except DonationCampaign.DoesNotExist:
        logger.error(f"Campaign with ID {campaign_id} not found")
        raise
        
    except SalesforceException as e:
        # Записываем ошибку в базу
        try:
            campaign = DonationCampaign.objects.get(id=campaign_id)
            campaign.salesforce_sync_error = str(e)
            campaign.save()
        except:
            pass
        
        logger.error(f"Salesforce sync failed for campaign {campaign_id}: {e}")
        
        # Retry with exponential backoff
        raise self.retry(
            countdown=60 * (2 ** self.request.retries),
            exc=e
        )
        
    except Exception as e:
        logger.error(f"Unexpected error syncing campaign {campaign_id}: {e}")
        raise self.retry(
            countdown=60 * (2 ** self.request.retries),
            exc=e
        )


@shared_task(bind=True, max_retries=3)
def update_salesforce_opportunity_status(self, donation_id, new_status):
    """Обновление статуса opportunity в Salesforce при изменении статуса пожертвования"""
    
    try:
        from .models import Donation
        from .services.salesforce import SalesforceService, SalesforceException
        
        donation = Donation.objects.get(id=donation_id)
        
        # Проверяем, что donation синхронизирован с Salesforce
        if not donation.salesforce_synced or not donation.salesforce_id:
            logger.warning(f"Donation {donation.donation_code} not synced to Salesforce, skipping status update")
            return f"Donation {donation.donation_code} not synced to Salesforce"
        
        # Обновляем статус в Salesforce
        sf_service = SalesforceService()
        result = sf_service.update_opportunity_status(donation.salesforce_id, new_status)
        
        if result.get('success'):
            logger.info(f"Successfully updated Salesforce opportunity {donation.salesforce_id} status to {new_status}")
            return f"Updated Salesforce opportunity status to {new_status}"
        else:
            raise SalesforceException(f"Status update failed: {result.get('message', 'Unknown error')}")
        
    except Donation.DoesNotExist:
        logger.error(f"Donation with ID {donation_id} not found")
        raise
        
    except SalesforceException as e:
        logger.error(f"Salesforce status update failed for donation {donation_id}: {e}")
        
        # Retry with exponential backoff
        raise self.retry(
            countdown=60 * (2 ** self.request.retries),
            exc=e
        )
        
    except Exception as e:
        logger.error(f"Unexpected error updating Salesforce status for donation {donation_id}: {e}")
        raise self.retry(
            countdown=60 * (2 ** self.request.retries),
            exc=e
        )


@shared_task
def bulk_sync_donations_to_salesforce(limit=50):
    """Массовая синхронизация несинхронизированных пожертвований с Salesforce"""
    
    try:
        from .models import Donation
        
        # Получаем несинхронизированные пожертвования
        unsynced_donations = Donation.objects.filter(
            salesforce_synced=False,
            status__in=['completed', 'processing']  # Синхронизируем только завершенные или обрабатываемые
        )[:limit]
        
        sync_count = 0
        for donation in unsynced_donations:
            try:
                # Запускаем задачу синхронизации для каждого пожертвования
                sync_donation_to_salesforce.delay(donation.id)
                sync_count += 1
            except Exception as e:
                logger.error(f"Failed to queue sync for donation {donation.id}: {e}")
                continue
        
        logger.info(f"Queued {sync_count} donations for Salesforce sync")
        return f"Queued {sync_count} donations for sync"
        
    except Exception as e:
        logger.error(f"Failed to bulk sync donations: {e}")
        raise e


@shared_task
def bulk_sync_campaigns_to_salesforce():
    """Массовая синхронизация несинхронизированных кампаний с Salesforce"""
    
    try:
        from .models import DonationCampaign
        
        # Получаем несинхронизированные кампании
        unsynced_campaigns = DonationCampaign.objects.filter(
            salesforce_synced=False,
            status__in=['active', 'completed']  # Синхронизируем только активные или завершенные
        )
        
        sync_count = 0
        for campaign in unsynced_campaigns:
            try:
                # Запускаем задачу синхронизации для каждой кампании
                sync_campaign_to_salesforce.delay(campaign.id)
                sync_count += 1
            except Exception as e:
                logger.error(f"Failed to queue sync for campaign {campaign.id}: {e}")
                continue
        
        logger.info(f"Queued {sync_count} campaigns for Salesforce sync")
        return f"Queued {sync_count} campaigns for sync"
        
    except Exception as e:
        logger.error(f"Failed to bulk sync campaigns: {e}")
        raise e


@shared_task(bind=True, max_retries=3)
def retry_failed_recurring_payment(self, donation_id, attempt_number=1):
    """Повторная попытка неудачного рекуррентного платежа с 72-часовыми интервалами"""
    
    try:
        from .models import Donation
        from .services.freedompay import FreedomPayRecurringService
        
        donation = Donation.objects.get(id=donation_id)
        
        # Проверяем что пожертвование все еще активно
        if not donation.recurring_active or donation.status != 'completed':
            logger.info(f"Donation {donation.donation_code} is no longer active for retry")
            return f"Donation {donation.donation_code} is not retryable"
        
        # Получаем токен карты
        card_token = donation.current_card_token
        if not card_token:
            logger.error(f"No card token for donation: {donation.donation_code}")
            return f"No card token for donation {donation.donation_code}"
        
        # Обрабатываем повторный платеж
        service = FreedomPayRecurringService()
        result = service.process_recurring_payment(donation, card_token)
        
        if result['success']:
            logger.info(f"Successfully retried recurring payment for donation: {donation.donation_code}")
            return f"Retry successful for donation {donation.donation_code}"
        else:
            # Если платеж снова неудачен, планируем следующую попытку
            if attempt_number < 3:  # Максимум 3 попытки
                next_retry_delay = 72 * 60 * 60  # 72 часа в секундах
                
                # Планируем следующую попытку
                retry_failed_recurring_payment.apply_async(
                    args=[donation_id, attempt_number + 1],
                    countdown=next_retry_delay
                )
                
                logger.info(f"Scheduled retry #{attempt_number + 1} for donation {donation.donation_code} in 72 hours")
                return f"Scheduled retry #{attempt_number + 1} for donation {donation.donation_code}"
            else:
                # Максимальное количество попыток исчерпано
                logger.warning(f"Max retry attempts reached for donation: {donation.donation_code}")
                
                # Создаем транзакцию с неудачным статусом
                from .models import DonationTransaction
                DonationTransaction.objects.create(
                    donation=donation,
                    transaction_id=f"RETRY_FAILED_{donation.donation_code}_{int(timezone.now().timestamp())}",
                    amount=donation.amount,
                    currency=donation.currency,
                    status='failed',
                    transaction_type='payment',
                    payment_gateway='freedompay',
                    error_message=f"Failed after {attempt_number} retry attempts",
                    gateway_response={'retry_attempts': attempt_number}
                )
                
                return f"Max retry attempts reached for donation {donation.donation_code}"
        
    except Donation.DoesNotExist:
        logger.error(f"Donation with ID {donation_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error retrying failed recurring payment for donation {donation_id}: {e}")
        
        # Повторяем задачу с 72-часовой задержкой если это не последняя попытка
        if attempt_number < 3:
            next_retry_delay = 72 * 60 * 60  # 72 часа в секундах
            raise self.retry(countdown=next_retry_delay, exc=e)
        else:
            raise e


@shared_task
def process_failed_recurring_payments():
    """Обработка неудачных рекуррентных платежей с планированием повторов"""
    
    try:
        from .models import Donation, DonationTransaction
        
        # Находим неудачные рекуррентные платежи за последние 24 часа
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        failed_recurring = DonationTransaction.objects.filter(
            donation__is_recurring=True,
            donation__recurring_active=True,
            status='failed',
            transaction_type='payment',
            created_at__gte=cutoff_time
        ).select_related('donation')
        
        retry_count = 0
        
        for transaction in failed_recurring:
            donation = transaction.donation
            
            # Проверяем что это действительно рекуррентный платеж (не первоначальный)
            if donation.parent_donation:
                # Планируем повторную попытку
                retry_failed_recurring_payment.delay(donation.id, 1)
                retry_count += 1
                
                logger.info(f"Scheduled retry for failed recurring payment: {transaction.transaction_id}")
        
        logger.info(f"Scheduled {retry_count} retries for failed recurring payments")
        return f"Scheduled {retry_count} retries for failed recurring payments"
        
    except Exception as e:
        logger.error(f"Failed to process failed recurring payments: {e}")
        raise e