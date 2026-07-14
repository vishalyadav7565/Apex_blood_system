import os

from django.core.asgi import get_asgi_application
from django.urls import path

from channels.routing import (
    ProtocolTypeRouter,
    URLRouter
)

from apps.blood_requests.consumers import (
    RequestConsumer
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "core.settings"
)

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({

    "http": django_asgi_app,

    "websocket": URLRouter([

        # Admin Dashboard
        path(
            "ws/requests/",
            RequestConsumer.as_asgi()
        ),

        # Hospital specific socket
        path(
            "ws/hospital/<int:hospital_id>/",
            RequestConsumer.as_asgi()
        ),
        path(
            "ws/requests/hospital/<int:hospital_id>/",
            RequestConsumer.as_asgi()
        ),

        # User specific socket
        path(
            "ws/user/<int:user_id>/",
            RequestConsumer.as_asgi()
        ),
        path(
            "ws/requests/user/<int:user_id>/",
            RequestConsumer.as_asgi()
        ),

    ]),
})