from rest_framework import serializers
from .models import DonationFormContent

class DonationFormContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationFormContent
        fields = '__all__'