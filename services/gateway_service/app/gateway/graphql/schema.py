import graphene

from .services.menu.queries import MenuQuery
from .services.menu.mutations import MenuMutation
from .services.order.queries import OrderQuery
from .services.order.mutations import OrderMutation
from .services.inventory.queries import InventoryQuery
from .services.inventory.mutations import InventoryMutation


class Query(
    MenuQuery,
    OrderQuery,
    InventoryQuery,
    # StaffQuery,    ← agregar cuando esté listo
    # LoyaltyQuery,  ← agregar cuando esté listo
    graphene.ObjectType,
):
    pass


class Mutation(
    MenuMutation,
    OrderMutation,
    InventoryMutation,
    # StaffMutation,    ← agregar cuando esté listo
    # LoyaltyMutation,  ← agregar cuando esté listo
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
