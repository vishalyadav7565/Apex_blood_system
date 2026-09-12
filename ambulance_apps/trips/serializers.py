from rest_framework import serializers
from ambulance_apps.trips.models import Trip


class TripSerializer(serializers.ModelSerializer):
    driver_details = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'

    def get_driver_details(self, trip):
        driver = trip.driver
        ambulance = driver.ambulance
        return {
            'id': driver.id,
            'name': driver.name,
            'phone': driver.phone,
            'is_online': driver.is_online,
            'current_latitude': driver.current_latitude,
            'current_longitude': driver.current_longitude,
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
