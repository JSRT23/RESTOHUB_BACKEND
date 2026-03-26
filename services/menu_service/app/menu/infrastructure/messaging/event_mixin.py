# menu_service/app/menu/infrastructure/messaging/event_mixin.py
from app.menu.infrastructure.messaging.utils import publish_after_commit


class EventPublishingMixin:

    event_created = None
    event_updated = None

    def publish_created_event(self, instance):
        if self.event_created:
            publish_after_commit(
                self.event_created,
                self.build_event_data(instance)
            )

    def publish_updated_event(self, instance):
        if self.event_updated:
            publish_after_commit(
                self.event_updated,
                self.build_event_data(instance)
            )

    def build_event_data(self, instance):
        raise NotImplementedError
