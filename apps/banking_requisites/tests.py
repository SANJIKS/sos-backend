from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import BankingRequisite


class BankingRequisiteModelTest(TestCase):
    """Тесты для модели BankingRequisite"""
    
    def setUp(self):
        self.requisite = BankingRequisite.objects.create(
            title='SOS Детские Деревни Кыргызстана',
            organization_type='main_foundation',
            currency='KGS',
            bank_name='ЗАО «Демир Кыргыз Интернешнл Банк»',
            account_number='1180000030113050',
            bik='118005',
            inn='02901199710077',
            okpo='21676470',
            tax_office='УГНС по Первомайскому району 004'
        )
    
    def test_string_representation(self):
        self.assertEqual(str(self.requisite), 'SOS Детские Деревни Кыргызстана (Кыргызский сом)')
    
    def test_verbose_name(self):
        self.assertEqual(BankingRequisite._meta.verbose_name, 'Банковский реквизит')
        self.assertEqual(BankingRequisite._meta.verbose_name_plural, 'Банковские реквизиты')


class BankingRequisiteAPITest(APITestCase):
    """Тесты для API банковских реквизитов"""
    
    def setUp(self):
        self.requisite = BankingRequisite.objects.create(
            title='SOS Детские Деревни Кыргызстана',
            organization_type='main_foundation',
            currency='KGS',
            bank_name='ЗАО «Демир Кыргыз Интернешнл Банк»',
            account_number='1180000030113050',
            bik='118005',
            is_active=True
        )
    
    def test_list_requisites(self):
        url = reverse('banking-requisites-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_retrieve_requisite(self):
        url = reverse('banking-requisites-detail', kwargs={'pk': self.requisite.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.requisite.title)
