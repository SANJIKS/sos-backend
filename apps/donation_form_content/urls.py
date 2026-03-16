from django.urls import path
from .views import DonationFormContentView

urlpatterns = [
    path('donation-form-content/', DonationFormContentView.as_view()),
]