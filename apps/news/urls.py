from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.news.views import (
    NewsViewSet,
    NewsCategoryViewSet,
    NewsTagViewSet,
    NewsStatsView
)

# Создаем роутер для API
router = DefaultRouter()
router.register(r'news', NewsViewSet, basename='news')
router.register(r'categories', NewsCategoryViewSet, basename='news-category')
router.register(r'tags', NewsTagViewSet, basename='news-tag')
router.register(r'stats', NewsStatsView, basename='news-stats')

app_name = 'news'

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
]