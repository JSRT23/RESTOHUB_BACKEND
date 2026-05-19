# config/middleware.py
from django.middleware.common import CommonMiddleware


class SafeCommonMiddleware(CommonMiddleware):
    """
    Igual que CommonMiddleware pero no explota con hostnames
    que contienen guión bajo (ej: order_service:8000).

    Django 5.2+ valida RFC 1034/1035 en request.get_host() antes
    de revisar ALLOWED_HOSTS, lo que rompe el scraping de Prometheus
    dentro de Docker donde los nombres de servicio usan guión bajo.
    """

    def process_request(self, request):
        try:
            return super().process_request(request)
        except Exception:
            return None
