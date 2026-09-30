"""
Motor de Performance (CORE) — MVP a nivel fondo.

Modelos implementados (todos CORE en el Model Governance Registry):
  - TWR (geométrico) del período completo y ventanas trailing 1a / 3a
  - CAGR / Annualized TWR:  (1+TWR)^(1/años) − 1
  - Excess Return:          TWR fondo − TWR benchmark  (solo con benchmark
                            certificado por el Motor de Benchmark)

ALCANCE DEL MVP: evalúa una serie de NAV ajustado de un VEHÍCULO (fondo),
que no tiene flujos externos — los repartos ya vienen reinvertidos en el
NAV ajustado. Por eso `cash_flows_dated_classified` debe venir declarado
explícitamente como lista vacía. Si llegan flujos (cartera de un cliente,
con aportes y rescates), el motor NO calcula: el TWR con CF y el MWR/XIRR
dependen de Fase 1 (datos de cartera vía TI). Nunca se ignora un flujo
en silencio (QM Principio 8).
"""

from __future__ import annotations

from afi_quant.engines.base import EngineResult
from afi_quant.engines.benchmark import certified_benchmark
from afi_quant.engines.series import (
    AdjustedSeries,
    align_on_common_dates,
    geometric_chain_return,
    trailing_window,
    years_between,
)

# Model Governance Registry: CAGR "menos informativo en periodos cortos (<3 años)".
CAGR_SHORT_PERIOD_YEARS = 3
TRAILING_WINDOWS_YEARS = (1, 3)


class PerformanceEngine:
    name = "performance"
    required_critical_data = [
        "nav_series_native_frequency",
        "cash_flows_dated_classified",
    ]

    def run(self, case) -> EngineResult:
        series = case.input_data.get("nav_series_native_frequency")
        flows = case.input_data.get("cash_flows_dated_classified")

        if not isinstance(series, AdjustedSeries) or len(series.points) < 2:
            return self._insufficient(
                "Falta 'nav_series_native_frequency' como AdjustedSeries con al menos "
                "2 puntos (Principio 8)."
            )
        if flows is None:
            return self._insufficient(
                "Faltan los flujos de caja declarados. Para un fondo sin flujos externos "
                "deben venir como lista vacía — no se asume que no existen."
            )
        if flows:
            return self._insufficient(
                f"Se recibieron {len(flows)} flujos externos. El TWR con flujos y el "
                "MWR/XIRR (cartera de cliente) dependen de Fase 1 — este MVP solo "
                "evalúa series de fondo sin flujos."
            )

        points = series.points
        twr = geometric_chain_return(points)
        years = years_between(series.start, series.end)
        values: dict = {
            "rut": series.rut,
            "serie": series.serie,
            "nemotecnico": series.nemotecnico,
            "desde": series.start.fecha.isoformat(),
            "hasta": series.end.fecha.isoformat(),
            "anos": years,
            "twr_periodo": twr,
            "cagr": (1 + twr) ** (1 / years) - 1,
            "cagr_periodo_corto": years < CAGR_SHORT_PERIOD_YEARS,
            "fuente": series.source,
        }

        for n in TRAILING_WINDOWS_YEARS:
            window = trailing_window(points, n)
            values[f"twr_{n}a"] = geometric_chain_return(window) if window else None

        benchmark, blocked_reason = certified_benchmark(case)
        if benchmark is None:
            values["excess_return"] = None
            values["excess_return_bloqueado"] = blocked_reason
        else:
            fund_pts, bench_pts = align_on_common_dates(points, benchmark.points)
            values["excess_return"] = excess_return(fund_pts, bench_pts)
            values["excess_return_desde"] = fund_pts[0].fecha.isoformat()

        return EngineResult(engine_name=self.name, values=values)

    def _insufficient(self, reason: str) -> EngineResult:
        return EngineResult(
            engine_name=self.name, insufficient_data=True, insufficient_data_reason=reason
        )


def excess_return(fund_points, benchmark_points) -> float:
    """TWR fondo − TWR benchmark sobre las mismas fechas (aritmético, como en el registro)."""
    return geometric_chain_return(fund_points) - geometric_chain_return(benchmark_points)
