from dataclasses import replace
from datetime import UTC, datetime

from app.domain.optimizacion import (
    AsignacionSucursalResultado,
    ConfiguracionOptimizacion,
    DistribucionCarritoVacioError,
    DistribucionConfigError,
    DistribucionNoEncontradaError,
    EntradaOptimizacion,
    IDistribucionRepository,
    IMotorOptimizacion,
    IPreferenciasRepository,
    ItemNoAsignadoResultado,
    OfertaItemCandidata,
    ParadaResultado,
    PreferenciaOptimizacion,
    ResultadoDistribucion,
    RuteoResultado,
)
from app.infra.geo_clients import IOsrmClient


class DistribucionService:
    def __init__(
        self,
        preferencias_repo: IPreferenciasRepository,
        distribucion_repo: IDistribucionRepository,
        motor: IMotorOptimizacion,
        osrm_client: IOsrmClient,
    ) -> None:
        self._preferencias_repo = preferencias_repo
        self._distribucion_repo = distribucion_repo
        self._motor = motor
        self._osrm_client = osrm_client

    def obtener_preferencias(self, usuario_id: int) -> ConfiguracionOptimizacion:
        return self._preferencias_repo.obtener_configuracion(usuario_id)

    def guardar_preferencias(
        self,
        usuario_id: int,
        *,
        radio_km: int | None,
        max_paradas: int | None,
        preferencia: PreferenciaOptimizacion | None,
        origen_lat: float | None,
        origen_lon: float | None,
        origen_direccion: str | None,
        origen_modalidad: str | None,
    ) -> ConfiguracionOptimizacion:
        return self._preferencias_repo.guardar_configuracion(
            usuario_id,
            radio_km=radio_km,
            max_paradas=max_paradas,
            preferencia=preferencia,
            origen_lat=origen_lat,
            origen_lon=origen_lon,
            origen_direccion=origen_direccion,
            origen_modalidad=origen_modalidad,
        )

    def distribuir(
        self,
        usuario_id: int,
        carrito_id: int,
        *,
        radio_km: int | None = None,
        max_paradas: int | None = None,
        preferencia: PreferenciaOptimizacion | None = None,
        origen_lat: float | None = None,
        origen_lon: float | None = None,
        origen_direccion: str | None = None,
        origen_modalidad: str | None = None,
    ) -> ResultadoDistribucion:
        configuracion_base = self._preferencias_repo.obtener_configuracion(usuario_id)

        configuracion = ConfiguracionOptimizacion(
            radio_km=radio_km if radio_km is not None else configuracion_base.radio_km,
            max_paradas=max_paradas if max_paradas is not None else configuracion_base.max_paradas,
            preferencia=preferencia if preferencia is not None else configuracion_base.preferencia,
            origen_lat=origen_lat if origen_lat is not None else configuracion_base.origen_lat,
            origen_lon=origen_lon if origen_lon is not None else configuracion_base.origen_lon,
            origen_direccion=(
                origen_direccion
                if origen_direccion is not None
                else configuracion_base.origen_direccion
            ),
            origen_modalidad=(
                origen_modalidad
                if origen_modalidad is not None
                else configuracion_base.origen_modalidad
            ),
            por_defecto_aplicado=configuracion_base.por_defecto_aplicado,
        )

        if configuracion.radio_km < 1 or configuracion.radio_km > 50:
            raise DistribucionConfigError("El radio_km debe estar entre 1 y 50.")

        items = self._distribucion_repo.obtener_items_carrito(usuario_id, carrito_id)
        if not items:
            raise DistribucionCarritoVacioError("El carrito está vacío.")

        ofertas = self._distribucion_repo.obtener_ofertas_candidatas(
            usuario_id,
            carrito_id,
            origen_lat=configuracion.origen_lat,
            origen_lon=configuracion.origen_lon,
            radio_km=configuracion.radio_km,
        )

        if not ofertas:
            ruteo = RuteoResultado(
                distancia_total_km=0.0,
                paradas=[
                    ParadaResultado(
                        orden=0,
                        sucursal_id=None,
                        nombre="Origen",
                        es_origen=True,
                        es_adicional=False,
                        distancia_desde_anterior_km=0.0,
                        productos=[],
                    )
                ],
            )
            return self._distribucion_repo.guardar_distribucion(
                usuario_id,
                carrito_id,
                configuracion=configuracion,
                asignaciones=[],
                items_no_asignados=[
                    ItemNoAsignadoResultado(
                        item_carrito_id=i.item_carrito_id,
                        producto_id=i.producto_id,
                        nombre_producto=i.nombre_producto,
                        cantidad=i.cantidad,
                        url_imagen=i.url_imagen,
                    )
                    for i in items
                ],
                ruteo=ruteo,
                costo_total_estimado=0.0,
                ahorro_estimado=None,
            )

        distancia_origen_sucursal_km = self._obtener_distancia_origen_sucursal_km(
            configuracion,
            self._ofertas_unicas_por_sucursal(ofertas),
        )
        asignaciones, items_no_asignados = self._motor.distribuir(
            EntradaOptimizacion(
                items=items,
                ofertas=ofertas,
                max_paradas=configuracion.max_paradas,
                preferencia=configuracion.preferencia,
                origen_lat=configuracion.origen_lat,
                origen_lon=configuracion.origen_lon,
                distancia_origen_sucursal_km=distancia_origen_sucursal_km,
            )
        )
        asignaciones = self._aplicar_distancia_origen_sucursal(
            asignaciones,
            distancia_origen_sucursal_km,
        )

        costo_total = round(sum(a.subtotal for a in asignaciones), 2)
        costo_referencia = self._distribucion_repo.calcular_costo_referencia(
            usuario_id,
            carrito_id,
            origen_lat=configuracion.origen_lat,
            origen_lon=configuracion.origen_lon,
            radio_km=configuracion.radio_km,
        )
        ahorro_estimado = None
        if costo_referencia is not None:
            ahorro_estimado = round(costo_referencia - costo_total, 2)

        ruteo = self._construir_ruteo(configuracion, asignaciones)
        return self._distribucion_repo.guardar_distribucion(
            usuario_id,
            carrito_id,
            configuracion=configuracion,
            asignaciones=asignaciones,
            items_no_asignados=items_no_asignados,
            ruteo=ruteo,
            costo_total_estimado=costo_total,
            ahorro_estimado=ahorro_estimado,
        )

    def obtener_distribucion_vigente(
        self,
        usuario_id: int,
        carrito_id: int,
    ) -> ResultadoDistribucion:
        distribucion = self._distribucion_repo.obtener_distribucion_vigente(usuario_id, carrito_id)
        if distribucion is None:
            raise DistribucionNoEncontradaError("No hay distribución vigente para ese carrito.")
        distancia_origen_sucursal_km = self._obtener_distancia_origen_sucursal_km(
            distribucion.configuracion,
            {
                asignacion.sucursal_id: (asignacion.latitud, asignacion.longitud)
                for asignacion in distribucion.asignaciones
            },
        )
        return replace(
            distribucion,
            asignaciones=self._aplicar_distancia_origen_sucursal(
                distribucion.asignaciones,
                distancia_origen_sucursal_km,
            ),
        )

    def _construir_ruteo(
        self,
        configuracion: ConfiguracionOptimizacion,
        asignaciones: list[AsignacionSucursalResultado],
    ) -> RuteoResultado:
        if not asignaciones:
            return RuteoResultado(
                distancia_total_km=0.0,
                paradas=[
                    ParadaResultado(
                        orden=0,
                        sucursal_id=None,
                        nombre="Origen",
                        es_origen=True,
                        es_adicional=False,
                        distancia_desde_anterior_km=0.0,
                        productos=[],
                    )
                ],
            )

        puntos = [(configuracion.origen_lat, configuracion.origen_lon)] + [
            (a.latitud, a.longitud) for a in asignaciones
        ]
        matriz = self._osrm_client.obtener_matriz_km(puntos)

        pendientes = set(range(1, len(puntos)))
        orden: list[int] = [0]
        actual = 0
        while pendientes:
            siguiente = min(pendientes, key=lambda idx: matriz[actual][idx])
            pendientes.remove(siguiente)
            orden.append(siguiente)
            actual = siguiente

        distancia_total = 0.0
        paradas: list[ParadaResultado] = [
            ParadaResultado(
                orden=0,
                sucursal_id=None,
                nombre="Origen",
                es_origen=True,
                es_adicional=False,
                distancia_desde_anterior_km=0.0,
                productos=[],
            )
        ]

        asignacion_por_indice = {indice + 1: asig for indice, asig in enumerate(asignaciones)}
        for orden_pos, idx in enumerate(orden[1:], start=1):
            previo = orden[orden_pos - 1]
            distancia = round(matriz[previo][idx], 3)
            distancia_total += distancia
            asignacion = asignacion_por_indice[idx]
            paradas.append(
                ParadaResultado(
                    orden=orden_pos,
                    sucursal_id=asignacion.sucursal_id,
                    nombre=asignacion.sucursal,
                    es_origen=False,
                    es_adicional=False,
                    distancia_desde_anterior_km=distancia,
                    productos=[item.nombre_producto for item in asignacion.items],
                )
        )

        return RuteoResultado(distancia_total_km=round(distancia_total, 3), paradas=paradas)

    def _obtener_distancia_origen_sucursal_km(
        self,
        configuracion: ConfiguracionOptimizacion,
        sucursales_por_id: dict[int, tuple[float, float]],
    ) -> dict[int, float]:
        if not sucursales_por_id:
            return {}

        sucursal_ids = list(sucursales_por_id)
        puntos = [(configuracion.origen_lat, configuracion.origen_lon)] + [
            sucursales_por_id[sucursal_id] for sucursal_id in sucursal_ids
        ]
        matriz = self._osrm_client.obtener_matriz_km(puntos)
        return {
            sucursal_id: matriz[0][indice + 1]
            for indice, sucursal_id in enumerate(sucursal_ids)
        }

    @staticmethod
    def _aplicar_distancia_origen_sucursal(
        asignaciones: list[AsignacionSucursalResultado],
        distancia_origen_sucursal_km: dict[int, float],
    ) -> list[AsignacionSucursalResultado]:
        return [
            replace(
                asignacion,
                distancia_km=distancia_origen_sucursal_km.get(asignacion.sucursal_id),
            )
            for asignacion in asignaciones
        ]

    @staticmethod
    def _ofertas_unicas_por_sucursal(
        ofertas: list[OfertaItemCandidata],
    ) -> dict[int, tuple[float, float]]:
        sucursales_unicas: dict[int, tuple[float, float]] = {}
        for oferta in sorted(
            ofertas,
            key=lambda oferta: (oferta.sucursal_id, oferta.item_carrito_id, oferta.precio_id),
        ):
            sucursales_unicas.setdefault(oferta.sucursal_id, (oferta.latitud, oferta.longitud))
        return sucursales_unicas


def nuevo_resultado_vacio(configuracion: ConfiguracionOptimizacion) -> ResultadoDistribucion:
    return ResultadoDistribucion(
        fecha_calculo=datetime.now(UTC),
        costo_total_estimado=0.0,
        ahorro_estimado=None,
        configuracion=configuracion,
        asignaciones=[],
        items_no_asignados=[],
        ruteo=RuteoResultado(distancia_total_km=0.0, paradas=[]),
    )
