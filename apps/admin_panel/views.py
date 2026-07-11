from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
import pandas as pd
import numpy as np
from apps.blood_requests.models import BloodRequest
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
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

from apps.users.models import User, HelpSupport
from apps.blood_requests.models import BloodRequest
from apps.hospitals.models import Hospital
from apps.notifications.utils import send_push_notification


# =========================================
# 🔐 ADMIN LOGIN
# =========================================
@api_view(['POST'])
@permission_classes([AllowAny])

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