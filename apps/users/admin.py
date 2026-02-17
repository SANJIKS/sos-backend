from django.contrib import admin
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule
from unfold.admin import ModelAdmin
from apps.users.models import User, TwoFactorAuth, TwoFactorCode, TwoFactorBackupCode, TwoFactorLog, UserAdminAccess
from apps.users.admin.user_admin_access import UserAdminAccessInline



@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'is_active', 'has_2fa', 'has_admin_access')
    list_filter = ('is_active', 'user_type', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'full_name')
    readonly_fields = ('uuid', 'email', 'created_at', 'updated_at', 'last_login')
    inlines = [UserAdminAccessInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('email', 'first_name', 'last_name', 'full_name', 'phone')
        }),
        ('Тип пользователя', {
            'fields': ('user_type', 'gender', 'birth_date', 'preferred_language')
        }),
        ('Адресная информация', {
            'fields': ('city', 'address', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Настройки уведомлений', {
            'fields': ('email_notifications', 'sms_notifications', 'newsletter_subscription'),
            'classes': ('collapse',)
        }),
        ('Согласия', {
            'fields': ('consent_data_processing', 'consent_marketing'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('is_active', 'is_staff', 'is_verified', 'registration_source'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    def has_2fa(self, obj):
        return obj.two_factor_auth.is_enabled if hasattr(obj, 'two_factor_auth') else False
    has_2fa.boolean = True
    has_2fa.short_description = '2FA включена'
    
    def has_admin_access(self, obj):
        """Проверить наличие настроенных прав доступа к админке"""
        if not obj or not obj.is_staff:
            return False
        if hasattr(obj, 'admin_access'):
            return obj.admin_access.is_active
        return False
    has_admin_access.boolean = True
    has_admin_access.short_description = 'Доступ к админке'


@admin.register(TwoFactorAuth)
class TwoFactorAuthAdmin(ModelAdmin):
    list_display = ('user', 'status', 'auth_method', 'is_required', 'is_locked', 'failed_attempts')
    list_filter = ('status', 'auth_method', 'is_required', 'backup_codes_enabled')
    search_fields = ('user__email', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at', 'last_used_at', 'last_failed_attempt')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'auth_method', 'status', 'is_required')
        }),
        ('Безопасность', {
            'fields': ('backup_codes_enabled', 'failed_attempts', 'last_failed_attempt')
        }),
        ('Статистика', {
            'fields': ('last_used_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_locked(self, obj):
        return obj.is_locked
    is_locked.boolean = True
    is_locked.short_description = 'Заблокирована'


@admin.register(TwoFactorCode)
class TwoFactorCodeAdmin(ModelAdmin):
    list_display = ('uuid', 'two_factor_auth', 'code_type', 'status', 'attempts_used', 'created_at', 'expires_at')
    list_filter = ('code_type', 'status', 'created_at')
    search_fields = ('two_factor_auth__user__email', 'uuid')
    readonly_fields = ('uuid', 'created_at', 'expires_at', 'used_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('uuid', 'two_factor_auth', 'code_type', 'status')
        }),
        ('Попытки', {
            'fields': ('attempts_used', 'max_attempts')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'expires_at', 'used_at'),
            'classes': ('collapse',)
        }),
        ('Метаданные', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TwoFactorBackupCode)
class TwoFactorBackupCodeAdmin(ModelAdmin):
    list_display = ('two_factor_auth', 'is_used', 'created_at', 'used_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('two_factor_auth__user__email',)
    readonly_fields = ('created_at', 'used_at')


@admin.register(TwoFactorLog)
class TwoFactorLogAdmin(ModelAdmin):
    list_display = ('two_factor_auth', 'log_type', 'status', 'ip_address', 'created_at')
    list_filter = ('log_type', 'status', 'created_at')
    search_fields = ('two_factor_auth__user__email', 'description', 'ip_address')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('two_factor_auth', 'log_type', 'status', 'description')
        }),
        ('Метаданные', {
            'fields': ('ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_to_csv', 'export_to_excel']
    
    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="2fa_logs.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Пользователь', 'Тип', 'Статус', 'Описание', 'IP', 'Дата'])
        
        for log in queryset:
            writer.writerow([
                log.two_factor_auth.user.email,
                log.get_log_type_display(),
                log.get_status_display(),
                log.description,
                log.ip_address,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_to_csv.short_description = "Экспорт в CSV"
    
    def export_to_excel(self, request, queryset):
        # Здесь можно добавить экспорт в Excel
        pass
    export_to_excel.short_description = "Экспорт в Excel"


admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)
