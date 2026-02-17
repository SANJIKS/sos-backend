"""
URLs для common приложения
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.localization import get_supported_languages, get_localization_info
from .views.search import GlobalSearchViewSet

app_name = 'common'

# Создаем router для ViewSet
router = DefaultRouter()
router.register(r'search', GlobalSearchViewSet, basename='search')

urlpatterns = [
    path('languages/', get_supported_languages, name='languages'),
    path('localization-info/', get_localization_info, name='localization-info'),
    path('', include(router.urls)),
]
