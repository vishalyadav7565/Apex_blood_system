from rest_framework import serializers
from ambulance_apps.trips.models import Trip
from core.utils import calculate_distance


class TripSerializer(serializers.ModelSerializer):
    driver_details = serializers.SerializerMethodField()
    pickup_otp = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'

    def get_pickup_otp(self, trip):
        if not trip.pickup_otp_hash:
            return None
        if ':' in trip.pickup_otp_hash and not trip.pickup_otp_hash.startswith('pbkdf2_'):
            return trip.pickup_otp_hash.split(':')[0]
        if len(trip.pickup_otp_hash) == 6 and trip.pickup_otp_hash.isdigit():
            return trip.pickup_otp_hash
        return None

    def get_driver_details(self, trip):
        driver = trip.driver
        ambulance = driver.ambulance
        driver_distance_km = None
        if all(value is not None for value in (
            driver.current_latitude,
            driver.current_longitude,
            trip.pickup_latitude,
            trip.pickup_longitude,
        )):
            driver_distance_km = round(calculate_distance(
                driver.current_latitude,
                driver.current_longitude,
                trip.pickup_latitude,
                trip.pickup_longitude,
            ), 2)
        return {
            'id': driver.id,
            'name': driver.name,
            'phone': driver.phone,
            'is_online': driver.is_online,
            'current_latitude': driver.current_latitude,
            'current_longitude': driver.current_longitude,
            'driver_distance_km': driver_distance_km,
            'pickup_location': {
                'latitude': trip.pickup_latitude,
                'longitude': trip.pickup_longitude,
            },
            'ambulance': {
                'id': ambulance.id,
                'vehicle_number': ambulance.vehicle_number,
                'ambulance_type': ambulance.ambulance_type,
            } if ambulance else None,
        }


class BookingCreateSerializer(serializers.ModelSerializer):
    """Validates the patient and location details submitted for a new booking."""

    class Meta:
        model = Trip
        fields = [
            'id',
            'driver',
            'ambulance_type',
            'patient_name',
            'patient_phone',
            'pickup_address',
            'destination_address',
            'pickup_latitude',
            'pickup_longitude',
            'destination_latitude',
            'destination_longitude',
            'status',
            'accepted_at',
            'rejected_at',
            'rejection_reason',
            'pickup_otp_expires_at',
            'otp_verified_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'accepted_at', 'rejected_at', 'rejection_reason',
            'pickup_otp_expires_at', 'otp_verified_at',
            'created_at', 'updated_at',
        ]
        extra_kwargs = {
            'driver': {'required': False},
            'ambulance_type': {'required': False},
        }

    def validate_patient_phone(self, value):
        if value and not value.strip():
            return None
        return value
