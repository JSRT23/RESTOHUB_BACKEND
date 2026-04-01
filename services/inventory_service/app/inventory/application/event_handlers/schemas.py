# inventory_service/app/inventory/application/event_handlers/schemas.py
"""
Validación de payloads entrantes.

Por qué: si menu_service o order_service mandan un campo con
nombre distinto o tipo incorrecto, el handler explota en runtime
con un KeyError o TypeError sin contexto. Los schemas atrapan
eso antes de tocar la base de datos.

Usamos dataclasses + validación manual (sin dependencias extra).
Si ya tienen Pydantic en el proyecto, reemplazar por BaseModel.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID


class SchemaError(ValueError):
    """Se lanza cuando el payload no cumple el schema esperado."""
    pass


def _require(data: dict, field: str) -> Any:
    val = data.get(field)
    if val is None:
        raise SchemaError(f"Campo requerido ausente: '{field}'")
    return val


def _uuid(data: dict, field: str) -> UUID:
    raw = _require(data, field)
    try:
        return UUID(str(raw))
    except (ValueError, AttributeError):
        raise SchemaError(f"'{field}' no es un UUID válido: {raw!r}")


def _decimal(data: dict, field: str) -> Decimal:
    raw = _require(data, field)
    try:
        return Decimal(str(raw))
    except Exception:
        raise SchemaError(f"'{field}' no es un número válido: {raw!r}")


# ─────────────────────────────────────────
# SCHEMAS — ORDER SERVICE
# ─────────────────────────────────────────

@dataclass
class DetallePedidoSchema:
    plato_id:  UUID
    cantidad:  int

    @classmethod
    def from_dict(cls, d: dict) -> "DetallePedidoSchema":
        plato_id = _uuid(d, "plato_id")
        cantidad = d.get("cantidad")
        if not isinstance(cantidad, (int, float)) or cantidad <= 0:
            raise SchemaError(
                f"'cantidad' debe ser > 0, recibido: {cantidad!r}")
        return cls(plato_id=plato_id, cantidad=int(cantidad))


@dataclass
class PedidoConfirmadoSchema:
    pedido_id:      UUID
    restaurante_id: UUID
    detalles:       list[DetallePedidoSchema]

    @classmethod
    def from_dict(cls, d: dict) -> "PedidoConfirmadoSchema":
        pedido_id = _uuid(d, "pedido_id")
        restaurante_id = _uuid(d, "restaurante_id")
        raw_detalles = _require(d, "detalles")

        if not isinstance(raw_detalles, list) or not raw_detalles:
            raise SchemaError("'detalles' debe ser una lista no vacía")

        detalles = [DetallePedidoSchema.from_dict(
            item) for item in raw_detalles]
        return cls(pedido_id=pedido_id, restaurante_id=restaurante_id, detalles=detalles)


# PedidoCanceladoSchema tiene el mismo shape
PedidoCanceladoSchema = PedidoConfirmadoSchema


# ─────────────────────────────────────────
# SCHEMAS — MENU SERVICE
# ─────────────────────────────────────────

@dataclass
class IngredienteSchema:
    ingrediente_id: UUID
    nombre:         str
    unidad_medida:  str

    @classmethod
    def from_dict(cls, d: dict) -> "IngredienteSchema":
        return cls(
            ingrediente_id=_uuid(d, "ingrediente_id"),
            nombre=str(_require(d, "nombre")),
            unidad_medida=str(_require(d, "unidad_medida")),
        )


@dataclass
class PlatoIngredienteSchema:
    plato_id:       UUID
    ingrediente_id: UUID
    cantidad:       Decimal
    unidad_medida:  str

    @classmethod
    def from_dict(cls, d: dict) -> "PlatoIngredienteSchema":
        return cls(
            plato_id=_uuid(d, "plato_id"),
            ingrediente_id=_uuid(d, "ingrediente_id"),
            cantidad=_decimal(d, "cantidad"),
            unidad_medida=str(_require(d, "unidad_medida")),
        )


@dataclass
class RestauranteCreadoSchema:
    restaurante_id: UUID
    nombre:         str
    pais:           str
    ciudad:         str

    @classmethod
    def from_dict(cls, d: dict) -> "RestauranteCreadoSchema":
        return cls(
            restaurante_id=_uuid(d, "restaurante_id"),
            nombre=str(_require(d, "nombre")),
            pais=str(_require(d, "pais")),
            ciudad=str(d.get("ciudad", "")),
        )
