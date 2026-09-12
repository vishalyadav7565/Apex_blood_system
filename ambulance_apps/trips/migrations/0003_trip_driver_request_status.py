from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('trips', '0002_trip_ambulance_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trip',
            name='rejected_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trip',
            name='rejection_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='trip',
            name='status',
            field=models.CharField(
                choices=[
                    ('requested', 'Requested'),
                    ('accepted', 'Accepted'),
                    ('started', 'Started'),
                    ('reached_pickup', 'Reached Pickup'),
                    ('picked_up', 'Picked Up'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('rejected', 'Rejected'),
                ],
                default='requested',
                max_length=30,
            ),
        ),
    ]
