from django.shortcuts import render
from rest_framework.generics import ListAPIView
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from apps.vacancies.models import Vacancy
from apps.vacancies.serializers import VacancySerializer


@extend_schema(tags=['vacancies'])
class VacancyListView(ListAPIView):
    serializer_class = VacancySerializer

    def get_queryset(self):
        return (
            Vacancy.objects
            .filter(is_active=True, deadline__date__gte=timezone.now().date())
            .order_by('-created_at')
        )
