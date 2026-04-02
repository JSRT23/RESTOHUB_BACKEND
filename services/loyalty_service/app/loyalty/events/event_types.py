# loyalty_service/app/loyalty/events/event_types.py
class LoyaltyEvents:
    """
    Eventos publicados por loyalty_service.

    Convención: app.{servicio}.{entidad}.{accion}

    ┌──────────────────────────────────────┬──────────────────────────────┐
    │ Evento                               │ Consumidores                 │
    ├──────────────────────────────────────┼──────────────────────────────┤
    │ puntos.acumulados                    │ gateway (notifica cliente)   │
    │ promocion.aplicada                   │ gateway / analytics          │
    └──────────────────────────────────────┴──────────────────────────────┘

    Eventos que CONSUME:
    ┌──────────────────────────────────────┬──────────────────────────────┐
    │ Origen                               │ Evento                       │
    ├──────────────────────────────────────┼──────────────────────────────┤
    │ order_service                        │ pedido.entregado             │
    │ order_service                        │ pedido.cancelado             │
    │ menu_service                         │ plato.creado/actualizado/    │
    │                                      │ desactivado                  │
    │ menu_service                         │ categoria.creada/actualizada/│
    │                                      │ desactivada                  │
    └──────────────────────────────────────┴──────────────────────────────┘
    """

    PUNTOS_ACUMULADOS = "app.loyalty.puntos.acumulados"
    # data: {
    #   cliente_id, pedido_id, restaurante_id,
    #   puntos_ganados, saldo_anterior, saldo_nuevo,
    #   nivel_anterior, nivel_nuevo
    # }

    PROMOCION_APLICADA = "app.loyalty.promocion.aplicada"
    # data: {
    #   cliente_id, pedido_id, promocion_id,
    #   descuento_aplicado, puntos_bonus_otorgados
    # }
