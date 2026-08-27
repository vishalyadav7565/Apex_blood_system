from rest_framework import serializers
from ambulance_apps.drivers.models import Driver
from ambulance_apps.ambulance.models import Ambulance


class DriverSerializer(serializers.ModelSerializer):
    ambulance_number = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Driver
        fields = [
            'id', 'name', 'phone', 'email', 'password', 'ambulance', 'ambulance_number', 'license_number',
            'license_expiry', 'aadhaar_number', 'aadhaar_card', 'driving_licence', 'photo', 'profile_photo',
            'father_name', 'gender', 'date_of_birth', 'pincode', 'state', 'district', 'complete_address',
            'fcm_token', 'is_verified', 'verification_status', 'owner_reviewed_at', 'admin_reviewed_at',
            'rejection_reason', 'review_notes', 'is_online', 'current_latitude', 'current_longitude',
            'last_location_update', 'aadhaar_ocr_data', 'dl_ocr_data', 'face_match_score', 'created_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'ambulance': {'required': False},
        }

    def validate(self, attrs):
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
