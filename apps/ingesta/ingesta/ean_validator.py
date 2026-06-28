from __future__ import annotations

from ingesta.parser import ProductoCSV


def ean_valido(codigo: str) -> bool:
    digits = codigo.strip()
    if not digits.isdigit() or len(digits) not in (8, 12, 13, 14):
        return False

    cuerpo = digits[:-1]
    digito_control = int(digits[-1])
    total = 0
    for index, digit in enumerate(reversed(cuerpo), start=1):
        factor = 3 if index % 2 == 1 else 1
        total += int(digit) * factor

    esperado = (10 - (total % 10)) % 10
    return digito_control == esperado


def producto_con_ean_valido(row: ProductoCSV) -> bool:
    return row.productos_ean.strip() == "1" and ean_valido(row.codigo_ean)


def filtrar_productos_validos(rows: list[ProductoCSV]) -> tuple[list[ProductoCSV], int]:
    validos: list[ProductoCSV] = []
    descartados = 0
    for row in rows:
        if producto_con_ean_valido(row):
            validos.append(row)
        else:
            descartados += 1
    return validos, descartados
