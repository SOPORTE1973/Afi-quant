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


def run_book(clients: list[BookClient] | None = None) -> BookResult:
    clients = clients or book_clients()
    universe = default_universe()
    params = simulation_registry()
    P = lambda n: get_parameter(n, params).value

    results = {bc.client.client_id: run_lifecycle(client=bc.client, universe=universe, params=params,
                                                  onboarding=bc.onboarding, ips=bc.ips)
               for bc in clients}
    as_of = max(date.fromisoformat(r.summary["fecha"]) for r in results.values())

    # M10 — un due diligence por fondo, compartido por todo el libro
    dossiers = load_dossiers()
    quality = next(iter(results.values())).advisory["calidad_datos"]["series"]
    proxies = policy_benchmark_proxies()
    dd_params = {p: P(p) for p in DD_PARAMS}
    reviews = {
        k: review_fund(k, v, dossiers["fondos"][k], as_of, dd_params,
                       index_series=proxies[PASSIVE_INDEX[k]].series if k in PASSIVE_INDEX else None,
                       rf_series=universe["MM"].series, data_quality=quality.get(k))
        for k, v in universe.items()
    }

    # M09 Monitoring — por cuenta, sin puntaje
    band = float(P("rebalancing_band_pct")) / 100
    max_hhi = P("max_hhi")
    accounts = []
    for bc in clients:
        r = results[bc.client.client_id]
        accounts.append({
            "id": bc.client.client_id, "nombre": bc.client.nombre, "asesor": bc.asesor,
            "perfil": bc.client.perfil_riesgo, "valor": r.summary["valor_final"],
            "dimensiones": monitor_account(r, bc.ips, universe, band, max_hhi, reviews),
            "datos_criticos_faltantes": [c["variable"] for c in r.advisory["catalogo"]
                                         if c["estado"] == "missing_critical"],
        })
    monitoring = prioritize(accounts)

    # Agregados del libro
    by_fund, by_admin, by_advisor = {}, {}, {}
    holders = {k: [] for k in universe}
    for bc in clients:
        r = results[bc.client.client_id]
        vals = r.rows[-1].valor_por_vehiculo
        for k, v in vals.items():
            if v <= 0:
                continue
            by_fund[k] = by_fund.get(k, 0.0) + v
            adm = universe[k].administradora
            by_admin[adm] = by_admin.get(adm, 0.0) + v
            holders[k].append({"cliente": bc.client.client_id, "valor": v})
        by_advisor[bc.asesor] = by_advisor.get(bc.asesor, 0.0) + r.summary["valor_final"]
    aum = sum(by_fund.values())
    aggregates = {
        "aum": aum, "por_fondo": by_fund, "por_administradora": by_admin, "por_asesor": by_advisor,
        "tenedores": holders,
        "aum_en_fondos_sin_dd": sum(v for k, v in by_fund.items() if not reviews[k].elegibilidad["elegible"]),
        "aum_en_fondos_con_senales": sum(v for k, v in by_fund.items() if reviews[k].senales),
        "aportes": sum(r.summary["aportado"] for r in results.values()),
        "retiros": sum(r.summary["retirado"] for r in results.values()),
    }
    return BookResult(as_of, clients, results, reviews, monitoring, aggregates, notes=[
        PRIORITY_RULE,
        "Dimensiones del monitoreo: propuesta mientras ESFS-02 esté abierto (" + ", ".join(DIMENSIONS) + ").",
        "Clientes, IPS y parámetros son de simulación; NAV, fichas y carteras de los fondos son reales.",
    ])
