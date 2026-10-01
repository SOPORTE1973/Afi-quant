"""
Motor centralizado: libro de clientes, due diligence compartido (M10) y
monitoreo sin puntaje (DF 2.1).
"""

from __future__ import annotations

from datetime import date

import pytest

from afi_quant.book.run import run_book
from afi_quant.due_diligence.review import ApprovedListEntry, load_dossiers, review_fund
from afi_quant.engines.monitoring import ALERT, ATTN, DIMENSIONS, OK, prioritize
from afi_quant.portfolio.universe import default_universe
from afi_quant.simulation.parameters import SIMULATION_VALUES

DD = {k: SIMULATION_VALUES[k] for k in ("dd_min_track_record_years", "dd_underperformance_months",
                                        "dd_te_increase_ratio", "dd_top5_max_pct", "dd_single_position_max_pct")}


@pytest.fixture(scope="module")
def book():
    return run_book()


def test_fund_without_odd_is_never_eligible():
    u, d = default_universe(), load_dossiers()["fondos"]
    r = review_fund("RF", u["RF"], d["RF"], date(2026, 9, 29), DD,
                    entry=ApprovedListEntry(estado="Approved-Active"))
    assert r.odd["estado"] == "pendiente"
    assert not r.elegibilidad["elegible"] and r.elegibilidad["nivel_maximo_decisiones_de_fondo"] == 2


def test_smoothed_nav_does_not_report_sharpe():
    u, d = default_universe(), load_dossiers()["fondos"]
    r = review_fund("DP", u["DP"], d["DP"], date(2026, 9, 29), DD, rf_series=u["MM"].series)
    assert "sharpe_3a" not in r.idd and "advertencia" in r.idd
    assert {s["tipo"] for s in r.senales} >= {"Concentración en una posición", "Liquidez"}


def test_signals_need_parameters():
    u, d = default_universe(), load_dossiers()["fondos"]
    r = review_fund("DP", u["DP"], d["DP"], date(2026, 9, 29), {})
    assert not [s for s in r.senales if s["tipo"].startswith("Concentración")]
    assert set(r.no_evaluado) == set(DD)


def test_prioritize_is_lexicographic_without_score():
    dims = lambda *st: {d: {"estado": s} for d, s in zip(DIMENSIONS, st)}
    accts = [{"id": "a", "valor": 9e9, "dimensiones": dims(ATTN, ATTN, OK, OK, OK, OK)},
             {"id": "b", "valor": 1e6, "dimensiones": dims(ALERT, OK, OK, OK, OK, OK)},
             {"id": "c", "valor": 5e6, "dimensiones": dims(ALERT, OK, OK, OK, OK, OK)}]
    assert [a["id"] for a in prioritize(accts)] == ["c", "b", "a"]
    assert all("score" not in a and "puntaje" not in a for a in accts)


def test_book_monitors_every_dimension_of_every_client(book):
    assert len(book.monitoring) == len(book.clients) == 5
    for a in book.monitoring:
        assert set(a["dimensiones"]) == set(DIMENSIONS)
        assert all(d["estado"] in ("ok", "atencion", "alerta", "sin_datos") for d in a["dimensiones"].values())


def test_incomplete_ips_is_declared_not_invented(book):
    sim5 = next(a for a in book.monitoring if a["id"] == "SIM-005")
    assert sim5["dimensiones"]["riesgo_ips"]["estado"] == "sin_datos"
    assert "Límites de riesgo por perfil (vol / VaR / ES)" in sim5["datos_criticos_faltantes"]


def test_book_aggregates_add_up(book):
    agg = book.aggregates
    assert sum(agg["por_fondo"].values()) == pytest.approx(agg["aum"])
    assert sum(agg["por_administradora"].values()) == pytest.approx(agg["aum"])
    assert agg["aum"] == pytest.approx(sum(r.summary["valor_final"] for r in book.results.values()), rel=1e-9)


def test_construction_respects_ips_volatility_limit(book):
    for bc in book.clients:
        lim = bc.ips.limites_riesgo.volatilidad_max_pct
        sleeves = book.results[bc.client.client_id].onboarding_results["construction"]["sleeves"]
        for s in sleeves.values():
            assert s["volatilidad_ex_ante"] <= lim / 100 + 1e-9
