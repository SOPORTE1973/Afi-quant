"""
Tests del pipeline del Orchestrator (M02) + Completeness Gate (M08).

Cubre el camino feliz mínimo: un caso se planea, el gate lo bloquea
por falta de datos (comportamiento correcto — no inventa resultados),
y separadamente, un caso con datos "disponibles" simulados pero sin
series reales en input_data corre los motores y recibe resultados
marcados como insuficientes. El caso con datos reales está en
test_pipeline.py.
"""

from __future__ import annotations

from afi_quant.completeness.gate import CompletenessReport
from afi_quant.data.benchmark_fixtures.etf_singular_ipsa import ETF_SINGULAR_IPSA_SERIES
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


def test_engines_declare_insufficient_data_when_input_data_is_empty():
    orchestrator = _make_orchestrator()
    case = DecisionCase(trigger="revisión periódica")
    orchestrator.build_plan(
        case, engines=["performance", "risk", "benchmark"], reason="revisión periódica"
    )

    # Simulamos que el Completeness Gate SÍ aprueba (todos los datos
    # declarados como disponibles) pero input_data viene vacío, para
    # probar que cada motor — aunque el gate pase — no inventa un
    # resultado sin la serie real.
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


def test_benchmark_engine_computes_real_return_when_data_is_present():
    # A diferencia del resto: cuando SÍ hay una serie real en
    # case.input_data, el motor de Benchmark calcula un retorno real
    # (no "insufficient_data") — performance/risk siguen sin datos.
    orchestrator = _make_orchestrator()
    case = DecisionCase(trigger="revisión periódica")
    orchestrator.build_plan(case, engines=["benchmark"], reason="revisión periódica")

    report = CompletenessReport.evaluate(
        required_critical=["benchmark_index_series"],
        required_optional=[],
        available=["benchmark_index_series"],
    )
    orchestrator.apply_completeness_gate(case, report)
    assert case.state == DecisionCaseState.ANALYZING

    case.input_data["benchmark_index_series"] = ETF_SINGULAR_IPSA_SERIES
    orchestrator.run_engines(case)

    result = case.engine_results["benchmark"]
    assert result.insufficient_data is False
    assert result.values["nemotecnico"] == "CFIETFIPSA"
    assert result.values["n_puntos"] == 12
    assert result.values["retorno_periodo_directo"] < 0
    assert "Elegibilidad NO verificada" in result.values["nota_elegibilidad"]
