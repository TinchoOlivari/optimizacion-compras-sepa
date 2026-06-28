import pytest

from ingesta.normalizadores import normalizar_provincia


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Buenos Aires", "Buenos Aires"),
        ("Bs. As.", "Buenos Aires"),
        ("bs as", "Buenos Aires"),
        ("CABA", "Ciudad Autónoma de Buenos Aires"),
        ("capital federal", "Ciudad Autónoma de Buenos Aires"),
        ("ar-x", "AR-X"),
    ],
)
def test_normalizar_provincia_known_values(raw: str, expected: str) -> None:
    assert normalizar_provincia(raw) == expected


def test_normalizar_provincia_unknown_value_preserved() -> None:
    assert normalizar_provincia("Provincia Inventada") == "Provincia Inventada"
