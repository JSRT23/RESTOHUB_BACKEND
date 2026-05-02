# tests/unit/test_schema.py
"""
Tests estructurales del schema GraphQL.
Verifican que todas las queries/mutations existen y tienen los campos esperados.
No requieren mocks — solo validan la introspección del schema.
"""
import pytest
from app.gateway.graphql.schema import schema


class TestQuerySchema:

    def test_schema_tiene_query(self):
        assert schema.graphql_schema.query_type is not None

    def test_schema_tiene_mutation(self):
        assert schema.graphql_schema.mutation_type is not None

    # ── Auth ──────────────────────────────────────────────────────────────
    def test_query_me_existe(self):
        fields = schema.graphql_schema.query_type.fields
        assert "me" in fields

    def test_query_usuarios_existe(self):
        assert "usuarios" in schema.graphql_schema.query_type.fields

    # ── Menu ──────────────────────────────────────────────────────────────
    def test_query_restaurantes_existe(self):
        assert "restaurantes" in schema.graphql_schema.query_type.fields

    def test_query_menu_restaurante_existe(self):
        assert "menuRestaurante" in schema.graphql_schema.query_type.fields

    def test_query_platos_existe(self):
        assert "platos" in schema.graphql_schema.query_type.fields

    def test_query_categorias_existe(self):
        assert "categorias" in schema.graphql_schema.query_type.fields

    def test_query_ingredientes_existe(self):
        assert "ingredientes" in schema.graphql_schema.query_type.fields

    def test_query_precios_existe(self):
        assert "precios" in schema.graphql_schema.query_type.fields

    # ── Staff ─────────────────────────────────────────────────────────────
    def test_query_empleados_existe(self):
        assert "empleados" in schema.graphql_schema.query_type.fields

    def test_query_turnos_existe(self):
        assert "turnos" in schema.graphql_schema.query_type.fields

    def test_query_asistencia_existe(self):
        assert "asistencia" in schema.graphql_schema.query_type.fields

    def test_query_alertas_operacionales_existe(self):
        assert "alertasOperacionales" in schema.graphql_schema.query_type.fields

    def test_query_nomina_existe(self):
        assert "nomina" in schema.graphql_schema.query_type.fields

    # ── Order ─────────────────────────────────────────────────────────────
    def test_query_pedidos_existe(self):
        assert "pedidos" in schema.graphql_schema.query_type.fields

    def test_query_pedido_existe(self):
        assert "pedido" in schema.graphql_schema.query_type.fields

    def test_query_comandas_existe(self):
        assert "comandas" in schema.graphql_schema.query_type.fields

    def test_query_seguimiento_pedido_existe(self):
        assert "seguimientoPedido" in schema.graphql_schema.query_type.fields

    # ── Inventory ─────────────────────────────────────────────────────────
    def test_query_proveedores_existe(self):
        assert "proveedores" in schema.graphql_schema.query_type.fields

    def test_query_almacenes_existe(self):
        assert "almacenes" in schema.graphql_schema.query_type.fields

    def test_query_stock_existe(self):
        assert "stock" in schema.graphql_schema.query_type.fields

    def test_query_ordenes_compra_existe(self):
        assert "ordenesCompra" in schema.graphql_schema.query_type.fields

    def test_query_alertas_stock_existe(self):
        assert "alertasStock" in schema.graphql_schema.query_type.fields

    # ── Loyalty ───────────────────────────────────────────────────────────
    def test_query_puntos_cliente_existe(self):
        assert "puntosCliente" in schema.graphql_schema.query_type.fields

    def test_query_promociones_existe(self):
        assert "promociones" in schema.graphql_schema.query_type.fields

    def test_query_cupones_existe(self):
        assert "cupones" in schema.graphql_schema.query_type.fields

    def test_query_validar_cupon_existe(self):
        assert "validarCupon" in schema.graphql_schema.query_type.fields


class TestMutationSchema:

    # ── Auth ──────────────────────────────────────────────────────────────
    def test_mutation_login_existe(self):
        assert "login" in schema.graphql_schema.mutation_type.fields

    def test_mutation_auto_registro_existe(self):
        assert "autoRegistro" in schema.graphql_schema.mutation_type.fields

    def test_mutation_verificar_codigo_existe(self):
        assert "verificarCodigo" in schema.graphql_schema.mutation_type.fields

    def test_mutation_registrar_usuario_existe(self):
        assert "registrarUsuario" in schema.graphql_schema.mutation_type.fields

    def test_mutation_vincular_empleado_id_existe(self):
        assert "vincularEmpleadoId" in schema.graphql_schema.mutation_type.fields

    def test_mutation_desactivar_usuario_existe(self):
        assert "desactivarUsuario" in schema.graphql_schema.mutation_type.fields

    # ── Menu ──────────────────────────────────────────────────────────────
    def test_mutation_crear_restaurante_existe(self):
        assert "crearRestaurante" in schema.graphql_schema.mutation_type.fields

    def test_mutation_crear_plato_existe(self):
        assert "crearPlato" in schema.graphql_schema.mutation_type.fields

    def test_mutation_crear_precio_plato_existe(self):
        assert "crearPrecioPlato" in schema.graphql_schema.mutation_type.fields

    # ── Staff ─────────────────────────────────────────────────────────────
    def test_mutation_crear_empleado_existe(self):
        assert "crearEmpleado" in schema.graphql_schema.mutation_type.fields

    def test_mutation_crear_turno_existe(self):
        assert "crearTurno" in schema.graphql_schema.mutation_type.fields

    def test_mutation_iniciar_turno_existe(self):
        assert "iniciarTurno" in schema.graphql_schema.mutation_type.fields

    def test_mutation_completar_turno_existe(self):
        assert "completarTurno" in schema.graphql_schema.mutation_type.fields

    def test_mutation_cancelar_turno_existe(self):
        assert "cancelarTurno" in schema.graphql_schema.mutation_type.fields

    def test_mutation_registrar_entrada_existe(self):
        assert "registrarEntrada" in schema.graphql_schema.mutation_type.fields

    def test_mutation_registrar_salida_existe(self):
        assert "registrarSalida" in schema.graphql_schema.mutation_type.fields

    def test_mutation_generar_nomina_existe(self):
        assert "generarNomina" in schema.graphql_schema.mutation_type.fields

    # ── Order ─────────────────────────────────────────────────────────────
    def test_mutation_crear_pedido_existe(self):
        assert "crearPedido" in schema.graphql_schema.mutation_type.fields

    def test_mutation_confirmar_pedido_existe(self):
        assert "confirmarPedido" in schema.graphql_schema.mutation_type.fields

    def test_mutation_cancelar_pedido_existe(self):
        assert "cancelarPedido" in schema.graphql_schema.mutation_type.fields

    def test_mutation_marcar_listo_existe(self):
        assert "marcarListo" in schema.graphql_schema.mutation_type.fields

    def test_mutation_entregar_pedido_existe(self):
        assert "entregarPedido" in schema.graphql_schema.mutation_type.fields

    def test_mutation_iniciar_comanda_existe(self):
        assert "iniciarComanda" in schema.graphql_schema.mutation_type.fields

    def test_mutation_comanda_lista_existe(self):
        assert "comandaLista" in schema.graphql_schema.mutation_type.fields

    # ── Inventory ─────────────────────────────────────────────────────────
    def test_mutation_crear_proveedor_existe(self):
        assert "crearProveedor" in schema.graphql_schema.mutation_type.fields

    def test_mutation_crear_almacen_existe(self):
        assert "crearAlmacen" in schema.graphql_schema.mutation_type.fields

    def test_mutation_crear_orden_compra_existe(self):
        assert "crearOrdenCompra" in schema.graphql_schema.mutation_type.fields

    def test_mutation_recibir_orden_compra_existe(self):
        assert "recibirOrdenCompra" in schema.graphql_schema.mutation_type.fields

    # ── Loyalty ───────────────────────────────────────────────────────────
    def test_mutation_acumular_puntos_existe(self):
        assert "acumularPuntos" in schema.graphql_schema.mutation_type.fields

    def test_mutation_canjear_puntos_existe(self):
        assert "canjearPuntos" in schema.graphql_schema.mutation_type.fields

    def test_mutation_crear_promocion_existe(self):
        assert "crearPromocion" in schema.graphql_schema.mutation_type.fields

    def test_mutation_evaluar_promocion_existe(self):
        assert "evaluarPromocion" in schema.graphql_schema.mutation_type.fields

    def test_mutation_crear_cupon_existe(self):
        assert "crearCupon" in schema.graphql_schema.mutation_type.fields

    def test_mutation_canjear_cupon_existe(self):
        assert "canjearCupon" in schema.graphql_schema.mutation_type.fields
