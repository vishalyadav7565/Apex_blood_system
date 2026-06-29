from rest_framework import serializers

from .models import Hospital
from .models import BloodInventory


# ==========================================
# HOSPITAL SERIALIZER
# ==========================================
class HospitalSerializer(
    serializers.ModelSerializer
):

    distance = serializers.SerializerMethodField()

    class Meta:

        model = Hospital

        fields = [

            'id',

            'name',

            'email',

            'phone',

            'address',

            'pincode',

            'latitude',

            'longitude',

            'is_verified',

            'created_at',

            'updated_at',

            'distance',
        ]

    def get_distance(self, obj):

        user_lat = self.context.get(
            'user_lat'
        )

        user_lng = self.context.get(
            'user_lng'
        )

        if (
            user_lat is None or
            user_lng is None or
            obj.latitude is None or
            obj.longitude is None
        ):
            return None

        from math import (
            radians,
            cos,
            sin,
            asin,
            sqrt
        )

        dlon = radians(
            obj.longitude - user_lng
        )

        dlat = radians(
            obj.latitude - user_lat
        )

        a = (
            sin(dlat / 2) ** 2
            +
            cos(radians(user_lat))
            *
            cos(radians(obj.latitude))
            *
            sin(dlon / 2) ** 2
        )

        c = 2 * asin(sqrt(a))

        return round(
            6371 * c,
            2
        )


# ==========================================
# HOSPITAL PROFILE SERIALIZER
# ==========================================
class HospitalProfileSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = Hospital

        fields = [

            'id',

            'name',

            'email',

            'phone',

            'address',

            'pincode',

            'latitude',

            'longitude',

            'is_verified',

            'created_at',

            'updated_at',
        ]

        read_only_fields = [

            'id',

            'is_verified',

            'created_at',

            'updated_at',
        ]


# ==========================================
# REGISTER SERIALIZER
# ==========================================
class HospitalRegisterSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = Hospital

        fields = [

            'id',

            'name',

            'email',

            'password',

            'phone',

            'address',

            'pincode',

            'latitude',

            'longitude',
        ]

        extra_kwargs = {

            'password': {
                'write_only': True
            }
        }


# ==========================================
# LOGIN SERIALIZER
# ==========================================
class HospitalLoginSerializer(
    serializers.Serializer
):

    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True
    )


# ==========================================
# BLOOD INVENTORY SERIALIZER
# ==========================================
class BloodInventorySerializer(
    serializers.ModelSerializer
):

    hospital_name = serializers.CharField(
        source='hospital.name',
        read_only=True
    )

    class Meta:

        model = BloodInventory

        fields = [

            'id',

            'hospital',

            'hospital_name',

            'blood_group',

            'units',

            'updated_at',
        ]