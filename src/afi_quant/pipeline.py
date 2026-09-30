"""
Pipeline de punta a punta para un Decision Case — MVP.

Encadena lo que ya existe, sin agregar cálculo fuera de los motores:

    Intake -> AnalysisPlan (M02) -> Completeness Gate (M08)
           -> motores (Benchmark, Performance, Risk) -> Explanation (M15)

El Completeness Report se arma con lo que cada motor del plan declara en
`required_critical_data` contra las claves presentes en `input_data` —
el gate no adivina qué hace falta, lo lee de los motores.

No avanza a Diagnosis/Recommendation: esos módulos (M11-M14) no existen
todavía, así que el caso queda en ANALYZING con la explicación adjunta.
"""

from __future__ import annotations

from typing import Any

from afi_quant.completeness.gate import CompletenessReport
from afi_quant.engines.base import EngineRegistry
from afi_quant.engines.benchmark import BenchmarkEngine
from afi_quant.engines.performance import PerformanceEngine
from afi_quant.engines.risk import RiskEngine
from afi_quant.explanation.fund_review_rules import build_context, fund_review_layer
from afi_quant.orchestrator.decision_case import DecisionCase, Orchestrator
from afi_quant.orchestrator.states import DecisionCaseState

# Benchmark primero: Performance y Risk leen su resultado como gate.
FUND_REVIEW_ENGINES = ["benchmark", "performance", "risk"]


def default_registry() -> EngineRegistry:
    registry = EngineRegistry()
    registry.register(BenchmarkEngine())
    registry.register(PerformanceEngine())
    registry.register(RiskEngine())
    return registry


def run_fund_review(
    input_data: dict[str, Any],
    *,
    trigger: str = "revisión periódica de fondo",
    client_ref: str | None = None,
    registry: EngineRegistry | None = None,
) -> DecisionCase:
    registry = registry or default_registry()
    orchestrator = Orchestrator(registry)

    case = DecisionCase(trigger=trigger, client_ref=client_ref, input_data=dict(input_data))
    case._log(f"Intake: {trigger}")
    orchestrator.build_plan(case, engines=FUND_REVIEW_ENGINES, reason=trigger)

    required: list[str] = []
    for name in case.plan.engines:
        for key in registry[name].required_critical_data:
            if key not in required:
                required.append(key)
    report = CompletenessReport.evaluate(
        required_critical=required,
        required_optional=[],
        available=[k for k in required if case.input_data.get(k) is not None],
    )
    orchestrator.apply_completeness_gate(case, report)
    if case.state == DecisionCaseState.DATA_BLOCKED:
        return case

    orchestrator.run_engines(case)
    case.explanation = fund_review_layer().explain(build_context(case), separator="\n")
    case._log("Explanation Layer: explicación determinística adjunta")
    return case
