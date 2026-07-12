from django.urls import path

from .views import (
    create_request,
    current_request,
    get_requests,
    get_request,
    hospital_accept,
    complete_request,
    fallback_donors,
    match_donors,
    my_requests,
    reject_request
)

urlpatterns = [

    path('', get_requests),

    path('create/', create_request),

    path('my-requests/', my_requests),
    
    path(
    "current-request/",
    current_request
),

    path('fallback/', fallback_donors),

    path('<int:id>/get/', get_request),
    path('detail/<int:id>/', get_request),
    path('detail/<int:id>', get_request),

    path('<int:id>/accept/', hospital_accept),

    path('<int:id>/complete/', complete_request),

    path('<int:id>/reject/', reject_request),

    path('<int:id>/donors/', match_donors),
]

