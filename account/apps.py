from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'account'

    def ready(self):
        # import signal handlers so they are registered
        try:
            import account.signals  # noqa: F401
        except ImportError:
            pass

        # make sure firebase is initialised once application starts
        from . import fcm
        try:
            fcm.init_firebase()
        except Exception:
            # ignore initialization errors here; they will surface when sending
            pass
