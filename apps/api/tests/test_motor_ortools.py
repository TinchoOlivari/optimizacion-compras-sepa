import pytest

from app.domain.optimizacion import (
    EntradaOptimizacion,
    ItemCarritoOptimizacion,
    OfertaItemCandidata,
    PreferenciaOptimizacion,
)
from app.infra.motor_ortools import MotorOrTools

cp_model = pytest.importorskip("ortools.sat.python.cp_model")


def _entrada_base(
    max_paradas: int = 1,
    *,
    distancias: dict[int, float] | None = None,
) -> EntradaOptimizacion:
    items = [
        ItemCarritoOptimizacion(
            item_carrito_id=1,
            producto_id=10,
            nombre_producto="Leche",
            cantidad=1,
        ),
        ItemCarritoOptimizacion(
            item_carrito_id=2,
            producto_id=11,
            nombre_producto="Pan",
            cantidad=1,
        ),
    ]
    ofertas = [
        OfertaItemCandidata(
            item_carrito_id=1,
            producto_id=10,
            precio_id=101,
            sucursal_id=1,
            sucursal="Sucursal 1",
            comercio="Comercio A",
            direccion=None,
            localidad=None,
            provincia=None,
            latitud=-31.4,
            longitud=-64.1,
            precio_unitario=100.0,
        ),
        OfertaItemCandidata(
            item_carrito_id=2,
            producto_id=11,
            precio_id=201,
            sucursal_id=2,
            sucursal="Sucursal 2",
            comercio="Comercio B",
            direccion=None,
            localidad=None,
            provincia=None,
            latitud=-31.5,
            longitud=-64.2,
            precio_unitario=90.0,
        ),
        OfertaItemCandidata(
            item_carrito_id=2,
            producto_id=11,
            precio_id=202,
            sucursal_id=1,
            sucursal="Sucursal 1",
            comercio="Comercio A",
            direccion=None,
            localidad=None,
            provincia=None,
            latitud=-31.4,
            longitud=-64.1,
            precio_unitario=110.0,
        ),
    ]
    return EntradaOptimizacion(
        items=items,
        ofertas=ofertas,
        max_paradas=max_paradas,
        preferencia="MENOR_PRECIO",
        origen_lat=-31.4,
        origen_lon=-64.1,
        distancia_origen_sucursal_km=distancias or {},
    )


def test_motor_respeta_max_paradas_en_greedy() -> None:
    motor = MotorOrTools()
    asignaciones, _ = motor._resolver_greedy(_entrada_base(max_paradas=1))

    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 1


def test_motor_retorna_items_no_asignados_si_no_hay_ofertas() -> None:
    entrada = _entrada_base()
    entrada = EntradaOptimizacion(
        items=entrada.items,
        ofertas=[],
        max_paradas=1,
        preferencia="MENOR_PRECIO",
        origen_lat=-31.4,
        origen_lon=-64.1,
    )
    motor = MotorOrTools()

    asignaciones, no_asignados = motor.distribuir(entrada)

    assert asignaciones == []
    assert len(no_asignados) == 2


def test_resolver_greedy_balanceado_sin_ofertas_no_crashea() -> None:
    entrada = _entrada_base()
    entrada = EntradaOptimizacion(
        items=entrada.items,
        ofertas=[],
        max_paradas=1,
        preferencia="BALANCEADO",
        origen_lat=-31.4,
        origen_lon=-64.1,
    )

    asignaciones, no_asignados = MotorOrTools()._resolver_greedy(entrada)

    assert asignaciones == []
    assert [item.item_carrito_id for item in no_asignados] == [1, 2]


def _item(item_id: int) -> ItemCarritoOptimizacion:
    return ItemCarritoOptimizacion(
        item_carrito_id=item_id,
        producto_id=item_id,
        nombre_producto=f"Producto {item_id}",
        cantidad=1,
    )


def _oferta(
    item_id: int,
    sucursal_id: int,
    precio: float,
    *,
    latitud: float,
    longitud: float,
) -> OfertaItemCandidata:
    return OfertaItemCandidata(
        item_carrito_id=item_id,
        producto_id=item_id,
        precio_id=item_id * 100 + sucursal_id,
        sucursal_id=sucursal_id,
        sucursal=f"Sucursal {sucursal_id}",
        comercio=f"Comercio {sucursal_id}",
        direccion=None,
        localidad=None,
        provincia=None,
        latitud=latitud,
        longitud=longitud,
        precio_unitario=precio,
    )


def _entrada_greedy(
    *,
    items: list[ItemCarritoOptimizacion],
    ofertas: list[OfertaItemCandidata],
    preferencia: PreferenciaOptimizacion,
    max_paradas: int = 1,
    distancias: dict[int, float] | None = None,
) -> EntradaOptimizacion:
    return EntradaOptimizacion(
        items=items,
        ofertas=ofertas,
        max_paradas=max_paradas,
        preferencia=preferencia,
        origen_lat=0.0,
        origen_lon=0.0,
        distancia_origen_sucursal_km=distancias or {},
    )


def test_resolver_greedy_prefiere_menor_precio() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 120.0, latitud=0.0, longitud=0.0),
            _oferta(1, 2, 100.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="MENOR_PRECIO",
        distancias={1: 10.0, 2: 5.0},
    )

    asignaciones, no_asignados = MotorOrTools()._resolver_greedy(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert asignaciones[0].subtotal == 100.0


def test_resolver_greedy_prefiere_menor_desplazamiento() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 80.0, latitud=0.0, longitud=0.1),
            _oferta(1, 2, 90.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="MENOR_DESPLAZAMIENTO",
        distancias={1: 50.0, 2: 5.0},
    )

    asignaciones, no_asignados = MotorOrTools()._resolver_greedy(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert asignaciones[0].subtotal == 90.0


def test_resolver_greedy_distancia_faltante_no_cuenta_como_cero() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 70.0, latitud=0.0, longitud=0.1),
            _oferta(1, 2, 80.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="MENOR_DESPLAZAMIENTO",
        distancias={2: 5.0},
    )

    asignaciones, no_asignados = MotorOrTools()._resolver_greedy(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert asignaciones[0].subtotal == 80.0


def test_resolver_greedy_balanceado_prefiere_distancia_conocida() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 50.0, latitud=0.0, longitud=0.1),
            _oferta(1, 2, 80.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="BALANCEADO",
        distancias={2: 5.0},
    )

    asignaciones, no_asignados = MotorOrTools()._resolver_greedy(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert asignaciones[0].subtotal == 80.0


def test_resolver_greedy_balanceado_max_paradas_no_prioriza_distancia_faltante_barata() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 1.0, latitud=0.0, longitud=0.1),
            _oferta(1, 2, 80.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="BALANCEADO",
        max_paradas=2,
        distancias={2: 5.0},
    )

    asignaciones, no_asignados = MotorOrTools()._resolver_greedy(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert asignaciones[0].subtotal == 80.0


def test_distribuir_balanceado_no_prioriza_distancia_faltante_con_ortools() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 50.0, latitud=0.0, longitud=0.1),
            _oferta(1, 2, 80.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="BALANCEADO",
        distancias={2: 5.0},
    )
    motor = MotorOrTools()

    def _fallar_greedy(
        _entrada: EntradaOptimizacion,
    ) -> tuple[list[object], list[object]]:
        raise AssertionError(
            "distribuir() no debe caer al greedy con OR-Tools disponible"
        )

    motor._resolver_greedy = _fallar_greedy  # type: ignore[method-assign]

    asignaciones, no_asignados = motor.distribuir(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert asignaciones[0].subtotal == 80.0


def test_distribuir_balanceado_max_paradas_no_prioriza_distancia_faltante_barata() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 1.0, latitud=0.0, longitud=0.1),
            _oferta(1, 2, 80.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="BALANCEADO",
        max_paradas=2,
        distancias={2: 5.0},
    )
    motor = MotorOrTools()

    def _fallar_greedy(
        _entrada: EntradaOptimizacion,
    ) -> tuple[list[object], list[object]]:
        raise AssertionError(
            "distribuir() no debe caer al greedy con OR-Tools disponible"
        )

    motor._resolver_greedy = _fallar_greedy  # type: ignore[method-assign]

    asignaciones, no_asignados = motor.distribuir(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert asignaciones[0].subtotal == 80.0


def test_distribuir_balanceado_preserva_distancia_cero_como_conocida() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 1.0, latitud=0.0, longitud=0.1),
            _oferta(1, 2, 80.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="BALANCEADO",
        max_paradas=2,
        distancias={2: 0.0},
    )

    asignaciones, no_asignados = MotorOrTools().distribuir(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert asignaciones[0].subtotal == 80.0


def test_resolver_greedy_balanceado_usa_distancia_faltante_si_no_hay_conocida() -> None:
    entrada = _entrada_greedy(
        items=[_item(1)],
        ofertas=[
            _oferta(1, 1, 50.0, latitud=0.0, longitud=0.1),
            _oferta(1, 2, 80.0, latitud=0.0, longitud=1.0),
        ],
        preferencia="BALANCEADO",
    )

    asignaciones, no_asignados = MotorOrTools()._resolver_greedy(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 1
    assert asignaciones[0].subtotal == 50.0


def test_resolver_greedy_balanceado_y_reuso_max_paradas() -> None:
    entrada = _entrada_greedy(
        items=[_item(1), _item(2)],
        ofertas=[
            _oferta(1, 1, 100.0, latitud=0.0, longitud=0.2),
            _oferta(1, 2, 115.0, latitud=0.0, longitud=0.1),
            _oferta(1, 3, 140.0, latitud=0.0, longitud=0.3),
            _oferta(2, 1, 90.0, latitud=0.0, longitud=0.2),
            _oferta(2, 2, 110.0, latitud=0.0, longitud=0.1),
        ],
        preferencia="BALANCEADO",
        max_paradas=1,
        distancias={1: 20.0, 2: 5.0, 3: 30.0},
    )

    asignaciones, no_asignados = MotorOrTools()._resolver_greedy(entrada)

    assert no_asignados == []
    assert len(asignaciones) == 1
    assert asignaciones[0].sucursal_id == 2
    assert [item.item_carrito_id for item in asignaciones[0].items] == [1, 2]
    assert asignaciones[0].subtotal == 225.0


def test_cp_sat_cubre_todos_los_items_dentro_de_paradas() -> None:
    entrada = EntradaOptimizacion(
        items=[_item(1), _item(2)],
        ofertas=[
            _oferta(1, 1, 100.0, latitud=-31.40, longitud=-64.10),
            _oferta(2, 2, 90.0, latitud=-31.50, longitud=-64.20),
        ],
        max_paradas=2,
        preferencia="MENOR_PRECIO",
        origen_lat=-31.40,
        origen_lon=-64.10,
    )

    asignaciones, no_asignados = MotorOrTools().distribuir(entrada)

    assert no_asignados == []
    assert {a.sucursal_id for a in asignaciones} == {1, 2}
    assert round(sum(a.subtotal for a in asignaciones), 2) == 190.0
