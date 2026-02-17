import secrets
import hashlib
import hmac
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta

from apps.users.models import TwoFactorAuth, TwoFactorCode, TwoFactorBackupCode, TwoFactorLog


class TwoFactorService:
    """Основной сервис для работы с 2FA"""
    
    @staticmethod
    def get_or_create_two_factor_auth(user):
        """Получить или создать объект 2FA для пользователя"""
        two_factor_auth, created = TwoFactorAuth.objects.get_or_create(user=user)
        
        # Если это админ или сотрудник, делаем 2FA обязательной
        if user.is_staff or user.is_superuser:
            two_factor_auth.is_required = True
            if two_factor_auth.status == TwoFactorAuth.Status.DISABLED:
                two_factor_auth.status = TwoFactorAuth.Status.REQUIRED
            two_factor_auth.save()
        
        return two_factor_auth
    
    @staticmethod
    def is_required_for_user(user):
        """Проверка, обязательна ли 2FA для пользователя"""
        if user.is_staff or user.is_superuser:
            return True
        
        # Здесь можно добавить логику для сотрудников SOS
        # Например, проверка по email домену или специальной группе
        return False
    
    @staticmethod
    def generate_code():
        """Генерация 6-значного кода"""
        return str(secrets.randbelow(1000000)).zfill(6)
    
    @staticmethod
    def generate_backup_codes(count=10):
        """Генерация резервных кодов"""
        codes = []
        for _ in range(count):
            # Генерируем 8-значный код с дефисами для удобства
            code = f"{secrets.randbelow(10000):04d}-{secrets.randbelow(10000):04d}"
            codes.append(code)
        return codes
    
    @staticmethod
    def hash_code(code):
        """Хеширование кода для безопасного хранения"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    @staticmethod
    def verify_code_hash(code, code_hash):
        """Проверка хеша кода"""
        return hmac.compare_digest(TwoFactorService.hash_code(code), code_hash)
    
    @staticmethod
    def encrypt_code(code):
        """Шифрование кода"""
        # Временно используем только хеширование для отладки
        return TwoFactorService.hash_code(code)
    
    @staticmethod
    def decrypt_code(encrypted_code):
        """Расшифровка кода"""
        # Временно возвращаем None, так как используем только хеширование
        return None


class TwoFactorCodeService:
    """Сервис для работы с кодами подтверждения"""
    
    @staticmethod
    def create_email_code(two_factor_auth, ip_address=None, user_agent=None):
        """Создание email кода"""
        code = TwoFactorService.generate_code()
        expires_at = timezone.now() + timedelta(minutes=5)  # 5 минут согласно ТЗ
        
        two_factor_code = TwoFactorCode.objects.create(
            two_factor_auth=two_factor_auth,
            code_type=TwoFactorCode.CodeType.EMAIL,
            encrypted_code=TwoFactorService.encrypt_code(code),
            code_hash=TwoFactorService.hash_code(code),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent or ''
        )
        
        # Логируем отправку кода
        TwoFactorLogService.log_action(
            two_factor_auth=two_factor_auth,
            log_type=TwoFactorLog.LogType.CODE_SENT,
            status=TwoFactorLog.Status.SUCCESS,
            description=f"Email код отправлен на {two_factor_auth.user.email}",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return two_factor_code, code
    
    @staticmethod
    def verify_code(two_factor_auth, code, ip_address=None, user_agent=None):
        """Проверка кода"""
        # Получаем активный код
        active_code = TwoFactorCode.objects.filter(
            two_factor_auth=two_factor_auth,
            code_type=TwoFactorCode.CodeType.EMAIL,
            status=TwoFactorCode.Status.PENDING,
            expires_at__gt=timezone.now()
        ).first()
        
        if not active_code:
            TwoFactorLogService.log_action(
                two_factor_auth=two_factor_auth,
                log_type=TwoFactorLog.LogType.CODE_FAILED,
                status=TwoFactorLog.Status.FAILED,
                description="Попытка проверить несуществующий или истекший код",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return False, "Код не найден или истек"
        
        # Проверяем количество попыток
        if active_code.attempts_used >= active_code.max_attempts:
            active_code.status = TwoFactorCode.Status.INVALIDATED
            active_code.save()
            
            TwoFactorLogService.log_action(
                two_factor_auth=two_factor_auth,
                log_type=TwoFactorLog.LogType.CODE_FAILED,
                status=TwoFactorLog.Status.FAILED,
                description="Превышено количество попыток ввода кода",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return False, "Превышено количество попыток"
        
        # Проверяем код
        if TwoFactorService.verify_code_hash(code, active_code.code_hash):
            # Код верный
            active_code.mark_as_used()
            two_factor_auth.reset_failed_attempts()
            two_factor_auth.last_used_at = timezone.now()
            two_factor_auth.save()
            
            TwoFactorLogService.log_action(
                two_factor_auth=two_factor_auth,
                log_type=TwoFactorLog.LogType.CODE_VERIFIED,
                status=TwoFactorLog.Status.SUCCESS,
                description="Код успешно подтвержден",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return True, "Код подтвержден"
        else:
            # Код неверный
            active_code.increment_attempts()
            two_factor_auth.increment_failed_attempts()
            
            TwoFactorLogService.log_action(
                two_factor_auth=two_factor_auth,
                log_type=TwoFactorLog.LogType.CODE_FAILED,
                status=TwoFactorLog.Status.FAILED,
                description="Введен неверный код",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return False, "Неверный код"
    
    @staticmethod
    def verify_backup_code(two_factor_auth, code, ip_address=None, user_agent=None):
        """Проверка резервного кода"""
        backup_code = TwoFactorBackupCode.objects.filter(
            two_factor_auth=two_factor_auth,
            is_used=False
        ).first()
        
        if not backup_code:
            return False, "Резервные коды не настроены"
        
        if TwoFactorService.verify_code_hash(code, backup_code.code_hash):
            backup_code.mark_as_used()
            two_factor_auth.reset_failed_attempts()
            two_factor_auth.last_used_at = timezone.now()
            two_factor_auth.save()
            
            TwoFactorLogService.log_action(
                two_factor_auth=two_factor_auth,
                log_type=TwoFactorLog.LogType.BACKUP_CODE_USED,
                status=TwoFactorLog.Status.SUCCESS,
                description="Использован резервный код",
                ip_address=ip_address,
                user_agent=user_agent
            )
            return True, "Резервный код подтвержден"
        else:
            return False, "Неверный резервный код"
    
    @staticmethod
    def cleanup_expired_codes():
        """Очистка истекших кодов"""
        expired_codes = TwoFactorCode.objects.filter(
            status=TwoFactorCode.Status.PENDING,
            expires_at__lt=timezone.now()
        )
        
        for code in expired_codes:
            code.mark_as_expired()
        
        return expired_codes.count()


class TwoFactorBackupCodeService:
    """Сервис для работы с резервными кодами"""
    
    @staticmethod
    def generate_backup_codes(two_factor_auth, count=10):
        """Генерация новых резервных кодов"""
        # Удаляем старые коды
        TwoFactorBackupCode.objects.filter(two_factor_auth=two_factor_auth).delete()
        
        # Генерируем новые
        codes = TwoFactorService.generate_backup_codes(count)
        backup_codes = []
        
        for code in codes:
            backup_code = TwoFactorBackupCode.objects.create(
                two_factor_auth=two_factor_auth,
                code_hash=TwoFactorService.hash_code(code)
            )
            backup_codes.append((backup_code, code))
        
        two_factor_auth.backup_codes_enabled = True
        two_factor_auth.save()
        
        return backup_codes
    
    @staticmethod
    def get_unused_backup_codes(two_factor_auth):
        """Получение неиспользованных резервных кодов"""
        return TwoFactorBackupCode.objects.filter(
            two_factor_auth=two_factor_auth,
            is_used=False
        ).count()


class TwoFactorLogService:
    """Сервис для логирования действий 2FA"""
    
    @staticmethod
    def log_action(two_factor_auth, log_type, status, description, ip_address=None, user_agent=None):
        """Логирование действия"""
        return TwoFactorLog.objects.create(
            two_factor_auth=two_factor_auth,
            log_type=log_type,
            status=status,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent or ''
        )
    
    @staticmethod
    def get_user_logs(two_factor_auth, limit=50):
        """Получение логов пользователя"""
        return TwoFactorLog.objects.filter(
            two_factor_auth=two_factor_auth
        ).order_by('-created_at')[:limit]
    
    @staticmethod
    def cleanup_old_logs(days=90):
        """Очистка старых логов"""
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = TwoFactorLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        return deleted_count


class TwoFactorRateLimitService:
    """Сервис для ограничения частоты запросов"""
    
    @staticmethod
    def is_rate_limited(user, action_type, max_attempts=3, window_minutes=60):
        """Проверка ограничения частоты"""
        cache_key = f"2fa_rate_limit:{user.id}:{action_type}"
        attempts = cache.get(cache_key, 0)
        
        if attempts >= max_attempts:
            return True
        
        cache.set(cache_key, attempts + 1, window_minutes * 60)
        return False
    
    @staticmethod
    def reset_rate_limit(user, action_type):
        """Сброс ограничения частоты"""
        cache_key = f"2fa_rate_limit:{user.id}:{action_type}"
        cache.delete(cache_key) 