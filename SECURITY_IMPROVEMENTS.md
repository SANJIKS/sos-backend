# 🔒 План улучшения безопасности проекта SOS-KG

## 📊 Текущее состояние безопасности

### ✅ Что уже хорошо настроено:
- 2FA для админки
- JWT аутентификация
- CSRF защита
- XSS защита (SECURE_BROWSER_XSS_FILTER)
- Content-Type sniffing защита
- X-Frame-Options: DENY
- HSTS настройки
- Переменные окружения для секретов

### ⚠️ Критические проблемы безопасности:

## 🚨 КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ

### 1. **HTTPS и SSL (КРИТИЧНО)**
```python
# В production.py раскомментировать:
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### 2. **CORS настройки (КРИТИЧНО)**
```python
# Слишком открытые CORS настройки
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # Только для разработки
    'http://127.0.0.1:3000', # Только для разработки
    'https://localhost:3000', # Только для разработки
]

# Нужно добавить:
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.sos-kg\.org$",  # Только поддомены sos-kg.org
]
CORS_ALLOW_CREDENTIALS = True  # Опасно с открытыми CORS
```

### 3. **Отсутствует Rate Limiting**
- Нет защиты от брутфорса
- Нет защиты от DDoS
- API endpoints не защищены

### 4. **Логирование безопасности**
- Нет аудита безопасности
- Нет мониторинга подозрительной активности
- Нет логирования попыток взлома

## 🛡️ ПЛАН УЛУЧШЕНИЙ

### Этап 1: Критические исправления (СРОЧНО)

#### 1.1 Настройка HTTPS
```python
# config/settings/production.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

#### 1.2 Улучшение CORS
```python
# config/settings/production.py
CORS_ALLOWED_ORIGINS = [
    'https://sos-kg.org',
    'https://www.sos-kg.org',
    'https://admin.sos-kg.org',
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.sos-kg\.org$",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # КРИТИЧНО!
```

#### 1.3 Добавление Rate Limiting
```python
# Установить django-ratelimit
INSTALLED_APPS = [
    # ...
    'django_ratelimit',
]

# Настройки
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_VIEW = 'apps.common.views.rate_limit_exceeded'
```

### Этап 2: Усиление безопасности

#### 2.1 Безопасность сессий
```python
# config/settings/production.py
SESSION_COOKIE_AGE = 1800  # 30 минут
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
```

#### 2.2 Безопасность паролей
```python
# config/settings/base.py
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Увеличить до 12
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'apps.users.validators.ComplexPasswordValidator',  # Кастомный валидатор
    },
]
```

#### 2.3 Безопасность файлов
```python
# config/settings/production.py
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644
```

### Этап 3: Мониторинг и аудит

#### 3.1 Логирование безопасности
```python
# config/settings/production.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'security': {
            'format': 'SECURITY {levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/app/logs/security.log',
            'formatter': 'security',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

#### 3.2 Middleware для мониторинга
```python
# apps/common/middleware/security.py
class SecurityMonitoringMiddleware:
    def process_request(self, request):
        # Логирование подозрительной активности
        # Блокировка по IP
        # Мониторинг попыток взлома
        pass
```

### Этап 4: Дополнительные меры

#### 4.1 Content Security Policy
```python
# config/settings/production.py
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
```

#### 4.2 Безопасность API
```python
# apps/common/permissions.py
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user
```

#### 4.3 Валидация входных данных
```python
# apps/common/validators.py
class SecurityValidator:
    @staticmethod
    def validate_file_upload(file):
        # Проверка типа файла
        # Проверка размера
        # Сканирование на вирусы
        pass
    
    @staticmethod
    def validate_input(data):
        # Санитизация HTML
        # Проверка на SQL инъекции
        # Проверка на XSS
        pass
```

## 🔧 НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ

### 1. Обновить production.py
### 2. Настроить HTTPS
### 3. Ограничить CORS
### 4. Добавить Rate Limiting
### 5. Настроить логирование безопасности

## 📈 МЕТРИКИ БЕЗОПАСНОСТИ

- Количество неудачных попыток входа
- Количество заблокированных IP
- Время отклика на подозрительную активность
- Покрытие тестами безопасности
- Регулярность обновлений зависимостей

## 🚀 ПРИОРИТЕТЫ

1. **КРИТИЧНО**: HTTPS + CORS + Rate Limiting
2. **ВЫСОКИЙ**: Логирование + Мониторинг
3. **СРЕДНИЙ**: CSP + Валидация
4. **НИЗКИЙ**: Дополнительные меры
