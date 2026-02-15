from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking, Notification, User
from django.utils import timezone
from datetime import timedelta

@receiver(post_save, sender=Booking)
def create_notifications_after_booking(sender, instance, created, **kwargs):
    if created:
        # Pobierz wszystkich użytkowników
        all_users = User.objects.all()

        # 1. Powiadomienie o utworzeniu nowej rezerwacji - DLA WSZYSTKICH UŻYTKOWNIKÓW
        for user in all_users:
            Notification.objects.create(
                user=user,
                message=f"Nowa rezerwacja: '{instance.title}' w sali {instance.room.name} przez {instance.user.name}",
                created_at=timezone.now()
            )

        # 2. Powiadomienie przypominające 1 godzinę przed rozpoczęciem - DLA WSZYSTKICH UŻYTKOWNIKÓW
        scheduled_time = instance.start_time - timedelta(hours=1)
        for user in all_users:
            Notification.objects.create(
                user=user,
                message=f"Przypomnienie: Rezerwacja '{instance.title}' w sali {instance.room.name} zaczyna się za godzinę!",
                created_at=scheduled_time
            )


