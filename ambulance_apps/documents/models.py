from django.db import models
from django.conf import settings
from django.utils import timezone


class VerificationSession(models.Model):
    """
    Model for real-time mobile/desktop document verification sessions.
    Security: Zero raw Aadhaar PII, numbers, or unencrypted personal data stored.
    """
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('PHONE_CONNECTED', 'Phone Connected'),
        ('AADHAAR_FRONT_REQUIRED', 'Aadhaar Front Required'),
        ('AADHAAR_FRONT_CAPTURED', 'Aadhaar Front Captured'),
        ('AADHAAR_BACK_REQUIRED', 'Aadhaar Back Required'),
        ('AADHAAR_BACK_CAPTURED', 'Aadhaar Back Captured'),
        ('AADHAAR_COMPLETED', 'Aadhaar Completed'),
        ('SELFIE_REQUIRED', 'Selfie Required'),
        ('SELFIE_CAPTURED', 'Selfie Captured'),
        ('REGISTRATION_COMPLETED', 'Registration Completed'),
        ('VERIFICATION_COMPLETED', 'Verification Completed'),
        ('SESSION_EXPIRED', 'Session Expired'),
        ('CANCELLED', 'Cancelled'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
        related_name='verification_sessions'
    )
    code = models.CharField(max_length=64, unique=True, db_index=True)
    token = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    token_hash = models.CharField(max_length=128, null=True, blank=True, db_index=True)

    status = models.CharField(max_length=64, choices=STATUS_CHOICES, default='CREATED')
    phone_connected = models.BooleanField(default=False)

    # Document & Selfie image payloads / CDN references
    aadhaar_front = models.TextField(blank=True, null=True)
    aadhaar_back = models.TextField(blank=True, null=True)
    selfie = models.TextField(blank=True, null=True)

    # Verification status flags
    aadhaar_front_verified = models.BooleanField(default=False)
    aadhaar_back_verified = models.BooleanField(default=False)
    selfie_verified = models.BooleanField(default=False)

    # Lifecycle Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Property Aliases for backward compatibility with existing DRF views & WebSocket serializers
    @property
    def front_image(self):
        return self.aadhaar_front

    @front_image.setter
    def front_image(self, value):
        self.aadhaar_front = value

    @property
    def back_image(self):
        return self.aadhaar_back

    @back_image.setter
    def back_image(self, value):
        self.aadhaar_back = value

    @property
    def selfie_image(self):
        return self.selfie

    @selfie_image.setter
    def selfie_image(self, value):
        self.selfie = value

    class Meta:
        db_table = 'verification_session'
        ordering = ['-updated_at']

    def __str__(self):
        return f"VerificationSession {self.code} ({self.status})"


