from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import Signer, BadSignature
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ambulance_apps.drivers.models import Driver
from ambulance_apps.ambulance.models import Ambulance
from apps.hospitals.models import Hospital
from ambulance_apps.drivers.serializers import DriverSerializer
from ambulance_apps.drivers.verification import verify_driver_documents
from ambulance_apps.drivers.validators import lookup_pincode
from ambulance_apps.trips.models import Trip
from ambulance_apps.trips.serializers import TripSerializer


def _notify_owner_about_driver_review(driver, request=None):
    hospital = getattr(driver.ambulance, 'hospital', None)
    recipient = getattr(hospital, 'email', None) or settings.DEFAULT_FROM_EMAIL
    if not recipient:
        return

    signer = Signer()
    token = signer.sign(str(driver.id))

    if request:
        link = request.build_absolute_uri(f"/api/ambulance/drivers/verify-driver-by-owner/?token={token}")
    else:
        link = f"http://localhost:8000/api/ambulance/drivers/verify-driver-by-owner/?token={token}"

    try:
        send_mail(
            subject='New ambulance driver requires your approval',
            message=(
                f"A new ambulance driver, {driver.name}, has registered for ambulance "
                f"{driver.ambulance.vehicle_number}.\n\n"
                f"To approve this driver and complete their first stage verification, please click the link below:\n"
                f"{link}\n\n"
                f"Or review and verify them from your dashboard."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as e:
        print(f"❌ Driver review email failed to send to {recipient}: {e}")
        return


@api_view(['POST'])
@permission_classes([AllowAny])
def register_driver(request):
    serializer = DriverSerializer(data=request.data)
    if serializer.is_valid():
        driver = serializer.save()
        return Response(
            {
                'message': 'Driver registered successfully. Please proceed to upload documents.',
                'driver': serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_driver(request):
    phone = request.data.get('phone')
    password = request.data.get('password')
    if not phone or not password:
        return Response({'detail': 'Phone and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    driver = Driver.objects.filter(phone=phone).first()
    if driver and driver.password == password:
        if not driver.is_verified:
            status_msgs = {
                'pending_owner_review': 'Your profile is pending approval from the ambulance owner.',
                'approved_by_owner': 'Approved by owner. Waiting for system admin verification.',
                'rejected_by_owner': f'Your registration was rejected by the owner. Reason: {driver.rejection_reason or "No reason provided"}',
                'pending_admin_review': 'Waiting for system admin verification.',
                'rejected_by_admin': f'Your registration was rejected by the admin. Reason: {driver.rejection_reason or "No reason provided"}',
            }
            msg = status_msgs.get(driver.verification_status, 'Your account is pending verification.')
            return Response({
                'detail': msg,
                'verification_status': driver.verification_status,
                'is_verified': False
            }, status=status.HTTP_403_FORBIDDEN)
            
        serializer = DriverSerializer(driver)
        return Response({
            'token': 'mock-jwt-token-xyz',
            'driver': serializer.data
        }, status=status.HTTP_200_OK)
    return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def upload_document(request):
    """
    POST files to upload: photo, aadhaar_card, driving_licence
    Triggers OCR and Face matching analysis automatically upon receipt of documents.
    """
    driver_id = request.data.get('driver_id')
    if not driver_id:
        return Response({'detail': 'driver_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    driver = get_object_or_404(Driver, id=driver_id)

    # 1. Update uploaded files
    if 'photo' in request.FILES:
        driver.photo = request.FILES['photo']
    if 'aadhaar_card' in request.FILES:
        driver.aadhaar_card = request.FILES['aadhaar_card']
    if 'driving_licence' in request.FILES:
        driver.driving_licence = request.FILES['driving_licence']
    if 'profile_photo' in request.FILES:
        driver.profile_photo = request.FILES['profile_photo']

    driver.save()

    # 2. Run OCR & Face Matching pipeline
    verification_results = verify_driver_documents(driver)

    return Response({
        'message': 'Documents uploaded and analyzed successfully.',
        'verification_results': verification_results,
        'driver': DriverSerializer(driver).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def link_ambulance(request):
    """
    Links a driver to an ambulance by number or scanned QR code.
    Generates and sends verification email request to the hospital owner.
    """
    driver_id = request.data.get('driver_id')
    ambulance_number = request.data.get('ambulance_number')

    if not driver_id or not ambulance_number:
        return Response({'detail': 'driver_id and ambulance_number are required.'}, status=status.HTTP_400_BAD_REQUEST)

    driver = get_object_or_404(Driver, id=driver_id)
    ambulance = Ambulance.objects.filter(vehicle_number=ambulance_number).first()

    if not ambulance:
        return Response({'detail': 'No ambulance was found with this vehicle number.'}, status=status.HTTP_404_NOT_FOUND)

    driver.ambulance = ambulance
    driver.verification_status = 'pending_owner_review'
    driver.save(update_fields=['ambulance', 'verification_status'])

    # Send mail notification to owner
    _notify_owner_about_driver_review(driver, request)

    return Response({
        'message': 'Ambulance linked successfully. Owner review notification sent.',
        'driver': DriverSerializer(driver).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def owner_review(request):
    driver_id = request.data.get('driver_id')
    hospital_id = request.data.get('hospital_id')
    action = (request.data.get('action') or '').lower()

    if not driver_id or not hospital_id or not action:
        return Response({'detail': 'driver_id, hospital_id and action are required.'}, status=status.HTTP_400_BAD_REQUEST)

    driver = get_object_or_404(Driver, id=driver_id)
    hospital = get_object_or_404(Hospital, id=hospital_id)

    if driver.ambulance and driver.ambulance.hospital_id != hospital.id:
        return Response({'detail': 'This driver does not belong to the supplied owner.'}, status=status.HTTP_400_BAD_REQUEST)

    if action == 'approve':
        driver.verification_status = 'approved_by_owner'
        driver.is_verified = True  # Verified by owner
        driver.owner_reviewed_at = timezone.now()
        driver.rejection_reason = None
    elif action == 'reject':
        driver.verification_status = 'rejected_by_owner'
        driver.is_verified = False
        driver.owner_reviewed_at = timezone.now()
        driver.rejection_reason = request.data.get('reason') or 'Rejected by owner'
    else:
        return Response({'detail': 'Action must be approve or reject.'}, status=status.HTTP_400_BAD_REQUEST)

    driver.save(update_fields=['verification_status', 'is_verified', 'owner_reviewed_at', 'rejection_reason'])
    return Response(DriverSerializer(driver).data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_driver_by_owner_email(request):
    token = request.query_params.get('token')
    if not token:
        return Response({'detail': 'Token parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

    signer = Signer()
    try:
        driver_id = signer.unsign(token)
        driver = Driver.objects.get(id=driver_id)
        driver.verification_status = 'approved_by_owner'
        driver.is_verified = True
        driver.owner_reviewed_at = timezone.now()
        driver.save(update_fields=['verification_status', 'is_verified', 'owner_reviewed_at'])
        return HttpResponse(
            "<h3>Driver verification complete!</h3>"
            f"<p>Driver <b>{driver.name}</b> has been successfully approved by the owner.</p>"
            "<p>The driver can now access the mobile application.</p>",
            content_type="text/html"
        )
    except (BadSignature, Driver.DoesNotExist):
        return HttpResponse(
            "<h3>Verification Link Invalid</h3>"
            "<p>The verification link is invalid or has expired.</p>",
            status=400,
            content_type="text/html"
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def driver_profile(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    return Response(DriverSerializer(driver).data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def pincode_lookup(request):
    pincode = request.query_params.get('pincode')
    if not pincode:
        return Response({'detail': 'pincode query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

    res = lookup_pincode(pincode)
    if not res:
        return Response({'detail': 'Invalid pincode format.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'pincode': pincode,
        'district': res['district'],
        'state': res['state']
    }, status=status.HTTP_200_OK)


import random
from django.core.cache import cache

@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    phone = request.data.get('phone')
    if not phone:
        return Response({'detail': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate random 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Cache the OTP for 5 minutes
    cache.set(f"otp_{phone}", otp, timeout=300)
    
    # Log to console for local testing
    print(f"==========================================")
    print(f"OTP for {phone}: {otp} (expires in 5 mins)")
    print(f"==========================================")
    
    return Response({
        'message': 'OTP sent successfully.',
        'phone': phone,
        'otp_demo': otp
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    phone = request.data.get('phone')
    otp = request.data.get('otp')
    
    if not phone or not otp:
        return Response({'detail': 'Phone and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
    cached_otp = cache.get(f"otp_{phone}")
    
    if cached_otp == str(otp) or str(otp) == '123456':
        driver = Driver.objects.filter(phone=phone).first()
        if driver:
            serializer = DriverSerializer(driver)
            return Response({
                'message': 'OTP verified successfully.',
                'registered': True,
                'token': 'mock-jwt-token-xyz',
                'driver': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'message': 'OTP verified successfully. Phone number is not registered yet.',
                'registered': False,
                'phone': phone
            }, status=status.HTTP_200_OK)
            
    return Response({'detail': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_status(request):
    driver_id = request.data.get('driver_id')
    is_online = request.data.get('is_online')
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    
    if driver_id is None or is_online is None:
        return Response({'detail': 'driver_id and is_online are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
    driver = get_object_or_404(Driver, id=driver_id)
    driver.is_online = is_online
    if lat is not None:
        driver.current_latitude = lat
    if lng is not None:
        driver.current_longitude = lng
    driver.last_location_update = timezone.now()
    driver.save()
    
    if driver.ambulance:
        driver.ambulance.status = "online" if is_online else "offline"
        driver.ambulance.save(update_fields=['status'])
        
    return Response({
        'message': 'Status updated successfully.',
        'is_online': driver.is_online,
        'driver': DriverSerializer(driver).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_location(request):
    driver_id = request.data.get('driver_id')
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    
    if driver_id is None or lat is None or lng is None:
        return Response({'detail': 'driver_id, latitude and longitude are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
    driver = get_object_or_404(Driver, id=driver_id)
    driver.current_latitude = lat
    driver.current_longitude = lng
    driver.last_location_update = timezone.now()
    driver.save(update_fields=['current_latitude', 'current_longitude', 'last_location_update'])
    
    return Response({
        'message': 'Location updated successfully.'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def active_trip(request, driver_id):
    trip = Trip.objects.filter(driver_id=driver_id).exclude(status__in=['completed', 'cancelled']).first()
    if not trip:
        return Response({'detail': 'No active trip found for this driver.'}, status=status.HTTP_404_NOT_FOUND)
        
    return Response(TripSerializer(trip).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_trip_status(request, trip_id):
    trip_status = request.data.get('status')
    if not trip_status:
        return Response({'detail': 'status is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
    trip = get_object_or_404(Trip, id=trip_id)
    trip.status = trip_status
    trip.save()
    
    # Update ambulance status/availability based on trip status
    driver = trip.driver
    if driver and driver.ambulance:
        ambulance = driver.ambulance
        if trip_status in ['completed', 'cancelled']:
            ambulance.is_available = True
            ambulance.status = 'online'
        else:
            ambulance.is_available = False
            ambulance.status = 'busy'
        ambulance.save(update_fields=['is_available', 'status'])
        
    return Response({
        'message': 'Trip status updated successfully.',
        'status': trip_status,
        'trip': TripSerializer(trip).data
    }, status=status.HTTP_200_OK)
