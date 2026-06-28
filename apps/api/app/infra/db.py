"""Acceso a base de datos (placeholder de scaffolding).

Aún no define modelos ni repositorios; solo provee la cadena de conexión y un
helper para abrir conexiones psycopg cuando la lógica de dominio lo requiera.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from app.core.config import get_settings


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        yield conn
