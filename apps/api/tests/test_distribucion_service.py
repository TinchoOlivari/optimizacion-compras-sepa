from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import pytest

from app.domain.optimizacion import (
    AsignacionSucursalResultado,
    ConfiguracionOptimizacion,
    DistribucionCarritoVacioError,
    EntradaOptimizacion,
    ItemAsignadoResultado,
    ItemCarritoOptimizacion,
    ItemNoAsignadoResultado,
    OfertaItemCandidata,
    ResultadoDistribucion,
    RuteoResultado,
)
from app.domain.servicios.distribucion import DistribucionService


@dataclass
class _FakePreferenciasRepo:
    configuracion: ConfiguracionOptimizacion

    def obtener_configuracion(self, usuario_id: int) -> ConfiguracionOptimizacion:
        _ = usuario_id
        return self.configuracion

    def guardar_configuracion(
        self,
        usuario_id: int,
        **kwargs: object,
    ) -> ConfiguracionOptimizacion:
        _ = (usuario_id, kwargs)
        return self.configuracion


class _FakeDistribucionRepo:
    def __init__(
        self,
        items: list[ItemCarritoOptimizacion],
        ofertas: list[OfertaItemCandidata] | None = None,
        costo_referencia: float | None = 200.0,
        distribucion_vigente: ResultadoDistribucion | None = None,
    ) -> None:
        self._items = items
        self._ofertas = ofertas or []
        self._costo_referencia = costo_referencia
        self._distribucion_vigente = distribucion_vigente
        self.ofertas_kwargs: dict[str, object] | None = None
        self.referencia_kwargs: dict[str, object] | None = None
        self.guardar_kwargs: dict[str, object] | None = None

    def obtener_items_carrito(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> list[ItemCarritoOptimizacion]:
        _ = (usuario_id, carrito_id)
        return self._items

    def obtener_ofertas_candidatas(
        self,
        usuario_id: int,
        carrito_id: int,
        **kwargs: object,
    ) -> list[OfertaItemCandidata]:
        _ = (usuario_id, carrito_id)
        self.ofertas_kwargs = kwargs
        return self._ofertas

    def calcular_costo_referencia(
        self,
        **kwargs: object,
    ) -> float | None:
        self.referencia_kwargs = kwargs
        return self._costo_referencia

    def guardar_distribucion(
        self,
        usuario_id: int,
        carrito_id: int,
        **kwargs: object,
    ) -> ResultadoDistribucion:
        _ = (usuario_id, carrito_id)
        self.guardar_kwargs = kwargs
        costo_total = cast(float, kwargs["costo_total_estimado"])
        ahorro = cast(float | None, kwargs["ahorro_estimado"])
        configuracion = cast(ConfiguracionOptimizacion, kwargs["configuracion"])
        asignaciones = cast(list[AsignacionSucursalResultado], kwargs["asignaciones"])
        items_no_asignados = cast(
            list[ItemNoAsignadoResultado],
            kwargs["items_no_asignados"],
        )
        ruteo = cast(RuteoResultado, kwargs["ruteo"])
        return ResultadoDistribucion(
            fecha_calculo=datetime.now(UTC),
            costo_total_estimado=costo_total,
            ahorro_estimado=ahorro,
            configuracion=configuracion,
            asignaciones=asignaciones,
            items_no_asignados=items_no_asignados,
            ruteo=ruteo,
        )

    def obtener_distribucion_vigente(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> ResultadoDistribucion | None:
        _ = (usuario_id, carrito_id)
        return self._distribucion_vigente


class _FakeMotor:
    def __init__(self, eventos: list[str] | None = None) -> None:
        self.ultima_entrada: EntradaOptimizacion | None = None
        self._eventos = eventos

    def distribuir(
        self,
        entrada: EntradaOptimizacion,
    ) -> tuple[list[AsignacionSucursalResultado], list[ItemNoAsignadoResultado]]:
        if self._eventos is not None:
            self._eventos.append("motor")
        self.ultima_entrada = entrada
        item = entrada.items[0]
        return (
            [
                AsignacionSucursalResultado(
                    sucursal_id=1,
                    sucursal="Sucursal Centro",
                    comercio="Comercio",
                    direccion=None,
                    localidad=None,
                    provincia=None,
                    latitud=-31.4,
                    longitud=-64.1,
                    subtotal=100.0,
                    items=[
                        ItemAsignadoResultado(
                            item_carrito_id=item.item_carrito_id,
                            producto_id=item.producto_id,
                            nombre_producto=item.nombre_producto,
                            cantidad=item.cantidad,
                            precio_id=99,
                            precio_unitario=100.0,
                            subtotal=100.0,
                        )
                    ],
                )
            ],
            [],
        )


class _FakeOsrm:
    def __init__(self, eventos: list[str] | None = None) -> None:
        self.llamadas: list[list[tuple[float, float]]] = []
        self._eventos = eventos

    def obtener_matriz_km(self, puntos: list[tuple[float, float]]) -> list[list[float]]:
        puntos_lista = list(puntos)
        self.llamadas.append(puntos_lista)
        if self._eventos is not None:
            self._eventos.append("osrm")

        size = len(puntos_lista)
        matriz = [[0.0 for _ in range(size)] for _ in range(size)]
        for indice in range(1, size):
            distancia = round(1.2 + ((indice - 1) * 2.8), 3)
            matriz[0][indice] = distancia
            matriz[indice][0] = distancia
        return matriz


def test_distribucion_falla_con_carrito_vacio() -> None:
    service = DistribucionService(
        preferencias_repo=_FakePreferenciasRepo(
            ConfiguracionOptimizacion(
                radio_km=5,
                max_paradas=3,
                preferencia="MENOR_PRECIO",
                origen_lat=-31.4,
                origen_lon=-64.1,
                por_defecto_aplicado=(),
            )
        ),
        distribucion_repo=_FakeDistribucionRepo(items=[]),
        motor=_FakeMotor(),
        osrm_client=_FakeOsrm(),
    )

    with pytest.raises(DistribucionCarritoVacioError):
        service.distribuir(usuario_id=1, carrito_id=5)


def test_distribucion_calcula_ahorro_y_ruteo() -> None:
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
        )
    ]
    ofertas = [
        OfertaItemCandidata(
            item_carrito_id=1,
            producto_id=10,
            precio_id=101,
            sucursal_id=2,
            sucursal="Sucursal Sur",
            comercio="Comercio B",
            direccion=None,
            localidad=None,
            provincia=None,
            latitud=-31.5,
            longitud=-64.2,
            precio_unitario=110.0,
        ),
        OfertaItemCandidata(
            item_carrito_id=2,
            producto_id=11,
            precio_id=102,
            sucursal_id=1,
            sucursal="Sucursal Centro",
            comercio="Comercio A",
            direccion=None,
            localidad=None,
            provincia=None,
            latitud=-31.4,
            longitud=-64.1,
            precio_unitario=100.0,
        ),
        OfertaItemCandidata(
            item_carrito_id=1,
            producto_id=10,
            precio_id=103,
            sucursal_id=1,
            sucursal="Sucursal Centro",
            comercio="Comercio A",
            direccion=None,
            localidad=None,
            provincia=None,
            latitud=-31.4,
            longitud=-64.1,
            precio_unitario=120.0,
        )
    ]
    repo = _FakeDistribucionRepo(items=items, ofertas=ofertas, costo_referencia=200.0)
    eventos: list[str] = []
    motor = _FakeMotor(eventos)
    osrm = _FakeOsrm(eventos)
    service = DistribucionService(
        preferencias_repo=_FakePreferenciasRepo(
            ConfiguracionOptimizacion(
                radio_km=5,
                max_paradas=3,
                preferencia="MENOR_PRECIO",
                origen_lat=-31.0,
                origen_lon=-64.0,
                por_defecto_aplicado=(),
            )
        ),
        distribucion_repo=repo,
        motor=motor,
        osrm_client=osrm,
    )

    result = service.distribuir(usuario_id=1, carrito_id=5)

    assert result.costo_total_estimado == 100.0
    assert result.ahorro_estimado == 100.0
    assert result.ruteo.distancia_total_km == 1.2
    assert result.asignaciones[0].distancia_km == 1.2
    assert eventos == ["osrm", "motor", "osrm"]
    assert len(osrm.llamadas) == 2
    assert osrm.llamadas[0] == [(-31.0, -64.0), (-31.4, -64.1), (-31.5, -64.2)]
    assert motor.ultima_entrada is not None
    assert motor.ultima_entrada.distancia_origen_sucursal_km == {1: 1.2, 2: 4.0}
    assert repo.ofertas_kwargs == {"origen_lat": -31.0, "origen_lon": -64.0, "radio_km": 5}
    assert repo.referencia_kwargs == {
        "origen_lat": -31.0,
        "origen_lon": -64.0,
        "radio_km": 5,
        "items": [(10, 1)],
    }
    assert motor.ultima_entrada.max_paradas == 3
    assert motor.ultima_entrada.preferencia == "MENOR_PRECIO"


def test_obtener_distribucion_vigente_recalcula_distancia_vial() -> None:
    distribucion = ResultadoDistribucion(
        fecha_calculo=datetime.now(UTC),
        costo_total_estimado=100.0,
        ahorro_estimado=20.0,
        configuracion=ConfiguracionOptimizacion(
            radio_km=5,
            max_paradas=3,
            preferencia="MENOR_PRECIO",
            origen_lat=-31.0,
            origen_lon=-64.0,
            por_defecto_aplicado=(),
        ),
        asignaciones=[
            AsignacionSucursalResultado(
                sucursal_id=1,
                sucursal="Sucursal Centro",
                comercio="Comercio",
                direccion=None,
                localidad=None,
                provincia=None,
                latitud=-31.4,
                longitud=-64.1,
                subtotal=100.0,
                items=[],
                distancia_km=99.9,
            )
        ],
        items_no_asignados=[],
        ruteo=RuteoResultado(distancia_total_km=1.2, paradas=[]),
    )
    service = DistribucionService(
        preferencias_repo=_FakePreferenciasRepo(distribucion.configuracion),
        distribucion_repo=_FakeDistribucionRepo(
            items=[],
            distribucion_vigente=distribucion,
        ),
        motor=_FakeMotor(),
        osrm_client=_FakeOsrm(),
    )

    result = service.obtener_distribucion_vigente(usuario_id=1, carrito_id=5)

    assert result.asignaciones[0].distancia_km == 1.2


def test_distribucion_preserva_defaults_en_configuracion_efectiva() -> None:
    items = [
        ItemCarritoOptimizacion(
            item_carrito_id=1,
            producto_id=10,
            nombre_producto="Leche",
            cantidad=1,
        )
    ]
    repo = _FakeDistribucionRepo(
        items=items,
        ofertas=[
            OfertaItemCandidata(
                item_carrito_id=1,
                producto_id=10,
                precio_id=99,
                sucursal_id=1,
                sucursal="Sucursal Centro",
                comercio="Comercio",
                direccion=None,
                localidad=None,
                provincia=None,
                latitud=-31.4,
                longitud=-64.1,
                precio_unitario=100.0,
            )
        ],
    )
    defaults = ("max_paradas", "preferencia")
    service = DistribucionService(
        preferencias_repo=_FakePreferenciasRepo(
            ConfiguracionOptimizacion(
                radio_km=10,
                max_paradas=3,
                preferencia="MENOR_PRECIO",
                origen_lat=-31.4,
                origen_lon=-64.1,
                por_defecto_aplicado=defaults,
            )
        ),
        distribucion_repo=repo,
        motor=_FakeMotor(),
        osrm_client=_FakeOsrm(),
    )

    result = service.distribuir(usuario_id=7, carrito_id=10)

    assert result.configuracion.por_defecto_aplicado == defaults
    assert repo.guardar_kwargs is not None
    saved_config = repo.guardar_kwargs["configuracion"]
    assert isinstance(saved_config, ConfiguracionOptimizacion)
    assert saved_config.por_defecto_aplicado == defaults


def test_distribucion_ahorro_queda_null_sin_referencia() -> None:
    items = [
        ItemCarritoOptimizacion(
            item_carrito_id=1,
            producto_id=10,
            nombre_producto="Leche",
            cantidad=1,
        )
    ]
    repo = _FakeDistribucionRepo(
        items=items,
        ofertas=[
            OfertaItemCandidata(
                item_carrito_id=1,
                producto_id=10,
                precio_id=99,
                sucursal_id=1,
                sucursal="Sucursal Centro",
                comercio="Comercio",
                direccion=None,
                localidad=None,
                provincia=None,
                latitud=-31.4,
                longitud=-64.1,
                precio_unitario=100.0,
            )
        ],
        costo_referencia=None,
    )
    service = DistribucionService(
        preferencias_repo=_FakePreferenciasRepo(
            ConfiguracionOptimizacion(
                radio_km=5,
                max_paradas=3,
                preferencia="MENOR_PRECIO",
                origen_lat=-31.4,
                origen_lon=-64.1,
                por_defecto_aplicado=(),
            )
        ),
        distribucion_repo=repo,
        motor=_FakeMotor(),
        osrm_client=_FakeOsrm(),
    )

    result = service.distribuir(usuario_id=1, carrito_id=5)

    assert result.costo_total_estimado == 100.0
    assert result.ahorro_estimado is None
