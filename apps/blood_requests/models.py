from django.db import models
from django.conf import settings

from apps.hospitals.models import Hospital


class BloodRequest(models.Model):

    STATUS_CHOICES = [
        ('searching', 'Searching'),
        ('blood_bank_found', 'Blood Bank Found'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
        , related_name='blood_requests'
    )

    request_code = models.CharField(max_length=20, unique=True, blank=True, null=True)

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

    patient_phone = models.CharField(max_length=20, blank=True, null=True)
    units = models.PositiveIntegerField(default=1)
    reason = models.TextField(blank=True, null=True)

    latitude = models.FloatField()

    longitude = models.FloatField()

    prescription = models.FileField(
        upload_to='prescriptions/',
        max_length=500,
        null=True,
        blank=True
    )

    prescription_image = models.FileField(upload_to='prescriptions/', max_length=500, null=True, blank=True)

    patient_name = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    blood_component = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    blood_units = models.IntegerField(
        default=1
    )

    status = models.CharField(
        max_length=30,
        default='pending'
    )

    otp = models.CharField(
        max_length=6,
        blank=True,
        null=True
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

    def save(self, *args, **kwargs):
        if not self.request_code:
            next_id = (type(self).objects.order_by('-id').values_list('id', flat=True).first() or 0) + 1
            self.request_code = f'#BR-{10000 + next_id}'
        if not self.patient_phone:
            self.patient_phone = self.user_phone or getattr(self.user, 'phone', None)
        if self.units == 1 and self.blood_units:
            self.units = self.blood_units
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.user_name} - "
            f"{self.blood_group} - "
            f"{self.status}"
        )