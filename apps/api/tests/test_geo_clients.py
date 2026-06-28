import json
from urllib.error import URLError

import pytest

from app.infra.geo_clients import OsrmClient


class _RespuestaOsrm:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_RespuestaOsrm":
        return self

    def __exit__(self, *args: object) -> None:
        _ = args

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_osrm_client_fallback_usa_haversine_si_falla_osrm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fallar(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        raise URLError("sin conexión")

    monkeypatch.setattr("app.infra.geo_clients.urlopen", _fallar)

    client = OsrmClient("http://osrm.local")
    matriz = client.obtener_matriz_km([(0.0, 0.0), (1.0, 0.0)])

    assert matriz[0][0] == 0.0
    assert matriz[1][1] == 0.0
    assert matriz[0][1] == pytest.approx(111.195, abs=0.01)
    assert matriz[1][0] == pytest.approx(111.195, abs=0.01)


def test_osrm_client_fallback_usa_haversine_si_matriz_tiene_distancia_nula(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _responder(*args: object, **kwargs: object) -> _RespuestaOsrm:
        _ = (args, kwargs)
        return _RespuestaOsrm(
            {
                "distances": [
                    [0.0, None],
                    [111_195.0, 0.0],
                ]
            }
        )

    monkeypatch.setattr("app.infra.geo_clients.urlopen", _responder)

    client = OsrmClient("http://osrm.local")
    matriz = client.obtener_matriz_km([(0.0, 0.0), (1.0, 0.0)])

    assert matriz[0][0] == 0.0
    assert matriz[1][1] == 0.0
    assert matriz[0][1] == pytest.approx(111.195, abs=0.01)
    assert matriz[1][0] == pytest.approx(111.195, abs=0.01)
