# gateway_service/app/gateway/graphql/schema.py
import graphene

from .services.menu.queries import MenuQuery
from .services.menu.mutations import MenuMutation
from .services.order.queries import OrderQuery
from .services.order.mutations import OrderMutation
from .services.inventory.queries import InventoryQuery
from .services.inventory.mutations import InventoryMutation
from .services.staff.queries import StaffQuery
from .services.staff.mutations import StaffMutation
from .services.loyalty.queries import LoyaltyQuery
from .services.loyalty.mutations import LoyaltyMutation


class Query(
    MenuQuery,
    OrderQuery,
    InventoryQuery,
    StaffQuery,
    LoyaltyQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    MenuMutation,
    OrderMutation,
    InventoryMutation,
    StaffMutation,
    LoyaltyMutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
