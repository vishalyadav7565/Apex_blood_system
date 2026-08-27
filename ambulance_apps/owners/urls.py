from django.urls import path
from .views import (
    register_owner,
    verify_registration_otps,
    verify_digilocker,
    upload_business_documents,
    login_owner_request,
    login_owner_verify,
    owner_profile,
    admin_approve_owner,
    verify_firebase_email_otp,
    login_owner_firebase,
    send_owner_email_otp,
    verify_owner_email_otp
)

urlpatterns = [
    # Owner Email OTP endpoints
    path('send-email-otp/', send_owner_email_otp, name='send-owner-email-otp'),
    path('verify-email-otp/', verify_owner_email_otp, name='verify-owner-email-otp'),

    # Registration flow
    path('register/', register_owner, name='register-owner'),
    path('register/verify-otps/', verify_registration_otps, name='verify-registration-otps'),
    path('register/verify-digilocker/', verify_digilocker, name='verify-digilocker'),
    path('register/upload-documents/', upload_business_documents, name='upload-business-documents'),

    # Login flow
    path('login/', login_owner_request, name='login-owner-request'),
    path('login/verify-otp/', login_owner_verify, name='login-owner-verify'),

    # Profile flow
    path('profile/<int:owner_id>/', owner_profile, name='owner-profile'),

    # Admin action
    path('admin-approve/<int:owner_id>/', admin_approve_owner, name='admin-approve-owner'),

    # Firebase Real Verification flow
    path('register/verify-firebase-email/', verify_firebase_email_otp, name='verify-firebase-email'),
    path('login/firebase/', login_owner_firebase, name='login-owner-firebase'),
]



