from datetime import timedelta
from math import asin, cos, radians, sin, sqrt
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ambulance_apps.ambulance.models import Ambulance
from ambulance_apps.drivers.models import Driver
from ambulance_apps.trips.serializers import BookingCreateSerializer, TripSerializer


PAST_TRIP_STATUSES = ('completed', 'cancelled', 'rejected')
MAX_BOOKING_DISTANCE_KM = 20
NEARBY_OPTIONS_DISTANCE_KM = 5
MAX_NEARBY_OPTIONS = 2
PICKUP_OTP_VALIDITY_MINUTES = 5


def _distance_km(latitude_a, longitude_a, latitude_b, longitude_b):
    """Return straight-line distance between two GPS positions in kilometres."""
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * 6371 * asin(sqrt(haversine))


def _nearby_ambulance_options(ambulance_type, latitude, longitude, max_distance_km):
    """Find available ambulances of a type and order them by driver distance."""
    candidates = (
        Ambulance.objects.select_related('driver')
        .filter(
            ambulance_type=ambulance_type,
            is_active=True,
            is_approved=True,
            is_available=True,
            status='online',
            driver__is_verified=True,
            driver__is_online=True,
        )
        .exclude(
            driver__current_latitude__isnull=True,
            driver__current_longitude__isnull=True,
        )
    )
    nearby = []
    for ambulance in candidates:
        distance_km = _distance_km(
            latitude,
            longitude,
            ambulance.driver.current_latitude,
            ambulance.driver.current_longitude,
        )
        if distance_km <= max_distance_km:
            nearby.append((ambulance, distance_km))
    return sorted(nearby, key=lambda item: item[1])


def _nearby_option_data(ambulance, distance_km):
    return {
        'ambulance_id': ambulance.id,
        'vehicle_number': ambulance.vehicle_number,
        'ambulance_type': ambulance.ambulance_type,
        'driver_id': ambulance.driver.id,
        'driver_name': ambulance.driver.name,
        'driver_phone': ambulance.driver.phone,
        'driver_distance_km': round(distance_km, 2),
    }


def _create_pickup_otp(trip):
    """Create a short-lived OTP. Only its hash is stored in the database."""
    otp = f'{secrets.randbelow(1_000_000):06d}'
    trip.pickup_otp_hash = make_password(otp)
    trip.pickup_otp_expires_at = timezone.now() + timedelta(minutes=PICKUP_OTP_VALIDITY_MINUTES)
    return otp


def _notify_user_about_pickup_otp(trip, otp):
    """Deliver the OTP through email when the patient has a registered email.

    A production SMS/FCM provider can be added here for phone-only users.
    """
    try:
        from apps.users.models import User
        user = User.objects.using('default').filter(phone=trip.patient_phone).first()
        if user and user.email:
            send_mail(
                subject='Your ambulance pickup OTP',
                message=(
                    f'Your ambulance driver accepted the request. Pickup OTP: {otp}. '
                    f'This code expires in {PICKUP_OTP_VALIDITY_MINUTES} minutes. Do not share it before pickup.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
    except Exception:
        # OTP remains valid even if a notification provider is temporarily unavailable.
        pass


def _booking_queryset(request):
    """Build a booking query scoped to one patient, driver, or ambulance."""
    patient_phone = request.query_params.get('patient_phone')
    driver_id = request.query_params.get('driver_id')
    ambulance_id = request.query_params.get('ambulance_id')

    if not any((patient_phone, driver_id, ambulance_id)):
        return None, Response(
            {'detail': 'Provide patient_phone, driver_id, or ambulance_id.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    trips = Trip.objects.select_related('driver__ambulance').order_by('-created_at')
    if patient_phone:
        trips = trips.filter(patient_phone=patient_phone)
    if driver_id:
        trips = trips.filter(driver_id=driver_id)
    if ambulance_id:
        trips = trips.filter(driver__ambulance_id=ambulance_id)
    return trips, None


@api_view(['POST'])
@permission_classes([AllowAny])
def create_booking(request):
    """
    Create a trip for an available driver and reserve that driver's ambulance.

    The ambulance row is locked while the booking is created so two simultaneous
    requests cannot reserve the same ambulance.
    """
    driver_id = request.data.get('driver') or request.data.get('driver_id')
    ambulance_id = request.data.get('ambulance_id')
    ambulance_type = request.data.get('ambulance_type')
    if not driver_id and not ambulance_id and not ambulance_type:
        return Response(
            {'detail': 'Provide ambulance_id, driver_id, or ambulance_type.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = BookingCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pickup_latitude = serializer.validated_data.get('pickup_latitude')
    pickup_longitude = serializer.validated_data.get('pickup_longitude')
    if (
        ambulance_type and not driver_id and not ambulance_id
        and (pickup_latitude is None or pickup_longitude is None)
    ):
        return Response(
            {'detail': 'pickup_latitude and pickup_longitude are required when booking by ambulance_type.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic(using='ambulance_db'):
        if ambulance_id:
            ambulance = get_object_or_404(
                Ambulance.objects.select_for_update().select_related('driver'),
                pk=ambulance_id,
            )
            driver = getattr(ambulance, 'driver', None)
            if not driver:
                return Response(
                    {'detail': 'The selected ambulance has no assigned driver.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if driver_id and str(driver.id) != str(driver_id):
                return Response(
                    {'detail': 'The selected driver is not assigned to this ambulance.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif driver_id:
            driver = get_object_or_404(
                Driver.objects.select_related('ambulance'),
                pk=driver_id,
            )
            if not driver.ambulance_id:
                return Response(
                    {'detail': 'The selected driver is not assigned to an ambulance.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ambulance = Ambulance.objects.select_for_update().get(pk=driver.ambulance_id)
        else:
            # Lock the ambulance before reserving it, so concurrent requests for
            # the same type cannot assign the same vehicle twice.
            candidates = (
                Ambulance.objects.select_for_update(skip_locked=True)
                .select_related('driver')
                .filter(
                    ambulance_type=ambulance_type,
                    is_active=True,
                    is_approved=True,
                    is_available=True,
                    status='online',
                    driver__is_verified=True,
                    driver__is_online=True,
                )
                .exclude(
                    driver__current_latitude__isnull=True,
                    driver__current_longitude__isnull=True,
                )
            )
            nearby_candidates = [
                (candidate, _distance_km(
                    pickup_latitude,
                    pickup_longitude,
                    candidate.driver.current_latitude,
                    candidate.driver.current_longitude,
                ))
                for candidate in candidates
            ]
            nearby_candidates = [
                candidate for candidate in nearby_candidates
                if candidate[1] <= MAX_BOOKING_DISTANCE_KM
            ]
            if not nearby_candidates:
                return Response(
                    {
                        'detail': (
                            f'No {ambulance_type} ambulance is available within '
                            f'{MAX_BOOKING_DISTANCE_KM} km of the pickup location.'
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            ambulance, driver_distance_km = min(nearby_candidates, key=lambda item: item[1])
            driver = ambulance.driver

        if ambulance_type and ambulance.ambulance_type != ambulance_type:
            return Response(
                {'detail': 'The selected ambulance does not match the requested ambulance type.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not driver.is_verified:
            return Response(
                {'detail': 'The selected driver is not verified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not ambulance.is_active or not ambulance.is_approved:
            return Response(
                {'detail': 'The selected ambulance is not active and approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not driver.is_online or ambulance.status != 'online' or not ambulance.is_available:
            return Response(
                {'detail': 'The selected ambulance is not currently available.'},
                status=status.HTTP_409_CONFLICT,
            )

        trip = serializer.save(
            driver=driver,
            ambulance_type=ambulance.ambulance_type,
            status='requested',
        )
        ambulance.is_available = False
        ambulance.status = 'busy'
        ambulance.save(update_fields=['is_available', 'status', 'updated_at'])

    response_data = {
        'message': 'Ambulance booked successfully.',
        'trip': TripSerializer(trip).data,
    }
    dispatch_event = {
        'event': 'NEW_REQUEST',
        'trip': TripSerializer(trip).data,
    }
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            'drivers_online',
            {'type': 'send_update', 'data': dispatch_event},
        )
    if ambulance_type and not driver_id:
        response_data['driver_distance_km'] = round(driver_distance_km, 2)
        response_data['search_radius_km'] = MAX_BOOKING_DISTANCE_KM
    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def pending_driver_requests(request, driver_id):
    """List booking requests waiting for a particular driver's decision."""
    get_object_or_404(Driver, pk=driver_id)
    trips = (
        Trip.objects.filter(driver_id=driver_id, status='requested')
        .select_related('driver__ambulance')
        .order_by('created_at')
    )
    return Response({'requests': TripSerializer(trips, many=True).data})


def _get_driver_trip_for_action(request, trip_id):
    driver_id = request.data.get('driver_id')
    if not driver_id:
        return None, Response(
            {'detail': 'driver_id is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    trip = get_object_or_404(
        Trip.objects.select_for_update().select_related('driver__ambulance'),
        pk=trip_id,
    )
    if str(trip.driver_id) != str(driver_id):
        return None, Response(
            {'detail': 'This booking request is not assigned to this driver.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if trip.status != 'requested':
        return None, Response(
            {'detail': f'This booking request has already been {trip.status}.'},
            status=status.HTTP_409_CONFLICT,
        )
    return trip, None


@api_view(['POST'])
@permission_classes([AllowAny])
def accept_booking_request(request, trip_id):
    """Allow the assigned driver to accept a pending booking request."""
    with transaction.atomic(using='ambulance_db'):
        trip, error_response = _get_driver_trip_for_action(request, trip_id)
        if error_response is not None:
            return error_response
        trip.status = 'accepted'
        trip.accepted_at = timezone.now()
        trip.rejected_at = None
        trip.rejection_reason = None
        otp = _create_pickup_otp(trip)
        trip.save(update_fields=[
            'status', 'accepted_at', 'rejected_at', 'rejection_reason',
            'pickup_otp_hash', 'pickup_otp_expires_at', 'updated_at',
        ])
        _notify_user_about_pickup_otp(trip, otp)

    return Response({
        'message': 'Booking request accepted.',
        'pickup_otp_delivery': 'sent_to_registered_user',
        'pickup_otp_expires_at': trip.pickup_otp_expires_at,
        'trip': TripSerializer(trip).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def reject_booking_request(request, trip_id):
    """Allow the assigned driver to reject a request and release the ambulance."""
    with transaction.atomic(using='ambulance_db'):
        trip, error_response = _get_driver_trip_for_action(request, trip_id)
        if error_response is not None:
            return error_response
        trip.status = 'rejected'
        trip.rejected_at = timezone.now()
        trip.rejection_reason = request.data.get('reason') or 'Rejected by driver'
        trip.save(update_fields=['status', 'rejected_at', 'rejection_reason', 'updated_at'])

        ambulance = Ambulance.objects.select_for_update().get(pk=trip.driver.ambulance_id)
        ambulance.is_available = True
        ambulance.status = 'online' if trip.driver.is_online else 'offline'
        ambulance.save(update_fields=['is_available', 'status', 'updated_at'])

    return Response({
        'message': 'Booking request rejected. Ambulance is available for another booking.',
        'trip': TripSerializer(trip).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_pickup_otp(request, trip_id):
    """Driver verifies the OTP given by the user at pickup and starts the trip."""
    driver_id = request.data.get('driver_id')
    otp = str(request.data.get('otp') or '').strip()
    if not driver_id or not otp:
        return Response(
            {'detail': 'driver_id and otp are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic(using='ambulance_db'):
        trip = get_object_or_404(
            Trip.objects.select_for_update().select_related('driver__ambulance'),
            pk=trip_id,
        )
        if str(trip.driver_id) != str(driver_id):
            return Response({'detail': 'This trip is not assigned to this driver.'}, status=status.HTTP_403_FORBIDDEN)
        if trip.status != 'reached_pickup':
            return Response(
                {'detail': 'The driver must mark reached_pickup before verifying the OTP.'},
                status=status.HTTP_409_CONFLICT,
            )
        if not trip.pickup_otp_hash or not trip.pickup_otp_expires_at:
            return Response({'detail': 'No active pickup OTP exists for this trip.'}, status=status.HTTP_400_BAD_REQUEST)
        if timezone.now() > trip.pickup_otp_expires_at:
            return Response({'detail': 'The pickup OTP has expired.'}, status=status.HTTP_400_BAD_REQUEST)
        if not check_password(otp, trip.pickup_otp_hash):
            return Response({'detail': 'Invalid pickup OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        trip.status = 'picked_up'
        trip.otp_verified_at = timezone.now()
        trip.pickup_otp_hash = None
        trip.save(update_fields=['status', 'otp_verified_at', 'pickup_otp_hash', 'updated_at'])

    return Response({
        'message': 'Pickup OTP verified. Trip started.',
        'trip': TripSerializer(trip).data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def track_booking(request, trip_id):
    """Return the assigned ambulance's latest GPS location for a user booking."""
    patient_phone = request.query_params.get('patient_phone')
    if not patient_phone:
        return Response({'detail': 'patient_phone is required.'}, status=status.HTTP_400_BAD_REQUEST)
    trip = get_object_or_404(
        Trip.objects.select_related('driver__ambulance'),
        pk=trip_id,
        patient_phone=patient_phone,
    )
    driver = trip.driver
    return Response({
        'trip_id': trip.id,
        'status': trip.status,
        'ambulance_location': {
            'latitude': driver.current_latitude,
            'longitude': driver.current_longitude,
            'last_updated_at': driver.last_location_update,
        },
        'driver': TripSerializer(trip).data['driver_details'],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_booking_options(request):
    """Show the two closest available ambulances within five kilometres."""
    ambulance_type = request.query_params.get('ambulance_type')
    latitude = request.query_params.get('pickup_latitude')
    longitude = request.query_params.get('pickup_longitude')
    if not ambulance_type or latitude is None or longitude is None:
        return Response(
            {
                'detail': (
                    'ambulance_type, pickup_latitude, and pickup_longitude are required.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    valid_ambulance_types = {value for value, _ in Ambulance.AMBULANCE_TYPES}
    if ambulance_type not in valid_ambulance_types:
        return Response(
            {'detail': f'ambulance_type must be one of: {", ".join(sorted(valid_ambulance_types))}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return Response(
            {'detail': 'pickup_latitude and pickup_longitude must be valid numbers.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return Response(
            {'detail': 'Pickup coordinates are outside the valid latitude/longitude range.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    nearby = _nearby_ambulance_options(
        ambulance_type,
        latitude,
        longitude,
        NEARBY_OPTIONS_DISTANCE_KM,
    )[:MAX_NEARBY_OPTIONS]
    return Response({
        'ambulance_type': ambulance_type,
        'search_radius_km': NEARBY_OPTIONS_DISTANCE_KM,
        'options': [_nearby_option_data(ambulance, distance) for ambulance, distance in nearby],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def booking_history(request):
    """Return the caller's live and past ambulance bookings in one response."""
    trips, error_response = _booking_queryset(request)
    if error_response is not None:
        return error_response

    live_trips = trips.exclude(status__in=PAST_TRIP_STATUSES)
    past_trips = trips.filter(status__in=PAST_TRIP_STATUSES)
    return Response({
        'live_bookings': TripSerializer(live_trips, many=True).data,
        'past_bookings': TripSerializer(past_trips, many=True).data,
        'live_count': live_trips.count(),
        'past_count': past_trips.count(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def live_bookings(request):
    """Return only currently active bookings."""
    trips, error_response = _booking_queryset(request)
    if error_response is not None:
        return error_response
    trips = trips.exclude(status__in=PAST_TRIP_STATUSES)
    return Response({'bookings': TripSerializer(trips, many=True).data})


@api_view(['GET'])
@permission_classes([AllowAny])
def past_bookings(request):
    """Return only completed or cancelled bookings."""
    trips, error_response = _booking_queryset(request)
    if error_response is not None:
        return error_response
    trips = trips.filter(status__in=PAST_TRIP_STATUSES)
    return Response({'bookings': TripSerializer(trips, many=True).data})
