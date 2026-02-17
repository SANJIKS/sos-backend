from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required


@require_http_methods(["GET", "POST"])
@login_required
def custom_logout(request):
    """Безопасный кастомный logout с очисткой 2FA cookies"""
    print(f"DEBUG: Custom logout called for user {request.user.email}")
    
    # Очищаем все 2FA данные из сессии
    request.session.pop('2fa_verified', None)
    request.session.pop('2fa_verified_at', None)
    request.session.pop('2fa_just_verified', None)
    
    # Очищаем 2FA cookies
    response = redirect('admin:login')
    response.delete_cookie('2fa_verified')
    response.delete_cookie('2fa_verified_at')
    
    # Выполняем стандартный logout
    logout(request)
    
    # Добавляем заголовки безопасности
    response['X-Frame-Options'] = 'DENY'
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-XSS-Protection'] = '1; mode=block'
    
    print(f"DEBUG: Custom logout completed, redirecting to admin:login")
    messages.success(request, "Вы успешно вышли из системы.")
    return response 