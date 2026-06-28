from ingesta.__main__ import main
from ingesta.config import load_config


def test_entrypoint_returns_zero() -> None:
    assert main() == 0


def test_load_config() -> None:
    config = load_config()
    assert config.database_url


def test_load_config_ckan_dataset_default() -> None:
    config = load_config()
    assert config.ckan_dataset_id
