# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Project

```bash
# Start all services (preferred — spins up postgres, rabbitmq, redis + all microservices)
docker compose up -d

# Stop without removing containers
docker compose down

# Per-service development (inside a service folder)
python manage.py runserver 0.0.0.0:8001   # adjust port per service

# Migrations
python manage.py makemigrations
python manage.py migrate

# Start RabbitMQ consumer for a service
python manage.py declare_queues           # must run first
python manage.py consume_<service>_events # e.g. consume_inventory_events
```

## Architecture Overview

Six Django microservices + one gateway, all in `services/`:

| Service | Port | Purpose |
|---|---|---|
| `gateway_service` | 8000 | GraphQL gateway (Graphene) — aggregates all other services via REST clients |
| `menu_service` | 8001 | Global catalog: Restaurante, Categoria, Plato, Ingrediente, PrecioPlato |
| `order_service` | 8002 | Orders: Pedido, DetallePedido, ComandaCocina, SeguimientoPedido |
| `inventory_service` | 8003 | Stock, batches, purchase orders, alerts |
| `loyalty_service` | 8004 | Points, promotions, coupons (uses Redis cache) |
| `staff_service` | 8005 | Employees, shifts, kitchen/delivery assignments |

**No shared database.** Each service has its own PostgreSQL DB. Cross-service references are plain `UUIDField` (no FK constraints).

## Event-Driven Messaging (RabbitMQ)

Event naming convention: `app.{service}.{entity}.{action}` — e.g. `app.menu.plato.creado`.

Key flows:
- `menu_service` → publishes `plato.*`, `ingrediente.*`, `restaurante.*`, `precio.*`, `plato_ingrediente.*`
- `order_service` → publishes `pedido.confirmado`, `pedido.cancelado`, `pedido.entregado`
- `inventory_service` consumes order events to adjust stock; publishes `alerta.*`, `stock.actualizado`
- `loyalty_service` consumes `pedido.entregado` to accumulate points

Each service has:
- `infrastructure/messaging/publisher.py` — singleton `get_publisher()`, call `.publish(event_type, data_dict)`
- `infrastructure/messaging/consumer_base.py` — `BaseConsumer`, register handlers then `.start()`
- `management/commands/declare_queues.py` — run once before consumer
- `management/commands/consume_*_events.py` — entry point for consumer process

Event handlers live in `application/event_handlers/`. All handlers must be **idempotent** (use `ProcessedEvent` model or guard logic).

## GraphQL Gateway

`gateway_service` uses Graphene (not Apollo Federation). The schema is composed manually in `app/gateway/graphql/schema.py` by mixing in per-service `Query`/`Mutation` classes.

Each service has a folder under `app/gateway/graphql/services/{service}/`:
- `types.py` — `graphene.ObjectType` matching the service REST response fields
- `queries.py` — resolvers that call the REST client
- `mutations.py` — mutations that call the REST client

REST clients in `app/gateway/client/{service}_client.py` use `httpx` with `INVENTORY_SERVICE_URL` etc. from env vars.

## Code Patterns

**Models:**
- All PKs: `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- Soft delete: `activo = BooleanField(default=True)` — never hard-delete business records
- Audit: `fecha_creacion` (auto_now_add) + `fecha_actualizacion` (auto_now)
- Immutable logs (`MovimientoInventario`, `TransaccionPuntos`, `SeguimientoPedido`): append-only, never updated

**Serializers:**
- `*Serializer` — full read (detail view)
- `*ListSerializer` — lightweight read (list view)
- `*WriteSerializer` — write operations (POST/PATCH)
- Separation is enforced via `get_serializer_class()` in each ViewSet

**ViewSets:** Use `perform_create` / `perform_update` to publish RabbitMQ events after saving. Custom actions use `@action(detail=True/False, methods=[...])`.

**Publishing events from a view:**
```python
get_publisher().publish(InventoryEvents.STOCK_ACTUALIZADO, InventoryEventBuilder.stock_actualizado(...))
```

## Inventory Service Specifics

- `_crear_movimiento(inv, tipo, cantidad, descripcion)` — helper that updates `IngredienteInventario.cantidad_actual` and creates a `MovimientoInventario` log entry. For `AJUSTE`, `cantidad` is signed (positive = add, negative = subtract).
- `_verificar_alertas(inv)` — call after any stock reduction to auto-create `AlertaStock` if below minimum.
- `RecetaPlato` — local copy of `menu_service`'s `PlatoIngrediente`, kept in sync via RabbitMQ. Used to calculate ingredient consumption per order and dish cost analysis.
- When receiving a purchase order (`OrdenCompra.recibir` action), a `LoteIngrediente` is created per detail, stock is increased, `costo_unitario` in `RecetaPlato` is updated, and `inv.lote_actual` is set.

## Stack

- Python 3.11, Django 6.0.3, Django REST Framework
- Graphene-Django (GraphQL)
- psycopg2 (PostgreSQL), pika (RabbitMQ), redis-py (Redis cache in loyalty_service)
- httpx (HTTP client in gateway)
- All services containerized via Docker Compose
