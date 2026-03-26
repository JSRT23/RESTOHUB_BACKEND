# staff_sercevice/app/staff/infrastructure/messaging/consumer_base.py
import json
import logging

logger = logging.getLogger(__name__)


class BaseConsumer:

    def process_message(self, body):
        try:
            message = json.loads(body)

            event_type = message.get("event_type")
            data = message.get("data", {})

            if not event_type:
                raise ValueError("event_type vacío")

            print(f"📥 EVENTO RECIBIDO → {event_type}")

            self.dispatch(event_type, data)

        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            raise

    def dispatch(self, event_type, data):
        raise NotImplementedError("Debes implementar dispatch()")
