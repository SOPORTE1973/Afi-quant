"""Motor de Riesgo (CORE) — stub de Fase 3.1. Ver performance.py para el patrón."""

from __future__ import annotations

from afi_quant.engines.base import EngineResult


class RiskEngine:
    name = "risk"
    required_critical_data = [
        "nav_series_native_frequency",
    ]

    def run(self, case) -> EngineResult:
        # TODO(Fase 3.1): Volatilidad histórica, Downside Deviation, Max
        # Drawdown, Tracking Error, Beta, VaR y Expected Shortfall
        # históricos (todos CORE en el Model Governance Registry).
        return EngineResult(
            engine_name=self.name,
            insufficient_data=True,
            insufficient_data_reason=(
                "Motor de Riesgo aún no implementado — pendiente de Fase 1 "
                "(datos reales) y del cierre del audit de infraestructura."
            ),
        )
