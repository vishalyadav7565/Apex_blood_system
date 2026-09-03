from django.urls import path
from ambulance_apps.ambulance.views import (
    register_ambulance,
    list_ambulances,
    ambulance_detail,
    approve_ambulance,
    reject_ambulance,
)

urlpatterns = [
    # Registration endpoint
    path('register/', register_ambulance, name='register-ambulance'),

    # Base collection endpoints: GET to list, POST to register
    path('', lambda request: register_ambulance(request) if request.method == 'POST' else list_ambulances(request), name='ambulance-collection'),

    # Detail endpoint: GET, PUT, PATCH, DELETE
    path('<int:pk>/', ambulance_detail, name='ambulance-detail'),

    # Admin approval & rejection endpoints
    path('<int:pk>/approve/', approve_ambulance, name='approve-ambulance'),
    path('<int:pk>/reject/', reject_ambulance, name='reject-ambulance'),
]
