from collections import defaultdict

from app.domain.optimizacion import (
    AsignacionSucursalResultado,
    EntradaOptimizacion,
    IMotorOptimizacion,
    ItemAsignadoResultado,
    ItemCarritoOptimizacion,
    ItemNoAsignadoResultado,
    OfertaItemCandidata,
    PreferenciaOptimizacion,
)

try:
    from ortools.sat.python import cp_model
except ImportError:  
    cp_model = None

_ESCALA = 1_000_000
# Penalización por ítem no asignado, en unidades normalizadas.
_PENAL_NO_ASIGNAR = 100.0

# Pesos (costo, distancia) por preferencia.
_EPSILON = 1e-3
_PESOS: dict[PreferenciaOptimizacion, tuple[float, float]] = {
    "MENOR_PRECIO": (1.0, _EPSILON),
    "MENOR_DESPLAZAMIENTO": (_EPSILON, 1.0),
    "BALANCEADO": (0.5, 0.5),
}

# Centinela determinístico para sucursales sin distancia calculada.
_DIST_SIN_DATO = 1e12
# Penalización explícita para BALANCEADO cuando una sucursal no tiene distancia.
# Debe dominar cualquier diferencia normalizada de costo/distancia, pero quedar muy
# por debajo de no asignar para no perder cobertura cuando no hay alternativa.
_PENAL_DISTANCIA_SIN_DATO = 2.0


def _costo_total_oferta(
    oferta: OfertaItemCandidata,
    item: ItemCarritoOptimizacion,
) -> float:
    return oferta.precio_unitario * item.cantidad


def _distancia_sucursal(
    entrada: EntradaOptimizacion,
    sucursal_id: int,
) -> float:
    return entrada.distancia_origen_sucursal_km.get(sucursal_id, _DIST_SIN_DATO)


def _distancia_sin_dato(
    entrada: EntradaOptimizacion,
    sucursal_id: int,
) -> bool:
    return sucursal_id not in entrada.distancia_origen_sucursal_km


def _normalizar(valor: float, minimo: float, maximo: float) -> float:
    if maximo <= minimo:
        return 0.5
    return (valor - minimo) / (maximo - minimo)


def _clave_greedy(
    oferta: OfertaItemCandidata,
    item: ItemCarritoOptimizacion,
    entrada: EntradaOptimizacion,
    *,
    costo_minimo: float | None = None,
    costo_maximo: float | None = None,
    distancia_minima: float | None = None,
    distancia_maxima: float | None = None,
) -> tuple[float, ...]:
    costo = _costo_total_oferta(oferta, item)
    distancia = _distancia_sucursal(entrada, oferta.sucursal_id)

    if entrada.preferencia == "MENOR_PRECIO":
        return (costo, distancia)

    if entrada.preferencia == "MENOR_DESPLAZAMIENTO":
        return (distancia, costo)

    assert costo_minimo is not None
    assert costo_maximo is not None
    assert distancia_minima is not None
    assert distancia_maxima is not None

    peso_costo, peso_distancia = _PESOS["BALANCEADO"]
    score = (
        peso_costo * _normalizar(costo, costo_minimo, costo_maximo)
        + peso_distancia * _normalizar(distancia, distancia_minima, distancia_maxima)
    )
    return (float(_distancia_sin_dato(entrada, oferta.sucursal_id)), score, costo, distancia)


def _ordenar_candidatas_greedy(
    candidatas: list[OfertaItemCandidata],
    item: ItemCarritoOptimizacion,
    entrada: EntradaOptimizacion,
) -> list[OfertaItemCandidata]:
    if not candidatas:
        return []

    if entrada.preferencia == "BALANCEADO":
        costos = [_costo_total_oferta(oferta, item) for oferta in candidatas]
        distancias = [_distancia_sucursal(entrada, oferta.sucursal_id) for oferta in candidatas]
        costo_minimo = min(costos)
        costo_maximo = max(costos)
        distancia_minima = min(distancias)
        distancia_maxima = max(distancias)

        return sorted(
            candidatas,
            key=lambda oferta: _clave_greedy(
                oferta,
                item,
                entrada,
                costo_minimo=costo_minimo,
                costo_maximo=costo_maximo,
                distancia_minima=distancia_minima,
                distancia_maxima=distancia_maxima,
            ),
        )

    return sorted(
        candidatas,
        key=lambda oferta: _clave_greedy(oferta, item, entrada),
    )


class MotorOrTools(IMotorOptimizacion):
    def __init__(self, *, timeout_seconds: float = 3.5) -> None:
        self._timeout_seconds = timeout_seconds

    def distribuir(
        self, entrada: EntradaOptimizacion
    ) -> tuple[
        list[AsignacionSucursalResultado],
        list[ItemNoAsignadoResultado],
    ]:
        if cp_model is None:
            return self._resolver_greedy(entrada)

        asignaciones = self._resolver_cp_sat(entrada)
        if asignaciones is None:
            return self._resolver_greedy(entrada)
        return asignaciones

    def _resolver_cp_sat(
        self,
        entrada: EntradaOptimizacion,
    ) -> tuple[list[AsignacionSucursalResultado], list[ItemNoAsignadoResultado]] | None:
        if not entrada.ofertas:
            return None

        item_por_id = {item.item_carrito_id: item for item in entrada.items}
        ofertas_por_item: dict[int, list[int]] = defaultdict(list)
        for idx, oferta in enumerate(entrada.ofertas):
            ofertas_por_item[oferta.item_carrito_id].append(idx)

        distancia_por_sucursal = {
            oferta.sucursal_id: _distancia_sucursal(entrada, oferta.sucursal_id)
            for oferta in sorted(
                entrada.ofertas,
                key=lambda oferta: (oferta.sucursal_id, oferta.item_carrito_id, oferta.precio_id),
            )
        }

        model = cp_model.CpModel()
        oferta_vars: dict[int, cp_model.IntVar] = {
            idx: model.new_bool_var(f"oferta_{idx}") for idx in range(len(entrada.ofertas))
        }
        sucursal_vars: dict[int, cp_model.IntVar] = {
            sucursal_id: model.new_bool_var(f"sucursal_{sucursal_id}")
            for sucursal_id in distancia_por_sucursal
        }
        no_asignar_vars: dict[int, cp_model.IntVar] = {
            item.item_carrito_id: model.new_bool_var(f"no_asignar_{item.item_carrito_id}")
            for item in entrada.items
        }

        for item in entrada.items:
            vars_item = [oferta_vars[idx] for idx in ofertas_por_item.get(item.item_carrito_id, [])]
            model.add(sum(vars_item) + no_asignar_vars[item.item_carrito_id] == 1)

        for idx, oferta in enumerate(entrada.ofertas):
            model.add(oferta_vars[idx] <= sucursal_vars[oferta.sucursal_id])

        model.add(sum(sucursal_vars.values()) <= entrada.max_paradas)

        w_costo, w_dist = _PESOS[entrada.preferencia]

        costo_max = 0.0
        for item in entrada.items:
            precios = [
                entrada.ofertas[idx].precio_unitario
                for idx in ofertas_por_item.get(item.item_carrito_id, [])
            ]
            if precios:
                costo_max += max(precios) * item.cantidad
        costo_max = max(costo_max, 1.0)

        distancia_max = max(distancia_por_sucursal.values(), default=0.0)
        distancia_norm = max(distancia_max * entrada.max_paradas, 1.0)

        objetivo = []
        for idx, oferta in enumerate(entrada.ofertas):
            cantidad = item_por_id[oferta.item_carrito_id].cantidad
            costo_real = oferta.precio_unitario * cantidad
            coef = w_costo * costo_real / costo_max
            objetivo.append(int(round(coef * _ESCALA)) * oferta_vars[idx])
        for sucursal_id, sucursal_var in sucursal_vars.items():
            coef = w_dist * distancia_por_sucursal[sucursal_id] / distancia_norm
            if entrada.preferencia == "BALANCEADO" and _distancia_sin_dato(
                entrada,
                sucursal_id,
            ):
                coef += _PENAL_DISTANCIA_SIN_DATO
            objetivo.append(int(round(coef * _ESCALA)) * sucursal_var)
        for no_asignar_var in no_asignar_vars.values():
            objetivo.append(int(round(_PENAL_NO_ASIGNAR * _ESCALA)) * no_asignar_var)
        model.minimize(sum(objetivo))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self._timeout_seconds
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        elegidas = [
            entrada.ofertas[idx]
            for idx, var in oferta_vars.items()
            if solver.value(var) == 1
        ]
        return _agrupar_asignaciones(entrada.items, elegidas)

    def _resolver_greedy(
        self,
        entrada: EntradaOptimizacion,
    ) -> tuple[list[AsignacionSucursalResultado], list[ItemNoAsignadoResultado]]:
        ofertas_por_item: dict[int, list[OfertaItemCandidata]] = defaultdict(list)
        for oferta in entrada.ofertas:
            ofertas_por_item[oferta.item_carrito_id].append(oferta)

        elegidas: list[OfertaItemCandidata] = []
        sucursales_usadas: set[int] = set()

        for item in entrada.items:
            candidatas = _ordenar_candidatas_greedy(
                ofertas_por_item.get(item.item_carrito_id, []),
                item,
                entrada,
            )
            if not candidatas:
                continue

            en_uso = [oferta for oferta in candidatas if oferta.sucursal_id in sucursales_usadas]
            elegida: OfertaItemCandidata | None
            if en_uso:
                elegida = en_uso[0]
            elif len(sucursales_usadas) < entrada.max_paradas:
                elegida = candidatas[0]
                sucursales_usadas.add(elegida.sucursal_id)
            else:
                elegida = candidatas[0] if candidatas[0].sucursal_id in sucursales_usadas else None

            if elegida is not None:
                elegidas.append(elegida)

        return _agrupar_asignaciones(entrada.items, elegidas)


def _agrupar_asignaciones(
    items: list[ItemCarritoOptimizacion],
    elegidas: list[OfertaItemCandidata],
) -> tuple[list[AsignacionSucursalResultado], list[ItemNoAsignadoResultado]]:
    item_por_id = {item.item_carrito_id: item for item in items}

    items_por_sucursal: dict[int, list[ItemAsignadoResultado]] = defaultdict(list)
    meta_sucursal: dict[int, OfertaItemCandidata] = {}

    for oferta in elegidas:
        item = item_por_id.get(oferta.item_carrito_id)
        if item is None:
            continue
        subtotal = round(oferta.precio_unitario * item.cantidad, 2)
        items_por_sucursal[oferta.sucursal_id].append(
            ItemAsignadoResultado(
                item_carrito_id=item.item_carrito_id,
                producto_id=item.producto_id,
                nombre_producto=item.nombre_producto,
                cantidad=item.cantidad,
                precio_id=oferta.precio_id,
                precio_unitario=round(oferta.precio_unitario, 2),
                subtotal=subtotal,
                url_imagen=item.url_imagen,
            )
        )
        meta_sucursal[oferta.sucursal_id] = oferta

    asignaciones: list[AsignacionSucursalResultado] = []
    for sucursal_id, items_asignados in items_por_sucursal.items():
        meta = meta_sucursal[sucursal_id]
        subtotal = round(sum(item.subtotal for item in items_asignados), 2)
        asignaciones.append(
            AsignacionSucursalResultado(
                sucursal_id=sucursal_id,
                sucursal=meta.sucursal,
                comercio=meta.comercio,
                direccion=meta.direccion,
                localidad=meta.localidad,
                provincia=meta.provincia,
                latitud=meta.latitud,
                longitud=meta.longitud,
                distancia_km=meta.distancia_km,
                bandera_nombre=meta.bandera_nombre,
                bandera_logo_url=meta.bandera_logo_url,
                subtotal=subtotal,
                items=items_asignados,
            )
        )

    asignados = {item.item_carrito_id for asig in asignaciones for item in asig.items}
    no_asignados = [
        ItemNoAsignadoResultado(
            item_carrito_id=item.item_carrito_id,
            producto_id=item.producto_id,
            nombre_producto=item.nombre_producto,
            cantidad=item.cantidad,
            url_imagen=item.url_imagen,
        )
        for item in items
        if item.item_carrito_id not in asignados
    ]
    return sorted(asignaciones, key=lambda a: a.subtotal, reverse=True), no_asignados
