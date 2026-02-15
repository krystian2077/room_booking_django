from django.db import models
from django.utils import timezone
from django.db.models import Sum, Count, Q
from decimal import Decimal

class User(models.Model):
    """Model użytkownika systemu."""
    email = models.EmailField(unique=True, verbose_name="Adres e-mail")
    name = models.CharField(max_length=100, verbose_name="Imię i nazwisko")
    department = models.CharField(max_length=50, blank=True, null=True, verbose_name="Departament")
    is_admin = models.BooleanField(default=False, null=True, blank=True, verbose_name="Administrator")
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True, verbose_name="Data dołączenia")

    class Meta:
        db_table = 'users'
        verbose_name = 'Użytkownik'
        verbose_name_plural = 'Użytkownicy'

    def __str__(self):
        return self.email

class Equipment(models.Model):
    """Model wyposażenia sali (projektor, tablica, wideokonferencja itp.)."""
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'equipment'
        verbose_name = 'Wyposażenie'
        verbose_name_plural = 'Wyposażenie'

    def __str__(self):
        return self.name

class Room(models.Model):
    """Model sali konferencyjnej."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nazwa sali")
    capacity = models.IntegerField(verbose_name="Pojemność")
    floor = models.IntegerField(default=0, null=True, blank=True, verbose_name="Piętro")
    description = models.TextField(blank=True, null=True, verbose_name="Opis")
    is_active = models.BooleanField(default=True, null=True, blank=True, verbose_name="Status (Aktywna)")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True, verbose_name="Stawka godzinowa")
    equipment = models.ManyToManyField(Equipment, related_name="rooms", blank=True, db_table='room_equipment')

    class Meta:
        db_table = 'rooms'
        verbose_name = 'Sala'
        verbose_name_plural = 'Sale'

    def __str__(self):
        return f"{self.name} (pojemność: {self.capacity})"

    def is_available(self, start_time, end_time, exclude_booking_id=None):
        query = self.bookings.filter(
            ~Q(status="cancelled"),
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        if exclude_booking_id:
            query = query.exclude(id=exclude_booking_id)
        return not query.exists()

class Booking(models.Model):
    """Model rezerwacji sali."""
    STATUS_CHOICES = [
        ('confirmed', '✓ Potwierdzona'),
        ('pending', '⏳ Oczekująca'),
        ('cancelled', '✗ Anulowana'),
        ('completed', '✔ Zakończona'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, default="confirmed", choices=STATUS_CHOICES)
    attendees_count = models.IntegerField(default=1, null=True, blank=True)
    
    # Pola dla rezerwacji cyklicznych
    recurrence_rule = models.CharField(max_length=50, blank=True, null=True)
    series_id = models.CharField(max_length=36, blank=True, null=True, db_index=True)
    recurring_end_date = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        verbose_name = 'Rezerwacja'
        verbose_name_plural = 'Rezerwacje'
        indexes = [
            models.Index(fields=['room', 'start_time', 'end_time'], name='idx_booking_room_time'),
        ]

    def __str__(self):
        return f"{self.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"

    @property
    def duration_hours(self):
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600

    @property
    def total_cost(self):
        if self.room and self.room.hourly_rate:
            return Decimal(self.room.hourly_rate) * Decimal(self.duration_hours)
        return Decimal(0)

class Notification(models.Model):
    """Model powiadomienia systemu."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Powiadomienie'
        verbose_name_plural = 'Powiadomienia'

    def __str__(self):
        return f"Powiadomienie #{self.id} dla {self.user.name}"
