from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Owner(models.Model):
    STATUS_CHOICES = [
        ("pending_verification", "Pending Verification"),
        ("pending_admin_review", "Pending Admin Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=255)
    company_name = models.CharField(max_length=150, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Verification stats
    verification_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending_verification"
    )
    is_verified = models.BooleanField(default=False)  # Final approval flag from super admin
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_aadhaar_verified = models.BooleanField(default=False)
    is_business_doc_verified = models.BooleanField(default=False)
    is_selfie_verified = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # DigiLocker / Aadhaar / Uploaded Documents
    digilocker_token = models.CharField(max_length=255, blank=True, null=True)
    aadhaar_number = models.CharField(max_length=20, blank=True, null=True)
    aadhaar_card = models.ImageField(upload_to="owners/aadhaar/", blank=True, null=True)
    aadhaar_card_back = models.ImageField(upload_to="owners/aadhaar_back/", blank=True, null=True)
    business_doc = models.ImageField(upload_to="owners/business_docs/", blank=True, null=True)
    selfie = models.ImageField(upload_to="owners/selfies/", blank=True, null=True)
    
    face_match_score = models.FloatField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name


class EmailOTP(models.Model):
    email = models.EmailField(db_index=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > (self.created_at + timedelta(minutes=5))

    def __str__(self):
        return f"{self.email} - {self.otp}"
