from rest_framework import mixins, viewsets, permissions
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import logging

from .models import QRCode
from .serializers import SecureQRCodeSerializer

logger = logging.getLogger(__name__)


class QRCodeReadOnlyViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """ViewSet только для чтения QR-кодов"""
    queryset = QRCode.objects.all()
    serializer_class = SecureQRCodeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @method_decorator(cache_page(60 * 15))  # Кэш на 15 минут
    def list(self, request, *args, **kwargs):
        """Получение списка QR-кодов с кэшированием"""
        return super().list(request, *args, **kwargs)
