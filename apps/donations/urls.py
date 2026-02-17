from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DonationViewSet,
    DonationTransactionViewSet,
    DonationCampaignViewSet,
)
from .views.freedompay import (
    FreedomPayWebhookView,
    create_freedompay_payment,
    create_unified_freedompay_payment,
    check_freedompay_payment,
    process_freedompay_refund,
    get_freedompay_methods,
    get_recaptcha_config,
)
from .views.ws_provider import (
    insert_ws_data,
    cancel_donation_ws,
    close_donation_ws,
    update_recurring_donation_ws,
)
from .views.export import export_donations


# Создаем роутер для API
router = DefaultRouter()

# Регистрируем ViewSets
router.register(r'donations', DonationViewSet, basename='donation')
router.register(r'transactions', DonationTransactionViewSet, basename='transaction')
router.register(r'campaigns', DonationCampaignViewSet, basename='campaign')

urlpatterns = [
    path('', include(router.urls)),
    
    # FreedomPay интеграция
    path('freedompay/webhook/', FreedomPayWebhookView.as_view(), name='freedompay-webhook'),
    path('freedompay/create-payment/', create_freedompay_payment, name='freedompay-create-payment'),
    path('freedompay/create-payment-unified/', create_unified_freedompay_payment, name='freedompay-create-payment-unified'),
    path('freedompay/check-payment/<str:order_id>/', check_freedompay_payment, name='freedompay-check-payment'),
    path('freedompay/refund/', process_freedompay_refund, name='freedompay-refund'),
    path('freedompay/methods/', get_freedompay_methods, name='freedompay-methods'),
    path('freedompay/recaptcha-config/', get_recaptcha_config, name='freedompay-recaptcha-config'),
    
    # WS Provider endpoints
    path('ws/insert-ws-data/', insert_ws_data, name='ws-insert-data'),
    path('ws/donations/<uuid:donation_uuid>/cancel/', cancel_donation_ws, name='ws-cancel-donation'),
    path('ws/donations/<uuid:donation_uuid>/close/', close_donation_ws, name='ws-close-donation'),
    path('ws/donations/<uuid:donation_uuid>/update-recurring/', update_recurring_donation_ws, name='ws-update-recurring'),
    
    # Export endpoints
    path('export/donations/', export_donations, name='export-donations'),
    

]