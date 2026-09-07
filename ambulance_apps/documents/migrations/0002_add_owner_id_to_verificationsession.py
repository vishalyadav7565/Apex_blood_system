from django.db import migrations
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "owner_id" bigint NULL;',
                    reverse_sql='ALTER TABLE "verification_session" DROP COLUMN IF EXISTS "owner_id";'
                ),
            ]
        ),
    ]
