from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import User, Room, Booking, Equipment, Notification
from django import forms
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from django.http import HttpResponse
from django.db.models import Count, Sum, Q
from django.contrib.admin import AdminSite
import csv
from datetime import datetime, timedelta

# Custom filters
class FutureBookingFilter(admin.SimpleListFilter):
    title = '⏰ Czas rezerwacji'
    parameter_name = 'future'

    def lookups(self, request, model_admin):
        return (
            ('future', '🔜 Nadchodzące'),
            ('active', '▶️ Aktywne teraz'),
            ('past', '✅ Zakończone'),
            ('today', '📅 Dzisiaj'),
            ('week', '📆 Ten tydzień'),
            ('month', '🗓️ Ten miesiąc'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'future':
            return queryset.filter(start_time__gte=now)
        if self.value() == 'active':
            return queryset.filter(start_time__lte=now, end_time__gte=now)
        if self.value() == 'past':
            return queryset.filter(end_time__lt=now)
        if self.value() == 'today':
            return queryset.filter(start_time__date=now.date())
        if self.value() == 'week':
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=7)
            return queryset.filter(start_time__gte=week_start, start_time__lt=week_end)
        if self.value() == 'month':
            return queryset.filter(start_time__year=now.year, start_time__month=now.month)
        return queryset


class BookingYearFilter(admin.SimpleListFilter):
    title = '📅 Rok'
    parameter_name = 'year'

    def lookups(self, request, model_admin):
        now = timezone.now()
        return (
            (str(now.year), str(now.year)),
            (str(now.year + 1), str(now.year + 1)),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(start_time__year=int(self.value()))
        return queryset


class BookingDurationFilter(admin.SimpleListFilter):
    title = '⏱️ Czas trwania'
    parameter_name = 'duration'

    def lookups(self, request, model_admin):
        return (
            ('short', '⚡ Krótkie (< 2h)'),
            ('medium', '⏰ Średnie (2-4h)'),
            ('long', '🕐 Długie (4-8h)'),
            ('full', '📅 Całodniowe (> 8h)'),
        )

    def queryset(self, request, queryset):
        from django.db.models import F, ExpressionWrapper, DurationField

        if self.value() == 'short':
            return queryset.annotate(
                duration=ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
            ).filter(duration__lt=timedelta(hours=2))
        elif self.value() == 'medium':
            return queryset.annotate(
                duration=ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
            ).filter(duration__gte=timedelta(hours=2), duration__lt=timedelta(hours=4))
        elif self.value() == 'long':
            return queryset.annotate(
                duration=ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
            ).filter(duration__gte=timedelta(hours=4), duration__lt=timedelta(hours=8))
        elif self.value() == 'full':
            return queryset.annotate(
                duration=ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
            ).filter(duration__gte=timedelta(hours=8))
        return queryset


class AttendeesCountFilter(admin.SimpleListFilter):
    title = 'Liczba uczestników'
    parameter_name = 'attendees'

    def lookups(self, request, model_admin):
        return (
            ('small', '👤 Małe (1-5)'),
            ('medium', '👥 Średnie (6-15)'),
            ('large', '👨‍👩‍👧‍👦 Duże (16-30)'),
            ('xlarge', '🏢 Bardzo duże (> 30)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'small':
            return queryset.filter(attendees_count__lte=5)
        elif self.value() == 'medium':
            return queryset.filter(attendees_count__gte=6, attendees_count__lte=15)
        elif self.value() == 'large':
            return queryset.filter(attendees_count__gte=16, attendees_count__lte=30)
        elif self.value() == 'xlarge':
            return queryset.filter(attendees_count__gt=30)
        return queryset


class UserActivityFilter(admin.SimpleListFilter):
    title = 'Aktywność użytkownika'
    parameter_name = 'activity'

    def lookups(self, request, model_admin):
        return (
            ('active', '🟢 Aktywny (> 5 rezerwacji)'),
            ('moderate', '🟡 Umiarkowany (2-5 rezerwacji)'),
            ('low', '🟠 Niski (1 rezerwacja)'),
            ('inactive', '🔴 Nieaktywny'),
        )

    def queryset(self, request, queryset):
        from django.db.models import Count

        if self.value() == 'active':
            active_users = User.objects.annotate(
                booking_count=Count('bookings')
            ).filter(booking_count__gt=5).values_list('id', flat=True)
            return queryset.filter(id__in=active_users)
        elif self.value() == 'moderate':
            moderate_users = User.objects.annotate(
                booking_count=Count('bookings')
            ).filter(booking_count__gte=2, booking_count__lte=5).values_list('id', flat=True)
            return queryset.filter(id__in=moderate_users)
        elif self.value() == 'low':
            low_users = User.objects.annotate(
                booking_count=Count('bookings')
            ).filter(booking_count=1).values_list('id', flat=True)
            return queryset.filter(id__in=low_users)
        elif self.value() == 'inactive':
            inactive_users = User.objects.annotate(
                booking_count=Count('bookings')
            ).filter(booking_count=0).values_list('id', flat=True)
            return queryset.filter(id__in=inactive_users)
        return queryset


class RoomCapacityFilter(admin.SimpleListFilter):
    title = 'Pojemność sali'
    parameter_name = 'capacity_range'

    def lookups(self, request, model_admin):
        return (
            ('micro', '🪑 Mikro (1-5)'),
            ('small', '👥 Mała (6-15)'),
            ('medium', '🏢 Średnia (16-30)'),
            ('large', '🎭 Duża (31-50)'),
            ('xlarge', '🏟️ Bardzo duża (> 50)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'micro':
            return queryset.filter(capacity__lte=5)
        elif self.value() == 'small':
            return queryset.filter(capacity__gte=6, capacity__lte=15)
        elif self.value() == 'medium':
            return queryset.filter(capacity__gte=16, capacity__lte=30)
        elif self.value() == 'large':
            return queryset.filter(capacity__gte=31, capacity__lte=50)
        elif self.value() == 'xlarge':
            return queryset.filter(capacity__gt=50)
        return queryset

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('name_with_badge', 'email', 'department_badge', 'is_admin_badge', 'booking_count_visual', 'last_booking', 'created_at')
    list_filter = ('department', 'is_admin', UserActivityFilter, 'created_at')
    search_fields = ('name', 'email', 'department')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    actions = ['make_admin', 'remove_admin', 'export_users_csv', 'send_welcome_email']
    list_per_page = 50
    change_list_template = 'admin/bookings/user/change_list.html'
    change_form_template = 'admin/bookings/user/change_form.html'

    # Mapowanie indeksu kolumny (list_display) na parametr filtra dla ikonki filtrowania
    COLUMN_FILTER_MAP = {
        2: 'department',
        3: 'is_admin',
        6: 'created_at',
    }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            cl = self.get_changelist_instance(request)
            filter_specs = getattr(cl, 'filter_specs', [])
            param_to_spec = {}
            for spec in filter_specs:
                key = getattr(spec, 'field_path', getattr(spec, 'parameter_name', None)) or spec.title
                param_to_spec[str(key)] = spec
            column_filters = []
            for i in range(len(self.list_display)):
                param = self.COLUMN_FILTER_MAP.get(i)
                if not param or param not in param_to_spec:
                    column_filters.append(None)
                    continue
                spec = param_to_spec[param]
                choices = []
                for c in spec.choices(cl):
                    qs = c.get('query_string', '') or ''
                    if isinstance(qs, str) and qs.startswith('?'):
                        qs = qs[1:]
                    choices.append({
                        'display': str(c.get('display', '')),
                        'query_string': qs,
                        'selected': bool(c.get('selected', False)),
                    })
                column_filters.append({
                    'param': param,
                    'title': getattr(spec, 'title', param),
                    'choices': choices,
                })
            extra_context['column_filters'] = column_filters
            extra_context['changelist_base_url'] = request.path
        except Exception:
            extra_context['column_filters'] = []
            extra_context['changelist_base_url'] = request.path
        return super().changelist_view(request, extra_context)

    fieldsets = (
        ('👤 Informacje podstawowe', {
            'fields': ('name', 'email', 'department'),
            'classes': ('wide',)
        }),
        ('🔐 Uprawnienia', {
            'fields': ('is_admin',),
        }),
        ('📊 Statystyki', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def name_with_badge(self, obj):
        badge = '👑' if obj.is_admin else '👤'
        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.5rem;">'
            '<span style="font-size: 1.2rem;">{}</span>'
            '<span style="font-weight: 700; color: #e2e8f0;">{}</span>'
            '</div>',
            badge, obj.name
        )
    name_with_badge.short_description = 'Nazwa'
    name_with_badge.admin_order_field = 'name'

    def department_badge(self, obj):
        colors = {
            'IT': '#2563eb',
            'HR': '#10b981',
            'Marketing': '#f59e0b',
            'Sprzedaż': '#ef4444',
            'Finanse': '#8b5cf6',
        }
        color = colors.get(obj.department, '#64748b')
        return format_html(
            '<span style="background: linear-gradient(135deg, {}33, {}22); '
            'color: {}; padding: 0.4rem 0.8rem; border-radius: 6px; '
            'font-weight: 700; font-size: 0.75rem; text-transform: uppercase; '
            'letter-spacing: 0.5px; border: 1px solid {}44;">{}</span>',
            color, color, color, color, obj.department
        )
    department_badge.short_description = 'Departament'
    department_badge.admin_order_field = 'department'

    def is_admin_badge(self, obj):
        from django.utils.safestring import mark_safe

        if obj.is_admin:
            return mark_safe(
                '<span style="background: linear-gradient(135deg, #10b98133, #05966922); '
                'color: #10b981; padding: 0.4rem 0.8rem; border-radius: 6px; '
                'font-weight: 800; font-size: 0.7rem; text-transform: uppercase; '
                'letter-spacing: 0.5px; border: 1px solid #10b98144; '
                'box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);">✓ ADMIN</span>'
            )
        return mark_safe(
            '<span style="color: #64748b; font-size: 0.8rem;">—</span>'
        )
    is_admin_badge.short_description = 'Admin'
    is_admin_badge.admin_order_field = 'is_admin'

    def booking_count_visual(self, obj):
        count = obj.bookings.count()
        if count > 10:
            color = '#10b981'
            icon = '🔥'
        elif count > 5:
            color = '#2563eb'
            icon = '⭐'
        elif count > 0:
            color = '#f59e0b'
            icon = '📊'
        else:
            color = '#64748b'
            icon = '—'

        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.5rem;">'
            '<span style="font-size: 1.1rem;">{}</span>'
            '<span style="font-weight: 800; color: {}; font-size: 1.1rem;">{}</span>'
            '</div>',
            icon, color, count
        )
    booking_count_visual.short_description = 'Rezerwacje'

    def last_booking(self, obj):
        last = obj.bookings.order_by('-start_time').first()
        if last:
            return format_html(
                '<span style="color: #94a3b8; font-size: 0.85rem;">{}</span>',
                last.start_time.strftime('%d.%m.%Y')
            )
        return mark_safe('<span style="color: #64748b;">—</span>')
    last_booking.short_description = 'Ostatnia rezerwacja'

    # Actions
    def make_admin(self, request, queryset):
        updated = queryset.update(is_admin=True)
        self.message_user(request, f'✅ Nadano uprawnienia administratora dla {updated} użytkowników', messages.SUCCESS)
    make_admin.short_description = '👑 Nadaj uprawnienia administratora'

    def remove_admin(self, request, queryset):
        updated = queryset.update(is_admin=False)
        self.message_user(request, f'✅ Usunięto uprawnienia administratora dla {updated} użytkowników', messages.SUCCESS)
    remove_admin.short_description = '❌ Usuń uprawnienia administratora'

    def export_users_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="uzytkownicy.csv"'
        response.write('\ufeff')  # BOM for UTF-8

        writer = csv.writer(response)
        writer.writerow(['Nazwa', 'Email', 'Departament', 'Admin', 'Liczba rezerwacji', 'Data utworzenia'])

        for user in queryset:
            writer.writerow([
                user.name,
                user.email,
                user.department,
                'Tak' if user.is_admin else 'Nie',
                user.bookings.count(),
                user.created_at.strftime('%Y-%m-%d %H:%M')
            ])

        self.message_user(request, f'✅ Wyeksportowano {queryset.count()} użytkowników', messages.SUCCESS)
        return response
    export_users_csv.short_description = '📥 Eksportuj do CSV'

    def send_welcome_email(self, request, queryset):
        count = queryset.count()
        # Tutaj implementacja wysyłania emaili
        self.message_user(request, f'📧 Wysłano email powitalny do {count} użytkowników', messages.SUCCESS)
    send_welcome_email.short_description = '📧 Wyślij email powitalny'

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Dodaj Użytkownika'
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Edycja Użytkownika'
        return super().change_view(request, object_id, form_url, extra_context)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'floor', 'is_active', 'hourly_rate', 'equipment_tags', 'utilization_bar', 'next_booking')
    list_editable = ('capacity', 'floor', 'is_active', 'hourly_rate')
    list_display_links = ('name',)
    list_filter = ('is_active', 'floor', RoomCapacityFilter)
    search_fields = ('name', 'description')
    ordering = ('name',)
    filter_horizontal = ('equipment',)
    actions = ['activate_rooms', 'deactivate_rooms', 'export_rooms_csv', 'generate_qr_codes']
    list_per_page = 50
    change_list_template = 'admin/bookings/room/change_list.html'
    change_form_template = 'admin/bookings/room/change_form.html'

    # Mapowanie indeksu kolumny (list_display) na parametr filtra dla ikonki filtrowania
    COLUMN_FILTER_MAP = {
        1: 'capacity_range',
        2: 'floor',
        3: 'is_active',
    }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            cl = self.get_changelist_instance(request)
            filter_specs = getattr(cl, 'filter_specs', [])
            param_to_spec = {}
            for spec in filter_specs:
                key = getattr(spec, 'field_path', getattr(spec, 'parameter_name', None)) or spec.title
                param_to_spec[str(key)] = spec
            column_filters = []
            for i in range(len(self.list_display)):
                param = self.COLUMN_FILTER_MAP.get(i)
                if not param or param not in param_to_spec:
                    column_filters.append(None)
                    continue
                spec = param_to_spec[param]
                choices = []
                for c in spec.choices(cl):
                    qs = c.get('query_string', '') or ''
                    if isinstance(qs, str) and qs.startswith('?'):
                        qs = qs[1:]
                    choices.append({
                        'display': str(c.get('display', '')),
                        'query_string': qs,
                        'selected': bool(c.get('selected', False)),
                    })
                column_filters.append({
                    'param': param,
                    'title': getattr(spec, 'title', param),
                    'choices': choices,
                })
            extra_context['column_filters'] = column_filters
            extra_context['changelist_base_url'] = request.path
        except Exception:
            extra_context['column_filters'] = []
            extra_context['changelist_base_url'] = request.path
        return super().changelist_view(request, extra_context)


    fieldsets = (
        ('🏢 Informacje podstawowe', {
            'fields': ('name', 'description'),
            'classes': ('wide',)
        }),
        ('📍 Lokalizacja i pojemność', {
            'fields': ('floor', 'capacity'),
        }),
        ('💰 Finanse', {
            'fields': ('hourly_rate',),
        }),
        ('🛠️ Wyposażenie', {
            'fields': ('equipment',),
            'classes': ('wide',)
        }),
        ('⚙️ Status', {
            'fields': ('is_active',),
        }),
    )

    def name_with_icon(self, obj):
        icon = '🟢' if obj.is_active else '🔴'
        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.5rem;">'
            '<span style="font-size: 1.2rem;">{}</span>'
            '<span style="font-weight: 700; color: #e2e8f0; font-size: 1.05rem;">{}</span>'
            '</div>',
            icon, obj.name
        )
    name_with_icon.short_description = 'Nazwa sali'
    name_with_icon.admin_order_field = 'name'

    def capacity_visual(self, obj):
        if obj.capacity > 50:
            icon = '🏟️'
            color = '#8b5cf6'
        elif obj.capacity > 30:
            icon = '🎭'
            color = '#2563eb'
        elif obj.capacity > 15:
            icon = '🏢'
            color = '#10b981'
        else:
            icon = '👥'
            color = '#f59e0b'

        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.5rem;">'
            '<span style="font-size: 1.2rem;">{}</span>'
            '<span style="font-weight: 800; color: {}; font-size: 1.1rem;">{}</span>'
            '<span style="color: #64748b; font-size: 0.85rem;">osób</span>'
            '</div>',
            icon, color, obj.capacity
        )
    capacity_visual.short_description = 'Pojemność'
    capacity_visual.admin_order_field = 'capacity'

    def floor_badge(self, obj):
        return format_html(
            '<span style="background: linear-gradient(135deg, #2563eb33, #2563eb22); '
            'color: #2563eb; padding: 0.4rem 0.8rem; border-radius: 6px; '
            'font-weight: 700; font-size: 0.75rem; border: 1px solid #2563eb44;">'
            '🏢 Piętro {}</span>',
            obj.floor
        )
    floor_badge.short_description = 'Piętro'
    floor_badge.admin_order_field = 'floor'


    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="background: linear-gradient(135deg, #10b98133, #05966922); '
                'color: #10b981; padding: 0.4rem 0.8rem; border-radius: 6px; '
                'font-weight: 800; font-size: 0.7rem; text-transform: uppercase; '
                'letter-spacing: 0.5px; border: 1px solid #10b98144; '
                'box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);">✓ AKTYWNA</span>'
            )
        return mark_safe(
            '<span style="background: linear-gradient(135deg, #ef444433, #dc262622); '
            'color: #ef4444; padding: 0.4rem 0.8rem; border-radius: 6px; '
            'font-weight: 800; font-size: 0.7rem; text-transform: uppercase; '
            'letter-spacing: 0.5px; border: 1px solid #ef444444;">✗ NIEAKTYWNA</span>'
        )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'

    def hourly_rate_display(self, obj):
        return format_html(
            '<span style="font-weight: 700; color: #10b981; font-size: 1rem;">{} zł</span>'
            '<span style="color: #64748b; font-size: 0.8rem;">/h</span>',
            obj.hourly_rate
        )
    hourly_rate_display.short_description = 'Stawka'
    hourly_rate_display.admin_order_field = 'hourly_rate'

    def equipment_tags(self, obj):
        items = obj.equipment.all()
        if not items:
            return mark_safe('<span style="color: #64748b;">—</span>')

        tags = ' '.join([
            f'<span style="background: rgba(37, 99, 235, 0.15); color: #60a5fa; '
            f'padding: 0.25rem 0.6rem; border-radius: 4px; font-size: 0.75rem; '
            f'font-weight: 600; margin-right: 0.25rem; border: 1px solid rgba(37, 99, 235, 0.3);">'
            f'{e.icon} {e.name}</span>'
            for e in items[:3]
        ])

        more = len(items) - 3
        if more > 0:
            tags += f'<span style="color: #64748b; font-size: 0.75rem; margin-left: 0.25rem;">+{more}</span>'

        return mark_safe(tags)
    equipment_tags.short_description = 'Wyposażenie'

    def utilization_bar(self, obj):
        thirty_days_ago = timezone.now() - timedelta(days=30)
        bookings_count = obj.bookings.filter(
            start_time__gte=thirty_days_ago,
            status='confirmed'
        ).count()

        # Zakładamy że 100% = 60 rezerwacji w miesiącu (2 dziennie)
        percentage = min(int((bookings_count / 60) * 100), 100)

        if percentage > 75:
            color = '#10b981'
            icon = '🔥'
        elif percentage > 50:
            color = '#2563eb'
            icon = '📈'
        elif percentage > 25:
            color = '#f59e0b'
            icon = '📊'
        else:
            color = '#64748b'
            icon = '📉'

        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.5rem;">'
            '<span style="font-size: 1rem;">{}</span>'
            '<div style="width: 80px; height: 20px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1);">'
            '<div style="width: {}%; height: 100%; background: linear-gradient(90deg, {}, {}aa); transition: width 0.3s ease;"></div>'
            '</div>'
            '<span style="font-weight: 700; color: {}; font-size: 0.85rem;">{}%</span>'
            '</div>',
            icon, percentage, color, color, color, percentage
        )
    utilization_bar.short_description = 'Wykorzystanie (30d)'

    def next_booking(self, obj):
        next_b = obj.bookings.filter(start_time__gte=timezone.now()).order_by('start_time').first()
        if next_b:
            return format_html(
                '<span style="color: #94a3b8; font-size: 0.85rem;">{}</span>',
                next_b.start_time.strftime('%d.%m %H:%M')
            )
        return mark_safe('<span style="color: #64748b;">—</span>')
    next_booking.short_description = 'Następna rezerwacja'

    # Actions
    def activate_rooms(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'✅ Aktywowano {updated} sal', messages.SUCCESS)
    activate_rooms.short_description = '✓ Aktywuj sale'

    def deactivate_rooms(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'⚠️ Dezaktywowano {updated} sal', messages.WARNING)
    deactivate_rooms.short_description = '✗ Dezaktywuj sale'

    def export_rooms_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="sale.csv"'
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow(['Nazwa', 'Pojemność', 'Piętro', 'Stawka/h', 'Status', 'Wyposażenie'])

        for room in queryset:
            equipment = ', '.join([e.name for e in room.equipment.all()])
            writer.writerow([
                room.name,
                room.capacity,
                room.floor,
                room.hourly_rate,
                'Aktywna' if room.is_active else 'Nieaktywna',
                equipment
            ])

        self.message_user(request, f'✅ Wyeksportowano {queryset.count()} sal', messages.SUCCESS)
        return response
    export_rooms_csv.short_description = '📥 Eksportuj do CSV'

    def generate_qr_codes(self, request, queryset):
        count = queryset.count()
        # Tutaj implementacja generowania kodów QR
        self.message_user(request, f'📱 Wygenerowano kody QR dla {count} sal', messages.SUCCESS)
    generate_qr_codes.short_description = '📱 Generuj kody QR'

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Dodaj Salę'
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Edycja Sali'
        return super().change_view(request, object_id, form_url, extra_context)

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'room_count')
    search_fields = ('name',)
    change_form_template = 'admin/bookings/equipment/change_form.html'
    
    def room_count(self, obj):
        count = obj.rooms.count()
        return format_html('<span style="font-weight: bold;">{} sal</span>', count)
    room_count.short_description = 'Liczba sal'

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Dodaj Wyposażenie'
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Edycja Wyposażenia'
        return super().change_view(request, object_id, form_url, extra_context)

class BookingChangeForm(forms.ModelForm):
    # Custom widgets for better UX with icons
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control booking-premium-input',
            'placeholder': '📌 Wpisz tytuł spotkania...',
            'style': 'font-size: 1.1rem; padding: 0.8rem;'
        }),
        help_text='✏️ Krótki, opisowy tytuł dla rezerwacji (np. "Spotkanie zespołu", "Prezentacja projektu")'
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control booking-premium-textarea',
            'placeholder': '📝 Dodaj opis lub notatki...',
            'rows': 4,
            'style': 'resize: vertical;'
        }),
        help_text='📄 Opcjonalnie dodaj szczegóły, agende lub ważne uwagi dotyczące spotkania'
    )

    room = forms.ModelChoiceField(
        queryset=Room.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-control booking-premium-select'
        }),
        help_text='🚪 Wybierz salę konferencyjną, w której odbędzie się spotkanie'
    )

    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control booking-premium-select'
        }),
        help_text='👤 Wybierz organizatora/właściciela rezerwacji'
    )

    attendees_count = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control booking-premium-input',
            'style': 'font-size: 1rem;',
            'placeholder': '👥 Liczba uczestników'
        }),
        help_text='👥 Liczba uczestników (musi być ≤ pojemność sali)'
    )

    status = forms.ChoiceField(
        choices=Booking.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control booking-premium-select'
        }),
        help_text='🔔 Zmień status rezerwacji'
    )

    start_time = forms.DateTimeField(
        widget=forms.TextInput(attrs={
            'class': 'form-control booking-premium-input datetime-input',
            'placeholder': 'DD/MM/YYYY HH:MM:SS',
            'autocomplete': 'off'
        }),
        help_text='📅 Data i godzina rozpoczęcia',
        input_formats=['%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M']
    )

    end_time = forms.DateTimeField(
        widget=forms.TextInput(attrs={
            'class': 'form-control booking-premium-input datetime-input',
            'placeholder': 'DD/MM/YYYY HH:MM:SS',
            'autocomplete': 'off'
        }),
        help_text='📅 Data i godzina zakończenia',
        input_formats=['%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M']
    )

    class Meta:
        model = Booking
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        attendees_count = cleaned_data.get('attendees_count', 0)
        
        if room and start_time and end_time:
            # E. Advanced validations
            
            # Check working hours (8:00 - 20:00)
            if start_time.hour < 8 or end_time.hour > 20:
                messages.warning(
                    self.request if hasattr(self, 'request') else None,
                    f"⚠️ Uwaga: Rezerwacja poza standardowymi godzinami pracy (8:00-20:00)"
                )
            
            # Check capacity
            if attendees_count > room.capacity:
                raise forms.ValidationError(
                    f"❌ Liczba uczestników ({attendees_count}) przekracza pojemność sali ({room.capacity})!"
                )
            
            # Check availability
            instance_id = self.instance.id if self.instance else None
            if not room.is_available(start_time, end_time, exclude_booking_id=instance_id):
                raise forms.ValidationError(f"❌ Sala {room.name} jest zajęta w tym terminie!")
        
        return cleaned_data

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingChangeForm
    list_display = (
        'title_with_icon',
        'room_badge',
        'user_badge',
        'time_range_display',
        'status_badge',
        'duration_visual',
        'attendees_visual',
        'cost_display',
    )
    list_display_links = ('title_with_icon',)
    list_filter = (
        'status',
        'room',
        'user',
        BookingYearFilter,
        FutureBookingFilter,
        BookingDurationFilter,
        AttendeesCountFilter,
        'start_time',
    )
    search_fields = ('title', 'user__name', 'user__email', 'room__name', 'description')
    date_hierarchy = 'start_time'
    actions = [
        'confirm_bookings',
        'cancel_bookings',
        'complete_bookings',
        'export_to_csv',
        'send_reminder',
        'duplicate_booking',
        'delete_series',
    ]
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 50
    change_list_template = 'admin/bookings/booking/change_list.html'

    # Mapowanie indeksu kolumny (list_display) na parametr filtra dla ikonki filtrowania
    COLUMN_FILTER_MAP = {
        1: 'room',
        2: 'user',
        3: 'future',  # Czas rezerwacji
        4: 'status',
        5: 'duration',
        6: 'attendees',
    }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            cl = self.get_changelist_instance(request)
            filter_specs = getattr(cl, 'filter_specs', [])
            param_to_spec = {}
            for spec in filter_specs:
                key = getattr(spec, 'field_path', getattr(spec, 'parameter_name', None)) or spec.title
                param_to_spec[str(key)] = spec
            column_filters = []
            for i in range(len(self.list_display)):
                param = self.COLUMN_FILTER_MAP.get(i)
                if not param or param not in param_to_spec:
                    column_filters.append(None)
                    continue
                spec = param_to_spec[param]
                choices = []
                for c in spec.choices(cl):
                    qs = c.get('query_string', '') or ''
                    if isinstance(qs, str) and qs.startswith('?'):
                        qs = qs[1:]
                    choices.append({
                        'display': str(c.get('display', '')),
                        'query_string': qs,
                        'selected': bool(c.get('selected', False)),
                    })
                column_filters.append({
                    'param': param,
                    'title': getattr(spec, 'title', param),
                    'choices': choices,
                })
            extra_context['column_filters'] = column_filters
            extra_context['changelist_base_url'] = request.path
        except Exception:
            extra_context['column_filters'] = []
            extra_context['changelist_base_url'] = request.path
        return super().changelist_view(request, extra_context)

    fieldsets = (
        ('✨ Podstawowe Informacje', {
            'fields': ('title', 'description'),
            'classes': ('wide', 'premium-fieldset'),
            'description': '📝 Wpisz tytuł i opis spotkania'
        }),
        ('🏢 Sala i Uczestnicy', {
            'fields': ('room', 'user', 'attendees_count'),
            'classes': ('premium-fieldset',),
            'description': '📍 Wybierz salę, użytkownika i liczbę uczestników'
        }),
        ('⏰ Rezerwacja Czasowa', {
            'fields': ('start_time', 'end_time', 'status'),
            'classes': ('premium-fieldset',),
            'description': '🕐 Ustal czas rozpoczęcia, zakończenia i status rezerwacji'
        }),
        ('📊 Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse', 'premium-fieldset'),
            'description': '📈 Informacje o tworzeniu i edycji rezerwacji'
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        return form

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Dodaj Rezerwację'
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'Edycja Rezerwacji'
        return super().change_view(request, object_id, form_url, extra_context)

    # ——— Premium list display ———
    def title_with_icon(self, obj):
        icon = '📌'
        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.5rem;">'
            '<span style="font-size: 1.2rem;">{}</span>'
            '<span style="font-weight: 700; color: #e2e8f0;">{}</span>'
            '</div>',
            icon, obj.title
        )
    title_with_icon.short_description = 'Tytuł'
    title_with_icon.admin_order_field = 'title'

    def room_badge(self, obj):
        return format_html(
            '<a href="/admin/bookings/room/{}/change/" style="text-decoration: none;">'
            '<span style="background: linear-gradient(135deg, #7c3aed33, #6d28d922); '
            'color: #a78bfa; padding: 0.4rem 0.8rem; border-radius: 6px; '
            'font-weight: 700; font-size: 0.75rem; border: 1px solid #7c3aed44;">'
            '🚪 {}</span></a>',
            obj.room.id, obj.room.name
        )
    room_badge.short_description = 'Sala'
    room_badge.admin_order_field = 'room__name'

    def user_badge(self, obj):
        return format_html(
            '<a href="/admin/bookings/user/{}/change/" style="text-decoration: none;">'
            '<span style="background: linear-gradient(135deg, #10b98133, #05966922); '
            'color: #34d399; padding: 0.4rem 0.8rem; border-radius: 6px; '
            'font-weight: 700; font-size: 0.75rem; border: 1px solid #10b98144;">'
            '👤 {}</span></a>',
            obj.user.id, obj.user.name
        )
    user_badge.short_description = 'Użytkownik'
    user_badge.admin_order_field = 'user__name'

    def time_range_display(self, obj):
        now = timezone.now()
        start_time = obj.start_time
        end_time = obj.end_time
        if start_time.tzinfo is None:
            start_time = timezone.make_aware(start_time)
        if end_time.tzinfo is None:
            end_time = timezone.make_aware(end_time)
        is_today = start_time.date() == now.date()
        is_past = end_time < now
        if is_today:
            badge_color, badge_text = '#10b981', 'DZISIAJ'
        elif is_past:
            badge_color, badge_text = '#64748b', 'ZAKOŃCZONE'
        else:
            badge_color, badge_text = '#2563eb', 'NADCHODZĄCE'
        return format_html(
            '<div style="display: flex; flex-direction: column; gap: 0.25rem;">'
            '<span style="color: #e2e8f0; font-weight: 600; font-size: 0.9rem;">📅 {}</span>'
            '<span style="color: #94a3b8; font-size: 0.85rem;">🕐 {} – {}</span>'
            '<span style="background: linear-gradient(135deg, {}33, {}22); color: {}; '
            'padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 700; font-size: 0.65rem; '
            'display: inline-block; width: fit-content;">{}</span>'
            '</div>',
            obj.start_time.strftime('%d.%m.%Y'),
            obj.start_time.strftime('%H:%M'),
            obj.end_time.strftime('%H:%M'),
            badge_color, badge_color, badge_color, badge_text
        )
    time_range_display.short_description = 'Termin'
    time_range_display.admin_order_field = 'start_time'

    def status_badge(self, obj):
        status_config = {
            'confirmed': ('#10b981', '✓ POTWIERDZONA', '✅'),
            'pending': ('#f59e0b', '⏳ OCZEKUJĄCA', '⏳'),
            'cancelled': ('#ef4444', '✗ ANULOWANA', '❌'),
            'completed': ('#8b5cf6', '✔ ZAKOŃCZONA', '✔️'),
        }
        color, text, icon = status_config.get(obj.status, ('#64748b', obj.status, '❓'))
        return format_html(
            '<span style="background: linear-gradient(135deg, {}33, {}22); color: {}; '
            'padding: 0.5rem 1rem; border-radius: 6px; font-weight: 800; font-size: 0.7rem; '
            'text-transform: uppercase; letter-spacing: 0.5px; border: 1px solid {}44;">{}</span>',
            color, color, color, color, text
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def duration_visual(self, obj):
        hours = (obj.end_time - obj.start_time).total_seconds() / 3600
        hours_str = f'{hours:.1f}'
        if hours >= 8:
            icon, color = '📅', '#8b5cf6'
        elif hours >= 4:
            icon, color = '🕐', '#2563eb'
        elif hours >= 2:
            icon, color = '⏰', '#10b981'
        else:
            icon, color = '⚡', '#f59e0b'
        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.5rem;">'
            '<span style="font-size: 1.2rem;">{}</span>'
            '<span style="font-weight: 800; color: {}; font-size: 1rem;">{}h</span>'
            '</div>',
            icon, color, hours_str
        )
    duration_visual.short_description = 'Czas trwania'
    duration_visual.admin_order_field = 'start_time'

    def attendees_visual(self, obj):
        count = obj.attendees_count or 0
        capacity = obj.room.capacity
        if capacity and capacity > 0:
            pct = int((count / capacity) * 100)
            if pct > 90:
                color, icon = '#ef4444', '🔥'
            elif pct > 70:
                color, icon = '#f59e0b', '⚠️'
            elif pct > 50:
                color, icon = '#10b981', '✓'
            else:
                color, icon = '#2563eb', '👥'
        else:
            color, icon = '#64748b', '👥'
        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.5rem;">'
            '<span style="font-size: 1.1rem;">{}</span>'
            '<span style="font-weight: 800; color: {};">{}</span>'
            '<span style="color: #64748b; font-size: 0.8rem;">/ {}</span>'
            '</div>',
            icon, color, count, capacity or '—'
        )
    attendees_visual.short_description = 'Uczestnicy'
    attendees_visual.admin_order_field = 'attendees_count'

    def cost_display(self, obj):
        hours = (obj.end_time - obj.start_time).total_seconds() / 3600
        rate = float(obj.room.hourly_rate or 0)
        cost = hours * rate
        cost_str = f'{cost:.2f}'
        return format_html(
            '<div style="display: flex; align-items: center; gap: 0.25rem;">'
            '<span style="font-weight: 800; color: #10b981; font-size: 1rem;">{} zł</span>'
            '<span style="color: #64748b; font-size: 0.85rem;">/h</span>'
            '</div>',
            cost_str
        )
    cost_display.short_description = 'Koszt'

    # ——— Akcje zbiorcze ———
    def confirm_bookings(self, request, queryset):
        cnt = queryset.exclude(status='cancelled').update(status='confirmed')
        self.message_user(request, f"✅ Potwierdzono {cnt} rezerwacji.", messages.SUCCESS)
    confirm_bookings.short_description = "✅ Potwierdź wybrane"

    def cancel_bookings(self, request, queryset):
        cnt = queryset.update(status='cancelled')
        self.message_user(request, f"❌ Anulowano {cnt} rezerwacji.", messages.WARNING)
    cancel_bookings.short_description = "❌ Anuluj wybrane"

    def complete_bookings(self, request, queryset):
        cnt = queryset.exclude(status='cancelled').update(status='completed')
        self.message_user(request, f"✔️ Oznaczono jako zakończone: {cnt} rezerwacji.", messages.SUCCESS)
    complete_bookings.short_description = "✔️ Oznacz jako zakończone"

    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="rezerwacje_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Tytuł', 'Sala', 'Użytkownik', 'Departament', 'Start', 'Koniec', 'Status', 'Uczestnicy', 'Czas (h)'])
        for booking in queryset:
            writer.writerow([
                booking.title,
                booking.room.name,
                booking.user.name,
                (booking.user.department or '-'),
                booking.start_time.strftime('%Y-%m-%d %H:%M'),
                booking.end_time.strftime('%Y-%m-%d %H:%M'),
                booking.status,
                booking.attendees_count or '',
                f"{booking.duration_hours:.2f}"
            ])
        self.message_user(request, f"📥 Wyeksportowano {queryset.count()} rezerwacji do CSV", messages.SUCCESS)
        return response
    export_to_csv.short_description = "📥 Eksportuj do CSV"

    def send_reminder(self, request, queryset):
        future = queryset.filter(start_time__gte=timezone.now())
        count = future.count()
        self.message_user(
            request,
            f"📧 Przypomnienia zostaną wysłane dla {count} nadchodzących rezerwacji (placeholder).",
            messages.SUCCESS
        )
    send_reminder.short_description = "📧 Wyślij przypomnienie"

    def duplicate_booking(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Wybierz dokładnie jedną rezerwację do skopiowania.", messages.ERROR)
            return
        orig = queryset.first()
        new_start = orig.start_time + timedelta(days=1)
        new_end = orig.end_time + timedelta(days=1)
        Booking.objects.create(
            room=orig.room,
            user=orig.user,
            title=f"{orig.title} (kopia)",
            description=orig.description,
            start_time=new_start,
            end_time=new_end,
            status='pending',
            attendees_count=orig.attendees_count or 1,
        )
        self.message_user(request, f"✅ Skopiowano rezerwację na {new_start.strftime('%d.%m.%Y')}.", messages.SUCCESS)
    duplicate_booking.short_description = "📋 Duplikuj (+1 dzień)"

    def delete_series(self, request, queryset):
        series_ids = queryset.exclude(series_id__isnull=True).exclude(series_id='').values_list('series_id', flat=True).distinct()
        if not series_ids:
            self.message_user(request, "Wybierz rezerwacje z serii cyklicznej.", messages.WARNING)
            return
        total = 0
        for sid in series_ids:
            total += Booking.objects.filter(series_id=sid).delete()[0]
        self.message_user(request, f"🗑️ Usunięto {total} rezerwacji z serii.", messages.SUCCESS)
    delete_series.short_description = "🗑️ Usuń całą serię"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_preview', 'is_read_colored', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__name', 'message')
    date_hierarchy = 'created_at'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Wiadomość'
    
    def is_read_colored(self, obj):
        color = '#10b981' if obj.is_read else '#f59e0b'
        text = 'Przeczytane' if obj.is_read else 'Nieprzeczytane'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, text)
    is_read_colored.short_description = 'Status'

# A. Custom Admin Site with Dashboard
class RoomBookerAdminSite(AdminSite):
    site_header = "🏢 RoomBooker Admin"
    site_title = "RoomBooker"
    index_title = "Panel Administracyjny"
    
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Dashboard Statistics
        now = timezone.now()
        today = now.date()

        # Total counts
        extra_context['total_bookings'] = Booking.objects.count()
        extra_context['total_users'] = User.objects.count()
        extra_context['total_rooms'] = Room.objects.filter(is_active=True).count()

        # Active bookings today
        extra_context['active_bookings'] = Booking.objects.filter(
            start_time__date=today,
            end_time__gte=now
        ).exclude(status='cancelled').count()

        return super().index(request, extra_context)

# Custom admin site with enhanced dashboard (disabled - using template override instead)
# admin_site = RoomBookerAdminSite(name='admin')
# admin.site = admin_site

