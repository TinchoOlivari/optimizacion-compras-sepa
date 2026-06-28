from datetime import date, datetime
from unittest.mock import MagicMock, patch

import httpx

from ingesta.ckan_client import CKANClient, CkanZipResource


def _resource_payload() -> dict:
    return {
        "success": True,
        "result": {
            "resources": [
                {
                    "url": "https://example.com/sepa_viernes.zip",
                    "format": "ZIP",
                    "description": "Precios SEPA Minoristas viernes, 2026-06-12",
                    "fileName": "sepa_viernes.zip",
                    "last_modified": "2026-06-12T16:19:12.375330",
                },
                {
                    "url": "https://example.com/sepa_lunes.zip",
                    "format": "ZIP",
                    "description": "Precios SEPA Minoristas lunes, 2026-06-15",
                    "fileName": "sepa_lunes.zip",
                    "last_modified": "2026-06-15T16:18:21.070225",
                },
                {
                    "url": "https://example.com/archivo-b.csv",
                    "format": "CSV",
                    "description": "Otro recurso",
                },
            ]
        },
    }


def test_discover_returns_minorista_zip_resources_only() -> None:
    response = MagicMock()
    response.json.return_value = _resource_payload()
    response.raise_for_status.return_value = None

    client_ctx = MagicMock()
    client_ctx.get.return_value = response

    with patch("ingesta.ckan_client.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = client_ctx
        ckan = CKANClient("https://datos.produccion.gob.ar")
        resources = ckan.discover("sepa-precios")

    assert [resource.url for resource in resources] == [
        "https://example.com/sepa_viernes.zip",
        "https://example.com/sepa_lunes.zip",
    ]


def test_select_latest_resource_elige_la_fecha_mas_reciente() -> None:
    ckan = CKANClient("https://datos.produccion.gob.ar")
    resources = [
        CkanZipResource(
            url="https://example.com/sepa_viernes.zip",
            description="Precios SEPA Minoristas viernes, 2026-06-12",
            file_name="sepa_viernes.zip",
            last_modified=datetime(2026, 6, 12, 16, 19, 12),
            fecha_publicacion=date(2026, 6, 12),
        ),
        CkanZipResource(
            url="https://example.com/sepa_lunes.zip",
            description="Precios SEPA Minoristas lunes, 2026-06-15",
            file_name="sepa_lunes.zip",
            last_modified=datetime(2026, 6, 15, 16, 18, 21),
            fecha_publicacion=date(2026, 6, 15),
        ),
    ]

    selected = ckan.select_latest_resource(resources)

    assert selected is not None
    assert selected.url == "https://example.com/sepa_lunes.zip"


def test_discover_reintenta_errores_5xx() -> None:
    fail_response = MagicMock()
    fail_response.status_code = 500
    fail_error = httpx.HTTPStatusError(
        "server error",
        request=MagicMock(),
        response=fail_response,
    )
    fail_response.raise_for_status.side_effect = fail_error

    ok_response = MagicMock()
    ok_response.json.return_value = _resource_payload()
    ok_response.raise_for_status.return_value = None

    client_ctx = MagicMock()
    client_ctx.get.side_effect = [fail_response, ok_response]

    with patch("ingesta.ckan_client.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = client_ctx
        ckan = CKANClient("https://datos.produccion.gob.ar")
        resources = ckan.discover("sepa-precios")

    assert len(resources) == 2
    assert client_ctx.get.call_count == 2
