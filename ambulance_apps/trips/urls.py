from django.urls import path

from .views import (
    booking_history,
    accept_booking_request,
    create_booking,
    live_bookings,
    nearby_booking_options,
    past_bookings,
    pending_driver_requests,
    reject_booking_request,
    track_booking,
    verify_pickup_otp,
)


urlpatterns = [
    path('', create_booking, name='create-booking'),
    path('create/', create_booking, name='create-booking-legacy'),
    path('nearby/', nearby_booking_options, name='nearby-booking-options'),
    path('driver/<int:driver_id>/requests/', pending_driver_requests, name='pending-driver-requests'),
    path('<int:trip_id>/accept/', accept_booking_request, name='accept-booking-request'),
    path('<int:trip_id>/reject/', reject_booking_request, name='reject-booking-request'),
    path('<int:trip_id>/verify-pickup-otp/', verify_pickup_otp, name='verify-pickup-otp'),
    path('<int:trip_id>/track/', track_booking, name='track-booking'),
    path('history/', booking_history, name='booking-history'),
    path('live/', live_bookings, name='live-bookings'),
    path('past/', past_bookings, name='past-bookings'),
]
