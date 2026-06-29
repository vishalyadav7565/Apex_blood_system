from httpcore import request
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from .models import Hospital
from math import radians, cos, sin, asin, sqrt
from .models import BloodInventory
from .serializers import BloodInventorySerializer
from .serializers import HospitalProfileSerializer
from rest_framework.permissions import IsAuthenticated
from apps.blood_requests.models import BloodRequest

from .serializers import (
    HospitalSerializer,
    HospitalRegisterSerializer,
    HospitalLoginSerializer,
   

)


# 📏 Distance function (optimized + safe)
def distance_km(lat1, lon1, lat2, lon2):
    try:
        dlon = radians(lon2 - lon1)
        dlat = radians(lat2 - lat1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return 6371 * c
    except:
        return None


# 🚀 GET NEARBY HOSPITALS (10KM)
@api_view(['GET'])
def nearby_hospitals(request):
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')

    # ❌ Missing params
    if not lat or not lng:
        return Response(
            {"error": "lat and lng are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user_lat = float(lat)
        user_lng = float(lng)
    except ValueError:
        return Response(
            {"error": "Invalid lat/lng format"},
            status=status.HTTP_400_BAD_REQUEST
        )

    hospitals = Hospital.objects.filter(is_verified=True)

    result = []

    for hospital in hospitals:
        dist = distance_km(
            user_lat,
            user_lng,
            hospital.latitude,
            hospital.longitude
        )

        if dist is not None and dist <= 50:  # Expanded search radius to 50km
            result.append({
                "id": hospital.id,
                "name": hospital.name,
                "email": hospital.email,
                "phone": hospital.phone,
                "address": hospital.address,
                "pincode": hospital.pincode,
                "latitude": hospital.latitude,
                "longitude": hospital.longitude,
                "lat": hospital.latitude,
                "lng": hospital.longitude,
                "distance": round(dist, 2),
                "type": "hospital"  # 🔥 useful for frontend
            })

    # 🔥 Sort nearest first
    result.sort(key=lambda x: x['distance'])

    return Response(result, status=status.HTTP_200_OK)


# 🚀 VERIFY HOSPITAL
@api_view(['POST'])
def verify_hospital(request, id):
    try:
        hospital = Hospital.objects.get(id=id)
        hospital.is_verified = True
        hospital.save()

        return Response(
            {"message": "Hospital verified successfully"},
            status=status.HTTP_200_OK
        )

    except Hospital.DoesNotExist:
        return Response(
            {"error": "Hospital not found"},
            status=status.HTTP_404_NOT_FOUND
        )

# ==========================================
# 🚀 REGISTER HOSPITAL
# ==========================================
@api_view(['POST'])
def register_hospital(request):

    serializer = HospitalRegisterSerializer(
        data=request.data
    )

    if serializer.is_valid():

        hospital = serializer.save()

        return Response(
            {
                "message":
                    "Hospital registered successfully",

                "hospital": {
                    "id": hospital.id,
                    "name": hospital.name,
                    "email": hospital.email,
                    "phone": hospital.phone,
                    "latitude": hospital.latitude,
                    "longitude": hospital.longitude,
                }
            },

            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


# ==========================================
# 🔐 LOGIN HOSPITAL
# ==========================================
@api_view(['POST'])
def login_hospital(request):
     
    print("===== LOGIN HIT =====")
    print(request.data)


    serializer = HospitalLoginSerializer(
        data=request.data
    )

    if serializer.is_valid():

        email = serializer.validated_data[
            'email'
        ]

        password = serializer.validated_data[
            'password'
        ]

        try:

            hospital = Hospital.objects.get(
                email=email
            )

            # ✅ PASSWORD CHECK
            if hospital.check_password(
                password
            ):

                return Response(
                    {
                        "message":
                            "Login successful",

                        "hospital": {

                            "id": hospital.id,

                            "name":
                                hospital.name,

                            "email":
                                hospital.email,

                            "phone":
                                hospital.phone,
                            "latitude":
                                hospital.latitude,
                            "longitude":    
                                hospital.longitude,

                            "is_verified":
                                hospital.is_verified,
                        }
                    },

                    status=status.HTTP_200_OK
                )

            else:

                return Response(
                    {
                        "error":
                            "Invalid password"
                    },

                    status=status.HTTP_401_UNAUTHORIZED
                )

        except Hospital.DoesNotExist:

            return Response(
                {
                    "error":
                        "Hospital not found"
                },

                status=status.HTTP_404_NOT_FOUND
            )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

# ==============================
# GET INVENTORY
# ==============================
@api_view(['GET'])
def get_inventory(request):

    hospital_id = request.GET.get("hospital_id")

    if not hospital_id:
        return Response(
            {"error": "hospital_id required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        hospital = Hospital.objects.get(id=hospital_id)

        inventory = BloodInventory.objects.filter(
            hospital=hospital
        ).order_by("blood_group")

        serializer = BloodInventorySerializer(
            inventory,
            many=True
        )

        return Response(
            {
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "inventory": serializer.data
            },
            status=status.HTTP_200_OK
        )

    except Hospital.DoesNotExist:
        return Response(
            {"error": "Hospital not found"},
            status=status.HTTP_404_NOT_FOUND
        )


# ==============================
# ADD STOCK
# ==============================
@api_view(['POST'])
def add_stock(request):

    hospital_id = request.data.get("hospital_id")
    blood_group = request.data.get("blood_group")
    units = request.data.get("units")

    if not hospital_id:
        return Response(
            {"error": "hospital_id required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not blood_group:
        return Response(
            {"error": "blood_group required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not units:
        return Response(
            {"error": "units required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:

        hospital = Hospital.objects.get(
            id=hospital_id
        )

        inventory, created = BloodInventory.objects.get_or_create(
            hospital=hospital,
            blood_group=blood_group,
            defaults={
                "units": 0
            }
        )

        inventory.units += int(units)
        inventory.save()

        return Response(
            {
                "message": "Stock added successfully",
                "hospital_id": hospital.id,
                "hospital_name": hospital.name,
                "blood_group": inventory.blood_group,
                "units": inventory.units
            },
            status=status.HTTP_200_OK
        )

    except Hospital.DoesNotExist:

        return Response(
            {"error": "Hospital not found"},
            status=status.HTTP_404_NOT_FOUND
        )


# ==============================
# REMOVE STOCK
# ==============================
@api_view(['POST'])
def remove_stock(request):

    hospital_id = request.data.get("hospital_id")
    blood_group = request.data.get("blood_group")
    units = request.data.get("units")

    if not hospital_id:
        return Response(
            {"error": "hospital_id required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not blood_group:
        return Response(
            {"error": "blood_group required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not units:
        return Response(
            {"error": "units required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:

        inventory = BloodInventory.objects.get(
            hospital_id=hospital_id,
            blood_group=blood_group
        )

        remove_units = int(units)

        if remove_units > inventory.units:
            return Response(
                {
                    "error":
                    f"Only {inventory.units} units available"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        inventory.units -= remove_units
        inventory.save()

        return Response(
            {
                "message": "Stock removed successfully",
                "blood_group": inventory.blood_group,
                "units": inventory.units
            },
            status=status.HTTP_200_OK
        )

    except BloodInventory.DoesNotExist:

        return Response(
            {"error": "Inventory not found"},
            status=status.HTTP_404_NOT_FOUND
        )
  # ==========================================
# GET HOSPITAL PROFILE
# ==========================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_profile(request, id):

    hospital = get_object_or_404(
        Hospital,
        id=id
    )

    serializer = HospitalProfileSerializer(
        hospital
    )

    return Response(
        serializer.data
    )


# ==========================================
# UPDATE HOSPITAL PROFILE
# ==========================================
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_hospital_profile(
    request,
    id
):

    hospital = get_object_or_404(
        Hospital,
        id=id
    )

    serializer = HospitalProfileSerializer(
        hospital,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():

        serializer.save()

        return Response({

            "success": True,

            "message":
                "Profile updated successfully",

            "hospital":
                serializer.data
        })

    return Response(
        serializer.errors,
        status=400
    )
@api_view(['GET'])
def all_hospitals(request):

    hospitals = Hospital.objects.all().order_by("name")

    data = []

    for hospital in hospitals:

        data.append({
            "id": hospital.id,
            "name": hospital.name,
            "email": hospital.email,
            "phone": hospital.phone,
            "address": hospital.address,
            "pincode": hospital.pincode,
            "latitude": hospital.latitude,
            "longitude": hospital.longitude,
            "lat": hospital.latitude,
            "lng": hospital.longitude,
            "is_verified": hospital.is_verified,
        })

    return Response(data)

@api_view(['GET'])
def hospital_stats(request):

    hospital_id = request.GET.get("hospital_id")

    if not hospital_id:
        return Response(
            {"error": "hospital_id required"},
            status=400
        )

    try:

        hospital = Hospital.objects.get(
            id=hospital_id
        )

        requests = BloodRequest.objects.filter(
            accepted_hospital=hospital
        ).order_by("-created_at")

        total_requests = requests.count()

        accepted_requests = requests.filter(
            status="accepted"
        ).count()

        rejected_requests = requests.filter(
            status="rejected"
        ).count()

        pending_requests = requests.filter(
            status="pending"
        ).count()

        inventory = BloodInventory.objects.filter(
            hospital=hospital
        )

        total_units = sum(
            item.units
            for item in inventory
        )

        recent_requests = []

        for req in requests[:20]:

            recent_requests.append({
                "id": req.id,
                "user_name": req.user_name,
                "user_phone": req.user_phone,
                "blood_group": req.blood_group,
                "status": req.status,
                "created_at": req.created_at,
                "prescription": (
                    request.build_absolute_uri(
                        req.prescription.url
                    )
                    if req.prescription
                    else None
                )
            })

        return Response({

            "hospital_id": hospital.id,
            "hospital_name": hospital.name,

            "total_requests": total_requests,
            "accepted_requests": accepted_requests,
            "rejected_requests": rejected_requests,
            "pending_requests": pending_requests,

            "total_blood_units": total_units,

            "success_rate":
                round(
                    (accepted_requests / total_requests) * 100,
                    2
                ) if total_requests > 0 else 0,

            "recent_requests":
                recent_requests
        })

    except Hospital.DoesNotExist:

        return Response(
            {"error": "Hospital not found"},
            status=404
        )
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_hospital_fcm_token(request):
    print("REQUEST DATA:", request.data)
    hospital_id = request.data.get("hospital_id")
    token = request.data.get("fcm_token")

    if not hospital_id or not token:
        return Response(
            {"error": "hospital_id and fcm_token required"},
            status=400
        )

    try:
        hospital = Hospital.objects.get(id=hospital_id)

    except Hospital.DoesNotExist:
        return Response(
            {"error": "Hospital not found"},
            status=404
        )

    hospital.fcm_token = token
    hospital.save()

    return Response({
        "success": True
    })