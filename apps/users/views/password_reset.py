from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.users.serializers import (
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    VerifyResetTokenSerializer
)
from apps.users.services.password_reset import PasswordResetService
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['auth'],
    summary='Запрос восстановления пароля',
    description='Отправить email с ссылкой для восстановления пароля',

)
class ForgotPasswordView(APIView):
    """Запрос восстановления пароля"""
    
    permission_classes = [AllowAny]

    def post(self, request):
        """Отправить email с ссылкой для восстановления пароля"""
        serializer = ForgotPasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            # Получаем IP и User-Agent для логирования
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Отправляем email (всегда возвращаем успех для безопасности)
            PasswordResetService.send_reset_email(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return Response({
                'message': 'Если указанный email существует в системе, на него будет отправлена ссылка для восстановления пароля'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        """Получить IP адрес клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@extend_schema(
    tags=['auth'],
    summary='Проверка токена восстановления',
    description='Проверить валидность токена восстановления пароля'
)
class VerifyResetTokenView(APIView):
    """Проверка валидности токена восстановления пароля"""
    
    permission_classes = [AllowAny]

    def post(self, request):
        """Проверить токен"""
        serializer = VerifyResetTokenSerializer(data=request.data)
        
        if serializer.is_valid():
            token = serializer.validated_data['token']
            
            reset_token, error = PasswordResetService.verify_reset_token(token)
            
            if error:
                return Response(
                    {'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'message': 'Токен действителен',
                'user_email': reset_token.user.email
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['auth'],
    summary='Сброс пароля',
    description='Сбросить пароль по токену восстановления'
)
class ResetPasswordView(APIView):
    """Сброс пароля по токену"""
    
    permission_classes = [AllowAny]

    def post(self, request):
        """Сбросить пароль"""
        serializer = ResetPasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            success, message = PasswordResetService.reset_password(token, new_password)
            
            if success:
                return Response({'message': message})
            else:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['auth'],
    summary='Очистка токенов',
    description='Очистка истекших токенов восстановления пароля'
)
@api_view(['POST'])
@permission_classes([AllowAny])
def cleanup_expired_tokens(request):
    """Очистка истекших токенов (для админов или cron)"""
    # Можно добавить проверку на админские права или API ключ
    count = PasswordResetService.cleanup_expired_tokens()
    return Response({
        'message': f'Очищено {count} истекших токенов'
    })

