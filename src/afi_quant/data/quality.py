"""
Controles de calidad de datos sobre series de NAV (ESFS 8.4; QM XVII).

  Outliers      salto diario extremo frente a la volatilidad reciente de la
                propia serie que se revierte al día siguiente: la firma típica
                de un error de carga. Queda `pending_validation` hasta que una
                fuente secundaria (administradora, custodio) lo confirme.
  Stale prices  NAV idéntico en observaciones consecutivas de un vehículo que
                valoriza a diario.
  Missing data  días corridos sin NAV entre dos observaciones.

Por qué el criterio de outlier no es solo "retorno extremo": en estas series
los retornos más extremos son eventos de mercado reales (estallido social de
2019, marzo de 2020) y excluirlos borraría el riesgo de cola que la
metodología pide medir. Incluso un salto que se revierte puede ser real (la
renta fija local el 14-11-2019). Por eso este módulo solo detecta y cuantifica;
la validación es humana o contra fuente secundaria, nunca automática.

Los umbrales son parámetros (ESFS-09 los deja abiertos): sin valor en el
Parameter Registry el control no se ejecuta y se declara.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date

PARAMS = ("stale_nav_run_obs", "outlier_return_mad_multiple", "outlier_reversal_ratio",
          "outlier_scale_window_obs", "nav_gap_max_days")


@dataclass
class QualityReport:
    serie: str
    n_obs: int
    desde: date
    hasta: date
    outliers: list[dict] = field(default_factory=list)
    stale_runs: list[dict] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    no_evaluado: list[str] = field(default_factory=list)

    @property
    def estado(self) -> str:
        if self.outliers or self.stale_runs:
            return "pending_validation"
        if self.gaps:
            return "degraded"
        return "available"


def check_series(name: str, points, params: dict) -> QualityReport:
    """`points`: observaciones con `.fecha` y `.valor_cuota`, ordenadas por fecha."""
    pts = list(points)
    rep = QualityReport(name, len(pts), pts[0].fecha, pts[-1].fecha)
    rep.no_evaluado = [p for p in PARAMS if params.get(p) is None]

    run_min = params.get("stale_nav_run_obs")
    if run_min is not None:
        start = 0
        for i in range(1, len(pts) + 1):
            if i == len(pts) or pts[i].valor_cuota != pts[start].valor_cuota:
                if i - start >= int(run_min):
                    rep.stale_runs.append({"desde": pts[start].fecha, "hasta": pts[i - 1].fecha,
                                           "n_obs": i - start, "valor": pts[start].valor_cuota})
                start = i

    k, rev, win = (params.get(p) for p in ("outlier_return_mad_multiple", "outlier_reversal_ratio",
                                           "outlier_scale_window_obs"))
    if None not in (k, rev, win):
        win = int(win)
        r = [b.valor_cuota / a.valor_cuota - 1 for a, b in zip(pts, pts[1:])]
        for t in range(win, len(r) - 1):
            w = r[t - win:t]
            med = statistics.median(w)
            scale = statistics.median(abs(x - med) for x in w) * 1.4826
            if scale <= 0 or abs(r[t] - med) <= float(k) * scale:
                continue
            if r[t] * r[t + 1] < 0 and abs(r[t + 1]) >= float(rev) * abs(r[t]):
                rep.outliers.append({"fecha": pts[t + 1].fecha, "retorno": r[t],
                                     "reversion": r[t + 1], "escala": scale})

    gap = params.get("nav_gap_max_days")
    if gap is not None:
        rep.gaps = [{"desde": a.fecha, "hasta": b.fecha, "dias": (b.fecha - a.fecha).days}
                    for a, b in zip(pts, pts[1:]) if (b.fecha - a.fecha).days > int(gap)]
    return rep


def exclusion_impact(points, flagged_dates, start: date, end: date) -> dict:
    """
    Volatilidad diaria anualizada en [start, end] con y sin los NAV marcados.
    Excluir un NAV deja un solo retorno entre sus vecinos, que es lo que
    habría mostrado la serie sin el salto.
    """
    pts = [p for p in points if start <= p.fecha <= end]
    clean = [p for p in pts if p.fecha not in set(flagged_dates)]

    def vol(ps):
        r = [b.valor_cuota / a.valor_cuota - 1 for a, b in zip(ps, ps[1:])]
        return statistics.stdev(r) * math.sqrt(252) if len(r) > 2 else None

    v0, v1 = vol(pts), vol(clean)
    n = sum(1 for p in pts if p.fecha in set(flagged_dates))
    return {"n_en_ventana": n, "vol_con": v0, "vol_sin": v1,
            "diferencia": None if v0 is None or v1 is None else v1 - v0}
