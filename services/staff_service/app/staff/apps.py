# staff_service/app/staff/apps.py
from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.staff"

    def ready(self):
        import app.staff.signals
