from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('trips', '0003_trip_driver_request_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='otp_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trip',
            name='pickup_otp_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trip',
            name='pickup_otp_hash',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
