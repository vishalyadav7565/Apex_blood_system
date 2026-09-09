from django.db import migrations
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_add_owner_id_to_verificationsession'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql='''
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "token" character varying(128) NULL;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "token_hash" character varying(128) NULL;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "phone_connected" boolean NOT NULL DEFAULT False;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "aadhaar_front" text NULL;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "aadhaar_back" text NULL;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "selfie" text NULL;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "aadhaar_front_verified" boolean NOT NULL DEFAULT False;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "aadhaar_back_verified" boolean NOT NULL DEFAULT False;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "selfie_verified" boolean NOT NULL DEFAULT False;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "expires_at" timestamp with time zone NULL;
                    ALTER TABLE "verification_session" ADD COLUMN IF NOT EXISTS "completed_at" timestamp with time zone NULL;
                    
                    -- Backfill from legacy columns if present
                    DO $$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'verification_session' AND column_name = 'front_image') THEN
                            EXECUTE 'UPDATE "verification_session" SET "aadhaar_front" = "front_image" WHERE "aadhaar_front" IS NULL AND "front_image" IS NOT NULL';
                        END IF;
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'verification_session' AND column_name = 'back_image') THEN
                            EXECUTE 'UPDATE "verification_session" SET "aadhaar_back" = "back_image" WHERE "aadhaar_back" IS NULL AND "back_image" IS NOT NULL';
                        END IF;
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'verification_session' AND column_name = 'selfie_image') THEN
                            EXECUTE 'UPDATE "verification_session" SET "selfie" = "selfie_image" WHERE "selfie" IS NULL AND "selfie_image" IS NOT NULL';
                        END IF;
                    END $$;
                    ''',
                    reverse_sql='SELECT 1;'
                ),
            ]
        ),
    ]
