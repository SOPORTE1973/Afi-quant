"""
Tests de construcción de cartera, diversificación, liquidez, metas y del
ciclo de vida simulado (cliente ficticio sobre precios reales).
"""

from __future__ import annotations

import math
import random
from dataclasses import replace
from datetime import date

import pytest

from afi_quant.engines.cma import (
    CMA, LEDOIT_WOLF, MonthlyHistory, build_cma, estimate_cma, ledoit_wolf_intensity, monthly_history,
)
from afi_quant.engines.construction import ConstructionEngine, optimize_grid
from afi_quant.engines.diversification import hhi, risk_contributions
from afi_quant.engines.goals import bootstrap_paths
from afi_quant.engines.performance import twr_with_flows, xirr
from afi_quant.orchestrator.decision_case import DecisionCase
from afi_quant.portfolio.universe import default_universe
from afi_quant.registries.parameter_registry import PARAMETER_REGISTRY, get_parameter
from afi_quant.simulation.lifecycle import LifecycleSimulation, run_lifecycle
from afi_quant.simulation.parameters import (
    ONBOARDING_DATE,
    SIMULATION_SOURCE,
    SIMULATION_VALUES,
    simulation_registry,
    synthetic_client,
)


@pytest.fixture(scope="module")
def universe():
    return default_universe()


@pytest.fixture(scope="module")
def lifecycle():
    return run_lifecycle()


def _toy_cma() -> CMA:
    keys = ["A", "B"]
    cov = {("A", "A"): 0.01, ("B", "B"): 0.04, ("A", "B"): 0.0, ("B", "A"): 0.0}
    return CMA(keys=keys, mu={"A": 0.05, "B": 0.10}, mu_historico={}, ancla="A",
               sharpe_comun=0.0, cov=cov, corr={}, n_obs=36,
               desde=date(2020, 1, 31), hasta=date(2022, 12, 31))


# --- fórmulas -------------------------------------------------------------

def test_optimize_grid_respects_constraints():
    cma = _toy_cma()
    w = optimize_grid(cma, ["A", "B"], delta=0.0, vol_cap=0.15, max_weight={"A": 1, "B": 1})
    # Sin aversión al riesgo gana el mayor retorno que cabe bajo 15% de volatilidad.
    assert math.sqrt(cma.portfolio_variance(w)) <= 0.15 + 1e-12
    assert sum(w.values()) == pytest.approx(1.0)
    assert w["B"] == pytest.approx(0.70)  # 0.75 daría vol 15.2%

    capped = optimize_grid(cma, ["A", "B"], delta=0.0, vol_cap=1.0, max_weight={"A": 1, "B": 0.4})
    assert capped["B"] == pytest.approx(0.4)


def test_optimize_grid_returns_none_when_infeasible():
    assert optimize_grid(_toy_cma(), ["B"], delta=3, vol_cap=0.05, max_weight={"B": 1}) is None


def test_risk_contributions_sum_to_one_and_hhi():
    cma = _toy_cma()
    rc = risk_contributions({"A": 0.5, "B": 0.5}, cma.cov)
    assert sum(rc.values()) == pytest.approx(1.0)
    assert rc["B"] == pytest.approx(0.8)  # 0.25·0.04 / (0.25·0.01 + 0.25·0.04)
    assert hhi({"A": 0.5, "B": 0.5}) == pytest.approx(0.5)


def test_xirr_and_twr_with_flows_by_hand():
    assert xirr([(date(2025, 1, 1), -100.0), (date(2026, 1, 1), 110.0)]) == pytest.approx(0.10, abs=1e-6)
    # 100 -> 110 (+10%), aporte de 90 -> 200 -> 180 (-10%): TWR = 1.1·0.9 − 1
    rets = twr_with_flows([(100.0, 110.0), (200.0, 180.0)])
    assert rets == pytest.approx([0.10, -0.10])


def test_bootstrap_is_deterministic(universe):
    h = monthly_history(universe, ONBOARDING_DATE, 36)
    w = {"MM": 0.5, "RVL": 0.5}
    a = bootstrap_paths(h, w, 24, 200, 6, 1_000_000, 10_000)
    b = bootstrap_paths(h, w, 24, 200, 6, 1_000_000, 10_000)
    assert a == b


# --- datos y parámetros -----------------------------------------------------

def test_cma_uses_no_data_after_decision_date(universe):
    h = monthly_history(universe, ONBOARDING_DATE, 36)
    assert len(h) == 36
    assert max(h.months) <= ONBOARDING_DATE


def _synthetic_history(n_months: int, seed: int = 7) -> MonthlyHistory:
    rng = random.Random(seed)
    common = [rng.gauss(0, 0.02) for _ in range(n_months)]
    returns = {k: [0.6 * c + rng.gauss(0, s) for c in common]
               for k, s in {"A": 0.01, "B": 0.02, "C": 0.03, "D": 0.015}.items()}
    months = [date(2000 + i // 12, i % 12 + 1, 28) for i in range(n_months)]
    return MonthlyHistory(keys=list(returns), months=months, returns=returns)


def test_ledoit_wolf_intensity_shrinks_less_with_more_data():
    short, long_ = _synthetic_history(36), _synthetic_history(2400)
    d_short, d_long = ledoit_wolf_intensity(short), ledoit_wolf_intensity(long_)
    assert 0 <= d_long < d_short <= 1
    assert d_long < 0.1


def test_cma_applies_calibrated_intensity(universe):
    h = monthly_history(universe, ONBOARDING_DATE, 36)
    cma = estimate_cma(h, 0.5, LEDOIT_WOLF)
    assert cma.shrinkage_intensidad == pytest.approx(ledoit_wolf_intensity(h))
    assert cma.shrinkage_metodo.startswith("Ledoit-Wolf")
    fixed = estimate_cma(h, 0.5, 0.3)
    assert fixed.shrinkage_intensidad == 0.3
    for i in h.keys:  # las varianzas no se tocan; solo las covarianzas cruzadas
        assert cma.cov[(i, i)] == pytest.approx(fixed.cov[(i, i)])


def test_simulation_values_never_leak_into_institutional_registry():
    sim = simulation_registry()
    for name in SIMULATION_VALUES:
        institutional = get_parameter(name, PARAMETER_REGISTRY)
        if name not in ("liquidity_bucket_short_days", "liquidity_bucket_medium_days"):
            assert institutional.value is None, name
        assert get_parameter(name, sim).source == SIMULATION_SOURCE


def test_construction_blocks_with_institutional_registry(universe):
    cma = build_cma(universe, ONBOARDING_DATE, 36, lambda n: get_parameter(n, simulation_registry()).value)
    case = DecisionCase(input_data=dict(
        client_profile=synthetic_client(), cma_estimate=cma, vehicle_universe=universe,
        as_of_date=ONBOARDING_DATE,  # sin parameter_registry -> usa el institucional (sin valores)
    ))
    result = ConstructionEngine().run(case)
    assert result.insufficient_data is True
    assert "vol_cap_long_pct" in result.insufficient_data_reason


# --- ciclo de vida ----------------------------------------------------------

def test_lifecycle_flows_add_up(lifecycle):
    s = lifecycle.summary
    months = s["meses"]
    assert months == 23
    # 150M iniciales + 1,5M mensuales por 23 meses (el aporte del pie pasa a jubilación).
    assert s["aportado"] == pytest.approx(150_000_000 + 1_500_000 * months)
    assert s["retirado"] == pytest.approx(60_000_000)
    assert sum(s["valor_por_meta"].values()) == pytest.approx(s["valor_final"])
    assert sum(s["pesos_actuales"].values()) == pytest.approx(1.0)


def test_lifecycle_key_events(lifecycle):
    by_type = {}
    for e in lifecycle.events:
        by_type.setdefault(e.tipo, []).append(e)
    assert by_type["onboarding"][0].fecha == ONBOARDING_DATE
    glide = by_type["cambio_horizonte"][0]
    assert glide.fecha == date(2025, 7, 31) and glide.detalle["pesos"] == {"MM": 1.0}
    assert by_type["meta_cumplida"][0].fecha == date(2026, 6, 30)
    assert by_type["cierre"][0].fecha == date(2026, 9, 29)
    # Toda decisión quedó ligada a un Decision Case con explicación.
    case_ids = {c.case_id for c in lifecycle.cases}
    for e in lifecycle.events:
        if e.case_id:
            assert e.case_id in case_ids
            assert e.explicacion


def test_lifecycle_realized_volatility_is_declared_not_invented(lifecycle):
    assert "volatilidad_anual" in lifecycle.summary["riesgo_no_calculado"]


def test_lifecycle_is_deterministic(lifecycle):
    assert run_lifecycle().summary == lifecycle.summary


def test_drawdown_alert_triggers_with_a_tight_threshold(universe):
    params = simulation_registry()
    params.parameters = [replace(p, value=0.5) if p.name == "drawdown_alert_pct" else p
                         for p in params.parameters]
    result = LifecycleSimulation(synthetic_client(), universe, params, ONBOARDING_DATE).run()
    alerts = [e for e in result.events if e.tipo == "alerta_caida"]
    assert alerts
    assert any(e.titulo == "Revisión extraordinaria" for e in result.events)
