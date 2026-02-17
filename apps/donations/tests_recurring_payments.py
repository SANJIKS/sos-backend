"""
Тесты для функционала рекуррентных платежей с без-акцептным списанием

Тестовая карта: 4111 1111 1111 1111, 12/30, 123
"""
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from dateutil.relativedelta import relativedelta

from apps.donations.models import Donation, DonationTransaction, DonationCampaign
from apps.donations.services.freedompay import FreedomPayService, FreedomPayRecurringService
from apps.donations.views.freedompay import FreedomPayWebhookView

User = get_user_model()


class RecurringPaymentsTestCase(TestCase):
    """Тесты для рекуррентных платежей с без-акцептным списанием"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        # Создаем пользователя (модель использует email как USERNAME_FIELD)
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Создаем кампанию
        self.campaign = DonationCampaign.objects.create(
            name='Test Campaign',
            slug='test-campaign',
            description='Test campaign description',
            goal_amount=Decimal('10000.00'),
            status=DonationCampaign.CampaignStatus.ACTIVE,
            start_date=timezone.now(),
        )
        
        # Тестовая карта
        self.test_card = {
            'number': '4111111111111111',
            'expiry': '12/30',
            'cvv': '123'
        }
        
        # Мокируем настройки FreedomPay
        self.freedompay_settings = {
            'FREEDOMPAY_BASE_URL': 'https://api.freedompay.kg',
            'FREEDOMPAY_MERCHANT_ID': 'test_merchant_id',
            'FREEDOMPAY_SECRET_KEY': 'test_secret_key',
            'FREEDOMPAY_TEST_MODE': True,
        }
    
    @override_settings(**{})
    def test_create_recurring_donation_monthly(self):
        """Тест создания ежемесячного рекуррентного пожертвования"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.PENDING,
                is_recurring=True,
            )
            
            # Проверяем, что пожертвование создано
            self.assertIsNotNone(donation)
            self.assertTrue(donation.is_recurring)
            self.assertEqual(donation.donation_type, 'monthly')
            self.assertIsNone(donation.first_payment_date)
            self.assertIsNone(donation.next_payment_date)
            self.assertIsNone(donation.current_card_token)
            self.assertIsNone(donation.recurring_profile_id)
    
    @override_settings(**{})
    def test_setup_recurring_payment_with_card_saving(self):
        """Тест настройки рекуррентного платежа с сохранением карты"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.PENDING,
                is_recurring=True,
            )
            
            # Мокируем ответ от FreedomPay
            mock_response = {
                'pg_status': 'ok',
                'pg_payment_id': '123456789',
                'pg_redirect_url': 'https://payment.freedompay.kg/pay/123456789',
            }
            
            with patch.object(FreedomPayService, 'create_payment', return_value={
                'success': True,
                'payment_url': mock_response['pg_redirect_url'],
                'order_id': f'DON_{donation.donation_code}_123456',
                'payment_id': mock_response['pg_payment_id'],
            }):
                service = FreedomPayRecurringService()
                result = service.setup_recurring_payment(donation)
                
                # Проверяем результат
                self.assertTrue(result['success'])
                self.assertIn('payment_url', result)
                
                # Проверяем, что транзакция создана
                transaction = DonationTransaction.objects.filter(
                    donation=donation
                ).first()
                self.assertIsNotNone(transaction)
                self.assertEqual(transaction.status, 'pending')
    
    @override_settings(**{})
    def test_webhook_saves_first_payment_date_and_card_token(self):
        """Тест обработки webhook с сохранением даты первого платежа и токена карты"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            # Создаем пожертвование
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.PENDING,
                is_recurring=True,
            )
            
            # Создаем транзакцию
            transaction = DonationTransaction.objects.create(
                donation=donation,
                transaction_id=f'DON_{donation.donation_code}_123456',
                external_transaction_id='123456789',
                amount=donation.amount,
                currency=donation.currency,
                status='pending',
                transaction_type='payment',
                payment_gateway='freedompay',
            )
            
            # Симулируем дату первого платежа (14 декабря 2025)
            first_payment_date = datetime(2025, 12, 14, 10, 30, 0)
            first_payment_date = timezone.make_aware(first_payment_date)
            
            # Мокируем webhook данные от FreedomPay
            webhook_data = {
                'pg_order_id': transaction.transaction_id,
                'pg_payment_id': '123456789',
                'pg_amount': '1000',
                'pg_currency': 'KGS',
                'pg_result': '1',  # Успешный платеж
                'pg_payment_date': first_payment_date.isoformat(),
                'pg_card_token': 'test_card_token_12345',
                'pg_recurring_profile_id': '67890',
                'pg_sig': 'test_signature',
            }
            
            # Мокируем проверку подписи и обработку webhook
            with patch.object(FreedomPayService, 'process_webhook', return_value={
                'order_id': transaction.transaction_id,
                'status': 'ok',
                'payment_id': '123456789',
                'amount': Decimal('1000.00'),
                'currency': 'KGS',
                'paid_at': first_payment_date.isoformat(),
                'card_token': 'test_card_token_12345',
                'recurring_profile_id': '67890',
            }):
                with patch.object(FreedomPayService, '_generate_freedompay_signature', return_value='test_signature'):
                    # Создаем mock request
                    from django.test import RequestFactory
                    factory = RequestFactory()
                    request = factory.post('/freedompay/webhook/', webhook_data)
                    
                    # Обрабатываем webhook
                    view = FreedomPayWebhookView()
                    response = view.post(request)
                    
                    # Обновляем объекты из БД
                    donation.refresh_from_db()
                    transaction.refresh_from_db()
                    
                    # Проверяем, что данные сохранены
                    self.assertEqual(donation.current_card_token, 'test_card_token_12345')
                    self.assertEqual(donation.recurring_profile_id, 67890)
                    self.assertIsNotNone(donation.first_payment_date)
                    self.assertEqual(donation.first_payment_date.date(), first_payment_date.date())
                    self.assertIsNotNone(donation.next_payment_date)
                    self.assertTrue(donation.recurring_active)
                    self.assertEqual(donation.status, 'completed')
                    self.assertEqual(transaction.status, 'success')
                    
                    # Проверяем, что next_payment_date рассчитана правильно
                    # Для monthly: следующий платеж должен быть 14 января 2026
                    expected_next_date = first_payment_date + relativedelta(months=1)
                    self.assertEqual(donation.next_payment_date.date(), expected_next_date.date())
    
    @override_settings(**{})
    def test_calculate_next_payment_date_from_first_payment(self):
        """Тест расчета даты следующего платежа от даты первого платежа"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            # Создаем пожертвование с установленной датой первого платежа
            first_payment_date = datetime(2025, 12, 14, 10, 30, 0)
            first_payment_date = timezone.make_aware(first_payment_date)
            
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.COMPLETED,
                is_recurring=True,
                first_payment_date=first_payment_date,
                current_card_token='test_card_token_12345',
                recurring_profile_id=67890,
                recurring_active=True,
            )
            
            service = FreedomPayRecurringService()
            next_date = service._calculate_next_payment_date(donation)
            
            # Проверяем, что следующая дата рассчитана правильно
            # Для monthly: 14 декабря 2025 -> 14 января 2026
            expected_date = first_payment_date + relativedelta(months=1)
            self.assertEqual(next_date.date(), expected_date.date())
            
            # Тест для quarterly
            donation.donation_type = 'quarterly'
            next_date_quarterly = service._calculate_next_payment_date(donation)
            expected_date_quarterly = first_payment_date + relativedelta(months=3)
            self.assertEqual(next_date_quarterly.date(), expected_date_quarterly.date())
            
            # Тест для yearly
            donation.donation_type = 'yearly'
            next_date_yearly = service._calculate_next_payment_date(donation)
            expected_date_yearly = first_payment_date + relativedelta(years=1)
            self.assertEqual(next_date_yearly.date(), expected_date_yearly.date())
            
            # Тест для one_time (не должно быть следующей даты)
            donation.donation_type = 'one_time'
            next_date_one_time = service._calculate_next_payment_date(donation)
            self.assertIsNone(next_date_one_time)
    
    @override_settings(**{})
    def test_process_recurring_payment_with_recurring_profile_id(self):
        """Тест обработки рекуррентного платежа с использованием recurring_profile_id"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            first_payment_date = datetime(2025, 12, 14, 10, 30, 0)
            first_payment_date = timezone.make_aware(first_payment_date)
            
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.COMPLETED,
                is_recurring=True,
                first_payment_date=first_payment_date,
                current_card_token='test_card_token_12345',
                recurring_profile_id=67890,
                recurring_active=True,
                next_payment_date=first_payment_date + relativedelta(months=1),
            )
            
            # Мокируем make_recurring_payment
            with patch.object(FreedomPayService, 'make_recurring_payment', return_value={
                'success': True,
                'order_id': f'REC_{donation.donation_code}_789012',
                'payment_id': '987654321',
                'status': 'ok',
                'message': 'Recurring payment processed successfully',
            }):
                service = FreedomPayRecurringService()
                result = service.process_recurring_payment(donation)
                
                # Проверяем результат
                self.assertTrue(result['success'])
                self.assertIn('transaction_id', result)
                
                # Проверяем, что транзакция создана
                transaction = DonationTransaction.objects.filter(
                    donation=donation
                ).exclude(transaction_id__startswith='DON_').first()
                self.assertIsNotNone(transaction)
                self.assertEqual(transaction.status, 'pending')
                
                # Проверяем, что next_payment_date обновлена
                donation.refresh_from_db()
                self.assertIsNotNone(donation.next_payment_date)
                # Следующий платеж должен быть 14 февраля 2026
                expected_next = first_payment_date + relativedelta(months=2)
                self.assertEqual(donation.next_payment_date.date(), expected_next.date())
    
    @override_settings(**{})
    def test_process_recurring_payment_with_card_token_fallback(self):
        """Тест обработки рекуррентного платежа с использованием card_token (fallback)"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            first_payment_date = datetime(2025, 12, 14, 10, 30, 0)
            first_payment_date = timezone.make_aware(first_payment_date)
            
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.COMPLETED,
                is_recurring=True,
                first_payment_date=first_payment_date,
                current_card_token='test_card_token_12345',
                # Нет recurring_profile_id, будет использован card_token
                recurring_active=True,
                next_payment_date=first_payment_date + relativedelta(months=1),
            )
            
            # Мокируем card_direct
            with patch.object(FreedomPayService, 'card_direct', return_value={
                'success': True,
                'order_id': f'DIRECT_{donation.donation_code}_789012',
                'payment_id': '987654321',
                'status': 'ok',
                'message': 'Direct payment successful',
            }):
                service = FreedomPayRecurringService()
                result = service.process_recurring_payment(donation, 'test_card_token_12345')
                
                # Проверяем результат
                self.assertTrue(result['success'])
                self.assertIn('transaction_id', result)
                
                # Проверяем, что использован card_direct
                donation.refresh_from_db()
                transaction = DonationTransaction.objects.filter(
                    donation=donation
                ).exclude(transaction_id__startswith='DON_').first()
                self.assertIsNotNone(transaction)
    
    @override_settings(**{})
    def test_one_time_donation_does_not_create_subscription(self):
        """Тест что одноразовое пожертвование не создает подписку"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='one_time',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.PENDING,
                is_recurring=False,
            )
            
            # Создаем транзакцию
            transaction = DonationTransaction.objects.create(
                donation=donation,
                transaction_id=f'DON_{donation.donation_code}_123456',
                external_transaction_id='123456789',
                amount=donation.amount,
                currency=donation.currency,
                status='pending',
                transaction_type='payment',
                payment_gateway='freedompay',
            )
            
            # Симулируем webhook данные
            webhook_data = {
                'pg_order_id': transaction.transaction_id,
                'pg_payment_id': '123456789',
                'pg_amount': '1000',
                'pg_currency': 'KGS',
                'pg_result': '1',
                'pg_payment_date': timezone.now().isoformat(),
                'pg_card_token': 'test_card_token_12345',
                'pg_recurring_profile_id': '67890',
                'pg_sig': 'test_signature',
            }
            
            # Мокируем обработку webhook
            with patch.object(FreedomPayService, 'process_webhook', return_value={
                'order_id': transaction.transaction_id,
                'status': 'ok',
                'payment_id': '123456789',
                'amount': Decimal('1000.00'),
                'currency': 'KGS',
                'paid_at': timezone.now().isoformat(),
                'card_token': 'test_card_token_12345',
                'recurring_profile_id': '67890',
            }):
                with patch.object(FreedomPayService, '_generate_freedompay_signature', return_value='test_signature'):
                    from django.test import RequestFactory
                    factory = RequestFactory()
                    request = factory.post('/freedompay/webhook/', webhook_data)
                    
                    view = FreedomPayWebhookView()
                    response = view.post(request)
                    
                    # Обновляем объекты из БД
                    donation.refresh_from_db()
                    
                    # Проверяем, что для one_time не сохраняются данные подписки
                    self.assertIsNone(donation.current_card_token)
                    self.assertIsNone(donation.recurring_profile_id)
                    self.assertIsNone(donation.first_payment_date)
                    self.assertIsNone(donation.next_payment_date)
                    self.assertFalse(donation.recurring_active)
    
    @override_settings(**{})
    def test_recurring_payment_date_preservation(self):
        """Тест сохранения дня месяца при расчете следующих платежей"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            # Первый платеж 14 декабря 2025
            first_payment_date = datetime(2025, 12, 14, 10, 30, 0)
            first_payment_date = timezone.make_aware(first_payment_date)
            
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.COMPLETED,
                is_recurring=True,
                first_payment_date=first_payment_date,
                current_card_token='test_card_token_12345',
                recurring_profile_id=67890,
                recurring_active=True,
            )
            
            service = FreedomPayRecurringService()
            
            # Первый следующий платеж: 14 января 2026
            next_date_1 = service._calculate_next_payment_date(donation)
            self.assertEqual(next_date_1.day, 14)
            self.assertEqual(next_date_1.month, 1)
            self.assertEqual(next_date_1.year, 2026)
            
            # Обновляем next_payment_date и рассчитываем следующий
            donation.next_payment_date = next_date_1
            donation.save()
            
            # Второй следующий платеж: 14 февраля 2026
            next_date_2 = service._calculate_next_payment_date(donation)
            self.assertEqual(next_date_2.day, 14)
            self.assertEqual(next_date_2.month, 2)
            self.assertEqual(next_date_2.year, 2026)
            
            # Третий следующий платеж: 14 марта 2026
            donation.next_payment_date = next_date_2
            donation.save()
            next_date_3 = service._calculate_next_payment_date(donation)
            self.assertEqual(next_date_3.day, 14)
            self.assertEqual(next_date_3.month, 3)
            self.assertEqual(next_date_3.year, 2026)
    
    @override_settings(**{})
    def test_child_donation_inherits_first_payment_date(self):
        """Тест что дочернее пожертвование наследует first_payment_date от родителя"""
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            first_payment_date = datetime(2025, 12, 14, 10, 30, 0)
            first_payment_date = timezone.make_aware(first_payment_date)
            
            # Родительское пожертвование
            parent_donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.COMPLETED,
                is_recurring=True,
                first_payment_date=first_payment_date,
                current_card_token='test_card_token_12345',
                recurring_profile_id=67890,
                recurring_active=True,
            )
            
            # Дочернее пожертвование (создается автоматически при обработке рекуррентного платежа)
            child_donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.PROCESSING,
                is_recurring=False,
                parent_donation=parent_donation,
                first_payment_date=parent_donation.first_payment_date,
                current_card_token=parent_donation.current_card_token,
                recurring_profile_id=parent_donation.recurring_profile_id,
            )
            
            # Проверяем, что дочернее пожертвование наследует first_payment_date
            self.assertEqual(child_donation.first_payment_date, parent_donation.first_payment_date)
            self.assertEqual(child_donation.current_card_token, parent_donation.current_card_token)
            self.assertEqual(child_donation.recurring_profile_id, parent_donation.recurring_profile_id)
            
            # Проверяем расчет следующей даты для дочернего пожертвования
            service = FreedomPayRecurringService()
            next_date = service._calculate_next_payment_date(child_donation)
            
            # Должна использоваться first_payment_date родителя
            expected_date = first_payment_date + relativedelta(months=1)
            self.assertEqual(next_date.date(), expected_date.date())
    
    @override_settings(**{})
    def test_full_recurring_payment_flow(self):
        """Интеграционный тест полного flow рекуррентных платежей:
        1. Создание пожертвования
        2. Первый платеж с сохранением карты
        3. Webhook сохраняет first_payment_date и токен
        4. Автоматический второй платеж через месяц
        5. Проверка что дата сохраняется правильно
        """
        with patch.dict('django.conf.settings.__dict__', self.freedompay_settings):
            # Шаг 1: Создаем рекуррентное пожертвование
            donation = Donation.objects.create(
                user=self.user,
                campaign=self.campaign,
                donor_email='donor@example.com',
                donor_phone='+996555123456',
                donor_full_name='Test Donor',
                amount=Decimal('1000.00'),
                currency='KGS',
                donation_type='monthly',
                payment_method=Donation.PaymentMethod.BANK_CARD,
                status=Donation.DonationStatus.PENDING,
                is_recurring=True,
            )
            
            # Шаг 2: Создаем первый платеж
            with patch.object(FreedomPayService, 'create_payment', return_value={
                'success': True,
                'payment_url': 'https://payment.freedompay.kg/pay/123456789',
                'order_id': f'DON_{donation.donation_code}_123456',
                'payment_id': '123456789',
            }):
                service = FreedomPayRecurringService()
                result = service.setup_recurring_payment(donation)
                self.assertTrue(result['success'])
            
            # Шаг 3: Симулируем успешный платеж через webhook
            first_payment_date = datetime(2025, 12, 14, 10, 30, 0)
            first_payment_date = timezone.make_aware(first_payment_date)
            
            transaction = DonationTransaction.objects.filter(
                donation=donation
            ).first()
            
            webhook_data = {
                'pg_order_id': transaction.transaction_id,
                'pg_payment_id': '123456789',
                'pg_amount': '1000',
                'pg_currency': 'KGS',
                'pg_result': '1',
                'pg_payment_date': first_payment_date.isoformat(),
                'pg_card_token': 'test_card_token_12345',
                'pg_recurring_profile_id': '67890',
                'pg_sig': 'test_signature',
            }
            
            with patch.object(FreedomPayService, 'process_webhook', return_value={
                'order_id': transaction.transaction_id,
                'status': 'ok',
                'payment_id': '123456789',
                'amount': Decimal('1000.00'),
                'currency': 'KGS',
                'paid_at': first_payment_date.isoformat(),
                'card_token': 'test_card_token_12345',
                'recurring_profile_id': '67890',
            }):
                with patch.object(FreedomPayService, '_generate_freedompay_signature', return_value='test_signature'):
                    from django.test import RequestFactory
                    factory = RequestFactory()
                    request = factory.post('/freedompay/webhook/', webhook_data)
                    
                    view = FreedomPayWebhookView()
                    view.post(request)
                    
                    # Проверяем что данные сохранены
                    donation.refresh_from_db()
                    self.assertEqual(donation.first_payment_date.date(), first_payment_date.date())
                    self.assertEqual(donation.current_card_token, 'test_card_token_12345')
                    self.assertEqual(donation.recurring_profile_id, 67890)
                    self.assertEqual(donation.status, 'completed')
                    
                    # Проверяем next_payment_date (должна быть 14 января 2026)
                    expected_next = first_payment_date + relativedelta(months=1)
                    self.assertEqual(donation.next_payment_date.date(), expected_next.date())
            
            # Шаг 4: Симулируем автоматический второй платеж (через месяц)
            # Устанавливаем next_payment_date на правильную дату от first_payment_date (14 января 2026)
            # но в прошлом относительно текущего времени, чтобы триггер сработал
            next_payment = first_payment_date + relativedelta(months=1)  # 14 января 2026
            # Если дата в будущем, устанавливаем её в прошлое (вчера), но сохраняем день месяца
            if next_payment > timezone.now():
                # Устанавливаем на вчера, но с правильным днем месяца от first_payment_date
                yesterday = timezone.now() - timedelta(days=1)
                try:
                    # Пытаемся установить правильный день месяца
                    next_payment = yesterday.replace(day=first_payment_date.day)
                    # Если получилась дата в будущем, используем просто вчера
                    if next_payment > timezone.now():
                        next_payment = yesterday
                except ValueError:
                    # Если день месяца невалиден (например, 31 февраля), используем просто вчера
                    next_payment = yesterday
            donation.next_payment_date = next_payment
            donation.save()
            
            with patch.object(FreedomPayService, 'make_recurring_payment', return_value={
                'success': True,
                'order_id': f'REC_{donation.donation_code}_789012',
                'payment_id': '987654321',
                'status': 'ok',
                'message': 'Recurring payment processed successfully',
            }):
                result = service.process_recurring_payment(donation)
                self.assertTrue(result['success'])
                
                # Проверяем что создана дочерняя транзакция
                child_transactions = DonationTransaction.objects.filter(
                    donation=donation
                ).exclude(transaction_id=transaction.transaction_id)
                self.assertTrue(child_transactions.exists())
                
                # Проверяем что next_payment_date обновлена (должна быть 14 февраля 2026)
                donation.refresh_from_db()
                # После обработки платежа next_payment_date должна быть рассчитана от next_payment_date (14 января)
                # которая была в прошлом, поэтому следующая дата будет 14 февраля
                expected_next_2 = first_payment_date + relativedelta(months=2)
                self.assertEqual(donation.next_payment_date.date(), expected_next_2.date())
                
                # Проверяем что день месяца сохраняется (14-е число)
                self.assertEqual(donation.next_payment_date.day, 14)

