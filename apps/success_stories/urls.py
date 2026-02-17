from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SuccessStoryViewSet

# Создаем роутер для API
router = DefaultRouter()
router.register(r'stories', SuccessStoryViewSet, basename='success-story')

urlpatterns = [
    path('', include(router.urls)),
]
