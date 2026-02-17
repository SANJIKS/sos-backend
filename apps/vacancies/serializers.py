from rest_framework import serializers
from apps.vacancies.models import Vacancy


class VacancySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vacancy
        fields = ['title', 'description', 'address', 'work_schedule', 'deadline']