from django.db import models
from apps.hospitals.models import Hospital
from ambulance_apps.owners.models import Owner


class Ambulance(models.Model):
    STATUS_CHOICES = [
        ("offline", "Offline"),
        ("online", "Online"),
        ("busy", "Busy"),
        ("maintenance", "Maintenance"),
    ]

    AMBULANCE_TYPES = [
        ("BLS", "BLS"),
        ("ALS", "ALS"),
        ("ICU", "ICU"),
        ("Neonatal", "Neonatal"),
        ("Patient Transport", "Patient Transport"),
    ]

    vehicle_number = models.CharField(
        max_length=50,
        unique=True
    )
    ambulance_type = models.CharField(
        max_length=30,
        choices=AMBULANCE_TYPES
    )
    registration_number = models.CharField(
        max_length=50,
        unique=True
    )
    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name="ambulances",
        db_constraint=False,
        null=True,
        blank=True
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="ambulances",
        db_constraint=False,
        null=True,
        blank=True
    )
    APPROVAL_STATUS_CHOICES = [
        ("pending_admin_review", "Pending Admin Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    approval_status = models.CharField(
        max_length=30,
        choices=APPROVAL_STATUS_CHOICES,
        default="pending_admin_review"
    )
    rejection_reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="offline"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ambulance"
        verbose_name_plural = "Ambulances"

    def __str__(self):
        return self.vehicle_number
