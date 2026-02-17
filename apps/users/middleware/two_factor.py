from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from apps.users.services.two_factor import TwoFactorService

User = get_user_model()


class TwoFactorAdminMiddleware(MiddlewareMixin):
    """
    Middleware для проверки 2FA при доступе к админ-панели
    """
    
    def process_request(self, request):
        # Проверяем, что это запрос к админ-панели
        if not request.path.startswith('/admin/'):
            return None
        
        # Пропускаем страницу логина, logout и статические файлы
        if request.path in ['/admin/login/', '/admin/logout/'] or request.path.startswith('/static/'):
            return None
        
        # Если пользователь не аутентифицирован, пропускаем (Django сам перенаправит на логин)
        if not request.user.is_authenticated:
            return None
        
        # Если это не админ или суперадмин, пропускаем
        if not (request.user.is_staff or request.user.is_superuser):
            return None
        
        # Получаем или создаем объект 2FA
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(request.user)
        
        # Если 2FA не обязательна для этого пользователя, пропускаем
        if not TwoFactorService.is_required_for_user(request.user):
            return None
        
        # Если 2FA отключена, но обязательна - перенаправляем на настройку
        if not two_factor_auth.is_enabled:
            messages.warning(
                request,
                "Для доступа к админ-панели необходимо включить двухфакторную аутентификацию."
            )
            return redirect('2fa_admin_setup')
        
        # Проверяем, была ли уже проверена 2FA в этой сессии
        session_verified = request.session.get('2fa_verified', False)
        cookie_verified = request.COOKIES.get('2fa_verified') == 'true'
        
        print(f"DEBUG: 2FA middleware - User: {request.user.email}, Path: {request.path}, Session verified: {session_verified}, Cookie verified: {cookie_verified}")
        
        # Проверяем, что пользователь аутентифицирован и 2FA проверена
        if (session_verified or cookie_verified) and request.user.is_authenticated:
            # Дополнительная проверка времени последней активности
            last_activity = request.session.get('last_activity')
            if last_activity:
                try:
                    last_activity_time = timezone.datetime.fromisoformat(last_activity)
                    # Если прошло больше 30 минут бездействия, требуем повторную 2FA
                    if timezone.now() - last_activity_time > timedelta(minutes=30):
                        print(f"DEBUG: 2FA middleware - Session expired for {request.user.email}")
                        request.session.pop('2fa_verified', None)
                        request.session.pop('2fa_verified_at', None)
                        return redirect('2fa_admin_verify')
                except (ValueError, TypeError):
                    pass
            
            # Обновляем время последней активности
            request.session['last_activity'] = timezone.now().isoformat()
            print(f"DEBUG: 2FA middleware - Allowing access for {request.user.email}")
            return None
        
        # Если 2FA заблокирована, показываем сообщение
        if two_factor_auth.is_locked:
            messages.error(
                request,
                "Двухфакторная аутентификация заблокирована из-за неудачных попыток. "
                "Попробуйте позже или обратитесь к администратору."
            )
            return HttpResponseForbidden("2FA заблокирована")
        
        # Проверяем, не является ли это перенаправлением после успешной 2FA
        # Если в сессии есть флаг о том, что 2FA только что была проверена
        if request.session.get('2fa_just_verified', False):
            # Убираем временный флаг и пропускаем
            request.session.pop('2fa_just_verified', None)
            request.session.modified = True
            print(f"DEBUG: 2FA middleware - Just verified flag found for {request.user.email}, allowing access")
            return None
        
        # Перенаправляем на страницу проверки 2FA
        return redirect('2fa_admin_verify')


class TwoFactorSessionMiddleware(MiddlewareMixin):
    """
    Middleware для управления сессией 2FA
    """
    
    def process_request(self, request):
        # Проверяем, что это запрос к админ-панели
        if not request.path.startswith('/admin/'):
            return None
        
        # Если пользователь не аутентифицирован, пропускаем
        if not request.user.is_authenticated:
            return None
        
        # Если это не админ или суперадмин, пропускаем
        if not (request.user.is_staff or request.user.is_superuser):
            return None
        
        # Получаем объект 2FA
        two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(request.user)
        
        # Если 2FA не обязательна, пропускаем
        if not TwoFactorService.is_required_for_user(request.user):
            return None
        
        # Если 2FA не включена, пропускаем
        if not two_factor_auth.is_enabled:
            return None
        
        # Проверяем время последней верификации 2FA
        last_verification = request.session.get('2fa_verified_at')
        if last_verification:
            from datetime import datetime, timedelta
            try:
                last_verification_time = datetime.fromisoformat(last_verification)
                # Если прошло больше 8 часов, требуем повторную верификацию
                if datetime.now() - last_verification_time > timedelta(hours=8):
                    request.session.pop('2fa_verified', None)
                    request.session.pop('2fa_verified_at', None)
                    return redirect('2fa_admin_verify')
            except (ValueError, TypeError):
                # Если время некорректное, очищаем сессию
                request.session.pop('2fa_verified', None)
                request.session.pop('2fa_verified_at', None)
        
        return None 