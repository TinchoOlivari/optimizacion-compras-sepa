from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from ingesta import __main__


class _FakeCursor:
    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def execute(self, *args: object, **kwargs: object) -> None:
        return None


class _FakeConnection:
    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def execute(self, *args: object, **kwargs: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return _FakeCursor()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _FakeLoteManager:
    last_detalle_errores: list[dict[str, str]] = []
    last_archivos_con_error: int = 0

    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    def begin(self, fecha_lote: object, origen: str) -> int:
        assert origen == "local"
        return 1

    def create_savepoint(self, name: str) -> None:
        assert name

    def rollback_to_savepoint(self, name: str) -> None:
        assert name

    def release_savepoint(self, name: str) -> None:
        assert name

    def finalize(
        self,
        lote_id: int,
        archivos_procesados: int,
        archivos_con_error: int,
        detalle_errores: list[dict[str, str]],
    ) -> str:
        assert lote_id == 1
        _FakeLoteManager.last_detalle_errores = detalle_errores
        _FakeLoteManager.last_archivos_con_error = archivos_con_error
        if archivos_con_error == 0:
            return "PROCESADO"
        if archivos_procesados > 0:
            assert detalle_errores
            return "PARCIAL"
        assert detalle_errores
        return "ERROR"


class _FakeRepo:
    fail_phase: str = ""
    productos_upsert: list[object] = []

    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    def upsert_comercios(self, rows: list[object]) -> dict[str, int]:
        assert rows
        if self.fail_phase in {"comercios", "all"}:
            raise RuntimeError("falla comercios")
        return {"30712345678": 1}

    def upsert_banderas(self, rows: list[object]) -> dict[str, int]:
        return {"1": 1}

    def upsert_sucursales(
        self,
        rows: list[object],
        comercio_ids: dict[str, int],
        bandera_ids: dict[str, int],
    ) -> dict[tuple[str, str, str], int]:
        assert rows
        if self.fail_phase in {"sucursales", "all"}:
            raise RuntimeError("falla sucursales")
        assert comercio_ids == {"999": 1}
        return {("999", "1", "1"): 1}

    def upsert_productos(self, rows: list[object]) -> dict[str, int]:
        _FakeRepo.productos_upsert = rows
        if self.fail_phase in {"productos", "all"}:
            raise RuntimeError("falla productos")
        return {"7790742363008": 1}

    def upsert_precios(
        self,
        rows: list[object],
        producto_ids: dict[str, int],
        sucursal_ids: dict[tuple[str, str, str], int],
        fecha_vigencia: object,
    ) -> int:
        if self.fail_phase in {"precios", "all"}:
            raise RuntimeError("falla precios")
        assert len(rows) == 1
        assert producto_ids == {"7790742363008": 1}
        assert sucursal_ids == {("999", "1", "1"): 1}
        return 1


def _write_fixture(directory: Path, include_mojibake_footer: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "comercio.csv").write_text(
        "id_comercio|id_bandera|comercio_cuit|comercio_razon_social|comercio_bandera_nombre|comercio_bandera_url|comercio_ultima_actualizacion|comercio_version_sepa\n"
        "999|1|30712345678|COMERCIO TEST|TEST|https://example.com|2026-04-14T01:04:03-03:00|1.0\n",
        encoding="utf-8",
    )
    sucursales = (
        "id_comercio|id_bandera|id_sucursal|sucursales_nombre|sucursales_tipo|sucursales_calle|sucursales_numero|sucursales_latitud|sucursales_longitud|sucursales_observaciones|sucursales_barrio|sucursales_codigo_postal|sucursales_localidad|sucursales_provincia|sucursales_lunes_horario_atencion|sucursales_martes_horario_atencion|sucursales_miercoles_horario_atencion|sucursales_jueves_horario_atencion|sucursales_viernes_horario_atencion|sucursales_sabado_horario_atencion|sucursales_domingo_horario_atencion\n"
        "999|1|1|Sucursal|Supermercado|Calle|123|-31.41|-64.18|||5000|Cordoba|Buenos Aires|8 a 20|8 a 20|8 a 20|8 a 20|8 a 20|8 a 20|Cerrado\n"
    )
    if include_mojibake_footer:
        sucursales += "Ãºltima actualizaciÃ³n: 2026-04-14T03:06:52-03:00\n"
    (directory / "sucursales.csv").write_text(sucursales, encoding="utf-8")
    (directory / "productos.csv").write_text(
        "id_comercio|id_bandera|id_sucursal|id_producto|productos_ean|productos_descripcion|productos_cantidad_presentacion|productos_unidad_medida_presentacion|productos_marca|productos_precio_lista|productos_precio_referencia|productos_cantidad_referencia|productos_unidad_medida_referencia|productos_precio_unitario_promo1|productos_leyenda_promo1|productos_precio_unitario_promo2|productos_leyenda_promo2\n"
        "999|1|1|7790742363008|1|Leche Test|1|ltr|TEST|1000|1000|1|ltr||||\n"
        "999|1|1|7790742363009|1|Leche Test Invalida|1|ltr|TEST|999|999|1|ltr||||\n",
        encoding="utf-8",
    )


def _run_pipeline(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    fail_phase: str,
    include_mojibake_footer: bool = False,
) -> int:
    fixture_dir = tmp_path / "sepa_local"
    _write_fixture(fixture_dir, include_mojibake_footer=include_mojibake_footer)

    _FakeRepo.fail_phase = fail_phase
    _FakeRepo.productos_upsert = []
    _FakeLoteManager.last_detalle_errores = []
    _FakeLoteManager.last_archivos_con_error = 0

    monkeypatch.setenv("SEPA_PORTAL_URL", "")
    monkeypatch.setenv("SEPA_DOWNLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")
    monkeypatch.setenv("SEPA_FECHA_LOTE", "2026-04-14")

    monkeypatch.setattr(__main__.psycopg, "connect", lambda _: _FakeConnection())
    monkeypatch.setattr(__main__, "RepositorioSEPA", _FakeRepo)
    monkeypatch.setattr(__main__, "LoteManager", _FakeLoteManager)

    return __main__.main()


def test_pipeline_local_filtra_ean_y_estado_procesado(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    exit_code = _run_pipeline(monkeypatch, tmp_path, fail_phase="")
    assert exit_code == 0
    assert len(_FakeRepo.productos_upsert) == 1


def test_pipeline_estado_parcial_ante_fallo_en_precios(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    exit_code = _run_pipeline(monkeypatch, tmp_path, fail_phase="precios")
    assert exit_code == 0


def test_pipeline_estado_error_ante_fallos_totales(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    exit_code = _run_pipeline(monkeypatch, tmp_path, fail_phase="all")
    assert exit_code == 1


def test_pipeline_descartes_en_footer_generan_parcial(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    exit_code = _run_pipeline(monkeypatch, tmp_path, fail_phase="", include_mojibake_footer=True)

    assert exit_code == 0
    assert _FakeLoteManager.last_archivos_con_error == 1
    assert any("footer_detected" in item.get("message", "") for item in _FakeLoteManager.last_detalle_errores)


def test_pipeline_reproceso_mantiene_descartes_estables(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    first_exit = _run_pipeline(monkeypatch, tmp_path, fail_phase="", include_mojibake_footer=True)
    first_errors = list(_FakeLoteManager.last_detalle_errores)

    second_exit = _run_pipeline(monkeypatch, tmp_path, fail_phase="", include_mojibake_footer=True)
    second_errors = list(_FakeLoteManager.last_detalle_errores)

    assert first_exit == 0
    assert second_exit == 0
    assert first_errors == second_errors
    assert any("footer_detected" in item.get("message", "") for item in second_errors)
