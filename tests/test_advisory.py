"""
Tests de lo que exige la metodología para asesorar: elegibilidad de
benchmark (QM XII), tracking error (QM V), flujo de rebalanceo con
alternativas (DF 6.8), escenarios en cinco dimensiones (QM XI), catálogo
de información (DF 4-5) y flujos del cliente (QM IV).
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from afi_quant.clients.ips import evaluate_catalog
from afi_quant.data.quality import PARAMS as QUALITY_PARAMS, check_series
from afi_quant.decision.recommendation import LEVEL3_ELEMENTS, NO_ALTERNATIVES, recommendation_layer
from afi_quant.decision.tradeoff import REBALANCING_DIMENSIONS, detect_tradeoffs
from afi_quant.data.fixtures import singular_global_equities
from afi_quant.engines.eligibility import ComparableProfile, check_eligibility
from afi_quant.engines.relative import relative_metrics, te_decomposition
from afi_quant.engines.scenario import episode_path, episode_returns
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


def test_every_rebalance_is_a_wm_decision_with_level3_evidence(lifecycle):
    rebalances = [e for e in lifecycle.ledger if e["tipo"] == "rebalanceo"]
    assert rebalances
    decided = [c for c in lifecycle.cases if c.wm_decision]
    assert decided and all(c.wm_decision["simulada"] for c in decided)
    for c in decided:
        for flow in c.alternatives.values():
            # DF v1.1 4.2: número variable, "no actuar" siempre visible
            assert "A" in flow["alternativas"] and set(flow["alternativas"]) <= {"A", "B", "C"}
            assert flow["nivel"] == 3
            chosen = flow["alternativas"][flow["recomendada"]]
            assert chosen["admisible"]
            assert all(flow["elementos_nivel_3"][e] for e in LEVEL3_ELEMENTS)
            assert "regla" in flow["tradeoffs"]


def test_rebalance_tradeoffs_show_both_directions(lifecycle):
    jan = next(e for e in lifecycle.events if e.tipo == "revision" and e.fecha == date(2026, 1, 31))
    tos = jan.detalle["flujos"]["jubilacion"]["tradeoffs"]["tradeoffs"]
    assert tos and all(t["mejora"] and t["empeora"] for t in tos)
    assert all(len(t) >= 9 for t in tos)


def test_recommendation_layer_levels():
    alts = {"A": {"nombre": "a"}, "B": {"nombre": "b"}}
    full = {e: "x" for e in LEVEL3_ELEMENTS}
    none = recommendation_layer(alternatives={}, candidates=[], criterion="c", choose=min, elements=full)
    assert none["nivel"] == 1 and none["recomendacion"] == NO_ALTERNATIVES
    blocked = recommendation_layer(alternatives=alts, candidates=["B"], criterion="c", choose=min,
                                   elements=full, blocking_missing=["IPS"])
    assert blocked["nivel"] == 2 and blocked["recomendada"] is None
    gap = recommendation_layer(alternatives=alts, candidates=["B"], criterion="c", choose=min,
                               elements={**full, "sensibilidad": None})
    assert gap["nivel"] == 2 and "sensibilidad" in gap["motivo_nivel"]
    ok = recommendation_layer(alternatives=alts, candidates=["B"], criterion="c", choose=min, elements=full)
    assert ok["nivel"] == 3 and ok["recomendada"] == "B" and "Bajo el criterio" in ok["recomendacion"]


def test_tradeoff_detection_does_not_weigh_dimensions():
    alts = {"A": {"volatilidad_ex_ante": 0.08, "prob_exito": 0.70, "rotacion_clp": 0},
            "B": {"volatilidad_ex_ante": 0.06, "prob_exito": 0.65, "rotacion_clp": 5_000_000},
            "C": {"volatilidad_ex_ante": 0.09, "prob_exito": 0.60, "rotacion_clp": 1_000}}
    out = detect_tradeoffs(alts, "A", REBALANCING_DIMENSIONS)
    keys = [t["alternativa"] for t in out["tradeoffs"]]
    assert keys == ["B"]  # C empeora todo: no es trade-off, es peor
    t = out["tradeoffs"][0]
    assert any("Volatilidad" in s for s in t["mejora"]) and any("Probabilidad" in s for s in t["empeora"])
    assert out["umbral"] is None and "OQ4" in out["nota"]


def test_construction_offers_alternative_portfolios(lifecycle):
    onb = lifecycle.cases[0].alternatives
    assert onb["emergencia"]["nivel"] == 1  # un solo vehículo elegible: nada que comparar
    jub = onb["jubilacion"]
    assert jub["nivel"] == 3 and jub["recomendada"] == "MVO"
    assert jub["alternativas"]["MVO"]["pesos"] == lifecycle.onboarding_results["construction"]["sleeves"]["jubilacion"]["pesos"]
    erc = jub["alternativas"]["ERC"]["contribucion_riesgo"]
    assert max(erc.values()) - min(erc.values()) < 1e-6


def test_reverse_stress_is_linear_in_the_breach_limit(lifecycle):
    inv = lifecycle.closing_results["scenario"]["inverso"]
    s = inv["escenario_stress_escalado"]
    assert s["perdida_escenario"] * s["multiplicador"] == pytest.approx(inv["limite"])
    rv = inv["renta_variable_en_bloque"]
    assert rv["exposicion"] * rv["shock_necesario"] == pytest.approx(-inv["limite"])


def test_data_quality_flags_reversals_and_stale_runs():
    class P:
        def __init__(self, d, v):
            self.fecha, self.valor_cuota = d, v
    base = date(2024, 1, 1)
    rng = random.Random(3)
    vals, v = [], 100.0
    for _ in range(120):
        v *= 1 + rng.gauss(0.0002, 0.001)
        vals.append(v)
    vals[90] *= 1.05          # salto que se revierte al día siguiente
    vals[100:103] = [vals[99]] * 3  # NAV repetido
    pts = [P(base + timedelta(days=i), x) for i, x in enumerate(vals)]
    rep = check_series("X", pts, {k: SIMULATION_VALUES[k] for k in QUALITY_PARAMS})
    assert [o["fecha"] for o in rep.outliers] == [pts[90].fecha]
    assert rep.stale_runs and rep.stale_runs[0]["n_obs"] >= 3
    assert rep.estado == "pending_validation"
    assert check_series("X", pts, {}).no_evaluado == list(QUALITY_PARAMS)


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


def test_crisis_path_ends_where_the_point_to_point_episode_does():
    u = default_universe()
    vals = {"MM": 16e6, "DP": 62e6, "RVL": 38e6, "RVG": 56e6}
    d0, d1 = date(2020, 2, 21), date(2020, 3, 23)
    path = episode_path(u, vals, d0, d1)
    rets = episode_returns({k: u[k] for k in vals}, d0, d1)
    point = sum(v * (1 + rets[k]["retorno"]) for k, v in vals.items()) / sum(vals.values()) - 1
    assert path["retorno_al_fin"] == pytest.approx(point)
    assert path["caida_maxima"] <= path["retorno_al_fin"]
    assert path["fecha_recuperacion"] is None or path["fecha_recuperacion"] > path["fecha_fondo"]
    assert path["fuentes"]["DP"] == "sustituto (MM)"


def test_crisis_path_declares_flat_when_substitute_has_no_data():
    u = default_universe()
    path = episode_path(u, {"MM": 1e6, "DP": 1e6, "RVL": 1e6}, date(2019, 10, 17), date(2019, 11, 14))
    assert path["fuentes"]["MM"] == "sin dato: plano" and path["fuentes"]["DP"] == "sin dato: plano"
