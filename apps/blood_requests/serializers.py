from rest_framework import serializers
from .models import BloodRequest


class BloodRequestSerializer(
    serializers.ModelSerializer
):

    patient_name = serializers.CharField(
        source='user_name',
        read_only=True
    )

    patient_phone = serializers.CharField(
        source='user_phone',
        read_only=True
    )

    patient_email = serializers.CharField(
        source='user_email',
        read_only=True
    )

    patient_address = serializers.CharField(
        source='user_address',
        read_only=True
    )

    document_url = serializers.SerializerMethodField()
    hospital_name = serializers.CharField(source='accepted_hospital.name', read_only=True, default=None)
    hospital_phone = serializers.CharField(source='accepted_hospital.phone', read_only=True, default=None)
    hospital_email = serializers.CharField(source='accepted_hospital.email', read_only=True, default=None)
    hospital_address = serializers.CharField(source='accepted_hospital.address', read_only=True, default=None)
    hospital_latitude = serializers.FloatField(source='accepted_hospital.latitude', read_only=True, default=None)
    hospital_longitude = serializers.FloatField(source='accepted_hospital.longitude', read_only=True, default=None)
    hospital_pincode = serializers.CharField(source='accepted_hospital.pincode', read_only=True, default=None)

    class Meta:

        model = BloodRequest

        fields = [

            "id",

            "user",

            "patient_name",

            "patient_phone",

            "patient_email",

            "patient_address",

            "blood_group",

            "latitude",

            "longitude",

            "prescription",

            "document_url",

            "status",

            "assigned_to",

            "expiry_time",

            "created_at",

            "accepted_hospital",

            "hospital_name",

            "hospital_phone",

            "hospital_email",

            "hospital_address",

            "hospital_latitude",

            "hospital_longitude",

            "hospital_pincode",
        ]

    def get_document_url(self, obj):

        request = self.context.get(
            'request'
        )

        if obj.prescription:

            if request:

                return request.build_absolute_uri(
                    obj.prescription.url
                )

            return obj.prescription.url

        return None