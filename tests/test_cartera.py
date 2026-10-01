"""
Cartera: posiciones por meta y fondo, vintage del capital y diversificación por
dimensión (DF 7.1: holdings → asset class → moneda → geografía → vintage → correlación
→ aporte al riesgo → factores → concentración).
"""

from __future__ import annotations

import math

import pytest

from afi_quant.due_diligence.review import load_dossiers
from afi_quant.engines.diversification import (
    diversification_ratio, effective_number_of_bets, exposure_breakdown, factor_exposure,
    look_through_issuers, risk_contributions,
)
from afi_quant.portfolio.analytics import capital_vintages
from afi_quant.portfolio.universe import default_universe
from afi_quant.simulation.lifecycle import run_lifecycle


@pytest.fixture(scope="module")
def life():
    return run_lifecycle()


def test_positions_reconcile_with_portfolio_and_gains(life):
    live = [p for p in life.positions if p["vigente"]]
    assert sum(p["valor"] for p in live) == pytest.approx(life.summary["valor_final"], rel=1e-9)
    gains = sum(p["ganancia_no_realizada"] + p["ganancia_realizada"] for p in life.positions)
    assert gains == pytest.approx(life.advisory["flujos"]["ganancia_neta"], rel=1e-6)
    assert all(p["primera_compra"] is not None for p in life.positions)


def test_capital_vintages_add_up_to_final_value(life):
    v = capital_vintages(life.rows)
    assert sum(c["valor"] for c in v) == pytest.approx(life.rows[-1].total, rel=1e-9)
    assert [c["anio"] for c in v] == sorted(c["anio"] for c in v)
    assert v[0]["anio"] == life.onboarding.year


def test_look_through_covers_the_whole_portfolio(life):
    w = life.summary["pesos_actuales"]
    lt = look_through_issuers(w, load_dossiers()["fondos"])
    assert sum(r["peso"] for r in lt) == pytest.approx(sum(w.values()), abs=2e-3)
    santander = next(r for r in lt if r["emisor"] == "Banco Santander-Chile")
    assert len(santander["por_fondo"]) >= 2   # aparece en más de un fondo: concentración oculta


def test_exposures_and_diversification_measures(life):
    w, u, d = life.summary["pesos_actuales"], default_universe(), load_dossiers()["fondos"]
    for dim, parts in exposure_breakdown(w, u, d).items():
        assert sum(parts.values()) == pytest.approx(1.0), dim
    f = factor_exposure(w, u, d)
    assert f["Moneda extranjera"] == pytest.approx(w.get("RVG", 0.0))
    cov = life.cases[-1].input_data["cma_estimate"].cov
    rc = risk_contributions(w, cov)
    enb = effective_number_of_bets(rc)
    assert 1 <= enb <= len(w) + 1e-9 and not math.isnan(enb)
    assert diversification_ratio(w, cov) >= 1 - 1e-9
