from rest_framework import serializers

from apps.partners.mixins import BuildFullUrlToImage
from apps.partners.models import Partner

class PartnerSerializer(serializers.ModelSerializer, BuildFullUrlToImage):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = '__all__'

    def get_logo(self, obj):
        logo = getattr(obj, 'logo', None)
        return self.get_full_url_to_image(logo)
