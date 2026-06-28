from decimal import Decimal

from ingesta.ean_validator import ean_valido, filtrar_productos_validos
from ingesta.parser import ProductoCSV


def _row(codigo: str, productos_ean: str = "1") -> ProductoCSV:
    return ProductoCSV(
        id_comercio="12",
        id_bandera="1",
        id_sucursal="2",
        codigo_ean=codigo,
        productos_ean=productos_ean,
        descripcion="Producto de prueba",
        cantidad_presentacion="1",
        unidad_medida_presentacion="un",
        marca="Marca",
        precio_lista=Decimal("100.00"),
    )


def test_ean_valido_gtin13() -> None:
    assert ean_valido("7790742363008")


def test_ean_invalido_checksum() -> None:
    assert not ean_valido("7790742363009")


def test_filtro_ean_y_gate_productos_ean() -> None:
    rows = [
        _row("7790742363008", "1"),
        _row("7790742363009", "1"),
        _row("7790742363008", "0"),
    ]

    validos, descartados = filtrar_productos_validos(rows)

    assert len(validos) == 1
    assert validos[0].codigo_ean == "7790742363008"
    assert descartados == 2
