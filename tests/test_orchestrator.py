"""
Tests del pipeline del Orchestrator (M02) + Completeness Gate (M08).

Cubre el camino feliz mínimo: un caso se planea, el gate lo bloquea
por falta de datos (comportamiento correcto — no inventa resultados),
y separadamente, un caso con datos "disponibles" simulados corre los
motores stub y recibe resultados marcados como insuficientes (porque
los motores reales de Fase 3.1 todavía no están implementados).
"""

from __future__ import annotations

from afi_quant.completeness.gate import CompletenessReport
from afi_quant.engines.base import EngineRegistry
from afi_quant.engines.benchmark import BenchmarkEngine
from afi_quant.engines.performance import PerformanceEngine
from afi_quant.engines.risk import RiskEngine
from afi_quant.orchestrator.decision_case import DecisionCase, Orchestrator
from afi_quant.orchestrator.states import DecisionCaseState


def _make_orchestrator() -> Orchestrator:
    registry = EngineRegistry()
    registry.register(PerformanceEngine())
    registry.register(RiskEngine())
    registry.register(BenchmarkEngine())
    return Orchestrator(registry)


def test_plan_rejects_unknown_engine():
    orchestrator = _make_orchestrator()
    case = DecisionCase(trigger="revisión periódica")
    try:
        orchestrator.build_plan(case, engines=["motor_inventado"], reason="test")
        assert False, "debería haber lanzado ValueError"
    except ValueError:
        pass


def test_completeness_gate_blocks_when_data_missing():
    orchestrator = _make_orchestrator()
    case = DecisionCase(trigger="revisión periódica")
    orchestrator.build_plan(case, engines=["performance"], reason="revisión periódica")

    report = CompletenessReport.evaluate(
        required_critical=["nav_series_native_frequency", "cash_flows_dated_classified"],
        required_optional=[],
        available=[],  # nada disponible todavía — esperado en este punto del proyecto
    )
    orchestrator.apply_completeness_gate(case, report)

    assert case.state == DecisionCaseState.DATA_BLOCKED
    assert "nav_series_native_frequency" in case.completeness_report.missing


def test_engines_run_declare_insufficient_data_when_stubbed():
    orchestrator = _make_orchestrator()
    case = DecisionCase(trigger="revisión periódica")
    orchestrator.build_plan(
        case, engines=["performance", "risk", "benchmark"], reason="revisión periódica"
    )

    # Simulamos que el Completeness Gate SÍ aprueba (todos los datos
    # declarados como disponibles), para probar que el motor stub —
    # aunque el gate pase — sigue sin inventar un resultado.
    report = CompletenessReport.evaluate(
        required_critical=["nav_series_native_frequency", "cash_flows_dated_classified"],
        required_optional=[],
        available=["nav_series_native_frequency", "cash_flows_dated_classified"],
    )
    orchestrator.apply_completeness_gate(case, report)
    assert case.state == DecisionCaseState.ANALYZING

    orchestrator.run_engines(case)

    for engine_name in ("performance", "risk", "benchmark"):
        result = case.engine_results[engine_name]
        assert result.insufficient_data is True
        assert result.insufficient_data_reason
