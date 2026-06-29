from os import name

from django.urls import path


from .views import (
    all_hospitals,
    nearby_hospitals,
    save_hospital_fcm_token,
    verify_hospital,
    register_hospital,
    login_hospital,
    get_inventory,
    add_stock,
    remove_stock,
    hospital_profile,
    update_hospital_profile,
    hospital_stats
)

urlpatterns = [

    # ==========================================
    # 📍 NEARBY HOSPITALS
    # ==========================================
    path(
        'nearby/',
        nearby_hospitals,
        name='nearby_hospitals'
    ),

    # ==========================================
    # ✅ VERIFY HOSPITAL
    # ==========================================
    path(
        'hospitals/<int:id>/verify/',
        verify_hospital,
        name='verify_hospital'
    ),

    # ==========================================
    # 🚀 REGISTER HOSPITAL
    # ==========================================
    path(
        'register/',
        register_hospital,
        name='register_hospital'
    ),

    # ==========================================
    # 🔐 LOGIN HOSPITAL
    # ==========================================
    path(
        'login/',
        login_hospital,
        name='login_hospital'
    ),

    # ==========================================
    # 🩸 GET INVENTORY
    # ==========================================
    path(
        'inventory/',
        get_inventory,
        name='get_inventory'
    ),

    # ==========================================
    # ➕ ADD STOCK
    # ==========================================
    path(
        'inventory/add/',
        add_stock,
        name='add_stock'
    ),
    path(
    'inventory/remove/',
    remove_stock,
    name='remove_stock'
),
path(
    "profile/<int:id>/",
    hospital_profile
),
path(
    "profile/<int:id>/update/",
    update_hospital_profile
),
path(
    "all/",
    all_hospitals,
    name="all_hospitals"
),
path(
    "stats/",
    hospital_stats,
    name="hospital_stats"
),
path(
    "save_hospital_fcm_token/",
    save_hospital_fcm_token
),
]