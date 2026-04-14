# gateway_service/app/gateway/graphql/services/inventory/mutations.py
import graphene
from .types import (
    ProveedorType, AlmacenType, StockType,
    LoteType, OrdenCompraType, AlertaStockType,
)
from ....client import inventory_client
from ....middleware.permissions import get_jwt_user


class DetalleOrdenInput(graphene.InputObjectType):
    ingrediente_id = graphene.ID(required=True)
    nombre_ingrediente = graphene.String(required=True)
    unidad_medida = graphene.String(required=True)
    cantidad = graphene.Float(required=True)
    precio_unitario = graphene.Float(required=True)


class DetalleRecepcionInput(graphene.InputObjectType):
    detalle_id = graphene.ID(required=True)
    cantidad_recibida = graphene.Float(required=True)
    numero_lote = graphene.String(required=True)
    fecha_vencimiento = graphene.String(required=True)
    fecha_produccion = graphene.String()


# ─────────────────────────────────────────
# PROVEEDOR
# ─────────────────────────────────────────

class CrearProveedor(graphene.Mutation):
    """
    Reglas de negocio (Opción B):

    admin_central puede crear proveedores con cualquier alcance:
      - alcance=GLOBAL  → visible para toda la cadena
      - alcance=PAIS    → requiere pais_destino
      - alcance=CIUDAD  → requiere ciudad_destino (y pais_destino)
      - alcance=LOCAL   → requiere restaurante_id destino

    gerente_local solo puede crear alcance=LOCAL para su propio restaurante.
      - No puede pasar alcance, pais_destino ni ciudad_destino.
      - creado_por_restaurante_id se inyecta automáticamente desde el JWT.
    """
    class Arguments:
        nombre = graphene.String(required=True)
        pais = graphene.String(required=True)
        ciudad = graphene.String()
        telefono = graphene.String()
        email = graphene.String()
        moneda_preferida = graphene.String()
        # Opción B — solo admin_central puede pasar estos campos
        alcance = graphene.String(
            description="GLOBAL | PAIS | CIUDAD | LOCAL. Solo admin_central puede asignar GLOBAL/PAIS/CIUDAD."
        )
        pais_destino = graphene.String(
            description="Requerido si alcance=PAIS o alcance=CIUDAD. Solo admin_central."
        )
        ciudad_destino = graphene.String(
            description="Requerido si alcance=CIUDAD. Solo admin_central."
        )
        restaurante_id_destino = graphene.ID(
            description="Restaurante destino para alcance=LOCAL. Solo admin_central puede asignarlo a otro restaurante."
        )

    ok = graphene.Boolean()
    proveedor = graphene.Field(ProveedorType)
    error = graphene.String()

    def mutate(self, info, nombre, pais, alcance=None, pais_destino=None,
               ciudad_destino=None, restaurante_id_destino=None, **kwargs):
        user = get_jwt_user(info)
        if not user:
            return CrearProveedor(ok=False, error="Debes iniciar sesión.")

        rol = user.get("rol")

        if rol == "admin_central":
            # Admin puede crear con cualquier alcance
            alcance_final = alcance or "GLOBAL"

            if alcance_final == "PAIS" and not pais_destino:
                return CrearProveedor(ok=False, error="alcance=PAIS requiere pais_destino.")
            if alcance_final == "CIUDAD" and (not ciudad_destino or not pais_destino):
                return CrearProveedor(ok=False, error="alcance=CIUDAD requiere ciudad_destino y pais_destino.")

            data = inventory_client.crear_proveedor({
                "nombre": nombre,
                "pais": pais,
                "alcance": alcance_final,
                "pais_destino": pais_destino,
                "ciudad_destino": ciudad_destino,
                "creado_por_restaurante_id": restaurante_id_destino,
                **kwargs,
            })

        elif rol == "gerente_local":
            # Gerente solo puede crear LOCAL para su propio restaurante
            restaurante_id = user.get("restaurante_id")
            if not restaurante_id:
                return CrearProveedor(ok=False, error="Tu cuenta no tiene restaurante asignado.")

            data = inventory_client.crear_proveedor({
                "nombre": nombre,
                "pais": pais,
                "alcance": "LOCAL",
                "creado_por_restaurante_id": restaurante_id,
                **kwargs,
            })

        else:
            return CrearProveedor(ok=False, error="No tienes permiso para crear proveedores.")

        if not data:
            return CrearProveedor(ok=False, error="Error al crear proveedor.")
        return CrearProveedor(ok=True, proveedor=data)


class ActualizarProveedor(graphene.Mutation):
    """
    admin_central puede editar cualquier proveedor.
    gerente_local solo puede editar proveedores LOCAL de su restaurante.
    """
    class Arguments:
        id = graphene.ID(required=True)
        nombre = graphene.String()
        pais = graphene.String()
        ciudad = graphene.String()
        telefono = graphene.String()
        email = graphene.String()
        moneda_preferida = graphene.String()
        activo = graphene.Boolean()
        # Solo admin_central puede cambiar alcance/destino
        alcance = graphene.String()
        pais_destino = graphene.String()
        ciudad_destino = graphene.String()

    ok = graphene.Boolean()
    proveedor = graphene.Field(ProveedorType)
    error = graphene.String()

    def mutate(self, info, id, alcance=None, pais_destino=None,
               ciudad_destino=None, **kwargs):
        user = get_jwt_user(info)
        if not user:
            return ActualizarProveedor(ok=False, error="Debes iniciar sesión.")

        rol = user.get("rol")

        if rol == "admin_central":
            payload = {k: v for k, v in kwargs.items() if v is not None}
            if alcance:
                payload["alcance"] = alcance
            if pais_destino:
                payload["pais_destino"] = pais_destino
            if ciudad_destino:
                payload["ciudad_destino"] = ciudad_destino

        elif rol == "gerente_local":
            # Gerente no puede cambiar alcance ni destino
            if alcance or pais_destino or ciudad_destino:
                return ActualizarProveedor(
                    ok=False,
                    error="No puedes cambiar el alcance de un proveedor."
                )
            payload = {k: v for k, v in kwargs.items() if v is not None}

        else:
            return ActualizarProveedor(ok=False, error="No tienes permiso para editar proveedores.")

        data = inventory_client.actualizar_proveedor(id, payload)
        if not data:
            return ActualizarProveedor(ok=False, error="Error al actualizar proveedor.")
        return ActualizarProveedor(ok=True, proveedor=data)


# ─────────────────────────────────────────
# ALMACÉN
# ─────────────────────────────────────────

class CrearAlmacen(graphene.Mutation):
    """Solo gerente_local puede crear almacenes (de su restaurante)."""
    class Arguments:
        restaurante_id = graphene.ID(required=True)
        nombre = graphene.String(required=True)
        descripcion = graphene.String()

    ok = graphene.Boolean()
    almacen = graphene.Field(AlmacenType)
    error = graphene.String()

    def mutate(self, info, restaurante_id, nombre, descripcion=None):
        user = get_jwt_user(info)
        if not user:
            return CrearAlmacen(ok=False, error="Debes iniciar sesión.")

        rol = user.get("rol")
        if rol not in ("admin_central", "gerente_local"):
            return CrearAlmacen(ok=False, error="No tienes permiso para crear almacenes.")

        # Gerente solo puede crear en su restaurante
        if rol == "gerente_local":
            restaurante_id = user.get("restaurante_id")

        data = inventory_client.crear_almacen({
            "restaurante_id": restaurante_id,
            "nombre":         nombre,
            "descripcion":    descripcion,
        })
        if not data:
            return CrearAlmacen(ok=False, error="Error al crear almacén.")
        return CrearAlmacen(ok=True, almacen=data)


# ─────────────────────────────────────────
# STOCK
# ─────────────────────────────────────────

class RegistrarStock(graphene.Mutation):
    """Registra un ingrediente en el inventario. Solo gerente_local."""
    class Arguments:
        ingrediente_id = graphene.ID(required=True)
        nombre_ingrediente = graphene.String(required=True)
        almacen_id = graphene.ID(required=True)
        unidad_medida = graphene.String(required=True)
        cantidad_actual = graphene.Float(required=True)
        nivel_minimo = graphene.Float(required=True)
        nivel_maximo = graphene.Float(required=True)

    ok = graphene.Boolean()
    stock = graphene.Field(StockType)
    error = graphene.String()

    def mutate(self, info, ingrediente_id, nombre_ingrediente, almacen_id,
               unidad_medida, cantidad_actual, nivel_minimo, nivel_maximo):
        user = get_jwt_user(info)
        if not user or user.get("rol") not in ("admin_central", "gerente_local"):
            return RegistrarStock(ok=False, error="No tienes permiso para registrar stock.")

        data = inventory_client.crear_stock({
            "ingrediente_id":     ingrediente_id,
            "nombre_ingrediente": nombre_ingrediente,
            "almacen":            almacen_id,
            "unidad_medida":      unidad_medida,
            "cantidad_actual":    str(cantidad_actual),
            "nivel_minimo":       str(nivel_minimo),
            "nivel_maximo":       str(nivel_maximo),
        })
        if not data:
            return RegistrarStock(ok=False, error="Error al registrar stock.")
        return RegistrarStock(ok=True, stock=data)


class AjustarStock(graphene.Mutation):
    """Ajuste manual de stock. Solo gerente_local."""
    class Arguments:
        id = graphene.ID(required=True)
        cantidad = graphene.Float(required=True)
        descripcion = graphene.String(required=True)

    ok = graphene.Boolean()
    stock = graphene.Field(StockType)
    error = graphene.String()

    def mutate(self, info, id, cantidad, descripcion):
        user = get_jwt_user(info)
        if not user or user.get("rol") not in ("admin_central", "gerente_local"):
            return AjustarStock(ok=False, error="No tienes permiso para ajustar stock.")

        data = inventory_client.ajustar_stock(id, cantidad, descripcion)
        if not data:
            return AjustarStock(ok=False, error="Error al ajustar stock.")
        return AjustarStock(ok=True, stock=data)


# ─────────────────────────────────────────
# LOTES
# ─────────────────────────────────────────

class RegistrarLote(graphene.Mutation):
    """Solo gerente_local puede registrar lotes."""
    class Arguments:
        ingrediente_id = graphene.ID(required=True)
        almacen_id = graphene.ID(required=True)
        proveedor_id = graphene.ID(required=True)
        numero_lote = graphene.String(required=True)
        fecha_vencimiento = graphene.String(required=True)
        cantidad_recibida = graphene.Float(required=True)
        unidad_medida = graphene.String(required=True)
        fecha_produccion = graphene.String()

    ok = graphene.Boolean()
    lote = graphene.Field(LoteType)
    error = graphene.String()

    def mutate(self, info, ingrediente_id, almacen_id, proveedor_id,
               numero_lote, fecha_vencimiento, cantidad_recibida,
               unidad_medida, fecha_produccion=None):
        user = get_jwt_user(info)
        if not user or user.get("rol") not in ("admin_central", "gerente_local"):
            return RegistrarLote(ok=False, error="No tienes permiso para registrar lotes.")

        data = inventory_client.crear_lote({
            "ingrediente_id":    ingrediente_id,
            "almacen":           almacen_id,
            "proveedor":         proveedor_id,
            "numero_lote":       numero_lote,
            "fecha_vencimiento": fecha_vencimiento,
            "fecha_produccion":  fecha_produccion,
            "cantidad_recibida": str(cantidad_recibida),
            "unidad_medida":     unidad_medida,
        })
        if not data:
            return RegistrarLote(ok=False, error="Error al registrar lote.")
        return RegistrarLote(ok=True, lote=data)


class RetirarLote(graphene.Mutation):
    """Solo gerente_local puede retirar lotes."""
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    lote = graphene.Field(LoteType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user or user.get("rol") not in ("admin_central", "gerente_local"):
            return RetirarLote(ok=False, error="No tienes permiso para retirar lotes.")

        data = inventory_client.retirar_lote(id)
        if not data:
            return RetirarLote(ok=False, error="Error al retirar lote.")
        return RetirarLote(ok=True, lote=data)


# ─────────────────────────────────────────
# ÓRDENES DE COMPRA
# ─────────────────────────────────────────

class CrearOrdenCompra(graphene.Mutation):
    """
    Solo gerente_local puede crear órdenes de compra.
    restaurante_id se inyecta desde el JWT — el frontend no lo pasa.
    """
    class Arguments:
        proveedor_id = graphene.ID(required=True)
        moneda = graphene.String(required=True)
        detalles = graphene.List(graphene.NonNull(
            DetalleOrdenInput), required=True)
        fecha_entrega_estimada = graphene.String()
        notas = graphene.String()

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, proveedor_id, moneda, detalles, **kwargs):
        user = get_jwt_user(info)
        if not user:
            return CrearOrdenCompra(ok=False, error="Debes iniciar sesión.")

        rol = user.get("rol")
        if rol not in ("admin_central", "gerente_local"):
            return CrearOrdenCompra(ok=False, error="No tienes permiso para crear órdenes de compra.")

        # Gerente: restaurante_id desde JWT. Admin: puede pasar cualquiera (futuro).
        restaurante_id = user.get("restaurante_id")
        if rol == "gerente_local" and not restaurante_id:
            return CrearOrdenCompra(ok=False, error="Tu cuenta no tiene restaurante asignado.")

        data = inventory_client.crear_orden_compra({
            "proveedor":      proveedor_id,
            "restaurante_id": restaurante_id,
            "moneda":         moneda,
            "detalles":       [dict(d) for d in detalles],
            **kwargs,
        })
        if not data:
            return CrearOrdenCompra(ok=False, error="Error al crear orden de compra.")
        return CrearOrdenCompra(ok=True, orden=data)


class EnviarOrdenCompra(graphene.Mutation):
    """Cambia estado BORRADOR → ENVIADA. Solo gerente_local."""
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user or user.get("rol") not in ("admin_central", "gerente_local"):
            return EnviarOrdenCompra(ok=False, error="No tienes permiso.")

        data = inventory_client.enviar_orden_compra(id)
        if not data:
            return EnviarOrdenCompra(ok=False, error="Error al enviar orden.")
        return EnviarOrdenCompra(ok=True, orden=data)


class RecibirOrdenCompra(graphene.Mutation):
    """
    Recibe la orden: crea lotes, actualiza stock y costos de receta.
    Solo gerente_local del restaurante propietario de la orden.
    """
    class Arguments:
        id = graphene.ID(required=True)
        detalles = graphene.List(graphene.NonNull(
            DetalleRecepcionInput), required=True)
        notas = graphene.String()

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id, detalles, notas=""):
        user = get_jwt_user(info)
        if not user or user.get("rol") not in ("admin_central", "gerente_local"):
            return RecibirOrdenCompra(ok=False, error="No tienes permiso.")

        data = inventory_client.recibir_orden_compra(id, {
            "detalles": [dict(d) for d in detalles],
            "notas":    notas,
        })
        if not data:
            return RecibirOrdenCompra(ok=False, error="Error al recibir orden.")
        return RecibirOrdenCompra(ok=True, orden=data)


class CancelarOrdenCompra(graphene.Mutation):
    """Solo gerente_local puede cancelar órdenes."""
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user or user.get("rol") not in ("admin_central", "gerente_local"):
            return CancelarOrdenCompra(ok=False, error="No tienes permiso.")

        data = inventory_client.cancelar_orden_compra(id)
        if not data:
            return CancelarOrdenCompra(ok=False, error="Error al cancelar orden.")
        return CancelarOrdenCompra(ok=True, orden=data)


# ─────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────

class ResolverAlerta(graphene.Mutation):
    """
    Gerente y supervisor pueden resolver alertas de su restaurante.
    """
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    alerta = graphene.Field(AlertaStockType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user:
            return ResolverAlerta(ok=False, error="Debes iniciar sesión.")

        rol = user.get("rol")
        if rol not in ("admin_central", "gerente_local", "supervisor"):
            return ResolverAlerta(ok=False, error="No tienes permiso para resolver alertas.")

        data = inventory_client.resolver_alerta(id)
        if not data:
            return ResolverAlerta(ok=False, error="Error al resolver alerta.")
        return ResolverAlerta(ok=True, alerta=data)


class IgnorarAlerta(graphene.Mutation):
    """
    Solo gerente_local puede ignorar alertas (decisión de negocio).
    El supervisor solo resuelve, no ignora.
    """
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    alerta = graphene.Field(AlertaStockType)
    error = graphene.String()

    def mutate(self, info, id):
        user = get_jwt_user(info)
        if not user:
            return IgnorarAlerta(ok=False, error="Debes iniciar sesión.")

        rol = user.get("rol")
        if rol not in ("admin_central", "gerente_local"):
            return IgnorarAlerta(ok=False, error="Solo el gerente puede ignorar alertas.")

        data = inventory_client.ignorar_alerta(id)
        if not data:
            return IgnorarAlerta(ok=False, error="Error al ignorar alerta.")
        return IgnorarAlerta(ok=True, alerta=data)


# ─────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────

class InventoryMutation(graphene.ObjectType):
    crear_proveedor = CrearProveedor.Field()
    actualizar_proveedor = ActualizarProveedor.Field()
    crear_almacen = CrearAlmacen.Field()
    registrar_stock = RegistrarStock.Field()
    ajustar_stock = AjustarStock.Field()
    registrar_lote = RegistrarLote.Field()
    retirar_lote = RetirarLote.Field()
    crear_orden_compra = CrearOrdenCompra.Field()
    enviar_orden_compra = EnviarOrdenCompra.Field()
    recibir_orden_compra = RecibirOrdenCompra.Field()
    cancelar_orden_compra = CancelarOrdenCompra.Field()
    resolver_alerta = ResolverAlerta.Field()
    ignorar_alerta = IgnorarAlerta.Field()

    ingrediente_id = graphene.ID(required=True)
    nombre_ingrediente = graphene.String(required=True)
    unidad_medida = graphene.String(required=True)
    cantidad = graphene.Float(required=True)
    precio_unitario = graphene.Float(required=True)


class DetalleRecepcionInput(graphene.InputObjectType):
    detalle_id = graphene.ID(required=True)
    cantidad_recibida = graphene.Float(required=True)
    numero_lote = graphene.String(required=True)
    fecha_vencimiento = graphene.String(required=True)
    fecha_produccion = graphene.String()


# ─────────────────────────────────────────
# PROVEEDOR
# ─────────────────────────────────────────

class CrearProveedor(graphene.Mutation):
    class Arguments:
        nombre = graphene.String(required=True)
        pais = graphene.String(required=True)
        ciudad = graphene.String()
        telefono = graphene.String()
        email = graphene.String()
        moneda_preferida = graphene.String()

    ok = graphene.Boolean()
    proveedor = graphene.Field(ProveedorType)
    error = graphene.String()

    def mutate(self, info, nombre, pais, **kwargs):
        data = inventory_client.crear_proveedor(
            {"nombre": nombre, "pais": pais, **kwargs}
        )
        if not data:
            return CrearProveedor(ok=False, error="Error al crear proveedor.")
        return CrearProveedor(ok=True, proveedor=data)


# ─────────────────────────────────────────
# ALMACÉN
# ─────────────────────────────────────────

class CrearAlmacen(graphene.Mutation):
    class Arguments:
        restaurante_id = graphene.ID(required=True)
        nombre = graphene.String(required=True)
        descripcion = graphene.String()

    ok = graphene.Boolean()
    almacen = graphene.Field(AlmacenType)
    error = graphene.String()

    def mutate(self, info, restaurante_id, nombre, descripcion=None):
        data = inventory_client.crear_almacen({
            "restaurante_id": restaurante_id,
            "nombre":         nombre,
            "descripcion":    descripcion,
        })
        if not data:
            return CrearAlmacen(ok=False, error="Error al crear almacén.")
        return CrearAlmacen(ok=True, almacen=data)


# ─────────────────────────────────────────
# STOCK
# ─────────────────────────────────────────

class RegistrarStock(graphene.Mutation):
    """Registra un ingrediente en el inventario de un almacén."""
    class Arguments:
        ingrediente_id = graphene.ID(required=True)
        nombre_ingrediente = graphene.String(required=True)
        almacen_id = graphene.ID(required=True)
        unidad_medida = graphene.String(required=True)
        cantidad_actual = graphene.Float(required=True)
        nivel_minimo = graphene.Float(required=True)
        nivel_maximo = graphene.Float(required=True)

    ok = graphene.Boolean()
    stock = graphene.Field(StockType)
    error = graphene.String()

    def mutate(self, info, ingrediente_id, nombre_ingrediente, almacen_id,
               unidad_medida, cantidad_actual, nivel_minimo, nivel_maximo):
        data = inventory_client.crear_stock({
            "ingrediente_id":     ingrediente_id,
            "nombre_ingrediente": nombre_ingrediente,
            "almacen":            almacen_id,
            "unidad_medida":      unidad_medida,
            "cantidad_actual":    str(cantidad_actual),
            "nivel_minimo":       str(nivel_minimo),
            "nivel_maximo":       str(nivel_maximo),
        })
        if not data:
            return RegistrarStock(ok=False, error="Error al registrar stock.")
        return RegistrarStock(ok=True, stock=data)


class AjustarStock(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        cantidad = graphene.Float(required=True)
        descripcion = graphene.String(required=True)

    ok = graphene.Boolean()
    stock = graphene.Field(StockType)
    error = graphene.String()

    def mutate(self, info, id, cantidad, descripcion):
        data = inventory_client.ajustar_stock(id, cantidad, descripcion)
        if not data:
            return AjustarStock(ok=False, error="Error al ajustar stock.")
        return AjustarStock(ok=True, stock=data)  # ✅ dict crudo


# ─────────────────────────────────────────
# LOTES
# ─────────────────────────────────────────

class RegistrarLote(graphene.Mutation):
    class Arguments:
        ingrediente_id = graphene.ID(required=True)
        almacen_id = graphene.ID(required=True)
        proveedor_id = graphene.ID(required=True)
        numero_lote = graphene.String(required=True)
        fecha_vencimiento = graphene.String(required=True)
        cantidad_recibida = graphene.Float(required=True)
        unidad_medida = graphene.String(required=True)
        fecha_produccion = graphene.String()

    ok = graphene.Boolean()
    lote = graphene.Field(LoteType)
    error = graphene.String()

    def mutate(self, info, ingrediente_id, almacen_id, proveedor_id,
               numero_lote, fecha_vencimiento, cantidad_recibida,
               unidad_medida, fecha_produccion=None):
        data = inventory_client.crear_lote({
            "ingrediente_id":    ingrediente_id,
            "almacen":           almacen_id,
            "proveedor":         proveedor_id,
            "numero_lote":       numero_lote,
            "fecha_vencimiento": fecha_vencimiento,
            "fecha_produccion":  fecha_produccion,
            "cantidad_recibida": str(cantidad_recibida),
            "unidad_medida":     unidad_medida,
        })
        if not data:
            return RegistrarLote(ok=False, error="Error al registrar lote.")
        return RegistrarLote(ok=True, lote=data)


class RetirarLote(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    lote = graphene.Field(LoteType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.retirar_lote(id)
        if not data:
            return RetirarLote(ok=False, error="Error al retirar lote.")
        return RetirarLote(ok=True, lote=data)


# ─────────────────────────────────────────
# ÓRDENES DE COMPRA
# ─────────────────────────────────────────

class CrearOrdenCompra(graphene.Mutation):
    class Arguments:
        proveedor_id = graphene.ID(required=True)
        restaurante_id = graphene.ID(required=True)
        moneda = graphene.String(required=True)
        detalles = graphene.List(graphene.NonNull(
            DetalleOrdenInput), required=True)
        fecha_entrega_estimada = graphene.String()
        notas = graphene.String()

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, proveedor_id, restaurante_id, moneda, detalles, **kwargs):
        data = inventory_client.crear_orden_compra({
            "proveedor":      proveedor_id,
            "restaurante_id": restaurante_id,
            "moneda":         moneda,
            "detalles":       [dict(d) for d in detalles],
            **kwargs,
        })
        if not data:
            return CrearOrdenCompra(ok=False, error="Error al crear orden de compra.")
        return CrearOrdenCompra(ok=True, orden=data)


class EnviarOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.enviar_orden_compra(id)
        if not data:
            return EnviarOrdenCompra(ok=False, error="Error al enviar orden.")
        return EnviarOrdenCompra(ok=True, orden=data)


class RecibirOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        detalles = graphene.List(graphene.NonNull(
            DetalleRecepcionInput), required=True)
        notas = graphene.String()

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id, detalles, notas=""):
        data = inventory_client.recibir_orden_compra(id, {
            "detalles": [dict(d) for d in detalles],
            "notas":    notas,
        })
        if not data:
            return RecibirOrdenCompra(ok=False, error="Error al recibir orden.")
        return RecibirOrdenCompra(ok=True, orden=data)


class CancelarOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    orden = graphene.Field(OrdenCompraType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.cancelar_orden_compra(id)
        if not data:
            return CancelarOrdenCompra(ok=False, error="Error al cancelar orden.")
        return CancelarOrdenCompra(ok=True, orden=data)


# ─────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────

class ResolverAlerta(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    # ✅ AlertaStockType, no AlertaType
    alerta = graphene.Field(AlertaStockType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.resolver_alerta(id)
        if not data:
            return ResolverAlerta(ok=False, error="Error al resolver alerta.")
        return ResolverAlerta(ok=True, alerta=data)


class IgnorarAlerta(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()
    alerta = graphene.Field(AlertaStockType)
    error = graphene.String()

    def mutate(self, info, id):
        data = inventory_client.ignorar_alerta(id)
        if not data:
            return IgnorarAlerta(ok=False, error="Error al ignorar alerta.")
        return IgnorarAlerta(ok=True, alerta=data)


# ─────────────────────────────────────────
# REGISTRO
# ─────────────────────────────────────────

class InventoryMutation(graphene.ObjectType):
    crear_proveedor = CrearProveedor.Field()
    crear_almacen = CrearAlmacen.Field()
    registrar_stock = RegistrarStock.Field()
    ajustar_stock = AjustarStock.Field()
    registrar_lote = RegistrarLote.Field()
    retirar_lote = RetirarLote.Field()
    crear_orden_compra = CrearOrdenCompra.Field()
    enviar_orden_compra = EnviarOrdenCompra.Field()
    recibir_orden_compra = RecibirOrdenCompra.Field()
    cancelar_orden_compra = CancelarOrdenCompra.Field()
    resolver_alerta = ResolverAlerta.Field()
    ignorar_alerta = IgnorarAlerta.Field()
