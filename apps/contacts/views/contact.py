from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view

from apps.contacts.models.contact import Contact, ContactCategory
from apps.contacts.serializers.contact import (
    ContactSerializer, ContactCreateSerializer, ContactListSerializer,
    ContactCategorySerializer, ContactFormSerializer
)


@extend_schema_view(
    list=extend_schema(tags=['contacts']),
    retrieve=extend_schema(tags=['contacts']),
)
class ContactCategoryViewSet(ReadOnlyModelViewSet):
    """ViewSet for ContactCategory model"""
    queryset = ContactCategory.objects.filter(is_active=True)
    serializer_class = ContactCategorySerializer
    lookup_field = 'uuid'
    
    def get_queryset(self):
        return ContactCategory.objects.filter(is_active=True).order_by('sort_order', 'name')


@extend_schema_view(
    list=extend_schema(tags=['contacts']),
    retrieve=extend_schema(tags=['contacts']),
    create=extend_schema(tags=['contacts']),
)
class ContactViewSet(ModelViewSet):
    """ViewSet для управления заявками обратной связи"""
    queryset = Contact.objects.all()
    lookup_field = 'uuid'
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ContactCreateSerializer
        elif self.action == 'list':
            return ContactListSerializer
        return ContactSerializer
    
    def get_permissions(self):
        """Создать заявку может любой, остальное только авторизованные"""
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Фильтрация по пользователю для обычных пользователей"""
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            # Обычные пользователи видят только свои заявки
            return self.queryset.filter(email=self.request.user.email)
        return self.queryset
    
    def create(self, request, *args, **kwargs):
        """Создание новой заявки обратной связи"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Добавляем техническую информацию
        contact = serializer.save(
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referrer=request.META.get('HTTP_REFERER', '')
        )
        
        # TODO: Отправка уведомления на email
        
        return Response({
            'message': 'Ваша заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.',
            'contact_id': str(contact.uuid)
        }, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Оставляем старые view для обратной совместимости
@extend_schema_view(get=extend_schema(tags=['contacts']))
class ContactListView(ListAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


@extend_schema_view(get=extend_schema(tags=['contacts']))
class ContactDetailView(RetrieveAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    lookup_field = 'uuid'
    permission_classes = [IsAuthenticatedOrReadOnly]


@extend_schema_view(
    post=extend_schema(
        summary="Отправить форму обратной связи",
        description="Простая форма обратной связи с полями: имя, email, сообщение",
        tags=['contacts']
    )
)
class ContactFormView(CreateAPIView):
    """Простая форма обратной связи из дизайна"""
    serializer_class = ContactFormSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """Создание заявки через простую форму"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Добавляем техническую информацию
        contact = serializer.save(
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referrer=request.META.get('HTTP_REFERER', '')
        )
        
        # TODO: Отправка уведомления на email
        
        return Response({
            'message': 'Ваше сообщение успешно отправлено! Мы свяжемся с вами в ближайшее время.',
            'contact_id': str(contact.uuid)
        }, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        """Получение IP адреса клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
