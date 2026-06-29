from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# =========================================
# CUSTOM USER MODEL
# =========================================
class User(AbstractUser):

    # BASIC INFO
    phone = models.CharField(
        max_length=15,
        unique=True
    )

    blood_group = models.CharField(
        max_length=5,
        blank=True,
        null=True
    )

    # NEW PROFILE FIELDS
    first_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    age = models.IntegerField(
        blank=True,
        null=True
    )

    address = models.TextField(
        blank=True,
        null=True
    )

    # DONOR STATUS
    is_donor = models.BooleanField(
        default=False
    )

    is_available = models.BooleanField(
        default=False
    )

    # LOCATION
    latitude = models.FloatField(
        null=True,
        blank=True
    )

    longitude = models.FloatField(
        null=True,
        blank=True
    )

    # CREATED DATE
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True
    )

    fcm_token = models.TextField(
    null=True,
    blank=True
)

    pincode = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    def __str__(self):

        return f"{self.phone}"


# =========================================
# OTP MODEL
# =========================================
class OTP(models.Model):

    phone = models.CharField(
        max_length=15,
        db_index=True
    )

    otp = models.CharField(
        max_length=6
    )

    is_verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ['-created_at']

    # =====================================
    # OTP EXPIRY CHECK
    # =====================================
    def is_expired(self):

        return timezone.now() > (
            self.created_at + timedelta(minutes=5)
        )

    def __str__(self):

        return f"{self.phone} - {self.otp}"


# =========================================
# HELP & SUPPORT MODEL
# =========================================
class HelpSupport(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets"
    )

    name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    subject = models.CharField(
        max_length=250
    )

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.status}"