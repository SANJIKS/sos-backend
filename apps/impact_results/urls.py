from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ImpactResultViewSet

# Создаем роутер для API
router = DefaultRouter()
router.register(r'', ImpactResultViewSet, basename='impact-result')

urlpatterns = [
    path('', include(router.urls)),
]
