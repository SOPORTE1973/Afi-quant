"""
Motor de Performance (CORE) — stub de Fase 3.1.

ESFS-01 Parte 25: Performance, Risk y Benchmark son el primer
sub-fase de motores (3.1) porque son los tres de prioridad
crítica/MVP obligatorio, y Performance/Risk no pueden reportarse de
forma responsable sin que Benchmark ya opere como gate.

Implementa por ahora TWR y Excess Return (Model Governance Registry:
ambos CORE). El cálculo real requiere:
  - serie de NAV por vehículo a frecuencia nativa
  - cash flows fechados y clasificados
  - TWR del benchmark elegible (gate del Motor de Benchmark)

Sin esos tres, el motor declara `insufficient_data` — nunca inventa
un número (QM Principio 8).
"""

from __future__ import annotations

from afi_quant.engines.base import EngineResult


class PerformanceEngine:
    name = "performance"
    required_critical_data = [
        "nav_series_native_frequency",
        "cash_flows_dated_classified",
    ]

    def run(self, case) -> EngineResult:
        # TODO(Fase 3.1): implementar TWR real una vez que el
        # Completeness Gate confirme que required_critical_data está
        # disponible para el caso. Hasta entonces, este stub siempre
        # declara datos insuficientes — es la postura correcta según
        # QM Principio 8, no un placeholder a ignorar.
        return EngineResult(
            engine_name=self.name,
            insufficient_data=True,
            insufficient_data_reason=(
                "Motor de Performance aún no implementado — pendiente de Fase 1 "
                "(datos reales) y del cierre del audit de infraestructura."
            ),
        )
