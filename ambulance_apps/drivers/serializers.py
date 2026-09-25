from rest_framework import serializers
from ambulance_apps.drivers.models import Driver
from ambulance_apps.ambulance.models import Ambulance


class DriverSerializer(serializers.ModelSerializer):
    ambulance_number = serializers.CharField(write_only=True, required=False)
    ambulance_details = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = [
            'id', 'name', 'phone', 'email', 'password', 'ambulance', 'ambulance_details', 'ambulance_number', 'license_number',
            'license_expiry', 'aadhaar_number', 'aadhaar_card', 'driving_licence', 'photo', 'profile_photo',
            'father_name', 'gender', 'date_of_birth', 'pincode', 'state', 'district', 'complete_address',
            'fcm_token', 'is_verified', 'verification_status', 'owner_reviewed_at', 'admin_reviewed_at',
            'rejection_reason', 'review_notes', 'is_online', 'current_latitude', 'current_longitude',
            'last_location_update', 'aadhaar_ocr_data', 'dl_ocr_data', 'face_match_score', 'created_at',
            'is_phone_verified'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'ambulance': {'required': False},
            'is_phone_verified': {'read_only': True},
        }

    def get_ambulance_details(self, obj):
        amb = getattr(obj, 'ambulance', None)
        if not amb and getattr(obj, 'ambulance_id', None):
            try:
                amb = Ambulance.objects.get(id=obj.ambulance_id)
            except Ambulance.DoesNotExist:
                return None
        if not amb:
            return None
        return {
            'id': amb.id,
            'vehicle_number': amb.vehicle_number,
            'registration_number': amb.registration_number,
            'ambulance_type': amb.ambulance_type,
            'status': amb.status,
            'is_available': amb.is_available,
            'is_active': amb.is_active,
            'is_approved': amb.is_approved,
            'approval_status': amb.approval_status,
        }

    def validate(self, attrs):
        phone = attrs.get('phone')
        if phone and Driver.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({
                'phone': 'A driver with this phone number is already registered. Please log in or use another number.'
            })

        license_number = attrs.get('license_number')
        if license_number and Driver.objects.filter(license_number=license_number).exists():
            raise serializers.ValidationError({
                'license_number': 'A driver with this licence number is already registered.'
            })

        ambulance_number = attrs.pop('ambulance_number', None)
        if ambulance_number:
            ambulance = Ambulance.objects.filter(vehicle_number=ambulance_number).first()
            if not ambulance:
                raise serializers.ValidationError({'ambulance_number': 'No ambulance was found with this vehicle number.'})
            if not getattr(ambulance, 'is_active', False):
                raise serializers.ValidationError({'ambulance_number': 'This ambulance is not active.'})
            attrs['ambulance'] = ambulance
        return attrs

    def create(self, validated_data):
        validated_data['verification_status'] = 'pending_owner_review'
        validated_data['is_verified'] = False
        return super().create(validated_data)
