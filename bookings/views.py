from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.db import transaction
from .models import Room, User, Booking, Equipment, Notification
import json
from datetime import datetime, timedelta
import uuid
from django.db.models import Q, Count, Sum, F
from django.db.models.functions import TruncDate, ExtractHour, ExtractWeekDay
import io

# Imports for reports
REPORTLAB_AVAILABLE = False
FONT_NAME = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import inch

    # Register Unicode fonts (Polish chars) for ReportLab
    try:
        dejavu_regular = font_manager.findfont('DejaVu Sans')
        dejavu_bold = font_manager.findfont('DejaVu Sans:bold')

        pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_regular))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', dejavu_bold))
        FONT_NAME = 'DejaVuSans'
        FONT_BOLD = 'DejaVuSans-Bold'
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
            FONT_NAME = 'Arial'
            FONT_BOLD = 'Arial-Bold'
        except Exception:
            FONT_NAME = 'Helvetica'
            FONT_BOLD = 'Helvetica-Bold'

    REPORTLAB_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    REPORTLAB_AVAILABLE = False


def summaries_page(request):
    return render(request, "summaries.html")


def _safe_localtime(dt):
    if dt is None:
        return None
    if timezone.is_naive(dt):
        try:
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        except Exception:
            return dt
    try:
        return timezone.localtime(dt)
    except Exception:
        return dt


def _summaries_time_range(request):
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')

    start_date = parse_date(start_str) if start_str else None
    end_date = parse_date(end_str) if end_str else None

    now = timezone.localtime(timezone.now())
    if not end_date:
        end_date = now.date()
    if not start_date:
        start_date = (end_date - timedelta(days=30))

    start_dt = timezone.make_aware(
        datetime.combine(start_date, datetime.min.time()),
        timezone.get_current_timezone(),
    )
    end_dt = timezone.make_aware(
        datetime.combine(end_date, datetime.max.time()),
        timezone.get_current_timezone(),
    )
    return start_date, end_date, start_dt, end_dt


def _filtered_bookings_qs(request):
    start_date, end_date, start_dt, end_dt = _summaries_time_range(request)

    qs = Booking.objects.select_related('room', 'user').filter(
        start_time__gte=start_dt,
        start_time__lte=end_dt,
    )

    room_id = request.GET.get('room_id')
    if room_id:
        room_ids = [x.strip() for x in str(room_id).split(',') if x.strip()]
        if len(room_ids) == 1:
            qs = qs.filter(room_id=room_ids[0])
        elif room_ids:
            qs = qs.filter(room_id__in=room_ids)

    dept = request.GET.get('dept')
    if dept:
        depts = [x.strip() for x in str(dept).split(',') if x.strip()]
        if len(depts) == 1:
            qs = qs.filter(user__department=depts[0])
        elif depts:
            qs = qs.filter(user__department__in=depts)

    status = request.GET.get('status')
    if status:
        statuses = [x.strip() for x in str(status).split(',') if x.strip()]
        if len(statuses) == 1:
            qs = qs.filter(status=statuses[0])
        elif statuses:
            qs = qs.filter(status__in=statuses)

    return qs, (start_date, end_date)


@require_http_methods(["GET"])
def get_summaries_api(request):
    qs, (start_date, end_date) = _filtered_bookings_qs(request)

    rooms_meta = list(Room.objects.filter(is_active=True).values('id', 'name').order_by('name'))
    departments_meta = list(User.objects.exclude(department__isnull=True).exclude(department='').values_list('department', flat=True).distinct().order_by('department'))
    users_meta = list(User.objects.values('id', 'name').order_by('name'))

    total_bookings = qs.count()
    total_hours = sum(b.duration_hours for b in qs)
    cancelled = qs.filter(status='cancelled').count()
    cancel_rate = (cancelled / total_bookings) if total_bookings else 0
    avg_minutes = (total_hours * 60 / total_bookings) if total_bookings else 0
    unique_rooms = qs.values('room_id').distinct().count()
    unique_users = qs.values('user_id').distinct().count()

    days = []
    cur = start_date
    while cur <= end_date:
        days.append(cur)
        cur += timedelta(days=1)

    trend_map = {d: {'count': 0, 'hours': 0.0} for d in days}
    for b in qs:
        d = _safe_localtime(b.start_time).date()
        if d in trend_map:
            trend_map[d]['count'] += 1
            trend_map[d]['hours'] += float(b.duration_hours)

    trend = [{'date': d.isoformat(), 'count': trend_map[d]['count'], 'hours': round(trend_map[d]['hours'], 2)} for d in days]

    # Weekly compare (this week vs previous week; based on end_date)
    end_weekday = end_date.isoweekday()  # 1..7
    week_start = end_date - timedelta(days=end_weekday - 1)
    prev_week_start = week_start - timedelta(days=7)
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    prev_week_days = [prev_week_start + timedelta(days=i) for i in range(7)]

    this_week_counts = {d: 0 for d in week_days}
    prev_week_counts = {d: 0 for d in prev_week_days}
    for b in qs:
        d = _safe_localtime(b.start_time).date()
        if d in this_week_counts:
            this_week_counts[d] += 1
        if d in prev_week_counts:
            prev_week_counts[d] += 1

    weekdays_labels = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd']
    weekly_compare = {
        'labels': weekdays_labels,
        'this_week_dates': [d.isoformat() for d in week_days],
        'prev_week_dates': [d.isoformat() for d in prev_week_days],
        'this_week': [this_week_counts[d] for d in week_days],
        'prev_week': [prev_week_counts[d] for d in prev_week_days],
    }

    # Reservation stats: daily/weekly/monthly counts
    stats_daily = [{'label': d.isoformat(), 'value': trend_map[d]['count']} for d in days]

    weekly_map = {}
    monthly_map = {}
    for b in qs:
        d = _safe_localtime(b.start_time).date()
        iso_year, iso_week, _ = d.isocalendar()
        wk_key = f"{iso_year}-W{iso_week:02d}"
        mo_key = f"{d.year}-{d.month:02d}"
        weekly_map[wk_key] = weekly_map.get(wk_key, 0) + 1
        monthly_map[mo_key] = monthly_map.get(mo_key, 0) + 1

    month_names_pl = [
        'styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec',
        'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'
    ]

    stats_weekly = []
    for k, v in sorted(weekly_map.items(), key=lambda x: x[0]):
        try:
            year_str, week_str = k.split('-W')
            y = int(year_str)
            w = int(week_str)
            wk_start = date.fromisocalendar(y, w, 1)
            wk_end = date.fromisocalendar(y, w, 7)
            pretty = f"{wk_start.strftime('%d.%m')}–{wk_end.strftime('%d.%m')}"
            stats_weekly.append({'label': k, 'label_pretty': pretty, 'start': wk_start.isoformat(), 'end': wk_end.isoformat(), 'value': v})
        except Exception:
            stats_weekly.append({'label': k, 'label_pretty': k, 'value': v})

    stats_monthly = []
    for k, v in sorted(monthly_map.items(), key=lambda x: x[0]):
        try:
            y_str, m_str = k.split('-')
            y = int(y_str)
            m = int(m_str)
            m_start = date(y, m, 1)
            if m == 12:
                m_end = date(y + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = date(y, m + 1, 1) - timedelta(days=1)
            pretty = f"{month_names_pl[m - 1]} {y}"
            stats_monthly.append({'label': k, 'label_pretty': pretty, 'start': m_start.isoformat(), 'end': m_end.isoformat(), 'value': v})
        except Exception:
            stats_monthly.append({'label': k, 'label_pretty': k, 'value': v})

    wh_start, wh_end = 8, 18
    possible_per_day = max(0, wh_end - wh_start)
    num_days = max(1, (end_date - start_date).days + 1)

    room_hours = {}
    room_counts = {}
    for b in qs:
        rid = b.room_id
        room_hours[rid] = room_hours.get(rid, 0.0) + float(b.duration_hours)
        room_counts[rid] = room_counts.get(rid, 0) + 1

    room_id_to_name = {r['id']: r['name'] for r in rooms_meta}
    top_room_items = []
    for rid, hrs in room_hours.items():
        util = (hrs / (num_days * possible_per_day) * 100) if possible_per_day else 0
        top_room_items.append({
            'room_id': rid, 
            'room': room_id_to_name.get(rid, str(rid)), 
            'hours': round(hrs, 2), 
            'utilization': round(util, 1),
            'count': room_counts.get(rid, 0)
        })
    top_room_items.sort(key=lambda x: x['hours'], reverse=True)
    top_rooms = top_room_items[:10]

    dept_counts = {}
    dept_hours = {}
    for b in qs:
        d = b.user.department or 'Brak departamentu'
        dept_counts[d] = dept_counts.get(d, 0) + 1
        dept_hours[d] = dept_hours.get(d, 0.0) + float(b.duration_hours)

    dept_items = []
    for d, c in dept_counts.items():
        dept_items.append({
            'dept': d,
            'count': c,
            'hours': round(dept_hours.get(d, 0.0), 2),
        })
    dept_items.sort(key=lambda x: x['hours'], reverse=True)
    dept_items = dept_items[:12]

    treemap = [{'name': x['room'], 'value': x['hours']} for x in top_room_items if x['hours'] > 0]

    scatter = []
    for b in qs[:500]:
        attendees = int(b.attendees_count or 0)
        minutes = int(round(float(b.duration_hours) * 60))
        scatter.append([attendees, minutes, f"{b.room.name} · {b.user.name}"])

    bins = [(0, 30), (30, 60), (60, 90), (90, 120)]
    hist_labels = ['0-30', '30-60', '60-90', '90-120', '120+']
    hist_vals = [0, 0, 0, 0, 0]
    for b in qs:
        minutes = float(b.duration_hours) * 60
        placed = False
        for i, (a, z) in enumerate(bins):
            if a <= minutes < z:
                hist_vals[i] += 1
                placed = True
                break
        if not placed:
            if minutes >= 120:
                hist_vals[4] += 1

    user_counts = {}
    user_hours = {}
    for b in qs:
        user_counts[b.user_id] = user_counts.get(b.user_id, 0) + 1
        user_hours[b.user_id] = user_hours.get(b.user_id, 0.0) + float(b.duration_hours)
    user_id_to_name = {u['id']: u['name'] for u in users_meta}
    top_users = []
    for uid, c in user_counts.items():
        top_users.append({
            'user_id': uid,
            'user': user_id_to_name.get(uid, str(uid)),
            'count': c,
            'hours': round(user_hours.get(uid, 0.0), 2),
        })
    top_users.sort(key=lambda x: x['count'], reverse=True)
    top_users = top_users[:10]

    return JsonResponse({
        'meta': {
            'rooms': rooms_meta,
            'departments': departments_meta,
            'users': users_meta,
        },
        'kpi': {
            'total_bookings': total_bookings,
            'total_hours': round(total_hours, 2),
            'cancel_rate': cancel_rate,
            'avg_minutes': round(avg_minutes, 2),
            'unique_rooms': unique_rooms,
            'unique_users': unique_users,
        },
        'trend': trend,
        'weekly_compare': weekly_compare,
        'reservation_stats': {
            'daily': stats_daily,
            'weekly': stats_weekly,
            'monthly': stats_monthly,
        },
        'top_rooms': top_rooms,
        'dept_overview': dept_items,
        'treemap': treemap,
        'scatter': scatter,
        'histogram': {
            'labels': hist_labels,
            'values': hist_vals,
        },
        'top_users': top_users,
    })


@require_http_methods(["GET"])
def get_summaries_bookings_api(request):
    qs, _ = _filtered_bookings_qs(request)

    date_str = request.GET.get('date')
    if date_str:
        d = parse_date(date_str)
        if d:
            start_dt = timezone.make_aware(
                datetime.combine(d, datetime.min.time()),
                timezone.get_current_timezone(),
            )
            end_dt = timezone.make_aware(
                datetime.combine(d, datetime.max.time()),
                timezone.get_current_timezone(),
            )
            qs = qs.filter(start_time__gte=start_dt, start_time__lte=end_dt)

    weekday = request.GET.get('weekday')
    hour = request.GET.get('hour')
    if weekday is not None and hour is not None:
        try:
            w = int(weekday)
            h = int(hour)
            matched_ids = []
            for b in qs:
                lt = _safe_localtime(b.start_time)
                if (lt.isoweekday() - 1) == w and lt.hour == h:
                    matched_ids.append(b.id)
            qs = qs.filter(id__in=matched_ids)
        except Exception:
            pass

    user_id = request.GET.get('user_id')
    if user_id:
        qs = qs.filter(user_id=user_id)

    # Zwiększamy limit do 5000 aby umożliwić filtrowanie po wszystkich rezerwacjach
    qs = qs.order_by('-start_time')[:5000]

    items = []
    for b in qs:
        lt_s = _safe_localtime(b.start_time)
        lt_e = _safe_localtime(b.end_time)
        minutes = int(round(float(b.duration_hours) * 60))
        items.append({
            'id': b.id,
            'start': lt_s.strftime('%Y-%m-%d %H:%M'),
            'end': lt_e.strftime('%Y-%m-%d %H:%M'),
            'room': b.room.name,
            'user': b.user.name,
            'department': b.user.department,
            'title': b.title,
            'status': b.status,
            'attendees': int(b.attendees_count or 0),
            'minutes': minutes,
        })

    return JsonResponse({'bookings': items})

def dashboard(request):
    """Strona główna dashboardu."""
    now = timezone.now()
    today = now.date()

    # Automatyczna aktualizacja statusów rezerwacji
    # Zmień status z "confirmed" na "completed" dla zakończonych rezerwacji
    Booking.objects.filter(
        status="confirmed",
        end_time__lt=now
    ).update(status="completed")

    # Statystyki - pokazują AKTYWNE rezerwacje (przyszłe + dzisiejsze trwające)
    stats = {
        "total_rooms": Room.objects.filter(is_active=True).count(),
        "total_users": User.objects.count(),
        # Aktywne rezerwacje = potwierdzone, które jeszcze się nie zakończyły
        "total_bookings": Booking.objects.filter(
            status="confirmed",
            end_time__gte=now
        ).count(),
        # Rezerwacje dziś = tylko aktywne dzisiejsze (nie zakończone)
        "bookings_today": Booking.objects.filter(
            start_time__date=today,
            end_time__gte=now,
        ).exclude(status="cancelled").count(),
    }

    # Rezerwacje: trwające + następne 30 dni (dla timeline'u)
    # Dodajemy mały margines (30 min), aby rezerwacje które właśnie się kończą nie znikały od razu
    upcoming = Booking.objects.filter(
        end_time__gte=now - timedelta(minutes=30),
        start_time__lte=now + timedelta(days=30),
        status="confirmed",
    ).order_by('start_time')[:100]

    # 20 ostatnich dodanych rezerwacji (dla tabeli "Ostatnie rezerwacje")
    recent_bookings = Booking.objects.all().select_related('room', 'user').order_by('-created_at')[:20]

    top_users = User.objects.annotate(
        booking_count=Count('bookings', filter=~Q(bookings__status='cancelled'))
    ).order_by('-booking_count')[:5]

    month_ago = now - timedelta(days=30)

    # Aktywne sale - tylko te które mają aktywne (przyszłe) rezerwacje
    active_rooms_ids = Booking.objects.filter(
        end_time__gte=now,
        status="confirmed"
    ).values_list('room_id', flat=True).distinct()

    stats['active_rooms'] = Room.objects.filter(
        id__in=active_rooms_ids,
        is_active=True
    ).count()

    room_utilization = []
    active_rooms = Room.objects.filter(is_active=True)

    for room in active_rooms:
        total_seconds = Booking.objects.filter(
            room=room,
            start_time__gte=month_ago,
        ).filter(~Q(status="cancelled")).annotate(
            duration=F('end_time') - F('start_time')
        ).aggregate(total=Sum('duration'))['total']

        total_hours = total_seconds.total_seconds() / 3600 if total_seconds else 0
        max_hours = 176
        utilization = (total_hours / max_hours) * 100 if max_hours else 0

        room_utilization.append({
            "room": room.name,
            "hours": round(total_hours, 1),
            "utilization": round(utilization, 1),
        })

    room_utilization.sort(key=lambda x: x["utilization"], reverse=True)

    department_stats = User.objects.values('department').annotate(
        booking_count=Count('bookings', filter=~Q(bookings__status='cancelled'))
    )

    heatmap_data = Booking.objects.filter(~Q(status="cancelled")).annotate(
        weekday=ExtractWeekDay('start_time'),
        hour=ExtractHour('start_time')
    ).values('weekday', 'hour').annotate(count=Count('id'))

    trend_data = Booking.objects.filter(
        start_time__gte=month_ago,
    ).filter(~Q(status="cancelled")).annotate(
        date=TruncDate('start_time')
    ).values('date').annotate(count=Count('id')).order_by('date')

    # Pobierz WSZYSTKIE nieprzeczytane powiadomienia (dla wszystkich użytkowników)
    # FILTRUJ: tylko te, których czas już nadszedł (created_at <= teraz)
    all_notifications = Notification.objects.filter(
        is_read=False,
        created_at__lte=timezone.now()  # Tylko powiadomienia, których czas już nadszedł
    ).select_related('user').order_by('-created_at')

    # Inteligentne wykrywanie użytkownika (dla dropdown - opcjonalne)
    user_id = request.GET.get('user_id')
    if not user_id:
        user_id = request.session.get('current_user_id', 1)
    else:
        request.session['current_user_id'] = int(user_id)

    user_id = int(user_id)

    return render(request, "dashboard.html", {
        "stats": stats,
        "upcoming": upcoming,
        "recent_bookings": recent_bookings,
        "top_users": top_users,
        "room_utilization": room_utilization,
        "department_stats": department_stats,
        "heatmap_data": heatmap_data,
        "trend_data": trend_data,
        "current_user_id": user_id,
        "all_notifications": all_notifications,  # Wszystkie powiadomienia
        "notifications_count": all_notifications.count(),  # Liczba powiadomień
    })

def notifications_page(request):
    # Opcjonalnie zachowaj user_id dla kompatybilności
    user_id = request.GET.get('user_id')
    if not user_id:
        user_id = request.session.get('current_user_id', 1)
    else:
        request.session['current_user_id'] = int(user_id)

    # Pobierz WSZYSTKIE powiadomienia, których czas już nadszedł
    all_notifications = Notification.objects.filter(
        is_read=False,
        created_at__lte=timezone.now()  # Tylko powiadomienia, których czas już nadszedł
    ).select_related('user').order_by('-created_at')

    return render(request, 'notifications.html', {
        'current_user_id': int(user_id),
        'all_notifications': all_notifications,
        'show_all': True,  # Flaga informująca że pokazujemy wszystkie
    })



def get_notifications_api(request):
    # Zwróć WSZYSTKIE nieprzeczytane powiadomienia dla WSZYSTKICH użytkowników
    # FILTRUJ: tylko te, których czas już nadszedł
    notifications = Notification.objects.filter(
        is_read=False,
        created_at__lte=timezone.now()  # Tylko powiadomienia, których czas już nadszedł
    ).select_related('user').order_by('-created_at')

    return JsonResponse({
        "notifications": [{
            "id": n.id,
            "message": n.message,
            "created_at": n.created_at.isoformat(),
            "is_read": n.is_read,
            "user_name": n.user.name,  # Dodaj nazwę użytkownika
            "user_id": n.user.id,
        } for n in notifications],
        "count": notifications.count()
    })

@csrf_exempt
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.is_read = True
        notification.save()
        return JsonResponse({"message": "Marked as read", "success": True})
    except Notification.DoesNotExist:
        return JsonResponse({"error": "Not found", "success": False}, status=404)

def monthly_report(request):
    if not REPORTLAB_AVAILABLE:
        return HttpResponse("Reportlab lub matplotlib nie zainstalowany", status=501)

    month_param = request.GET.get("month")
    if not month_param:
        return JsonResponse({"error": "Wymagany parametr miesiąca"}, status=400)

    try:
        year, month = map(int, month_param.split('-'))
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        start_date = timezone.make_aware(start_date)
        end_date = timezone.make_aware(end_date)
    except ValueError:
        return JsonResponse({"error": "Niepoprawny format miesiąca. Użyj YYYY-MM"}, status=400)

    bookings = Booking.objects.filter(
        start_time__gte=start_date,
        start_time__lt=end_date,
        status="confirmed"
    ).select_related('room', 'user').order_by('start_time')

    # Przygotowanie bufora dla PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    # Style
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'PolishTitle',
        parent=styles['Title'],
        fontName=FONT_BOLD,
        fontSize=20,
        spaceAfter=10,
        textColor=colors.HexColor('#1a237e')
    )
    subtitle_style = ParagraphStyle(
        'PolishSubtitle',
        parent=styles['Normal'],
        fontName=FONT_BOLD,
        fontSize=12,
        spaceAfter=15,
        textColor=colors.HexColor('#667eea')
    )
    normal_style = ParagraphStyle(
        'PolishNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10,
    )
    header_style = ParagraphStyle(
        'PolishHeader',
        parent=styles['Normal'],
        fontName=FONT_BOLD,
        fontSize=12,
        spaceBefore=10,
        spaceAfter=10,
        textColor=colors.HexColor('#1a237e')
    )

    # Nagłówek
    elements.append(Paragraph(f"RAPORT REZERWACJI - {month_param}", title_style))
    elements.append(Spacer(1, 10))

    # Podsumowanie
    total_bookings = bookings.count()
    total_hours = sum(b.duration_hours for b in bookings)

    summary_data = [
        [Paragraph("<b>Liczba rezerwacji</b>", normal_style), f"{total_bookings}"],
        [Paragraph("<b>Całkowite godziny</b>", normal_style), f"{total_hours:.1f}h"],
        [Paragraph("<b>Średnia godzin/rezerwacja</b>", normal_style), f"{total_hours/total_bookings:.1f}h" if total_bookings > 0 else "N/A"],
    ]
    summary_table = Table(summary_data, colWidths=[300, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f2f5')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTNAME', (1, 0), (1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccc')),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Wykres rezerwacji per sala
    room_counts = {}
    for b in bookings:
        name = b.room.name
        room_counts[name] = room_counts.get(name, 0) + 1
    
    if room_counts:
        elements.append(Paragraph("Rezerwacje per sala", subtitle_style))
        plt.figure(figsize=(10, 4))
        rooms = list(room_counts.keys())
        counts = list(room_counts.values())
        colors_bar = ['#667eea', '#764ba2', '#11998e', '#38ef7d', '#fc4a1a', '#f7b733']
        plt.bar(rooms, counts, color=colors_bar[:len(rooms)], edgecolor='black', linewidth=1.2)
        plt.title(f'Liczba rezerwacji per sala - {month_param}', fontsize=12, fontweight='bold')
        plt.xlabel('Sala', fontsize=10)
        plt.ylabel('Liczba rezerwacji', fontsize=10)
        plt.xticks(rotation=15, ha='right')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        chart_buffer = io.BytesIO()
        plt.savefig(chart_buffer, format='png', dpi=150, bbox_inches='tight')
        chart_buffer.seek(0)
        plt.close()
        
        elements.append(Image(chart_buffer, width=6.5*inch, height=2.6*inch))
        elements.append(Spacer(1, 15))

    # Wykres godzin per departament
    dept_hours = {}
    for b in bookings:
        dept = b.user.department or "Brak departamentu"
        dept_hours[dept] = dept_hours.get(dept, 0) + b.duration_hours

    if dept_hours:
        elements.append(Paragraph("Godziny rezerwacji per departament", subtitle_style))
        plt.figure(figsize=(10, 4))
        depts = list(dept_hours.keys())
        hours = list(dept_hours.values())
        plt.bar(depts, hours, color=colors_bar[:len(depts)], edgecolor='black', linewidth=1.2)
        plt.title(f'Zarezerwowane godziny per departament - {month_param}', fontsize=12, fontweight='bold')
        plt.xlabel('Departament', fontsize=10)
        plt.ylabel('Godziny', fontsize=10)
        plt.xticks(rotation=15, ha='right')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        chart_buffer2 = io.BytesIO()
        plt.savefig(chart_buffer2, format='png', dpi=150, bbox_inches='tight')
        chart_buffer2.seek(0)
        plt.close()

        elements.append(Image(chart_buffer2, width=6.5*inch, height=2.6*inch))
        elements.append(Spacer(1, 15))

    elements.append(Paragraph("Szczegóły rezerwacji", header_style))

    # Tabela z danymi
    table_data = [[
        Paragraph("<b>Data</b>", normal_style),
        Paragraph("<b>Sala</b>", normal_style),
        Paragraph("<b>Użytkownik</b>", normal_style),
        Paragraph("<b>Tytuł</b>", normal_style),
        Paragraph("<b>Czas (h)</b>", normal_style)
    ]]
    
    for b in bookings:
        duration = b.duration_hours
        table_data.append([
            b.start_time.strftime("%Y-%m-%d %H:%M"),
            b.room.name,
            b.user.name,
            b.title[:20] + "..." if len(b.title) > 20 else b.title,
            f"{duration:.1f}"
        ])

    table = Table(table_data, colWidths=[90, 90, 100, 120, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
    ]))
    elements.append(table)
    
    elements.append(Spacer(1, 20))

    # Footer
    elements.append(Paragraph(f"<b>Podsumowanie miesiąca:</b><br/>Całkowita liczba rezerwacji: {bookings.count()}<br/>Suma zarezerwowanych godzin: {total_hours:.1f} h<br/>Średnia rezerwacji na dzień: {bookings.count()/30:.1f}", normal_style))

    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="raport_{month_param}.pdf"'
    response['X-PDF-Font-Name'] = FONT_NAME
    response['X-PDF-Font-Bold'] = FONT_BOLD
    return response

def new_booking_page(request):
    """Strona z formularzem nowej rezerwacji."""
    return render(request, "bookings.html")

def recurring_bookings_page(request):
    """Strona z formularzem rezerwacji cyklicznych."""
    return render(request, "recurring_bookings_new.html")

def get_rooms_api(request):
    """Zwraca listę wszystkich sal."""
    rooms = Room.objects.filter(is_active=True)
    return JsonResponse([{"id": r.id, "name": r.name, "capacity": r.capacity} for r in rooms], safe=False)

def get_users_api(request):
    """Zwraca listę wszystkich użytkowników."""
    users = User.objects.all()
    return JsonResponse([{"id": u.id, "name": u.name, "department": u.department} for u in users], safe=False)

def get_bookings(request):
    """Pobierz listę rezerwacji z filtrami."""
    query = Booking.objects.select_related('room', 'user').all()

    room_id = request.GET.get("room_id")
    if room_id:
        query = query.filter(room_id=room_id)

    user_id = request.GET.get("user_id")
    if user_id:
        query = query.filter(user_id=user_id)

    date_str = request.GET.get("date")
    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter(start_time__date=date)
        except ValueError:
            return JsonResponse({"error": "Niepoprawny format daty. Użyj YYYY-MM-DD."}, status=400)

    status = request.GET.get("status")
    if status:
        query = query.filter(status=status)

    query = query.order_by("-start_time")

    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 20)
    
    paginator = Paginator(query, per_page)
    page_obj = paginator.get_page(page_number)

    bookings_list = []
    for b in page_obj:
        bookings_list.append({
            "id": b.id,
            "title": b.title,
            "description": b.description,
            "start_time": b.start_time.isoformat(),
            "end_time": b.end_time.isoformat(),
            "status": b.status,
            "attendees_count": b.attendees_count,
            "duration_hours": round(b.duration_hours, 2),
            "total_cost": float(round(b.total_cost, 2)),
            "room": {"id": b.room.id, "name": b.room.name},
            "user": {"id": b.user.id, "name": b.user.name}
        })

    return JsonResponse({
        "bookings": bookings_list,
        "total": paginator.count,
        "pages": paginator.num_pages,
        "current_page": page_obj.number,
    })

@csrf_exempt
@require_http_methods(["POST"])
def create_booking(request):
    """Utwórz nową rezerwację."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    required = ["room_id", "user_id", "title", "start_time", "end_time"]
    for field in required:
        if field not in data:
            return JsonResponse({"error": f"Brak wymaganego pola: {field}"}, status=400)

    try:
        start_time = parse_datetime(data["start_time"].replace('Z', '+00:00'))
        end_time = parse_datetime(data["end_time"].replace('Z', '+00:00'))
        
        if not start_time or not end_time:
            raise ValueError("Błędny format daty")
            
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Niepoprawny format daty."}, status=400)

    if start_time >= end_time:
        return JsonResponse({"error": "Czas rozpoczęcia musi być przed czasem zakończenia."}, status=400)

    if start_time < timezone.now():
         return JsonResponse({"error": "Nie można rezerwować w przeszłości."}, status=400)

    try:
        room = Room.objects.get(id=int(data["room_id"]))
        if not room.is_active:
            return JsonResponse({"error": "Sala jest nieaktywna."}, status=400)
    except Room.DoesNotExist:
        return JsonResponse({"error": "Sala nie istnieje."}, status=404)

    try:
        user = User.objects.get(id=int(data["user_id"]))
    except User.DoesNotExist:
        return JsonResponse({"error": "Użytkownik nie istnieje."}, status=404)

    attendees = int(data.get("attendees_count", 1))
    if attendees > room.capacity:
        return JsonResponse({"error": f"Zbyt wielu uczestników. Pojemność sali: {room.capacity}."}, status=400)

    if not room.is_available(start_time, end_time):
        return JsonResponse({"error": "Sala jest już zarezerwowana w tym czasie."}, status=409)

    booking = Booking.objects.create(
        room=room,
        user=user,
        title=data["title"],
        description=data.get("description"),
        start_time=start_time,
        end_time=end_time,
        attendees_count=attendees,
    )

    # Automatycznie ustaw user_id w sesji aby pokazać powiadomienia tego użytkownika
    request.session['current_user_id'] = user.id

    return JsonResponse({
        "message": "Rezerwacja utworzona.",
        "booking": {
            "id": booking.id,
            "title": booking.title,
            "start_time": booking.start_time.isoformat(),
            "end_time": booking.end_time.isoformat(),
        },
        "user_id": user.id,  # Zwróć user_id aby frontend mógł go użyć
    }, status=201)

@csrf_exempt
@require_http_methods(["DELETE"])
def cancel_booking(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({"error": "Rezerwacja nie istnieje."}, status=404)

    if booking.status == "cancelled":
        return JsonResponse({"error": "Rezerwacja już anulowana."}, status=400)

    if booking.start_time < timezone.now():
        return JsonResponse({"error": "Nie można anulować przeszłej rezerwacji."}, status=400)

    booking.status = "cancelled"
    booking.save()
    return JsonResponse({"message": "Rezerwacja anulowana."})

def find_available(request):
    try:
        start_time_str = request.GET.get("start_time")
        end_time_str = request.GET.get("end_time")
        if not start_time_str or not end_time_str:
            return JsonResponse({"error": "Wymagane parametry: start_time i end_time (ISO)."}, status=400)
        
        start_time = parse_datetime(start_time_str.replace('Z', '+00:00'))
        end_time = parse_datetime(end_time_str.replace('Z', '+00:00'))

        if not start_time or not end_time:
            raise ValueError("Błędny format daty")

        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Niepoprawny format daty. Użyj ISO format."}, status=400)

    capacity = int(request.GET.get("capacity", 1))
    eq_param = request.GET.get("equipment")
    
    rooms = Room.objects.filter(is_active=True, capacity__gte=capacity)
    if eq_param:
        equipment_names = [e.strip() for e in eq_param.split(",") if e.strip()]
        for eq_name in equipment_names:
            rooms = rooms.filter(equipment__name=eq_name)

    available_rooms = []
    for room in rooms:
        if room.is_available(start_time, end_time):
            available_rooms.append({
                "id": room.id,
                "name": room.name,
                "capacity": room.capacity,
                "floor": room.floor,
                "description": room.description,
                "hourly_rate": float(room.hourly_rate),
                "equipment": [e.name for e in room.equipment.all()]
            })

    return JsonResponse({
        "available_rooms": available_rooms,
        "search_criteria": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "min_capacity": capacity,
        },
    })

@csrf_exempt
@require_http_methods(["POST"])
def create_recurring(request):
    try:
        data = json.loads(request.body)
        required = ["room_id", "user_id", "title", "start_time", "end_time", "frequency", "occurrences"]
        for field in required:
            if field not in data:
                return JsonResponse({"error": f"Brak wymaganego pola: {field}"}, status=400)

        start_time = parse_datetime(data["start_time"].replace('Z', '+00:00'))
        end_time = parse_datetime(data["end_time"].replace('Z', '+00:00'))

        if not start_time or not end_time:
            return JsonResponse({"error": "Niepoprawny format daty."}, status=400)

        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        if timezone.is_naive(end_time):
            end_time = timezone.make_aware(end_time)
        
        if start_time >= end_time:
            return JsonResponse({"error": "Czas rozpoczęcia musi być przed czasem zakończenia."}, status=400)
        if start_time < timezone.now():
            return JsonResponse({"error": "Nie można rezerwować w przeszłości."}, status=400)

        room = Room.objects.get(id=int(data["room_id"]))
        user = User.objects.get(id=int(data["user_id"]))
        
        frequency = data["frequency"].lower()
        occurrences = int(data["occurrences"])
        
        frequency_map = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "biweekly": timedelta(weeks=2),
            "monthly": timedelta(days=30)
        }
        
        if frequency not in frequency_map:
            return JsonResponse({"error": "Niepoprawna częstotliwość."}, status=400)
            
        interval = frequency_map[frequency]
        series_id = str(uuid.uuid4())
        
        created_bookings = []
        with transaction.atomic():
            current_start = start_time
            current_end = end_time
            for i in range(occurrences):
                if not room.is_available(current_start, current_end):
                    raise Exception(f"Sala zajęta w dniu {current_start}")
                
                booking = Booking.objects.create(
                    room=room, user=user, title=data["title"],
                    description=data.get("description"),
                    start_time=current_start, end_time=current_end,
                    attendees_count=int(data.get("attendees_count", 1)),
                    recurrence_rule=frequency.upper(),
                    series_id=series_id
                )
                created_bookings.append(booking)
                current_start += interval
                current_end += interval
                
        return JsonResponse({"message": f"Utworzono {len(created_bookings)} rezerwacji."}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
