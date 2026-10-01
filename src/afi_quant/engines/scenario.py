"""
Motor de Escenarios (CORE) — "¿qué pasaría si...?" (QM XI, ESFS 11.7).

  - Hypothetical Stress: los cuatro escenarios en paralelo del Scenario
    Decision Flow (DF v1.0 6.11: Base, Optimista, Adverso, Stress), con
    shocks por subclase de la Scenario Library versionada.
  - Historical Simulation: la cartera ACTUAL aplicada a episodios reales
    (estallido social, COVID, etc.) con los retornos observados de cada
    vehículo en la ventana del episodio.

Regla de reporte (QM XI): todo escenario informa su impacto en, como
mínimo, retorno, riesgo, liquidez, concentración y objetivos del
cliente — nunca solo retorno. La moneda es transversal: la cartera es
100% CLP y el componente FX del fondo global ya viene en su NAV en CLP;
no se asume cobertura.

Trayectoria de crisis: además del resultado de punta a punta, cada episodio
trae el recorrido diario de la cartera ACTUAL comprada al inicio y mantenida
(sin rebalancear), desde el inicio del episodio hasta recuperar su valor o un
año después del fin, lo que ocurra primero. Es la misma Historical Simulation
(CORE) mirada día a día: profundidad, días hasta el fondo y días de
recuperación. No hay modelo nuevo.

Reverse Stress Testing (ADVANCED, QM XI): en vez de preguntar cuánto se
pierde en un escenario, pregunta qué shock haría falta para "romper" un
límite. La definición de ruptura es un parámetro (`reverse_stress_breach_limit`;
ESFS 11.6 la pide explícita). Con "ips_max_drawdown", la ruptura es perder la
caída máxima que tolera el IPS del cliente. Se informa en tres direcciones:
el escenario Stress escalado, la renta variable en bloque y cada fondo solo.
La relación es lineal (pérdida = Σ peso × shock), sin modelo nuevo.

Un vehículo sin historia en un episodio no se omite en silencio: se usa
el sustituto declarado (deuda privada -> money market, igual que en el
policy benchmark) o, si tampoco hay, 0% con la cobertura informada.
"""

from __future__ import annotations

import math
from datetime import date

from afi_quant.engines.base import EngineResult, parameter_value
from afi_quant.engines.diversification import hhi, risk_contributions
from afi_quant.engines.goals import bootstrap_paths, percentile, recentered_returns
from afi_quant.engines.risk import historical_var_es
from afi_quant.clients.profile import months_between

EPISODE_SUBSTITUTES = {"DP": "MM"}


def _price_on(points, d: date):
    before = [p for p in points if p.fecha <= d]
    return before[-1] if before else None


def episode_returns(universe, desde: date, hasta: date) -> dict:
    out = {}
    for k, v in universe.items():
        p0, p1 = _price_on(v.series.points, desde), _price_on(v.series.points, hasta)
        # El precio de inicio debe estar a pocos días del inicio del episodio: si la
        # serie empieza después, el vehículo no tiene dato para ese episodio.
        if p0 is not None and p1 is not None and (desde - p0.fecha).days <= 7:
            out[k] = {"retorno": p1.valor_cuota / p0.valor_cuota - 1, "fuente": "observado"}
    for k in universe:
        if k in out:
            continue
        sub = EPISODE_SUBSTITUTES.get(k)
        if sub in out and out[sub]["fuente"] == "observado":
            out[k] = {"retorno": out[sub]["retorno"], "fuente": f"sustituto ({sub})"}
        else:
            out[k] = {"retorno": 0.0, "fuente": "sin dato: 0%"}
    return out


RECOVERY_HORIZON_DAYS = 365


def episode_path(universe, values: dict[str, float], desde: date, hasta: date,
                 recovery_days: int = RECOVERY_HORIZON_DAYS) -> dict:
    """
    Valor diario de la cartera actual (comprar y mantener) durante el episodio y su
    recuperación. Un vehículo sin historia usa su sustituto declarado; sin sustituto,
    queda plano (0%) y se informa.
    """
    end_cap = date.fromordinal(hasta.toordinal() + recovery_days)
    series, sources = {}, {}
    for k in values:
        pts = universe[k].series.points
        p0 = _price_on(pts, desde)
        if p0 is not None and (desde - p0.fecha).days <= 7:
            series[k], sources[k] = pts, "observado"
    for k in values:
        if k in series:
            continue
        sub = EPISODE_SUBSTITUTES.get(k)
        if series.get(sub):
            series[k], sources[k] = series[sub], f"sustituto ({sub})"
        else:
            series[k], sources[k] = None, "sin dato: plano"
    last_data = min(s[-1].fecha for s in series.values() if s)
    days = sorted({p.fecha for s in series.values() if s for p in s if desde <= p.fecha <= min(end_cap, last_data)})
    base = {k: _price_on(s, desde).valor_cuota for k, s in series.items() if s}
    cursor = {k: 0 for k in series}
    last_px = dict(base)
    path = []
    total0 = sum(values.values())
    for d in days:
        row = {}
        for k, s in series.items():
            if s is None:
                row[k] = values[k]
                continue
            while cursor[k] < len(s) and s[cursor[k]].fecha <= d:
                last_px[k] = s[cursor[k]].valor_cuota
                cursor[k] += 1
            row[k] = values[k] * last_px[k] / base[k]
        path.append({"fecha": d, "por_vehiculo": row, "total": sum(row.values())})
        if d > hasta and path[-1]["total"] >= total0:
            break
    trough = min(path, key=lambda p: p["total"])
    rec = next((p for p in path if p["fecha"] > trough["fecha"] and p["total"] >= total0), None)
    at_end = next((p for p in reversed(path) if p["fecha"] <= hasta), path[-1])
    return {
        "puntos": path, "fuentes": sources,
        "valor_inicial": total0,
        "caida_maxima": trough["total"] / total0 - 1, "fecha_fondo": trough["fecha"],
        "dias_hasta_fondo": (trough["fecha"] - desde).days,
        "fecha_recuperacion": rec["fecha"] if rec else None,
        "dias_recuperacion": (rec["fecha"] - trough["fecha"]).days if rec else None,
        "retorno_al_fin": at_end["total"] / total0 - 1,
        "horizonte_recuperacion_dias": recovery_days,
        "datos_hasta": days[-1] if days else None,
    }


class ScenarioEngine:
    name = "scenario"
    required_critical_data = ["current_values", "vehicle_universe", "scenario_library",
                              "scenario_history", "as_of_date"]

    def run(self, case) -> EngineResult:
        data = case.input_data
        values = {k: v for k, v in data["current_values"].items() if v > 0}
        universe = data["vehicle_universe"]
        library = data["scenario_library"]
        history = data["scenario_history"]
        as_of = data["as_of_date"]
        cma = data.get("cma_estimate")
        total = sum(values.values())
        weights = {k: v / total for k, v in values.items()}

        base_ctx = {
            "weights": weights, "values": values, "total": total, "universe": universe,
            "history": history, "cma": cma, "as_of": as_of, "case": case,
            "sleeves": data.get("sleeve_holdings"), "client": data.get("client_profile"),
            "contributions": data.get("monthly_contributions") or {},
            "targets": data.get("target_sleeves"),
        }
        base_var = historical_var_es(_port_hist(history, weights), 0.95)

        hypothetical = {}
        for key, sc in library["escenarios"].items():
            shocks = {k: sc["shocks"][universe[k].subclase] / 100 for k in values}
            suspended = {k for k in values if universe[k].subclase in sc.get("rescates_suspendidos", [])}
            hypothetical[key] = self._assess(sc["nombre"], shocks, {k: "hipotético" for k in values},
                                             suspended, base_ctx, base_var)

        historical = {}
        for key, ep in library["episodios"].items():
            d0, d1 = date.fromisoformat(ep["desde"]), date.fromisoformat(ep["hasta"])
            rets = episode_returns({k: universe[k] for k in values}, d0, d1)
            res = self._assess(ep["nombre"], {k: r["retorno"] for k, r in rets.items()},
                               {k: r["fuente"] for k, r in rets.items()}, set(), base_ctx, base_var)
            res["desde"], res["hasta"] = ep["desde"], ep["hasta"]
            res["cobertura_observada"] = sum(weights[k] for k, r in rets.items() if r["fuente"] == "observado")
            res["trayectoria"] = episode_path(universe, values, d0, d1)
            historical[key] = res

        reverse = self._reverse_stress(case, weights, total, library, universe)

        return EngineResult(engine_name=self.name, values={
            "inverso": reverse,
            "biblioteca_version": library["version"],
            "biblioteca_autor": library["autor"],
            "valor_base": total,
            "var95_1m_base": base_var[0],
            "hipoteticos": hypothetical,
            "historicos": historical,
            "moneda": "Cartera 100% CLP; el componente FX del fondo global viene en su NAV en CLP, sin cobertura asumida.",
        })

    def _reverse_stress(self, case, weights, total, library, universe) -> dict:
        breach = parameter_value(case, "reverse_stress_breach_limit")
        ips = case.input_data.get("ips")
        if breach is None:
            return {"no_calculado": "Sin definición de 'ruptura' en el Parameter Registry (ESFS 11.6)."}
        if breach != "ips_max_drawdown":
            return {"no_calculado": f"Definición de ruptura no soportada: {breach}."}
        tol_pct = ips.limites_riesgo.drawdown_tolerado_pct if ips else None
        if tol_pct is None:
            return {"no_calculado": "El IPS no declara caída máxima tolerada: no hay límite que romper."}
        tol = tol_pct / 100

        def needed(exposure: float) -> dict:
            shock = -tol / exposure if exposure > 0 else None
            return {"exposicion": exposure, "shock_necesario": shock,
                    "posible": shock is not None and shock >= -1.0}

        stress = library["escenarios"].get("stress")
        scaled = None
        if stress:
            loss = -sum(w * stress["shocks"][universe[k].subclase] / 100 for k, w in weights.items())
            mult = tol / loss if loss > 0 else None
            scaled = {"perdida_escenario": loss, "multiplicador": mult,
                      "shocks_en_ruptura": ({s: v * mult for s, v in stress["shocks"].items()}
                                            if mult else None)}
        equity = sum(w for k, w in weights.items() if universe[k].clase_activo == "Renta Variable")
        return {
            "definicion": f"pérdida igual a la caída máxima tolerada en el IPS ({tol:.0%})",
            "limite": tol, "perdida_clp": tol * total,
            "escenario_stress_escalado": scaled,
            "renta_variable_en_bloque": needed(equity),
            "por_fondo": {k: needed(w) for k, w in weights.items()},
            "nota": ("Lineal y sin correlaciones: cada dirección supone que solo se mueve lo indicado. "
                     "Un shock 'no posible' exige perder más de 100% del fondo."),
        }

    def _assess(self, nombre, shocks, sources, suspended, ctx, base_var) -> dict:
        weights, values, total = ctx["weights"], ctx["values"], ctx["total"]
        post = {k: values[k] * (1 + shocks[k]) for k in values}
        post_total = sum(post.values())
        post_w = {k: v / post_total for k, v in post.items()}
        pnl_by = {k: post[k] - values[k] for k in values}

        # Riesgo: VaR 95% 1m histórico con los pesos post-shock
        var_post = historical_var_es(_port_hist(ctx["history"], post_w), 0.95)

        # Liquidez: activos disponibles en 0-3m vs obligaciones de 0-3m y 3-12m
        client, as_of = ctx["client"], ctx["as_of"]
        liquid = sum(v for k, v in post.items() if k not in suspended
                     and ctx["universe"][k].dias_liquidez <= 90)
        oblig_short = oblig_12m = 0.0
        if client is not None:
            for g in client.goals:
                if g.fecha is None:
                    oblig_short += g.monto_objetivo
                elif g.fecha > as_of and (g.fecha - as_of).days <= 365:
                    oblig_12m += g.monto_objetivo

        # Concentración
        cma = ctx["cma"]
        rc = risk_contributions(post_w, cma.cov) if cma is not None else None

        # Objetivos del cliente: probabilidad de éxito desde los valores post-shock
        goals = self._goal_probabilities(shocks, ctx)

        return {
            "nombre": nombre,
            "retorno": post_total / total - 1,
            "pnl_clp": post_total - total,
            "pnl_por_vehiculo": pnl_by,
            "shock_por_vehiculo": shocks,
            "fuente_por_vehiculo": sources,
            "mayor_perdida_vehiculo": (min(pnl_by, key=pnl_by.get)
                                       if min(pnl_by.values()) < 0 else None),
            "var95_1m_post": var_post[0],
            "var95_1m_cambio": var_post[0] - base_var[0],
            "liquidez_0_3m_disponible": liquid,
            "rescates_suspendidos": sorted(suspended),
            "lcr_0_3m": liquid / oblig_short if oblig_short else None,
            "lcr_0_12m": liquid / (oblig_short + oblig_12m) if (oblig_short + oblig_12m) else None,
            "pesos_post": post_w,
            "hhi_post": hhi(post_w),
            "contribucion_riesgo_post": rc,
            "metas": goals,
        }

    def _goal_probabilities(self, shocks, ctx) -> dict:
        case, client, sleeves, targets = ctx["case"], ctx["client"], ctx["sleeves"], ctx["targets"]
        n_sims = parameter_value(case, "mc_simulations")
        block = parameter_value(case, "mc_block_months")
        if client is None or sleeves is None or targets is None or n_sims is None or block is None:
            return {}
        returns = recentered_returns(ctx["history"], ctx["cma"]) if ctx["cma"] is not None else None
        out = {}
        for g in client.goals:
            if g.key not in sleeves:
                continue
            post_value = sum(v * (1 + shocks.get(k, 0.0)) for k, v in sleeves[g.key].items())
            if g.fecha is None:
                out[g.key] = {"meta": g.nombre, "tipo": "reserva", "cobertura": post_value / g.monto_objetivo}
                continue
            months = months_between(ctx["as_of"], g.fecha)
            finals = sorted(bootstrap_paths(ctx["history"], targets[g.key], months, int(n_sims), int(block),
                                            post_value, ctx["contributions"].get(g.key, 0.0), returns=returns))
            out[g.key] = {"meta": g.nombre, "tipo": "meta con fecha",
                          "prob_exito": sum(v >= g.monto_objetivo for v in finals) / len(finals),
                          "p50": percentile(finals, 0.5)}
        return out


def _port_hist(history, weights) -> list[float]:
    return [sum(w * history.returns[k][t] for k, w in weights.items()) for t in range(len(history))]
