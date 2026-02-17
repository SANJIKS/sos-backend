from django.urls import path
from apps.users.views.registration import RegisterView
from apps.users.views.verify_email import VerifyEmailView
from apps.users.views.password_reset import (
    ForgotPasswordView,
    VerifyResetTokenView,
    ResetPasswordView,
    cleanup_expired_tokens
)
from apps.users.views.two_factor import (
    TwoFactorStatusView,
    SendTwoFactorCodeView,
    VerifyTwoFactorCodeView,
    EnableTwoFactorView,
    DisableTwoFactorView,
    GenerateBackupCodesView,
    TwoFactorLogsView,
    reset_failed_attempts
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-account/', VerifyEmailView.as_view(), name='verify_account'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Password Reset
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-reset-token/', VerifyResetTokenView.as_view(), name='verify_reset_token'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('cleanup-tokens/', cleanup_expired_tokens, name='cleanup_tokens'),
    
    # Two-Factor Authentication
    path('2fa/status/', TwoFactorStatusView.as_view(), name='2fa_status'),
    path('2fa/send-code/', SendTwoFactorCodeView.as_view(), name='2fa_send_code'),
    path('2fa/verify-code/', VerifyTwoFactorCodeView.as_view(), name='2fa_verify_code'),
    path('2fa/enable/', EnableTwoFactorView.as_view(), name='2fa_enable'),
    path('2fa/disable/', DisableTwoFactorView.as_view(), name='2fa_disable'),
    path('2fa/backup-codes/', GenerateBackupCodesView.as_view(), name='2fa_backup_codes'),
    path('2fa/logs/', TwoFactorLogsView.as_view(), name='2fa_logs'),
    path('2fa/reset-attempts/', reset_failed_attempts, name='2fa_reset_attempts'),
]
