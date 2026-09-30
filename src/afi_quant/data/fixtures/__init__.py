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
    (rut 9194, serie UNICA), 2021-09-30 a 2026-09-29, 1822 puntos.
    `falcom_tactical()` entrega por defecto la ventana de 3 años
    (desde 2023-09-29) que usa la demo de revisión de fondo.
  - cfietfcd_nav_ajustado.csv — ETF Singular Chile Corta Duración
    (rut 9823, UNICA), 2021-09-30 a 2026-09-29, 1822 puntos.
  - cfietfcc_nav_ajustado.csv — ETF Singular Chile Corporativo
    (rut 9705, UNICA), 2021-09-30 a 2026-09-29, 1822 puntos.
  - cfibtgplaa_nav_ajustado.csv — BTG Pactual Liquidez Alternativa FI
    (rut 10145, serie A), 2021-10-04 (inicio) a 2026-09-29, 1822 puntos.
  - cfietfge_nav_ajustado.csv — ETF Singular Global Equities
    (rut 9706, UNICA), 2021-09-30 a 2026-09-29, 1822 puntos.
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


def load_series_csv(
    filename: str, *, rut: str, serie: str, nemotecnico: str, source: str, desde: date | None = None
) -> AdjustedSeries:
    with open(_DIR / filename, encoding="utf-8", newline="") as fh:
        points = [
            NavPoint(fecha=date.fromisoformat(row["fecha"]), valor_cuota=float(row["nav_ajustado"]))
            for row in csv.DictReader(fh)
        ]
    if desde is not None:
        points = [p for p in points if p.fecha >= desde]
    return AdjustedSeries(rut=rut, serie=serie, nemotecnico=nemotecnico, points=points, source=source)


def falcom_tactical(desde: date | None = date(2023, 9, 29)) -> AdjustedSeries:
    return load_series_csv(
        "cfifalctac_nav_ajustado.csv",
        rut="9194",
        serie="UNICA",
        nemotecnico="CFIFALCTAC",
        source=f"mcp__MCP_Afitrading__nav_ajustado(rut=9194, serie=UNICA, "
               f"desde={desde or '2021-09-30'}, hasta=2026-09-29) — {_QUERIED}",
        desde=desde,
    )


def _five_year(filename: str, rut: str, serie: str, nemotecnico: str, desde: str) -> AdjustedSeries:
    return load_series_csv(
        filename,
        rut=rut,
        serie=serie,
        nemotecnico=nemotecnico,
        source=f"mcp__MCP_Afitrading__nav_ajustado(rut={rut}, serie={serie}, "
               f"desde={desde}, hasta=2026-09-29) — {_QUERIED}",
    )


def singular_corta_duracion() -> AdjustedSeries:
    return _five_year("cfietfcd_nav_ajustado.csv", "9823", "UNICA", "CFIETFCD", "2021-09-30")


def singular_corporativo() -> AdjustedSeries:
    return _five_year("cfietfcc_nav_ajustado.csv", "9705", "UNICA", "CFIETFCC", "2021-09-30")


def btg_liquidez_alternativa() -> AdjustedSeries:
    return _five_year("cfibtgplaa_nav_ajustado.csv", "10145", "A", "CFIBTGPLAA", "2021-10-04")


def singular_global_equities() -> AdjustedSeries:
    return _five_year("cfietfge_nav_ajustado.csv", "9706", "UNICA", "CFIETFGE", "2021-09-30")


def etf_ipsa() -> AdjustedSeries:
    return load_series_csv(
        "cfietfipsa_nav_ajustado.csv",
        rut="10748",
        serie="UNICA",
        nemotecnico="CFIETFIPSA",
        source=f"mcp__MCP_Afitrading__nav_ajustado(rut=10748, serie=UNICA, "
               f"desde=2025-05-12, hasta=2026-09-29) — {_QUERIED}",
    )
