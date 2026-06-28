from app.domain.compra_guiada import (
    CompraGuiadaDetalle,
    CompraGuiadaNotFoundError,
    CompraGuiadaPendienteError,
    CompraGuiadaValidationError,
    EstadoItemActualizable,
    ICompraGuiadaRepository,
)


class CompraGuiadaService:
    def __init__(self, compra_repo: ICompraGuiadaRepository) -> None:
        self._compra_repo = compra_repo

    def iniciar(self, usuario_id: int, carrito_distribuido_id: int) -> CompraGuiadaDetalle:
        return self._compra_repo.iniciar(usuario_id, carrito_distribuido_id)

    def obtener(self, usuario_id: int, compra_id: int) -> CompraGuiadaDetalle:
        compra = self._compra_repo.obtener(usuario_id, compra_id)
        if compra is None:
            raise CompraGuiadaNotFoundError("No se encontró la compra guiada.")
        return compra

    def actualizar_item(
        self,
        usuario_id: int,
        compra_id: int,
        progreso_item_id: int,
        estado: EstadoItemActualizable,
    ) -> CompraGuiadaDetalle:
        compra = self._compra_repo.actualizar_item(
            usuario_id,
            compra_id,
            progreso_item_id,
            estado,
        )
        if compra is None:
            raise CompraGuiadaNotFoundError("No se encontró el progreso indicado.")
        return compra

    def finalizar(
        self,
        usuario_id: int,
        compra_id: int,
        *,
        confirmar_interrupcion: bool = False,
    ) -> CompraGuiadaDetalle:
        compra = self.obtener(usuario_id, compra_id)
        pendientes = sum(
            1
            for parada in compra.paradas
            for item in parada.items
            if item.estado == "PENDIENTE"
        )
        if pendientes > 0 and not confirmar_interrupcion:
            raise CompraGuiadaPendienteError(
                "La compra tiene productos pendientes. Confirmá la interrupción para finalizar."
            )

        estado_cierre = "INTERRUMPIDA" if pendientes > 0 else "COMPLETADA"
        finalizada = self._compra_repo.finalizar(usuario_id, compra_id, estado_cierre)
        if finalizada is None:
            raise CompraGuiadaValidationError("No se pudo finalizar la compra guiada.")
        return finalizada
