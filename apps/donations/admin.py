import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    RangeDateTimeFilter,
    MultipleRelatedDropdownFilter,
    SingleNumericFilter,
)

from .models import (
    Donation,
    DonationTransaction,
    DonationCampaign,
)
from .models.card_history import DonorCardHistory


def export_to_csv(modeladmin, request, queryset):
    """Экспорт выбранных записей в CSV"""
    opts = modeladmin.model._meta
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename={opts.verbose_name_plural}.csv'
    
    writer = csv.writer(response)
    
    # Заголовки (названия полей)
    field_names = [field.verbose_name for field in opts.fields]
    writer.writerow(field_names)
    
    # Данные
    for obj in queryset:
        row = []
        for field in opts.fields:
            value = getattr(obj, field.name)
            if value is None:
                value = ''
            row.append(str(value))
        writer.writerow(row)
    
    return response

export_to_csv.short_description = _('Экспорт в CSV')


class DonationTransactionInline(TabularInline):
    model = DonationTransaction
    extra = 0
    readonly_fields = ('uuid', 'transaction_id', 'created_at')
    fields = (
        'transaction_id', 'status', 'amount', 'payment_gateway', 'created_at'
    )


@admin.register(DonationCampaign)
class DonationCampaignAdmin(ModelAdmin):
    list_display = (
        'status', 'image', 'name'
    )
    list_filter = (
        'status',
        'is_featured', 
        ('start_date', RangeDateFilter),
    )
    search_fields = ('name', 'description')
    readonly_fields = ('uuid', 'raised_amount', 'created_at', 'updated_at')
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('name', 'description', 'image', 'status', 'is_featured')
        }),
        (_('Финансовые цели'), {
            'fields': ('goal_amount', 'raised_amount')
        }),
        (_('Даты'), {
            'fields': ('start_date', 'end_date')
        }),
        (_('Системная информация'), {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [export_to_csv]


@admin.register(Donation)
class DonationAdmin(ModelAdmin):
    list_display = (
        'donation_code', 'donor_full_name', 'donor_email', 
        'amount', 'donation_type', 'status', 'is_recurring', 
        'subscription_status', 'created_at'
    )
    list_filter = (
        'status',
        'donation_type',
        'subscription_status',
        'is_recurring',
        ('created_at', RangeDateTimeFilter),
    )
    search_fields = (
        'donation_code', 'donor_full_name', 'donor_email', 
        'donor_phone', 'amount'
    )
    readonly_fields = (
        'uuid', 'donation_code', 'created_at', 'updated_at', 
        'payment_completed_at', 'salesforce_synced'
    )
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': (
                'donation_code', 'donor_full_name', 'donor_email', 'donor_phone',
                'amount', 'donation_type', 'status'
            )
        }),
        (_('Рекуррентные платежи'), {
            'fields': (
                'is_recurring', 'recurring_active', 'subscription_status', 
                'next_payment_date', 'current_card_token'
            ),
            'classes': ('collapse',)
        }),
        (_('F2F информация'), {
            'fields': ('f2f_coordinator', 'f2f_location'),
            'classes': ('collapse',)
        }),
        (_('Дополнительно'), {
            'fields': ('donor_comment', 'admin_notes'),
            'classes': ('collapse',)
        }),
        (_('Salesforce'), {
            'fields': (
                'salesforce_id', 'salesforce_synced', 'salesforce_sync_error'
            ),
            'classes': ('collapse',)
        }),
        (_('Системная информация'), {
            'fields': (
                'uuid', 'created_at', 'updated_at', 'payment_completed_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [DonationTransactionInline]
    actions = [export_to_csv]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('campaign')


@admin.register(DonationTransaction)
class DonationTransactionAdmin(ModelAdmin):
    list_display = (
        'transaction_id', 'donation', 'amount', 'status', 'payment_gateway', 'created_at'
    )
    list_filter = (
        'status',
        'transaction_type',
        'payment_gateway',
        ('created_at', RangeDateTimeFilter),
    )
    search_fields = ('transaction_id', 'donation__donation_code')
    readonly_fields = ('uuid', 'created_at', 'processed_at')
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': (
                'donation', 'transaction_id', 'amount', 'status', 'transaction_type'
            )
        }),
        (_('Платежная система'), {
            'fields': ('payment_gateway', 'gateway_response'),
            'classes': ('collapse',)
        }),
        (_('Системная информация'), {
            'fields': ('uuid', 'created_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [export_to_csv]

















@admin.register(DonorCardHistory)
class DonorCardHistoryAdmin(ModelAdmin):
    list_display = (
        'donation', 'change_type', 'old_card_token', 'new_card_token', 
        'created_at', 'salesforce_synced'
    )
    list_filter = (
        'change_type',
        ('created_at', RangeDateTimeFilter),
        'salesforce_synced',
    )
    search_fields = (
        'donation__donation_code', 'donation__donor_full_name', 
        'donation__donor_email', 'old_card_token', 'new_card_token'
    )
    readonly_fields = ('uuid', 'created_at')
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': (
                'donation', 'change_type', 'old_card_token', 'new_card_token', 'change_reason'
            )
        }),
        (_('Техническая информация'), {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        (_('Salesforce'), {
            'fields': ('salesforce_synced', 'salesforce_sync_error'),
            'classes': ('collapse',)
        }),
        (_('Системная информация'), {
            'fields': ('uuid', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [export_to_csv]