from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend

from apps.partners.models import Partner
from apps.partners.serializers import PartnerSerializer
from apps.partners.filters import PartnerFilter


@extend_schema(tags=['partners'])
class PartnerListView(ListAPIView):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PartnerFilter
    
    