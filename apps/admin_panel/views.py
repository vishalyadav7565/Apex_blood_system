import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q

logger = logging.getLogger(__name__)
import pandas as pd
import numpy as np
from apps.blood_requests.models import BloodRequest
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny
)
from apps.hospitals.models import (
    Hospital,
    BloodInventory
)

from apps.blood_requests.models import (
    BloodRequest
)

from django.contrib.auth import authenticate

from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User, HelpSupport, UserActivityLog
from apps.blood_requests.models import BloodRequest
from apps.hospitals.models import Hospital
from apps.notifications.utils import send_push_notification
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from ambulance_apps.owners.models import Owner
from ambulance_apps.drivers.models import Driver
from ambulance_apps.ambulance.models import Ambulance
from ambulance_apps.trips.models import AmbulanceRequest
from ambulance_apps.trips.models import Trip


from django.views.decorators.csrf import csrf_exempt


def _admin_only(request):
    return request.user.is_authenticated and request.user.is_staff


def _request_status(request):
    return request.get('detailed_status') or request.get('status') or ''


def _serialize_admin_user(user, blood_requests, ambulance_requests):
    return {
        'id': user.id,
        'user_id_code': user.user_id_code or f'ALS-{10000 + user.id}',
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
        'phone': user.phone,
        'email': user.email,
        'blood_group': user.blood_group,
        'age': user.age,
        'gender': user.gender,
        'state': user.state,
        'district': user.district,
        'city': user.city,
        'address': user.address,
        'pincode': user.pincode,
        'is_donor': user.is_donor,
        'is_available': user.is_available,
        'is_active': user.is_active,
        'latitude': user.latitude,
        'longitude': user.longitude,
        'created_at': user.created_at,
        'updated_at': user.updated_at,
        'last_active': user.last_active,
        'last_login': user.last_login,
        'total_active_days': user.total_active_days,
        'blood_requests': blood_requests,
        'ambulance_requests': ambulance_requests,
        'activity_logs': [
            {
                'id': log.id,
                'activity_type': log.activity_type,
                'title': log.title,
                'description': log.description,
                'reference_id': log.reference_id,
                'created_at': log.created_at,
            }
            for log in UserActivityLog.objects.filter(user_id=user.id)[:100]
        ],
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def advanced_users(request):
    if not _admin_only(request):
        return Response({'error': 'Admin permission required.'}, status=status.HTTP_403_FORBIDDEN)

    now = timezone.now()
    search = request.query_params.get('search', '').strip()
    state = request.query_params.get('state', '').strip()
    district = request.query_params.get('district', '').strip()
    blood_group = request.query_params.get('blood_group', '').strip()
    activity_status = request.query_params.get('activity_status', '').strip()

    users = User.objects.all()
    if search:
        users = users.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
            | Q(user_id_code__icontains=search)
        )
    if state:
        users = users.filter(state__iexact=state)
    if district:
        users = users.filter(district__iexact=district)
    if blood_group:
        users = users.filter(blood_group__iexact=blood_group)

    blood_rows = list(BloodRequest.objects.select_related('accepted_hospital').order_by('-created_at'))
    ambulance_rows = list(AmbulanceRequest.objects.using('ambulance_db').select_related('driver').order_by('-created_at'))
    trip_rows = list(Trip.objects.using('ambulance_db').select_related('driver__ambulance').order_by('-created_at'))

def _get_prescription_image_url(item, request=None):
    img = item.prescription_image or item.prescription
    if not img:
        return None
    val = str(img).strip()
    if not val:
        return None
    if val.startswith('http://') or val.startswith('https://'):
        return val
    try:
        url = img.url
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if url.startswith('/media/http://') or url.startswith('/media/https://'):
            return url.replace('/media/', '', 1)
        if request:
            return request.build_absolute_uri(url)
        return f"https://api.apexlifesaver.com{url}"
    except Exception:
        return f"https://api.apexlifesaver.com/media/{val}"


def _get_hospital_info(hospital):
    if not hospital:
        return None
    return {
        'id': hospital.id,
        'name': hospital.name,
        'phone': hospital.phone,
        'email': hospital.email,
        'address': hospital.address,
    }


    blood_by_user = {}
    blood_user_ids = set()
    for item in blood_rows:
        blood_user_ids.add(item.user_id)
        hospital = item.accepted_hospital
        blood_by_user.setdefault(item.user_id, []).append({
            'id': item.id,
            'request_code': item.request_code or f'#BR-{10000 + item.id}',
            'patient_name': item.patient_name or item.user_name,
            'patient_phone': item.patient_phone or item.user_phone,
            'blood_group': item.blood_group,
            'units': item.units or item.blood_units,
            'reason': item.reason,
            'status': item.status,
            'user_address': item.user_address,
            'latitude': item.latitude,
            'longitude': item.longitude,
            'prescription_image': _get_prescription_image_url(item, request),
            'accepted_hospital': hospital.name if hospital else None,
            'hospital_details': _get_hospital_info(hospital),
            'created_at': item.created_at,
        })

    ambulance_by_user = {}
    ambulance_user_ids = set()
    for item in ambulance_rows:
        ambulance_user_ids.add(item.user_id)
        ambulance_by_user.setdefault(item.user_id, []).append({
            'id': item.id,
            'request_code': item.request_code or f'#AR-{20000 + item.id}',
            'patient_name': item.patient_name,
            'patient_phone': item.patient_phone,
            'emergency_type': item.emergency_type,
            'pickup_address': item.pickup_address,
            'pickup_latitude': item.pickup_latitude,
            'pickup_longitude': item.pickup_longitude,
            'destination_address': item.destination_address,
            'hospital_name': item.hospital_name,
            'driver_name': item.driver.name if item.driver else None,
            'driver_phone': item.driver.phone if item.driver else None,
            'vehicle_number': item.vehicle_number or (item.driver.ambulance.vehicle_number if item.driver and item.driver.ambulance else None),
            'status': item.status,
            'created_at': item.created_at,
        })

    # Existing ambulance bookings are stored as Trip records and are included
    # until all clients write the dedicated AmbulanceRequest model.
    phone_to_user_id = dict(User.objects.filter(phone__isnull=False).values_list('phone', 'id'))
    for item in trip_rows:
        user_id = phone_to_user_id.get(item.patient_phone)
        if not user_id:
            continue
        ambulance_user_ids.add(user_id)
        ambulance_by_user.setdefault(user_id, []).append({
            'id': item.id,
            'request_code': f'#AR-{20000 + item.id}',
            'patient_name': item.patient_name,
            'patient_phone': item.patient_phone,
            'emergency_type': 'Medical Emergency',
            'pickup_address': item.pickup_address,
            'pickup_latitude': item.pickup_latitude,
            'pickup_longitude': item.pickup_longitude,
            'destination_address': item.destination_address,
            'hospital_name': item.driver.ambulance.hospital.name if item.driver and item.driver.ambulance and item.driver.ambulance.hospital else None,
            'driver_name': item.driver.name if item.driver else None,
            'driver_phone': item.driver.phone if item.driver else None,
            'vehicle_number': item.driver.ambulance.vehicle_number if item.driver and item.driver.ambulance else None,
            'status': item.status,
            'created_at': item.created_at,
        })

    if activity_status == 'active_now':
        users = users.filter(is_available=True)
    elif activity_status == 'active_today':
        users = users.filter(Q(last_active__date=now.date()) | Q(last_login__date=now.date()))
    elif activity_status == 'inactive_7d':
        users = users.filter(Q(last_active__lt=now - timedelta(days=7)) | Q(last_active__isnull=True))
    elif activity_status == 'inactive_30d':
        users = users.filter(Q(last_active__lt=now - timedelta(days=30)) | Q(last_active__isnull=True))
    elif activity_status == 'blood_users':
        users = users.filter(id__in=blood_user_ids)
    elif activity_status == 'ambulance_users':
        users = users.filter(id__in=ambulance_user_ids)
    elif activity_status == 'no_requests':
        users = users.exclude(id__in=blood_user_ids | ambulance_user_ids)

    users = list(users.order_by('-id'))
    results = [
        _serialize_admin_user(
            user,
            blood_by_user.get(user.id, []),
            ambulance_by_user.get(user.id, []),
        )
        for user in users
    ]
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_blood = sum(1 for item in blood_rows if item.created_at >= month_start)
    monthly_ambulance = sum(1 for item in ambulance_rows if item.created_at >= month_start)
    monthly_ambulance += sum(1 for item in trip_rows if item.created_at >= month_start)
    return Response({
        'count': len(results),
        'overview_stats': {
            'total_users': User.objects.count(),
            'active_today': User.objects.filter(Q(last_active__date=now.date()) | Q(last_login__date=now.date())).count(),
            'inactive_7d': User.objects.filter(Q(last_active__lt=now - timedelta(days=7)) | Q(last_active__isnull=True)).count(),
            'requests_this_month': monthly_blood + monthly_ambulance,
            'active_now': User.objects.filter(is_available=True).count(),
        },
        'results': results,
    })


# =========================================
# 🔐 ADMIN LOGIN
# =========================================
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def admin_login(request):

    username = request.data.get("username")

    password = request.data.get("password")

    user = authenticate(

        username=username,

        password=password
    )

    # ✅ CHECK ADMIN
    if user is not None and user.is_staff:

        refresh = RefreshToken.for_user(user)

        return Response({

            "success": True,

            "token":
                str(refresh.access_token),

            "refresh":
                str(refresh),

            "admin": {

                "id": user.id,

                "username": user.username,

                "is_staff": user.is_staff,
            }
        })

    return Response({

        "success": False,

        "message":
            "Invalid admin credentials"

    }, status=401)

    # =========================================
# 👤 ADMIN PROFILE
# =========================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])

def admin_profile(request):

    # ✅ ONLY ADMIN
    if not request.user.is_staff:

        return Response({

            "error":
                "Unauthorized"

        }, status=403)

    user = request.user

    return Response({

        "id":
            user.id,

        "username":
            user.username,

        "email":
            user.email,

        "first_name":
            user.first_name,

        "last_name":
            user.last_name,

        "is_staff":
            user.is_staff,

        "date_joined":
            user.date_joined,
    })


# =========================================
# 📊 DASHBOARD
# =========================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])

def dashboard(request):

    # ✅ ONLY ADMIN
    if not request.user.is_staff:

        return Response({

            "error": "Unauthorized"

        }, status=403)

    return Response({

        "total_users":
            User.objects.count(),

        "total_requests":
            BloodRequest.objects.count(),

        "total_hospitals":
            Hospital.objects.count(),

        "active_donors":
            User.objects.filter(

                is_available=True,

                is_donor=True
            ).count(),

        "verified_hospitals":
            Hospital.objects.filter(

                is_verified=True
            ).count(),

        "pending_requests":
            BloodRequest.objects.filter(

                status__in=['pending', 'broadcasting', 'searching_hospital', 'searching_next_hospital']
            ).count(),
    })


# =========================================
# 🗺️ MAP DATA
# =========================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])

def map_data(request):

    # ✅ ONLY ADMIN
    if not request.user.is_staff:

        return Response({

            "error": "Unauthorized"

        }, status=403)

    users = User.objects.exclude(

        latitude=None,

        longitude=None
    )

    hospitals = Hospital.objects.exclude(

        latitude=None,

        longitude=None
    )

    requests = BloodRequest.objects.exclude(

        latitude=None,

        longitude=None
    )

    return Response({

        "users": list(

            users.values(

                'id',

                'phone',

                'blood_group',

                'latitude',

                'longitude',

                'is_available',

                'is_donor'
            )
        ),

        "hospitals": list(

            hospitals.values(

                'id',

                'name',

                'latitude',

                'longitude',

                'is_verified'
            )
        ),

        "requests": list(

            requests.values(

                'id',

                'blood_group',

                'latitude',

                'longitude',

                'status'
            )
        ),
    })


# =========================================
# 👥 ALL USERS
# =========================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])

def all_users(request):

    # ✅ ONLY ADMIN
    if not request.user.is_staff:

        return Response({

            "error": "Unauthorized"

        }, status=403)

    users = User.objects.all().order_by('-id')

    data = []

    for user in users:

        data.append({

            "id":
                user.id,

            "username":
                user.username,

            "first_name":
                user.first_name,

            "last_name":
                user.last_name,

            "phone":
                user.phone,

            "age":
                user.age,

            "address":
                user.address,

            "blood_group":
                user.blood_group,

            "is_donor":
                user.is_donor,

            "is_available":
                user.is_available,

            "latitude":
                user.latitude,

            "longitude":
                user.longitude,

            "created_at":
                user.created_at,
        })

    return Response(data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_hospitals(request):

    if not request.user.is_staff:
        return Response(
            {"error": "Unauthorized"},
            status=403
        )

    hospitals = Hospital.objects.all().order_by("-id")

    data = []

    for hospital in hospitals:

        # Hospital Inventory Only
        inventory = BloodInventory.objects.filter(
            hospital=hospital
        )

        inventory_data = []
        total_units = 0

        for item in inventory:

            inventory_data.append({
                "blood_group": item.blood_group,
                "units": item.units
            })

            total_units += item.units

        # Request Stats
        # NOTE:
        # BloodRequest model me hospital FK hona chahiye.
        # Agar abhi nahi hai to temporary 0 rakho.

        total_requests = 0
        accepted_requests = 0
        pending_requests = 0

        recent_data = []

        data.append({

            "hospital": {

                "id": hospital.id,
                "name": hospital.name,
                "address": hospital.address,
                "phone": hospital.phone,
                "email": hospital.email,
                "latitude": hospital.latitude,
                "longitude": hospital.longitude,
                "is_verified": hospital.is_verified,
                "created_at": hospital.created_at,
            },

            "stats": {

                "total_inventory": total_units,
                "total_requests": total_requests,
                "accepted_requests": accepted_requests,
                "pending_requests": pending_requests,
            },

            "inventory": inventory_data,

            "recent_requests": recent_data,
        })

    return Response(data)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_hospital_status(request, id):

    if not request.user.is_staff:
        return Response(
            {"error": "Unauthorized"},
            status=403
        )

    try:
        hospital = Hospital.objects.get(id=id)

        is_verified = request.data.get(
            "is_verified"
        )

        if is_verified is not None:
            hospital.is_verified = is_verified

        hospital.save()

        return Response({
            "id": hospital.id,
            "name": hospital.name,
            "is_verified": hospital.is_verified
        })

    except Hospital.DoesNotExist:
        return Response(
            {"error": "Hospital not found"},
            status=404
        )
    
@api_view(["GET"])
def analytics_dashboard(request):

    today = timezone.now().date()

    week_start = today - timedelta(days=7)

    month_start = today - timedelta(days=30)

    total_requests = BloodRequest.objects.count()

    pending = BloodRequest.objects.filter(
        status__in=["pending", "broadcasting", "searching_hospital"]
    ).count()

    accepted = BloodRequest.objects.filter(
        status="accepted"
    ).count()

    rejected = BloodRequest.objects.filter(
        status="rejected"
    ).count()

    searching = BloodRequest.objects.filter(
        status__in=["searching_next_hospital", "searching_donor"]
    ).count()

    completed = BloodRequest.objects.filter(
        status="completed"
    ).count()

    today_requests = BloodRequest.objects.filter(
        created_at__date=today
    ).count()

    weekly_requests = BloodRequest.objects.filter(
        created_at__date__gte=week_start
    ).count()

    monthly_requests = BloodRequest.objects.filter(
        created_at__date__gte=month_start
    ).count()

    blood_groups = list(
        BloodRequest.objects
        .values("blood_group")
        .annotate(count=Count("id"))
    )

    hospitals = Hospital.objects.count()

    donors = User.objects.filter(
        is_donor=True
    ).count()

    return Response({
        "total_requests": total_requests,
        "pending_requests": pending,
        "accepted_requests": accepted,
        "rejected_requests": rejected,
        "searching_requests": searching,
        "completed_requests": completed,
        "today_requests": today_requests,
        "weekly_requests": weekly_requests,
        "monthly_requests": monthly_requests,
        "total_hospitals": hospitals,
        "total_donors": donors,
        "blood_group_stats": blood_groups,
    })

@api_view(["GET"])
def hospital_performance(request):

    hospitals = Hospital.objects.all()

    data = []

    for hospital in hospitals:

        accepted = BloodRequest.objects.filter(
            accepted_hospital=hospital
        ).count()

        data.append({
            "hospital": hospital.name,
            "accepted_requests": accepted,
        })

    return Response(data)
@api_view(["GET"])
def blood_group_trends(request):

    qs = BloodRequest.objects.values(
        "blood_group"
    )

    df = pd.DataFrame(list(qs))

    if df.empty:
        return Response([])

    trend = (
        df.groupby("blood_group")
        .size()
        .reset_index(name="count")
        .to_dict("records")
    )

    return Response(trend)


@api_view(['GET'])
def export_requests(request):

    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    hospital_id = request.GET.get("hospital_id")
    blood_group = request.GET.get("blood_group")
    status_filter = request.GET.get("status")

    requests = BloodRequest.objects.all()

    # Date Filter
    if from_date:
        requests = requests.filter(
            created_at__date__gte=from_date
        )

    if to_date:
        requests = requests.filter(
            created_at__date__lte=to_date
        )

    # Hospital Filter
    if hospital_id:
        requests = requests.filter(
            accepted_hospital_id=hospital_id
        )

    # Blood Group Filter
    if blood_group:
        requests = requests.filter(
            blood_group=blood_group
        )

    # Status Filter
    if status_filter:
        requests = requests.filter(
            status=status_filter
        )

    data = []

    for req in requests:

        data.append({

            "Request ID":
                req.id,

            "Patient Name":
                req.user_name,

            "Phone":
                req.user_phone,

            "Email":
                req.user_email,

            "Address":
                req.user_address,

            "Blood Group":
                req.blood_group,

            "Status":
                req.status,

            "Hospital":
                req.accepted_hospital.name
                if req.accepted_hospital
                else "",

            "Hospital Phone":
                req.accepted_hospital.phone
                if req.accepted_hospital
                else "",

            "Created At":
                req.created_at.strftime(
                    "%d-%m-%Y %H:%M:%S"
                ) if req.created_at else "",
        })

    df = pd.DataFrame(data)

    response = HttpResponse(
        content_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; '
        'filename="blood_requests_report.xlsx"'
    )

    with pd.ExcelWriter(
        response,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Requests",
            index=False
        )

    return response


# =========================================
# 📢 SEND CUSTOM BROADCAST NOTIFICATION
# =========================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_custom_notification(request):
    # Only staff/admin
    if not request.user.is_staff:
        return Response(
            {"error": "Unauthorized admin access"},
            status=403
        )

    title = request.data.get("title")
    body = request.data.get("body")
    target_type = request.data.get("target_type", "all")  # all, donors, hospitals
    pincode = request.data.get("pincode")
    blood_group = request.data.get("blood_group")
    hospital_id = request.data.get("hospital_id")

    if not title or not body:
        return Response(
            {"error": "title and body are required"},
            status=400
        )

    tokens = []

    # 0a. Handle Single Hospital targeting (Notifies ONLY that specific Hospital on the Hospital App)
    if target_type == "single_hospital":
        if not hospital_id:
            return Response(
                {"error": "hospital_id is required for single hospital targeting"},
                status=400
            )
        try:
            h = Hospital.objects.get(id=hospital_id)
            if h.fcm_token:
                tokens.append((h.fcm_token, "hospital"))
        except Hospital.DoesNotExist:
            return Response({"error": "Hospital not found"}, status=404)

    # 0b. Handle Donation Camp specific targeting (Donors only + Mandatory Pincode on User App)
    elif target_type == "donation_camp":
        if not pincode:
            return Response(
                {"error": "pincode is required for donation camp targeting"},
                status=400
            )
        
        users = User.objects.filter(is_donor=True, pincode=pincode).exclude(fcm_token__isnull=True).exclude(fcm_token="")
        if blood_group:
            users = users.filter(blood_group=blood_group)
        
        for u in users:
            if u.fcm_token:
                tokens.append((u.fcm_token, "donor"))

    # 1. Fetch matching Users / Donors (User App)
    elif target_type in ["all", "donors", "users"]:
        users = User.objects.exclude(fcm_token__isnull=True).exclude(fcm_token="")
        if target_type == "donors":
            users = users.filter(is_donor=True)
        if pincode:
            users = users.filter(pincode=pincode)
        if blood_group:
            users = users.filter(blood_group=blood_group)
        
        for u in users:
            if u.fcm_token:
                tokens.append((u.fcm_token, "user"))

    # 2. Fetch matching Hospitals (Hospital App)
    if target_type in ["all", "hospitals"]:
        hospitals = Hospital.objects.exclude(fcm_token__isnull=True).exclude(fcm_token="")
        if pincode:
            hospitals = hospitals.filter(pincode=pincode)
        
        for h in hospitals:
            if h.fcm_token:
                tokens.append((h.fcm_token, "hospital"))

    # Deduplicate tokens
    unique_tokens = list(set(tokens))

    success_count = 0
    failure_count = 0

    for token, role in unique_tokens:
        success = send_push_notification(
            token=token,
            title=title,
            body=body,
            data={
                "event": "CUSTOM_BROADCAST",
                "target_type": target_type,
                "role": role
            }
        )
        if success:
            success_count += 1
        else:
            failure_count += 1

    return Response({
        "success": True,
        "total_targets": len(unique_tokens),
        "success_count": success_count,
        "failure_count": failure_count
    })


# ==========================================
# ADMIN HELP & SUPPORT TICKETS MANAGEMENT
# ==========================================
@api_view(['GET'])
def all_support_tickets(request):

    tickets = HelpSupport.objects.all().order_by('-created_at')

    data = []

    for t in tickets:
        data.append({
            "id": t.id,
            "user_id": t.user.id if t.user else None,
            "name": t.name or (f"{t.user.first_name} {t.user.last_name}".strip() if t.user else "Anonymous"),
            "email": t.email or (t.user.email if t.user else None),
            "phone": t.phone or (t.user.phone if t.user else None),
            "subject": t.subject,
            "message": t.message,
            "status": t.status,
            "created_at": timezone.localtime(t.created_at).isoformat() if t.created_at else None,
        })

    return Response(data)


@api_view(['POST', 'PATCH', 'PUT'])
def update_support_status(request, id):

    try:
        ticket = HelpSupport.objects.get(id=id)
    except HelpSupport.DoesNotExist:
        return Response({"error": "Support ticket not found"}, status=404)

    status_val = request.data.get("status")

    if not status_val:
        return Response({"error": "status is required"}, status=400)

    ticket.status = status_val
    ticket.save()

    return Response({
        "success": True,
        "message": "Support ticket status updated",
        "ticket": {
            "id": ticket.id,
            "status": ticket.status,
            "subject": ticket.subject
        }
    })


def get_owner_media_url(file_field, request=None):
    if not file_field:
        return None
    try:
        url = file_field.url
    except Exception:
        url = str(file_field) if file_field else None

    if not url:
        return None

    if url.startswith('http') or url.startswith('data:') or url.startswith('blob:'):
        return url

    clean_path = url.lstrip('/')
    if clean_path.startswith('api/media/'):
        clean_path = clean_path[len('api/media/'):]
    elif clean_path.startswith('media/'):
        clean_path = clean_path[len('media/'):]

    full_path = f"/api/media/{clean_path}"

    if request is not None:
        host = request.get_host()
        if 'localhost' in host or '127.0.0.1' in host or 'web' in host:
            return f"https://api.apexlifesaver.com{full_path}"
        return request.build_absolute_uri(full_path)

    return f"https://api.apexlifesaver.com{full_path}"


def serialize_owner_data(owner, request=None):
    aadhaar_card = owner.aadhaar_card
    aadhaar_card_back = getattr(owner, 'aadhaar_card_back', None)
    selfie = owner.selfie
    business_doc = owner.business_doc

    # Auto-fallback to real-time VerificationSession images if owner record fields are unpopulated
    if not aadhaar_card or not aadhaar_card_back or not selfie:
        try:
            from ambulance_apps.documents.models import VerificationSession
            vs = VerificationSession.objects.order_by('-updated_at').first()

            if vs:
                if not aadhaar_card and vs.aadhaar_front:
                    aadhaar_card = vs.aadhaar_front
                if not aadhaar_card_back and vs.aadhaar_back:
                    aadhaar_card_back = vs.aadhaar_back
                if not selfie and vs.selfie:
                    selfie = vs.selfie
        except Exception as sync_err:
            logger.warning(f"Error fetching verification session fallback images: {sync_err}")

    return {
        "id": owner.id,
        "name": owner.name,
        "email": owner.email,
        "phone": owner.phone,
        "company_name": owner.company_name,
        "address": owner.address,
        "verification_status": owner.verification_status,
        "is_verified": owner.is_verified,
        "is_email_verified": owner.is_email_verified,
        "is_phone_verified": owner.is_phone_verified,
        "is_aadhaar_verified": owner.is_aadhaar_verified,
        "is_business_doc_verified": getattr(owner, 'is_business_doc_verified', False),
        "is_selfie_verified": getattr(owner, 'is_selfie_verified', False),
        "rejection_reason": owner.rejection_reason,
        "aadhaar_number": owner.aadhaar_number,
        "aadhaar_card": get_owner_media_url(aadhaar_card, request),
        "aadhaar_card_back": get_owner_media_url(aadhaar_card_back, request),
        "business_doc": get_owner_media_url(business_doc, request),
        "selfie": get_owner_media_url(selfie, request),
        "face_match_score": owner.face_match_score,
        "created_at": owner.created_at.isoformat() if owner.created_at else None,
    }


# ==========================================
# AMBULANCE & DRIVERS MANAGEMENT
# ==========================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ambulance_owners(request):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)

    owners = Owner.objects.all().order_by('-id')

    state = request.query_params.get('state')
    district = request.query_params.get('district')
    verification_status = request.query_params.get('verification_status')

    if state:
        owners = owners.filter(address__icontains=state)
    if district:
        owners = owners.filter(address__icontains=district)
    if verification_status:
        if verification_status == 'verified':
            owners = owners.filter(Q(verification_status='approved') | Q(is_verified=True))
        elif verification_status == 'pending':
            owners = owners.filter(verification_status__in=['pending_verification', 'pending_admin_review'])
        elif verification_status == 'rejected':
            owners = owners.filter(verification_status='rejected')

    data = [serialize_owner_data(owner, request) for owner in owners]
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_ambulance_owner(request, id):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)

    owner = get_object_or_404(Owner, id=id)
    action = request.data.get('action', 'approve')
    doc_type = request.data.get('doc_type', 'all')
    reason = request.data.get('reason', '')

    if doc_type == 'aadhaar':
        owner.is_aadhaar_verified = (action == 'approve')
    elif doc_type == 'business_doc':
        owner.is_business_doc_verified = (action == 'approve')
    elif doc_type == 'selfie':
        owner.is_selfie_verified = (action == 'approve')
    elif doc_type == 'all':
        if action == 'approve':
            owner.is_aadhaar_verified = True
            owner.is_business_doc_verified = True
            owner.is_selfie_verified = True
            owner.verification_status = 'approved'
            owner.is_verified = True
            owner.rejection_reason = None
        else:
            owner.verification_status = 'rejected'
            owner.is_verified = False
            owner.rejection_reason = reason or "Rejected by Super Admin"

    # Auto-promote to approved if all 3 documents are approved
    if owner.is_aadhaar_verified and owner.is_business_doc_verified and owner.is_selfie_verified and action == 'approve':
        owner.verification_status = 'approved'
        owner.is_verified = True
        owner.rejection_reason = None
    elif action == 'reject':
        owner.verification_status = 'rejected'
        owner.is_verified = False
        owner.rejection_reason = reason or f"{doc_type.replace('_', ' ').title()} rejected by Super Admin"

    owner.save()
    return Response(serialize_owner_data(owner, request))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ambulance_drivers(request):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)
        
    drivers = Driver.objects.all().order_by('-id')
    
    state = request.query_params.get('state')
    district = request.query_params.get('district')
    verification_status = request.query_params.get('verification_status')
    
    if state:
        drivers = drivers.filter(state__iexact=state)
    if district:
        drivers = drivers.filter(district__iexact=district)
    if verification_status:
        if verification_status == 'verified':
            drivers = drivers.filter(Q(verification_status='approved_by_admin') | Q(is_verified=True))
        elif verification_status == 'pending':
            drivers = drivers.filter(verification_status__in=['pending_owner_review', 'approved_by_owner', 'pending_admin_review'])
        elif verification_status == 'rejected':
            drivers = drivers.filter(verification_status__in=['rejected_by_owner', 'rejected_by_admin'])

    data = []
    for driver in drivers:
        data.append({
            "id": driver.id,
            "name": driver.name,
            "phone": driver.phone,
            "email": driver.email,
            "gender": driver.gender,
            "date_of_birth": driver.date_of_birth,
            "pincode": driver.pincode,
            "state": driver.state,
            "district": driver.district,
            "complete_address": driver.complete_address,
            "ambulance": {
                "id": driver.ambulance.id,
                "vehicle_number": driver.ambulance.vehicle_number,
                "ambulance_type": driver.ambulance.ambulance_type,
            } if driver.ambulance else None,
            "license_number": driver.license_number,
            "license_expiry": driver.license_expiry.isoformat() if driver.license_expiry else None,
            "aadhaar_number": driver.aadhaar_number,
            "aadhaar_card": driver.aadhaar_card.url if driver.aadhaar_card else None,
            "driving_licence": driver.driving_licence.url if driver.driving_licence else None,
            "photo": driver.photo.url if driver.photo else None,
            "profile_photo": driver.profile_photo.url if driver.profile_photo else None,
            "is_verified": driver.is_verified,
            "verification_status": driver.verification_status,
            "rejection_reason": driver.rejection_reason,
            "review_notes": driver.review_notes,
            "created_at": driver.created_at.isoformat() if driver.created_at else None,
        })
        
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_ambulance_driver(request, id):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)
        
    driver = get_object_or_404(Driver, id=id)
    action = request.data.get('action')  # 'approve' or 'reject'
    reason = request.data.get('reason', '')
    
    if action == 'approve':
        driver.verification_status = 'approved_by_admin'
        driver.is_verified = True
        driver.admin_reviewed_at = timezone.now()
        driver.rejection_reason = None
    elif action == 'reject':
        driver.verification_status = 'rejected_by_admin'
        driver.is_verified = False
        driver.rejection_reason = reason
        driver.admin_reviewed_at = timezone.now()
    else:
        return Response({"error": "Invalid action. Choose 'approve' or 'reject'"}, status=400)
        
    driver.save()
    return Response({
        "id": driver.id,
        "name": driver.name,
        "verification_status": driver.verification_status,
        "is_verified": driver.is_verified
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ambulances(request):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)
        
    ambulances = Ambulance.objects.all().order_by('-id')
    
    state = request.query_params.get('state')
    district = request.query_params.get('district')
    verification_status = request.query_params.get('verification_status') or request.query_params.get('approval_status')
    search = request.query_params.get('search')
    
    if state:
        ambulances = ambulances.filter(
            Q(driver__state__iexact=state) | 
            Q(hospital__address__icontains=state) |
            Q(owner__address__icontains=state)
        )
    if district:
        ambulances = ambulances.filter(
            Q(driver__district__iexact=district) | 
            Q(hospital__address__icontains=district) |
            Q(owner__address__icontains=district)
        )
    if verification_status:
        if verification_status in ['verified', 'approved']:
            ambulances = ambulances.filter(Q(approval_status='approved') | Q(is_approved=True))
        elif verification_status == 'pending':
            ambulances = ambulances.filter(approval_status='pending_admin_review')
        elif verification_status == 'rejected':
            ambulances = ambulances.filter(approval_status='rejected')

    if search:
        ambulances = ambulances.filter(
            Q(vehicle_number__icontains=search) |
            Q(registration_number__icontains=search) |
            Q(owner__name__icontains=search) |
            Q(owner__company_name__icontains=search) |
            Q(hospital__name__icontains=search)
        )

    data = []
    for amb in ambulances:
        data.append({
            "id": amb.id,
            "vehicle_number": amb.vehicle_number,
            "ambulance_type": amb.ambulance_type,
            "registration_number": amb.registration_number,
            "owner": {
                "id": amb.owner.id,
                "name": amb.owner.name,
                "company_name": amb.owner.company_name,
                "phone": amb.owner.phone,
                "email": amb.owner.email,
            } if amb.owner else None,
            "hospital": {
                "id": amb.hospital.id,
                "name": amb.hospital.name,
            } if amb.hospital else None,
            "is_active": amb.is_active,
            "is_available": amb.is_available,
            "is_approved": amb.is_approved,
            "approval_status": amb.approval_status,
            "rejection_reason": amb.rejection_reason,
            "status": amb.status,
            "created_at": amb.created_at.isoformat() if amb.created_at else None,
        })
        
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_ambulance_admin(request, id):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)
        
    try:
        ambulance = Ambulance.objects.get(id=id)
    except Ambulance.DoesNotExist:
        return Response({"error": f"Ambulance #{id} not found."}, status=404)

    ambulance.is_approved = True
    ambulance.approval_status = "approved"
    ambulance.is_active = True
    ambulance.rejection_reason = None
    ambulance.save()
    return Response({
        "message": "Ambulance approved successfully.",
        "id": ambulance.id,
        "vehicle_number": ambulance.vehicle_number,
        "approval_status": ambulance.approval_status,
        "is_approved": ambulance.is_approved
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_ambulance_admin(request, id):
    if not request.user.is_staff:
        return Response({"error": "Unauthorized"}, status=403)
        
    try:
        ambulance = Ambulance.objects.get(id=id)
    except Ambulance.DoesNotExist:
        return Response({"error": f"Ambulance #{id} not found."}, status=404)

    reason = request.data.get('reason') or request.data.get('rejection_reason') or 'Registration rejected by admin.'
    ambulance.is_approved = False
    ambulance.approval_status = "rejected"
    ambulance.is_active = False
    ambulance.rejection_reason = reason
    ambulance.save()
    return Response({
        "message": "Ambulance rejected.",
        "id": ambulance.id,
        "vehicle_number": ambulance.vehicle_number,
        "approval_status": ambulance.approval_status,
        "is_approved": ambulance.is_approved,
        "rejection_reason": ambulance.rejection_reason
    })


def _relative_time(value):
    if not value:
        return None
    seconds = max(0, int((timezone.now() - value).total_seconds()))
    if seconds < 60:
        return f'{seconds} sec ago'
    minutes = seconds // 60
    if minutes < 60:
        return f'{minutes} min ago'
    hours = minutes // 60
    if hours < 24:
        return f'{hours} hr ago'
    return f'{hours // 24} days ago'


def _status_steps(status_value):
    status_value = status_value or 'searching'
    found_done = status_value in {'blood_bank_found', 'accepted', 'completed'}
    result_done = status_value in {'accepted', 'completed'}
    result_rejected = status_value in {'rejected', 'cancelled'}
    return [
        {'step': 'searching', 'label': 'Searching', 'status': 'completed'},
        {'step': 'found', 'label': 'Blood Bank Found', 'status': 'completed' if found_done else 'pending'},
        {'step': 'result', 'label': 'Accepted / Rejected', 'status': 'rejected' if result_rejected else 'completed' if result_done else 'pending'},
    ]


def _blood_request_detail(item, request):
    hospital = item.accepted_hospital
    return {
        'id': item.id,
        'request_code': item.request_code or f'#BR-{10000 + item.id}',
        'patient_name': item.patient_name or item.user_name or (item.user.get_full_name() if item.user else None),
        'patient_phone': item.patient_phone or item.user_phone or (item.user.phone if item.user else None),
        'required_blood_group': item.blood_group,
        'units': item.units or item.blood_units,
        'reason': item.reason,
        'created_at': item.created_at,
        'location': item.user_address,
        'prescription_image': _get_prescription_image_url(item, request),
        'accepted_hospital': hospital.name if hospital else None,
        'hospital_details': _get_hospital_info(hospital),
        'status': item.status,
        'status_steps': _status_steps(item.status),
    }


def _ambulance_request_detail(item):
    driver = item.driver
    ambulance = driver.ambulance if driver else None
    return {
        'id': item.id,
        'request_code': item.request_code or f'#AR-{20000 + item.id}',
        'patient_name': item.patient_name,
        'patient_phone': item.patient_phone,
        'emergency_type': item.emergency_type,
        'created_at': item.created_at,
        'status': item.status.replace('_', ' ').title(),
        'pickup': {
            'address': item.pickup_address,
            'is_live': item.pickup_latitude is not None and item.pickup_longitude is not None,
            'latitude': item.pickup_latitude,
            'longitude': item.pickup_longitude,
        },
        'destination': {
            'hospital_name': item.hospital_name,
            'address': item.destination_address,
        },
        'driver': {
            'name': driver.name if driver else None,
            'phone': driver.phone if driver else None,
            'vehicle_number': item.vehicle_number or ambulance.vehicle_number if ambulance else item.vehicle_number,
        },
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request, user_id):
    if not _admin_only(request):
        return Response({'error': 'Admin permission required.'}, status=status.HTTP_403_FORBIDDEN)
    user = get_object_or_404(User, id=user_id)
    blood_requests = BloodRequest.objects.filter(user_id=user.id).select_related('accepted_hospital').order_by('-created_at')
    ambulance_requests = AmbulanceRequest.objects.using('ambulance_db').filter(user_id=user.id).select_related('driver').order_by('-created_at')
    activity = list(UserActivityLog.objects.filter(user_id=user.id).order_by('-created_at')[:100])
    events = []
    for log in activity:
        events.append({
            'created_at': log.created_at,
            'time': timezone.localtime(log.created_at).strftime('%I:%M %p'),
            'icon': {'active': '🟢', 'login': '🔐', 'blood_request': '🩸', 'ambulance_request': '🚑', 'location_update': '📍'}.get(log.activity_type, '•'),
            'type': log.activity_type,
            'label': log.title,
            'request_id': int(log.reference_id) if log.reference_id and log.reference_id.isdigit() else None,
        })
    grouped = {}
    for event in events:
        event_date = event.pop('created_at').date()
        date_group = 'TODAY' if event_date == timezone.localdate() else 'YESTERDAY' if event_date == timezone.localdate() - timedelta(days=1) else event_date.strftime('%d %b').upper()
        grouped.setdefault(date_group, []).append(event)

    serialized_blood = [_blood_request_detail(item, request) for item in blood_requests]
    serialized_ambulance = [_ambulance_request_detail(item) for item in ambulance_requests]

    return Response({
        'user': {
            'id': user.id,
            'user_id_code': user.user_id_code or f'ALS-{10000 + user.id}',
            'full_name': user.get_full_name(),
            'phone': user.phone,
            'email': user.email,
            'age': user.age,
            'gender': user.gender,
            'blood_group': user.blood_group,
            'state': user.state,
            'district': user.district,
            'city': user.city,
            'address': user.address,
            'is_active': user.is_active,
            'is_available': user.is_available,
            'created_at': user.created_at,
            'last_active': user.last_active,
            'last_login': user.last_login,
            'total_active_days': user.total_active_days,
            'last_seen': _relative_time(user.last_active),
            'live_location': {
                'latitude': user.latitude,
                'longitude': user.longitude,
                'last_updated': _relative_time(user.last_active),
            },
            'blood_requests': serialized_blood,
            'ambulance_requests': serialized_ambulance,
        },
        'stats': {
            'blood_requests_count': len(serialized_blood),
            'ambulance_requests_count': len(serialized_ambulance),
        },
        'blood_requests': serialized_blood,
        'ambulance_requests': serialized_ambulance,
        'activity_timeline': [
            {'date_group': date_group, 'events': group_events}
            for date_group, group_events in grouped.items()
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blood_request_detail(request, request_id):
    if not _admin_only(request):
        return Response({'error': 'Admin permission required.'}, status=status.HTTP_403_FORBIDDEN)
    item = get_object_or_404(BloodRequest.objects.select_related('user'), id=request_id)
    return Response(_blood_request_detail(item, request))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ambulance_request_detail(request, request_id):
    if not _admin_only(request):
        return Response({'error': 'Admin permission required.'}, status=status.HTTP_403_FORBIDDEN)
    item = AmbulanceRequest.objects.using('ambulance_db').select_related('driver').filter(id=request_id).first()
    if item:
        return Response(_ambulance_request_detail(item))

    trip = get_object_or_404(
        Trip.objects.using('ambulance_db').select_related('driver__ambulance'),
        id=request_id,
    )
    driver = trip.driver
    ambulance = driver.ambulance if driver else None
    return Response({
        'id': trip.id,
        'request_code': f'#AR-{20000 + trip.id}',
        'patient_name': trip.patient_name,
        'patient_phone': trip.patient_phone,
        'emergency_type': 'Medical Emergency',
        'created_at': trip.created_at,
        'status': trip.status.replace('_', ' ').title(),
        'pickup': {
            'address': trip.pickup_address,
            'is_live': trip.pickup_latitude is not None and trip.pickup_longitude is not None,
            'latitude': trip.pickup_latitude,
            'longitude': trip.pickup_longitude,
        },
        'destination': {
            'hospital_name': ambulance.hospital.name if ambulance and ambulance.hospital else None,
            'address': trip.destination_address,
        },
        'driver': {
            'name': driver.name if driver else None,
            'phone': driver.phone if driver else None,
            'vehicle_number': ambulance.vehicle_number if ambulance else None,
        },
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_user_active(request, user_id):
    if not _admin_only(request):
        return Response({'error': 'Admin permission required.'}, status=status.HTTP_403_FORBIDDEN)
    user = get_object_or_404(User, id=user_id)
    is_active = request.data.get('is_active')
    if not isinstance(is_active, bool):
        return Response({'error': 'is_active must be boolean.'}, status=status.HTTP_400_BAD_REQUEST)
    if user.id == request.user.id and not is_active:
        return Response({'error': 'You cannot block your own admin account.'}, status=status.HTTP_400_BAD_REQUEST)
    user.is_active = is_active
    user.save(update_fields=['is_active', 'updated_at'])
    return Response({'id': user.id, 'is_active': user.is_active, 'message': 'User blocked.' if not is_active else 'User unblocked.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_admin_user(request):
    if not _admin_only(request):
        return Response({'error': 'Admin permission required.'}, status=status.HTTP_403_FORBIDDEN)
    phone = str(request.data.get('phone') or '').strip()
    if not phone:
        return Response({'error': 'phone is required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User(
            username=phone,
            phone=phone,
            email=request.data.get('email') or '',
            first_name=request.data.get('first_name') or '',
            last_name=request.data.get('last_name') or '',
            blood_group=request.data.get('blood_group') or None,
            age=request.data.get('age') or None,
            gender=request.data.get('gender') or None,
            state=request.data.get('state') or None,
            district=request.data.get('district') or None,
            city=request.data.get('city') or None,
            address=request.data.get('address') or None,
            is_donor=bool(request.data.get('is_donor', False)),
        )
        user.set_unusable_password()
        user.save()
    except (IntegrityError, ValueError) as error:
        return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'user': _serialize_admin_user(user, [], []), 'message': 'User created successfully.'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def live_users_map(request):
    if not _admin_only(request):
        return Response({'error': 'Admin permission required.'}, status=status.HTTP_403_FORBIDDEN)
    users = User.objects.filter(Q(is_available=True) | (Q(latitude__isnull=False) & Q(longitude__isnull=False)))
    state = request.query_params.get('state')
    district = request.query_params.get('district')
    search = request.query_params.get('search')
    if state:
        users = users.filter(state__iexact=state)
    if district:
        users = users.filter(district__iexact=district)
    if search:
        users = users.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(phone__icontains=search) | Q(user_id_code__icontains=search))
    return Response(list(users.values('id', 'user_id_code', 'first_name', 'last_name', 'phone', 'state', 'district', 'city', 'latitude', 'longitude', 'is_available', 'is_active')))