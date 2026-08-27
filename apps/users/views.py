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

from django.core.mail import send_mail
from django.conf import settings

from firebase_admin import auth as firebase_auth
from . import firebase_utils
from .models import OTP, HelpSupport

try:
    from drf_spectacular.utils import extend_schema
except ImportError:
    def extend_schema(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

User = get_user_model()


def normalize_phone(phone):
    if not phone:
        return ""
    # Remove all non-digit characters
    digits = "".join(c for c in phone if c.isdigit())
    # If the number has 12 digits and starts with '91' (Indian country code), strip it
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    # If it has 11 digits and starts with '0', strip it
    elif len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    return digits



# =========================================
# SEND OTP
# =========================================
@extend_schema(tags=['Authentication & OTP'], summary="Send Phone or Email OTP")
@ratelimit(
    key='ip',
    rate='5/m',
    block=True
)
@api_view(['POST'])
def send_otp(request):

    raw_phone = request.data.get('phone')
    phone = normalize_phone(raw_phone)
    raw_email = request.data.get('email')
    email = raw_email.strip().lower() if raw_email else ""

    target_identifier = phone or email

    if not target_identifier:
        return Response(
            {"error": "Phone or email required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # remove old otp
    OTP.objects.filter(
        phone=target_identifier
    ).delete()

    # generate new otp
    otp = str(
        random.randint(100000, 999999)
    )

    OTP.objects.create(
        phone=target_identifier,
        otp=otp
    )

    print(f"[INFO] OTP for {target_identifier} -> {otp}")

    email_sent = False
    if email:
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #ffffff;">
            <h2 style="color: #d9534f; text-align: center; margin-bottom: 5px;">Apex Life Saver</h2>
            <p style="text-align: center; color: #666; font-size: 14px; margin-top: 0;">Emergency Medical Response Network</p>
            <hr style="border: 0; border-top: 1px solid #eee;" />
            <h3 style="color: #333; margin-top: 20px;">User Verification Code</h3>
            <p style="font-size: 15px; color: #555;">Use the following One-Time Password (OTP) to complete your login or registration:</p>
            <div style="text-align: center; margin: 25px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #d9534f; background: #f8d7da; padding: 12px 28px; border-radius: 6px; display: inline-block;">
                    {otp}
                </span>
            </div>
            <p style="font-size: 14px; color: #777;">This OTP is valid for <strong>5 minutes</strong>. Do not share this code with anyone.</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
            <p style="font-size: 12px; color: #999; text-align: center;">&copy; Apex Life Saver. All rights reserved.</p>
        </div>
        """
        text_content = f"Your Apex Life Saver OTP is: {otp}\n\nThis OTP will expire in 5 minutes."
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', 'info@apexlifesaver.com')
        try:
            sent_count = send_mail(
                subject="Your Verification Code - Apex Life Saver",
                message=text_content,
                html_message=html_content,
                from_email=from_email,
                recipient_list=[email],
                fail_silently=False
            )
            email_sent = sent_count > 0
            print(f"[SUCCESS] User OTP email sent to {email} (Sent count: {sent_count})")
        except Exception as e:
            print(f"[ERROR] Failed to send user OTP email to {email}: {e}")

    resp = {
        "success": True,
        "message": "OTP sent",
        "otp": otp
    }
    if email:
        resp["email_sent"] = email_sent

    return Response(resp)


# =========================================
# VERIFY OTP + LOGIN/REGISTER
# =========================================
@extend_schema(tags=['Authentication & OTP'], summary="Verify Phone or Email OTP & Login")
@ratelimit(
    key='ip',
    rate='10/m',
    block=True
)
@api_view(['POST'])
def verify_otp(request):

    raw_phone = request.data.get('phone')
    phone = normalize_phone(raw_phone)
    raw_email = request.data.get('email')
    email = raw_email.strip().lower() if raw_email else ""
    target_identifier = phone or email

    otp = request.data.get('otp')

    # =================================
    # VALIDATION
    # =================================
    if not target_identifier or not otp:

        return Response({
            "error": "Phone/email and OTP required"
        }, status=400)

    try:

        # =================================
        # GET LATEST OTP
        # =================================
        record = OTP.objects.filter(
            phone=target_identifier
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

    user.first_name = request.data.get('first_name', user.first_name)
    user.last_name = request.data.get('last_name', user.last_name)
    user.email = request.data.get('email', user.email)
    user.age = request.data.get('age', user.age)
    user.address = request.data.get('address', user.address)
    user.blood_group = request.data.get('blood_group', user.blood_group)
    user.pincode = request.data.get('pincode', user.pincode)

    if 'is_donor' in request.data:
        user.is_donor = request.data.get('is_donor')

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
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def firebase_login(request):

    if request.method == 'GET':
        id_token = request.query_params.get('idToken') or request.query_params.get('id_token')
        if not id_token:
            return Response(
                {"message": "Firebase Login Endpoint. Please submit a POST request with 'idToken' in the request body, or a GET request with 'idToken' in the query parameters."},
                status=status.HTTP_200_OK
            )
    else:
        id_token = request.data.get('idToken') or request.data.get('id_token')

    if not id_token:
        return Response(
            {"error": "idToken is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Verify the Firebase ID Token using Firebase Admin SDK
        decoded_token = firebase_auth.verify_id_token(id_token, clock_skew_seconds=60)
        phone_number = normalize_phone(decoded_token.get('phone_number'))

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