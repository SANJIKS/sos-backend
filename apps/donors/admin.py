from django.contrib import admin

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RangeDateFilter,
)

from apps.donors.models import (
    Donor,
)


@admin.register(Donor)
class DonorAdmin(ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'gender', 'preferred_language', 'created_at')
    list_filter = ('gender', 'preferred_language', ('created_at', RangeDateFilter))
    search_fields = ('full_name', 'email', 'phone')
    ordering = ('-created_at',)
