from datetime import UTC, datetime
from typing import cast

import pytest

from app.domain.compra_guiada import (
    AlternativaFaltante,
    CompraGuiadaDetalle,
    CompraGuiadaPendienteError,
    EstadoCierre,
    EstadoItem,
    EstadoItemActualizable,
    ICompraGuiadaRepository,
    ItemCompraGuiada,
    ParadaCompraGuiada,
    TipoAlternativaFaltante,
)
from app.domain.servicios.compra_guiada import CompraGuiadaService


class _FakeCompraGuiadaRepo(ICompraGuiadaRepository):
    def __init__(self, compra: CompraGuiadaDetalle) -> None:
        self.compra = compra
        self.estado_cierre: EstadoCierre | None = None
        self.estado_item: EstadoItemActualizable | None = None
        self.alternativas: list[AlternativaFaltante] = []
        self.precio_aplicado: int | None = None

    def iniciar(self, usuario_id: int, carrito_distribuido_id: int) -> CompraGuiadaDetalle:
        _ = (usuario_id, carrito_distribuido_id)
        return self.compra

    def obtener(self, usuario_id: int, compra_id: int) -> CompraGuiadaDetalle | None:
        _ = (usuario_id, compra_id)
        return self.compra

    def actualizar_item(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
        estado: EstadoItemActualizable,
    ) -> CompraGuiadaDetalle | None:
        _ = (usuario_id, compra_id, progreso_item_id)
        self.estado_item = estado
        return _compra(estado=estado)

    def buscar_alternativas_faltante(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
    ) -> list[AlternativaFaltante]:
        _ = (usuario_id, compra_id, progreso_item_id)
        return self.alternativas

    def aplicar_alternativa_faltante(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
        precio_id: int,
    ) -> CompraGuiadaDetalle | None:
        _ = (usuario_id, compra_id, progreso_item_id)
        self.precio_aplicado = precio_id
        return _compra(estado="PENDIENTE", sucursal_id=11)

    def finalizar(
        self,
        usuario_id: int,
        compra_id: int,
        estado_cierre: EstadoCierre,
    ) -> CompraGuiadaDetalle | None:
        _ = (usuario_id, compra_id)
        self.estado_cierre = estado_cierre
        return self.compra


def test_actualizar_item_no_encontrado_busca_alternativas() -> None:
    repo = _FakeCompraGuiadaRepo(_compra())
    service = CompraGuiadaService(repo)

    actualizacion = service.actualizar_item(1, 2, 3, "NO_ENCONTRADO")

    assert repo.estado_item == "NO_ENCONTRADO"
    assert actualizacion.compra.paradas[0].items[0].estado == "NO_ENCONTRADO"
    assert actualizacion.resultado_alternativas is not None
    assert not actualizacion.resultado_alternativas.tiene_alternativas


def test_actualizar_item_no_encontrado_jamas_autoasigna() -> None:
    repo = _FakeCompraGuiadaRepo(_compra())
    repo.alternativas = [_alternativa(esta_en_recorrido=True)]
    service = CompraGuiadaService(repo)

    actualizacion = service.actualizar_item(1, 2, 3, "NO_ENCONTRADO")

    assert repo.precio_aplicado is None
    assert not actualizacion.aplicado_automaticamente
    assert actualizacion.resultado_alternativas is not None
    assert actualizacion.resultado_alternativas.tiene_alternativas
    assert actualizacion.resultado_alternativas.alternativas[0].esta_en_recorrido


def test_finalizar_rechaza_pendientes_sin_confirmacion() -> None:
    service = CompraGuiadaService(_FakeCompraGuiadaRepo(_compra()))

    with pytest.raises(CompraGuiadaPendienteError):
        service.finalizar(1, 2, confirmar_interrupcion=False)


def test_finalizar_interrumpe_si_hay_pendientes_y_confirmacion() -> None:
    repo = _FakeCompraGuiadaRepo(_compra())
    service = CompraGuiadaService(repo)

    service.finalizar(1, 2, confirmar_interrupcion=True)

    assert repo.estado_cierre == "INTERRUMPIDA"


def test_finalizar_completa_sin_pendientes() -> None:
    repo = _FakeCompraGuiadaRepo(_compra(estado="CONSEGUIDO"))
    service = CompraGuiadaService(repo)

    service.finalizar(1, 2)

    assert repo.estado_cierre == "COMPLETADA"


def _compra(estado: str = "PENDIENTE", sucursal_id: int = 10) -> CompraGuiadaDetalle:
    return CompraGuiadaDetalle(
        id=2,
        carrito_distribuido_id=9,
        fecha_inicio=datetime(2026, 1, 1, tzinfo=UTC),
        fecha_cierre=None,
        estado_cierre=None,
        paradas=[
            ParadaCompraGuiada(
                orden=1,
                sucursal_id=sucursal_id,
                sucursal="Sucursal Centro",
                comercio="Comercio",
                direccion=None,
                localidad=None,
                provincia=None,
                distancia_desde_anterior_km=1.2,
                bandera_nombre=None,
                bandera_logo_url=None,
                subtotal=100.0,
                es_adicional=False,
                items=[
                    ItemCompraGuiada(
                        progreso_item_id=3,
                        item_asignado_id=4,
                        item_carrito_id=5,
                        producto_id=6,
                        nombre_producto="Leche",
                        cantidad=1,
                        precio_unitario=100.0,
                        subtotal=100.0,
                        estado=cast(EstadoItem, estado),
                    )
                ],
            )
        ],
    )


def _alternativa(
    esta_en_recorrido: bool,
    tipo: str = "MISMO_PRODUCTO",
) -> AlternativaFaltante:
    return AlternativaFaltante(
        tipo=cast(TipoAlternativaFaltante, tipo),
        precio_id=77,
        producto_id=6,
        nombre_producto="Leche",
        url_imagen=None,
        sucursal_id=11,
        sucursal="Sucursal Norte",
        comercio="Comercio",
        direccion=None,
        localidad=None,
        provincia=None,
        bandera_nombre=None,
        bandera_logo_url=None,
        precio_unitario=105.0,
        subtotal=105.0,
        diferencia_precio=5.0,
        distancia_km=1.5,
        esta_en_recorrido=esta_en_recorrido,
        requiere_nueva_parada=not esta_en_recorrido,
        confianza="ALTA",
        motivo="Mismo producto en una parada ya recomendada.",
    )
