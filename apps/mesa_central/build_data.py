"""
Datos de la Mesa Central: un archivo compartido (libro, fondos, referencias) y
uno por cliente con todo lo que muestra su espacio de trabajo.

    python apps/mesa_central/build_data.py <dir_salida>
"""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from pathlib import Path

from afi_quant.book.run import run_book
from afi_quant.data.fixtures import afp_sistema_c
from afi_quant.due_diligence.review import load_dossiers
from afi_quant.engines.cma import LEDOIT_WOLF, apply_registry_assumptions, estimate_cma, monthly_history
from afi_quant.engines.construction import grid_portfolios, optimize_grid
from afi_quant.engines.monitoring import DIMENSION_NAMES, DIMENSIONS
from afi_quant.portfolio.timeseries import daily_portfolio, normalized
from afi_quant.portfolio.universe import default_universe, policy_benchmark_proxies
from afi_quant.registries.parameter_registry import get_parameter
from afi_quant.simulation.lifecycle import CMA_WINDOW_MONTHS
from afi_quant.simulation.parameters import SCENARIO_LIBRARY, SIMULATION_VALUES, simulation_registry

CAT = {"onboarding": "Onboarding", "revision": "Rebalanceo", "cambio_horizonte": "Glide path",
       "revision_anual": "Revisión anual", "meta_cumplida": "Meta cumplida", "meta_deficit": "Meta con déficit",
       "alerta_caida": "Alerta", "cierre": "Cierre"}


def js(x):
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): js(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [js(v) for v in x]
    if isinstance(x, float):
        return None if math.isnan(x) or math.isinf(x) else round(x, 6)
    return x


def construction_moments(r, u, P):
    VEH = list(u)
    max_w = float(P("max_weight_per_vehicle_pct")) / 100
    delta = float(P("risk_aversion_delta"))

    def keys_caps(h):
        if h == "corto":
            ks = [k for k, v in u.items() if v.subclase == P("short_horizon_eligible_subclass")]
            return ks, {k: 1.0 for k in ks}
        return VEH, {k: max_w for k in VEH}

    out = []
    cases = [c for c in r.cases if "construction" in c.engine_results
             and not c.engine_results["construction"].insufficient_data]
    for n, case in enumerate(cases):
        cma, as_of = case.input_data["cma_estimate"], case.input_data["as_of_date"]
        sleeves = case.engine_results["construction"].values["sleeves"]
        frontera = {}
        for g, s in sleeves.items():
            ks, caps = keys_caps(s["horizonte"])
            if len(ks) < 2:
                continue
            pts = sorted({(round(math.sqrt(cma.portfolio_variance(w)), 4), round(cma.portfolio_return(w), 4))
                          for w in grid_portfolios(ks, caps)})
            env, best = [], -1
            for v, ret in sorted(pts, key=lambda p: (p[0], -p[1])):
                if ret > best + 1e-9:
                    env.append([v, ret])
                    best = ret
            frontera[g] = {"nube": [list(p) for p in pts[::max(1, len(pts) // 700)]], "envolvente": env,
                           "tope": s["tope_volatilidad"], "elegida": [s["volatilidad_ex_ante"], s["retorno_esperado"]]}
        sens = {}
        if n == 0:
            for tag, inten in (("sin shrinkage", 0.0), ("fija 0,30", 0.3), ("Ledoit-Wolf", LEDOIT_WOLF)):
                c2 = apply_registry_assumptions(
                    estimate_cma(monthly_history(u, as_of, CMA_WINDOW_MONTHS), float(P("cma_return_shrinkage")), inten),
                    u, P("cma_expected_return"), P("cma_expected_volatility"))
                sens[tag] = {"intensidad": c2.shrinkage_intensidad, "sleeves": {}}
                for g, s in sleeves.items():
                    ks, caps = keys_caps(s["horizonte"])
                    w = optimize_grid(c2, ks, delta, s["tope_volatilidad"], caps)
                    if w:
                        sens[tag]["sleeves"][g] = {"pesos": w, "ret": c2.portfolio_return(w),
                                                   "vol": math.sqrt(c2.portfolio_variance(w))}
        alts = {}
        for g, a in (case.alternatives or {}).items():
            alts[g] = {"nivel": a.get("nivel"), "recomendada": a.get("recomendada"),
                       "motivo_nivel": a.get("motivo_nivel"), "recomendacion": a.get("recomendacion"),
                       "alternativas": {k: {x: v.get(x) for x in ("nombre", "pesos", "retorno_esperado",
                                                                  "volatilidad_ex_ante", "retorno_escenario_adverso",
                                                                  "prob_exito", "hhi", "max_contribucion_riesgo",
                                                                  "admisible", "motivo_inadmisible")}
                                        for k, v in a.get("alternativas", {}).items()},
                       "tradeoffs": [{x: t[x] for x in ("alternativa", "conflicto", "mejora", "empeora")}
                                     for t in a.get("tradeoffs", {}).get("tradeoffs", [])]}
        out.append({
            "fecha": as_of, "trigger": case.trigger, "n_obs": cma.n_obs, "desde": cma.desde, "hasta": cma.hasta,
            "intensidad": cma.shrinkage_intensidad, "metodo": cma.shrinkage_metodo, "rbar": cma.correlacion_promedio,
            "mu": cma.mu, "mu_historico": cma.mu_historico, "vol": {k: cma.vol(k) for k in VEH},
            "corr_muestral": [[cma.corr[(i, j)] for j in VEH] for i in VEH],
            "corr_usada": [[cma.corr_post(i, j) for j in VEH] for i in VEH],
            "frontera": frontera, "sensibilidad": sens, "alternativas": alts,
            "sleeves": {g: {"horizonte": s["horizonte"], "tope": s["tope_volatilidad"], "fuente": s.get("tope_fuente"),
                            "pesos": s["pesos"], "ret": s["retorno_esperado"], "vol": s["volatilidad_ex_ante"]}
                        for g, s in sleeves.items()},
            "total": case.engine_results["construction"].values["asignacion_total"],
        })
    return out


def compact_stress(stress: dict, VEH) -> dict:
    """La trayectoria diaria de cada episodio va en columnas para no inflar el archivo."""
    out = dict(stress)
    out["historicos"] = {}
    for k, ep in stress["historicos"].items():
        ep = dict(ep)
        tr = ep.pop("trayectoria", None)
        if tr:
            pts = tr.pop("puntos")
            held = [v for v in VEH if pts and v in pts[0]["por_vehiculo"]]
            ep["trayectoria"] = {**tr, "fechas": [p["fecha"] for p in pts], "total": [round(p["total"]) for p in pts],
                                 "veh": {v: [round(p["por_vehiculo"][v]) for p in pts] for v in held}}
        out["historicos"][k] = ep
    return out


def client_payload(bc, r, u, prox, P, account):
    c, ips = bc.client, bc.ips
    a, close, s = r.advisory, r.closing_results, r.summary
    VEH = list(u)
    daily = daily_portfolio(r.rows, u, prox)
    start, end = r.rows[0].fecha, r.rows[-1].fecha
    norm = {k: normalized(v.series, start, end) for k, v in u.items()}
    norm["IPSA"] = normalized(prox["RVL"].series, start, end)
    if len([p for p in afp_sistema_c().points if start <= p.fecha <= end]) > 2:
        norm["AFP"] = normalized(afp_sistema_c(), start, end)

    news = []
    for i, e in enumerate(r.events, 1):
        quiet = e.tipo == "revision" and "cardinalidad cero" in e.explicacion
        news.append({"id": f"ev{i}", "n": i, "fecha": e.fecha, "tipo": e.tipo,
                     "categoria": "Sin operar" if quiet else CAT.get(e.tipo, e.tipo), "titulo": e.titulo,
                     "resumen": re.split(r"(?<=[.])\s", e.explicacion, maxsplit=1)[0], "texto": e.explicacion,
                     "quiet": quiet})
    rebal = []
    for e in r.events:
        if e.tipo == "revision" and e.detalle.get("flujos"):
            for g, f in e.detalle["flujos"].items():
                rebal.append({
                    "fecha": e.fecha, "meta": g, "desvio": f["mayor_desvio"], "vehiculo": f["mayor_desvio_vehiculo"],
                    "recomendada": f.get("recomendada"), "criterio": f.get("criterio"), "nivel": f["nivel"],
                    "motivo_nivel": f.get("motivo_nivel"), "recomendacion": f.get("recomendacion"),
                    "descartadas": f.get("descartadas", {}),
                    "tradeoffs": [{x: t[x] for x in ("alternativa", "conflicto", "mejora", "empeora")}
                                  for t in f["tradeoffs"]["tradeoffs"]],
                    "alternativas": {k: {x: v.get(x) for x in ("nombre", "rotacion_clp", "volatilidad_ex_ante",
                                                              "retorno_escenario_adverso", "admisible",
                                                              "motivo_inadmisible", "mayor_desvio_restante", "prob_exito")}
                                     for k, v in f["alternativas"].items()}})
    rows = r.rows
    settled = {e.detalle.get("meta") for e in r.events if e.tipo in ("meta_cumplida", "meta_deficit")}
    rent = {k: {kk: vv for kk, vv in v.items() if kk != "rolling_36m"} for k, v in a["rentabilidad_activos"].items()}
    rel = a["relativo"]
    goal_meta = close["clientgoal"]["metas"]
    lim = ips.limites_riesgo
    return {
        "id": c.client_id, "asesor": bc.asesor, "monitoreo": account,
        "cliente": {"id": c.client_id, "nombre": c.nombre, "edad": c.age(r.onboarding), "perfil": c.perfil_riesgo,
                    "puntaje": c.puntaje_cuestionario, "gasto": c.gasto_mensual,
                    "metas": [{"key": g.key, "nombre": g.nombre, "prioridad": g.prioridad, "objetivo": g.monto_objetivo,
                               "fecha": g.fecha, "capital": g.capital_inicial, "aporte": g.aporte_mensual,
                               "prob_deseada": g.probabilidad_deseada, "liquidez": g.liquidez_requerida,
                               "cerrada": g.key not in goal_meta}
                              for g in c.goals]},
        "ips": {"id": ips.ips_id, "vigente_desde": ips.vigente_desde, "revisar_antes_de": ips.revisar_antes_de,
                "moneda": ips.moneda_base, "tolerancia": ips.tolerancia_riesgo, "capacidad": ips.capacidad_riesgo,
                "limites": {"vol": lim.volatilidad_max_pct, "var": lim.var95_1m_max_pct, "es": lim.es95_1m_max_pct,
                            "dd": lim.drawdown_tolerado_pct},
                "patrimonio": ips.patrimonio_total, "fuera_afi": ips.inversiones_fuera_afi,
                "admin_max": (ips.limites_concentracion or {}).get("administradora"),
                "lbs": vars(ips.life_balance_sheet) if ips.life_balance_sheet else None},
        "onboarding": r.onboarding, "n_casos": len(r.cases),
        "resumen": s, "metas_cierre": goal_meta,
        "noticias": news, "rebalanceos": rebal,
        "ts": {"fechas": [p["fecha"] for p in daily], "valor": [round(p["valor"]) for p in daily],
               "twr": [round(p["indice_twr"], 6) for p in daily], "bench": [round(p["benchmark"], 6) for p in daily],
               "neto": [round(p["aportes_netos"]) for p in daily], "dd": [round(p["drawdown"], 6) for p in daily],
               "flujo": [round(p["flujo_externo"]) for p in daily],
               "veh": {k: [round(p["por_vehiculo"].get(k, 0.0)) for p in daily] for k in VEH},
               "meta": {g.key: [round(p["por_meta"][g.key]) if g.key in p["por_meta"] else None for p in daily]
                        for g in c.goals},
               "norm": {k: {"fechas": [p["fecha"] for p in v], "valores": [round(p["valor"], 4) for p in v]}
                        for k, v in norm.items()}},
        "retornos_mensuales": [{"mes": b.fecha.isoformat()[:7], "r": b.indice_twr / a_.indice_twr - 1}
                               for a_, b in zip(rows, rows[1:])],
        "abanico": {g: m.get("trayectoria") for g, m in goal_meta.items() if m.get("trayectoria")},
        "drift": {"actual": s["pesos_actuales"], "objetivo": s["pesos_politica"],
                  "banda": float(P("rebalancing_band_pct")) / 100},
        "max_dd_diario": min(p["drawdown"] for p in daily),
        "div_cierre": close["diversification"],
        "construccion": {"momentos": construction_moments(r, u, P),
                         "pesos_t": [{"fecha": row.fecha,
                                      "actual": {k: row.valor_por_vehiculo.get(k, 0) / max(1e-9, sum(row.valor_por_vehiculo.values()))
                                                 for k in VEH},
                                      "politica": {k: row.pesos_politica.get(k, 0) for k in VEH}} for row in rows],
                         "delta": float(P("risk_aversion_delta")), "tope_peso": float(P("max_weight_per_vehicle_pct")) / 100,
                         "paso": 0.05, "ventana": CMA_WINDOW_MONTHS},
        "catalogo": a["catalogo"], "rentabilidad": rent, "flujos": a["flujos"],
        "benchmark": a["benchmark"]["candidatos"],
        "relativo": {"asignacion": {k: v for k, v in rel.get("asignacion_vigente", {}).items() if k != "retornos_mensuales"},
                     "realizado": rel.get("realizado")},
        "stress": compact_stress(a["stress"], VEH), "limites": a["limites_ips"], "liquidez": close["liquidity"],
        "metas_cerradas": sorted(x for x in settled if x),
    }


def main(out_dir: str):
    out = Path(out_dir)
    (out / "clientes").mkdir(parents=True, exist_ok=True)
    b = run_book()
    u = default_universe()
    prox = policy_benchmark_proxies()
    reg = simulation_registry()
    P = lambda n: get_parameter(n, reg).value
    VEH = list(u)
    adv0 = next(iter(b.results.values())).advisory

    funds = {}
    for k, rv in b.fund_reviews.items():
        i = rv.idd
        funds[k] = {
            "key": k, "nombre": u[k].nombre, "administradora": u[k].administradora, "clase": u[k].clase_activo,
            "subclase": u[k].subclase, "liquidez": u[k].liquidez, "precio_de_mercado": u[k].precio_de_mercado,
            "ficha": rv.ficha,
            "idd": {x: i.get(x) for x in ("desde_datos", "hasta", "meses", "anios_datos", "retorno_1a", "retorno_3a",
                                           "retorno_5a", "volatilidad_3a", "max_drawdown_3a", "sharpe_3a", "calmar_3a",
                                           "advertencia")},
            "relativo": {x: i["relativo"].get(x) for x in ("n_obs", "exceso_anual", "tracking_error",
                                                           "information_ratio", "beta", "hit_ratio")}
            if i.get("relativo") else None,
            "exceso_12m": i.get("exceso_12m_rolling"),
            "senales": rv.senales, "pilares": rv.pilares, "odd": rv.odd, "etapas": rv.etapas,
            "estado": rv.approved_list.estado, "elegibilidad": rv.elegibilidad, "no_evaluado": rv.no_evaluado,
            "tenedores": b.aggregates["tenedores"][k],
            "rentabilidad": {kk: vv for kk, vv in adv0["rentabilidad_activos"][k].items() if kk != "rolling_36m"},
            "nav": [{"f": p.fecha, "v": round(p.valor_cuota, 4)} for p in u[k].series.points
                    if p.fecha >= date(2021, 10, 1) and p.fecha.weekday() == 4],
        }
    shared = {
        "as_of": b.as_of, "notas": b.notes, "dimensiones": {d: DIMENSION_NAMES[d] for d in DIMENSIONS},
        "agregados": b.aggregates, "monitoreo": b.monitoring, "fondos": funds, "vehiculos": VEH,
        "clientes": {bc.client.client_id: {"nombre": bc.client.nombre, "perfil": bc.client.perfil_riesgo,
                                           "asesor": bc.asesor,
                                           "valor": b.results[bc.client.client_id].summary["valor_final"]}
                     for bc in b.clients},
        "universo": {k: {"nombre": v.nombre, "adm": v.administradora, "clase": v.clase_activo, "subclase": v.subclase,
                         "liquidez": v.liquidez, "rut": v.series.rut, "precio_mercado": v.precio_de_mercado}
                     for k, v in u.items()},
        "referencias": adv0["referencias"], "relativo_por_fondo": adv0["relativo"].get("por_fondo"),
        "calidad_datos": adv0["calidad_datos"], "parametros": SIMULATION_VALUES, "biblioteca": SCENARIO_LIBRARY,
        "fuente_fondos": load_dossiers()["fuente"],
    }
    (out / "libro.json").write_text(json.dumps(js(shared), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sizes = {}
    for bc in b.clients:
        cid = bc.client.client_id
        account = next(x for x in b.monitoring if x["id"] == cid)
        txt = json.dumps(js(client_payload(bc, b.results[cid], u, prox, P, account)), ensure_ascii=False,
                         separators=(",", ":"))
        (out / "clientes" / f"{cid}.json").write_text(txt, encoding="utf-8")
        sizes[cid] = len(txt)
    print("libro", (out / "libro.json").stat().st_size, sizes)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent / "dist" / "data"))
