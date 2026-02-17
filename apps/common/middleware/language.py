"""
Middleware для автоматического определения языка
"""
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class LanguageMiddleware(MiddlewareMixin):
    """
    Middleware для автоматического определения языка
    """
    
    def process_request(self, request):
        # Получаем язык из заголовка Accept-Language
        language = self.get_language_from_request(request)
        
        # Активируем язык
        translation.activate(language)
        request.LANGUAGE_CODE = language
        
        return None
    
    def get_language_from_request(self, request):
        """
        Определение языка из запроса
        """
        # Проверяем параметр ?lang=
        if 'lang' in request.GET:
            lang = request.GET['lang']
            if lang in [code for code, _ in settings.LANGUAGES]:
                return lang
        
        # Проверяем заголовок Accept-Language
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        
        # Парсим заголовок Accept-Language более точно
        if accept_language:
            # Разделяем по запятой и берем первый язык
            languages = [lang.strip().split(';')[0].split('-')[0] for lang in accept_language.split(',')]
            for lang in languages:
                if lang in [code for code, _ in settings.LANGUAGES]:
                    return lang
        
        # Возвращаем язык по умолчанию
        return settings.LANGUAGE_CODE
