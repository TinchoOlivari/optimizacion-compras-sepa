from __future__ import annotations

import os

import pytest


@pytest.fixture()
def database_url() -> str | None:
    return os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
