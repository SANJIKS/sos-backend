from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MapPointViewSet

router = DefaultRouter()
router.register(r'map-points', MapPointViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
