from rest_framework import serializers
from apps.hospitals.models import Hospital
from apps.hospitals.serializers import HospitalSerializer
from ambulance_apps.owners.models import Owner
from ambulance_apps.owners.serializers import OwnerSerializer
from ambulance_apps.ambulance.models import Ambulance


class AmbulanceSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=Owner.objects.all(),
        source='owner',
        write_only=True,
        required=False,
        allow_null=True
    )
    hospital = HospitalSerializer(read_only=True)
    hospital_id = serializers.PrimaryKeyRelatedField(
        queryset=Hospital.objects.all(),
        source='hospital',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Ambulance
        fields = [
            'id',
            'vehicle_number',
            'ambulance_type',
            'registration_number',
            'owner',
            'owner_id',
            'hospital',
            'hospital_id',
            'is_active',
            'is_available',
            'is_approved',
            'approval_status',
            'rejection_reason',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_approved', 'approval_status', 'created_at', 'updated_at']


class AmbulanceRegisterSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    hospital_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Ambulance
        fields = [
            'id',
            'vehicle_number',
            'ambulance_type',
            'registration_number',
            'owner_id',
            'hospital_id',
            'is_active',
            'is_available',
            'is_approved',
            'approval_status',
            'rejection_reason',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_approved', 'approval_status', 'rejection_reason', 'created_at', 'updated_at']

    def validate_vehicle_number(self, value):
        val = value.strip()
        if Ambulance.objects.filter(vehicle_number__iexact=val).exists():
            raise serializers.ValidationError("An ambulance with this vehicle number already exists.")
        return val

    def validate_registration_number(self, value):
        val = value.strip()
        if Ambulance.objects.filter(registration_number__iexact=val).exists():
            raise serializers.ValidationError("An ambulance with this registration number already exists.")
        return val

    def validate(self, attrs):
        owner_id = attrs.pop('owner_id', None)
        if owner_id is not None:
            try:
                attrs['owner'] = Owner.objects.get(id=owner_id)
            except Owner.DoesNotExist:
                raise serializers.ValidationError({'owner_id': f"Owner with ID {owner_id} does not exist."})

        hospital_id = attrs.pop('hospital_id', None)
        if hospital_id is not None:
            try:
                attrs['hospital'] = Hospital.objects.get(id=hospital_id)
            except Hospital.DoesNotExist:
                raise serializers.ValidationError({'hospital_id': f"Hospital with ID {hospital_id} does not exist."})
        return attrs

    def create(self, validated_data):
        validated_data['approval_status'] = 'pending_admin_review'
        validated_data['is_approved'] = False
        return Ambulance.objects.create(**validated_data)
