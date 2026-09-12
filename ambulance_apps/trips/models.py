from django.db import models
from ambulance_apps.drivers.models import Driver

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
