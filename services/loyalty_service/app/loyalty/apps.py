from django.apps import AppConfig


class LoyaltyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.loyalty"

    def ready(self):
        import app.loyalty.signals
