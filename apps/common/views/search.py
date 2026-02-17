"""
Общий поиск по всему сайту
"""
from rest_framework import status
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# Импорты всех моделей для поиска
from apps.news.models import News
from apps.programs.models import Program
from apps.success_stories.models import SuccessStory
from apps.timeline.models import TimelineEvent
from apps.principles.models import Principle
from apps.impact_results.models import ImpactResult
from apps.partners.models import Partner
from apps.locations.models import MapPoint
from apps.faq.models import FAQ
from apps.vacancies.models import Vacancy
from apps.social_networks.models import SocialNetwork
from apps.donation_options.models import DonationOption

# Импорты ViewSet'ов для определения lookup_field
from apps.news.views import NewsViewSet
from apps.programs.views import ProgramViewSet
from apps.success_stories.views import SuccessStoryViewSet
from apps.timeline.views import TimelineEventViewSet
from apps.principles.views import PrincipleViewSet
from apps.impact_results.views import ImpactResultViewSet
from apps.partners.views import PartnerListView
from apps.locations.views import MapPointViewSet
from apps.faq.views import FAQAPIView
from apps.vacancies.views import VacancyListView
from apps.social_networks.views import SocialNetworkViewSet
from apps.donation_options.views import DonationOptionViewSet


def get_lookup_field_from_viewset(model_type):
    """
    Определяет правильный lookup_field для модели на основе ViewSet
    """
    viewset_mapping = {
        'news': NewsViewSet,
        'programs': ProgramViewSet,
        'stories': SuccessStoryViewSet,
        'timeline': TimelineEventViewSet,
        'principles': PrincipleViewSet,
        'impact': ImpactResultViewSet,
        'partners': PartnerListView,
        'locations': MapPointViewSet,
        'faq': FAQAPIView,
        'vacancies': VacancyListView,
        'social': SocialNetworkViewSet,
        'donations': DonationOptionViewSet,
    }
    
    viewset_class = viewset_mapping.get(model_type)
    if not viewset_class:
        return 'uuid'  # По умолчанию используем uuid
    
    # Получаем lookup_field из ViewSet
    lookup_field = getattr(viewset_class, 'lookup_field', 'uuid')
    return lookup_field


def highlight_search_terms(text, query, max_length=200):
    """
    Подсвечивает найденные слова в тексте
    """
    if not text or not query:
        return text
    
    import re
    
    # Ограничиваем длину текста
    if len(text) > max_length:
        text = text[:max_length] + '...'
    
    # Создаем паттерн для поиска (игнорируем регистр)
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    
    # Подсвечиваем найденные слова
    highlighted_text = pattern.sub(f'<mark>{query}</mark>', text)
    
    return highlighted_text


def calculate_relevance_score(obj, query, fields):
    """
    Вычисляет релевантность результата поиска
    """
    score = 0
    query_lower = query.lower()
    
    for field in fields:
        field_value = getattr(obj, field, '')
        if field_value:
            field_lower = field_value.lower()
            # Подсчитываем количество вхождений
            count = field_lower.count(query_lower)
            if count > 0:
                # Бонус за точное совпадение в начале
                if field_lower.startswith(query_lower):
                    score += count * 3
                # Бонус за совпадение в заголовке
                elif field in ['title', 'name', 'question']:
                    score += count * 2
                else:
                    score += count
    
    return min(score, 10)  # Нормализуем до 10


def build_full_url(request, obj, url_field, url_prefix, model_type):
    """
    Строит полный URL для объекта с правильным идентификатором
    """
    # Базовый URL фронтенда
    frontend_base_url = "https://sos-nomadpro.vercel.app"
    
    # Получаем язык из запроса (по умолчанию 'ru')
    lang = request.GET.get('lang', 'ru')
    
    # Получаем идентификатор объекта
    identifier = None
    
    # Проверяем, существует ли поле и не пустое ли оно
    if hasattr(obj, url_field):
        field_value = getattr(obj, url_field, None)
        # Проверяем, что значение не None и не пустая строка
        if field_value is not None and str(field_value).strip():
            identifier = field_value
    
    # Если нет uuid/slug или поле пустое, используем id
    if not identifier:
        if hasattr(obj, 'id'):
            identifier = obj.id
        else:
            # Если нет id, используем pk
            identifier = obj.pk
    
    # Маппинг типов контента на URL пути фронтенда
    frontend_paths = {
        'news': 'news',
        'programs': 'programs', 
        'stories': 'success-stories',
        'timeline': 'timeline',
        'principles': 'principles',
        'impact': 'impact',
        'partners': 'partners',
        'locations': 'locations',
        'faq': 'faq',
        'vacancies': 'vacancies',
        'social': 'social',
        'donations': 'donations'
    }
    
    # Получаем путь для типа контента
    content_path = frontend_paths.get(model_type, model_type)
    
    # Строим полный URL для фронтенда
    full_url = f"{frontend_base_url}/{lang}/{content_path}/{identifier}"
    
    return full_url


@extend_schema(
    tags=['search'],
    summary='Общий поиск по всему сайту',
    description='Поиск по всем моделям сайта с поддержкой фильтрации по типу контента и подсветкой найденных слов',
    parameters=[
        OpenApiParameter(
            name='q',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Поисковый запрос',
            required=True
        ),
        OpenApiParameter(
            name='type',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Тип контента для поиска (news, programs, stories, timeline, principles, impact, partners, locations, faq, vacancies, social, donations)',
            required=False
        ),
        OpenApiParameter(
            name='limit',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Количество результатов (по умолчанию 20, максимум 100)',
            required=False
        ),
        OpenApiParameter(
            name='lang',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Язык для генерации URL (по умолчанию ru)',
            required=False
        ),
    ],
    responses={
        200: {
            'description': 'Результаты поиска с подсветкой',
            'content': {
                'application/json': {
                    'example': {
                        'query': 'Они',
                        'total_results': 15,
                        'results': [
                            {
                                'id': 1,
                                'type': 'news',
                                'title': 'Новости об образовании',
                                'title_highlighted': 'Новости об образовании',
                                'description': 'Описание новости...',
                                'description_highlighted': 'Описание новости...',
                                'url': 'https://sos-nomadpro.vercel.app/ru/news/obrazovanie-news',
                                'created_at': '2024-01-01T00:00:00Z',
                                'relevance_score': 0.85
                            }
                        ]
                    }
                }
            }
        }
    }
)
class GlobalSearchViewSet(ReadOnlyModelViewSet):
    """
    ViewSet для общего поиска по всему сайту
    """
    permission_classes = [AllowAny]
    queryset = []
    
    def get_queryset(self):
        """
        Возвращает пустой queryset, так как поиск выполняется в custom action
        """
        return []
    
    def list(self, request):
        """
        Общий поиск по всему сайту
        """
        query = request.GET.get('q', '').strip()
        content_type = request.GET.get('type', '').strip()
        limit = min(int(request.GET.get('limit', 20)), 100)
        
        if not query:
            return Response({
                'error': 'Поисковый запрос не может быть пустым'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Словарь моделей для поиска с автоматическим определением lookup_field
        search_models = {
            'news': {
                'model': News,
                'fields': ['title', 'title_kg', 'title_en', 'content', 'content_kg', 'content_en', 'excerpt', 'excerpt_kg', 'excerpt_en'],
                'filter': {'status': 'published', 'published_at__lte': timezone.now()},
                'url_prefix': '/api/v1/news/'
            },
            'programs': {
                'model': Program,
                'fields': ['title', 'description', 'short_description', 'content', 'target_audience', 'author_name', 'author_title', 'quote'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/programs/'
            },
            'stories': {
                'model': SuccessStory,
                'fields': ['title', 'quote_text', 'author_name', 'author_position', 'description'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/success-stories/stories/'
            },
            'timeline': {
                'model': TimelineEvent,
                'fields': ['title', 'description', 'location', 'participants', 'impact'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/timeline/'
            },
            'principles': {
                'model': Principle,
                'fields': ['title', 'subtitle', 'description', 'key_points', 'impact'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/principles/'
            },
            'impact': {
                'model': ImpactResult,
                'fields': ['title', 'description', 'detailed_description', 'source'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/impact-results/'
            },
            'partners': {
                'model': Partner,
                'fields': ['name', 'name_kg', 'name_en'],
                'filter': {},
                'url_prefix': '/api/v1/partners/'
            },
            'locations': {
                'model': MapPoint,
                'fields': ['name', 'name_kg', 'name_en', 'description', 'description_kg', 'description_en'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/locations/'
            },
            'faq': {
                'model': FAQ,
                'fields': ['question', 'answer'],
                'filter': {},
                'url_prefix': '/api/v1/faq/'
            },
            'vacancies': {
                'model': Vacancy,
                'fields': ['title', 'description', 'address'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/vacancies/'
            },
            'social': {
                'model': SocialNetwork,
                'fields': ['name', 'description'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/social-networks/'
            },
            'donations': {
                'model': DonationOption,
                'fields': ['title', 'description', 'detailed_description', 'requirements', 'benefits'],
                'filter': {'is_active': True},
                'url_prefix': '/api/v1/donation-options/'
            }
        }
        
        # Если указан конкретный тип, ищем только в нем
        if content_type and content_type in search_models:
            models_to_search = {content_type: search_models[content_type]}
        else:
            models_to_search = search_models
        
        results = []
        total_results = 0
        
        for model_type, model_config in models_to_search.items():
            model = model_config['model']
            fields = model_config['fields']
            filters = model_config['filter']
            url_prefix = model_config['url_prefix']
            
            # Автоматически определяем lookup_field из ViewSet
            url_field = get_lookup_field_from_viewset(model_type)
            
            # Создаем Q объекты для поиска по всем полям
            q_objects = Q()
            for field in fields:
                q_objects |= Q(**{f'{field}__icontains': query})
            
            # Выполняем поиск
            if filters:
                queryset = model.objects.filter(**filters).filter(q_objects)
            else:
                queryset = model.objects.filter(q_objects)
            
            # Дополнительная проверка для новостей - только опубликованные с правильной датой
            if model_type == 'news':
                queryset = queryset.filter(
                    status='published',
                    published_at__lte=timezone.now()
                )
            
            # Фильтрация по is_active=True для всех типов контента
            # Проверяем, есть ли поле is_active в модели
            if hasattr(model._meta, 'get_field'):
                try:
                    model._meta.get_field('is_active')
                    queryset = queryset.filter(is_active=True)
                except:
                    # Поле is_active не существует в этой модели
                    pass
            
            # Ограничиваем количество результатов
            model_results = queryset[:limit]
            
            for obj in model_results:
                try:
                    # Вычисляем релевантность
                    relevance_score = calculate_relevance_score(obj, query, fields)
                    
                    # Получаем полный URL с правильным идентификатором
                    full_url = build_full_url(request, obj, url_field, url_prefix, model_type)
                    
                    # Получаем заголовок (приоритет: основной язык, затем kg, затем en)
                    title = getattr(obj, 'title', '') or getattr(obj, 'name', '') or getattr(obj, 'question', '')
                    if not title:
                        title = getattr(obj, 'title_kg', '') or getattr(obj, 'name_kg', '')
                    if not title:
                        title = getattr(obj, 'title_en', '') or getattr(obj, 'name_en', '')
                    
                    # Получаем описание
                    description = ''
                    for desc_field in ['excerpt', 'short_description', 'description', 'content']:
                        desc_value = getattr(obj, desc_field, '')
                        if desc_value:
                            description = desc_value
                            break
                    
                    # Создаем подсвеченные версии
                    title_highlighted = highlight_search_terms(title, query, 100)
                    description_highlighted = highlight_search_terms(description, query, 200)
                    
                    result = {
                        'type': model_type,
                        'title': title,
                        'title_highlighted': title_highlighted,
                        'description': description,
                        'description_highlighted': description_highlighted,
                        'url': full_url,
                        'created_at': obj.created_at.isoformat() if hasattr(obj, 'created_at') else None,
                        'relevance_score': relevance_score
                    }
                    
                    results.append(result)
                    total_results += 1
                    
                except Exception as e:
                    # Логируем ошибку, но продолжаем обработку других объектов
                    print(f"Ошибка при обработке объекта {obj} типа {model_type}: {e}")
                    continue
        
        # Сортируем по релевантности
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Ограничиваем общее количество результатов
        results = results[:limit]
        
        return Response({
            'query': query,
            'total_results': len(results),
            'results': results
        })