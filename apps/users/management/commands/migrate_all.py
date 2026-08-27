from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from apps.users.management.commands.migrate import ensure_database_exists


class Command(BaseCommand):
    help = "Run migrations on all configured databases (default/blood_db and ambulance_db)"

    def handle(self, *args, **options):
        for db_key in settings.DATABASES.keys():
            ensure_database_exists(db_key, stdout=self.stdout)

        self.stdout.write(self.style.NOTICE("Running migrations for 'default' (blood_db)..."))
        call_command('migrate', database='default')
        self.stdout.write(self.style.SUCCESS("Finished migrations for 'default'."))

        self.stdout.write(self.style.NOTICE("Running migrations for 'ambulance_db'..."))
        call_command('migrate', database='ambulance_db')
        self.stdout.write(self.style.SUCCESS("Finished migrations for 'ambulance_db'."))

