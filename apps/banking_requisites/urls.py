from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BankingRequisiteViewSet

router = DefaultRouter()
router.register(r'requisites', BankingRequisiteViewSet, basename='banking-requisites')

urlpatterns = [
    path('', include(router.urls)),
]
