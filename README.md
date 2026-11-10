# 🍽️ RestoHub — Backend

Plataforma de gestión de restaurantes basada en **microservicios Django**, con un **gateway GraphQL** y comunicación por eventos (RabbitMQ).

![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)
![GraphQL](https://img.shields.io/badge/GraphQL-Graphene-E10098?logo=graphql&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?logo=rabbitmq&logoColor=white)
![Postgres](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

## Arquitectura

| Servicio | Puerto | Responsabilidad |
|---|---|---|
| `gateway_service` | 8000 | Gateway GraphQL (Graphene); agrega los demás servicios vía clientes REST |
| `menu_service` | 8001 | Catálogo: restaurantes, categorías, platos, ingredientes, precios |
| `order_service` | 8002 | Pedidos, detalle, comandas de cocina, seguimiento |
| `inventory_service` | 8003 | Stock, lotes, órdenes de compra, alertas |
| `loyalty_service` | 8004 | Puntos, promociones, cupones (caché en Redis) |
| `staff_service` | 8005 | Empleados, turnos, asignaciones |
| `auth_service` | 8006 | Autenticación |

Infraestructura: PostgreSQL 15 (una base por servicio, creadas por `docker/init.sql`), RabbitMQ, Redis, Prometheus (9090) y Grafana (3000).

**Sin base de datos compartida:** las referencias entre servicios son `UUID` sin claves foráneas.

### Eventos (RabbitMQ)

Convención `app.{servicio}.{entidad}.{accion}`, p. ej. `app.menu.plato.creado`.

- `menu_service` publica cambios de platos, ingredientes, restaurantes y precios.
- `order_service` publica `pedido.confirmado`, `pedido.cancelado`, `pedido.entregado`.
- `inventory_service` consume pedidos para descontar stock y publica alertas.
- `loyalty_service` consume `pedido.entregado` para acumular puntos.

Los handlers deben ser **idempotentes**.

## Cómo correrlo

### Con Docker (recomendado)

```bash
git clone -b juan-backend https://github.com/JSRT23/RESTOHUB_BACKEND.git
cd RESTOHUB_BACKEND
docker compose up -d      # levanta postgres, rabbitmq, redis y todos los servicios
docker compose down       # detener sin borrar datos
```

### Sin Docker (un servicio)

```bash
cd services/menu_service
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8001      # ajusta el puerto por servicio
python manage.py declare_queues              # una vez, antes del consumer
python manage.py consume_<servicio>_events   # p. ej. consume_inventory_events
```

Necesitas PostgreSQL, RabbitMQ y Redis accesibles y las variables de cada servicio.

## Convenciones de código

- PK `UUID`; borrado lógico con `activo`; auditoría con `fecha_creacion` / `fecha_actualizacion`.
- Logs inmutables (movimientos de inventario, transacciones de puntos, seguimiento de pedidos): solo se agregan.
- Serializers separados: `*Serializer` (detalle), `*ListSerializer` (lista), `*WriteSerializer` (escritura).
- Más detalle en [`CLAUDE.md`](CLAUDE.md).

## CI/CD y monitoreo

- Workflow en `.github/workflows/ci-cd.yml`.
- Prometheus y Grafana en `monitoring/`; en producción las métricas se envían a Grafana Cloud con [restohub-alloy](https://github.com/JSRT23/restohub-alloy).

Frontends: [RESTOHUB_FRONTEND](https://github.com/JSRT23/RESTOHUB_FRONTEND).

> 🔐 **Seguridad:** este repo tenía un archivo `.env` versionado con credenciales. Rota esas credenciales y deja de versionar el `.env`.
