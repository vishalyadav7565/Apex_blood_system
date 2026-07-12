from urllib import request

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from geopy.distance import geodesic

from .models import BloodRequest
from apps.users.models import User
from apps.hospitals.models import Hospital
from apps.notifications.utils import send_push_notification
from .utils import notify_compatible_donors


def format_local_time(dt):
    if not dt:
        return None
    try:
        return timezone.localtime(dt).isoformat()
    except Exception:
        return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)


# ==========================================
# CREATE REQUEST
# ==========================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_request(request):

    prescription = request.FILES.get(
        'prescription'
    )

    req = BloodRequest.objects.create(

        user=request.user,

        user_name=(
            f"{request.user.first_name} "
            f"{request.user.last_name}"
        ).strip() or request.user.username,

        user_phone=request.user.phone,

        user_email=request.user.email,

        user_address=request.user.address,

        blood_group=request.data.get(
            'blood_group'
        ),

        latitude=request.data.get(
            'latitude'
        ),

        longitude=request.data.get(
            'longitude'
        ),

        prescription=prescription,

        status='pending'
    )

    req.expiry_time = (
        timezone.now() +
        timedelta(minutes=10)
    )

    req.save()

    channel_layer = get_channel_layer()

    # 1. Emit Initial REQUEST_CREATED Update to User
    async_to_sync(channel_layer.group_send)(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {
                "event": "REQUEST_CREATED",
                "request_id": req.id,
                "status": "pending",
                "message": "Blood request created successfully."
            }
        }
    )

    # 2. Transition to broadcasting status
    req.status = 'broadcasting'
    req.save()

    async_to_sync(channel_layer.group_send)(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {
                "event": "BROADCASTING",
                "request_id": req.id,
                "status": "broadcasting",
                "message": "Broadcasting request to nearby hospitals..."
            }
        }
    )

    hospitals = Hospital.objects.filter(
        is_verified=True
    )

    notified_hospitals = []

    # ======================================
    # HOSPITAL NOTIFICATION
    # ======================================

    for hospital in hospitals:

        if hospital.latitude and hospital.longitude:

            distance = geodesic(
                (
                    float(req.latitude),
                    float(req.longitude)
                ),
                (
                    float(hospital.latitude),
                    float(hospital.longitude)
                )
            ).km

            if distance <= 20:

                h_info = {
                    "id": hospital.id,
                    "name": hospital.name,
                    "distance": round(distance, 2),
                    "lat": hospital.latitude,
                    "lng": hospital.longitude,
                    "phone": hospital.phone,
                    "address": hospital.address
                }
                notified_hospitals.append(h_info)

                if getattr(hospital, "fcm_token", None):
                    send_push_notification(
                        token=hospital.fcm_token,
                        title="New Urgent Blood Request!",
                        body=f"Request for {req.blood_group} blood within {round(distance, 2)} km.",
                        data={
                            "event": "NEW_REQUEST",
                            "request_id": str(req.id)
                        }
                    )

                async_to_sync(
                    channel_layer.group_send
                )(
                    f"hospital_{hospital.id}",
                    {
                        "type": "send_update",
                        "data": {

                            "event":
                                "NEW_REQUEST",

                            "request_id":
                                req.id,

                            "patient_name":
                                req.user_name,

                            "user_name":
                                req.user_name,

                            "patient_phone":
                                req.user_phone,

                            "user_phone":
                                req.user_phone,

                            "patient_email":
                                req.user_email,

                            "user_email":
                                req.user_email,

                            "patient_address":
                                req.user_address,

                            "user_address":
                                req.user_address,

                            "blood_group":
                                req.blood_group,

                            "distance":
                                round(distance, 2),

                            "lat":
                                req.latitude,

                            "lng":
                                req.longitude,

                            "status": "pending",

                            "detailed_status": "searching_hospital",

                            "document": (
                                request.build_absolute_uri(req.prescription.url)
                                if req.prescription
                                else None
                            ),

                            "document_url": (
                                request.build_absolute_uri(req.prescription.url)
                                if req.prescription
                                else None
                            ),

                            "prescription": (
                                request.build_absolute_uri(req.prescription.url)
                                if req.prescription
                                else None
                            ),
                        }
                    }
                )

    # 3. Transition to searching_hospital status
    req.status = 'searching_hospital'
    req.save()

    # ======================================
    # ADMIN DASHBOARD UPDATE
    # ======================================

    async_to_sync(
        channel_layer.group_send
    )(
        "requests",
        {
            "type": "send_update",
            "data": {

                "event":
                    "NEW_REQUEST",

                "request_id":
                    req.id,

                "patient_name":
                    req.user_name,

                "blood_group":
                    req.blood_group,

                "status":
                    req.status,

                "lat":
                    req.latitude,

                "lng":
                    req.longitude,
            }
        }
    )

    # ======================================
    # USER APP UPDATE (Searching Hospital with nearby list)
    # ======================================

    async_to_sync(
        channel_layer.group_send
    )(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {

                "event":
                    "SEARCHING_HOSPITAL",

                "request_id":
                    req.id,

                "status":
                    "broadcasting",

                "detailed_status":
                    req.status,

                "message":
                    f"Searching nearby hospitals within 20 km. Found {len(notified_hospitals)} hospitals.",

                "nearby_hospitals":
                    notified_hospitals
            }
        }
    )

    return Response({

        "success": True,

        "id":
            req.id,

        "patient_name":
            req.user_name,

        "patient_phone":
            req.user_phone,

        "patient_email":
            req.user_email,

        "patient_address":
            req.user_address,

        "blood_group":
            req.blood_group,

        "status":
            req.status,

        "hospitals_notified":
            len(notified_hospitals),

        "nearby_hospitals":
            notified_hospitals
    })
# ==========================================
# GET ALL REQUESTS
# ==========================================
@api_view(['GET'])
def get_requests(request):

    requests = BloodRequest.objects.all().order_by('-id')

    data = []

    for req in requests:

        data.append({

            "id":
                req.id,

            # Patient Details
            "patient_name":
                req.user_name,

            "user_name":
                req.user_name,

            "patient_phone":
                req.user_phone,

            "user_phone":
                req.user_phone,

            "patient_email":
                req.user_email,

            "user_email":
                req.user_email,

            "patient_address":
                req.user_address,

            "user_address":
                req.user_address,

            # Request Details
            "blood_group":
                req.blood_group,

            "status":
                "pending" if req.status in ["searching_hospital", "searching_next_hospital"] else req.status,

            "detailed_status":
                req.status,

            "latitude":
                req.latitude,

            "longitude":
                req.longitude,

            "document":
                request.build_absolute_uri(req.prescription.url)
                if req.prescription
                else None,

            "document_url":
                request.build_absolute_uri(req.prescription.url)
                if req.prescription
                else None,

            "prescription":
                request.build_absolute_uri(req.prescription.url)
                if req.prescription
                else None,

            "created_at":
                format_local_time(req.created_at),

            # Accepted Hospital Details
            "accepted_hospital":
                req.accepted_hospital.name
                if req.accepted_hospital
                else None,

            "hospital_phone":
                req.accepted_hospital.phone
                if req.accepted_hospital
                else None,

            "hospital_email":
                req.accepted_hospital.email
                if req.accepted_hospital
                else None,

            "hospital_address":
                req.accepted_hospital.address
                if req.accepted_hospital
                else None,

            "hospital_latitude":
                req.accepted_hospital.latitude
                if req.accepted_hospital
                else None,

            "hospital_longitude":
                req.accepted_hospital.longitude
                if req.accepted_hospital
                else None,

            "hospital_pincode":
                req.accepted_hospital.pincode
                if req.accepted_hospital
                else None,
        })

    return Response(data)
# ==========================================
# GET SINGLE REQUEST
# ==========================================
@api_view(['GET'])
def get_request(request, id):

    req = get_object_or_404(
        BloodRequest,
        id=id
    )

    h = req.accepted_hospital

    return Response({

        "id": req.id,

        "patient_name":
            req.user_name,

        "user_name":
            req.user_name,

        "patient_phone":
            req.user_phone,

        "user_phone":
            req.user_phone,

        "patient_email":
            req.user_email,

        "user_email":
            req.user_email,

        "patient_address":
            req.user_address,

        "user_address":
            req.user_address,

        "blood_group":
            req.blood_group,

        "status":
            "pending" if req.status in ["searching_hospital", "searching_next_hospital"] else req.status,

        "detailed_status":
            req.status,

        "latitude":
            req.latitude,

        "longitude":
            req.longitude,

        "document":
            request.build_absolute_uri(req.prescription.url)
            if req.prescription
            else None,

        "document_url":
            request.build_absolute_uri(req.prescription.url)
            if req.prescription
            else None,

        "prescription":
            request.build_absolute_uri(req.prescription.url)
            if req.prescription
            else None,

        "created_at":
            format_local_time(req.created_at),

        "hospital_name": h.name if h else None,
        "hospital_phone": h.phone if h else None,
        "hospital_email": h.email if h else None,
        "hospital_address": h.address if h else None,
        "hospital_latitude": h.latitude if h else None,
        "hospital_longitude": h.longitude if h else None,
        "hospital_lat": h.latitude if h else None,
        "hospital_lng": h.longitude if h else None,
        "hospital_pincode": h.pincode if h else None,
        "hospital": {
            "id": h.id, "name": h.name, "phone": h.phone, "email": h.email,
            "address": h.address, "latitude": h.latitude, "longitude": h.longitude,
            "lat": h.latitude, "lng": h.longitude, "pincode": h.pincode
        } if h else None,
        "accepted_hospital": {
            "id": h.id, "name": h.name, "phone": h.phone, "email": h.email,
            "address": h.address, "latitude": h.latitude, "longitude": h.longitude,
            "lat": h.latitude, "lng": h.longitude, "pincode": h.pincode
        } if h else None,
    })

# ==========================================
# HOSPITAL ACCEPT
# ==========================================
@api_view(['POST'])
def hospital_accept(request, id):

    req = get_object_or_404(
        BloodRequest,
        id=id
    )

    if req.status not in ['pending', 'broadcasting', 'searching_hospital']:

        return Response(
            {
                "error":
                    f"Request already {req.status}"
            },
            status=400
        )

    hospital_id = (
        request.data.get("hospital_id") or
        request.data.get("hospital") or
        request.data.get("id") or
        request.GET.get("hospital_id")
    )

    req.status = "accepted"

    req.assigned_to = "hospital"

    # Save accepted hospital
    if hospital_id:

        try:

            hospital = Hospital.objects.get(
                id=hospital_id
            )

            req.accepted_hospital = hospital

        except Hospital.DoesNotExist:

            return Response(
                {
                    "error":
                        "Hospital not found"
                },
                
                status=404
            )

    req.save()
    

    h = req.accepted_hospital
    h_data = {
        "id": h.id if h else None,
        "name": h.name if h else None,
        "phone": h.phone if h else None,
        "email": h.email if h else None,
        "address": h.address if h else None,
        "latitude": h.latitude if h else None,
        "longitude": h.longitude if h else None,
        "lat": h.latitude if h else None,
        "lng": h.longitude if h else None,
        "pincode": h.pincode if h else None,
    } if h else None

    # ======================================
    # PUSH NOTIFICATION
    # ======================================
    if getattr(req.user, "fcm_token", None):
        send_push_notification(
            token=req.user.fcm_token,
            title="Blood Request Accepted!",
            body=f"Your request for {req.blood_group} blood has been accepted by {h.name if h else 'a hospital'}.",
            data={
                "event": "REQUEST_ACCEPTED",
                "request_id": req.id,
                "status": "accepted",
                "hospital": h.name if h else None,
                "hospital_name": h.name if h else None,
                "hospital_phone": h.phone if h else None,
                "hospital_email": h.email if h else None,
                "hospital_address": h.address if h else None,
                "hospital_latitude": h.latitude if h else None,
                "hospital_longitude": h.longitude if h else None,
                "hospital_lat": h.latitude if h else None,
                "hospital_lng": h.longitude if h else None,
                "hospital_pincode": h.pincode if h else None,
                "hospital_details": h_data,
                "accepted_hospital": h_data,
                "message": f"Your request has been accepted by {h.name if h else 'a hospital'}."
            }
        )

    # ======================================
    # WEBSOCKET EVENT
    # ======================================
    channel_layer = get_channel_layer()

    # Admin Dashboard
    async_to_sync(
        channel_layer.group_send
    )(
        "requests",
        {
            "type": "send_update",
            "data": {

                "event":
                    "REQUEST_ACCEPTED",

                "request_id":
                    req.id,

                "status":
                    "accepted",

                "hospital":
                    h.name
                    if h
                    else None,
            }
        }
    )

    # User App
    async_to_sync(
        channel_layer.group_send
    )(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {
                "event": "REQUEST_ACCEPTED",
                "request_id": req.id,
                "status": "accepted",
                "detailed_status": "accepted",
                "hospital": h.name if h else None,
                "hospital_name": h.name if h else None,
                "hospital_phone": h.phone if h else None,
                "hospital_email": h.email if h else None,
                "hospital_address": h.address if h else None,
                "hospital_latitude": h.latitude if h else None,
                "hospital_longitude": h.longitude if h else None,
                "hospital_pincode": h.pincode if h else None,
                "hospital_details": h_data,
                "accepted_hospital": h_data,
                "message": f"Your request has been accepted by {h.name if h else 'a hospital'}."
            }
        }
    )

    return Response({

        "success": True,

        "message":
            "Request accepted successfully",

        "request_id":
            req.id,

        "status":
            req.status,

        "hospital":
            h.name
            if h
            else None,

        "hospital_name": h.name if h else None,
        "hospital_phone": h.phone if h else None,
        "hospital_email": h.email if h else None,
        "hospital_address": h.address if h else None,
        "hospital_latitude": h.latitude if h else None,
        "hospital_longitude": h.longitude if h else None,
        "hospital_lat": h.latitude if h else None,
        "hospital_lng": h.longitude if h else None,
        "hospital_pincode": h.pincode if h else None,
        "hospital_details": h_data,
        "accepted_hospital": h_data,
    })
#==========================================
# REJECT REQUEST
#==========================================
@api_view(['POST'])
def reject_request(request, id):

    req = get_object_or_404(
        BloodRequest,
        id=id
    )

    if req.status not in ['pending', 'broadcasting', 'searching_hospital', 'searching_next_hospital']:

        return Response(
            {
                "error":
                    f"Request already {req.status}"
            },
            status=400
        )

    hospital_id = request.data.get(
        "hospital_id"
    )

    if not hospital_id:

        return Response(
            {
                "error":
                    "hospital_id required"
            },
            status=400
        )

    try:

        hospital = Hospital.objects.get(
            id=hospital_id
        )

    except Hospital.DoesNotExist:

        return Response(
            {
                "error":
                    "Hospital not found"
            },
            status=404
        )

    # 1. Save hospital and transition status to rejected
    req.accepted_hospital = hospital

    req.status = "rejected"

    req.assigned_to = "hospital"

    req.save()

    # ======================================
    # PUSH NOTIFICATION
    # ======================================
    if getattr(req.user, "fcm_token", None):
        send_push_notification(
            token=req.user.fcm_token,
            title="Blood Request Update",
            body=f"{hospital.name} could not fulfill your request. We are searching for alternatives.",
            data={
                "event": "REQUEST_REJECTED",
                "request_id": str(req.id)
            }
        )

    # ======================================
    # WEBSOCKET UPDATE (Rejection event)
    # ======================================

    channel_layer = get_channel_layer()

    # Admin Dashboard
    async_to_sync(
        channel_layer.group_send
    )(
        "requests",
        {
            "type": "send_update",
            "data": {
                "event":
                    "REQUEST_REJECTED",

                "request_id":
                    req.id,

                "status":
                    "rejected",

                "hospital":
                    hospital.name,

                "blood_group":
                    req.blood_group,
            }
        }
    )

    # User App
    async_to_sync(
        channel_layer.group_send
    )(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {
                "event":
                    "REQUEST_REJECTED",

                "request_id":
                    req.id,

                "status":
                    "rejected",

                "hospital":
                    hospital.name,

                "message":
                    f"{hospital.name} rejected your request"
            }
        }
    )

    # 2. Transition to searching_next_hospital
    req.status = "searching_next_hospital"
    req.save()

    all_hospitals = Hospital.objects.filter(is_verified=True).exclude(id=hospital.id)
    next_hospitals = []
    for h in all_hospitals:
        if h.latitude and h.longitude:
            distance = geodesic(
                (float(req.latitude), float(req.longitude)),
                (float(h.latitude), float(h.longitude))
            ).km
            if distance <= 20:
                next_hospitals.append({
                    "id": h.id,
                    "name": h.name,
                    "distance": round(distance, 2),
                    "lat": h.latitude,
                    "lng": h.longitude,
                    "phone": h.phone,
                    "address": h.address
                })

                if getattr(h, "fcm_token", None):
                    send_push_notification(
                        token=h.fcm_token,
                        title="New Urgent Blood Request!",
                        body=f"Request for {req.blood_group} blood within {round(distance, 2)} km.",
                        data={
                            "event": "NEW_REQUEST",
                            "request_id": str(req.id)
                        }
                    )

                async_to_sync(channel_layer.group_send)(
                    f"hospital_{h.id}",
                    {
                        "type": "send_update",
                        "data": {
                            "event": "NEW_REQUEST",
                            "request_id": req.id,
                            "patient_name": req.user_name,
                            "user_name": req.user_name,
                            "patient_phone": req.user_phone,
                            "user_phone": req.user_phone,
                            "patient_email": req.user_email,
                            "user_email": req.user_email,
                            "patient_address": req.user_address,
                            "user_address": req.user_address,
                            "blood_group": req.blood_group,
                            "distance": round(distance, 2),
                            "lat": req.latitude,
                            "lng": req.longitude,
                            "status": "pending",
                            "detailed_status": "searching_next_hospital",
                            "document": (
                                request.build_absolute_uri(req.prescription.url)
                                if req.prescription
                                else None
                            ),
                            "document_url": (
                                request.build_absolute_uri(req.prescription.url)
                                if req.prescription
                                else None
                            ),
                            "prescription": (
                                request.build_absolute_uri(req.prescription.url)
                                if req.prescription
                                else None
                            ),
                        }
                    }
                )

    async_to_sync(
        channel_layer.group_send
    )(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {
                "event":
                    "SEARCHING_NEXT_HOSPITAL",

                "request_id":
                    req.id,

                "status":
                    "broadcasting",

                "detailed_status":
                    "searching_next_hospital",

                "message":
                    f"Searching next hospital... Found {len(next_hospitals)} alternatives.",

                "nearby_hospitals":
                    next_hospitals
            }
        }
    )

    # 3. Transition to searching_donor status (Fallback)
    from .utils import COMPATIBLE_DONORS
    compatible_groups = COMPATIBLE_DONORS.get(req.blood_group, [req.blood_group])
    donors = User.objects.filter(
        is_donor=True,
        is_available=True,
        blood_group__in=compatible_groups
    )
    nearby_donors = []
    for donor in donors:
        if donor.latitude and donor.longitude:
            dist = geodesic(
                (float(req.latitude), float(req.longitude)),
                (float(donor.latitude), float(donor.longitude))
            ).km
            if dist <= 10:
                nearby_donors.append({
                    "id": donor.id,
                    "name": (f"{donor.first_name} {donor.last_name}").strip() or donor.username,
                    "distance": round(dist, 2),
                    "lat": donor.latitude,
                    "lng": donor.longitude,
                    "phone": donor.phone,
                    "blood_group": donor.blood_group
                })

    req.status = "searching_donor"
    req.save()

    # Notify donors in the background
    notify_compatible_donors(req)

    # Webhook Admin Update
    async_to_sync(
        channel_layer.group_send
    )(
        "requests",
        {
            "type": "send_update",
            "data": {
                "event": "SEARCHING_DONOR",
                "request_id": req.id,
                "status": req.status,
                "blood_group": req.blood_group,
            }
        }
    )

    # Webhook User Update with nearby donors
    async_to_sync(
        channel_layer.group_send
    )(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {
                "event": "SEARCHING_DONOR",
                "request_id": req.id,
                "status": "broadcasting",
                "detailed_status": req.status,
                "message": "Hospitals busy. Searching nearby blood donors...",
                "nearby_donors": nearby_donors
            }
        }
    )

    return Response({
        "success": True,
        "request_id": req.id,
        "status": req.status,
        "hospital": hospital.name,
        "message": "Request rejected and transitioned to searching donors fallback."
    })
# ==========================================
# FALLBACK DONORS
# ==========================================
@api_view(['GET'])
def fallback_donors(request):

    now = timezone.now()

    expired = BloodRequest.objects.filter(
        status__in=['pending', 'broadcasting', 'searching_hospital', 'searching_next_hospital'],
        expiry_time__lt=now
    )

    channel_layer = get_channel_layer()

    updated_count = 0

    from .utils import COMPATIBLE_DONORS

    for req in expired:

        # Scan for compatible donors within 10 km
        compatible_groups = COMPATIBLE_DONORS.get(req.blood_group, [req.blood_group])
        donors = User.objects.filter(
            is_donor=True,
            is_available=True,
            blood_group__in=compatible_groups
        )
        nearby_donors = []
        for donor in donors:
            if donor.latitude and donor.longitude:
                dist = geodesic(
                    (float(req.latitude), float(req.longitude)),
                    (float(donor.latitude), float(donor.longitude))
                ).km
                if dist <= 10:
                    nearby_donors.append({
                        "id": donor.id,
                        "name": (f"{donor.first_name} {donor.last_name}").strip() or donor.username,
                        "distance": round(dist, 2),
                        "lat": donor.latitude,
                        "lng": donor.longitude,
                        "phone": donor.phone,
                        "blood_group": donor.blood_group
                    })

        req.status = 'searching_donor'
        req.save()
        notify_compatible_donors(req)

        updated_count += 1

        # ======================================
        # ADMIN DASHBOARD UPDATE
        # ======================================
        async_to_sync(
            channel_layer.group_send
        )(
            "requests",
            {
                "type": "send_update",
                "data": {
                    "event": "SEARCHING_DONOR",
                    "request_id": req.id,
                    "status": req.status,
                    "blood_group": req.blood_group,
                }
            }
        )

        # ======================================
        # USER APP UPDATE
        # ======================================
        async_to_sync(
            channel_layer.group_send
        )(
            f"user_{req.user.id}",
            {
                "type": "send_update",
                "data": {
                    "event": "SEARCHING_DONOR",
                    "request_id": req.id,
                    "status": "broadcasting",
                    "detailed_status": req.status,
                    "message": "Hospitals busy. Searching nearby blood donors...",
                    "nearby_donors": nearby_donors
                }
            }
        )

    return Response({
        "updated": updated_count,
        "message": "fallback triggered"
    })


# ==========================================
# MATCH DONORS
# ==========================================
@api_view(['GET'])
def match_donors(request, id):

    req = get_object_or_404(
        BloodRequest,
        id=id
    )

    donors = User.objects.filter(
        is_available=True,
        is_donor=True
    )

    result = []

    for d in donors:

        if d.latitude and d.longitude:

            dist = geodesic(
                (
                    float(req.latitude),
                    float(req.longitude)
                ),
                (
                    float(d.latitude),
                    float(d.longitude)
                )
            ).km

            if dist <= 10:

                result.append({

                    "id":
                        d.id,

                    "name":
                        getattr(d, "first_name", ""),

                    "phone":
                        getattr(d, "phone", ""),

                    "blood_group":
                        getattr(d, "blood_group", ""),

                    "distance":
                        round(dist, 2)
                })

    # ======================================
    # USER REALTIME UPDATE
    # ======================================
    channel_layer = get_channel_layer()

    async_to_sync(
        channel_layer.group_send
    )(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {

                "event":
                    "DONORS_FOUND",

                "request_id":
                    req.id,

                "count":
                    len(result),

                "donors":
                    result
            }
        }
    )

    return Response({
        "count": len(result),
        "data": result
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_request(request, id):
    req = get_object_or_404(BloodRequest, id=id)

    # Allow completing if the request is accepted or searching_donor
    if req.status not in ['accepted', 'searching_donor']:
        return Response(
            {
                "error": f"Cannot complete request with status {req.status}"
            },
            status=400
        )

    req.status = "completed"
    req.save()

    channel_layer = get_channel_layer()

    # Webhook Admin Update
    async_to_sync(channel_layer.group_send)(
        "requests",
        {
            "type": "send_update",
            "data": {
                "event": "REQUEST_COMPLETED",
                "request_id": req.id,
                "status": req.status,
            }
        }
    )

    # Webhook User Update
    async_to_sync(channel_layer.group_send)(
        f"user_{req.user.id}",
        {
            "type": "send_update",
            "data": {
                "event": "REQUEST_COMPLETED",
                "request_id": req.id,
                "status": req.status,
                "message": "Blood request completed successfully."
            }
        }
    )

    return Response({
        "success": True,
        "request_id": req.id,
        "status": req.status,
        "message": "Request completed successfully."
    })


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import BloodRequest


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_requests(request):

    try:

        print("========== MY REQUEST API HIT ==========")
        print("USER:", request.user)
        print("USER ID:", request.user.id)
        print("AUTH:", request.auth)

        requests = BloodRequest.objects.filter(
            user=request.user
        ).order_by("-created_at")

        print("TOTAL REQUESTS:", requests.count())

        data = []

        for req in requests:

            try:

                prescription_url = None

                if req.prescription:
                    prescription_url = (
                        request.build_absolute_uri(
                            req.prescription.url
                        )
                    )

                h = req.accepted_hospital
                data.append({
                    "id": req.id,
                    "blood_group": req.blood_group,
                    "status": req.status,
                    "hospital_name": h.name if h else None,
                    "hospital_phone": h.phone if h else None,
                    "hospital_email": h.email if h else None,
                    "hospital_address": h.address if h else None,
                    "hospital_latitude": h.latitude if h else None,
                    "hospital_longitude": h.longitude if h else None,
                    "hospital_pincode": h.pincode if h else None,
                    "user_name": req.user_name,
                    "user_phone": req.user_phone,
                    "created_at": format_local_time(req.created_at),
                    "prescription": prescription_url
                })

            except Exception as row_error:

                print(
                    f"ROW ERROR REQUEST {req.id}:",
                    str(row_error)
                )

        return Response(data)

    except Exception as e:

        print("========== ERROR ==========")
        print(str(e))

        return Response(
            {
                "success": False,
                "error": str(e)
            },
            status=400
        )
    
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_request(request):

    req = BloodRequest.objects.filter(
        user=request.user
    ).order_by("-created_at").first()

    if not req:
        return Response({
            "message": "No request found"
        })

    h = req.accepted_hospital
    h_data = {
        "id": h.id if h else None,
        "name": h.name if h else None,
        "phone": h.phone if h else None,
        "email": h.email if h else None,
        "address": h.address if h else None,
        "latitude": h.latitude if h else None,
        "longitude": h.longitude if h else None,
        "lat": h.latitude if h else None,
        "lng": h.longitude if h else None,
        "pincode": h.pincode if h else None,
    } if h else None

    return Response({
        "id": req.id,
        "blood_group": req.blood_group,
        "status": req.status,
        "hospital_name": h.name if h else None,
        "hospital_phone": h.phone if h else None,
        "hospital_email": h.email if h else None,
        "hospital_address": h.address if h else None,
        "hospital_latitude": h.latitude if h else None,
        "hospital_longitude": h.longitude if h else None,
        "hospital_lat": h.latitude if h else None,
        "hospital_lng": h.longitude if h else None,
        "hospital_pincode": h.pincode if h else None,
        "hospital_details": h_data,
        "accepted_hospital": h_data,
        "created_at": format_local_time(req.created_at),
        "prescription": (
            request.build_absolute_uri(
                req.prescription.url
            )
            if req.prescription
            else None
        )
    })