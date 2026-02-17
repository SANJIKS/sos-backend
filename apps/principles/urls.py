from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrincipleViewSet

# Создаем роутер для API
router = DefaultRouter()
router.register(r'', PrincipleViewSet, basename='principle')

urlpatterns = [
    path('', include(router.urls)),
]
