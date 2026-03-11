from rest_framework import viewsets, filters, status
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import SOSFriend
from .serializers import SOSFriendSerializer, SOSFriendCreateSerializer


class SOSFriendPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'current_page': self.page.number,
            'results': data,
        })


class SOSFriendViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    pagination_class = SOSFriendPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sort_order', 'created_at']
    ordering = ['sort_order', '-created_at']

    def get_queryset(self):
        return SOSFriend.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.action == 'create':
            return SOSFriendCreateSerializer
        return SOSFriendSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    http_method_names = ['get', 'post', 'head', 'options']