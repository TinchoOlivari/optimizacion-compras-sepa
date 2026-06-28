from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
def fetch_zip(url: str, download_dir: str) -> Path:
    destino_dir = Path(download_dir)
    destino_dir.mkdir(parents=True, exist_ok=True)

    nombre = _resolve_zip_filename(url)
    destino_zip = destino_dir / nombre
    if destino_zip.exists() and destino_zip.stat().st_size > 0:
        return destino_zip

    with httpx.Client(timeout=120.0) as client, client.stream("GET", url) as response:
        response.raise_for_status()
        with destino_zip.open("wb") as out:
            for chunk in response.iter_bytes():
                if chunk:
                    out.write(chunk)

    return destino_zip


def extract(zip_path: Path) -> list[Path]:
    extract_root = zip_path.with_suffix("")
    extract_root.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path) as archive:
        archive.extractall(extract_root)
    _extract_nested_zips(extract_root)
    return find_data_dirs(extract_root)


def _extract_nested_zips(root: Path) -> None:
    for inner_zip in sorted(root.rglob("*.zip")):
        dest = inner_zip.with_suffix("")
        dest.mkdir(parents=True, exist_ok=True)
        try:
            with ZipFile(inner_zip) as archive:
                archive.extractall(dest)
        except (BadZipFile, OSError):
            logger.warning("Error al extraer zip anidado %s, se omite", inner_zip)


def find_data_dirs(root: Path) -> list[Path]:
    if _is_data_dir(root):
        return [root]

    directorios: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() and _is_data_dir(path):
            directorios.append(path)
    return directorios


def collect_local_data_dirs(download_dir: Path) -> list[Path]:
    directorios = find_data_dirs(download_dir)
    local_dir = download_dir / "local"
    if local_dir.is_dir():
        directorios.extend(find_data_dirs(local_dir))
    return sorted(set(directorios))


def _is_data_dir(path: Path) -> bool:
    return (path / "comercio.csv").exists() and (path / "sucursales.csv").exists() and (
        path / "productos.csv"
    ).exists()


def _resolve_zip_filename(url: str) -> str:
    path = urlparse(url).path
    candidate = Path(path).name
    if candidate.lower().endswith(".zip") and candidate:
        return candidate
    return "sepa.zip"
