"""Motor de Benchmark (CORE).

Actúa como gate: Performance y Risk (Excess Return, Tracking Error,
Beta, Brinson-Fachler) dependen de que este motor confirme que el
benchmark es elegible antes de comparar contra él (AFI Benchmark
Eligibility Framework — verificación de 8 dimensiones, es una regla,
no una fórmula).

ESTADO: el cálculo de retorno de la serie candidata (TWR geométrico
sobre `AdjustedSeries`, ver `engines/series.py`) ya es real — no un
stub — y corre sobre datos reales del conector MCP_Afitrading cuando
se le pasa una serie en `case.input_data["benchmark_index_series"]`.

Lo que ESTE motor todavía NO hace es certificar elegibilidad: las "8
dimensiones" del AFI Benchmark Eligibility Framework están nombradas
en ESFS-01 pero su contenido exacto (cuáles son, cómo se evalúa cada
una) no está confirmado en este código — no se va a inventar esa
regla. Hasta que el Comité confirme las 8 dimensiones, este motor
calcula el retorno de la serie candidata pero lo marca explícitamente
como "elegibilidad NO verificada", y ningún otro motor debería tratar
ese benchmark como comparable todavía (Principio 7).
"""

from __future__ import annotations

from afi_quant.engines.base import EngineResult
from afi_quant.engines.series import AdjustedSeries, geometric_chain_return, total_return

ELIGIBILITY_NOTE = (
    "Elegibilidad NO verificada: el AFI Benchmark Eligibility Framework "
    "(verificación de 8 dimensiones, ESFS-01) no está confirmado en este "
    "código todavía. Este resultado es el retorno de la serie candidata, "
    "no una certificación de que sea comparable (Principio 7)."
)


class BenchmarkEngine:
    name = "benchmark"
    required_critical_data = [
        "benchmark_index_series",
    ]

    def run(self, case) -> EngineResult:
        if case.input_data.get("benchmark_candidates"):
            return self._run_eligibility(case)
        series = case.input_data.get("benchmark_index_series")

        if series is None:
            return EngineResult(
                engine_name=self.name,
                insufficient_data=True,
                insufficient_data_reason=(
                    "Falta 'benchmark_index_series' en case.input_data — sin una "
                    "serie de NAV ajustado no hay sobre qué calcular (Principio 8)."
                ),
            )

        if not isinstance(series, AdjustedSeries):
            return EngineResult(
                engine_name=self.name,
                insufficient_data=True,
                insufficient_data_reason=(
                    "'benchmark_index_series' debe ser un afi_quant.engines.series."
                    "AdjustedSeries ya deduplicado, no un dict/list crudo."
                ),
            )

        if len(series.points) < 2:
            return EngineResult(
                engine_name=self.name,
                insufficient_data=True,
                insufficient_data_reason=(
                    f"La serie de '{series.nemotecnico}' tiene "
                    f"{len(series.points)} punto(s) — se necesitan al menos 2 "
                    "para calcular un retorno."
                ),
            )

        chained = geometric_chain_return(series.points)
        direct = total_return(series)

        return EngineResult(
            engine_name=self.name,
            insufficient_data=False,
            values={
                "rut": series.rut,
                "serie": series.serie,
                "nemotecnico": series.nemotecnico,
                "desde": series.start.fecha.isoformat(),
                "hasta": series.end.fecha.isoformat(),
                "n_puntos": len(series.points),
                "retorno_periodo_twr": chained,
                "retorno_periodo_directo": direct,
                "fuente": series.source,
                # Siempre False hasta que exista el Eligibility Framework:
                # Performance/Risk leen esta clave para decidir si pueden
                # calcular métricas relativas (Excess Return, TE, Beta).
                "elegibilidad_verificada": False,
                "nota_elegibilidad": ELIGIBILITY_NOTE,
            },
        )

    def _run_eligibility(self, case) -> EngineResult:
        """
        Modo cartera: aplica el AFI Benchmark Eligibility Framework (8
        dimensiones, `engines/eligibility.py`) a cada candidato, en el orden
        recibido, contra el perfil del portafolio. El primero que habilita la
        comparación queda como benchmark del caso; los demás se informan con
        la dimensión exacta que falló (D10).
        """
        from afi_quant.engines.base import parameter_value
        from afi_quant.engines.eligibility import check_eligibility

        params = {name: parameter_value(case, name) for name in (
            "benchmark_critical_dimensions", "benchmark_partial_allows_comparison",
            "benchmark_risk_ratio_max", "benchmark_allocation_max_distance_pct",
            "benchmark_liquidity_max_gap_pct")}
        portfolio = case.input_data["portfolio_profile"]
        checks = [check_eligibility(portfolio, c, params) for c in case.input_data["benchmark_candidates"]]
        chosen = next((c for c in checks if c["habilita_comparacion"]), None)
        return EngineResult(
            engine_name=self.name,
            values={
                "candidatos": checks,
                "nemotecnico": chosen["benchmark"] if chosen else None,
                "elegibilidad_verificada": chosen is not None,
                "estado_elegibilidad": chosen["estado"] if chosen else "no_elegible",
                "benchmark_del_caso": chosen["benchmark"] if chosen else None,
                "parametros": params,
            },
        )


def certified_benchmark(case) -> tuple[AdjustedSeries | None, str | None]:
    """
    Gate que usan Performance y Risk antes de cualquier métrica relativa.

    Devuelve (serie, None) solo si el Motor de Benchmark ya corrió en este
    caso y certificó la elegibilidad; si no, (None, motivo). Hoy siempre
    devuelve el motivo — ver ELIGIBILITY_NOTE.
    """
    result = case.engine_results.get(BenchmarkEngine.name)
    if result is None:
        return None, (
            "El Motor de Benchmark no corrió antes en este caso — sin su gate "
            "no hay contra qué comparar."
        )
    if result.insufficient_data:
        return None, f"El Motor de Benchmark no produjo resultado: {result.insufficient_data_reason}"
    if not result.values.get("elegibilidad_verificada"):
        return None, (
            f"El benchmark candidato ({result.values['nemotecnico']}) no tiene "
            "elegibilidad certificada (Principio 7)."
        )
    return case.input_data["benchmark_index_series"], None
