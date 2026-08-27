from django.db import models
from django.conf import settings


class Driver(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ("pending_owner_review", "Pending Owner Review"),
        ("approved_by_owner", "Approved By Owner"),
        ("rejected_by_owner", "Rejected By Owner"),
        ("pending_admin_review", "Pending Admin Review"),
        ("approved_by_admin", "Approved By Admin"),
        ("rejected_by_admin", "Rejected By Admin"),
    ]

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True)
    password = models.CharField(max_length=255)
    father_name = models.CharField(max_length=150, blank=True, null=True)
    gender = models.CharField(max_length=10, default="Male")
    date_of_birth = models.CharField(max_length=20, blank=True, null=True)
    pincode = models.CharField(max_length=6, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    complete_address = models.TextField(blank=True, null=True)

    # Reference to ambulance in ambulance app
    ambulance = models.OneToOneField(
        'ambulance.Ambulance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="driver"
    )

    license_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    license_expiry = models.DateField(blank=True, null=True)
    aadhaar_number = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # Documents upload files
    aadhaar_card = models.ImageField(upload_to="drivers/aadhaar/", blank=True, null=True)
    driving_licence = models.ImageField(upload_to="drivers/licence/", blank=True, null=True)
    photo = models.ImageField(upload_to="drivers/photos/", blank=True, null=True)  # Selfie
    profile_photo = models.ImageField(upload_to="drivers/profile/", blank=True, null=True)

    fcm_token = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=30,
        choices=VERIFICATION_STATUS_CHOICES,
        default="pending_owner_review"
    )

    # Verification logs
    owner_reviewed_at = models.DateTimeField(blank=True, null=True)
    admin_reviewed_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    review_notes = models.TextField(blank=True, null=True)

    # Telemetry
    is_online = models.BooleanField(default=False)
    current_latitude = models.FloatField(blank=True, null=True)
    current_longitude = models.FloatField(blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)

    # OCR results logs
    aadhaar_ocr_data = models.JSONField(blank=True, null=True)
    dl_ocr_data = models.JSONField(blank=True, null=True)
    face_match_score = models.FloatField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
