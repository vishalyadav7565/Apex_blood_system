from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.users.views import create_support_ticket, firebase_login

urlpatterns = [

    # ADMIN
    path(
        'admin/',
        admin.site.urls
    ),

    # AUTH & FIREBASE LOGIN ALIASES
    path('api/auth/firebase-login/', firebase_login),
    path('api/auth/firebase-login', firebase_login),
    path('api/users/firebase-login/', firebase_login),
    path('api/users/firebase-login', firebase_login),

    # HELP & SUPPORT ALIASES
    path('api/users/support/create/', create_support_ticket),
    path('api/users/support/create', create_support_ticket),
    path('api/users/support/', create_support_ticket),
    path('api/users/support', create_support_ticket),
    path('api/support/create/', create_support_ticket),
    path('api/support/create', create_support_ticket),
    path('api/support/', create_support_ticket),
    path('api/support', create_support_ticket),

    # USERS
    path(
        'api/users/',
        include('apps.users.urls')
    ),

    # HOSPITALS
    path(
        'api/hospitals/',
        include('apps.hospitals.urls')
    ),

    # BLOOD REQUESTS
    path(
        'api/requests/',
        include('apps.blood_requests.urls')
    ),

    # ADMIN PANEL
    path(
        'api/admin/',
        include('apps.admin_panel.urls')
    ),

    # JWT AUTH
    path(
        'api/token/',
        TokenObtainPairView.as_view(),
        name='token_obtain_pair'
    ),

    path(
        'api/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),
]

# MEDIA FILES
if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

