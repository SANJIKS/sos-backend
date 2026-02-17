from django.urls import path
from apps.vacancies.views import VacancyListView

urlpatterns = [
    path('', VacancyListView.as_view(), name='vacancy-list'),
]