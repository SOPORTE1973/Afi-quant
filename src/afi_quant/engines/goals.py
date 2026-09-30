"""
Motor de Cliente/Goal y Motor de Escenarios.

  - Goal-Based Monte Carlo con bootstrap por bloques (CORE): simula la
    cartera de cada meta hasta su fecha, con los aportes del cliente, y
    estima la probabilidad de llegar al monto objetivo. Los bloques de
    meses consecutivos se toman de la historia REAL del universo hasta la
    fecha de decisión, así que se preservan la correlación entre clases y
    la autocorrelación de corto plazo.
  - Historical Simulation (CORE): aplica a la cartera actual los peores
    12 meses y el peor mes observados en esa misma historia.

Si el caso trae una CMA (`cma_estimate`), cada retorno histórico se
re-centra en ella: r' = (r − media histórica)·(σ_CMA/σ_hist) + μ_CMA/12.
Así la proyección usa los mismos supuestos que la construcción, y de la
historia toma solo la forma de las fluctuaciones (correlaciones, rachas).

Reproducibilidad: la semilla es fija. Con los mismos datos y parámetros,
el resultado es idéntico (Principio 3). Los montos son nominales en CLP.

Limitación declarada (registro de modelos): el resultado depende de la
representatividad del histórico usado.
"""

from __future__ import annotations

import random
import statistics

from afi_quant.clients.profile import months_between
from afi_quant.engines.base import EngineResult, parameter_value

SEED = 20241031


def recentered_returns(history, cma) -> dict[str, list[float]]:
    """Retornos históricos con media μ_CMA/12 y volatilidad σ_CMA/√12."""
    out = {}
    for k, rets in history.returns.items():
        mean = statistics.fmean(rets)
        sd = statistics.stdev(rets)
        scale = (cma.vol(k) / 12 ** 0.5) / sd if sd > 0 else 1.0
        out[k] = [(r - mean) * scale + cma.mu[k] / 12 for r in rets]
    return out


def bootstrap_paths(history, weights: dict[str, float], months: int, n_sims: int,
                    block: int, start_value: float, monthly_contribution: float,
                    seed: int = SEED, returns: dict[str, list[float]] | None = None) -> list[float]:
    """Valor final de cada trayectoria (cartera rebalanceada mensualmente a `weights`)."""
    returns = returns or history.returns
    port = [sum(weights[k] * returns[k][t] for k in weights) for t in range(len(history))]
    n = len(port)
    rng = random.Random(seed)
    finals = []
    for _ in range(n_sims):
        value = start_value
        m = 0
        while m < months:
            start = rng.randrange(n)
            for j in range(block):
                if m >= months:
                    break
                value = value * (1 + port[(start + j) % n]) + monthly_contribution
                m += 1
        finals.append(value)
    return finals


def percentile(sorted_values: list[float], q: float) -> float:
    idx = min(len(sorted_values) - 1, max(0, round(q * (len(sorted_values) - 1))))
    return sorted_values[idx]


def historical_stress(history, weights: dict[str, float]) -> dict:
    """Retornos observados SIN re-centrar: es lo que efectivamente pasó."""
    port = [sum(weights[k] * history.returns[k][t] for k in weights) for t in range(len(history))]
    worst_month = min(range(len(port)), key=lambda t: port[t])
    worst_12 = None
    for t in range(len(port) - 11):
        r = 1.0
        for x in port[t:t + 12]:
            r *= 1 + x
        if worst_12 is None or r - 1 < worst_12[0]:
            worst_12 = (r - 1, t)
    out = {
        "peor_mes": port[worst_month],
        "peor_mes_fecha": history.months[worst_month].isoformat(),
    }
    if worst_12:
        out["peores_12m"] = worst_12[0]
        out["peores_12m_hasta"] = history.months[worst_12[1] + 11].isoformat()
    return out


class GoalsEngine:
    name = "goals"
    required_critical_data = ["client_profile", "scenario_history", "as_of_date"]

    def run(self, case) -> EngineResult:
        n_sims = parameter_value(case, "mc_simulations")
        block = parameter_value(case, "mc_block_months")
        if n_sims is None or block is None:
            return EngineResult(
                engine_name=self.name, insufficient_data=True,
                insufficient_data_reason=(
                    "Faltan 'mc_simulations' o 'mc_block_months' en el Parameter Registry."
                ),
            )
        client = case.input_data["client_profile"]
        history = case.input_data["scenario_history"]
        as_of = case.input_data["as_of_date"]
        sleeves = case.input_data.get("target_sleeves")
        if sleeves is None:
            construction = case.engine_results.get("construction")
            if construction is None or construction.insufficient_data:
                return EngineResult(
                    engine_name=self.name, insufficient_data=True,
                    insufficient_data_reason="No hay carteras por meta que proyectar.",
                )
            sleeves = {k: s["pesos"] for k, s in construction.values["sleeves"].items()}
            sleeve_values = construction.values["capital_por_meta"]
        else:
            sleeve_values = case.input_data["sleeve_values"]
        contributions = case.input_data.get("monthly_contributions") or {
            g.key: g.aporte_mensual for g in client.goals
        }

        cma = case.input_data.get("cma_estimate")
        returns = recentered_returns(history, cma) if cma is not None else None

        results = {}
        for g in client.goals:
            if g.key not in sleeves or g.key not in sleeve_values:
                continue
            if g.fecha is None:
                results[g.key] = {
                    "meta": g.nombre,
                    "tipo": "reserva",
                    "valor_actual": sleeve_values[g.key],
                    "cobertura": sleeve_values[g.key] / g.monto_objetivo,
                }
                continue
            months = months_between(as_of, g.fecha)
            if months <= 0:
                continue
            finals = sorted(bootstrap_paths(
                history, sleeves[g.key], months, int(n_sims), int(block),
                sleeve_values[g.key], contributions.get(g.key, 0.0), returns=returns,
            ))
            results[g.key] = {
                "meta": g.nombre,
                "tipo": "meta con fecha",
                "meses": months,
                "monto_objetivo": g.monto_objetivo,
                "prob_exito": sum(v >= g.monto_objetivo for v in finals) / len(finals),
                "p10": percentile(finals, 0.10),
                "p50": percentile(finals, 0.50),
                "p90": percentile(finals, 0.90),
                "media": statistics.fmean(finals),
            }

        total_value = sum(sleeve_values[k] for k in sleeves if k in sleeve_values)
        total_w: dict[str, float] = {}
        for k, w in sleeves.items():
            if k not in sleeve_values:
                continue
            for v, x in w.items():
                total_w[v] = total_w.get(v, 0.0) + x * sleeve_values[k] / total_value

        return EngineResult(
            engine_name=self.name,
            values={
                "metas": results,
                "stress_historico": historical_stress(history, total_w),
                "simulaciones": int(n_sims),
                "bloque_meses": int(block),
                "historia_desde": history.months[0].isoformat(),
                "historia_hasta": history.months[-1].isoformat(),
                "historia_meses": len(history),
                "recentrado_en_cma": cma is not None,
            },
        )
