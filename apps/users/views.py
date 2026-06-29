import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.permissions import AllowAny

from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from django_ratelimit.decorators import ratelimit
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from firebase_admin import auth as firebase_auth
from .models import OTP, HelpSupport

User = get_user_model()


# =========================================
# SEND OTP
# =========================================
@ratelimit(
    key='ip',
    rate='5/m',
    block=True
)
@api_view(['POST'])
def send_otp(request):

    phone = request.data.get('phone')

    if not phone:

        return Response(
            {"error": "Phone required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # remove old otp
    OTP.objects.filter(
        phone=phone
    ).delete()

    # generate new otp
    otp = str(
        random.randint(100000, 999999)
    )

    OTP.objects.create(
        phone=phone,
        otp=otp
    )

    print(f"📲 OTP for {phone} → {otp}")

    return Response({

        "success": True,

        "message": "OTP sent",

        # DEV ONLY
        "otp": otp
    })


# =========================================
# VERIFY OTP + LOGIN/REGISTER
# =========================================
@ratelimit(
    key='ip',
    rate='10/m',
    block=True
)
@api_view(['POST'])
def verify_otp(request):

    phone = request.data.get('phone')
    otp = request.data.get('otp')

    # =================================
    # VALIDATION
    # =================================
    if not phone or not otp:

        return Response({
            "error": "Phone and OTP required"
        }, status=400)

    try:

        # =================================
        # GET LATEST OTP
        # =================================
        record = OTP.objects.filter(
            phone=phone
        ).latest('created_at')

        print("DB OTP:", record.otp)
        print("USER OTP:", otp)

        # =================================
        # OTP EXPIRY CHECK
        # =================================
        expiry_time = (
            record.created_at +
            timedelta(minutes=5)
        )

        if timezone.now() > expiry_time:

            record.delete()

            return Response({
                "error": "OTP expired"
            }, status=400)

        # =================================
        # VERIFY OTP
        # =================================
        if str(record.otp) != str(otp):

            return Response({
                "error": "Invalid OTP"
            }, status=400)

        # =================================
        # MARK VERIFIED
        # =================================
        record.is_verified = True
        record.save()

        # =================================
        # DELETE OLD OTPs
        # =================================
        OTP.objects.filter(
            phone=phone
        ).delete()

        # =================================
        # CHECK USER EXISTS
        # =================================
        try:

            user = User.objects.get(
                phone=phone
            )

            created = False

        except User.DoesNotExist:

            # =================================
            # CREATE NEW USER
            # =================================
            user = User.objects.create(
                phone=phone,
                username=phone
            )

            created = True

        # =================================
        # JWT TOKEN
        # =================================
        refresh = RefreshToken.for_user(user)

        # =================================
        # RESPONSE
        # =================================
        return Response({

            "success": True,

            "message": "OTP verified",

            "is_new_user": created,

            "token": str(
                refresh.access_token
            ),

            "refresh": str(refresh),

            "user": {

                "id":
                    user.id,

                "phone":
                    user.phone,

                "username":
                    user.username,

                "first_name":
                    user.first_name,

                "last_name":
                    user.last_name,
                "email":
                     user.email,

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
            }
        })

    # =================================
    # OTP NOT FOUND
    # =================================
    except OTP.DoesNotExist:

        return Response({
            "error": "OTP not found"
        }, status=404)

    # =================================
    # SERVER ERROR
    # =================================
    except Exception as e:

        print(
            "VERIFY OTP ERROR:",
            str(e)
        )

        return Response({
            "error": str(e)
        }, status=500)


# =========================================
# COMPLETE PROFILE
# =========================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_profile(request):

    user = request.user

    user.first_name = request.data.get(
        'first_name',
        ''
    )

    user.last_name = request.data.get(
        'last_name',
        ''
    )
    user.email = request.data.get(
    'email',
    user.email
)

    user.age = request.data.get(
        'age'
    )

    user.address = request.data.get(
        'address',
        ''
    )

    user.blood_group = request.data.get(
        'blood_group'
    )

    user.is_donor = request.data.get(
        'is_donor',
        False
    )

    user.pincode = request.data.get(
        'pincode',
        user.pincode
    )

    user.save()

    return Response({

        "success": True,

        "message": "Profile completed",

        "user": {

            "id":
                user.id,

            "phone":
                user.phone,

            "first_name":
                user.first_name,

            "last_name":
                user.last_name,

            "email":
                     user.email,

            "age":
                user.age,

            "address":
                user.address,

            "pincode":
                user.pincode,

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
        }
    })


# =========================================
# GET PROFILE
# =========================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):

    user = request.user

    return Response({

        "id":
            user.id,

        "phone":
            user.phone,

        "username":
            user.username,

        "first_name":
            user.first_name,

        "last_name":
            user.last_name,

        "email": 
               user.email,

        "age":
            user.age,

        "address":
            user.address,

        "pincode":
            user.pincode,

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
    })


# =========================================
# TOGGLE DONOR STATUS
# =========================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_donor(request):

    user = request.user

    user.is_available = (
        not user.is_available
    )

    user.save()

    return Response({

        "success": True,

        "available":
            user.is_available
    })


# =========================================
# UPDATE LOCATION
# =========================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_location(request):

    user = request.user

    latitude = request.data.get(
        'latitude'
    )

    longitude = request.data.get(
        'longitude'
    )

    if not latitude or not longitude:

        return Response({
            "error":
                "Latitude and longitude required"
        }, status=400)

    user.latitude = latitude
    user.longitude = longitude

    user.save()

    return Response({

        "success": True,

        "message":
            "Location updated",

        "latitude":
            user.latitude,

        "longitude":
            user.longitude,
    })


# =========================================
# LIVE LOCATIONS
# =========================================
@api_view(['GET'])
def live_locations(request):

    users = User.objects.filter(
        is_available=True
    ).exclude(
        latitude__isnull=True,
        longitude__isnull=True
    )

    return Response(

        list(

            users.values(

                'id',

                'phone',

                'first_name',

                'last_name',

                'email',

                'age',

                'address',

                'blood_group',

                'latitude',

                'longitude',
            )
        )
    )


# =========================================
# ALL USERS FOR ADMIN PANEL
# =========================================
@api_view(['GET'])
@permission_classes([AllowAny])
def all_users(request):

    users = User.objects.all().order_by('-id')

    data = []

    for user in users:

        data.append({

            "id":
                user.id,

            "phone":
                user.phone,

            "username":
                user.username,

            "first_name":
                user.first_name,

            "last_name":
                user.last_name,

            "email":
                     user.email,

            "age":
                user.age,

            "address":
                user.address,

            "pincode":
                user.pincode,

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
        })

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_fcm_token(request):

    token = request.data.get(
        "fcm_token"
    )

    if not token:
        return Response(
            {
                "error":
                "fcm_token required"
            },
            status=400
        )

    request.user.fcm_token = token

    request.user.save()

    return Response({
        "success": True
    })


# =========================================
# HELP & SUPPORT TICKET CREATION
# =========================================
@api_view(['POST'])
@permission_classes([AllowAny])
def create_support_ticket(request):

    subject = request.data.get('subject')
    message = request.data.get('message')

    if not subject or not message:
        return Response(
            {"error": "Subject and message are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = request.user if request.user and request.user.is_authenticated else None

    name = request.data.get('name') or (
        f"{user.first_name} {user.last_name}".strip() or user.username if user else None
    )
    email = request.data.get('email') or (user.email if user else None)
    phone = request.data.get('phone') or (user.phone if user else None)

    ticket = HelpSupport.objects.create(
        user=user,
        name=name,
        email=email,
        phone=phone,
        subject=subject,
        message=message,
        status="pending"
    )

    # Broadcast real-time event to Admin Dashboard
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "requests",
            {
                "type": "send_update",
                "data": {
                    "event": "NEW_SUPPORT_TICKET",
                    "ticket_id": ticket.id,
                    "subject": ticket.subject,
                    "name": ticket.name,
                    "phone": ticket.phone,
                    "email": ticket.email,
                    "status": ticket.status,
                    "created_at": timezone.localtime(ticket.created_at).isoformat()
                }
            }
        )
    except Exception as ws_err:
        print("WS SUPPORT TICKET ERROR:", str(ws_err))

    return Response({
        "success": True,
        "message": "Help & support query submitted successfully",
        "ticket": {
            "id": ticket.id,
            "subject": ticket.subject,
            "message": ticket.message,
            "status": ticket.status,
            "created_at": timezone.localtime(ticket.created_at).isoformat()
        }
    }, status=status.HTTP_201_CREATED)


# =========================================
# FIREBASE PHONE AUTHENTICATION LOGIN
# =========================================
@api_view(['POST'])
@permission_classes([AllowAny])
def firebase_login(request):

    id_token = request.data.get('idToken') or request.data.get('id_token')

    if not id_token:
        return Response(
            {"error": "idToken is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Verify the Firebase ID Token using Firebase Admin SDK
        decoded_token = firebase_auth.verify_id_token(id_token)
        phone_number = decoded_token.get('phone_number')

        if not phone_number:
            return Response(
                {"error": "Firebase token does not contain a phone number"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create user in database
        user, created = User.objects.get_or_create(
            phone=phone_number,
            defaults={'username': phone_number}
        )

        # Generate JWT Tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "message": "Firebase authentication successful",
            "is_new_user": created,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "token": str(refresh.access_token),
            "user": {
                "id": user.id,
                "phone": user.phone,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "blood_group": user.blood_group,
                "is_donor": user.is_donor,
                "is_available": user.is_available,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print("FIREBASE AUTH ERROR:", str(e))
        return Response(
            {"error": f"Invalid or expired Firebase token: {str(e)}"},
            status=status.HTTP_401_UNAUTHORIZED
        )