"""Desembolso de la jubilación (engines/decumulation.py)."""

from datetime import date

import pytest

from afi_quant.engines.decumulation import decumulation_plan


def _plan(returns, levels=(0.5, 0.75, 0.9), inflation=3.0):
    return decumulation_plan(capital=1_000_000_000, start=date(2050, 1, 31), birth=date(1985, 1, 15), end_age=90,
                             inflation_pct=inflation, weights={"A": 1.0}, returns={"A": returns},
                             expected_return=0.06, n_sims=2000, block=6, levels=list(levels), as_of=date(2026, 9, 29))


def test_constant_return_matches_growing_annuity():
    r, g = 0.005, (1.03) ** (1 / 12) - 1
    out = _plan([r] * 60)
    n = out["meses"]
    annuity = 1_000_000_000 * (1 + r) ** n / sum((1 + g) ** k * (1 + r) ** (n - 1 - k) for k in range(n))
    for lvl in out["niveles"]:
        assert lvl["retiro_inicial"] == pytest.approx(annuity, rel=1e-9)
        assert lvl["trayectoria"][-1]["p50"] == pytest.approx(0, abs=1)


def test_confidence_is_met_and_monotonic():
    rets = [0.02, -0.03, 0.01, 0.04, -0.05, 0.015, 0.006, -0.01, 0.03, 0.0, 0.012, -0.02] * 5
    out = _plan(rets)
    ws = [lvl["retiro_inicial"] for lvl in out["niveles"]]
    assert ws[0] > ws[1] > ws[2]
    for lvl in out["niveles"]:
        assert lvl["trayectoria"][-1]["vigente"] >= lvl["confianza"] - 1e-9
        assert lvl["retiro_final"] == pytest.approx(lvl["retiro_inicial"] * (1.03 ** (1 / 12)) ** (out["meses"] - 1))


def test_no_period_after_end_age():
    out = decumulation_plan(capital=1.0, start=date(2080, 1, 1), birth=date(1985, 1, 1), end_age=90,
                            inflation_pct=3, weights={"A": 1.0}, returns={"A": [0.0] * 12}, expected_return=0,
                            n_sims=10, block=6, levels=[0.5], as_of=date(2026, 9, 29))
    assert "no_calculado" in out


def test_preserving_capital_constant_return():
    r, g = 0.005, (1.03) ** (1 / 12) - 1
    out = _plan([r] * 60)
    n, c = out["meses"], 1_000_000_000
    b = sum((1 + g) ** k * (1 + r) ** (n - 1 - k) for k in range(n))
    keep = (c * (1 + r) ** n - c * (1 + g) ** n) / b
    for lvl in out["niveles"]:
        assert lvl["preservando"]["retiro_inicial"] == pytest.approx(keep, rel=1e-9)
        assert lvl["preservando"]["capital_final_real_p50"] == pytest.approx(c, rel=1e-9)
        assert lvl["preservando"]["retiro_inicial"] < lvl["retiro_inicial"]


def test_preserving_capital_meets_confidence():
    rets = [0.02, -0.03, 0.01, 0.04, -0.05, 0.015, 0.006, -0.01, 0.03, 0.0, 0.012, -0.02] * 5
    for lvl in _plan(rets)["niveles"]:
        q = lvl["preservando"]
        assert 0 <= q["retiro_inicial"] <= lvl["retiro_inicial"]
        if q["retiro_inicial"] > 0:
            assert q["capital_final_real_p10" if lvl["confianza"] >= 0.9 else "capital_final_real_p50"] >= 1_000_000_000 * (1 - 1e-9)
