"""
Motor de onboarding para la Mesa Central (asistente "Nuevo cliente").

El artifact no puede llamar al motor Python, así que el asistente reimplementa
en JS la construcción desde cero con las MISMAS reglas, alimentado con lo que
exporta este módulo:

  - CMA a la fecha de decisión (μ y Σ con shrinkage Ledoit-Wolf), igual que
    `build_cma` en el onboarding del libro.
  - Parámetros de construcción y del Monte Carlo del Parameter Registry.
  - Retornos mensuales históricos re-centrados en la CMA (base del bootstrap).
  - Escenarios del Comité y trayectorias relativas de cada episodio histórico.
  - Límites de riesgo de referencia por perfil (los del libro sintético).
  - Catálogo de información (ESFS 9.1 / DF 5.2) con el estado de lo que no
    depende del cliente.
  - Un caso de control calculado por `LifecycleSimulation.construct`, el
    mismo camino que el onboarding del libro, para verificar paridad en JS.

Los retornos van sin redondear: la paridad del bootstrap es exacta, no aproximada.
"""

from __future__ import annotations

import math
from datetime import date

from afi_quant.book.clients import sim_002, sim_003
from afi_quant.clients.ips import CATALOG
from afi_quant.clients.profile import ClientProfile, Goal
from afi_quant.engines.cma import build_cma, monthly_history
from afi_quant.engines.goals import SEED, recentered_returns
from afi_quant.engines.scenario import EPISODE_SUBSTITUTES, RECOVERY_HORIZON_DAYS, _price_on
from afi_quant.simulation.lifecycle import CMA_WINDOW_MONTHS, LifecycleSimulation
from afi_quant.simulation.parameters import SCENARIO_LIBRARY, synthetic_ips

PARAMS = ("risk_horizon_short_max_months", "risk_horizon_medium_max_months", "vol_cap_short_pct",
          "vol_cap_medium_pct", "vol_cap_long_pct", "max_weight_per_vehicle_pct",
          "short_horizon_eligible_subclass", "risk_aversion_delta", "mc_simulations", "mc_block_months",
          "cma_return_shrinkage", "cma_covariance_shrinkage")

# Variables del catálogo que el asistente completa con lo que declara el cliente
CLIENT_VARS = {
    "IPS vigente y firmado", "Moneda base", "País de residencia y segmento", "Perfil y tolerancia al riesgo declarada",
    "Capacidad de riesgo (objetiva)", "Límites de riesgo por perfil (vol / VaR / ES)", "Drawdown tolerado",
    "Patrimonio total (incluye fuera de AFI)", "Inversiones existentes fuera de AFI",
    "Life balance sheet (capital humano, activos, pasivos, compromisos)",
    "Restricciones ESG / regulatorias / familiares", "Límites de concentración (emisor / gestor / país)",
    "Monto y fecha de cada meta", "Horizonte de cada meta (corto / medio / largo)", "Moneda de cada meta",
    "Probabilidad deseada de cada meta", "Prioridad relativa de cada meta",
    "Liquidez requerida en la fecha de cada meta",
    "Calendario de flujos esperados (aportes, retiros, impuestos, gastos)",
}
# Existen solo después de ejecutar la propuesta (no bloquean una construcción desde cero)
POST_VARS = {"Flujos realizados fechados y clasificados", "Posiciones por instrumento", "SAA vigente y bandas"}


def episode_relative_paths(universe, desde: date, hasta: date, recovery_days=RECOVERY_HORIZON_DAYS) -> dict:
    """Precio relativo al inicio de cada vehículo, día a día, con las reglas de `episode_path`
    (sustitutos, plano sin dato) y sin cortar en la recuperación: el corte depende de la cartera."""
    end_cap = date.fromordinal(hasta.toordinal() + recovery_days)
    series, sources = {}, {}
    for k, v in universe.items():
        p0 = _price_on(v.series.points, desde)
        if p0 is not None and (desde - p0.fecha).days <= 7:
            series[k], sources[k] = v.series.points, "observado"
    for k in universe:
        if k in series:
            continue
        sub = EPISODE_SUBSTITUTES.get(k)
        if series.get(sub):
            series[k], sources[k] = series[sub], f"sustituto ({sub})"
        else:
            series[k], sources[k] = None, "sin dato: plano"
    last_data = min(s[-1].fecha for s in series.values() if s)
    days = sorted({p.fecha for s in series.values() if s for p in s if desde <= p.fecha <= min(end_cap, last_data)})
    rel = {}
    for k, s in series.items():
        if s is None:
            rel[k] = [1.0] * len(days)
            continue
        base = _price_on(s, desde).valor_cuota
        rel[k] = [round(_price_on(s, d).valor_cuota / base, 6) for d in days]
    return {"fechas": [d.isoformat() for d in days], "rel": rel, "fuentes": sources}


def control_case(u, reg, as_of: date) -> dict:
    """Prospecto de control: lo construye el motor real (LifecycleSimulation.construct)."""
    def ym(months):
        y, m = divmod(as_of.month - 1 + months, 12)
        return date(as_of.year + y, m + 1, 28)

    goals = [
        Goal("emergencia", "Fondo de emergencia", "esencial", 15_000_000, None, 15_000_000, 0,
             liquidez_requerida="disponible en 3 días hábiles"),
        Goal("auto", "Cambio de auto", "aspiracional", 20_000_000, ym(10), 17_000_000, 300_000,
             probabilidad_deseada=0.7, liquidez_requerida="efectivo en la fecha"),
        Goal("vivienda", "Pie de vivienda", "importante", 90_000_000, ym(30), 60_000_000, 700_000,
             probabilidad_deseada=0.8, liquidez_requerida="efectivo en la fecha"),
        Goal("retiro", "Capital de retiro", "esencial", 600_000_000, ym(240), 120_000_000, 1_000_000,
             probabilidad_deseada=0.75, liquidez_requerida="retiros programados"),
    ]
    client = ClientProfile("PRO-CONTROL", "Prospecto de control", date(1985, 6, 1), "Moderado", None, None,
                           goals=goals, nota="Caso de control para la paridad JS–Python; no es una persona real.")
    ips = synthetic_ips()
    sim = LifecycleSimulation(client, u, reg, as_of, ips=ips, scenario_library=SCENARIO_LIBRARY)
    capital = {g.key: g.capital_inicial for g in goals}
    case, _ = sim.construct(as_of, capital, "onboarding — control de paridad")
    con = case.engine_results["construction"].values
    gr = case.engine_results["clientgoal"].values if "clientgoal" in case.engine_results else {}
    return {
        "metas": [{"key": g.key, "nombre": g.nombre, "prioridad": g.prioridad, "objetivo": g.monto_objetivo,
                   "fecha": g.fecha.isoformat() if g.fecha else None, "capital": g.capital_inicial,
                   "aporte": g.aporte_mensual, "prob_deseada": g.probabilidad_deseada,
                   "liquidez": g.liquidez_requerida} for g in goals],
        "vol_ips_pct": ips.limites_riesgo.volatilidad_max_pct,
        "esperado": {
            "sleeves": {k: {"horizonte": s["horizonte"], "tope": s["tope_volatilidad"], "fuente": s["tope_fuente"],
                            "pesos": s["pesos"], "ret": s["retorno_esperado"], "vol": s["volatilidad_ex_ante"]}
                        for k, s in con["sleeves"].items()},
            "total": con["asignacion_total"],
            "metas": {k: {x: v.get(x) for x in ("prob_exito", "p10", "p50", "p90", "media", "cobertura")}
                      for k, v in gr.get("metas", {}).items()},
            "alternativas": {g: {"nivel": a.get("nivel"), "recomendada": a.get("recomendada"),
                                 "alts": {k: {x: v.get(x) for x in ("pesos", "retorno_esperado", "volatilidad_ex_ante",
                                                                    "prob_exito", "hhi", "admisible")}
                                          for k, v in a.get("alternativas", {}).items()}}
                             for g, a in (case.alternatives or {}).items()},
        },
    }


def motor_payload(u, reg, P, as_of: date, estados: dict[str, dict]) -> dict:
    """`estados`: catálogo evaluado de un cliente del libro; de ahí sale el estado de lo
    que depende de la plataforma (CMAs, curvas, Approved List...), igual para todo cliente."""
    VEH = list(u)
    cma = build_cma(u, as_of, CMA_WINDOW_MONTHS, P)
    hist = monthly_history(u, as_of)
    rr = recentered_returns(hist, cma)
    lib = SCENARIO_LIBRARY
    ref_ips = {"Conservador": sim_002().ips, "Moderado": synthetic_ips(), "Agresivo": sim_003().ips}
    episodes = {}
    for k, e in lib["episodios"].items():
        d0, d1 = date.fromisoformat(e["desde"]), date.fromisoformat(e["hasta"])
        episodes[k] = {"nombre": e["nombre"], "desde": e["desde"], "hasta": e["hasta"],
                       **episode_relative_paths(u, d0, d1)}
    return {
        "as_of": as_of.isoformat(), "vehiculos": VEH,
        "subclase": {k: v.subclase for k, v in u.items()},
        "liquidez": {k: v.liquidez for k, v in u.items()},
        "params": {p: P(p) for p in PARAMS}, "semilla": SEED, "paso_grilla": 0.05,
        "cma": {"desde": cma.desde.isoformat(), "hasta": cma.hasta.isoformat(), "n_obs": cma.n_obs,
                "intensidad": cma.shrinkage_intensidad, "metodo": cma.shrinkage_metodo,
                "rbar": cma.correlacion_promedio, "nota": cma.nota,
                "mu": [cma.mu[k] for k in VEH], "cov": [[cma.cov[(i, j)] for j in VEH] for i in VEH]},
        "historia": {"meses": [m.isoformat() for m in hist.months], "retornos": [rr[k] for k in VEH]},
        "escenarios": {k: {"nombre": s["nombre"], "shocks": {v: s["shocks"][u[v].subclase] / 100 for v in VEH},
                           "suspendidos": [v for v in VEH if u[v].subclase in s.get("rescates_suspendidos", [])]}
                       for k, s in lib["escenarios"].items()},
        "biblioteca": {"version": lib["version"], "autor": lib["autor"]},
        "episodios": episodes,
        "perfiles": {p: {"vol": i.limites_riesgo.volatilidad_max_pct, "var": i.limites_riesgo.var95_1m_max_pct,
                         "es": i.limites_riesgo.es95_1m_max_pct, "dd": i.limites_riesgo.drawdown_tolerado_pct}
                     for p, i in ref_ips.items()},
        "catalogo": [{"grupo": c.grupo, "variable": c.variable, "criticidad": c.criticidad, "habilita": c.habilita,
                      "fuente_doc": c.fuente_doc,
                      "origen": "cliente" if c.variable in CLIENT_VARS else "post" if c.variable in POST_VARS
                      else "plataforma",
                      "estado": estados.get(c.variable, {}).get("estado"),
                      "comportamiento": estados.get(c.variable, {}).get("comportamiento")} for c in CATALOG],
        "control": control_case(u, reg, as_of),
    }


def clean(x):
    """Como `js` de build_data pero sin redondear (paridad exacta)."""
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [clean(v) for v in x]
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x
