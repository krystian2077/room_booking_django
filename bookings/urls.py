from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('summaries', views.summaries_page, name='summaries_page'),
    path('new', views.new_booking_page, name='new_booking_page'),
    path('recurring-page', views.recurring_bookings_page, name='recurring_bookings_page'),
    path('notifications', views.notifications_page, name='notifications_page'),
    path('api/rooms', views.get_rooms_api, name='get_rooms_api'),
    path('api/users', views.get_users_api, name='get_users_api'),
    path('api/bookings', views.get_bookings, name='get_bookings'),
    path('api/bookings/create', views.create_booking, name='create_booking'),
    path('api/bookings/<int:booking_id>', views.cancel_booking, name='cancel_booking'),
    path('api/available-rooms', views.find_available, name='find_available'),
    path('api/bookings/recurring', views.create_recurring, name='create_recurring'),
    path('api/notifications', views.get_notifications_api, name='get_notifications_api'),
    path('api/notifications/<int:notification_id>/read', views.mark_notification_read, name='mark_notification_read'),
    path('api/reports/monthly', views.monthly_report, name='monthly_report'),
    path('api/summaries', views.get_summaries_api, name='get_summaries_api'),
    path('api/summaries/bookings', views.get_summaries_bookings_api, name='get_summaries_bookings_api'),
]
