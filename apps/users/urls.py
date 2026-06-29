from django.urls import path
from .views import (
    live_locations,
    save_fcm_token,
    send_otp,
    update_location,
    verify_otp,
    complete_profile,
    profile,
    toggle_donor,
    all_users,
    create_support_ticket,
    firebase_login,
)

urlpatterns = [
    path('send-otp/', send_otp),
    path('verify-otp/', verify_otp),
    path('firebase-login/', firebase_login),
    path('firebase-login', firebase_login),
    path('complete-profile/', complete_profile),
    path('profile/', profile),
    path('toggle-donor/', toggle_donor),
     path('location/', update_location),
    path('live/', live_locations),
    path('all-users/', all_users),
    path("save-fcm-token/", save_fcm_token),
    path("support/create/", create_support_ticket),
    path("support/create", create_support_ticket),
    path("support/", create_support_ticket),
    path("support", create_support_ticket),
]