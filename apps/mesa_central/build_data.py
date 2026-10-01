"""Datos de la plataforma central: libro, clientes, due diligence, monitoreo."""
import json
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
from afi_quant.book.run import run_book
from afi_quant.engines.monitoring import DIMENSION_NAMES, DIMENSIONS
from afi_quant.portfolio.timeseries import daily_portfolio
from afi_quant.portfolio.universe import default_universe, policy_benchmark_proxies
from afi_quant.simulation.parameters import SCENARIO_LIBRARY

OUT = sys.argv[1]
b = run_book()
u = default_universe()
prox = policy_benchmark_proxies()
VEH = list(u)


def js(x):
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): js(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [js(v) for v in x]
    if isinstance(x, float):
        return round(x, 6)
    return x


CAT = {"onboarding": "Onboarding", "revision": "Rebalanceo", "cambio_horizonte": "Glide path",
       "revision_anual": "Revisión anual", "meta_cumplida": "Meta cumplida", "meta_deficit": "Meta con déficit",
       "alerta_caida": "Alerta", "cierre": "Cierre"}

clients = {}
for bc in b.clients:
    cid = bc.client.client_id
    r = b.results[cid]
    daily = daily_portfolio(r.rows, u, prox)
    s, adv, close = r.summary, r.advisory, r.closing_results
    goals = []
    for g in bc.client.goals:
        m = close["clientgoal"]["metas"].get(g.key)
        settled = next((e for e in r.events if e.tipo in ("meta_cumplida", "meta_deficit") and e.detalle.get("meta") == g.key), None)
        goals.append({
            "key": g.key, "nombre": g.nombre, "prioridad": g.prioridad, "objetivo": g.monto_objetivo,
            "fecha": g.fecha, "deseada": g.probabilidad_deseada, "aporte": g.aporte_mensual,
            "valor": s["valor_por_meta"].get(g.key),
            "prob": (m or {}).get("prob_exito"), "cobertura": (m or {}).get("cobertura"),
            "p10": (m or {}).get("p10"), "p50": (m or {}).get("p50"), "p90": (m or {}).get("p90"),
            "trayectoria": (m or {}).get("trayectoria"),
            "estado": "cumplida" if any(e.tipo == "meta_cumplida" and g.nombre in e.titulo for e in r.events)
            else ("activa" if m else "cerrada"),
        })
    news = []
    for i, e in enumerate(r.events, 1):
        quiet = e.tipo == "revision" and "cardinalidad cero" in e.explicacion
        news.append({"n": i, "fecha": e.fecha, "categoria": "Sin operar" if quiet else CAT.get(e.tipo, e.tipo),
                     "titulo": e.titulo, "texto": e.explicacion, "quiet": quiet})
    last_alloc = next(c for c in reversed(r.cases) if "construction" in c.engine_results
                      and not c.engine_results["construction"].insufficient_data)
    con = last_alloc.engine_results["construction"].values
    st = close["scenario"]
    clients[cid] = {
        "id": cid, "nombre": bc.client.nombre, "asesor": bc.asesor, "perfil": bc.client.perfil_riesgo,
        "edad": bc.client.age(b.as_of), "onboarding": bc.onboarding, "gasto": bc.client.gasto_mensual,
        "ips": {"id": bc.ips.ips_id, "limites": vars(bc.ips.limites_riesgo), "patrimonio": bc.ips.patrimonio_total,
                "fuera_afi": bc.ips.inversiones_fuera_afi, "tolerancia": bc.ips.tolerancia_riesgo,
                "capacidad": bc.ips.capacidad_riesgo, "admin_max": (bc.ips.limites_concentracion or {}).get("administradora")},
        "resumen": {"valor": s["valor_final"], "aportado": s["aportado"], "retirado": s["retirado"],
                    "twr": s["twr"], "twr_anual": s["twr_anual"], "xirr": s["xirr"], "meses": s["meses"],
                    "max_dd": s["max_drawdown"], "vol_ex_ante": s["volatilidad_ex_ante"],
                    "pesos": s["pesos_actuales"], "politica": s["pesos_politica"]},
        "ts": {"fechas": [p["fecha"] for p in daily], "valor": [round(p["valor"]) for p in daily],
               "neto": [round(p["aportes_netos"]) for p in daily],
               "twr": [round(p["indice_twr"], 6) for p in daily], "bench": [round(p["benchmark"], 6) for p in daily],
               "dd": [round(p["drawdown"], 5) for p in daily],
               "veh": {k: [round(p["por_vehiculo"].get(k, 0.0)) for p in daily] for k in VEH}},
        "metas": goals,
        "noticias": news,
        "asignacion": {"fecha": last_alloc.input_data["as_of_date"], "total": con["asignacion_total"],
                       "sleeves": {g: {"pesos": x["pesos"], "ret": x["retorno_esperado"], "vol": x["volatilidad_ex_ante"],
                                       "tope": x["tope_volatilidad"], "fuente": x.get("tope_fuente"), "horizonte": x["horizonte"]}
                                   for g, x in con["sleeves"].items()}},
        "stress": {k: {"nombre": v["nombre"], "retorno": v["retorno"], "pnl": v["pnl_clp"],
                       "metas": {g: m.get("prob_exito") for g, m in (v.get("metas") or {}).items()},
                       "desde": v.get("desde"), "hasta": v.get("hasta")}
                   for k, v in {**st["hipoteticos"], **st["historicos"]}.items()},
        "inverso": st.get("inverso"),
        "limites": adv["limites_ips"]["controles"],
        "flujos": {k: adv["flujos"].get(k) for k in ("aportes_externos", "retiros_externos", "ganancia_neta", "lectura")},
        "faltantes": [c["variable"] for c in adv["catalogo"] if c["estado"] == "missing_critical"],
        "benchmark": {"relativo": {k: v for k, v in (adv["relativo"].get("realizado") or {}).items()
                                   if k in ("retorno_portafolio_anual", "retorno_benchmark_anual", "exceso_anual",
                                            "hit_ratio", "desde", "hasta", "tracking_error_bloqueado")}},
    }

funds = {}
for k, rv in b.fund_reviews.items():
    i = rv.idd
    funds[k] = {
        "key": k, "nombre": u[k].nombre, "administradora": u[k].administradora, "clase": u[k].clase_activo,
        "subclase": u[k].subclase, "liquidez": u[k].liquidez, "precio_de_mercado": u[k].precio_de_mercado,
        "ficha": rv.ficha,
        "idd": {x: i.get(x) for x in ("desde_datos", "hasta", "meses", "anios_datos", "retorno_1a", "retorno_3a",
                                       "retorno_5a", "volatilidad_3a", "max_drawdown_3a", "sharpe_3a",
                                       "calmar_3a", "advertencia")},
        "relativo": {x: (i.get("relativo") or {}).get(x) for x in ("n_obs", "exceso_anual", "tracking_error",
                                                                    "information_ratio", "beta", "hit_ratio")}
        if i.get("relativo") else None,
        "exceso_12m": i.get("exceso_12m_rolling"),
        "senales": rv.senales, "pilares": rv.pilares, "odd": rv.odd, "etapas": rv.etapas,
        "estado": rv.approved_list.estado, "elegibilidad": rv.elegibilidad, "no_evaluado": rv.no_evaluado,
        "tenedores": b.aggregates["tenedores"][k],
        "nav": [{"f": p.fecha, "v": round(p.valor_cuota, 4)} for p in u[k].series.points
                if p.fecha >= date(2021, 10, 1) and p.fecha.weekday() == 4],
    }

data = {
    "as_of": b.as_of, "notas": b.notes, "dimensiones": {d: DIMENSION_NAMES[d] for d in DIMENSIONS},
    "agregados": b.aggregates, "monitoreo": b.monitoring, "clientes": clients, "fondos": funds,
    "escenarios_version": SCENARIO_LIBRARY["version"],
    "fuente_fondos": __import__("afi_quant.due_diligence.review", fromlist=["load_dossiers"]).load_dossiers()["fuente"],
}
txt = json.dumps(js(data), ensure_ascii=False, separators=(",", ":"))
open(OUT, "w", encoding="utf-8").write(txt)
print(len(txt), {c: len(v["ts"]["fechas"]) for c, v in clients.items()})
