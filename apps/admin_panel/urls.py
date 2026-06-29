from django.urls import path

from .views import (
    admin_profile,
    all_hospitals,
    export_requests,
    set_hospital_status,
    dashboard,
    map_data,
    admin_login,
    all_users,
    analytics_dashboard,
    hospital_performance,
    blood_group_trends,
    send_custom_notification,
    all_support_tickets,
    update_support_status,
)

urlpatterns = [

    path(
        'login/',
        admin_login
    ),
     path(
        'profile/',
        admin_profile
    ),

    path(
        'dashboard/',
        dashboard
    ),

    path(
        'map/',
        map_data
    ),

    path(
        'users/',
        all_users
    ),

    path(
        'hospitals/',
        all_hospitals
    ),

    path(
        'hospitals/<int:id>/status/',
        set_hospital_status
    ),
     path(
        "analytics/",
        analytics_dashboard
    ),

    path(
        "hospital-performance/",
        hospital_performance
    ),

    path(
        "blood-group-trends/",
        blood_group_trends
    ),

    path(
        "export-requests/",
        export_requests
    ),
    path(
        "send-notification/",
        send_custom_notification
    ),
    path(
        "support/",
        all_support_tickets
    ),
    path(
        "support/<int:id>/status/",
        update_support_status
    ),
]
