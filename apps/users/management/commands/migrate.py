import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from django.conf import settings
from django.core.management.commands.migrate import Command as MigrateCommand
from django.core.management import call_command


def ensure_database_exists(db_alias, stdout=None):
    db_config = settings.DATABASES.get(db_alias)
    if not db_config or db_config.get('ENGINE') != 'django.db.backends.postgresql':
        return

    db_name = db_config.get('NAME')
    if not db_name:
        return

    user = db_config.get('USER', 'postgres')
    password = db_config.get('PASSWORD', '')
    host = db_config.get('HOST', 'localhost')
    port = db_config.get('PORT', '5432')

    # 1. Try connecting to target database directly
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=user,
            password=password,
            host=host,
            port=port,
            connect_timeout=3
        )
        conn.close()
        return  # Database already exists
    except psycopg2.OperationalError as e:
        err_msg = str(e)
        if f'database "{db_name}" does not exist' not in err_msg and 'FATAL:  database' not in err_msg:
            return  # Different connection error

    # 2. Try creating missing database by connecting to administrative database
    admin_dbs = ['postgres', 'template1', os.getenv('DB_NAME', 'blood_db')]
    for admin_db in admin_dbs:
        if admin_db == db_name:
            continue
        try:
            conn = psycopg2.connect(
                dbname=admin_db,
                user=user,
                password=password,
                host=host,
                port=port,
                connect_timeout=5
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            cursor.close()
            conn.close()
            msg = f"Successfully auto-created PostgreSQL database: '{db_name}'"
            if stdout:
                stdout.write(stdout.style.SUCCESS(msg))
            else:
                print(msg)
            break
        except Exception:
            continue


class Command(MigrateCommand):
    help = "Updates database schema. Automatically migrates both default (blood_db) and ambulance_db."

    def handle(self, *args, **options):
        specified_db = options.get('database')

        # Ensure all configured databases exist before running migrations
        for db_key in settings.DATABASES.keys():
            ensure_database_exists(db_key, stdout=self.stdout)

        # If caller explicitly specified a non-default database flag, follow that flag
        if specified_db and specified_db != 'default':
            super().handle(*args, **options)
            return

        # 1. Migrate default (blood_db)
        self.stdout.write(self.style.NOTICE("=== Migrating 'default' (blood_db) ==="))
        super().handle(*args, **options)

        # 2. Migrate ambulance_db
        self.stdout.write(self.style.NOTICE("=== Migrating 'ambulance_db' ==="))
        amb_options = options.copy()
        amb_options['database'] = 'ambulance_db'
        call_command('migrate', **amb_options)

