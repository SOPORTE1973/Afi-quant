"""
Tests de lo que exige la metodología para asesorar: elegibilidad de
benchmark (QM XII), tracking error (QM V), flujo de rebalanceo con
alternativas (DF 6.8), escenarios en cinco dimensiones (QM XI), catálogo
de información (DF 4-5) y flujos del cliente (QM IV).
"""

from __future__ import annotations

from datetime import date

import pytest

from afi_quant.clients.ips import evaluate_catalog
from afi_quant.data.fixtures import singular_global_equities
from afi_quant.engines.eligibility import ComparableProfile, check_eligibility
from afi_quant.engines.relative import relative_metrics, te_decomposition
from afi_quant.engines.scenario import episode_returns
from afi_quant.flows.rebalancing import partial_weights
from afi_quant.portfolio.analytics import multi_period_returns
from afi_quant.portfolio.universe import default_universe
from afi_quant.simulation.lifecycle import run_lifecycle
from afi_quant.simulation.parameters import SIMULATION_VALUES, synthetic_client, synthetic_ips

PARAMS = {k: SIMULATION_VALUES[k] for k in (
    "benchmark_critical_dimensions", "benchmark_partial_allows_comparison", "benchmark_risk_ratio_max",
    "benchmark_allocation_max_distance_pct", "benchmark_liquidity_max_gap_pct")}


@pytest.fixture(scope="module")
def lifecycle():
    return run_lifecycle()


def _profile(**kw):
    base = dict(nombre="x", tipo="policy", objetivo="multi-meta", composicion={"RV": 0.4, "RF": 0.6},
                volatilidad=0.06, moneda="CLP", peso_fuera_0_3m=0.0, horizonte="multi",
                costos="neto", restricciones="libre")
    base.update(kw)
    return ComparableProfile(**base)


# --- Benchmark Eligibility Framework ---------------------------------------

def test_eligible_only_when_all_eight_dimensions_pass():
    res = check_eligibility(_profile(nombre="cartera"), _profile(), PARAMS)
    assert res["estado"] == "elegible" and res["habilita_comparacion"]
    assert len(res["dimensiones"]) == 8


def test_critical_dimension_not_verifiable_blocks_comparison():
    # Sin información de moneda (crítica según D10) no se asume comparabilidad.
    res = check_eligibility(_profile(), _profile(moneda=None), PARAMS)
    assert res["estado"] == "no_elegible"
    assert not res["habilita_comparacion"]
    assert "sin ranking" in res["regla"] or "no se genera ranking" in res["regla"]


def test_similar_numbers_do_not_make_a_peer_comparable():
    # El caso AFP de QM XII: mismo riesgo y moneda, pero otro objetivo y régimen.
    afp = _profile(objetivo="previsional", restricciones="DL 3.500", peso_fuera_0_3m=1.0)
    res = check_eligibility(_profile(), afp, PARAMS)
    assert res["estado"] == "no_elegible"
    assert {"objetivo", "restricciones", "liquidez"} <= set(res["no_cumple"])


def test_substitute_component_makes_benchmark_partial():
    res = check_eligibility(_profile(), _profile(sustitutos=["Deuda Privada"]), PARAMS)
    assert res["estado"] == "parcial"
    assert res["habilita_comparacion"]   # porque la simulación lo permite (ESFS-14 abierto)


def test_lifecycle_benchmark_candidates(lifecycle):
    cands = {c["benchmark"]: c for c in lifecycle.advisory["benchmark"]["candidatos"]}
    assert cands["Policy benchmark (SAA vigente)"]["estado"] == "parcial"
    assert cands["Sistema AFP, Fondo C"]["estado"] == "no_elegible"
    assert cands["S&P/CLX IPSA (vía FM Security Index Fund)"]["estado"] == "no_elegible"


# --- Tracking error ----------------------------------------------------------

def test_tracking_error_blocked_below_36_observations():
    months = [date(2024, m, 28) for m in range(1, 13)]
    res = relative_metrics([0.01] * 12, [0.0] * 12, months)
    assert "tracking_error" not in res and "tracking_error_bloqueado" in res


def test_te_decomposition_sums_to_one():
    a = [0.01, -0.02, 0.015, 0.0, 0.005, -0.01]
    b = [0.002, 0.001, -0.003, 0.004, 0.0, 0.001]
    parts = te_decomposition({"A": a, "B": b}, {"A": 0.5, "B": 0.5})
    assert sum(parts.values()) == pytest.approx(1.0)


def test_lifecycle_te_uses_36_to_60_months(lifecycle):
    av = lifecycle.advisory["relativo"]["asignacion_vigente"]
    assert 36 <= av["n_obs"] <= 60
    assert av["tracking_error"] > 0
    assert sum(av["descomposicion_te"].values()) == pytest.approx(1.0)
    realized = lifecycle.advisory["relativo"]["realizado"]
    assert "tracking_error_bloqueado" in realized   # 23 meses < 36


# --- Rebalancing Decision Flow ----------------------------------------------

def test_partial_weights_sum_to_one_and_stay_in_band():
    current = {"A": 0.70, "B": 0.20, "C": 0.10}
    target = {"A": 0.50, "B": 0.30, "C": 0.20}
    w = partial_weights(current, target, 0.025)
    assert sum(w.values()) == pytest.approx(1.0)
    assert all(abs(w[k] - target[k]) <= 0.05 + 1e-9 for k in target)


def test_every_rebalance_is_a_wm_decision_with_three_alternatives(lifecycle):
    rebalances = [e for e in lifecycle.ledger if e["tipo"] == "rebalanceo"]
    assert rebalances
    decided = [c for c in lifecycle.cases if c.wm_decision]
    assert decided and all(c.wm_decision["simulada"] for c in decided)
    for c in decided:
        for flow in c.alternatives.values():
            assert set(flow["alternativas"]) == {"A", "B", "C"}
            chosen = flow["alternativas"][flow["recomendada"]]
            assert chosen["admisible"]


def test_glide_path_rejects_partial_alternative_with_ineligible_vehicles(lifecycle):
    july = next(e for e in lifecycle.events if e.tipo == "revision" and e.fecha == date(2025, 7, 31))
    flow = july.detalle["flujos"]["pie"]
    assert flow["alternativas"]["B"]["admisible"] is False
    assert flow["recomendada"] == "C"


# --- Escenarios ----------------------------------------------------------------

def test_episode_uses_declared_substitute_when_vehicle_has_no_history():
    u = default_universe()
    rets = episode_returns(u, date(2020, 2, 21), date(2020, 3, 23))
    assert rets["DP"]["fuente"] == "sustituto (MM)"
    assert rets["RVL"]["fuente"] == "observado" and rets["RVL"]["retorno"] < -0.2


def test_scenarios_report_five_dimensions(lifecycle):
    stress = lifecycle.advisory["stress"]
    assert set(stress["hipoteticos"]) == {"base", "optimista", "adverso", "stress"}
    for sc in (*stress["hipoteticos"].values(), *stress["historicos"].values()):
        assert {"retorno", "var95_1m_post", "lcr_0_3m", "hhi_post", "metas"} <= set(sc)
    s = stress["hipoteticos"]["stress"]
    w = lifecycle.summary["pesos_actuales"]
    expected = sum(w[k] * s["shock_por_vehiculo"][k] for k in w)
    assert s["retorno"] == pytest.approx(expected)
    assert s["rescates_suspendidos"] == ["DP"]


# --- Catálogo de información -----------------------------------------------------

def test_catalog_blocks_missing_critical_and_warns_on_synthetic():
    ctx = {"client": synthetic_client(), "ips": synthetic_ips(), "universe": default_universe(),
           "as_of": date(2026, 9, 29), "synthetic_fields": {"IPS vigente y firmado"}}
    rows = {r["variable"]: r for r in evaluate_catalog(ctx)}
    assert rows["Estado en Approved List + ODD"]["comportamiento"] == "BLOQUEO"
    assert rows["Inversiones existentes fuera de AFI"]["comportamiento"] == "ADVERTENCIA"
    assert rows["IPS vigente y firmado"]["estado"] == "degraded"
    assert rows["Moneda base"]["estado"] == "available"


# --- Flujos y rentabilidad por activo -------------------------------------------

def test_vehicle_gains_add_up_to_client_gain(lifecycle):
    rent = lifecycle.advisory["rentabilidad_activos"]
    flows = lifecycle.advisory["flujos"]
    total_gain = sum(v["ciclo"]["ganancia_clp"] for v in rent.values())
    assert total_gain == pytest.approx(flows["ganancia_neta"], rel=1e-9)
    ext = [e for e in flows["libro"] if e["externo"]]
    assert sum(e["monto"] for e in ext if e["monto"] > 0) == pytest.approx(lifecycle.summary["aportado"])


def test_multi_period_returns_match_connector():
    # Publicado por el conector para ETF Singular Global Equities al 2026-09-29: y1 = 17,0745%.
    mp = multi_period_returns(singular_global_equities(), date(2026, 9, 29))
    assert mp["1a"] * 100 == pytest.approx(17.074533879455124, abs=1e-6)
