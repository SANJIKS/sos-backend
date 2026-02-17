"""
Views для работы с локализацией
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import translation
from apps.common.utils.localization import get_available_languages, get_default_language


@api_view(['GET'])
@permission_classes([AllowAny])
def get_supported_languages(request):
    """
    Получить список поддерживаемых языков
    """
    languages = get_available_languages()
    return Response({
        'languages': languages,
        'default_language': get_default_language(),
        'current_language': translation.get_language()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_localization_info(request):
    """
    Получить информацию о локализации
    """
    return Response({
        'current_language': translation.get_language(),
        'supported_languages': get_available_languages(),
        'default_language': get_default_language(),
        'language_detection': {
            'from_header': request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            'from_param': request.GET.get('lang', ''),
        }
    })
