"""
Cierre del ciclo de vida: el análisis que ve el Wealth Manager.

Todo lo que se calcula aquí sale de los motores (Benchmark, Risk,
Diversification, Liquidity, ClientGoal, Scenario vía Decision Case) o de
las funciones de Performance/Risk relativo (`engines/relative.py`) — este
módulo solo reúne los resultados por tema:

  catalogo              variables de asesoría y su estado (DF 4-5, ESFS 9)
  rentabilidad_activos  cuadro multi-período por vehículo + aporte al cliente
  flujos                libro de flujos clasificados, TWR vs XIRR, calendario
  benchmark             las 8 dimensiones para cada candidato (QM XII)
  relativo              TE, IR, beta, hit ratio, descomposición, atribución
  stress                4 escenarios + episodios históricos (QM XI)
  limites_ips           riesgo vs límites del IPS (D8: alerta, nunca ajuste)
"""

from __future__ import annotations

import math
import statistics
from datetime import date

from afi_quant.clients.ips import evaluate_catalog
from afi_quant.engines.cma import build_cma, monthly_history
from afi_quant.engines.eligibility import ComparableProfile
from afi_quant.engines.performance import twr_with_flows, xirr
from afi_quant.engines.relative import MIN_TE_OBS, chain, relative_metrics, rolling_te, te_decomposition
from afi_quant.engines.risk import historical_var_es, max_drawdown
from afi_quant.engines.series import AdjustedSeries, NavPoint, month_end_points, period_returns
from afi_quant.pipeline import run_case
from afi_quant.portfolio.analytics import (
    aligned_monthly_returns, constant_mix, multi_period_returns, rolling_annualized,
)
from afi_quant.portfolio.universe import policy_benchmark_proxies
from afi_quant.simulation.narrative import clp

CMA_WINDOW_MONTHS = 36
TE_WINDOW_MONTHS = 60        # QM V: 36-60 observaciones mensuales
PORTFOLIO_OBJECTIVE = "multi-meta (goal-based, IPS)"
PORTFOLIO_HORIZON = "multi-horizonte (metas del IPS)"
PORTFOLIO_RESTRICTIONS = "persona natural sin régimen de inversión regulado"


def _by_class(weights: dict[str, float], universe) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, w in weights.items():
        c = universe[k].clase_activo
        out[c] = out.get(c, 0.0) + w
    return out


def _vol(rets: list[float]) -> float:
    return statistics.stdev(rets) * math.sqrt(12)


def closing_advisory(sim) -> dict:
    from afi_quant.data.fixtures import afp_sistema_c, security_ipsa_index

    universe = sim.universe
    ym = sim.calendar[-1]
    as_of = sim.nav["MM"][ym].fecha
    sleeve_vals = sim.sleeve_values(ym)
    sleeve_totals = {g: sum(v.values()) for g, v in sleeve_vals.items()}
    by_vehicle = sim.vehicle_values(ym)
    total = sum(by_vehicle.values())
    weights = {k: v / total for k, v in by_vehicle.items() if v > 0}
    policy_w = sim.policy_weights(ym)
    proxies = policy_benchmark_proxies()
    cma = build_cma(universe, as_of, CMA_WINDOW_MONTHS, sim.params_value)

    # --- Performance absoluta de la cartera --------------------------------
    rets = twr_with_flows(sim.twr_periods)
    twr = chain(rets)
    years = (as_of - sim.onboarding).days / 365.25
    ext_flows = sim.flows + [(as_of, total)]

    # --- Policy benchmark realizado (pesos de la SAA vigente mes a mes) -----
    proxy_rets_month = []
    bench_index = [NavPoint(sim.rows[0].fecha, 1.0)]
    for prev, row in zip(sim.rows, sim.rows[1:]):
        r = 0.0
        for k, w in prev.pesos_politica.items():
            s = proxies[k].series
            r += w * (_price(s, row.fecha) / _price(s, prev.fecha) - 1)
        proxy_rets_month.append(r)
        bench_index.append(NavPoint(row.fecha, bench_index[-1].valor_cuota * (1 + r)))
    bench_series = AdjustedSeries(
        rut="POLICY-SIM-001", serie="SAA", nemotecnico="POLICY-SIM-001", points=bench_index,
        source="Policy benchmark: SAA vigente de cada mes sobre proxies pasivos (precios reales)",
    )
    index_series = AdjustedSeries(
        rut="SIM-001", serie="CARTERA", nemotecnico="CARTERA-SIM-001",
        points=[NavPoint(r.fecha, r.indice_twr) for r in sim.rows],
        source="Índice TWR de la cartera simulada (precios reales, cliente ficticio)",
    )

    # --- Perfiles para el Benchmark Eligibility Framework -------------------
    ipsa = security_ipsa_index()
    afp = afp_sistema_c()
    fund_series = {k: v.series for k, v in universe.items()}
    proxy_series = {k: p.series for k, p in proxies.items()}
    hist = aligned_monthly_returns({**{f"F_{k}": s for k, s in fund_series.items()},
                                    **{f"P_{k}": s for k, s in proxy_series.items()},
                                    "IPSA": ipsa}, as_of)
    last36 = slice(-36, None)
    port_hist = constant_mix({k: hist.returns[f"F_{k}"] for k in weights}, weights)
    policy_hist = constant_mix({k: hist.returns[f"P_{k}"] for k in policy_w}, policy_w)
    afp_hist = aligned_monthly_returns({"AFP": afp, **{f"F_{k}": s for k, s in fund_series.items()}}, as_of)
    peso_ilq = sum(w for k, w in weights.items() if universe[k].dias_liquidez > 90)

    portfolio_profile = ComparableProfile(
        "Cartera SIM-001", "portafolio", objetivo=PORTFOLIO_OBJECTIVE,
        composicion=_by_class(weights, universe), volatilidad=_vol(port_hist[last36]), moneda="CLP",
        peso_fuera_0_3m=peso_ilq, horizonte=PORTFOLIO_HORIZON, costos="neto",
        restricciones=PORTFOLIO_RESTRICTIONS,
    )
    candidates = [
        ComparableProfile(
            "Policy benchmark (SAA vigente)", "policy", objetivo=PORTFOLIO_OBJECTIVE,
            composicion=_by_class(policy_w, universe), volatilidad=_vol(policy_hist[last36]),
            moneda="CLP", peso_fuera_0_3m=0.0, horizonte=PORTFOLIO_HORIZON, costos="neto",
            restricciones=PORTFOLIO_RESTRICTIONS, sustitutos=["Deuda Privada"],
            notas={"asset_allocation": proxies["DP"].nota,
                   "costos": "Proxies pasivos medidos por su valor cuota neto de costos."},
        ),
        ComparableProfile(
            "S&P/CLX IPSA (vía FM Security Index Fund)", "market",
            objetivo="crecimiento (renta variable local)", composicion={"Renta Variable": 1.0},
            volatilidad=_vol(hist.returns["IPSA"][last36]), moneda="CLP", peso_fuera_0_3m=0.0,
            horizonte=None, costos="neto", restricciones="universo acotado a acciones del IPSA",
            notas={"horizonte": "Un índice de mercado no declara horizonte de referencia."},
        ),
        ComparableProfile(
            "Sistema AFP, Fondo C", "peer", objetivo="previsional (acumulación para la pensión)",
            composicion=None, volatilidad=_vol(afp_hist.returns["AFP"][last36]), moneda="CLP",
            peso_fuera_0_3m=1.0, horizonte="previsional (hasta la pensión)", costos=None,
            restricciones="DL 3.500: régimen de inversión de los fondos de pensiones",
            notas={"asset_allocation": "El conector no entrega la composición del Sistema AFP.",
                   "liquidez": "Ahorro previsional obligatorio: no rescatable hasta la pensión.",
                   "costos": ("El valor cuota es neto de costos del fondo, pero la comisión AFP se "
                              "cobra sobre la remuneración: no se puede verificar neto contra neto.")},
        ),
    ]

    # --- Decision Case de cierre ---------------------------------------------
    case = run_case(
        sim.engines, ["benchmark", "risk", "diversification", "liquidity", "clientgoal", "scenario"],
        sim.input_data(
            as_of, nav_series_native_frequency=index_series, cma_estimate=cma,
            current_weights=weights, current_values=by_vehicle,
            target_sleeves=sim.targets, sleeve_values=sleeve_totals, sleeve_holdings=sleeve_vals,
            scenario_history=monthly_history(universe, as_of),
            monthly_contributions=dict(sim.contributions),
            scenario_library=sim.scenario_library,
            benchmark_index_series=bench_series, benchmark_candidates=candidates,
            portfolio_profile=portfolio_profile,
        ),
        trigger="cierre de la simulación — revisión integral de asesoría",
        client_ref=sim.client.client_id,
    )
    results = {n: r.values for n, r in case.engine_results.items()}
    bench = results["benchmark"]
    risk = results["risk"]
    div = results["diversification"]

    # --- Relativo: asignación vigente sobre la historia (36-60 meses) -------
    relativo: dict = {"benchmark": bench["benchmark_del_caso"], "estado": bench["estado_elegibilidad"]}
    if bench["elegibilidad_verificada"]:
        win = slice(-TE_WINDOW_MONTHS, None)
        months = hist.months[win]
        f = {k: hist.returns[f"F_{k}"][win] for k in universe}
        p = {k: hist.returns[f"P_{k}"][win] for k in universe}
        port = constant_mix({k: f[k] for k in weights}, weights)
        benchm = constant_mix({k: p[k] for k in policy_w}, policy_w)
        components = {k: [a - b for a, b in zip(f[k], p[k])] for k in universe}
        components["drift"] = [sum((weights.get(k, 0.0) - policy_w.get(k, 0.0)) * f[k][t] for k in universe)
                               for t in range(len(months))]
        comp_w = {k: policy_w.get(k, 0.0) for k in universe}
        comp_w["drift"] = 1.0
        relativo["asignacion_vigente"] = {
            **relative_metrics(port, benchm, months),
            "descomposicion_te": te_decomposition(components, comp_w),
            "te_rolling_36m": rolling_te(port, benchm, months),
            "retornos_mensuales": [{"mes": m.isoformat(), "cartera": a, "benchmark": b}
                                   for m, a, b in zip(months, port, benchm)],
            "nota": ("Pesos actuales aplicados a los últimos meses de historia real (backtest de la "
                     "asignación vigente, no la trayectoria realizada)."),
        }
        # Realizado en el ciclo de vida (23 meses): TE bloqueado por muestra
        relativo["realizado"] = {
            **relative_metrics(rets, proxy_rets_month, [r.fecha for r in sim.rows[1:]]),
            "atribucion": _brinson(sim, proxies),
        }
        # Por fondo contra su proxy (evaluación de gestores, QM IV/V)
        por_fondo = {}
        long = aligned_monthly_returns({"F": universe["RVL"].series, "P": proxies["RVL"].series}, as_of)
        w60 = slice(-TE_WINDOW_MONTHS, None)
        por_fondo["RVL"] = relative_metrics(long.returns["F"][w60], long.returns["P"][w60], long.months[w60])
        dp = aligned_monthly_returns({"F": universe["DP"].series, "P": proxies["DP"].series}, as_of)
        por_fondo["DP"] = relative_metrics(dp.returns["F"][w60], dp.returns["P"][w60], dp.months[w60])
        for k in ("MM", "RF", "RVG"):
            por_fondo[k] = {"nota": "El vehículo es el mismo índice pasivo del benchmark: tracking error 0 por construcción."}
        relativo["por_fondo"] = por_fondo
    else:
        relativo["bloqueado"] = "Ningún candidato habilita la comparación: no se calcula TE ni exceso."

    # --- Rentabilidad por activo --------------------------------------------
    rent = {}
    first_row, rows = sim.rows[0], sim.rows
    for k, v in universe.items():
        mp = multi_period_returns(v.series, as_of)
        own = period_returns(month_end_points([p for p in v.series.points if p.fecha <= as_of]))
        own_months = [p.fecha for p in month_end_points([p for p in v.series.points if p.fecha <= as_of])][1:]
        contrib = 0.0
        for prev, row in zip(rows, rows[1:]):
            if prev.total and k in prev.valor_por_vehiculo:
                w = prev.valor_por_vehiculo[k] / prev.total
                contrib += w * (_price(v.series, row.fecha) / _price(v.series, prev.fecha) - 1)
        rent[k] = {
            **mp, "nombre": v.nombre, "clase": v.clase_activo, "subclase": v.subclase,
            "ciclo": {
                "retorno_vehiculo": _price(v.series, as_of) / _price(v.series, first_row.fecha) - 1,
                "valor_final": by_vehicle.get(k, 0.0),
                "invertido_neto": sim.invested[k],
                "ganancia_clp": by_vehicle.get(k, 0.0) - sim.invested[k],
                "contribucion_aprox": contrib,
                "peso_actual": weights.get(k, 0.0),
            },
            "rolling_36m": rolling_annualized(own, own_months),
        }
    referencias = {
        "IPSA": {**multi_period_returns(ipsa, as_of), "nombre": "S&P/CLX IPSA (FM Security Index Fund, serie A)"},
        "AFP_C": {**multi_period_returns(afp, as_of), "nombre": "Sistema AFP, Fondo C",
                  "nota": "Último dato publicado: " + afp.points[-1].fecha.isoformat()},
    }

    # --- Flujos ---------------------------------------------------------------
    external_in = sum(e["monto"] for e in sim.ledger if e["externo"] and e["monto"] > 0)
    external_out = -sum(e["monto"] for e in sim.ledger if e["externo"] and e["monto"] < 0)
    internal = sum(e["monto"] for e in sim.ledger if e["tipo"] == "transferencia_interna")
    rotation = sum(e["monto"] for e in sim.ledger if e["tipo"] == "rebalanceo")
    xirr_v = xirr(ext_flows)
    twr_a = (1 + twr) ** (1 / years) - 1
    flujos = {
        "libro": sim.ledger,
        "aportes_externos": external_in,
        "retiros_externos": external_out,
        "transferencias_internas": internal,
        "rotacion_rebalanceo": rotation,
        "ganancia_neta": total - external_in + external_out,
        "twr_anual": twr_a,
        "xirr": xirr_v,
        "lectura": _twr_vs_xirr(twr_a, xirr_v),
        "calendario_esperado": [
            {"fecha": f.fecha.isoformat() if f.fecha else None, "monto": f.monto,
             "clasificacion": f.clasificacion, "recurrencia": f.recurrencia,
             "hasta": f.hasta.isoformat() if f.hasta else None, "meta": f.meta}
            for f in (sim.ips.flujos_esperados if sim.ips else [])
        ],
        "escalera_liquidez": results["liquidity"]["escalera"],
    }

    # --- Límites del IPS (D8) -------------------------------------------------
    port_hist_all = constant_mix({k: hist.returns[f"F_{k}"] for k in weights}, weights)
    var95, es95, tail = historical_var_es(port_hist_all, 0.95)
    lim = sim.ips.limites_riesgo if sim.ips else None
    checks = []
    if lim:
        for name, value, limit in (
            ("Volatilidad ex-ante", div["volatilidad_ex_ante"], lim.volatilidad_max_pct),
            ("VaR 95% 1 mes (histórico)", var95, lim.var95_1m_max_pct),
            ("ES 95% 1 mes (histórico)", es95, lim.es95_1m_max_pct),
            ("Máxima caída realizada", -risk["max_drawdown"], lim.drawdown_tolerado_pct),
        ):
            checks.append({"metrica": name, "valor": value, "limite": limit / 100,
                           "estado": "dentro" if value <= limit / 100 else "excede: alerta sin ajuste automático"})
    limites = {"controles": checks, "muestra_meses": len(port_hist_all), "obs_cola_95": tail,
               "nota": "VaR y ES históricos con los pesos actuales sobre la historia común de los cinco fondos."}

    # --- Catálogo de información ----------------------------------------------
    from afi_quant.simulation.parameters import SCENARIO_LIBRARY
    ctx = {
        "client": sim.client, "ips": sim.ips, "universe": universe, "as_of": as_of,
        "realized_flows": sim.ledger or None, "positions": by_vehicle, "saa": policy_w,
        "band": sim.params_value("rebalancing_band_pct"), "horizons": sim.horizons,
        "cma_institucional": "valores de simulación", "benchmark_check": bench["estado_elegibilidad"],
        "single_currency": True, "scenario_library": SCENARIO_LIBRARY["version"],
        "look_through": "solo BTG Liquidez Alternativa: 99,98% en FIP Facturas (cierre IFRS 2026-06)",
        "transaction_costs": None, "rate_curves": None,
        "synthetic_fields": SYNTHETIC_FIELDS,
    }
    catalogo = evaluate_catalog(ctx)

    # --- Resumen y evento de cierre -------------------------------------------
    summary = {
        "fecha": as_of.isoformat(), "valor_final": total, "valor_por_meta": sleeve_totals,
        "pesos_actuales": weights, "pesos_politica": policy_w,
        "aportado": external_in, "retirado": external_out,
        "twr": twr, "twr_anual": twr_a, "xirr": xirr_v,
        "max_drawdown": risk["max_drawdown"], "volatilidad_ex_ante": div["volatilidad_ex_ante"],
        "riesgo_no_calculado": risk["no_calculado"], "meses": len(rets),
    }
    blocked = risk["no_calculado"].get("volatilidad_anual")
    sim.log(as_of, "cierre", "Cierre: revisión integral de asesoría", {
        "evento": "cierre", "fecha": as_of.isoformat(), "valor": clp(total),
        "twr": twr, "twr_anual": twr_a, "xirr": xirr_v,
        "aportes": clp(external_in), "retiros": clp(external_out),
        "riesgo_bloqueado": blocked.rstrip(".") if blocked else None,
        "vol_ex_ante": div["volatilidad_ex_ante"],
        **sim._projection_ctx(case),
    }, case)

    advisory = {
        "catalogo": catalogo,
        "rentabilidad_activos": rent,
        "referencias": referencias,
        "flujos": flujos,
        "benchmark": bench,
        "relativo": relativo,
        "stress": results["scenario"],
        "limites_ips": limites,
        "look_through": {"DP": {"cierre": "2026-06 (IFRS)", "posiciones": 1,
                                "detalle": "99,98% en cuotas de FIP Facturas (fondo de inversión privado)",
                                "implicancia": ("NAV sin precio de mercado diario: volatilidad y correlación "
                                                "subestimadas (QM X). Concentración en un solo emisor.")}},
    }
    return {"results": results, "summary": summary, "advisory": advisory}


# Regla fija de lectura TWR vs XIRR (QM IV: "así gestionamos tu dinero" vs "así te fue a ti").
TWR_XIRR_MATERIAL_GAP = 0.005


def _twr_vs_xirr(twr_a: float, xirr_v: float) -> str:
    base = (f"TWR {twr_a:.2%} anual: cómo se gestionó el dinero, sin el efecto del momento de los "
            f"aportes. XIRR {xirr_v:.2%} anual: el retorno personal del cliente, con sus aportes y "
            "retiros reales. ")
    gap = xirr_v - twr_a
    if abs(gap) < TWR_XIRR_MATERIAL_GAP:
        return base + ("Son prácticamente iguales (diferencia menor a 0,5 pp): el momento de los "
                       "aportes y retiros casi no cambió el resultado del cliente.")
    if gap < 0:
        return base + ("La XIRR es menor: una parte relevante del dinero entró después de los meses "
                       "de mayor alza, o salió antes de ellos.")
    return base + "La XIRR es mayor: el dinero aportado llegó antes de los meses de mayor alza."


SYNTHETIC_FIELDS = {
    "IPS vigente y firmado", "Perfil y tolerancia al riesgo declarada", "Capacidad de riesgo (objetiva)",
    "Límites de riesgo por perfil (vol / VaR / ES)", "Drawdown tolerado", "Patrimonio total (incluye fuera de AFI)",
    "Life balance sheet (capital humano, activos, pasivos, compromisos)",
    "Restricciones ESG / regulatorias / familiares", "Límites de concentración (emisor / gestor / país)",
    "Monto y fecha de cada meta", "Probabilidad deseada de cada meta", "Prioridad relativa de cada meta",
    "Liquidez requerida en la fecha de cada meta",
    "Calendario de flujos esperados (aportes, retiros, impuestos, gastos)",
    "CMAs institucionales (μ, σ, correlaciones)", "Escenarios de stress del Comité (versionados)",
    "Holdings subyacentes (look-through)", "SAA vigente y bandas",
}


def _price(series, d: date) -> float:
    before = [p for p in series.points if p.fecha <= d]
    return before[-1].valor_cuota


def _brinson(sim, proxies) -> dict:
    """
    Brinson-Fachler (ADVANCED) por vehículo sobre el ciclo realizado, sumando
    los efectos mensuales (aritmético, sin linking — se declara). Asignación:
    (w_p − w_b)(r_b,i − R_b). Selección: w_b (r_p,i − r_b,i). Interacción:
    (w_p − w_b)(r_p,i − r_b,i).
    """
    out = {k: {"asignacion": 0.0, "seleccion": 0.0, "interaccion": 0.0} for k in sim.universe}
    for prev, row in zip(sim.rows, sim.rows[1:]):
        if not prev.total:
            continue
        wp = {k: v / prev.total for k, v in prev.valor_por_vehiculo.items()}
        wb = prev.pesos_politica
        rp = {k: _price(v.series, row.fecha) / _price(v.series, prev.fecha) - 1 for k, v in sim.universe.items()}
        rb = {k: _price(p.series, row.fecha) / _price(p.series, prev.fecha) - 1 for k, p in proxies.items()}
        Rb = sum(wb.get(k, 0.0) * rb[k] for k in sim.universe)
        for k in sim.universe:
            dw = wp.get(k, 0.0) - wb.get(k, 0.0)
            out[k]["asignacion"] += dw * (rb[k] - Rb)
            out[k]["seleccion"] += wb.get(k, 0.0) * (rp[k] - rb[k])
            out[k]["interaccion"] += dw * (rp[k] - rb[k])
    totals = {e: sum(v[e] for v in out.values()) for e in ("asignacion", "seleccion", "interaccion")}
    return {"por_vehiculo": out, "total": totals,
            "nota": "Suma aritmética de efectos mensuales (sin linking geométrico). Modelo ADVANCED."}
