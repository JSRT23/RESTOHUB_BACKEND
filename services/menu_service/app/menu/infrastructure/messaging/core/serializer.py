# menu_service/app/menu/infrastructure/messaging/core/serializer.py
# infrastructure/messaging/core/serializer.py

import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class SerializadorEventos:

    @staticmethod
    def serializar(evento: dict) -> str:
        return json.dumps(evento, default=SerializadorEventos._serializer)

    @staticmethod
    def deserializar(body: bytes) -> dict:
        return json.loads(body.decode("utf-8"))

    @staticmethod
    def _serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return str(obj)
