from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SOSFriendViewSet

router = DefaultRouter()
router.register(r'friends', SOSFriendViewSet, basename='sos-friends')

urlpatterns = [
    path('', include(router.urls)),
]