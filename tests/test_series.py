"""
Tests de la capa de series de NAV (`engines/series.py`) sobre datos
reales del conector MCP_Afitrading — no sintéticos.

Ver `data/benchmark_fixtures/etf_singular_ipsa.py` para la procedencia
exacta del fixture.
"""

from __future__ import annotations

from datetime import date

from afi_quant.data.benchmark_fixtures.etf_singular_ipsa import (
    ETF_SINGULAR_IPSA_SERIES,
)
from afi_quant.engines.series import (
    AdjustedSeries,
    NavPoint,
    dedupe_snapshots,
    geometric_chain_return,
    total_return,
)


def test_fixture_has_no_gaps_beyond_calendar_and_is_ascending():
    dates = [p.fecha for p in ETF_SINGULAR_IPSA_SERIES.points]
    assert dates == sorted(dates)
    assert len(dates) == 12
    assert dates[0] == date(2026, 9, 15)
    assert dates[-1] == date(2026, 9, 29)


def test_geometric_chain_return_matches_total_return_on_real_data():
    # Sobre una serie de precio sin flujos externos, encadenar retornos
    # diarios (TWR) debe coincidir con el retorno directo punta a punta.
    chained = geometric_chain_return(ETF_SINGULAR_IPSA_SERIES.points)
    direct = total_return(ETF_SINGULAR_IPSA_SERIES)
    # Coinciden salvo error de punto flotante del encadenado (12 multiplicaciones).
    assert abs(chained - direct) < 1e-9
    assert round(chained * 100, 4) == round(direct * 100, 4)


def test_total_return_sign_matches_known_direction():
    # Dato real: el fondo cerró el período más abajo de donde partió
    # (1369.4591 -> 1337.1848), así que el retorno del período es negativo.
    assert total_return(ETF_SINGULAR_IPSA_SERIES) < 0


def test_dedupe_snapshots_keeps_latest_snapshot_per_market_date():
    raw = [
        {"hasta": "2026-09-16", "fecha_snapshot": "2026-09-16 09:05:00", "valor_cuota": "1358.0000"},
        {"hasta": "2026-09-16", "fecha_snapshot": "2026-09-16 16:40:00", "valor_cuota": "1358.9392"},
        {"hasta": "2026-09-15", "fecha_snapshot": "2026-09-15 16:40:00", "valor_cuota": "1369.4591"},
    ]
    points = dedupe_snapshots(raw)
    assert points == [
        NavPoint(fecha=date(2026, 9, 15), valor_cuota=1369.4591),
        NavPoint(fecha=date(2026, 9, 16), valor_cuota=1358.9392),
    ]


def test_adjusted_series_rejects_unordered_points():
    import pytest

    with pytest.raises(ValueError):
        AdjustedSeries(
            rut="x",
            serie="x",
            nemotecnico="x",
            source="test",
            points=[
                NavPoint(fecha=date(2026, 9, 16), valor_cuota=1.0),
                NavPoint(fecha=date(2026, 9, 15), valor_cuota=1.0),
            ],
        )
