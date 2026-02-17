from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DigitalCampaignViewSet, CampaignMetricViewSet

# Создаем роутер для API
router = DefaultRouter()
router.register(r'campaigns', DigitalCampaignViewSet, basename='digital-campaign')
router.register(r'metrics', CampaignMetricViewSet, basename='campaign-metric')

urlpatterns = [
    path('', include(router.urls)),
]

