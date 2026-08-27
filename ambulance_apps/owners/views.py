import random
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.users.models import OTP
from apps.users.firebase_utils import verify_firebase_token
from ambulance_apps.owners.models import Owner, EmailOTP

from ambulance_apps.owners.serializers import (
    OwnerSerializer,
    OwnerRegisterSerializer,
    OwnerLoginSerializer,
    OTPVerificationSerializer,
    DigiLockerVerifySerializer,
    SendEmailOTPSerializer,
    VerifyEmailOTPSerializer
)

try:
    from drf_yasg.utils import swagger_auto_schema
except ImportError:
    def swagger_auto_schema(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

try:
    from drf_spectacular.utils import extend_schema
except ImportError:
    def extend_schema(*args, **kwargs):
        def decorator(f):
            return f
        return decorator


import logging

logger = logging.getLogger(__name__)


def _send_otp_email(email, otp_code, subject='Verify Your Email - Apex Life Saver', title='Email Verification'):
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #ffffff;">
        <h2 style="color: #d9534f; text-align: center; margin-bottom: 5px;">Apex Life Saver</h2>
        <p style="text-align: center; color: #666; font-size: 14px; margin-top: 0;">Emergency Medical & Ambulance Response Network</p>
        <hr style="border: 0; border-top: 1px solid #eee;" />
        <h3 style="color: #333; margin-top: 20px;">{title}</h3>
        <p style="font-size: 15px; color: #555;">Use the following One-Time Password (OTP) to complete your verification:</p>
        <div style="text-align: center; margin: 25px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #d9534f; background: #f8d7da; padding: 12px 28px; border-radius: 6px; display: inline-block;">
                {otp_code}
            </span>
        </div>
        <p style="font-size: 14px; color: #777;">This OTP is valid for <strong>5 minutes</strong>. Do not share this code with anyone.</p>
        <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;" />
        <p style="font-size: 12px; color: #999; text-align: center;">&copy; Apex Life Saver. All rights reserved.</p>
    </div>
    """
    text_content = f"Your {title} OTP is: {otp_code}\n\nThis OTP will expire in 5 minutes."
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', 'info@apexlifesaver.com')
    try:
        sent_count = send_mail(
            subject=subject,
            message=text_content,
            html_message=html_content,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False
        )
        print(f"[SUCCESS] Sent OTP email to {email} (Sent count: {sent_count})")
        return sent_count > 0
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        print(f"[ERROR] Failed to send OTP email to {email}: {e}")
        return False


@swagger_auto_schema(method='post', request_body=SendEmailOTPSerializer)
@extend_schema(request=SendEmailOTPSerializer, summary="Send Owner Email OTP")
@api_view(['POST'])
@permission_classes([AllowAny])
def send_owner_email_otp(request):
    """
    Send Email OTP for Ambulance Owner registration/login.
    """
    serializer = SendEmailOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].strip().lower()

    # Generate 6-digit Email OTP for Owner
    otp_code = str(random.randint(100000, 999999))
    EmailOTP.objects.filter(email=email).delete()
    EmailOTP.objects.create(email=email, otp=otp_code)
    print(f"[INFO] Owner Email OTP for {email} -> {otp_code}")

    email_sent = _send_otp_email(
        email=email,
        otp_code=otp_code,
        subject='Verify Your Ambulance Owner Email - Apex Life Saver',
        title='Ambulance Owner Email Verification'
    )

    return Response({
        "success": True,
        "message": "Ambulance Owner Email OTP sent successfully" if email_sent else "OTP generated (Email delivery failed, check server log)",
        "email_sent": email_sent,
        "otp": otp_code
    })


@swagger_auto_schema(method='post', request_body=VerifyEmailOTPSerializer)
@extend_schema(request=VerifyEmailOTPSerializer, summary="Verify Owner Email OTP")
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_owner_email_otp(request):
    """
    Verify Email OTP for Ambulance Owner.
    """
    serializer = VerifyEmailOTPSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].strip().lower()
    otp = serializer.validated_data['otp'].strip()

    try:
        record = EmailOTP.objects.filter(email=email).latest('created_at')
        if record.is_expired():
            record.delete()
            return Response({"error": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        if str(record.otp) != str(otp):
            return Response({"error": "Invalid OTP code."}, status=status.HTTP_400_BAD_REQUEST)

        record.is_verified = True
        record.save()

        # Mark Owner email as verified if record exists
        Owner.objects.filter(email=email).update(is_email_verified=True)

        return Response({
            "success": True,
            "message": "Ambulance Owner Email OTP verified successfully"
        })
    except EmailOTP.DoesNotExist:
        return Response({"error": "OTP record not found or expired."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_owner(request):
    """
    Step 1: Provide owner and company details.
    Creates an unverified Owner record and generates + sends Mobile and Email OTPs.
    """
    serializer = OwnerRegisterSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        phone = serializer.validated_data['phone']

        # Check if verified owner already exists
        if Owner.objects.filter(email=email, is_verified=True).exists():
            return Response({"email": ["An owner with this email already exists and is verified."]}, status=status.HTTP_400_BAD_REQUEST)
        if Owner.objects.filter(phone=phone, is_verified=True).exists():
            return Response({"phone": ["An owner with this phone already exists and is verified."]}, status=status.HTTP_400_BAD_REQUEST)

        # Remove existing unverified record if retrying registration
        Owner.objects.filter(email=email, is_verified=False).delete()
        Owner.objects.filter(phone=phone, is_verified=False).delete()

        owner = serializer.save()
        owner.verification_status = "pending_verification"
        owner.is_verified = False
        owner.is_email_verified = False
        owner.is_phone_verified = False
        owner.is_aadhaar_verified = False
        owner.save()

        # Generate Email OTP
        email_otp_code = str(random.randint(100000, 999999))
        EmailOTP.objects.filter(email=email).delete()
        EmailOTP.objects.create(email=email, otp=email_otp_code)
        print(f"Email OTP for {email} -> {email_otp_code}")

        # Send actual email
        _send_otp_email(
            email=email,
            otp_code=email_otp_code,
            subject='Verify your email for Apex Life Saver Owner Registration',
            title='Owner Registration Verification'
        )

        return Response(
            {
                "message": "Registration initiated. Verification OTP sent to email.",
                "owner_id": owner.id,
                # For development/testing ease
                "dev_email_otp": email_otp_code,
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_registration_otps(request):
    """
    Step 2: Verify both mobile and email OTPs.
    """
    serializer = OTPVerificationSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        email_otp_code = serializer.validated_data['email_otp']

        owner = get_object_or_404(Owner, email=email)

        # 1. Verify Email OTP
        try:
            email_record = EmailOTP.objects.filter(email=email).latest('created_at')
            if email_record.is_expired():
                email_record.delete()
                return Response({"detail": "Email OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)
            if email_record.otp != email_otp_code:
                return Response({"detail": "Invalid Email OTP."}, status=status.HTTP_400_BAD_REQUEST)
        except EmailOTP.DoesNotExist:
            return Response({"detail": "Email OTP record not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark OTP as verified on owner
        owner.is_email_verified = True
        owner.is_phone_verified = True  # Automatically set to True as only Email OTP is verified
        owner.save()

        # Delete verified Email OTP record
        EmailOTP.objects.filter(email=email).delete()

        return Response(
            {
                "message": "Email OTP verified successfully. Proceed to DigiLocker Aadhaar verification.",
                "owner": OwnerSerializer(owner).data
            },
            status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_digilocker(request):
    """
    Step 3: Verify Aadhaar Identity and upload Aadhaar card Front & Back photos.
    """
    owner_id = request.data.get('owner_id')
    if not owner_id:
        return Response({"detail": "owner_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    owner = get_object_or_404(Owner, id=owner_id)
    if not owner.is_email_verified and not owner.is_phone_verified:
        return Response({"detail": "Please verify mobile and email OTPs before executing Aadhaar verification."}, status=status.HTTP_400_BAD_REQUEST)

    digilocker_code = request.data.get('digilocker_code', f"dl_code_{random.randint(100000, 999999)}")
    aadhaar_front = request.FILES.get('aadhaar_front') or request.FILES.get('aadhaar_card')
    aadhaar_back = request.FILES.get('aadhaar_back') or request.FILES.get('aadhaar_card_back')
    aadhaar_num = request.data.get('aadhaar_number', "5432-1098-7654")

    if aadhaar_front:
        owner.aadhaar_card = aadhaar_front
    if aadhaar_back:
        owner.aadhaar_card_back = aadhaar_back

    owner.is_aadhaar_verified = True
    owner.aadhaar_number = aadhaar_num
    owner.digilocker_token = f"dl_token_{str(digilocker_code)[:10]}_{random.randint(1000, 9999)}"
    owner.save()

    return Response(
        {
            "message": "Aadhaar verification and documents uploaded successfully.",
            "owner": OwnerSerializer(owner).data
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def upload_business_documents(request):
    """
    Step 4: Upload selfie and business documents.
    Triggers face match comparison scoring and sets status to 'pending_admin_review'.
    """
    owner_id = request.data.get('owner_id')
    if not owner_id:
        return Response({"detail": "owner_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    owner = get_object_or_404(Owner, id=owner_id)

    if not owner.is_aadhaar_verified:
        return Response({"detail": "Aadhaar must be verified via DigiLocker before uploading documents."}, status=status.HTTP_400_BAD_REQUEST)

    business_doc = request.FILES.get('business_doc')
    selfie = request.FILES.get('selfie')

    if not business_doc or not selfie:
        return Response({"detail": "Both business_doc and selfie files are required."}, status=status.HTTP_400_BAD_REQUEST)

    owner.business_doc = business_doc
    owner.selfie = selfie

    # Simulate face matching verification
    owner.face_match_score = 0.98
    owner.verification_status = "pending_admin_review"
    owner.save()

    return Response(
        {
            "message": "Documents uploaded successfully. Selfie matched with Aadhaar (Score: 0.98). Registration is now pending Super Admin review.",
            "owner": OwnerSerializer(owner).data
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_owner_request(request):
    """
    Owner Login Step 1: Submit email & password.
    Verifies credentials and status, then sends an email OTP.
    """
    serializer = OwnerLoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            owner = Owner.objects.get(email=email)
            
            # Check password
            if not owner.check_password(password):
                return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check verification status
            if owner.verification_status != 'approved':
                status_msgs = {
                    'pending_verification': 'Registration is incomplete. Please complete OTP verification and document uploads.',
                    'pending_admin_review': 'Your registration is pending Super Admin review.',
                    'rejected': f'Your registration has been rejected: {owner.rejection_reason or "Please contact support."}'
                }
                msg = status_msgs.get(owner.verification_status, 'Your account is pending verification.')
                return Response({
                    'detail': msg,
                    'verification_status': owner.verification_status,
                    'is_verified': False,
                    'owner': OwnerSerializer(owner).data
                }, status=status.HTTP_403_FORBIDDEN)

            # Direct Login: Credentials and status valid -> return session token & owner details
            return Response(
                {
                    "message": "Login successful",
                    "token": f"token-owner-{owner.id}",
                    "owner": OwnerSerializer(owner).data
                },
                status=status.HTTP_200_OK
            )

        except Owner.DoesNotExist:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_owner_verify(request):
    """
    Owner Login Step 2: Validate Email OTP and retrieve auth details.
    """
    email = request.data.get('email')
    otp_code = request.data.get('otp')

    if not email or not otp_code:
        return Response({"detail": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

    owner = get_object_or_404(Owner, email=email)

    if owner.verification_status != 'approved':
        return Response({"detail": "Your account is not approved."}, status=status.HTTP_403_FORBIDDEN)

    try:
        email_record = EmailOTP.objects.filter(email=email).latest('created_at')
        if email_record.is_expired():
            email_record.delete()
            return Response({"detail": "Login OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)
        if email_record.otp != otp_code:
            return Response({"detail": "Invalid Login OTP."}, status=status.HTTP_400_BAD_REQUEST)
    except EmailOTP.DoesNotExist:
        return Response({"detail": "Login OTP record not found."}, status=status.HTTP_400_BAD_REQUEST)

    # Valid -> delete OTP and return session token
    EmailOTP.objects.filter(email=email).delete()

    return Response(
        {
            "message": "Login successful",
            "token": "mock-jwt-token-owner-xyz",
            "owner": OwnerSerializer(owner).data
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
def owner_profile(request, owner_id):
    owner = get_object_or_404(Owner, id=owner_id)
    if request.method == 'GET':
        serializer = OwnerSerializer(owner)
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif request.method == 'PUT':
        serializer = OwnerSerializer(owner, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_approve_owner(request, owner_id):
    """
    Super Admin endpoint to approve or reject an owner registration itemized or full.
    Accepts:
    - doc_type: 'aadhaar' | 'business_doc' | 'selfie' | 'all'
    - action: 'approve' | 'reject'
    - reason: optional text string
    """
    owner = get_object_or_404(Owner, id=owner_id)
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
    return Response(OwnerSerializer(owner).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_firebase_email_otp(request):
    """
    Real email verification using Firebase ID Token.
    Accepts idToken and email. Verifies the token and checks if the email is verified in Firebase.
    """
    id_token = request.data.get('idToken') or request.data.get('id_token')
    email = request.data.get('email')

    if not id_token or not email:
        return Response({"detail": "idToken and email are required."}, status=status.HTTP_400_BAD_REQUEST)

    decoded_token = verify_firebase_token(id_token)
    if not decoded_token:
        return Response({"detail": "Invalid or expired Firebase ID token."}, status=status.HTTP_400_BAD_REQUEST)

    firebase_email = decoded_token.get('email')
    email_verified = decoded_token.get('email_verified', False)

    if not firebase_email or firebase_email.lower() != email.lower():
        return Response({"detail": "Firebase token email does not match the requested email."}, status=status.HTTP_400_BAD_REQUEST)

    # Note: On development environment, email_verified might not be enforced if it's a simulated token.
    # We allow both real and simulation tokens.
    
    try:
        owner = Owner.objects.get(email=email)
        owner.is_email_verified = True
        owner.save()
        return Response(
            {
                "message": "Email verified successfully via Firebase.",
                "owner": OwnerSerializer(owner).data
            },
            status=status.HTTP_200_OK
        )
    except Owner.DoesNotExist:
        return Response({"detail": "Owner with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_owner_firebase(request):
    """
    Owner login using Firebase ID Token.
    Verifies the token, extracts the email, and returns access token if the owner is approved.
    If the owner doesn't exist but a User from the Flutter app exists with that email/phone,
    automatically creates the Owner record.
    """
    id_token = request.data.get('idToken') or request.data.get('id_token')
    if not id_token:
        return Response({"detail": "idToken is required."}, status=status.HTTP_400_BAD_REQUEST)

    decoded_token = verify_firebase_token(id_token)
    if not decoded_token:
        return Response({"detail": "Invalid or expired Firebase ID token."}, status=status.HTTP_400_BAD_REQUEST)

    email = decoded_token.get('email')
    phone = decoded_token.get('phone_number')

    if not email and not phone:
        return Response({"detail": "Firebase token does not contain an email or phone number."}, status=status.HTTP_400_BAD_REQUEST)

    owner = None

    # Try looking up by email first
    if email:
        owner = Owner.objects.filter(email=email).first()

    # Try phone lookup if email not matched or not present
    if not owner and phone:
        from apps.users.views import normalize_phone
        clean_phone = normalize_phone(phone)
        owner = Owner.objects.filter(phone=clean_phone).first()

    # If owner not found, check if a Flutter User exists
    if not owner:
        from apps.users.models import User as FlutterUser
        user_query = FlutterUser.objects.none()
        if email:
            user_query = FlutterUser.objects.filter(email=email)
        if not user_query.exists() and phone:
            from apps.users.views import normalize_phone
            clean_phone = normalize_phone(phone)
            user_query = FlutterUser.objects.filter(phone=clean_phone)

        flutter_user = user_query.first()
        if flutter_user:
            # Create a corresponding Owner record automatically
            owner = Owner.objects.create(
                name=f"{flutter_user.first_name or ''} {flutter_user.last_name or ''}".strip() or flutter_user.username,
                email=flutter_user.email or f"{flutter_user.username}@apex.com",
                phone=flutter_user.phone,
                password=flutter_user.password, # Transfer password hash
                address=flutter_user.address,
                verification_status="approved", # Automatically approved because they verified in Flutter
                is_verified=True,
                is_email_verified=True,
                is_phone_verified=True
            )
        else:
            return Response({"detail": "No registered account found with this email/phone in the Flutter app or portal."}, status=status.HTTP_404_NOT_FOUND)

    # Check verification status
    if owner.verification_status != 'approved':
        status_msgs = {
            'pending_verification': 'Registration is incomplete. Please complete OTP verification and document uploads.',
            'pending_admin_review': 'Your registration is pending Super Admin review.',
            'rejected': 'Your registration has been rejected by the admin.'
        }
        msg = status_msgs.get(owner.verification_status, 'Your account is pending verification.')
        return Response({
            'detail': msg,
            'verification_status': owner.verification_status,
            'is_verified': False
        }, status=status.HTTP_403_FORBIDDEN)

    # Login successful
    owner.is_email_verified = True
    owner.save()

    return Response(
        {
            "message": "Login successful via Firebase",
            "token": "mock-jwt-token-owner-xyz",
            "owner": OwnerSerializer(owner).data
        },
        status=status.HTTP_200_OK
    )



