"""La serie diaria reconstruida debe cuadrar con los cierres mensuales de la simulación."""

from __future__ import annotations

import pytest

from afi_quant.portfolio.timeseries import daily_portfolio
from afi_quant.portfolio.universe import default_universe, policy_benchmark_proxies
from afi_quant.simulation.lifecycle import run_lifecycle


@pytest.fixture(scope="module")
def data():
    r = run_lifecycle()
    return r, daily_portfolio(r.rows, default_universe(), policy_benchmark_proxies())


def test_daily_series_matches_month_end_rows(data):
    r, daily = data
    closes = [p for p in daily if p["cierre"]]
    assert len(closes) == len(r.rows)
    for p, row in zip(closes, r.rows):
        assert p["indice_twr"] == pytest.approx(row.indice_twr, abs=1e-12)
        assert p["valor"] == pytest.approx(row.total, rel=1e-12)


def test_daily_parts_add_up_and_net_contributions(data):
    r, daily = data
    for p in daily[::37]:
        assert sum(p["por_vehiculo"].values()) == pytest.approx(p["valor"])
        assert sum(p["por_meta"].values()) == pytest.approx(p["valor"])
    assert daily[-1]["aportes_netos"] == pytest.approx(r.summary["aportado"] - r.summary["retirado"])


def test_daily_drawdown_is_at_least_the_monthly_one(data):
    r, daily = data
    assert min(p["drawdown"] for p in daily) <= r.summary["max_drawdown"] + 1e-12


def test_goal_fan_path_ends_at_final_percentiles(data):
    r, _ = data
    jub = r.closing_results["clientgoal"]["metas"]["jubilacion"]
    last = jub["trayectoria"][-1]
    assert last["mes"] == jub["meses"]
    assert last["p50"] == pytest.approx(jub["p50"])
    assert all(a["p10"] <= a["p50"] <= a["p90"] for a in jub["trayectoria"])
