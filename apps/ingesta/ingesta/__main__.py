"""Entrypoint del proceso de ingesta SEPA"""

from datetime import date
import logging
from pathlib import Path
import sys

import psycopg

from ingesta.ckan_client import CKANClient
from ingesta.config import load_config
from ingesta.downloader import collect_local_data_dirs, extract, fetch_zip
from ingesta.ean_validator import filtrar_productos_validos
from ingesta.lote_manager import LoteManager, build_error
from ingesta.parser import (
    ComercioCSV,
    DiscardedRow,
    ProductoCSV,
    SucursalCSV,
    iter_productos_chunks,
    parse_comercio,
    parse_sucursales,
)
from ingesta.repository import RepositorioSEPA

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingesta")


def main() -> int:
    total_steps = 5
    current_step = 0

    config = load_config()
    fecha_lote = _resolve_fecha_lote(config.sepa_fecha_lote)
    current_step += 1
    _log_progress(current_step, total_steps, "Configuración cargada")

    directorios_datos: list[Path] = []
    origen = "local"

    if config.sepa_portal_url.strip():
        origen = config.sepa_portal_url.strip()
        client = CKANClient(config.sepa_portal_url)
        resources = client.discover(config.ckan_dataset_id)
        logger.info("CKAN devolvió %s recursos ZIP minoristas", len(resources))
        resource = client.select_latest_resource(resources)
        if resource is None:
            logger.warning("No hay recursos ZIP minoristas en CKAN para dataset %s", config.ckan_dataset_id)
        else:
            if resource.fecha_publicacion is not None:
                fecha_lote = resource.fecha_publicacion
            logger.info(
                "Descargando último ZIP SEPA disponible (fecha_lote=%s): %s (%s)",
                fecha_lote.isoformat(),
                resource.description or resource.file_name,
                resource.url,
            )
            zip_path = fetch_zip(resource.url, config.sepa_download_dir)
            directorios_datos.extend(extract(zip_path))
    else:
        directorios_datos.extend(collect_local_data_dirs(Path(config.sepa_download_dir)))

    current_step += 1
    _log_progress(current_step, total_steps, "Datos fuente detectados")

    if not directorios_datos:
        logger.warning("No se encontraron directorios con comercio.csv/sucursales.csv/productos.csv")
        return 0

    directorios_unicos = sorted(set(directorios_datos))
    current_step += 1
    _log_progress(current_step, total_steps, "Directorios de datos listos")

    archivos_procesados = 0
    archivos_con_error = 0
    detalle_errores: list[dict[str, str]] = []

    with psycopg.connect(config.database_url) as conn:
        lote_manager = LoteManager(conn)
        repository = RepositorioSEPA(conn)

        # Carga batch idempotente: relajar fsync por commit (re-correr es seguro
        # por uq_* + ON CONFLICT). Recorta la latencia de los muchos commits por chunk.
        conn.execute("SET synchronous_commit = off")

        lote_id = lote_manager.begin(fecha_lote=fecha_lote, origen=origen)
        conn.commit()

        _preparar_indices_carga(conn)
        for index, directorio in enumerate(directorios_unicos, start=1):
            logger.info("Procesando directorio %s/%s: %s", index, len(directorios_unicos), directorio)

            try:
                comercios = parse_comercio(directorio / "comercio.csv")
                sucursales_result = parse_sucursales(directorio / "sucursales.csv")
                sucursales = sucursales_result.rows
            except Exception as error:
                archivos_con_error += 1
                detalle_errores.append(build_error(f"parse_{directorio.name}", error))
                continue

            _append_sucursales_discard_errors(directorio.name, sucursales_result.discarded, detalle_errores)

            id_comercio_to_db: dict[str, int] = {}
            bandera_ids: dict[str, int] = {}
            sucursal_ids: dict[tuple[str, str, str], int] = {}
            producto_ids: dict[str, int] = {}

            try:
                _upsert_comercios(repository, comercios, id_comercio_to_db)
                bandera_ids = _upsert_banderas(repository, comercios)
                conn.commit()
            except Exception as error:
                conn.rollback()
                logger.exception("Error en phase_1_comercios_%s", index)
                archivos_con_error += 1
                detalle_errores.append(build_error(f"phase_1_comercios_{directorio.name}", error))
                continue

            try:
                _upsert_sucursales(repository, sucursales, id_comercio_to_db, bandera_ids, sucursal_ids)
                conn.commit()
            except Exception as error:
                conn.rollback()
                logger.exception("Error en phase_2_sucursales_%s", index)
                archivos_con_error += 1
                detalle_errores.append(build_error(f"phase_2_sucursales_{directorio.name}", error))
                continue

            repository.delete_precios_por_sucursales(list(sucursal_ids.values()))
            conn.commit()

            productos_parseados = 0
            productos_validos_total = 0
            productos_descartados_total = 0
            huerfanos_producto = 0
            huerfanos_sucursal = 0
            directorio_ok = True

            try:
                for chunk_index, productos_chunk in enumerate(
                    iter_productos_chunks(directorio / "productos.csv", config.productos_chunk_size),
                    start=1,
                ):
                    productos_parseados += len(productos_chunk)
                    productos_validos, productos_descartados = filtrar_productos_validos(productos_chunk)
                    productos_validos_total += len(productos_validos)
                    productos_descartados_total += productos_descartados

                    if not productos_validos:
                        continue

                    try:
                        _upsert_productos(repository, productos_validos, producto_ids)
                        _, hprod, hsuc = repository.upsert_precios(
                            productos_validos, producto_ids, sucursal_ids, fecha_lote
                        )
                        huerfanos_producto += hprod
                        huerfanos_sucursal += hsuc
                        conn.commit()
                    except Exception as error:
                        conn.rollback()
                        logger.exception("Error en chunk de productos/precios %s_%s", index, chunk_index)
                        directorio_ok = False
                        detalle_errores.append(
                            build_error(
                                f"phase_3_4_productos_precios_{directorio.name}_chunk_{chunk_index}",
                                error,
                            )
                        )
                        break
            except Exception as error:
                conn.rollback()
                directorio_ok = False
                detalle_errores.append(build_error(f"parse_productos_{directorio.name}", error))

            logger.info(
                "Directorio %s: productos_parseados=%s validos=%s descartados_ean=%s "
                "huerfanos_producto=%s huerfanos_sucursal=%s",
                directorio.name,
                productos_parseados,
                productos_validos_total,
                productos_descartados_total,
                huerfanos_producto,
                huerfanos_sucursal,
            )

            if directorio_ok:
                archivos_procesados += 1
                if sucursales_result.discarded:
                    archivos_con_error += 1
            else:
                archivos_procesados += 1
                archivos_con_error += 1

            logger.info(
                "Progreso directorios %s/%s (procesados=%s, con_error=%s)",
                index,
                len(directorios_unicos),
                archivos_procesados,
                archivos_con_error,
            )

        _restaurar_indices_carga(conn)

        current_step += 1
        _log_progress(current_step, total_steps, "Carga incremental de directorios completada")

        estado = lote_manager.finalize(
            lote_id=lote_id,
            archivos_procesados=archivos_procesados,
            archivos_con_error=archivos_con_error,
            detalle_errores=detalle_errores,
        )
        conn.commit()

    logger.info(
        "Lote finalizado estado=%s archivos_procesados=%s archivos_con_error=%s",
        estado,
        archivos_procesados,
        archivos_con_error,
    )
    current_step += 1
    _log_progress(current_step, total_steps, "Ingesta finalizada")
    return 0 if estado in {"PROCESADO", "PARCIAL"} else 1


def _resolve_fecha_lote(fecha_lote_env: str) -> date:
    raw = fecha_lote_env.strip()
    if not raw:
        return date.today()
    return date.fromisoformat(raw)


def _upsert_comercios(
    repository: RepositorioSEPA,
    comercios: list[ComercioCSV],
    id_comercio_to_db: dict[str, int],
) -> None:
    ids_por_cuit = repository.upsert_comercios(comercios)
    for comercio in comercios:
        comercio_db_id = ids_por_cuit.get(comercio.cuit)
        if comercio_db_id is not None:
            id_comercio_to_db[comercio.id_comercio] = comercio_db_id


def _upsert_banderas(
    repository: RepositorioSEPA,
    comercios: list[ComercioCSV],
) -> dict[str, int]:
    return repository.upsert_banderas(comercios)


def _upsert_sucursales(
    repository: RepositorioSEPA,
    sucursales: list[SucursalCSV],
    id_comercio_to_db: dict[str, int],
    bandera_ids: dict[str, int],
    sucursal_ids: dict[tuple[str, str, str], int],
) -> None:
    sucursal_ids.update(repository.upsert_sucursales(sucursales, id_comercio_to_db, bandera_ids))


def _append_sucursales_discard_errors(
    directorio: str,
    discarded_rows: list[DiscardedRow],
    detalle_errores: list[dict[str, str]],
) -> None:
    if not discarded_rows:
        return

    razones: dict[str, int] = {}
    for discarded in discarded_rows:
        razones[discarded.reason] = razones.get(discarded.reason, 0) + 1
        message = (
            f"Línea {discarded.line_number} descartada ({discarded.reason}). "
            f"raw={discarded.raw_content}"
        )
        detalle_errores.append(
            build_error(
                f"phase_2_sucursales_{directorio}_line_{discarded.line_number}",
                ValueError(message),
            )
        )

    logger.warning(
        "Descartes en sucursales.csv directorio=%s total=%s por_motivo=%s",
        directorio,
        len(discarded_rows),
        razones,
    )


def _upsert_productos(
    repository: RepositorioSEPA,
    productos_validos: list[ProductoCSV],
    producto_ids: dict[str, int],
) -> None:
    # En SEPA un mismo EAN se repite en casi todas las sucursales; basta con
    # upsertear el producto la primera vez que aparece en el directorio.
    nuevos = [row for row in productos_validos if row.codigo_ean not in producto_ids]
    if not nuevos:
        return
    producto_ids.update(repository.upsert_productos(nuevos))


def _preparar_indices_carga(conn: psycopg.Connection) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute("DROP INDEX IF EXISTS ix_precio_producto_valor")
            cur.execute("DROP INDEX IF EXISTS ix_producto_nombre_trgm")
        conn.commit()
        logger.info("Índices secundarios eliminados para acelerar la carga")
    except Exception:
        conn.rollback()
        logger.exception("No se pudieron eliminar los índices secundarios; se continúa con los índices presentes")


def _restaurar_indices_carga(conn: psycopg.Connection) -> None:
    import time

    for attempt in range(3):
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS ix_precio_producto_valor ON precio (producto_id, valor)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS ix_producto_nombre_trgm"
                    " ON producto USING GIN (nombre gin_trgm_ops)"
                )
            conn.commit()
            logger.info("Índices secundarios reconstruidos")
            return
        except Exception:
            conn.rollback()
            if attempt < 2:
                logger.warning("Reintentando índices en %ds (intento %d/3)...", (attempt + 1) * 3, attempt + 2)
                time.sleep((attempt + 1) * 3)
            else:
                logger.exception("No se pudieron reconstruir los índices secundarios; recrearlos manualmente")


def _log_progress(current_step: int, total_steps: int, etapa: str) -> None:
    total = max(total_steps, 1)
    current = max(0, min(current_step, total))
    percent = int((current / total) * 100)
    bar_width = 20
    filled = int((current / total) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    logger.info("Progreso de ingesta %s/%s [%s] %s%% - %s", current, total, bar, percent, etapa)


if __name__ == "__main__":
    sys.exit(main())
