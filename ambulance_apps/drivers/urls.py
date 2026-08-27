from django.urls import path

from .views import (
    register_driver,
    login_driver,
    upload_document,
    link_ambulance,
    owner_review,
    verify_driver_by_owner_email,
    driver_profile,
    pincode_lookup,
    send_otp,
    verify_otp,
    update_status,
    update_location,
    active_trip,
    update_trip_status,
)

urlpatterns = [
    # OTP
    path('send-otp/', send_otp, name='send-otp'),
    path('verify-otp/', verify_otp, name='verify-otp'),

    # Register & Login
    path('register/', register_driver, name='register-driver'),
    path('login/', login_driver, name='login-driver'),

    # Upload Doc & Linking
    path('upload-doc/', upload_document, name='upload-document'),
    path('link-ambulance/', link_ambulance, name='link-ambulance'),

    # Owner Review & Verification
    path('owner-review/', owner_review, name='owner-review'),
    path('verify-driver-by-owner/', verify_driver_by_owner_email, name='verify-driver-by-owner'),

    # Profile & Pincode
    path('profile/<int:driver_id>/', driver_profile, name='driver-profile'),
    path('pincode-lookup/', pincode_lookup, name='pincode-lookup'),

    # Status & Location updates
    path('update-status/', update_status, name='update-status'),
    path('update-location/', update_location, name='update-location'),

    # Trip handling
    path('active-trip/<int:driver_id>/', active_trip, name='active-trip'),
    path('trip/<int:trip_id>/update-status/', update_trip_status, name='update-trip-status'),
]
