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
    advanced_users,
    user_profile,
    blood_request_detail,
    ambulance_request_detail,
    toggle_user_active,
    add_admin_user,
    live_users_map,
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
    approve_ambulance_admin,
    reject_ambulance_admin,
    update_user_profile,
)
from apps.users.views import pincode_lookup_view

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
        advanced_users
    ),
    path('users/<int:user_id>/profile/', user_profile),
    path('users/<int:user_id>/update/', update_user_profile),
    path('users/<int:user_id>/toggle-active/', toggle_user_active),
    path('users/add-user/', add_admin_user),
    path('users/live-map/', live_users_map),
    path('pincode/<str:pincode>/', pincode_lookup_view),
    path('requests/blood/<int:request_id>/', blood_request_detail),
    path('requests/ambulance/<int:request_id>/', ambulance_request_detail),

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
    path(
        "ambulances/<int:id>/approve/",
        approve_ambulance_admin
    ),
    path(
        "ambulances/<int:id>/reject/",
        reject_ambulance_admin
    ),
]
