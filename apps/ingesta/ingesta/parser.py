from __future__ import annotations

import codecs
import csv
import logging
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TextIO

from ingesta.normalizadores import normalizar_provincia


logger = logging.getLogger("ingesta.parser")
_ID_PATTERN = re.compile(r"\d{1,20}")


@dataclass(frozen=True)
class ComercioCSV:
    id_comercio: str
    id_bandera: str
    cuit: str
    razon_social: str
    bandera_nombre: str


@dataclass(frozen=True)
class SucursalCSV:
    id_comercio: str
    id_bandera: str
    id_sucursal: str
    nombre: str
    direccion: str
    localidad: str
    provincia: str
    latitud: float | None
    longitud: float | None


@dataclass(frozen=True)
class ProductoCSV:
    id_comercio: str
    id_bandera: str
    id_sucursal: str
    codigo_ean: str
    productos_ean: str
    descripcion: str
    cantidad_presentacion: str
    unidad_medida_presentacion: str
    marca: str
    precio_lista: Decimal


@dataclass(frozen=True)
class DiscardedRow:
    line_number: int
    reason: str
    raw_content: str


@dataclass(frozen=True)
class ParseResult:
    rows: list[SucursalCSV]
    discarded: list[DiscardedRow]


@dataclass(frozen=True)
class _RawCSVRow:
    line_number: int
    values: dict[str, str]
    raw_content: str
    insufficient_columns: bool
    footer_detected: bool


def parse_comercio(path: Path) -> list[ComercioCSV]:
    rows: list[ComercioCSV] = []
    for row in _iter_data_rows(path):
        id_comercio = _get_required(row, "id_comercio")
        id_bandera = _get_required(row, "id_bandera")
        cuit = _get_required(row, "comercio_cuit")
        razon_social = _get_required(row, "comercio_razon_social")
        bandera_nombre = _get_required(row, "comercio_bandera_nombre")
        if None in (id_comercio, id_bandera, cuit, razon_social, bandera_nombre):
            continue
        rows.append(
            ComercioCSV(
                id_comercio=id_comercio,
                id_bandera=id_bandera,
                cuit=cuit,
                razon_social=razon_social,
                bandera_nombre=bandera_nombre,
            )
        )
    return rows


def parse_sucursales(path: Path) -> ParseResult:
    rows: list[SucursalCSV] = []
    discarded: list[DiscardedRow] = []

    for raw_row in _iter_raw_data_rows(path):
        if raw_row.footer_detected:
            discarded.append(
                DiscardedRow(
                    line_number=raw_row.line_number,
                    reason="footer_detected",
                    raw_content=_truncate_raw(raw_row.raw_content),
                )
            )
            continue

        if raw_row.insufficient_columns:
            discarded.append(
                DiscardedRow(
                    line_number=raw_row.line_number,
                    reason="insufficient_columns",
                    raw_content=_truncate_raw(raw_row.raw_content),
                )
            )
            continue

        row = raw_row.values
        id_comercio = _get_required(row, "id_comercio")
        id_bandera = _get_required(row, "id_bandera")
        id_sucursal = _get_required(row, "id_sucursal")
        nombre = _get_required(row, "sucursales_nombre")
        localidad = _get_required(row, "sucursales_localidad")
        provincia = _get_required(row, "sucursales_provincia")
        if None in (id_comercio, id_bandera, id_sucursal, nombre, localidad, provincia):
            discarded.append(
                DiscardedRow(
                    line_number=raw_row.line_number,
                    reason="invalid_data_type",
                    raw_content=_truncate_raw(raw_row.raw_content),
                )
            )
            continue

        if not (
            _ID_PATTERN.fullmatch(id_comercio)
            and _ID_PATTERN.fullmatch(id_bandera)
            and _ID_PATTERN.fullmatch(id_sucursal)
        ):
            discarded.append(
                DiscardedRow(
                    line_number=raw_row.line_number,
                    reason="invalid_data_type",
                    raw_content=_truncate_raw(raw_row.raw_content),
                )
            )
            continue

        provincia_normalizada = normalizar_provincia(provincia)
        if provincia_normalizada != provincia:
            logger.debug(
                "Provincia normalizada en línea %s: %r -> %r",
                raw_row.line_number,
                provincia,
                provincia_normalizada,
            )

        calle = row.get("sucursales_calle", "").strip()
        numero = row.get("sucursales_numero", "").strip()
        direccion = " ".join(v for v in [calle, numero] if v)
        rows.append(
            SucursalCSV(
                id_comercio=id_comercio,
                id_bandera=id_bandera,
                id_sucursal=id_sucursal,
                nombre=nombre,
                direccion=direccion,
                localidad=localidad,
                provincia=provincia_normalizada,
                latitud=_to_float(row.get("sucursales_latitud", "")),
                longitud=_to_float(row.get("sucursales_longitud", "")),
            )
        )
    return ParseResult(rows=rows, discarded=discarded)


def parse_productos(path: Path) -> list[ProductoCSV]:
    return list(iter_productos(path))


def iter_productos(path: Path) -> Iterator[ProductoCSV]:
    for row in _iter_data_rows(path):
        id_comercio = _get_required(row, "id_comercio")
        id_bandera = _get_required(row, "id_bandera")
        id_sucursal = _get_required(row, "id_sucursal")
        codigo_ean = _get_required(row, "id_producto")
        productos_ean = _get_required(row, "productos_ean")
        descripcion = _get_required(row, "productos_descripcion")
        cantidad = _get_required(row, "productos_cantidad_presentacion")
        unidad = _get_required(row, "productos_unidad_medida_presentacion")
        marca = _get_required(row, "productos_marca")
        if None in (
            id_comercio,
            id_bandera,
            id_sucursal,
            codigo_ean,
            productos_ean,
            descripcion,
            cantidad,
            unidad,
            marca,
        ):
            continue

        precio = _to_decimal(row.get("productos_precio_lista", ""))
        if precio is None or precio <= 0:
            continue

        yield ProductoCSV(
            id_comercio=id_comercio,
            id_bandera=id_bandera,
            id_sucursal=id_sucursal,
            codigo_ean=codigo_ean,
            productos_ean=productos_ean,
            descripcion=descripcion,
            cantidad_presentacion=cantidad,
            unidad_medida_presentacion=unidad,
            marca=marca,
            precio_lista=precio,
        )


def iter_productos_chunks(path: Path, chunk_size: int) -> Iterator[list[ProductoCSV]]:
    chunk: list[ProductoCSV] = []
    size = max(chunk_size, 1)
    for producto in iter_productos(path):
        chunk.append(producto)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _iter_data_rows(path: Path) -> Iterator[dict[str, str]]:
    for raw_row in _iter_raw_data_rows(path):
        if raw_row.footer_detected:
            continue
        if raw_row.insufficient_columns:
            continue
        if all((value or "").strip() == "" for value in raw_row.values.values()):
            continue
        if raw_row.values:
            yield raw_row.values


def _iter_raw_data_rows(path: Path) -> Iterator[_RawCSVRow]:
    with _open_with_encoding(path) as csv_file:
        reader = csv.reader(csv_file, delimiter="|")
        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError(f"CSV sin encabezado: {path}") from error

        # Las claves del encabezado se normalizan una sola vez, no por celda.
        keys = [_normalize_key(column) for column in header]
        num_keys = len(keys)

        for line_number, row in enumerate(reader, start=2):
            if not row:
                continue

            insufficient_columns = len(row) < num_keys
            normalized: dict[str, str] = {}
            raw_values: list[str] = []

            for idx, key in enumerate(keys):
                value = row[idx] if idx < len(row) else ""
                sanitized = _sanitize_text(value)
                normalized[key] = sanitized
                raw_values.append(sanitized)

            first_value = _sanitize_text(row[0]) if row else ""
            raw_content = "|".join(raw_values).strip()
            footer_detected = _is_footer_line(first_value) or _is_footer_line(raw_content)
            yield _RawCSVRow(
                line_number=line_number,
                values=normalized,
                raw_content=raw_content,
                insufficient_columns=insufficient_columns,
                footer_detected=footer_detected,
            )


def _open_with_encoding(path: Path) -> TextIO:
    # Lectura streaming: evita cargar productos.csv completo en memoria.
    # Se detecta el encoding leyendo en bloques (memoria constante) y luego se
    # abre el archivo en modo texto para que csv lo consuma línea por línea.
    encoding = _detectar_encoding(path)
    return path.open("r", encoding=encoding, errors="replace", newline="")


def _detectar_encoding(path: Path) -> str:
    # El corpus SEPA es UTF-8; si algún paquete viene en cp1252/latin-1 se detecta
    # acá sin cargar el archivo entero (decodificación incremental por bloques).
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        with path.open("rb") as raw:
            while True:
                block = raw.read(1 << 20)
                if not block:
                    decoder.decode(b"", final=True)
                    break
                decoder.decode(block)
        return "utf-8-sig"
    except UnicodeDecodeError:
        logger.warning("Fallback de encoding para %s: cp1252", path.name)
        return "cp1252"


def _normalize_key(value: str) -> str:
    return _sanitize_text(value).replace("\ufeff", "").strip()


def _sanitize_text(value: str) -> str:
    return value.replace("\x00", "")


def _get_required(row: dict[str, str], key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def _is_footer_line(value: str) -> bool:
    if not value.strip():
        return False

    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    compact = re.sub(r"[^a-z0-9\s]", " ", without_accents)
    tokens = [token for token in compact.split() if token]
    if len(tokens) < 2:
        return False

    first, second = tokens[0], tokens[1]
    if first == "ultima" and second.startswith("actualizaci"):
        return True

    mojibake_prefixes = {"aoltima", "uoltima", "aultima"}
    return first in mojibake_prefixes and second.startswith("actualizaci")


def _truncate_raw(value: str, max_length: int = 100) -> str:
    if len(value) <= max_length:
        return value
    return value[:max_length]


def _to_float(value: str) -> float | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_decimal(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
