from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import BankingRequisite


@admin.register(BankingRequisite)
class BankingRequisiteAdmin(ModelAdmin):
    list_display = [
        'title_with_icon', 
        'organization_type_badge', 
        'currency_badge', 
        'bank_name_short', 
        'account_number_short',
        'is_active_badge',
        'sort_order',
        'created_at_formatted',
        'actions_column'
    ]
    list_filter = [
        'organization_type',
        'currency',
        'is_active',
        'created_at'
    ]
    search_fields = [
        'title',
        'bank_name',
        'account_number',
        'bik',
        'swift',
        'inn',
        'okpo'
    ]
    list_editable = ['sort_order']
    ordering = ['sort_order', 'title']
    list_per_page = 25
    list_select_related = True
    preserve_filters = True
    save_as = True
    save_as_continue = True
    save_on_top = True
    show_full_result_count = True
    show_change_link = True
    
    # Расширенные настройки
    readonly_fields = ['created_at', 'updated_at']
    
    # Расширенные поля с группировкой
    fieldsets = (
        (_('Основная информация'), {
            'fields': (
                'title',
                'organization_type', 
                'currency',
                'description',
                'is_active',
                'sort_order'
            ),
            'classes': ('wide', 'extrapretty')
        }),
        (_('Банковские данные'), {
            'fields': (
                'bank_name',
                'account_number',
                'bik',
                'swift'
            ),
            'classes': ('wide', 'extrapretty')
        }),
        (_('Налоговые данные'), {
            'fields': (
                'inn',
                'okpo',
                'tax_office'
            ),
            'classes': ('wide', 'extrapretty')
        }),
        (_('Корреспондентские банки'), {
            'fields': (
                'correspondent_bank',
                'correspondent_swift',
                'correspondent_address',
                'correspondent_account'
            ),
            'classes': ('collapse', 'extrapretty')
        })
    )
    
    # Действия для массовых операций
    actions = [
        'activate_requisites',
        'deactivate_requisites',
        'export_to_csv',
        'export_to_excel'
    ]
    
    # Дополнительные настройки
    date_hierarchy = 'created_at'
    empty_value_display = '-'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    # Действия для массовых операций
    def activate_requisites(self, request, queryset):
        """Активировать выбранные реквизиты"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'Активировано {updated} реквизитов.',
            level='SUCCESS'
        )
    activate_requisites.short_description = _('Активировать выбранные реквизиты')
    
    def deactivate_requisites(self, request, queryset):
        """Деактивировать выбранные реквизиты"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Деактивировано {updated} реквизитов.',
            level='WARNING'
        )
    deactivate_requisites.short_description = _('Деактивировать выбранные реквизиты')
    
    def export_to_csv(self, request, queryset):
        """Экспорт в CSV"""
        # Реализация экспорта в CSV
        pass
    export_to_csv.short_description = _('Экспорт в CSV')
    
    def export_to_excel(self, request, queryset):
        """Экспорт в Excel"""
        # Реализация экспорта в Excel
        pass
    export_to_excel.short_description = _('Экспорт в Excel')
    
    # Улучшенные методы отображения
    @display(description=_('Название'), ordering='title')
    def title_with_icon(self, obj):
        """Отображение названия с иконкой и ссылкой"""
        icon = "🏦" if obj.organization_type == 'main_foundation' else "🏘️" if obj.organization_type == 'children_village' else "🏢"
        url = reverse('admin:banking_requisites_bankingrequisite_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none; color: inherit;">'
            '<span style="font-weight: 600;">{} {}</span></a>',
            url, icon, obj.title
        )
    
    @display(description=_('Тип организации'), ordering='organization_type')
    def organization_type_badge(self, obj):
        """Отображение типа организации как бейдж с анимацией"""
        colors = {
            'main_foundation': 'primary',
            'children_village': 'success', 
            'educational_center': 'warning',
            'other': 'secondary'
        }
        color = colors.get(obj.organization_type, 'secondary')
        return format_html(
            '<span class="badge bg-{} text-white px-2 py-1 rounded-pill" '
            'style="font-size: 0.8em; transition: all 0.3s ease;">{}</span>',
            color,
            obj.get_organization_type_display()
        )
    
    @display(description=_('Валюта'), ordering='currency')
    def currency_badge(self, obj):
        """Отображение валюты как бейдж с иконками"""
        currency_icons = {
            'KGS': '🇰🇬',
            'USD': '🇺🇸',
            'EUR': '🇪🇺',
            'RUB': '🇷🇺'
        }
        colors = {
            'KGS': 'success',
            'USD': 'primary',
            'EUR': 'info',
            'RUB': 'danger'
        }
        color = colors.get(obj.currency, 'secondary')
        icon = currency_icons.get(obj.currency, '💰')
        return format_html(
            '<span class="badge bg-{} text-white px-2 py-1 rounded-pill" '
            'style="font-size: 0.8em;">{} {}</span>',
            color, icon, obj.get_currency_display()
        )
    
    @display(description=_('Банк'), ordering='bank_name')
    def bank_name_short(self, obj):
        """Сокращенное название банка с тултипом"""
        short_name = obj.bank_name[:30] + "..." if len(obj.bank_name) > 30 else obj.bank_name
        return format_html(
            '<span title="{}" style="cursor: help;">{}</span>',
            obj.bank_name, short_name
        )
    
    @display(description=_('Счет'), ordering='account_number')
    def account_number_short(self, obj):
        """Сокращенный номер счета с копированием"""
        short_number = obj.account_number[:15] + "..." if len(obj.account_number) > 15 else obj.account_number
        return format_html(
            '<span title="{}" style="cursor: pointer; font-family: monospace;" '
            'onclick="navigator.clipboard.writeText(\'{}\')">{}</span>',
            obj.account_number, obj.account_number, short_number
        )
    
    @display(description=_('Статус'), ordering='is_active')
    def is_active_badge(self, obj):
        """Отображение статуса активности с анимацией"""
        if obj.is_active:
            return format_html(
                '<span class="badge bg-success text-white px-2 py-1 rounded-pill" '
                'style="font-size: 0.8em; animation: pulse 2s infinite;">'
                '✓ Активен</span>'
            )
        return format_html(
            '<span class="badge bg-danger text-white px-2 py-1 rounded-pill" '
            'style="font-size: 0.8em;">✗ Неактивен</span>'
        )
    
    @display(description=_('Создано'), ordering='created_at')
    def created_at_formatted(self, obj):
        """Форматированная дата создания с относительным временем"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days == 0:
            if diff.seconds < 3600:
                relative = f"{diff.seconds // 60} мин назад"
            else:
                relative = f"{diff.seconds // 3600} ч назад"
        elif diff.days == 1:
            relative = "Вчера"
        elif diff.days < 7:
            relative = f"{diff.days} дн назад"
        else:
            relative = obj.created_at.strftime('%d.%m.%Y')
            
        return format_html(
            '<span title="{}" style="font-size: 0.9em;">{}</span>',
            obj.created_at.strftime('%d.%m.%Y %H:%M'), relative
        )
    
    @display(description=_('Действия'))
    def actions_column(self, obj):
        """Колонка с быстрыми действиями"""
        change_url = reverse('admin:banking_requisites_bankingrequisite_change', args=[obj.pk])
        delete_url = reverse('admin:banking_requisites_bankingrequisite_delete', args=[obj.pk])
        
        return format_html(
            '<div class="btn-group btn-group-sm" role="group">'
            '<a href="{}" class="btn btn-outline-primary btn-sm" title="Редактировать">'
            '✏️</a>'
            '<a href="{}" class="btn btn-outline-danger btn-sm" title="Удалить" '
            'onclick="return confirm(\'Вы уверены?\')">🗑️</a>'
            '</div>',
            change_url, delete_url
        )
