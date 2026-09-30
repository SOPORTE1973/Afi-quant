"""
Fixtures de series reales (NAV ajustado) en CSV — `fecha,nav_ajustado`.

Fuente: `nav_ajustado` del conector MCP_Afitrading, consultado en vivo
el 2026-09-30 (fecha_snapshot 2026-09-30 15:01:39). Son datos reales de
mercado, no sintéticos: el NAV ajustado ya reinvierte los repartos, por
eso sirve para medir retorno total (el valor libro cae el día del
dividendo y subestimaría a cualquier fondo que reparta).

Existen solo para correr la demo y los tests de forma reproducible sin
depender del conector. En producción los motores reciben la serie del
conector en vivo.

  - cfifalctac_nav_ajustado.csv — FI Falcom Tactical Chilean Equities
    (rut 9194, serie UNICA), 2023-09-29 a 2026-09-29, 1093 puntos.
    Repartos en el período: 2024-05-14, 2025-06-04, 2026-06-19.
  - cfietfipsa_nav_ajustado.csv — ETF Singular IPSA (rut 10748, serie
    UNICA), 2025-05-12 (inicio de la serie) a 2026-09-29, 499 puntos.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from afi_quant.engines.series import AdjustedSeries, NavPoint

_DIR = Path(__file__).parent
_QUERIED = "consultado 2026-09-30"


def load_series_csv(filename: str, *, rut: str, serie: str, nemotecnico: str, source: str) -> AdjustedSeries:
    with open(_DIR / filename, encoding="utf-8", newline="") as fh:
        points = [
            NavPoint(fecha=date.fromisoformat(row["fecha"]), valor_cuota=float(row["nav_ajustado"]))
            for row in csv.DictReader(fh)
        ]
    return AdjustedSeries(rut=rut, serie=serie, nemotecnico=nemotecnico, points=points, source=source)


def falcom_tactical() -> AdjustedSeries:
    return load_series_csv(
        "cfifalctac_nav_ajustado.csv",
        rut="9194",
        serie="UNICA",
        nemotecnico="CFIFALCTAC",
        source=f"mcp__MCP_Afitrading__nav_ajustado(rut=9194, serie=UNICA, "
               f"desde=2023-09-29, hasta=2026-09-29) — {_QUERIED}",
    )


def etf_ipsa() -> AdjustedSeries:
    return load_series_csv(
        "cfietfipsa_nav_ajustado.csv",
        rut="10748",
        serie="UNICA",
        nemotecnico="CFIETFIPSA",
        source=f"mcp__MCP_Afitrading__nav_ajustado(rut=10748, serie=UNICA, "
               f"desde=2025-05-12, hasta=2026-09-29) — {_QUERIED}",
    )
