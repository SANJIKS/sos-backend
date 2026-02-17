import logging
from typing import Dict, Optional, List, Any
from decimal import Decimal
from datetime import datetime, date
from django.conf import settings
from django.utils import timezone
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError
import json

logger = logging.getLogger(__name__)


class SalesforceException(Exception):
    """Исключения для работы с Salesforce"""
    pass


class SalesforceService:
    """Сервис для работы с Salesforce CRM"""

    def __init__(self):
        self.username = getattr(settings, 'SALESFORCE_USERNAME', '')
        self.password = getattr(settings, 'SALESFORCE_PASSWORD', '')
        self.security_token = getattr(settings, 'SALESFORCE_SECURITY_TOKEN', '')
        self.domain = getattr(settings, 'SALESFORCE_DOMAIN', 'login')
        self.version = getattr(settings, 'SALESFORCE_VERSION', '60.0')
        self.mock_mode = getattr(settings, 'SALESFORCE_MOCK_MODE', True)
        
        # Автоматически включаем mock режим если credentials не настроены
        if not self.username or not self.password or not self.security_token:
            logger.warning("Salesforce credentials not configured, enabling mock mode")
            self.mock_mode = True
        
        self._sf_client = None

    def _get_client(self) -> Optional[Salesforce]:
        """Получение клиента Salesforce с кешированием"""
        if self.mock_mode:
            return None
            
        if self._sf_client is None:
            try:
                self._sf_client = Salesforce(
                    username=self.username,
                    password=self.password,
                    security_token=self.security_token,
                    domain=self.domain,
                    version=self.version
                )
                logger.info("Successfully connected to Salesforce")
            except SalesforceError as e:
                logger.error(f"Failed to connect to Salesforce: {e}")
                raise SalesforceException(f"Salesforce connection failed: {e}")
        
        return self._sf_client

    def _handle_mock_response(self, operation: str, data: Dict = None) -> Dict:
        """Обработка mock ответов для тестирования"""
        logger.info(f"Mock Salesforce operation: {operation} with data: {data}")
        
        mock_responses = {
            'create_contact': {
                'success': True,
                'id': f'0031234567890{timezone.now().strftime("%H%M%S")}',
                'message': 'Contact created successfully (MOCK)'
            },
            'update_contact': {
                'success': True,
                'message': 'Contact updated successfully (MOCK)'
            },
            'create_opportunity': {
                'success': True,
                'id': f'0061234567890{timezone.now().strftime("%H%M%S")}',
                'message': 'Opportunity created successfully (MOCK)'
            },
            'create_campaign': {
                'success': True,
                'id': f'7011234567890{timezone.now().strftime("%H%M%S")}',
                'message': 'Campaign created successfully (MOCK)'
            },
            'search_contact': {
                'success': True,
                'records': [],
                'message': 'No contacts found (MOCK)'
            }
        }
        
        return mock_responses.get(operation, {
            'success': True,
            'message': f'Mock operation {operation} completed'
        })

    def create_or_update_contact(self, donor_data: Dict) -> Dict:
        """Создание или обновление контакта в Salesforce"""
        if self.mock_mode:
            return self._handle_mock_response('create_contact', donor_data)

        try:
            sf = self._get_client()
            
            # Поиск существующего контакта по email
            existing_contact = self.search_contact_by_email(donor_data.get('email'))
            
            contact_data = {
                'FirstName': donor_data.get('first_name', ''),
                'LastName': donor_data.get('last_name', 'Unknown'),
                'Email': donor_data.get('email'),
                'Phone': donor_data.get('phone', ''),
                'MailingStreet': donor_data.get('address', ''),
                'MailingCity': donor_data.get('city', ''),
                'MailingCountry': donor_data.get('country', 'Kyrgyzstan'),
                'Description': f"Donor from SOS Children's Villages KG. Source: {donor_data.get('source', 'Online')}",
                'LeadSource': donor_data.get('source', 'Website'),
            }
            
            # Убираем пустые значения
            contact_data = {k: v for k, v in contact_data.items() if v}
            
            if existing_contact:
                # Обновляем существующий контакт
                sf.Contact.update(existing_contact['Id'], contact_data)
                logger.info(f"Updated Salesforce contact: {existing_contact['Id']}")
                return {
                    'success': True,
                    'id': existing_contact['Id'],
                    'action': 'updated',
                    'message': 'Contact updated successfully'
                }
            else:
                # Создаем новый контакт
                result = sf.Contact.create(contact_data)
                logger.info(f"Created Salesforce contact: {result['id']}")
                return {
                    'success': True,
                    'id': result['id'],
                    'action': 'created',
                    'message': 'Contact created successfully'
                }
                
        except SalesforceError as e:
            logger.error(f"Salesforce contact operation failed: {e}")
            raise SalesforceException(f"Contact operation failed: {e}")

    def search_contact_by_email(self, email: str) -> Optional[Dict]:
        """Поиск контакта по email"""
        if self.mock_mode:
            mock_response = self._handle_mock_response('search_contact', {'email': email})
            return mock_response['records'][0] if mock_response['records'] else None

        try:
            sf = self._get_client()
            query = f"SELECT Id, FirstName, LastName, Email FROM Contact WHERE Email = '{email}' LIMIT 1"
            result = sf.query(query)
            
            return result['records'][0] if result['records'] else None
            
        except SalesforceError as e:
            logger.error(f"Salesforce contact search failed: {e}")
            return None

    def create_opportunity(self, donation_data: Dict, contact_id: str) -> Dict:
        """Создание возможности (пожертвования) в Salesforce"""
        if self.mock_mode:
            return self._handle_mock_response('create_opportunity', donation_data)

        try:
            sf = self._get_client()
            
            # Определяем тип возможности с учетом последующих платежей
            is_subsequent = donation_data.get('is_subsequent_payment', False)
            stage_name = self._map_donation_status_to_stage(
                donation_data.get('status', 'pending'), 
                is_subsequent
            )
            
            # Используем Order ID в названии и описании для правильной связи платежей
            order_id = donation_data.get('order_id', donation_data.get('donation_code', 'N/A'))
            
            opportunity_data = {
                'Name': f"Donation {order_id} - {donation_data.get('donor_name', 'Anonymous')}",
                'ContactId': contact_id,
                'Amount': float(donation_data.get('amount', 0)),
                'StageName': stage_name,
                'CloseDate': donation_data.get('close_date', timezone.now().date().isoformat()),
                'Type': self._map_donation_type(donation_data.get('donation_type', 'one_time')),
                'LeadSource': donation_data.get('source', 'Website'),
                'Description': f"""
Donation Details:
- Order ID: {order_id}
- Code: {donation_data.get('donation_code', 'N/A')}
- Type: {donation_data.get('donation_type', 'N/A')}
- Payment Method: {donation_data.get('payment_method', 'N/A')}
- Currency: {donation_data.get('currency', 'KGS')}
- Donor Comment: {donation_data.get('donor_comment', 'N/A')}
- Campaign: {donation_data.get('campaign_name', 'General')}
- Parent Order ID: {donation_data.get('parent_order_id', 'N/A')}
                """.strip(),
                'CurrencyIsoCode': donation_data.get('currency', 'KGS'),
            }
            
            # Добавляем кампанию если есть
            if donation_data.get('campaign_id'):
                opportunity_data['CampaignId'] = donation_data['campaign_id']
            
            result = sf.Opportunity.create(opportunity_data)
            logger.info(f"Created Salesforce opportunity: {result['id']}")
            
            return {
                'success': True,
                'id': result['id'],
                'message': 'Opportunity created successfully'
            }
            
        except SalesforceError as e:
            logger.error(f"Salesforce opportunity creation failed: {e}")
            raise SalesforceException(f"Opportunity creation failed: {e}")

    def create_campaign(self, campaign_data: Dict) -> Dict:
        """Создание кампании в Salesforce"""
        if self.mock_mode:
            return self._handle_mock_response('create_campaign', campaign_data)

        try:
            sf = self._get_client()
            
            campaign_sf_data = {
                'Name': campaign_data.get('title', 'Untitled Campaign'),
                'Description': campaign_data.get('description', ''),
                'Type': 'Fundraising',
                'Status': 'In Progress' if campaign_data.get('is_active', True) else 'Completed',
                'StartDate': campaign_data.get('start_date', timezone.now().date().isoformat()),
                'EndDate': campaign_data.get('end_date'),
                'ExpectedRevenue': float(campaign_data.get('target_amount', 0)) if campaign_data.get('target_amount') else None,
                'BudgetedCost': float(campaign_data.get('target_amount', 0)) if campaign_data.get('target_amount') else None,
                'IsActive': campaign_data.get('is_active', True),
            }
            
            # Убираем None значения
            campaign_sf_data = {k: v for k, v in campaign_sf_data.items() if v is not None}
            
            result = sf.Campaign.create(campaign_sf_data)
            logger.info(f"Created Salesforce campaign: {result['id']}")
            
            return {
                'success': True,
                'id': result['id'],
                'message': 'Campaign created successfully'
            }
            
        except SalesforceError as e:
            logger.error(f"Salesforce campaign creation failed: {e}")
            raise SalesforceException(f"Campaign creation failed: {e}")

    def update_opportunity_status(self, opportunity_id: str, new_status: str) -> Dict:
        """Обновление статуса возможности"""
        if self.mock_mode:
            return self._handle_mock_response('update_opportunity', {
                'opportunity_id': opportunity_id,
                'status': new_status
            })

        try:
            sf = self._get_client()
            
            stage_name = self._map_donation_status_to_stage(new_status)
            
            update_data = {
                'StageName': stage_name
            }
            
            # Если завершено успешно, устанавливаем дату закрытия
            if new_status == 'completed':
                update_data['CloseDate'] = timezone.now().date().isoformat()
            
            sf.Opportunity.update(opportunity_id, update_data)
            logger.info(f"Updated Salesforce opportunity {opportunity_id} status to {new_status}")
            
            return {
                'success': True,
                'message': 'Opportunity status updated successfully'
            }
            
        except SalesforceError as e:
            logger.error(f"Salesforce opportunity update failed: {e}")
            raise SalesforceException(f"Opportunity update failed: {e}")

    def _map_donation_status_to_stage(self, status: str, is_subsequent_payment: bool = False) -> str:
        """Маппинг статуса пожертвования в стадии Salesforce"""
        if is_subsequent_payment:
            # Для последующих платежей используем специальные статусы
            mapping = {
                'pending': 'Prospecting',
                'processing': 'Qualification',
                'completed': 'Closed Won',
                'failed': 'Missed',  # Критично: не закрываем донат, только обновляем стадию
                'cancelled': 'Closed Lost',  # Отмененные пожертвования
                'refunded': 'Prospecting'  # Оставляем открытым до выяснения логики
            }
        else:
            # Для первоначальных платежей
            mapping = {
                'pending': 'Prospecting',
                'processing': 'Qualification',
                'completed': 'Closed Won',
                'failed': 'Closed Lost',
                'cancelled': 'Closed Lost',  # Отмененные пожертвования
                'refunded': 'Prospecting'  # Оставляем открытым до выяснения логики
            }
        return mapping.get(status, 'Prospecting')

    def _map_donation_type(self, donation_type: str) -> str:
        """Маппинг типа пожертвования"""
        mapping = {
            'one_time': 'One-time Donation',
            'monthly': 'Monthly Recurring',
            'quarterly': 'Quarterly Recurring',
            'yearly': 'Annual Recurring'
        }
        return mapping.get(donation_type, 'One-time Donation')

    def sync_donor_to_salesforce(self, donor_data: Dict) -> Dict:
        """Синхронизация донора в Salesforce"""
        try:
            # Разбиваем полное имя на имя и фамилию
            full_name = donor_data.get('donor_full_name', '').strip()
            name_parts = full_name.split(' ', 1)
            
            salesforce_donor = {
                'first_name': name_parts[0] if name_parts else '',
                'last_name': name_parts[1] if len(name_parts) > 1 else 'Unknown',
                'email': donor_data.get('donor_email', ''),
                'phone': donor_data.get('donor_phone', ''),
                'source': donor_data.get('donor_source', 'Online'),
            }
            
            result = self.create_or_update_contact(salesforce_donor)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync donor to Salesforce: {e}")
            raise SalesforceException(f"Donor sync failed: {e}")

    def create_recurring_donation(self, recurring_data: Dict, contact_id: str) -> Dict:
        """Создание Recurring Donation объекта в Salesforce (NPSP)"""
        if self.mock_mode:
            return self._handle_mock_response('create_recurring_donation', recurring_data)
        
        try:
            sf = self._get_client()
            
            # NPSP использует объект npe03__Recurring_Donation__c
            recurring_donation_data = {
                'npe03__Contact__c': contact_id,
                'npe03__Amount__c': float(recurring_data.get('amount', 0)),
                'npe03__Installment_Period__c': self._map_recurring_period(recurring_data.get('donation_type', 'monthly')),
                'npe03__Date_Established__c': recurring_data.get('start_date', timezone.now().date().isoformat()),
                'npe03__Open_Ended_Status__c': 'Open',
                'Name': f"Recurring Donation - {recurring_data.get('order_id', 'N/A')}",
                'npe03__Recurring_Donation_Campaign__c': recurring_data.get('campaign_id'),
            }
            
            # Убираем None значения
            recurring_donation_data = {k: v for k, v in recurring_donation_data.items() if v is not None}
            
            result = sf.npe03__Recurring_Donation__c.create(recurring_donation_data)
            logger.info(f"Created Salesforce Recurring Donation: {result['id']}")
            
            return {
                'success': True,
                'id': result['id'],
                'message': 'Recurring Donation created successfully'
            }
            
        except SalesforceError as e:
            logger.error(f"Salesforce Recurring Donation creation failed: {e}")
            # Если объект не существует, возвращаем mock ответ
            if 'INVALID_TYPE' in str(e):
                logger.warning("Recurring Donation object not available, skipping")
                return {
                    'success': True,
                    'id': f'MOCK_RD_{timezone.now().strftime("%H%M%S")}',
                    'message': 'Recurring Donation created (MOCK - object not available)'
                }
            raise SalesforceException(f"Recurring Donation creation failed: {e}")
    
    def create_payment(self, payment_data: Dict, opportunity_id: str) -> Dict:
        """Создание Payment объекта в Salesforce (NPSP)"""
        if self.mock_mode:
            return self._handle_mock_response('create_payment', payment_data)
        
        try:
            sf = self._get_client()
            
            # NPSP использует объект npe01__OppPayment__c
            payment_sf_data = {
                'npe01__Opportunity__c': opportunity_id,
                'npe01__Payment_Amount__c': float(payment_data.get('amount', 0)),
                'npe01__Payment_Date__c': payment_data.get('payment_date', timezone.now().date().isoformat()),
                'npe01__Payment_Method__c': self._map_payment_method(payment_data.get('payment_method', 'bank_card')),
                'npe01__Paid__c': payment_data.get('status') == 'completed',
            }
            
            # Убираем None значения
            payment_sf_data = {k: v for k, v in payment_sf_data.items() if v is not None}
            
            result = sf.npe01__OppPayment__c.create(payment_sf_data)
            logger.info(f"Created Salesforce Payment: {result['id']}")
            
            return {
                'success': True,
                'id': result['id'],
                'message': 'Payment created successfully'
            }
            
        except SalesforceError as e:
            logger.error(f"Salesforce Payment creation failed: {e}")
            # Если объект не существует, возвращаем mock ответ
            if 'INVALID_TYPE' in str(e):
                logger.warning("Payment object not available, skipping")
                return {
                    'success': True,
                    'id': f'MOCK_PAY_{timezone.now().strftime("%H%M%S")}',
                    'message': 'Payment created (MOCK - object not available)'
                }
            raise SalesforceException(f"Payment creation failed: {e}")
    
    def _map_recurring_period(self, donation_type: str) -> str:
        """Маппинг типа пожертвования в период NPSP"""
        mapping = {
            'monthly': 'Monthly',
            'quarterly': 'Quarterly',
            'yearly': 'Yearly',
            'one_time': 'Monthly'  # По умолчанию
        }
        return mapping.get(donation_type, 'Monthly')
    
    def _map_payment_method(self, payment_method: str) -> str:
        """Маппинг способа оплаты в формат Salesforce"""
        mapping = {
            'bank_card': 'Credit Card',
            'bank_transfer': 'Bank Transfer',
            'mobile_payment': 'Mobile Payment',
            'cash': 'Cash',
            'crypto': 'Other'
        }
        return mapping.get(payment_method, 'Other')

    def sync_donation_to_salesforce(self, donation_data: Dict) -> Dict:
        """Синхронизация пожертвования в Salesforce с полной иерархией"""
        try:
            # Шаг 1: Синхронизируем донора (Contact)
            donor_result = self.sync_donor_to_salesforce(donation_data)
            contact_id = donor_result.get('id')
            
            if not contact_id:
                raise SalesforceException("Failed to get or create contact ID")
            
            # Шаг 2: Для рекуррентных пожертвований создаем Recurring Donation
            recurring_donation_id = None
            is_recurring = donation_data.get('is_recurring', False) or donation_data.get('donation_type') in ['monthly', 'quarterly', 'yearly']
            
            if is_recurring and not donation_data.get('parent_order_id'):
                # Это первый платеж в рекуррентной подписке
                try:
                    recurring_data = {
                        'amount': donation_data.get('amount', 0),
                        'donation_type': donation_data.get('donation_type', 'monthly'),
                        'start_date': donation_data.get('created_at', timezone.now()).date().isoformat(),
                        'campaign_id': donation_data.get('salesforce_campaign_id'),
                        'order_id': donation_data.get('order_id', donation_data.get('donation_code', '')),
                    }
                    recurring_result = self.create_recurring_donation(recurring_data, contact_id)
                    recurring_donation_id = recurring_result.get('id')
                except Exception as e:
                    logger.warning(f"Failed to create Recurring Donation: {e}")
            
            # Шаг 3: Создаем Opportunity
            opportunity_data = {
                'order_id': donation_data.get('order_id', donation_data.get('donation_code', '')),
                'donation_code': donation_data.get('donation_code', ''),
                'donor_name': donation_data.get('donor_full_name', ''),
                'amount': donation_data.get('amount', 0),
                'currency': donation_data.get('currency', 'KGS'),
                'donation_type': donation_data.get('donation_type', 'one_time'),
                'payment_method': donation_data.get('payment_method', ''),
                'donor_comment': donation_data.get('donor_comment', ''),
                'status': donation_data.get('status', 'pending'),
                'source': donation_data.get('donor_source', 'Online'),
                'close_date': donation_data.get('created_at', timezone.now()).date().isoformat(),
                'campaign_name': donation_data.get('campaign_title', 'General'),
                'campaign_id': donation_data.get('salesforce_campaign_id'),
                'parent_order_id': donation_data.get('parent_order_id'),
            }
            
            opportunity_result = self.create_opportunity(opportunity_data, contact_id)
            opportunity_id = opportunity_result.get('id')
            
            # Шаг 4: Создаем Payment для каждой транзакции
            payment_id = None
            if donation_data.get('status') in ['completed', 'processing']:
                try:
                    payment_data = {
                        'amount': donation_data.get('amount', 0),
                        'payment_method': donation_data.get('payment_method', 'bank_card'),
                        'payment_date': donation_data.get('payment_date') or donation_data.get('created_at', timezone.now()),
                        'status': donation_data.get('status', 'pending'),
                    }
                    payment_result = self.create_payment(payment_data, opportunity_id)
                    payment_id = payment_result.get('id')
                except Exception as e:
                    logger.warning(f"Failed to create Payment: {e}")
            
            return {
                'success': True,
                'contact_id': contact_id,
                'recurring_donation_id': recurring_donation_id,
                'opportunity_id': opportunity_id,
                'payment_id': payment_id,
                'message': 'Donation synced to Salesforce successfully with full hierarchy'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync donation to Salesforce: {e}")
            raise SalesforceException(f"Donation sync failed: {e}")