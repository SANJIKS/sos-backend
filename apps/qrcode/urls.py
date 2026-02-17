from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QRCodeReadOnlyViewSet

router = DefaultRouter()
router.register(r'qrcode', QRCodeReadOnlyViewSet, basename='qrcode')

urlpatterns = [
    path('', include(router.urls)),
]