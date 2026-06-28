import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    sepa_portal_url: str
    ckan_dataset_id: str
    sepa_download_dir: str
    sepa_fecha_lote: str
    productos_chunk_size: int


def load_config() -> Config:
    raw_chunk_size = os.environ.get("PRODUCTOS_CHUNK_SIZE", "50000")
    try:
        productos_chunk_size = max(1, int(raw_chunk_size))
    except ValueError:
        productos_chunk_size = 50000

    return Config(
        database_url=os.environ.get("DATABASE_URL", "postgresql://tfg:tfg@db:5432/tfg"),
        sepa_portal_url=os.environ.get("SEPA_PORTAL_URL", ""),
        ckan_dataset_id=os.environ.get("CKAN_DATASET_ID", "sepa-precios"),
        sepa_download_dir=os.environ.get("SEPA_DOWNLOAD_DIR", "/data/sepa"),
        sepa_fecha_lote=os.environ.get("SEPA_FECHA_LOTE", ""),
        productos_chunk_size=productos_chunk_size,
    )
