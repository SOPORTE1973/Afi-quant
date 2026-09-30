"""Tests del pipeline de punta a punta (Intake -> Gate -> motores -> Explicación)."""

from __future__ import annotations

from afi_quant.data.fixtures import etf_ipsa, falcom_tactical
from afi_quant.orchestrator.states import DecisionCaseState
from afi_quant.pipeline import run_fund_review


def _full_input():
    return {
        "nav_series_native_frequency": falcom_tactical(),
        "cash_flows_dated_classified": [],
        "benchmark_index_series": etf_ipsa(),
    }


def test_fund_review_runs_all_engines_and_explains():
    case = run_fund_review(_full_input())
    assert case.state == DecisionCaseState.ANALYZING
    assert list(case.engine_results) == ["benchmark", "performance", "risk"]
    assert all(not r.insufficient_data for r in case.engine_results.values())
    assert "CFIFALCTAC rindió 105.79%" in case.explanation
    assert "no sostiene una recomendación" in case.explanation


def test_explanation_is_deterministic():
    # Principio 3: mismos inputs -> mismo texto, siempre.
    assert run_fund_review(_full_input()).explanation == run_fund_review(_full_input()).explanation


def test_gate_blocks_before_any_engine_runs():
    data = _full_input()
    del data["nav_series_native_frequency"]
    case = run_fund_review(data)
    assert case.state == DecisionCaseState.DATA_BLOCKED
    assert case.completeness_report.missing == ["nav_series_native_frequency"]
    assert case.engine_results == {}
    assert case.explanation is None
