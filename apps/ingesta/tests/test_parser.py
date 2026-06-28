from pathlib import Path

import pytest

from ingesta.parser import (
    _get_required,
    iter_productos_chunks,
    parse_comercio,
    parse_productos,
    parse_sucursales,
)


FIXTURE_BASE = Path(__file__).resolve().parents[3] / "SEPA" / "sepa_1_comercio-sepa-12_2026-04-14_09-05-11"


def test_parse_comercio_fixture() -> None:
    rows = parse_comercio(FIXTURE_BASE / "comercio.csv")
    assert len(rows) == 1
    assert rows[0].id_comercio == "12"
    assert rows[0].cuit == "30548083156"


def test_parse_sucursales_fixture() -> None:
    result = parse_sucursales(FIXTURE_BASE / "sucursales.csv")
    assert result.rows
    assert result.rows[0].id_sucursal
    assert result.rows[0].direccion
    assert len(result.discarded) == 1
    assert result.discarded[0].reason == "footer_detected"


def test_parse_productos_pipe_delimited(tmp_path: Path) -> None:
    csv_path = tmp_path / "productos.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|id_producto|productos_ean|productos_descripcion|productos_cantidad_presentacion|productos_unidad_medida_presentacion|productos_marca|productos_precio_lista|productos_precio_referencia|productos_cantidad_referencia|productos_unidad_medida_referencia|productos_precio_unitario_promo1|productos_leyenda_promo1|productos_precio_unitario_promo2|productos_leyenda_promo2\n"
        "12|1|2|7790742363008|1|LECHE|1|ltr|MARCA|2500.5|2500.5|1|ltr||||\n",
        encoding="utf-8",
    )

    rows = parse_productos(csv_path)

    assert len(rows) == 1
    assert rows[0].codigo_ean.isdigit()
    assert rows[0].precio_lista > 0


def test_parse_productos_descarta_precio_cero(tmp_path: Path) -> None:
    csv_path = tmp_path / "productos.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|id_producto|productos_ean|productos_descripcion|productos_cantidad_presentacion|productos_unidad_medida_presentacion|productos_marca|productos_precio_lista\n"
        "12|1|2|7790742363008|1|LECHE|1|ltr|MARCA|0\n"
        "12|1|2|7790742363009|1|YOGUR|1|u|MARCA|1800\n",
        encoding="utf-8",
    )

    rows = parse_productos(csv_path)

    assert len(rows) == 1
    assert rows[0].codigo_ean == "7790742363009"


def test_parse_sucursales_ignora_footer_con_acentos(tmp_path: Path) -> None:
    csv_path = tmp_path / "sucursales.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|sucursales_nombre|sucursales_tipo|sucursales_calle|sucursales_numero|sucursales_latitud|sucursales_longitud|sucursales_observaciones|sucursales_barrio|sucursales_codigo_postal|sucursales_localidad|sucursales_provincia\n"
        "23|1|6201|Dialogos|Autoservicio|Av. Mitre|852|-34.1629|-58.9648|||B2804AQR|Campana|AR-B\n"
        "Última actualización: 2026-04-14T03:06:52-03:00\n",
        encoding="utf-8",
    )

    result = parse_sucursales(csv_path)

    assert len(result.rows) == 1
    assert result.rows[0].id_comercio == "23"
    assert len(result.discarded) == 1
    assert result.discarded[0].reason == "footer_detected"


@pytest.mark.parametrize(
    "footer_line",
    [
        "Última actualización: 2026-04-14T03:06:52-03:00",
        "Ãºltima actualizaciÃ³n: 2026-04-14T03:06:52-03:00",
        "©®™ Última actualización: 2026-04-14T03:06:52-03:00",
    ],
)
def test_parse_sucursales_descarta_footer_mojibake(tmp_path: Path, footer_line: str) -> None:
    csv_path = tmp_path / "sucursales.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|sucursales_nombre|sucursales_tipo|sucursales_calle|sucursales_numero|sucursales_latitud|sucursales_longitud|sucursales_observaciones|sucursales_barrio|sucursales_codigo_postal|sucursales_localidad|sucursales_provincia\n"
        "23|1|6201|Dialogos|Autoservicio|Av. Mitre|852|-34.1629|-58.9648|||B2804AQR|Campana|AR-B\n"
        f"{footer_line}\n",
        encoding="utf-8",
    )

    result = parse_sucursales(csv_path)

    assert len(result.rows) == 1
    assert len(result.discarded) == 1
    assert result.discarded[0].reason == "footer_detected"


def test_parse_sucursales_descarta_ids_invalidos(tmp_path: Path) -> None:
    csv_path = tmp_path / "sucursales.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|sucursales_nombre|sucursales_tipo|sucursales_calle|sucursales_numero|sucursales_latitud|sucursales_longitud|sucursales_observaciones|sucursales_barrio|sucursales_codigo_postal|sucursales_localidad|sucursales_provincia\n"
        "23|1|6201|Dialogos|Autoservicio|Av. Mitre|852|-34.1629|-58.9648|||B2804AQR|Campana|AR-B\n"
        "ABC|1|6201|Invalida|Autoservicio|Av. Mitre|852|-34.1629|-58.9648|||B2804AQR|Campana|AR-B\n",
        encoding="utf-8",
    )

    result = parse_sucursales(csv_path)

    assert len(result.rows) == 1
    assert len(result.discarded) == 1
    assert result.discarded[0].reason == "invalid_data_type"


def test_parse_sucursales_descartes_estables_en_reproceso(tmp_path: Path) -> None:
    csv_path = tmp_path / "sucursales.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|sucursales_nombre|sucursales_tipo|sucursales_calle|sucursales_numero|sucursales_latitud|sucursales_longitud|sucursales_observaciones|sucursales_barrio|sucursales_codigo_postal|sucursales_localidad|sucursales_provincia\n"
        "23|1|6201|Dialogos|Autoservicio|Av. Mitre|852|-34.1629|-58.9648|||B2804AQR|Campana|AR-B\n"
        "ABC|1|6201|Invalida|Autoservicio|Av. Mitre|852|-34.1629|-58.9648|||B2804AQR|Campana|AR-B\n"
        "Ãºltima actualizaciÃ³n: 2026-04-14T03:06:52-03:00\n",
        encoding="utf-8",
    )

    first = parse_sucursales(csv_path)
    second = parse_sucursales(csv_path)

    assert len(first.rows) == 1
    assert len(second.rows) == 1
    assert first.discarded == second.discarded


def test_parse_sucursales_normaliza_buenos_aires(tmp_path: Path) -> None:
    csv_path = tmp_path / "sucursales.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|sucursales_nombre|sucursales_tipo|sucursales_calle|sucursales_numero|sucursales_latitud|sucursales_longitud|sucursales_observaciones|sucursales_barrio|sucursales_codigo_postal|sucursales_localidad|sucursales_provincia\n"
        "23|1|6201|Dialogos|Autoservicio|Av. Mitre|852|-34.1629|-58.9648|||B2804AQR|Campana|Bs. As.\n",
        encoding="utf-8",
    )

    result = parse_sucursales(csv_path)

    assert len(result.rows) == 1
    assert result.rows[0].provincia == "Buenos Aires"


def test_parse_comercio_cp1252_fallback(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    csv_path = tmp_path / "comercio.csv"
    content = (
        "id_comercio|id_bandera|comercio_cuit|comercio_razon_social|comercio_bandera_nombre\n"
        "20|1|33504047089|LA AGRÍCOLA|LAR\n"
    )
    csv_path.write_bytes(content.encode("cp1252"))

    rows = parse_comercio(csv_path)

    assert len(rows) == 1
    assert rows[0].razon_social == "LA AGRÍCOLA"
    assert "Fallback de encoding" in caplog.text


def test_get_required_devuelve_none_en_vacio() -> None:
    row = {"id_comercio": "   "}
    assert _get_required(row, "id_comercio") is None


def test_parse_comercio_con_bom_en_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "comercio.csv"
    csv_path.write_text(
        "\ufeffid_comercio|id_bandera|comercio_cuit|comercio_razon_social|comercio_bandera_nombre\n"
        "20|1|33504047089|LA AGRICOLA|LAR\n",
        encoding="utf-8",
    )

    rows = parse_comercio(csv_path)

    assert len(rows) == 1
    assert rows[0].id_comercio == "20"


def test_iter_productos_chunks_generates_batches(tmp_path: Path) -> None:
    csv_path = tmp_path / "productos.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|id_producto|productos_ean|productos_descripcion|productos_cantidad_presentacion|productos_unidad_medida_presentacion|productos_marca|productos_precio_lista\n"
        "12|1|2|7790742363008|1|LECHE|1|ltr|MARCA|2500.5\n"
        "12|1|2|7790742363009|1|YOGUR|1|u|MARCA|1800\n",
        encoding="utf-8",
    )

    chunks = list(iter_productos_chunks(csv_path, chunk_size=1))

    assert len(chunks) == 2
    assert len(chunks[0]) == 1
    assert len(chunks[1]) == 1


def test_parse_comercio_strips_nul_bytes(tmp_path: Path) -> None:
    csv_path = tmp_path / "comercio.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|comercio_cuit|comercio_razon_social|comercio_bandera_nombre\n"
        "20|1|33504047089|LA\x00AGRICOLA|LAR\x00\n",
        encoding="utf-8",
    )

    rows = parse_comercio(csv_path)

    assert len(rows) == 1
    assert rows[0].razon_social == "LAAGRICOLA"
    assert "\x00" not in rows[0].razon_social
    assert "\x00" not in rows[0].bandera_nombre


def test_parse_sucursales_strips_nul_bytes(tmp_path: Path) -> None:
    csv_path = tmp_path / "sucursales.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|sucursales_nombre|sucursales_tipo|sucursales_calle|sucursales_numero|sucursales_latitud|sucursales_longitud|sucursales_observaciones|sucursales_barrio|sucursales_codigo_postal|sucursales_localidad|sucursales_provincia\n"
        "23|1|6201|Dia\x00logos|Autoservicio|Av. Mit\x00re|852|-34.1629|-58.9648|||B2804AQR|Cam\x00pana|AR-B\n",
        encoding="utf-8",
    )

    result = parse_sucursales(csv_path)

    assert len(result.rows) == 1
    assert result.rows[0].nombre == "Dialogos"
    assert "\x00" not in result.rows[0].nombre
    assert "\x00" not in result.rows[0].direccion
    assert result.rows[0].direccion == "Av. Mitre 852"
    assert result.rows[0].localidad == "Campana"


def test_parse_productos_strips_nul_bytes(tmp_path: Path) -> None:
    csv_path = tmp_path / "productos.csv"
    csv_path.write_text(
        "id_comercio|id_bandera|id_sucursal|id_producto|productos_ean|productos_descripcion|productos_cantidad_presentacion|productos_unidad_medida_presentacion|productos_marca|productos_precio_lista\n"
        "12|1|2|7790742363008|1|LECHE\x00ENTERA|1|ltr|MARCA\x00|2500.5\n",
        encoding="utf-8",
    )

    rows = parse_productos(csv_path)

    assert len(rows) == 1
    assert rows[0].descripcion == "LECHEENTERA"
    assert "\x00" not in rows[0].descripcion
    assert "\x00" not in rows[0].marca
