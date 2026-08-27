from rest_framework import serializers
from ambulance_apps.owners.models import Owner


class OwnerSerializer(serializers.ModelSerializer):
    is_approved = serializers.SerializerMethodField()

    class Meta:
        model = Owner
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'company_name',
            'address',
            'verification_status',
            'is_verified',
            'is_approved',
            'is_email_verified',
            'is_phone_verified',
            'is_aadhaar_verified',
            'is_business_doc_verified',
            'is_selfie_verified',
            'rejection_reason',
            'digilocker_token',
            'aadhaar_number',
            'aadhaar_card',
            'aadhaar_card_back',
            'business_doc',
            'selfie',
            'face_match_score',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'verification_status',
            'is_verified',
            'is_email_verified',
            'is_phone_verified',
            'is_aadhaar_verified',
            'face_match_score',
            'created_at',
            'updated_at',
        ]

    def get_is_approved(self, obj):
        return obj.verification_status == 'approved'



class OwnerRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = [
            'id',
            'name',
            'email',
            'password',
            'phone',
            'company_name',
            'address',
        ]
        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'email': {
                'validators': []
            },
            'phone': {
                'validators': []
            }
        }


class OwnerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    email_otp = serializers.CharField(max_length=6)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    mobile_otp = serializers.CharField(max_length=6, required=False, allow_blank=True)


class DigiLockerVerifySerializer(serializers.Serializer):
    owner_id = serializers.IntegerField()
    digilocker_code = serializers.CharField(max_length=255)


class SendEmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class VerifyEmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, required=True)
