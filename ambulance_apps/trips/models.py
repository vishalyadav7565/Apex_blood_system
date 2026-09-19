from django.db import models
from ambulance_apps.drivers.models import Driver
from django.conf import settings

class Trip(models.Model):
    AMBULANCE_TYPES = [
        ('BLS', 'BLS'),
        ('ALS', 'ALS'),
        ('ICU', 'ICU'),
        ('Neonatal', 'Neonatal'),
        ('Patient Transport', 'Patient Transport'),
    ]

    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('started', 'Started'),
        ('reached_pickup', 'Reached Pickup'),
        ('picked_up', 'Picked Up'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='trips')
    ambulance_type = models.CharField(max_length=30, choices=AMBULANCE_TYPES)
    patient_name = models.CharField(max_length=150, default="Emergency Patient")
    patient_phone = models.CharField(max_length=15, blank=True, null=True)
    pickup_address = models.TextField(default="Pickup Address")
    destination_address = models.TextField(default="Hospital Address")
    
    pickup_latitude = models.FloatField(blank=True, null=True)
    pickup_longitude = models.FloatField(blank=True, null=True)
    destination_latitude = models.FloatField(blank=True, null=True)
    destination_longitude = models.FloatField(blank=True, null=True)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='requested')
    accepted_at = models.DateTimeField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    pickup_otp_hash = models.CharField(max_length=255, blank=True, null=True)
    pickup_otp_expires_at = models.DateTimeField(blank=True, null=True)
    otp_verified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trip {self.id} for {self.patient_name} - Status: {self.status}"


class AmbulanceRequest(models.Model):
    STATUS_CHOICES = [
        ('searching', 'Searching'),
        ('driver_assigned', 'Driver Assigned'),
        ('en_route', 'En Route'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    request_code = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ambulance_requests',
        db_constraint=False,
    )
    patient_name = models.CharField(max_length=150)
    patient_phone = models.CharField(max_length=20)
    emergency_type = models.CharField(max_length=100, default='Medical Emergency')
    pickup_address = models.TextField()
    pickup_latitude = models.FloatField(blank=True, null=True)
    pickup_longitude = models.FloatField(blank=True, null=True)
    destination_address = models.TextField(blank=True, null=True)
    hospital_name = models.CharField(max_length=200, blank=True, null=True)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='ambulance_requests')
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='searching')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.request_code:
            next_id = (type(self).objects.using('ambulance_db').order_by('-id').values_list('id', flat=True).first() or 0) + 1
            self.request_code = f'#AR-{20000 + next_id}'
        super().save(*args, **kwargs)
