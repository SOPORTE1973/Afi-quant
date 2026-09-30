"""
Motor de Riesgo (CORE) — MVP a nivel fondo.

Modelos implementados (todos CORE en el Model Governance Registry):
  - Volatilidad histórica  σ(retornos mensuales) · √12
  - Maximum Drawdown       max(peak−trough)/peak sobre la serie diaria,
                           con fecha de recuperación (el registro pide
                           combinarlo con Recovery Time)
  - VaR histórico          percentil empírico de pérdidas mensuales, 95%
                           (cliente) y 99% (Comité) — confianzas tomadas
                           de la nota del registro, horizonte 1 mes
  - Expected Shortfall     media de las pérdidas en la cola del VaR
  - Downside Deviation     solo si el Parameter Registry tiene MAR
  - Tracking Error / Beta  solo con benchmark certificado por el Motor de
                           Benchmark y ≥ 36 retornos mensuales comunes

Frecuencia: las métricas de dispersión usan retornos MENSUALES (último
dato de cada mes). Los fondos chilenos publican NAV también fines de
semana, así que anualizar retornos diarios con √252 o √365 mezcla
convenciones; con retornos mensuales esa ambigüedad desaparece.

Umbrales de muestra: mínimo 36 retornos mensuales para volatilidad y
Tracking Error (registro: "Ventana 3-5 años", "Mín. 36-60 obs.
mensuales"). Con menos, el motor declara la métrica como no calculada.
"""

from __future__ import annotations

import math
import statistics

from afi_quant.engines.base import EngineResult
from afi_quant.engines.benchmark import certified_benchmark
from afi_quant.engines.series import (
    AdjustedSeries,
    NavPoint,
    align_on_common_dates,
    month_end_points,
    period_returns,
)
from afi_quant.registries.parameter_registry import get_parameter

MIN_MONTHLY_OBS = 36
VAR_CONFIDENCES = (0.95, 0.99)


class RiskEngine:
    name = "risk"
    required_critical_data = [
        "nav_series_native_frequency",
    ]

    def run(self, case) -> EngineResult:
        series = case.input_data.get("nav_series_native_frequency")
        if not isinstance(series, AdjustedSeries) or len(series.points) < 2:
            return EngineResult(
                engine_name=self.name,
                insufficient_data=True,
                insufficient_data_reason=(
                    "Falta 'nav_series_native_frequency' como AdjustedSeries con al "
                    "menos 2 puntos (Principio 8)."
                ),
            )

        monthly = month_end_points(series.points)
        rets = period_returns(monthly)
        blocked: dict[str, str] = {}
        values: dict = {
            "nemotecnico": series.nemotecnico,
            "n_retornos_mensuales": len(rets),
            "ultimo_cierre_mensual": monthly[-1].fecha.isoformat(),
        }

        values.update(max_drawdown(series.points))

        if len(rets) >= MIN_MONTHLY_OBS:
            values["volatilidad_anual"] = annualized_volatility(rets)
            for conf in VAR_CONFIDENCES:
                var, es, tail = historical_var_es(rets, conf)
                pct = round(conf * 100)
                values[f"var_{pct}_1m"] = var
                values[f"es_{pct}_1m"] = es
                values[f"obs_cola_{pct}"] = tail
        else:
            reason = (
                f"Solo {len(rets)} retornos mensuales; el mínimo es {MIN_MONTHLY_OBS} "
                "(Model Governance Registry: ventana 3-5 años)."
            )
            blocked["volatilidad_anual"] = reason
            blocked["var_es"] = reason

        mar = get_parameter("downside_deviation_mar_pct").value
        if mar is None:
            blocked["downside_deviation"] = (
                "El Parameter Registry no tiene valor para 'downside_deviation_mar_pct' "
                "— no se inventa un MAR."
            )
        elif len(rets) >= MIN_MONTHLY_OBS:
            values["downside_deviation_anual"] = downside_deviation(rets, float(mar) / 100)

        benchmark, reason = certified_benchmark(case)
        if benchmark is None:
            blocked["tracking_error_beta"] = reason
        else:
            f_pts, b_pts = align_on_common_dates(series.points, benchmark.points)
            f_rets = period_returns(month_end_points(f_pts))
            b_rets = period_returns(month_end_points(b_pts))
            if len(f_rets) < MIN_MONTHLY_OBS:
                blocked["tracking_error_beta"] = (
                    f"Solo {len(f_rets)} retornos mensuales comunes con el benchmark; "
                    f"el mínimo es {MIN_MONTHLY_OBS}."
                )
            else:
                values["tracking_error_anual"] = tracking_error(f_rets, b_rets)
                values["beta"] = beta(f_rets, b_rets)

        values["no_calculado"] = blocked
        return EngineResult(engine_name=self.name, values=values)


def annualized_volatility(monthly_returns: list[float]) -> float:
    return statistics.stdev(monthly_returns) * math.sqrt(12)


def downside_deviation(monthly_returns: list[float], mar: float) -> float:
    shortfalls = [min(r - mar, 0.0) ** 2 for r in monthly_returns]
    return math.sqrt(sum(shortfalls) / len(shortfalls)) * math.sqrt(12)


def max_drawdown(points: list[NavPoint]) -> dict:
    """
    Mayor caída desde un máximo previo. Devuelve la caída (negativa), las
    fechas de peak y trough, y la primera fecha en que se recuperó el
    peak (None si todavía no se recupera).
    """
    peak = points[0]
    worst = 0.0
    worst_peak = worst_trough = points[0]
    for p in points:
        if p.valor_cuota > peak.valor_cuota:
            peak = p
        dd = p.valor_cuota / peak.valor_cuota - 1
        if dd < worst:
            worst, worst_peak, worst_trough = dd, peak, p

    recovery = next(
        (p for p in points
         if p.fecha > worst_trough.fecha and p.valor_cuota >= worst_peak.valor_cuota),
        None,
    )
    return {
        "max_drawdown": worst,
        "max_drawdown_peak": worst_peak.fecha.isoformat(),
        "max_drawdown_trough": worst_trough.fecha.isoformat(),
        "max_drawdown_recuperacion": recovery.fecha.isoformat() if recovery else None,
        "max_drawdown_dias_recuperacion": (
            (recovery.fecha - worst_trough.fecha).days if recovery else None
        ),
    }


def historical_var_es(returns: list[float], confidence: float) -> tuple[float, float, int]:
    """
    VaR y Expected Shortfall históricos, expresados como pérdida positiva.

    Con n observaciones, la cola son las k = ceil(n·(1−confianza)) peores:
    VaR es la k-ésima peor pérdida y ES el promedio de las k. Se devuelve k
    para que quien lea sepa cuántas observaciones sostienen la cifra.
    """
    ordered = sorted(returns)
    # round(): 20·(1−0.95) da 1.0000000000000009 en punto flotante y ceil lo subiría a 2.
    k = max(1, math.ceil(round(len(ordered) * (1 - confidence), 9)))
    tail = ordered[:k]
    return -tail[-1], -sum(tail) / k, k


def tracking_error(fund_returns: list[float], bench_returns: list[float]) -> float:
    active = [f - b for f, b in zip(fund_returns, bench_returns)]
    return statistics.stdev(active) * math.sqrt(12)


def beta(fund_returns: list[float], bench_returns: list[float]) -> float:
    return statistics.covariance(fund_returns, bench_returns) / statistics.variance(bench_returns)
