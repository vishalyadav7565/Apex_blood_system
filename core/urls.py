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

    # AMBULANCE
    path(
        'api/ambulance/',
        include('ambulance_apps.ambulance.urls')
    ),

    # DRIVERS
    path(
        'api/drivers/',
        include('ambulance_apps.drivers.urls')
    ),

    # OWNERS
    path(
        'api/owners/',
        include('ambulance_apps.owners.urls')
    ),

    # DOCUMENTS (OpenCV & OCR)
    path(
        'api/documents/',
        include('ambulance_apps.documents.urls')
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

# SWAGGER & API DOCUMENTATION (SAFE CONDITIONAL IMPORT)
try:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui-root'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
except ImportError:
    pass

# MEDIA & STATIC FILES
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += staticfiles_urlpatterns()

