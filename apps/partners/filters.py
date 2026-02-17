"""
Фильтры для партнеров
"""
import django_filters
from django.db.models import Q
from .models import Partner


class PartnerFilter(django_filters.FilterSet):
    """
    Фильтр для партнеров
    """
    
    category = django_filters.ChoiceFilter(
        choices=Partner.CategoryChoices.choices,
        help_text='Категория партнера'
    )
