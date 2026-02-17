from django.urls import path
from apps.users.views.admin_2fa import (
    admin_2fa_setup,
    admin_2fa_verify,
    admin_2fa_send_code,
    admin_2fa_backup_codes
)
from apps.users.views.profile import (
    UserProfileView,
    UserDonationHistoryView,
    UserSubscriptionsView,
    UserStatsView,
    ChangePasswordView,
    cancel_subscription,
    reactivate_subscription
)

urlpatterns = [
    # User Profile URLs
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/donations/', UserDonationHistoryView.as_view(), name='user_donations'),
    path('profile/subscriptions/', UserSubscriptionsView.as_view(), name='user_subscriptions'),
    path('profile/stats/', UserStatsView.as_view(), name='user_stats'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('profile/subscriptions/<str:donation_uuid>/cancel/', cancel_subscription, name='cancel_subscription'),
    path('profile/subscriptions/<str:donation_uuid>/reactivate/', reactivate_subscription, name='reactivate_subscription'),
    
    # Admin 2FA URLs
    path('admin/2fa/setup/', admin_2fa_setup, name='2fa_admin_setup'),
    path('admin/2fa/verify/', admin_2fa_verify, name='2fa_admin_verify'),
    path('admin/2fa/send-code/', admin_2fa_send_code, name='2fa_admin_send_code'),
    path('admin/2fa/backup-codes/', admin_2fa_backup_codes, name='2fa_admin_backup_codes'),
]
