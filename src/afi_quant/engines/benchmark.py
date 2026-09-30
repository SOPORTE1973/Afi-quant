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
                "nota_elegibilidad": ELIGIBILITY_NOTE,
            },
        )
