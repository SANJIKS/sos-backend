from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.urls import reverse

from apps.users.services.two_factor import (
    TwoFactorService,
    TwoFactorCodeService,
    TwoFactorBackupCodeService,
    TwoFactorLogService
)
from apps.users.services.email import send_email


def is_admin_user(user):
    """Проверка, является ли пользователь админом"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(is_admin_user)
def admin_2fa_setup(request):
    """Страница настройки 2FA для админ-панели"""
    
    two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(request.user)
    
    if request.method == 'POST':
        # Включаем 2FA
        two_factor_auth.auth_method = 'email'
        two_factor_auth.status = 'enabled'
        two_factor_auth.save()
        
        # Отправляем первый код
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            two_factor_code, code = TwoFactorCodeService.create_email_code(
                two_factor_auth, ip_address, user_agent
            )
            
            # Отправляем email
            send_email(
                subject="Настройка двухфакторной аутентификации",
                message=f"""
                Для завершения настройки двухфакторной аутентификации введите код: {code}
                
                Код действителен в течение 5 минут.
                """,
                recipient_list=[request.user.email]
            )
            
            messages.success(request, "Код подтверждения отправлен на ваш email.")
            return redirect('admin:2fa_verify')
            
        except Exception as e:
            messages.error(request, "Ошибка при отправке кода. Попробуйте позже.")
    
    context = {
        'user': request.user,
        'two_factor_auth': two_factor_auth,
    }
    
    return render(request, 'admin/2fa_setup.html', context)


@login_required
@user_passes_test(is_admin_user)
def admin_2fa_verify(request):
    """Страница проверки 2FA для админ-панели"""
    
    two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(request.user)
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        use_backup_code = request.POST.get('use_backup_code') == 'on'
        
        if not code:
            messages.error(request, "Введите код подтверждения.")
            return render(request, 'admin/2fa_verify.html', {'user': request.user})
        
        # Получаем IP и User-Agent
        ip_address = get_client_ip(request)
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
            # Очищаем старые данные 2FA из сессии
            request.session.pop('2fa_verified', None)
            request.session.pop('2fa_verified_at', None)
            request.session.pop('2fa_just_verified', None)
            
            # Отмечаем 2FA как проверенную в сессии
            request.session['2fa_verified'] = True
            request.session['2fa_verified_at'] = timezone.now().isoformat()
            request.session['2fa_just_verified'] = True  # Временный флаг для middleware
            request.session['last_activity'] = timezone.now().isoformat()  # Обновляем активность
            
            # Принудительно сохраняем сессию
            request.session.modified = True
            request.session.save()
            
            print(f"DEBUG: 2FA verification - User: {request.user.email}, Session set: {request.session.get('2fa_verified')}")
            print(f"DEBUG: 2FA verification - Session keys: {list(request.session.keys())}")
            print(f"DEBUG: 2FA verification - Session data: {dict(request.session)}")
            
            # Проверяем, это AJAX запрос?
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response = JsonResponse({
                    'success': True,
                    'redirect_url': reverse('admin:index')
                })
                response.set_cookie('2fa_verified', 'true', max_age=28800, httponly=True, secure=False)
                return response
            else:
                # Обычный запрос - редирект
                response = redirect('admin:index')
                response.set_cookie('2fa_verified', 'true', max_age=28800, httponly=True, secure=False)
                messages.success(request, "Двухфакторная аутентификация подтверждена.")
                return response
        else:
            messages.error(request, message)
    
    context = {
        'user': request.user,
        'two_factor_auth': two_factor_auth,
        'backup_codes_count': TwoFactorBackupCodeService.get_unused_backup_codes(two_factor_auth),
    }
    
    return render(request, 'admin/2fa_verify.html', context)


@login_required
@user_passes_test(is_admin_user)
def admin_2fa_send_code(request):
    """AJAX endpoint для отправки кода 2FA"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    
    two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(request.user)
    
    if not two_factor_auth.is_enabled:
        return JsonResponse({'error': '2FA не включена'}, status=400)
    
    if two_factor_auth.is_locked:
        return JsonResponse({'error': '2FA заблокирована'}, status=400)
    
    # Получаем IP и User-Agent
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    try:
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
            recipient_list=[request.user.email]
        )
        
        return JsonResponse({'success': True, 'message': 'Код отправлен на email'})
        
    except Exception as e:
        return JsonResponse({'error': 'Ошибка при отправке кода'}, status=500)


@login_required
@user_passes_test(is_admin_user)
def admin_2fa_backup_codes(request):
    """Страница для генерации резервных кодов"""
    
    two_factor_auth = TwoFactorService.get_or_create_two_factor_auth(request.user)
    
    if not two_factor_auth.is_enabled:
        messages.error(request, "2FA должна быть включена для генерации резервных кодов.")
        return redirect('admin:2fa_setup')
    
    if request.method == 'POST':
        count = int(request.POST.get('count', 10))
        
        try:
            backup_codes_data = TwoFactorBackupCodeService.generate_backup_codes(two_factor_auth, count)
            codes = [code for _, code in backup_codes_data]
            
            context = {
                'user': request.user,
                'two_factor_auth': two_factor_auth,
                'backup_codes': codes,
                'show_codes': True,
            }
            
            messages.success(request, f"Сгенерировано {count} резервных кодов.")
            return render(request, 'admin/2fa_backup_codes.html', context)
            
        except Exception as e:
            messages.error(request, "Ошибка при генерации резервных кодов.")
    
    context = {
        'user': request.user,
        'two_factor_auth': two_factor_auth,
        'backup_codes_count': TwoFactorBackupCodeService.get_unused_backup_codes(two_factor_auth),
    }
    
    return render(request, 'admin/2fa_backup_codes.html', context)


def get_client_ip(request):
    """Получение IP адреса клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip 