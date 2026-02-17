from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SocialNetworkViewSet

# Создаем роутер для API
router = DefaultRouter()
router.register(r'', SocialNetworkViewSet, basename='social-network')

urlpatterns = [
    path('', include(router.urls)),
]
