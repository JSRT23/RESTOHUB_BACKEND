from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.inventory"

    def ready(self):
        import app.inventory.signals
