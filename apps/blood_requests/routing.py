from django.urls import path

from .consumers import (
    RequestConsumer
)

websocket_urlpatterns = [

    path(
        "ws/admin/",
        RequestConsumer.as_asgi()
    ),

    path(
        "ws/user/<int:user_id>/",
        RequestConsumer.as_asgi()
    ),

    path(
        "ws/hospital/<int:hospital_id>/",
        RequestConsumer.as_asgi()
    ),
]