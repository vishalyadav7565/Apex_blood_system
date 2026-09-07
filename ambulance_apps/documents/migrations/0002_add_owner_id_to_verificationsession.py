from django.db import migrations

def add_owner_id_column(apps, schema_editor):
    table_name = 'verification_session'
    with schema_editor.connection.cursor() as cursor:
        if schema_editor.connection.vendor == 'postgresql':
            cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "owner_id" bigint NULL;')
        elif schema_editor.connection.vendor == 'sqlite':
            # Check if column exists for SQLite
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            columns = [column[1] for column in cursor.fetchall()]
            if 'owner_id' not in columns:
                cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "owner_id" integer NULL;')

class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_owner_id_column, reverse_code=migrations.RunPython.noop),
    ]
