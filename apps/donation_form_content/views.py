from rest_framework.views import APIView
from rest_framework.response import Response
from .models import DonationFormContent
from .serializers import DonationFormContentSerializer

class DonationFormContentView(APIView):
    def get(self, request):
        lang = request.query_params.get('lang', 'ru')
        instance = DonationFormContent.objects.first()
        if not instance:
            return Response({})
        
        data = {
            'title': getattr(instance, f'title_{lang}', None) or instance.title,
            'description': getattr(instance, f'description_{lang}', None) or instance.description,
            'button_text': getattr(instance, f'button_text_{lang}', None) or instance.button_text,
        }
        return Response(data)