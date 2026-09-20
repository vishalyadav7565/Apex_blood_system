from django.contrib import admin
from django.urls import path, include, re_path

from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from django.http import JsonResponse
from ambulance_apps.trips.views import verify_pickup_otp

def root_health_check(request):
    return JsonResponse({
        "status": "healthy",
        "service": "Apex Life Saver Backend API",
        "version": "1.0.0"
    })

urlpatterns = [

    # ROOT HEALTH CHECK
    path(
        '',
        root_health_check,
        name='root-health-check'
    ),

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
    path(
        'api/ambulances/',
        include('ambulance_apps.ambulance.urls')
    ),
    path(
        'api/owners/ambulances/',
        include('ambulance_apps.ambulance.urls')
    ),

    # AMBULANCE BOOKINGS
    path(
        'api/ambulance/bookings/',
        include('ambulance_apps.trips.urls')
    ),

    # DRIVERS
    path(
        'api/drivers/',
        include('ambulance_apps.drivers.urls')
    ),
    path(
        'api/ambulance/drivers/',
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

    # VERIFICATION SESSIONS (WebSocket & Mobile QR)
    path(
        'api/verification/',
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

    # FALLBACK ROUTING FOR MALFORMED CLIENT VERIFY-PICKUP-OTP REQUESTS
    re_path(
        r'^api/.*(?:ambulance/bookings|trip)/(?P<trip_id>\d+)/verify-pickup-otp/?$',
        verify_pickup_otp,
        name='global-verify-pickup-otp'
    ),
    re_path(
        r'^api/.*verify-pickup-otp/(?P<trip_id>\d+)/?$',
        verify_pickup_otp,
        name='global-verify-pickup-otp-fallback'
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

# MEDIA & STATIC FILES (SERVE UNCONDITIONALLY FOR PRODUCTION & DOCKER DEPLOYMENTS)
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^api/media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
