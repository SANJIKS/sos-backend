from django.db import models
from django.utils.translation import gettext_lazy as _


class BankingRequisite(models.Model):
    """Модель банковских реквизитов"""
    
    class Currency(models.TextChoices):
        KGS = 'KGS', _('Кыргызский сом')
        USD = 'USD', _('Доллар США')
        EUR = 'EUR', _('Евро')
        RUB = 'RUB', _('Российский рубль')
    
    class OrganizationType(models.TextChoices):
        MAIN_FOUNDATION = 'main_foundation', _('Основной фонд')
        CHILDREN_VILLAGE = 'children_village', _('Детская деревня')
        EDUCATIONAL_CENTER = 'educational_center', _('Образовательный центр')
        OTHER = 'other', _('Другое')
    
    # Основная информация
    title = models.CharField(max_length=255, verbose_name=_('Название'))
    organization_type = models.CharField(
        max_length=50,
        choices=OrganizationType.choices,
        default=OrganizationType.MAIN_FOUNDATION,
        verbose_name=_('Тип организации')
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        verbose_name=_('Валюта')
    )
    
    # Банковские данные
    bank_name = models.CharField(max_length=255, verbose_name=_('Название банка'))
    account_number = models.CharField(max_length=50, verbose_name=_('Номер счета'))
    bik = models.CharField(max_length=20, blank=True, verbose_name=_('БИК'))
    swift = models.CharField(max_length=20, blank=True, verbose_name=_('SWIFT'))
    
    # Налоговые данные
    inn = models.CharField(max_length=20, blank=True, verbose_name=_('ИНН'))
    okpo = models.CharField(max_length=20, blank=True, verbose_name=_('ОКПО'))
    tax_office = models.CharField(max_length=255, blank=True, verbose_name=_('Налоговая инспекция'))
    
    # Корреспондентские банки
    correspondent_bank = models.CharField(max_length=255, blank=True, verbose_name=_('Корреспондентский банк'))
    correspondent_swift = models.CharField(max_length=20, blank=True, verbose_name=_('SWIFT корреспондентского банка'))
    correspondent_address = models.TextField(blank=True, verbose_name=_('Адрес корреспондентского банка'))
    correspondent_account = models.CharField(max_length=50, blank=True, verbose_name=_('Корреспондентский счет'))
    
    # Дополнительная информация
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активный'))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок сортировки'))
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))
    
    class Meta:
        verbose_name = _('Банковский реквизит')
        verbose_name_plural = _('Банковские реквизиты')
        ordering = ['sort_order', 'title']
    
    def __str__(self):
        return f"{self.title} ({self.get_currency_display()})"
