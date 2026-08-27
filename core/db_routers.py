class DatabaseRouter:
    """
    A router to control all database operations on models in the
    ambulance applications versus blood bank / primary auth applications.
    """

    AMBULANCE_APPS = {
        'owners',
        'ambulance',
        'drivers',
        'trips',
        'tracking',
        'notifications',
        'documents',
        'payments',
        'analytics',
        'support',
    }

    def db_for_read(self, model, **hints):
        """
        Attempts to read ambulance models go to ambulance_db.
        """
        if model._meta.app_label in self.AMBULANCE_APPS:
            return 'ambulance_db'
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Attempts to write ambulance models go to ambulance_db.
        """
        if model._meta.app_label in self.AMBULANCE_APPS:
            return 'ambulance_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in ambulance_apps is involved with another
        model in ambulance_apps, or cross-app references where allowed.
        """
        if (
            obj1._meta.app_label in self.AMBULANCE_APPS and
            obj2._meta.app_label in self.AMBULANCE_APPS
        ):
            return True
        elif (
            obj1._meta.app_label not in self.AMBULANCE_APPS and
            obj2._meta.app_label not in self.AMBULANCE_APPS
        ):
            return True
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the ambulance apps only appear in the 'ambulance_db'
        database, and all other apps appear in 'default' (blood_db).
        """
        if app_label in self.AMBULANCE_APPS:
            return db == 'ambulance_db'
        return db == 'default'
