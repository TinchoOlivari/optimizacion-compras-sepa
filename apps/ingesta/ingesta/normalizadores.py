from __future__ import annotations

import re
import unicodedata

ISO_3166_2_AR: frozenset[str] = frozenset(
    {
        "AR-A",
        "AR-B",
        "AR-C",
        "AR-D",
        "AR-E",
        "AR-F",
        "AR-G",
        "AR-H",
        "AR-J",
        "AR-K",
        "AR-L",
        "AR-M",
        "AR-N",
        "AR-P",
        "AR-Q",
        "AR-R",
        "AR-S",
        "AR-T",
        "AR-U",
        "AR-V",
        "AR-W",
        "AR-X",
        "AR-Y",
        "AR-Z",
    }
)

_PROVINCIA_MAP: dict[str, str] = {
    "buenos aires": "Buenos Aires",
    "bs as": "Buenos Aires",
    "bs as.": "Buenos Aires",
    "bs. as": "Buenos Aires",
    "bs. as.": "Buenos Aires",
    "bsas": "Buenos Aires",
    "caba": "Ciudad Autónoma de Buenos Aires",
    "capital federal": "Ciudad Autónoma de Buenos Aires",
    "ciudad autonoma de buenos aires": "Ciudad Autónoma de Buenos Aires",
    "ciudad autónoma de buenos aires": "Ciudad Autónoma de Buenos Aires",
}

_ISO_PATTERN = re.compile(r"^AR-[A-Za-z]$")


def normalizar_provincia(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return trimmed

    upper = trimmed.upper()
    if _ISO_PATTERN.fullmatch(upper):
        return upper

    normalized_key = _normalizar_texto(trimmed)
    return _PROVINCIA_MAP.get(normalized_key, trimmed)


def _normalizar_texto(value: str) -> str:
    lowercase = value.lower().strip()
    normalized = unicodedata.normalize("NFKD", lowercase)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", without_accents)
