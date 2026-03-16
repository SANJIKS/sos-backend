from django.contrib import admin
from .models import DonationFormContent

@admin.register(DonationFormContent)
class DonationFormContentAdmin(admin.ModelAdmin):
    list_display = ['title']