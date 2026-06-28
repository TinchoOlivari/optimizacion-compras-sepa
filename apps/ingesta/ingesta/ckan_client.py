from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_fixed

_FECHA_EN_DESCRIPCION = re.compile(r"(\d{4}-\d{2}-\d{2})\s*$")
_CKAN_REINTENTOS = 4
_CKAN_ESPERA_SEGUNDOS = 3


@dataclass(frozen=True)
class CkanZipResource:
    url: str
    description: str
    file_name: str
    last_modified: datetime | None
    fecha_publicacion: date | None


class CKANClient:
    def __init__(self, base_url: str, timeout_seconds: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def discover(self, dataset_id: str) -> list[CkanZipResource]:
        payload = _fetch_package_show(self.base_url, dataset_id, self.timeout_seconds)

        if not payload.get("success"):
            raise ValueError("CKAN respondió success=false")

        result = payload.get("result")
        if not isinstance(result, dict):
            raise ValueError("CKAN package_show sin campo result válido")

        resources = result.get("resources")
        if not isinstance(resources, list):
            raise ValueError("CKAN package_show sin resources")

        zip_resources: list[CkanZipResource] = []
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            if not _es_recurso_zip(resource):
                continue
            url = resource.get("url")
            if not isinstance(url, str) or not url.strip():
                continue
            description = str(resource.get("description") or resource.get("name") or "")
            if "minoristas" not in description.lower():
                continue
            zip_resources.append(
                CkanZipResource(
                    url=url.strip(),
                    description=description,
                    file_name=str(resource.get("fileName") or ""),
                    last_modified=_parse_last_modified(resource.get("last_modified")),
                    fecha_publicacion=_parse_fecha_publicacion(description),
                )
            )

        return zip_resources

    def select_latest_resource(self, resources: list[CkanZipResource]) -> CkanZipResource | None:
        if not resources:
            return None
        return max(resources, key=_sort_key)


def _reintentar_error_ckan(error: BaseException) -> bool:
    if isinstance(error, httpx.TimeoutException):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code >= 500
    return False


@retry(
    retry=retry_if_exception(_reintentar_error_ckan),
    stop=stop_after_attempt(_CKAN_REINTENTOS),
    wait=wait_fixed(_CKAN_ESPERA_SEGUNDOS),
    reraise=True,
)
def _fetch_package_show(base_url: str, dataset_id: str, timeout_seconds: float) -> dict[str, Any]:
    endpoint = f"{base_url}/api/3/action/package_show"
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.get(endpoint, params={"id": dataset_id})
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    return payload


def _sort_key(resource: CkanZipResource) -> tuple[date, datetime]:
    return (
        resource.fecha_publicacion or date.min,
        resource.last_modified or datetime.min,
    )


def _parse_fecha_publicacion(description: str) -> date | None:
    match = _FECHA_EN_DESCRIPCION.search(description.strip())
    if match is None:
        return None
    return date.fromisoformat(match.group(1))


def _parse_last_modified(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _es_recurso_zip(resource: dict[str, Any]) -> bool:
    value_candidates = [
        resource.get("format"),
        resource.get("name"),
        resource.get("url"),
        resource.get("fileName"),
    ]
    text = " ".join(str(v).lower() for v in value_candidates if v is not None)
    return "zip" in text
