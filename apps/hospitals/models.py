from django.db import models
from django.contrib.auth.hashers import (
    make_password,
    check_password

)


class Hospital(models.Model):

    name = models.CharField(
        max_length=100
    )

    email = models.EmailField(
        unique=True,
        blank=True,
        null=True
    )

    password = models.CharField(
        max_length=255
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    address = models.TextField(
        blank=True,
        null=True
    )

    latitude = models.FloatField(
        null=True,
        blank=True
    )

    longitude = models.FloatField(
        null=True,
        blank=True
    )

    is_verified = models.BooleanField(
        default=False
    )

    blood_units = models.IntegerField(
        default=0
    )

    blood_group = models.CharField(
        max_length=5,
        blank=True,
        null=True
    )

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
        blank=True,
        null=True
    )

    pincode = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    # =====================================
    # HASH PASSWORD
    # =====================================
    def save(self, *args, **kwargs):

        if (
            self.password and
            not self.password.startswith('pbkdf2_')
        ):
            self.password = make_password(
                self.password
            )

        super().save(*args, **kwargs)

    # =====================================
    # CHECK PASSWORD
    # =====================================
    def check_password(
        self,
        raw_password
    ):

        return check_password(
            raw_password,
            self.password
        )

    def __str__(self):

        return self.name
    
class BloodInventory(models.Model):

    BLOOD_GROUPS = [
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    ]

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="inventories"
    )

    blood_group = models.CharField(
        max_length=5,
        choices=BLOOD_GROUPS
    )

    units = models.IntegerField(
        default=0
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    class Meta:
        unique_together = (
            "hospital",
            "blood_group"
        )

    def __str__(self):
        return f"{self.hospital.name} - {self.blood_group}"