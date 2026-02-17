from django.urls import path

from apps.faq.views import FAQAPIView

urlpatterns = [
    path('', FAQAPIView.as_view(), name='faq-list'),
]