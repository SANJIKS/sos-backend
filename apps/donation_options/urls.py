from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DonationOptionViewSet

# Создаем роутер для API
router = DefaultRouter()
router.register(r'', DonationOptionViewSet, basename='donation-option')

urlpatterns = [
    path('', include(router.urls)),
]
