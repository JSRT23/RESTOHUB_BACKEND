# gateway_service/app/gateway/graphql/schema.py
import graphene

from .services.auth.queries import AuthQuery
from .services.auth.mutations import AuthMutation
from .services.menu.queries import MenuQuery
from .services.menu.mutations import MenuMutation
from .services.staff.queries import StaffQuery
from .services.staff.mutations import StaffMutation
from .services.order.queries import OrderQuery
from .services.order.mutations import OrderMutation
from .services.inventory.queries import InventoryQuery
from .services.inventory.mutations import InventoryMutation
from .services.loyalty.queries import LoyaltyQuery
from .services.loyalty.mutations import LoyaltyMutation


class Query(
    AuthQuery,
    MenuQuery,
    StaffQuery,
    OrderQuery,
    InventoryQuery,
    LoyaltyQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    AuthMutation,
    MenuMutation,
    StaffMutation,
    OrderMutation,
    InventoryMutation,
    LoyaltyMutation,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
