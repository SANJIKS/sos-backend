"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

@csrf_exempt
def health_check(request):
    """Health check endpoint for load balancers and monitoring"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': '2025-08-25T20:30:00Z'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/v1/auth/', include('apps.users.auth_urls')),
    path('api/v1/users/', include('apps.users.user_urls')),
    path('api/v1/donations/', include('apps.donations.urls')),
    path('api/v1/donors/', include('apps.donors.urls')),
    path('api/v1/news/', include('apps.news.urls')),
    path('api/v1/contacts/', include('apps.contacts.urls')),
    path('api/v1/partners/', include('apps.partners.urls')),
    path('api/v1/vacancies/', include('apps.vacancies.urls')),
    path('api/v1/faq/', include('apps.faq.urls')),
    path('api/v1/locations/', include('apps.locations.urls')),
    path('api/v1/success-stories/', include('apps.success_stories.urls')),
    path('api/v1/programs/', include('apps.programs.urls')),
    path('api/v1/timeline/', include('apps.timeline.urls')),
    path('api/v1/principles/', include('apps.principles.urls')),
    path('api/v1/impact-results/', include('apps.impact_results.urls')),
    path('api/v1/donation-options/', include('apps.donation_options.urls')),
    path('api/v1/social-networks/', include('apps.social_networks.urls')),
    path('api/v1/banking-requisites/', include('apps.banking_requisites.urls')),
    path('api/v1/digital-campaigns/', include('apps.digital_campaigns.urls')),
    path('api/v1/feedback/', include('apps.feedback.urls')),
    path('api/v1/qrcode/', include('apps.qrcode.urls')),
    path('api/v1/common/', include('apps.common.urls')),

    
    path('health/', health_check, name='health_check'),
    
    # API Documentation
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui-root'),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
