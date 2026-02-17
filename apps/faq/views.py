from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema
from apps.faq.models import FAQ
from apps.faq.serializers import FAQSerializer


@extend_schema(
    summary="Получить список FAQ",
    description="Возвращает список часто задаваемых вопросов, отсортированных по номеру",
    tags=['faq']
)
class FAQAPIView(ListAPIView):
    """API для получения списка часто задаваемых вопросов"""
    serializer_class = FAQSerializer

    def get_queryset(self):
        return FAQ.objects.all().order_by('number_of_questions')
