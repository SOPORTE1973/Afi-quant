"""
Portfolio Construction Decision Flow (DF v1.1 7.1 y 7.3, caso 3).

    Client Objectives → Horizons → Risk → Liquidity → Constraints → Expected
    Returns → Risk Model → Correlations → Optimization → Scenarios →
    Alternative Portfolios → Wealth Manager

El Construction Engine entrega la cartera MVO robusta de cada meta. Este
flujo arma las carteras alternativas que el DF pide mostrar (típico 2-4) con
modelos ya clasificados en la QM, sin inventar ninguno:

  MVO robusto           (CORE)     máx μ − δ/2·σ² en la grilla, con tope de vol
  Mínima volatilidad    (CORE)     misma grilla y restricciones, menor σ
  Paridad de riesgo ERC (ADVANCED) aporte al riesgo igualado; la QM lo define
                                   como "portafolio de referencia" de máxima
                                   diversificación de riesgo, no como reemplazo

Luego pasan por Trade-off Detection (frente a la cartera MVO) y por la
Recommendation Layer, con el mismo criterio que usa el motor.
"""

from __future__ import annotations

import math

from afi_quant.clients.profile import months_between
from afi_quant.decision.recommendation import recommendation_layer
from afi_quant.decision.tradeoff import CONSTRUCTION_DIMENSIONS, detect_tradeoffs
from afi_quant.engines.construction import grid_portfolios
from afi_quant.engines.diversification import hhi, risk_contributions
from afi_quant.engines.goals import bootstrap_paths, recentered_returns

NAMES = {"MVO": "MVO robusto (CORE)", "MINVOL": "Mínima volatilidad (CORE)",
         "ERC": "Paridad de riesgo ERC (ADVANCED, referencia)"}


def equal_risk_contribution(cma, keys: list[str], iterations: int = 500) -> dict[str, float]:
    """Pesos long-only con igual aporte a la varianza (iteración multiplicativa)."""
    w = {k: 1 / cma.vol(k) for k in keys}
    s = sum(w.values())
    w = {k: v / s for k, v in w.items()}
    for _ in range(iterations):
        rc = risk_contributions(w, cma.cov)
        w = {k: w[k] * (1 / len(keys) / rc[k]) ** 0.5 for k in keys}
        s = sum(w.values())
        w = {k: v / s for k, v in w.items()}
    return w


def construction_alternatives(*, goal, sleeve: dict, keys: list[str], caps: dict[str, float], cma,
                              delta: float, adverse_shocks: dict[str, float], history, n_sims: int,
                              block: int, value: float, contribution: float, as_of,
                              missing_data: list[str]) -> dict:
    vol_cap = sleeve["tope_volatilidad"]
    out = {"meta": goal.nombre, "alternativas": {}}
    if len(keys) < 2:
        out.update(nivel=1, recomendada=None, motivo_nivel=(
            "Un solo vehículo elegible para el horizonte: no hay carteras alternativas que comparar."))
        return out

    grid = list(grid_portfolios(keys, caps))
    feasible = [w for w in grid if math.sqrt(cma.portfolio_variance(w)) <= vol_cap + 1e-12]
    weights = {"MVO": dict(sleeve["pesos"]),
               "MINVOL": min(grid, key=cma.portfolio_variance),
               "ERC": equal_risk_contribution(cma, keys)}
    returns = recentered_returns(history, cma)
    months = months_between(as_of, goal.fecha) if goal.fecha else None
    for key, w in weights.items():
        w = {k: x for k, x in w.items() if x > 1e-9}
        vol = math.sqrt(cma.portfolio_variance(w))
        rc = risk_contributions(w, cma.cov)
        reasons = []
        over = sorted(k for k, x in w.items() if x > caps[k] + 1e-9)
        if over:
            reasons.append(f"supera el tope por fondo en {', '.join(over)}")
        if vol > vol_cap + 1e-12:
            reasons.append(f"volatilidad {vol:.1%} sobre el tope del horizonte ({vol_cap:.1%})")
        alt = {
            "nombre": NAMES[key], "pesos": w,
            "retorno_esperado": cma.portfolio_return(w), "volatilidad_ex_ante": vol,
            "utilidad": cma.portfolio_return(w) - delta / 2 * vol * vol,
            "retorno_escenario_adverso": sum(x * adverse_shocks[k] for k, x in w.items()),
            "hhi": hhi(w), "contribucion_riesgo": rc, "max_contribucion_riesgo": max(rc.values()),
            "admisible": not reasons, "motivo_inadmisible": "; ".join(reasons) or None,
            "prob_exito": None,
        }
        if months:
            finals = bootstrap_paths(history, w, months, n_sims, block, value, contribution, returns=returns)
            alt["prob_exito"] = sum(v >= goal.monto_objetivo for v in finals) / len(finals)
        out["alternativas"][key] = alt
    if all(abs(weights["MINVOL"].get(k, 0) - weights["MVO"].get(k, 0)) < 1e-9 for k in keys):
        del out["alternativas"]["MINVOL"]
        out["descartadas"] = {"MINVOL": "coincide con la cartera MVO"}

    alts = out["alternativas"]
    out["tradeoffs"] = detect_tradeoffs(
        alts, "MVO", CONSTRUCTION_DIMENSIONS,
        scenarios="retorno de cada cartera en el escenario adverso del Comité (simulación)",
        sensitivity={"carteras_admisibles_en_grilla": len(feasible), "carteras_en_grilla": len(grid)},
    )
    criterion = f"mayor utilidad μ − {delta:g}/2·σ² entre las carteras admisibles (MVO robusto, QM VII)"
    elements = {
        "criterios": criterion,
        "inputs": f"CMA al {as_of.isoformat()} ({cma.n_obs} meses, shrinkage {cma.shrinkage_metodo})",
        "resultados": {k: {"retorno_esperado": a["retorno_esperado"], "volatilidad_ex_ante": a["volatilidad_ex_ante"],
                           "prob_exito": a["prob_exito"]} for k, a in alts.items()},
        "supuestos": "μ y σ de simulación del Parameter Registry; correlaciones históricas con shrinkage",
        "restricciones": f"tope de volatilidad {vol_cap:.1%}; tope por fondo; long-only; grilla de 5 pp",
        "escenarios": {k: a["retorno_escenario_adverso"] for k, a in alts.items()},
        "sensibilidad": out["tradeoffs"]["tradeoffs"] or "sin conflictos entre carteras",
        "datos_faltantes": missing_data,
        "limitaciones": "CMAs no institucionales; ERC se muestra como referencia y no se optimiza en la grilla",
    }
    out.update(recommendation_layer(
        alternatives=alts, candidates=[k for k, a in alts.items() if a["admisible"]], criterion=criterion,
        choose=lambda ks: max(ks, key=lambda k: alts[k]["utilidad"]), elements=elements,
    ))
    return out
