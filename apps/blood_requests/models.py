from django.db import models
from django.conf import settings

from apps.hospitals.models import Hospital


class BloodRequest(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    # User Snapshot Data
    user_name = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    user_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    user_email = models.EmailField(
        blank=True,
        null=True
    )

    user_address = models.TextField(
        blank=True,
        null=True
    )

    blood_group = models.CharField(
        max_length=5
    )

    latitude = models.FloatField()

    longitude = models.FloatField()

    prescription = models.FileField(
        upload_to='prescriptions/',
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=30,
        default='pending'
    )

    assigned_to = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    expiry_time = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    accepted_hospital = models.ForeignKey(
    Hospital,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="accepted_requests"
)

    def __str__(self):
        return (
            f"{self.user_name} - "
            f"{self.blood_group} - "
            f"{self.status}"
        )