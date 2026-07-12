from django.urls import path

from .consumers import (
    RequestConsumer
)

websocket_urlpatterns = [

    path(
        "ws/admin/",
        RequestConsumer.as_asgi()
    ),

    # Standard User path
    path(
        "ws/user/<int:user_id>/",
        RequestConsumer.as_asgi()
    ),
    # Alias User path (for Flutter client compatibility)
    path(
        "ws/requests/user/<int:user_id>/",
        RequestConsumer.as_asgi()
    ),

    # Standard Hospital path
    path(
        "ws/hospital/<int:hospital_id>/",
        RequestConsumer.as_asgi()
    ),
    # Alias Hospital path (for Flutter client compatibility)
    path(
        "ws/requests/hospital/<int:hospital_id>/",
        RequestConsumer.as_asgi()
    ),
]