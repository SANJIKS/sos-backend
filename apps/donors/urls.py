from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.donors.views import (
    F2FRegionViewSet,
    F2FLocationViewSet,
    F2FCoordinatorViewSet,
    F2FRegistrationViewSet,
    F2FRegistrationDocumentViewSet,
    F2FDailyReportViewSet
)

# Создаем роутер для F2F API
router = DefaultRouter()
router.register(r'f2f/regions', F2FRegionViewSet, basename='f2f-region')
router.register(r'f2f/locations', F2FLocationViewSet, basename='f2f-location')
router.register(r'f2f/coordinators', F2FCoordinatorViewSet, basename='f2f-coordinator')
router.register(r'f2f/registrations', F2FRegistrationViewSet, basename='f2f-registration')
router.register(r'f2f/documents', F2FRegistrationDocumentViewSet, basename='f2f-document')
router.register(r'f2f/reports', F2FDailyReportViewSet, basename='f2f-report')

app_name = 'donors'

urlpatterns = [
    # F2F API endpoints
    path('', include(router.urls)),
]