from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from apps.users.models import TwoFactorAuth, TwoFactorLog, TwoFactorCode
from apps.users.serializers.two_factor import (
    TwoFactorAuthSerializer,
    SendTwoFactorCodeSerializer,
    VerifyTwoFactorCodeSerializer,
    EnableTwoFactorSerializer,
    DisableTwoFactorSerializer,
    GenerateBackupCodesSerializer,
    BackupCodesResponseSerializer,
    TwoFactorLogSerializer,
    TwoFactorStatusSerializer,
    TwoFactorSetupSerializer
)
from apps.users.services.two_factor import (
    TwoFactorService,
    TwoFactorCodeService,
    TwoFactorBackupCodeService,
    TwoFactorLogService,
    TwoFactorRateLimitService
)
from apps.users.services.email import send_email


class TwoFactorStatusView(APIView):
    """View для получения статуса 2FA"""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Получить статус двухфакторной аутентификации",
        description="Возвращает текущий статус 2FA для пользователя",
        responses={200: TwoFactorStatusSerializer},
        tags=['users']
    )
    def get(self, request):
        user = request.user
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(user)
        
        # Вычисляем время блокировки
        lock_until = None
        if two_factor_auth.is_locked and two_factor_auth.last_failed_attempt:
            from datetime import timedelta
            lock_until = two_factor_auth.last_failed_attempt + timedelta(minutes=30)
        
        data = {
            'is_enabled': two_factor_auth.is_enabled,
            'is_required': two_factor_auth.is_required,
            'is_locked': two_factor_auth.is_locked,
            'auth_method': two_factor_auth.auth_method,
            'backup_codes_enabled': two_factor_auth.backup_codes_enabled,
            'backup_codes_count': TwoFactorBackupCodeService.get_unused_backup_codes(two_factor_auth),
            'failed_attempts': two_factor_auth.failed_attempts,
            'last_used_at': two_factor_auth.last_used_at,
            'lock_until': lock_until
        }
        
        serializer = TwoFactorStatusSerializer(data)
        return Response(serializer.data)


class SendTwoFactorCodeView(APIView):
    """View для отправки кода 2FA"""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Отправить код двухфакторной аутентификации",
        description="Отправляет код подтверждения на email пользователя",
        request=SendTwoFactorCodeSerializer,
        responses={
            200: {"type": "object", "properties": {"detail": {"type": "string"}}},
            400: {"type": "object", "properties": {"error": {"type": "string"}}}
        },
        tags=['users'],
        examples=[
            OpenApiExample(
                "Success",
                value={"detail": "Код отправлен на email"},
                response_only=True,
                status_codes=["200"]
            ),
            OpenApiExample(
                "Rate Limited",
                value={"error": "Превышен лимит отправки кодов. Попробуйте позже"},
                response_only=True,
                status_codes=["400"]
            )
        ]
    )
    def post(self, request):
        serializer = SendTwoFactorCodeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(user)
        
        # Получаем IP и User-Agent
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            # Создаем код
            two_factor_code, code = TwoFactorCodeService.create_email_code(
                two_factor_auth, ip_address, user_agent
            )
            
            # Отправляем email
            send_email(
                subject="Код подтверждения двухфакторной аутентификации",
                message=f"""
                Ваш код подтверждения: {code}
                
                Код действителен в течение 5 минут.
                Если вы не запрашивали этот код, проигнорируйте это сообщение.
                """,
                recipient_list=[user.email]
            )
            
            return Response({"detail": "Код отправлен на email"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": "Ошибка при отправке кода. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VerifyTwoFactorCodeView(APIView):
    """View для проверки кода 2FA"""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Проверить код двухфакторной аутентификации",
        description="Проверяет введенный код подтверждения",
        request=VerifyTwoFactorCodeSerializer,
        responses={
            200: {"type": "object", "properties": {"detail": {"type": "string"}}},
            400: {"type": "object", "properties": {"error": {"type": "string"}}}
        },
        tags=['users']
    )
    def post(self, request):
        serializer = VerifyTwoFactorCodeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(user)
        
        code = serializer.validated_data['code']
        use_backup_code = serializer.validated_data['use_backup_code']
        
        # Получаем IP и User-Agent
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        if use_backup_code:
            success, message = TwoFactorCodeService.verify_backup_code(
                two_factor_auth, code, ip_address, user_agent
            )
        else:
            success, message = TwoFactorCodeService.verify_code(
                two_factor_auth, code, ip_address, user_agent
            )
        
        if success:
            return Response({"detail": message}, status=status.HTTP_200_OK)
        else:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class EnableTwoFactorView(APIView):
    """View для включения 2FA"""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Включить двухфакторную аутентификацию",
        description="Включает 2FA для пользователя",
        request=EnableTwoFactorSerializer,
        responses={
            200: {"type": "object", "properties": {"detail": {"type": "string"}}},
            400: {"type": "object", "properties": {"error": {"type": "string"}}}
        },
        tags=['users']
    )
    def post(self, request):
        serializer = EnableTwoFactorSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(user)
        
        auth_method = serializer.validated_data['auth_method']
        
        # Включаем 2FA
        two_factor_auth.auth_method = auth_method
        two_factor_auth.status = TwoFactorAuth.Status.ENABLED
        two_factor_auth.save()
        
        # Логируем включение
        TwoFactorLogService.log_action(
            two_factor_auth=two_factor_auth,
            log_type=TwoFactorLog.LogType.TWO_FACTOR_ENABLED,
            status=TwoFactorLog.Status.SUCCESS,
            description=f"2FA включена с методом {auth_method}",
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response(
            {"detail": "Двухфакторная аутентификация включена"},
            status=status.HTTP_200_OK
        )
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DisableTwoFactorView(APIView):
    """View для отключения 2FA"""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Отключить двухфакторную аутентификацию",
        description="Отключает 2FA для пользователя",
        request=DisableTwoFactorSerializer,
        responses={
            200: {"type": "object", "properties": {"detail": {"type": "string"}}},
            400: {"type": "object", "properties": {"error": {"type": "string"}}}
        },
        tags=['users']
    )
    def post(self, request):
        serializer = DisableTwoFactorSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(user)
        
        # Отключаем 2FA
        two_factor_auth.status = TwoFactorAuth.Status.DISABLED
        two_factor_auth.save()
        
        # Удаляем все активные коды
        TwoFactorCode.objects.filter(
            two_factor_auth=two_factor_auth,
            status=TwoFactorCode.Status.PENDING
        ).update(status=TwoFactorCode.Status.INVALIDATED)
        
        # Логируем отключение
        TwoFactorLogService.log_action(
            two_factor_auth=two_factor_auth,
            log_type=TwoFactorLog.LogType.TWO_FACTOR_DISABLED,
            status=TwoFactorLog.Status.SUCCESS,
            description="2FA отключена",
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response(
            {"detail": "Двухфакторная аутентификация отключена"},
            status=status.HTTP_200_OK
        )
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class GenerateBackupCodesView(APIView):
    """View для генерации резервных кодов"""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Сгенерировать резервные коды",
        description="Генерирует новые резервные коды для 2FA",
        request=GenerateBackupCodesSerializer,
        responses={200: BackupCodesResponseSerializer},
        tags=['users']
    )
    def post(self, request):
        serializer = GenerateBackupCodesSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(user)
        
        count = serializer.validated_data['count']
        
        # Генерируем резервные коды
        backup_codes_data = TwoFactorBackupCodeService.generate_backup_codes(two_factor_auth, count)
        
        # Извлекаем только коды для ответа
        codes = [code for _, code in backup_codes_data]
        
        response_data = {
            'codes': codes,
            'warning': "Сохраните эти коды в безопасном месте. Они показываются только один раз!"
        }
        
        serializer = BackupCodesResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TwoFactorLogsView(APIView):
    """View для просмотра логов 2FA"""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Получить логи двухфакторной аутентификации",
        description="Возвращает логи действий 2FA для пользователя",
        parameters=[
            OpenApiParameter(name='limit', type=int, default=50, description='Количество записей')
        ],
        responses={200: TwoFactorLogSerializer(many=True)},
        tags=['users']
    )
    def get(self, request):
        user = request.user
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(user)
        
        limit = int(request.GET.get('limit', 50))
        logs = TwoFactorLogService.get_user_logs(two_factor_auth, limit)
        
        serializer = TwoFactorLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_failed_attempts(request):
    """Сброс неудачных попыток 2FA (для админов)"""
    user = request.user
    
    if not user.is_staff:
        return Response(
            {"error": "Недостаточно прав"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(user)
    two_factor_auth.reset_failed_attempts()
    
    return Response(
        {"detail": "Неудачные попытки сброшены"},
        status=status.HTTP_200_OK
    ) 