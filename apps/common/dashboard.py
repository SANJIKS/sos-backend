"""
Dashboard callback для Django Unfold
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

@staff_member_required
def dashboard_callback(request):
    """
    Кастомный дашборд для SOS Children's Villages
    """
    from apps.news.models import News
    from apps.programs.models import Program
    from apps.contacts.models import Contact
    from apps.donations.models import Donation
    from apps.users.models import User
    
    # Статистика за последние 30 дней
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    context = {
        'stats': {
            'total_users': User.objects.count(),
            'active_programs': Program.objects.filter(is_active=True).count(),
            'recent_news': News.objects.filter(created_at__gte=thirty_days_ago).count(),
            'pending_contacts': Contact.objects.filter(status='new').count(),
            'total_donations': Donation.objects.count(),
        },
        'recent_activities': {
            'new_contacts': Contact.objects.filter(
                created_at__gte=thirty_days_ago
            ).order_by('-created_at')[:5],
            'recent_programs': Program.objects.filter(
                created_at__gte=thirty_days_ago
            ).order_by('-created_at')[:5],
        }
    }
    
    return render(request, 'admin/dashboard.html', context)
