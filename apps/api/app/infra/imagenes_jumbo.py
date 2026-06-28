"""Clientes para obtener URLs de imágenes de productos desde APIs externas.
"""

from __future__ import annotations

import asyncio
import re
import sys
import time
from typing import Any, Callable

import httpx
import psycopg
from psycopg.rows import dict_row

DEFAULT_CONCURRENCY = 25
DB_FLUSH_INTERVAL = 50
REQUEST_TIMEOUT = 10.0

# ── URL templates ──────────────────────────────────────────────────────────

VTEX_PATH = (
    "/api/catalog_system/pub/products/search/"
    "?fq=alternateIds_Ean:{ean}"
)
PRECIOS_CLAROS_URL = "https://imagenes.preciosclaros.gob.ar/productos/{ean}.jpg"
PRICELY_PRODUCT_URL = "https://pricely.ar/product/{ean}"

# Regex para extraer la URL de imagen del HTML de Pricely.
# El patrón captura {folder}/{ean}.webp desde cualquier URL de images.pricely.ar.
_PRICELY_IMAGE_RE = re.compile(
    rb'https://images\.pricely\.ar/images/(\d+/\d+\.(?:webp|jpg|png|jpeg))'
)
COTO_CONSTRUCTOR_URL = (
    "https://ac.cnstrc.com/search/{ean}"
    "?c=cio_client_id&key=key_r6xzz4IAoTWcipni&i=tfg_backfill"
)

# ── Fetchers ───────────────────────────────────────────────────────────────


def _vtex_factory(base_url: str) -> Callable:
    """Crea un fetcher VTEX para una URL base (ej. https://www.jumbo.com.ar)."""
    url_template = base_url.rstrip("/") + VTEX_PATH

    async def _fetch(ean: str, client: httpx.AsyncClient) -> str | None:
        url = url_template.format(ean=ean)
        try:
            response = await client.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                return None
            data: list[dict[str, Any]] = response.json()
            if not data or not isinstance(data, list):
                return None
            items: list[dict[str, Any]] = data[0].get("items", [])
            if not items:
                return None
            images: list[dict[str, str]] = items[0].get("images", [])
            if not images:
                return None
            return images[0].get("imageUrl")
        except Exception:
            return None

    return _fetch


async def _fetch_imagen_precios_claros(ean: str, client: httpx.AsyncClient) -> str | None:
    url = PRECIOS_CLAROS_URL.format(ean=ean)
    try:
        response = await client.head(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return url
        return None
    except Exception:
        return None


async def _fetch_imagen_coto(ean: str, client: httpx.AsyncClient) -> str | None:
    url = COTO_CONSTRUCTOR_URL.format(ean=ean)
    try:
        response = await client.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return None
        data: dict[str, Any] = response.json()
        results: list[dict[str, Any]] = data.get("response", {}).get("results", [])
        if not results:
            return None
        image_url = results[0].get("data", {}).get("image_url")
        return image_url or None
    except Exception:
        return None


async def _fetch_imagen_pricely(ean: str, client: httpx.AsyncClient) -> str | None:
    """Busca la imagen en la página de producto de Pricely vía streaming.

    Lee el HTML en chunks y corta ni bien encuentra el og:image
    (típicamente en los primeros 5 KB), evitando descargar la página completa.
    """
    url = PRICELY_PRODUCT_URL.format(ean=ean)
    try:
        async with client.stream("GET", url, timeout=REQUEST_TIMEOUT) as response:
            if response.status_code != 200:
                return None
            accumulated = b""
            async for chunk in response.aiter_bytes(4096):
                accumulated += chunk
                m = _PRICELY_IMAGE_RE.search(accumulated)
                if m:
                    return m.group(0).decode()
                if len(accumulated) > 32768:
                    return None
        return None
    except Exception:
        return None


_FETCHERS: dict[str, Callable] = {
    "jumbo": _vtex_factory("https://www.jumbo.com.ar"),
    "carrefour": _vtex_factory("https://www.carrefour.com.ar"),
    "farmaplus": _vtex_factory("https://www.farmaplus.com.ar"),
    "dia": _vtex_factory("https://diaonline.supermercadosdia.com.ar"),
    "farmacity": _vtex_factory("https://www.farmacity.com"),
    "masonline": _vtex_factory("https://www.masonline.com.ar"),
    "farmalife": _vtex_factory("https://www.farmalife.com.ar"),
    "josimar": _vtex_factory("https://www.josimar.com.ar"),
    "comodinencasa": _vtex_factory("https://www.comodinencasa.com.ar"),
    "precios_claros": _fetch_imagen_precios_claros,
    "pricely": _fetch_imagen_pricely,
    "coto": _fetch_imagen_coto,
}

# ── Backfill engine ────────────────────────────────────────────────────────


async def _backfill(
    db_url: str,
    *,
    source: str,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, int]:
    fetch = _FETCHERS[source]

    conn = psycopg.connect(db_url, row_factory=dict_row)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, codigo_ean
                FROM producto
                WHERE url_imagen IS NULL
                  AND (marca IS NULL
                       OR LOWER(marca) NOT IN ('sin marca', 'generico', 's/d'))
                """
            )
            productos = cur.fetchall()
    finally:
        conn.close()

    total = len(productos)
    if total == 0:
        print("No hay productos sin imagen. Nada que hacer.")
        return {"total": 0, "actualizados": 0, "fallidos": 0}

    print(f"Fuente: {source}")
    print(f"Productos sin imagen: {total}")
    print(f"Concurrencia HTTP: {concurrency} | Flush DB cada: {DB_FLUSH_INTERVAL}")

    actualizados = 0
    fallidos = 0
    ultimo_ean = ""
    pendientes: list[tuple[int, str]] = []
    lock = asyncio.Lock()
    t0 = time.monotonic()

    async def _flush() -> None:
        nonlocal actualizados
        if not pendientes:
            return
        conn_write = psycopg.connect(db_url)
        try:
            with conn_write.cursor() as cur:
                cur.executemany(
                    "UPDATE producto SET url_imagen = %s WHERE id = %s",
                    [(url, pid) for pid, url in pendientes],
                )
            conn_write.commit()
        finally:
            conn_write.close()
        actualizados += len(pendientes)
        pendientes.clear()

    async def _mostrar_progreso() -> None:
        nonlocal ultimo_ean
        procesados = actualizados + fallidos + len(pendientes)
        elapsed = time.monotonic() - t0
        rps = procesados / elapsed if elapsed > 0 else 0
        print(
            f"\r  {procesados}/{total} | ✓:{actualizados + len(pendientes)}"
            f"  ✗:{fallidos} | {rps:.0f} req/s"
            f" | {ultimo_ean}    ",
            end="",
            flush=True,
        )

    async def _procesar(producto: dict[str, Any], client: httpx.AsyncClient) -> None:
        nonlocal fallidos, ultimo_ean
        url_imagen = await fetch(producto["codigo_ean"], client)
        async with lock:
            ultimo_ean = producto["codigo_ean"]
            if url_imagen:
                pendientes.append((producto["id"], url_imagen))
                if len(pendientes) >= DB_FLUSH_INTERVAL:
                    await _flush()
            else:
                fallidos += 1
            procesados = actualizados + fallidos + len(pendientes)
            if procesados % 10 == 0 or procesados == 1:
                await _mostrar_progreso()

    sem = asyncio.Semaphore(concurrency)

    async def _con_semaforo(producto: dict[str, Any], client: httpx.AsyncClient) -> None:
        async with sem:
            await _procesar(producto, client)

    limits = httpx.Limits(
        max_keepalive_connections=concurrency,
        max_connections=concurrency,
        keepalive_expiry=30,
    )
    async with httpx.AsyncClient(limits=limits) as client:
        tareas = [_con_semaforo(p, client) for p in productos]
        await asyncio.gather(*tareas)

    if pendientes:
        await _flush()
    await _mostrar_progreso()
    print()

    elapsed = time.monotonic() - t0
    print(f"  Total: {total} | ✓ {actualizados} | ✗ {fallidos}")
    print(f"  Tiempo: {elapsed:.1f}s | {total / elapsed:.0f} req/s")
    return {"total": total, "actualizados": actualizados, "fallidos": fallidos}


def backfill_sync(
    db_url: str,
    *,
    source: str = "jumbo",
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict[str, int]:
    return asyncio.run(_backfill(db_url, source=source, concurrency=concurrency))


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Backfill de imágenes de productos")
    parser.add_argument(
        "--source",
        choices=list(_FETCHERS),
        default="jumbo",
        help="Fuente de imágenes (default: jumbo)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Requests HTTP simultáneos (default: {DEFAULT_CONCURRENCY})",
    )
    args = parser.parse_args()

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://tfg:tfg@localhost:5432/tfg",
    )
    resultado = backfill_sync(db_url, source=args.source, concurrency=args.concurrency)
    print(f"\nResultado: {resultado}")
    sys.exit(0 if resultado["fallidos"] == 0 else 1)