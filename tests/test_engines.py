"""
Tests de los motores de Performance y Riesgo.

Dos tipos de prueba:
  - fórmulas sobre números a mano (resultado verificable sin computador)
  - motores sobre datos reales del conector (data/fixtures/), contrastados
    contra las rentabilidades que el propio conector publica para el
    mismo fondo (y1, y3 del 2026-09-29) — así el TWR se valida contra una
    fuente independiente, no contra sí mismo.
"""

from __future__ import annotations

from datetime import date

import pytest

from afi_quant.data.fixtures import etf_ipsa, falcom_tactical
from afi_quant.engines.base import EngineResult
from afi_quant.engines.benchmark import certified_benchmark
from afi_quant.engines.performance import PerformanceEngine
from afi_quant.engines.risk import (
    RiskEngine,
    beta,
    historical_var_es,
    max_drawdown,
    tracking_error,
)
from afi_quant.engines.series import NavPoint, month_end_points, trailing_window
from afi_quant.orchestrator.decision_case import DecisionCase

# Publicado por el conector (rentabilidades de rut 9194, hasta 2026-09-29).
CONNECTOR_Y1_PCT = 20.05734403931867
CONNECTOR_Y3_PCT = 105.79103603973947


def _pts(values, start=date(2026, 1, 1)):
    return [NavPoint(fecha=date.fromordinal(start.toordinal() + i), valor_cuota=v)
            for i, v in enumerate(values)]


def _case(**input_data) -> DecisionCase:
    return DecisionCase(trigger="test", input_data=input_data)


# --- fórmulas ------------------------------------------------------------

def test_max_drawdown_and_recovery_by_hand():
    pts = _pts([100, 120, 90, 110, 125])
    dd = max_drawdown(pts)
    assert dd["max_drawdown"] == pytest.approx(-0.25)  # 120 -> 90
    assert dd["max_drawdown_peak"] == pts[1].fecha.isoformat()
    assert dd["max_drawdown_trough"] == pts[2].fecha.isoformat()
    assert dd["max_drawdown_recuperacion"] == pts[4].fecha.isoformat()
    assert dd["max_drawdown_dias_recuperacion"] == 2


def test_max_drawdown_not_recovered():
    dd = max_drawdown(_pts([100, 80, 90]))
    assert dd["max_drawdown"] == pytest.approx(-0.20)
    assert dd["max_drawdown_recuperacion"] is None


def test_historical_var_es_by_hand():
    returns = [0.01 * i for i in range(-10, 10)]  # 20 obs: -10% ... +9%
    var, es, k = historical_var_es(returns, 0.95)
    assert k == 1
    assert var == pytest.approx(0.10)
    var, es, k = historical_var_es(returns, 0.90)
    assert k == 2
    assert var == pytest.approx(0.09)
    assert es == pytest.approx(0.095)


def test_beta_and_tracking_error_by_hand():
    bench = [0.01, -0.02, 0.03, 0.00]
    fund = [2 * b for b in bench]
    assert beta(fund, bench) == pytest.approx(2.0)
    assert tracking_error(bench, bench) == pytest.approx(0.0)


def test_month_end_points_keeps_last_observation_of_each_month():
    pts = [
        NavPoint(date(2026, 1, 30), 1.0),
        NavPoint(date(2026, 1, 31), 2.0),
        NavPoint(date(2026, 2, 27), 3.0),
    ]
    assert month_end_points(pts) == [pts[1], pts[2]]


def test_trailing_window_refuses_partial_windows():
    bench = etf_ipsa()  # empieza 2025-05-12: no cubre 3 años
    assert trailing_window(bench.points, 1) is not None
    assert trailing_window(bench.points, 3) is None


# --- motores sobre datos reales -----------------------------------------

def test_performance_matches_connector_published_returns():
    result = PerformanceEngine().run(
        _case(nav_series_native_frequency=falcom_tactical(), cash_flows_dated_classified=[])
    )
    assert result.insufficient_data is False
    v = result.values
    assert v["twr_1a"] * 100 == pytest.approx(CONNECTOR_Y1_PCT, abs=1e-9)
    assert v["twr_3a"] * 100 == pytest.approx(CONNECTOR_Y3_PCT, abs=1e-9)
    assert v["cagr"] == pytest.approx((1 + v["twr_periodo"]) ** (1 / v["anos"]) - 1)
    assert v["cagr_periodo_corto"] is False


def test_performance_refuses_undeclared_or_nonempty_cash_flows():
    fund = falcom_tactical()
    missing = PerformanceEngine().run(_case(nav_series_native_frequency=fund))
    assert missing.insufficient_data is True

    with_flows = PerformanceEngine().run(
        _case(nav_series_native_frequency=fund,
              cash_flows_dated_classified=[{"fecha": "2026-01-02", "monto": 1_000_000}])
    )
    assert with_flows.insufficient_data is True
    assert "Fase 1" in with_flows.insufficient_data_reason


def test_performance_blocks_excess_return_without_certified_benchmark():
    result = PerformanceEngine().run(
        _case(nav_series_native_frequency=falcom_tactical(), cash_flows_dated_classified=[])
    )
    assert result.values["excess_return"] is None
    assert "Benchmark no corrió" in result.values["excess_return_bloqueado"]


def test_risk_engine_on_real_data():
    result = RiskEngine().run(_case(nav_series_native_frequency=falcom_tactical()))
    v = result.values
    assert result.insufficient_data is False
    assert v["n_retornos_mensuales"] == 36
    assert 0 < v["volatilidad_anual"] < 1
    assert v["max_drawdown"] < 0
    assert v["var_99_1m"] >= v["var_95_1m"] > 0
    assert v["es_95_1m"] >= v["var_95_1m"]
    # Sin MAR en el Parameter Registry ni benchmark certificado: se declara, no se inventa.
    assert set(v["no_calculado"]) == {"downside_deviation", "tracking_error_beta"}


def test_risk_engine_declares_short_history():
    result = RiskEngine().run(_case(nav_series_native_frequency=etf_ipsa()))
    v = result.values
    assert v["n_retornos_mensuales"] < 36
    assert "volatilidad_anual" not in v
    assert "volatilidad_anual" in v["no_calculado"]
    assert "max_drawdown" in v  # el drawdown no depende de un mínimo de meses


def test_certified_benchmark_gate_opens_only_when_eligibility_verified():
    bench = etf_ipsa()
    case = _case(benchmark_index_series=bench)
    case.engine_results["benchmark"] = EngineResult(
        engine_name="benchmark",
        values={"nemotecnico": "CFIETFIPSA", "elegibilidad_verificada": False},
    )
    series, reason = certified_benchmark(case)
    assert series is None and "certificada" in reason

    case.engine_results["benchmark"].values["elegibilidad_verificada"] = True
    series, reason = certified_benchmark(case)
    assert series is bench and reason is None
