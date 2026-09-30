"""Motor de Benchmark (CORE) — stub de Fase 3.1.

Actúa como gate: Performance y Risk (Excess Return, Tracking Error,
Beta, Brinson-Fachler) dependen de que este motor confirme que el
benchmark es elegible antes de comparar contra él (AFI Benchmark
Eligibility Framework — verificación de 8 dimensiones, es una regla,
no una fórmula).
"""

from __future__ import annotations

from afi_quant.engines.base import EngineResult


class BenchmarkEngine:
    name = "benchmark"
    required_critical_data = [
        "benchmark_index_series",
    ]

    def run(self, case) -> EngineResult:
        # TODO(Fase 3.1): implementar las 8 dimensiones del AFI
        # Benchmark Eligibility Framework. Sin esto, ningún otro motor
        # debería poder comparar contra un benchmark (es un gate, no
        # un motor opcional).
        return EngineResult(
            engine_name=self.name,
            insufficient_data=True,
            insufficient_data_reason=(
                "Motor de Benchmark aún no implementado — pendiente de Fase 1 "
                "(datos reales) y del cierre del audit de infraestructura."
            ),
        )
