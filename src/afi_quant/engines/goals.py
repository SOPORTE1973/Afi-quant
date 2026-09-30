"""
Motor de Cliente/Goal — `AFI.ClientGoal.Engine` (QM II.10, ESFS 11.10).

  - Goal-Based Monte Carlo con bootstrap por bloques (CORE): simula la
    cartera de cada meta hasta su fecha, con los aportes del cliente, y
    estima la probabilidad de llegar al monto objetivo. Los bloques de
    meses consecutivos se toman de la historia REAL del universo hasta la
    fecha de decisión, así que se preservan la correlación entre clases y
    la autocorrelación de corto plazo.

No introduce modelos de mercado propios (ESFS 11.10): comparte el Monte
Carlo / Block Bootstrap con el Motor de Escenarios (`engines/scenario.py`),
que es donde vive el stress histórico.

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
                    seed: int = SEED, returns: dict[str, list[float]] | None = None,
                    checkpoints: dict[int, list[float]] | None = None) -> list[float]:
    """
    Valor final de cada trayectoria (cartera rebalanceada mensualmente a
    `weights`). Si se pasa `checkpoints` ({mes: []}), guarda además el valor
    de cada trayectoria en esos meses — para el abanico en el tiempo. No
    altera la secuencia aleatoria: los valores finales son los mismos.
    """
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
                if checkpoints is not None and m in checkpoints:
                    checkpoints[m].append(value)
        finals.append(value)
    return finals


def percentile(sorted_values: list[float], q: float) -> float:
    idx = min(len(sorted_values) - 1, max(0, round(q * (len(sorted_values) - 1))))
    return sorted_values[idx]


class ClientGoalEngine:
    name = "clientgoal"
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
            marks = {m: [] for m in list(range(12, months, 12)) + [months]}
            finals = sorted(bootstrap_paths(
                history, sleeves[g.key], months, int(n_sims), int(block),
                sleeve_values[g.key], contributions.get(g.key, 0.0), returns=returns,
                checkpoints=marks,
            ))
            path = [{"mes": 0, **{q: sleeve_values[g.key] for q in ("p10", "p25", "p50", "p75", "p90")}}]
            for m in sorted(marks):
                vals = sorted(marks[m])
                path.append({"mes": m, "p10": percentile(vals, 0.10), "p25": percentile(vals, 0.25),
                             "p50": percentile(vals, 0.50), "p75": percentile(vals, 0.75),
                             "p90": percentile(vals, 0.90)})
            results[g.key] = {
                "meta": g.nombre,
                "tipo": "meta con fecha",
                "meses": months,
                "monto_objetivo": g.monto_objetivo,
                "prob_exito": sum(v >= g.monto_objetivo for v in finals) / len(finals),
                "probabilidad_deseada": g.probabilidad_deseada,
                "bajo_probabilidad_deseada": (
                    g.probabilidad_deseada is not None
                    and sum(v >= g.monto_objetivo for v in finals) / len(finals) < g.probabilidad_deseada
                ),
                "p10": percentile(finals, 0.10),
                "p50": percentile(finals, 0.50),
                "p90": percentile(finals, 0.90),
                "trayectoria": path,
                "media": statistics.fmean(finals),
            }

        return EngineResult(
            engine_name=self.name,
            values={
                "metas": results,
                "simulaciones": int(n_sims),
                "bloque_meses": int(block),
                "historia_desde": history.months[0].isoformat(),
                "historia_hasta": history.months[-1].isoformat(),
                "historia_meses": len(history),
                "recentrado_en_cma": cma is not None,
            },
        )
