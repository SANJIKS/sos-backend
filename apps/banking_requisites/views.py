from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .models import BankingRequisite
from .serializers import BankingRequisiteSerializer, BankingRequisiteListSerializer


class BankingRequisiteViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для банковских реквизитов"""
    
    queryset = BankingRequisite.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['organization_type', 'currency']
    search_fields = ['title', 'bank_name', 'account_number']
    ordering_fields = ['sort_order', 'title', 'created_at']
    ordering = ['sort_order', 'title']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BankingRequisiteListSerializer
        return BankingRequisiteSerializer
