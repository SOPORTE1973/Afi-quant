"""
Rebalancing Decision Flow (DF v1.0 6.8; QM XIII; ESFS 11.11).

No es un motor: la lista canónica de motores es de diez y crear uno nuevo
está prohibido (DF 20). Es un FLUJO que usa Construction (el objetivo),
Risk, Liquidity y Scenario:

    Current Portfolio → Target Allocation → Drift → ¿Es material el drift?
    → Risk Impact → Liquidity Impact → Cost Impact → Scenarios
    → Alternatives → Analytical Recommendation → Wealth Manager

Alternativas (DF v1.1 4.2): el número no es fijo. Para rebalanceo el patrón
típico es A/B/C, pero una alternativa que coincide con otra no se presenta
dos veces, y si ninguna es evaluable se declara. Candidatas:
  A — No rebalancear.
  B — Rebalanceo parcial: cada peso fuera de banda vuelve a la mitad de
      la banda (objetivo ± banda/2); el resto se reparte en proporción a lo
      que falta hacia el objetivo. Volver solo al borde haría que el ruido
      del mes siguiente lo sacara otra vez (rebalanceos recurrentes).

Admisibilidad: una alternativa solo puede recomendarse si cumple las
restricciones de construcción de la meta — vehículos elegibles (los del
objetivo vigente) y tope de volatilidad del horizonte. A se muestra
siempre, aunque no sea admisible, porque "no actuar" es una opción que el
WM debe ver con sus consecuencias.
  C — Rebalanceo completo al objetivo.

Después de calcular las alternativas, Trade-off Detection (M12) muestra qué
mejora y qué empeora cada una frente a no actuar, sin ponderar, y la
Recommendation Layer (M14) decide si la evidencia alcanza el Nivel 3.

El sistema NO ejecuta operaciones (QM XIII: "posición institucional
permanente") ni asigna quién decide (DF v1.1 3.1).
"""

from __future__ import annotations

import math

from afi_quant.clients.profile import months_between
from afi_quant.decision.recommendation import recommendation_layer
from afi_quant.decision.tradeoff import REBALANCING_DIMENSIONS, detect_tradeoffs
from afi_quant.engines.diversification import hhi
from afi_quant.engines.goals import bootstrap_paths, recentered_returns

ALTERNATIVE_NAMES = {"A": "No rebalancear", "B": "Rebalanceo parcial (a la mitad de la banda)",
                     "C": "Rebalanceo completo al objetivo"}


def drift(values: dict[str, float], target: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    keys = set(values) | set(target)
    return {k: values.get(k, 0.0) / total - target.get(k, 0.0) for k in keys}


def partial_weights(current_w: dict[str, float], target: dict[str, float], band: float) -> dict[str, float]:
    keys = set(current_w) | set(target)
    w = {k: min(max(current_w.get(k, 0.0), target.get(k, 0.0) - band), target.get(k, 0.0) + band)
         for k in keys}
    w = {k: max(0.0, v) for k, v in w.items()}
    residual = 1.0 - sum(w.values())
    if abs(residual) > 1e-12:
        if residual > 0:
            gaps = {k: max(0.0, target.get(k, 0.0) - w[k]) for k in keys}
        else:
            gaps = {k: max(0.0, w[k] - target.get(k, 0.0)) for k in keys}
        total_gap = sum(gaps.values())
        if total_gap > 0:
            for k in keys:
                w[k] += residual * gaps[k] / total_gap
    return {k: v for k, v in w.items() if v > 1e-12}


def rebalancing_flow(*, goal, values: dict[str, float], target: dict[str, float], band: float,
                     cma, universe, adverse_shocks: dict[str, float], history, n_sims: int,
                     block: int, contribution: float, as_of, missing_data: list[str],
                     vol_cap: float | None = None, band_sensitivity: float = 0.02,
                     blocking_missing: list[str] | None = None,
                     tradeoff_threshold: float | None = None) -> dict:
    total = sum(values.values())
    current_w = {k: v / total for k, v in values.items()}
    d = drift(values, target)
    worst = max(d, key=lambda k: abs(d[k]))
    material = abs(d[worst]) > band + 1e-12
    out = {
        "meta": goal.nombre, "valor": total, "banda": band, "desvios": d,
        "mayor_desvio_vehiculo": worst, "mayor_desvio": d[worst], "material": material,
        "alternativas": {}, "nivel": 0,
    }
    if not material:
        out["nota"] = ("Ningún desvío supera la banda: el filtro de materialidad detiene el flujo "
                       "antes de calcular impactos (DF 6.8). Cardinalidad cero es una respuesta válida.")
        return out

    returns = recentered_returns(history, cma)
    weights_by_alt = {"A": current_w, "B": partial_weights(current_w, target, band / 2),
                      "C": dict(target)}
    out["descartadas"] = {}
    same = lambda a, b: all(abs(a.get(k, 0.0) - b.get(k, 0.0)) < 1e-9 for k in set(a) | set(b))
    if same(weights_by_alt["B"], weights_by_alt["C"]):
        del weights_by_alt["B"]
        out["descartadas"]["B"] = "coincide con el rebalanceo completo: no es una alternativa distinta"
    eligible = {k for k, w in target.items() if w > 0}
    for key, w in weights_by_alt.items():
        trades = {k: w.get(k, 0.0) * total - values.get(k, 0.0) for k in set(w) | set(values)}
        trades = {k: v for k, v in trades.items() if abs(v) >= 1}
        sells = [k for k, v in trades.items() if v < 0]
        slowest = max((universe[k].dias_liquidez for k in sells), default=0)
        vol = math.sqrt(cma.portfolio_variance({k: x for k, x in w.items() if x}))
        adverse = sum(x * adverse_shocks[k] for k, x in w.items())
        remaining = max(abs(w.get(k, 0.0) - target.get(k, 0.0)) for k in set(w) | set(target))
        alt = {
            "nombre": ALTERNATIVE_NAMES[key],
            "pesos": w,
            "operaciones": trades,
            "rotacion_clp": sum(abs(v) for v in trades.values()) / 2,
            "mayor_desvio_restante": remaining,
            "volatilidad_ex_ante": vol,
            "hhi": hhi({k: x for k, x in w.items() if x}),
            "retorno_escenario_adverso": adverse,
            "liquidez": ("sin operaciones" if not trades else
                         f"ejecutable en hasta {slowest} días hábiles (vende {', '.join(sorted(sells))})"),
            "costos": "sin dato de costos de transacción ni impacto fiscal: se muestra la rotación",
        }
        reasons = []
        outside = sorted(k for k, x in w.items() if x > 1e-9 and k not in eligible)
        if outside:
            reasons.append(f"mantiene vehículos no elegibles para la meta ({', '.join(outside)})")
        if vol_cap is not None and vol > vol_cap + 1e-12:
            reasons.append(f"volatilidad {vol:.1%} sobre el tope del horizonte ({vol_cap:.1%})")
        alt["admisible"] = not reasons
        alt["motivo_inadmisible"] = "; ".join(reasons) or None
        if goal.fecha is not None:
            months = months_between(as_of, goal.fecha)
            finals = bootstrap_paths(history, w, months, n_sims, block, total, contribution, returns=returns)
            alt["prob_exito"] = sum(v >= goal.monto_objetivo for v in finals) / len(finals)
        out["alternativas"][key] = alt

    # Sensibilidad: qué cambia si la banda institucional fuera ±2 pp distinta
    out["sensibilidad"] = {
        f"banda {b:.0%}": {
            "material": abs(d[worst]) > b + 1e-12,
            "rotacion_parcial_clp": sum(abs(partial_weights(current_w, target, b / 2).get(k, 0.0) * total
                                            - values.get(k, 0.0))
                                        for k in set(values) | set(target)) / 2,
        }
        for b in (max(0.0, band - band_sensitivity), band + band_sensitivity)
    }

    # M12 — Trade-off Detection frente a no actuar
    out["tradeoffs"] = detect_tradeoffs(
        out["alternativas"], "A", REBALANCING_DIMENSIONS, threshold=tradeoff_threshold,
        scenarios="retorno de cada alternativa en el escenario adverso del Comité (simulación)",
        sensitivity=out["sensibilidad"],
    )

    # M14 — Recommendation Layer
    criterion = ("menor rotación entre las alternativas admisibles que dejan todos los pesos "
                 "dentro de la banda institucional")
    alts = out["alternativas"]
    candidates = [k for k, a in alts.items() if a["admisible"] and a["mayor_desvio_restante"] <= band + 1e-9]
    n_tradeoffs = len(out["tradeoffs"]["tradeoffs"])
    elements = {
        "criterios": criterion,
        "inputs": (f"valor de la meta {total:,.0f} CLP; pesos actuales y objetivo de {len(target)} "
                   f"vehículos; CMA al {as_of.isoformat()}; {n_sims} trayectorias"),
        "resultados": {k: {"rotacion_clp": a["rotacion_clp"], "volatilidad_ex_ante": a["volatilidad_ex_ante"],
                           "prob_exito": a.get("prob_exito")} for k, a in alts.items()},
        "supuestos": f"CMA de simulación; banda {band:.0%}; bootstrap por bloques de {block} meses",
        "restricciones": (f"vehículos elegibles de la meta; tope de volatilidad {vol_cap:.1%}"
                          if vol_cap is not None else "vehículos elegibles de la meta"),
        "escenarios": {k: a["retorno_escenario_adverso"] for k, a in alts.items()},
        "sensibilidad": out["sensibilidad"],
        "datos_faltantes": missing_data,
        "limitaciones": (f"{n_tradeoffs} trade-off(s) entregados al WM sin ponderar; sin costos de "
                         "transacción ni impacto tributario"),
    }
    rec = recommendation_layer(
        alternatives=alts, candidates=candidates, criterion=criterion,
        choose=lambda ks: min(ks, key=lambda k: alts[k]["rotacion_clp"]),
        elements=elements, blocking_missing=blocking_missing,
    )
    out.update(rec)
    out["datos_faltantes"] = missing_data
    if rec["recomendacion"] and rec["nivel"] == 3:
        out["recomendacion"] += " No considera costos de transacción ni impacto tributario, que no están disponibles."
    return out
