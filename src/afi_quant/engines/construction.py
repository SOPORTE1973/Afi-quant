"""
Motor de Construcción (CORE) — MVO robusto por meta.

Modelo: MVO robusto (shrinkage + constraints), CORE en el Model
Governance Registry:  max w'μ − δ/2·w'Σw  sujeto a
  - pesos ≥ 0 que suman 100%
  - volatilidad ex-ante ≤ tope del horizonte de la meta
  - peso por vehículo ≤ `max_weight_per_vehicle_pct` (metas medio/largo)
  - metas de horizonte corto: solo la subclase elegible (Money Market)

Resolución: búsqueda exhaustiva en una grilla de 5 puntos porcentuales.
Con 5 vehículos son 10.626 carteras — se evalúan todas. Es exacto para
esa grilla, determinístico y auditable: cualquiera puede verificar que
la cartera elegida es la mejor de la lista, sin un solver de caja negra.

Construye una cartera POR META (goal-based): cada meta tiene su propio
horizonte de riesgo, y la asignación total es la suma ponderada por el
capital de cada meta.
"""

from __future__ import annotations

import math

from afi_quant.clients.profile import LONG, MEDIUM, SHORT
from afi_quant.engines.base import EngineResult, parameter_value

GRID_STEP = 0.05


def grid_portfolios(keys: list[str], max_weight: dict[str, float], step: float = GRID_STEP):
    """Todas las carteras long-only de la grilla (pesos múltiplos de `step`, suma 1)."""
    units = round(1 / step)
    caps = [min(units, math.floor(max_weight[k] / step + 1e-9)) for k in keys]
    alloc = [0] * len(keys)

    def rec(i: int, remaining: int):
        if i == len(keys) - 1:
            if remaining <= caps[i]:
                alloc[i] = remaining
                yield {k: alloc[j] / units for j, k in enumerate(keys) if alloc[j]}
            return
        for u in range(min(remaining, caps[i]) + 1):
            alloc[i] = u
            yield from rec(i + 1, remaining - u)
        alloc[i] = 0

    yield from rec(0, units)


def optimize_grid(cma, keys: list[str], delta: float, vol_cap: float,
                  max_weight: dict[str, float], step: float = GRID_STEP):
    """Mejor cartera de la grilla que cumple las restricciones, o None si ninguna."""
    best = None
    best_util = -math.inf
    for w in grid_portfolios(keys, max_weight, step):
        var = cma.portfolio_variance(w)
        if math.sqrt(var) > vol_cap + 1e-12:
            continue
        util = cma.portfolio_return(w) - delta / 2 * var
        if util > best_util + 1e-15:
            best, best_util = w, util
    return best


VOL_CAP_PARAM = {SHORT: "vol_cap_short_pct", MEDIUM: "vol_cap_medium_pct", LONG: "vol_cap_long_pct"}
REQUIRED_PARAMS = [
    "risk_horizon_short_max_months", "risk_horizon_medium_max_months",
    "vol_cap_short_pct", "vol_cap_medium_pct", "vol_cap_long_pct",
    "max_weight_per_vehicle_pct", "short_horizon_eligible_subclass", "risk_aversion_delta",
]


class ConstructionEngine:
    name = "construction"
    required_critical_data = ["client_profile", "cma_estimate", "vehicle_universe", "as_of_date"]

    def run(self, case) -> EngineResult:
        params = {p: parameter_value(case, p) for p in REQUIRED_PARAMS}
        missing = [p for p, v in params.items() if v is None]
        if missing:
            return EngineResult(
                engine_name=self.name, insufficient_data=True,
                insufficient_data_reason=(
                    f"Parámetros sin valor en el Parameter Registry: {missing}. Sin ellos no "
                    "hay restricciones con qué construir — no se inventan."
                ),
            )

        client = case.input_data["client_profile"]
        cma = case.input_data["cma_estimate"]
        universe = case.input_data["vehicle_universe"]
        as_of = case.input_data["as_of_date"]
        sleeve_values = case.input_data.get("sleeve_values") or {
            g.key: g.capital_inicial for g in client.goals
        }
        max_w = float(params["max_weight_per_vehicle_pct"]) / 100
        delta = float(params["risk_aversion_delta"])

        sleeves: dict[str, dict] = {}
        blocked: dict[str, str] = {}
        for goal in client.goals:
            if goal.key not in sleeve_values:
                continue
            horizon = goal.horizon(as_of, int(params["risk_horizon_short_max_months"]),
                                   int(params["risk_horizon_medium_max_months"]))
            vol_cap = float(params[VOL_CAP_PARAM[horizon]]) / 100
            if horizon == SHORT:
                keys = [k for k, v in universe.items()
                        if v.subclase == params["short_horizon_eligible_subclass"]]
                caps = {k: 1.0 for k in keys}
            else:
                keys = list(universe)
                caps = {k: max_w for k in keys}
            weights = optimize_grid(cma, keys, delta, vol_cap, caps)
            if weights is None:
                blocked[goal.key] = (
                    f"Ninguna cartera de la grilla cumple volatilidad ≤ {vol_cap:.1%} con los "
                    "vehículos elegibles."
                )
                continue
            sleeves[goal.key] = {
                "horizonte": horizon,
                "tope_volatilidad": vol_cap,
                "pesos": weights,
                "retorno_esperado": cma.portfolio_return(weights),
                "volatilidad_ex_ante": math.sqrt(cma.portfolio_variance(weights)),
            }

        total_capital = sum(v for k, v in sleeve_values.items() if k in sleeves)
        total: dict[str, float] = {}
        for key, sleeve in sleeves.items():
            share = sleeve_values[key] / total_capital
            for k, w in sleeve["pesos"].items():
                total[k] = total.get(k, 0.0) + share * w

        return EngineResult(
            engine_name=self.name,
            values={
                "sleeves": sleeves,
                "asignacion_total": total,
                "retorno_esperado_total": cma.portfolio_return(total),
                "volatilidad_ex_ante_total": math.sqrt(cma.portfolio_variance(total)),
                "capital_por_meta": dict(sleeve_values),
                "cma_desde": cma.desde.isoformat(),
                "cma_hasta": cma.hasta.isoformat(),
                "cma_n_obs": cma.n_obs,
                "nota_cma": cma.nota,
                "shrinkage_covarianzas": cma.shrinkage_intensidad,
                "shrinkage_metodo": cma.shrinkage_metodo,
                "no_calculado": blocked,
            },
        )
