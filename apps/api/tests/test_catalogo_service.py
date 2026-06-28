from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.domain.catalogo import CatalogoNotFoundError, CatalogoService, CatalogoValidationError
from app.domain.ports import PrecioProducto, ProductoResumen


@dataclass
class FakeCatalogoRepo:
    producto: ProductoResumen | None = ProductoResumen(
        id=42,
        codigo_ean="7790580492432",
        nombre="Leche Entera",
        marca="Marca",
        presentacion="1L",
        url_imagen=None,
    )

    def __post_init__(self) -> None:
        self.llamado_ean: str | None = None
        self.llamado_nombre: tuple[str, int] | None = None
        self.llamado_precios: tuple[int, float | None, float | None, int | None, int | None] | None = None

    def buscar_por_ean(self, codigo_ean: str) -> ProductoResumen | None:
        self.llamado_ean = codigo_ean
        if self.producto is None:
            return None
        if codigo_ean == self.producto.codigo_ean:
            return self.producto
        return None

    def buscar_por_nombre(self, texto: str, limite: int) -> list[ProductoResumen]:
        self.llamado_nombre = (texto, limite)
        if self.producto is None:
            return []
        return [self.producto]

    def obtener_producto(self, producto_id: int) -> ProductoResumen | None:
        if self.producto is None:
            return None
        if producto_id == self.producto.id:
            return self.producto
        return None

    def obtener_precios_producto(
        self,
        producto_id: int,
        *,
        lat: float | None,
        lon: float | None,
        radio_km: int | None,
        limite: int | None = None,
    ) -> list[PrecioProducto]:
        self.llamado_precios = (producto_id, lat, lon, radio_km, limite)
        if lat is None or lon is None or radio_km is None:
            return []
        return [
            PrecioProducto(
                comercio_id=1,
                comercio="Comercio A",
                sucursal_id=10,
                sucursal="Sucursal A",
                direccion="Calle 123",
                localidad="Córdoba",
                provincia="Córdoba",
                precio=900.0,
                fecha_vigencia=datetime(2026, 1, 1, tzinfo=UTC),
                distancia_km=1.2,
            ),
            PrecioProducto(
                comercio_id=2,
                comercio="Comercio B",
                sucursal_id=20,
                sucursal="Sucursal B",
                direccion="Calle 456",
                localidad="Córdoba",
                provincia="Córdoba",
                precio=850.0,
                fecha_vigencia=datetime(2026, 1, 1, tzinfo=UTC),
                distancia_km=0.8,
            ),
        ]


def test_buscar_por_nombre_requiere_minimo_4_caracteres() -> None:
    service = CatalogoService(FakeCatalogoRepo())

    with pytest.raises(CatalogoValidationError):
        service.buscar("abc")


def test_buscar_por_ean_exacto_devuelve_un_item() -> None:
    repo = FakeCatalogoRepo()
    service = CatalogoService(repo)

    result = service.buscar("7790580492432")

    assert len(result) == 1
    assert result[0].codigo_ean == "7790580492432"
    assert repo.llamado_ean == "7790580492432"


def test_buscar_ean_invalido_falla() -> None:
    service = CatalogoService(FakeCatalogoRepo())

    with pytest.raises(CatalogoValidationError):
        service.buscar("123456")


def test_detalle_marca_precio_minimo() -> None:
    repo = FakeCatalogoRepo()
    service = CatalogoService(repo)

    result = service.detalle(42, lat=-31.4, lon=-64.1, radio_km=5)

    assert result.filtro_radio_activo is True
    assert len(result.precios) == 2
    assert result.precios[1].precio_minimo is True
    assert result.mensaje is None
    assert repo.llamado_precios == (42, -31.4, -64.1, 5, 6)


def test_detalle_sin_geo_no_devuelve_precios() -> None:
    repo = FakeCatalogoRepo()
    service = CatalogoService(repo)

    result = service.detalle(42)

    assert result.filtro_radio_activo is False
    assert result.precios == []
    assert result.mensaje == "Indicá tu ubicación para ver precios cercanos"
    assert repo.llamado_precios == (42, None, None, None, None)


def test_detalle_producto_inexistente() -> None:
    service = CatalogoService(FakeCatalogoRepo(producto=None))

    with pytest.raises(CatalogoNotFoundError):
        service.detalle(9999)
