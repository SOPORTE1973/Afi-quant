"""
Motor centralizado: corre el libro completo con un solo universo, una sola
CMA por fecha, un solo Parameter Registry y un solo due diligence por fondo.

Lo que se calcula una vez y se comparte (como una plataforma tipo "whole
portfolio"): series de NAV, calidad de datos, due diligence de cada fondo
(M10) y supuestos de mercado. Lo que es de cada cliente: IPS, metas,
construcción, decisiones y su monitoreo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from afi_quant.book.clients import BookClient, book_clients
from afi_quant.due_diligence.review import PARAMS as DD_PARAMS, FundReview, load_dossiers, review_fund
from afi_quant.engines.monitoring import DIMENSIONS, PRIORITY_RULE, monitor_account, prioritize
from afi_quant.portfolio.universe import default_universe, policy_benchmark_proxies
from afi_quant.registries.parameter_registry import get_parameter
from afi_quant.simulation.lifecycle import LifecycleResult, run_lifecycle
from afi_quant.simulation.parameters import simulation_registry

PASSIVE_INDEX = {"RVL": "RVL"}   # vehículo -> proxy pasivo del policy benchmark (QM XII)


@dataclass
class BookResult:
    as_of: date
    clients: list[BookClient]
    results: dict[str, LifecycleResult]
    fund_reviews: dict[str, FundReview]
    monitoring: list[dict]
    aggregates: dict
    notes: list[str] = field(default_factory=list)


def fund_reviews(universe, as_of: date, P, quality: dict) -> dict[str, FundReview]:
    """M10 — un due diligence por fondo, compartido por todo el libro."""
    dossiers = load_dossiers()
    proxies = policy_benchmark_proxies()
    dd_params = {p: P(p) for p in DD_PARAMS}
    return {
        k: review_fund(k, v, dossiers["fondos"][k], as_of, dd_params,
                       index_series=proxies[PASSIVE_INDEX[k]].series if k in PASSIVE_INDEX else None,
                       rf_series=universe["MM"].series, data_quality=quality.get(k))
        for k, v in universe.items()
    }


def account_entry(bc: BookClient, r: LifecycleResult, universe, P, reviews) -> dict:
    """M09 Monitoring de una cuenta, sin puntaje."""
    return {
        "id": bc.client.client_id, "nombre": bc.client.nombre, "asesor": bc.asesor,
        "perfil": bc.client.perfil_riesgo, "valor": r.summary["valor_final"],
        "dimensiones": monitor_account(r, bc.ips, universe, float(P("rebalancing_band_pct")) / 100,
                                       P("max_hhi"), reviews),
        "datos_criticos_faltantes": [c["variable"] for c in r.advisory["catalogo"]
                                     if c["estado"] == "missing_critical"],
    }


def holdings_entry(bc: BookClient, r: LifecycleResult) -> dict:
    """Lo que cada cuenta aporta a los agregados del libro."""
    return {"id": bc.client.client_id, "asesor": bc.asesor,
            "por_fondo": {k: v for k, v in r.rows[-1].valor_por_vehiculo.items() if v > 0},
            "valor": r.summary["valor_final"], "aportado": r.summary["aportado"],
            "retirado": r.summary["retirado"]}


def book_aggregates(holdings: list[dict], universe, eligible: dict[str, bool], signals: dict[str, bool]) -> dict:
    by_fund, by_admin, by_advisor = {}, {}, {}
    holders = {k: [] for k in universe}
    for h in holdings:
        for k, v in h["por_fondo"].items():
            by_fund[k] = by_fund.get(k, 0.0) + v
            adm = universe[k].administradora
            by_admin[adm] = by_admin.get(adm, 0.0) + v
            holders[k].append({"cliente": h["id"], "valor": v})
        by_advisor[h["asesor"]] = by_advisor.get(h["asesor"], 0.0) + h["valor"]
    return {
        "aum": sum(by_fund.values()), "por_fondo": by_fund, "por_administradora": by_admin,
        "por_asesor": by_advisor, "tenedores": holders,
        "aum_en_fondos_sin_dd": sum(v for k, v in by_fund.items() if not eligible[k]),
        "aum_en_fondos_con_senales": sum(v for k, v in by_fund.items() if signals[k]),
        "aportes": sum(h["aportado"] for h in holdings),
        "retiros": sum(h["retirado"] for h in holdings),
    }


BOOK_NOTES = [
    PRIORITY_RULE,
    "Dimensiones del monitoreo: propuesta mientras ESFS-02 esté abierto (" + ", ".join(DIMENSIONS) + ").",
    "Clientes, IPS y parámetros son de simulación; NAV, fichas y carteras de los fondos son reales.",
]


def run_client(bc: BookClient, universe, params) -> LifecycleResult:
    return run_lifecycle(client=bc.client, universe=universe, params=params, onboarding=bc.onboarding,
                         ips=bc.ips, extra_flows=bc.eventos)


def run_book(clients: list[BookClient] | None = None) -> BookResult:
    clients = clients or book_clients()
    universe = default_universe()
    params = simulation_registry()
    P = lambda n: get_parameter(n, params).value

    results = {bc.client.client_id: run_client(bc, universe, params) for bc in clients}
    as_of = max(date.fromisoformat(r.summary["fecha"]) for r in results.values())
    quality = next(iter(results.values())).advisory["calidad_datos"]["series"]
    reviews = fund_reviews(universe, as_of, P, quality)
    monitoring = prioritize([account_entry(bc, results[bc.client.client_id], universe, P, reviews)
                             for bc in clients])
    aggregates = book_aggregates([holdings_entry(bc, results[bc.client.client_id]) for bc in clients], universe,
                                 {k: rv.elegibilidad["elegible"] for k, rv in reviews.items()},
                                 {k: bool(rv.senales) for k, rv in reviews.items()})
    return BookResult(as_of, clients, results, reviews, monitoring, aggregates, notes=list(BOOK_NOTES))
