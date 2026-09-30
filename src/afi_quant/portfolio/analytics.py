"""
Utilidades de análisis sobre series reales — sin lógica de decisión.

  - `aligned_monthly_returns`: retornos mensuales (último dato de cada mes)
    en los meses comunes a todas las series. Frecuencia más baja común,
    nunca interpolada (QM IV, XVII Frequency Mismatch).
  - `multi_period_returns`: cuadro multi-período por vehículo (ESFS 11.1:
    YTD, 1-3-5 años, desde inicio), sobre NAV ajustado.
  - `rolling_annualized`: rolling returns de 36 meses (QM IV: consistencia,
    evita "period picking").
  - `constant_mix`: retorno mensual de una mezcla rebalanceada cada mes.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date

from afi_quant.engines.risk import max_drawdown
from afi_quant.engines.series import NavPoint, month_end_points, period_returns, trailing_window


@dataclass
class AlignedReturns:
    months: list[date]
    returns: dict[str, list[float]]

    def __len__(self) -> int:
        return len(self.months)


def aligned_monthly_returns(series_by_key: dict, as_of: date, since: date | None = None) -> AlignedReturns:
    ends = {}
    for k, s in series_by_key.items():
        pts = [p for p in s.points if p.fecha <= as_of and (since is None or p.fecha >= since)]
        ends[k] = {(p.fecha.year, p.fecha.month): p for p in month_end_points(pts)}
    common = sorted(set.intersection(*(set(e) for e in ends.values())))
    first = next(iter(ends))
    return AlignedReturns(
        months=[ends[first][m].fecha for m in common[1:]],
        returns={k: period_returns([ends[k][m] for m in common]) for k in ends},
    )


def constant_mix(returns: dict[str, list[float]], weights: dict[str, float]) -> list[float]:
    n = len(next(iter(returns.values())))
    return [sum(w * returns[k][t] for k, w in weights.items() if w) for t in range(n)]


def _window_return(points: list[NavPoint], start: date) -> float | None:
    before = [p for p in points if p.fecha <= start]
    if not before:
        return None
    return points[-1].valor_cuota / before[-1].valor_cuota - 1


def multi_period_returns(series, as_of: date) -> dict:
    pts = [p for p in series.points if p.fecha <= as_of]
    end = pts[-1].fecha
    out = {"nemotecnico": series.nemotecnico, "hasta": end.isoformat(), "desde_inicio_fecha": pts[0].fecha.isoformat()}

    def months_back(m: int) -> date:
        y, mo = end.year, end.month - m
        while mo <= 0:
            mo += 12
            y -= 1
        day = min(end.day, 28)
        return date(y, mo, day)

    out["1m"] = _window_return(pts, months_back(1))
    out["3m"] = _window_return(pts, months_back(3))
    out["ytd"] = _window_return(pts, date(end.year - 1, 12, 31))
    for years in (1, 3, 5):
        window = trailing_window(pts, years)
        if window is None:
            out[f"{years}a"] = None
            continue
        total = window[-1].valor_cuota / window[0].valor_cuota - 1
        out[f"{years}a"] = total if years == 1 else (1 + total) ** (1 / years) - 1   # 3a y 5a anualizados
    total = pts[-1].valor_cuota / pts[0].valor_cuota - 1
    yrs = (end - pts[0].fecha).days / 365.25
    out["desde_inicio_anual"] = (1 + total) ** (1 / yrs) - 1 if yrs > 0 else None

    window3 = trailing_window(pts, 3)
    if window3:
        rets = period_returns(month_end_points(window3))
        out["volatilidad_3a"] = statistics.stdev(rets) * math.sqrt(12) if len(rets) >= 36 else None
        out["max_drawdown_3a"] = max_drawdown(window3)["max_drawdown"]
    else:
        out["volatilidad_3a"] = out["max_drawdown_3a"] = None
    return out


def rolling_annualized(returns: list[float], months: list[date], window: int = 36) -> list[dict]:
    out = []
    for end in range(window, len(returns) + 1):
        acc = 1.0
        for r in returns[end - window:end]:
            acc *= 1 + r
        out.append({"hasta": months[end - 1].isoformat(), "retorno_anual": acc ** (12 / window) - 1})
    return out
