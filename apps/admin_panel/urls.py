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
    get_ambulance_owners,
    verify_ambulance_owner,
    get_ambulance_drivers,
    verify_ambulance_driver,
    get_ambulances,
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
    path(
        "ambulance-owners/",
        get_ambulance_owners
    ),
    path(
        "ambulance-owners/<int:id>/verify/",
        verify_ambulance_owner
    ),
    path(
        "ambulance-drivers/",
        get_ambulance_drivers
    ),
    path(
        "ambulance-drivers/<int:id>/verify/",
        verify_ambulance_driver
    ),
    path(
        "ambulances/",
        get_ambulances
    ),
]
