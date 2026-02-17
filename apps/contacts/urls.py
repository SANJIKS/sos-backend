from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.contact import (
    ContactListView, ContactDetailView, ContactCategoryViewSet, ContactViewSet, ContactFormView
)
from .views.office import OfficeViewSet

# Create router for API
router = DefaultRouter()
router.register(r'categories', ContactCategoryViewSet, basename='contact-category')
router.register(r'offices', OfficeViewSet, basename='office')
router.register(r'contacts', ContactViewSet, basename='contact')

app_name = 'contacts'

urlpatterns = [
    # Простая форма обратной связи из дизайна
    path('form/', ContactFormView.as_view(), name='contact-form'),
    # Старые эндпоинты для обратной совместимости
    path('contacts-list/', ContactListView.as_view(), name='contact-list'),
    path('<uuid:uuid>/', ContactDetailView.as_view(), name='contact-detail'),
    # Новые эндпоинты через роутер
    path('', include(router.urls)),
]