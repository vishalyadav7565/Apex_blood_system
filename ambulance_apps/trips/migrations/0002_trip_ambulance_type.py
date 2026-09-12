from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('trips', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='ambulance_type',
            field=models.CharField(
                choices=[
                    ('BLS', 'BLS'),
                    ('ALS', 'ALS'),
                    ('ICU', 'ICU'),
                    ('Neonatal', 'Neonatal'),
                    ('Patient Transport', 'Patient Transport'),
                ],
                default='BLS',
                max_length=30,
            ),
            preserve_default=False,
        ),
    ]
