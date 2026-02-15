"""
Context processors for admin dashboard
"""
from django.utils import timezone
from bookings.models import Booking, User, Room


def admin_dashboard_stats(request):
    """
    Dodaje statystyki do kontekstu admin dashboard
    """
    # Only for admin pages
    if not request.path.startswith('/admin'):
        return {}

    now = timezone.now()
    today = now.date()

    context = {
        'total_bookings': Booking.objects.count(),
        'total_users': User.objects.count(),
        'total_rooms': Room.objects.filter(is_active=True).count(),
        'active_bookings': Booking.objects.filter(
            start_time__date=today,
            end_time__gte=now
        ).exclude(status='cancelled').count(),
    }

    # Dodaj dane dla wyszukiwania (tylko na stronie głównej dashboardu)
    if request.path == '/admin/' or request.path == '/admin':
        context['recent_bookings'] = Booking.objects.select_related('room', 'user').order_by('-created_at')[:20]
        context['all_users'] = User.objects.all()[:20]
        context['all_rooms'] = Room.objects.filter(is_active=True)[:20]

    return context

