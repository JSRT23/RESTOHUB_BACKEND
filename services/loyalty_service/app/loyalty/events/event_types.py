# loyalty_service/app/loyalty/events/event_types.py
class LoyaltyEvents:
    """
    Eventos publicados por loyalty_service al exchange 'restohub'.
    Convención: app.{servicio}.{entidad}.{accion}

    Consumidores:
    ┌──────────────────────────────────┬─────────────────────────────────┐
    │ Evento                           │ Consumidores                    │
    ├──────────────────────────────────┼─────────────────────────────────┤
    │ puntos.acumulados                │ gateway                         │
    │ puntos.canjeados                 │ gateway, order_service          │
    │ promocion.aplicada               │ order_service                   │
    │ cupon.generado                   │ gateway                         │
    │ cupon.canjeado                   │ gateway                         │
    └──────────────────────────────────┴─────────────────────────────────┘
    """

    # Puntos
    PUNTOS_ACUMULADOS = "app.loyalty.puntos.acumulados"
    # data: { cuenta_id, cliente_id, puntos_acumulados, saldo_nuevo,
    #         nivel, pedido_id, restaurante_id }

    PUNTOS_CANJEADOS = "app.loyalty.puntos.canjeados"
    # data: { cuenta_id, cliente_id, puntos_canjeados, saldo_nuevo,
    #         pedido_id }

    # Promociones
    PROMOCION_APLICADA = "app.loyalty.promocion.aplicada"
    # data: { promocion_id, pedido_id, cliente_id,
    #         tipo_descuento, descuento, puntos_bonus }
    # order_service consume este evento para aplicar el descuento al pedido

    # Cupones
    CUPON_GENERADO = "app.loyalty.cupon.generado"
    # data: { cupon_id, codigo, cliente_id, tipo_descuento,
    #         valor_descuento, fecha_fin }

    CUPON_CANJEADO = "app.loyalty.cupon.canjeado"
    # data: { cupon_id, codigo, cliente_id, pedido_id,
    #         valor_descuento }
