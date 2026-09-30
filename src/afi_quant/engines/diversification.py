"""
Motor de Diversificación (CORE).

Modelos: HHI (Herfindahl-Hirschman), Risk Contribution / Marginal y
matriz de correlaciones — CORE en el Model Governance Registry.

Opera sobre la asignación total: la de `input_data["current_weights"]`
si viene (cartera real en una revisión), o la que acaba de proponer el
Motor de Construcción en este mismo caso.
"""

from __future__ import annotations

import math

from afi_quant.engines.base import EngineResult, parameter_value


def hhi(weights: dict[str, float]) -> float:
    return sum(w * w for w in weights.values())


def group_weights(weights: dict[str, float], group_of: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, w in weights.items():
        out[group_of[k]] = out.get(group_of[k], 0.0) + w
    return out


def risk_contributions(weights: dict[str, float], cov) -> dict[str, float]:
    """Fracción de la varianza total que aporta cada vehículo: w_i·(Σw)_i / w'Σw (suma 1)."""
    marginal = {i: sum(cov[(i, j)] * weights[j] for j in weights) for i in weights}
    var = sum(weights[i] * marginal[i] for i in weights)
    return {i: weights[i] * marginal[i] / var for i in weights}


class DiversificationEngine:
    name = "diversification"
    required_critical_data = ["cma_estimate", "vehicle_universe"]

    def run(self, case) -> EngineResult:
        weights = case.input_data.get("current_weights")
        if weights is None:
            construction = case.engine_results.get("construction")
            if construction is None or construction.insufficient_data:
                return EngineResult(
                    engine_name=self.name, insufficient_data=True,
                    insufficient_data_reason="No hay cartera sobre la cual medir diversificación.",
                )
            weights = construction.values["asignacion_total"]
        weights = {k: w for k, w in weights.items() if w > 0}

        cma = case.input_data["cma_estimate"]
        universe = case.input_data["vehicle_universe"]
        by_manager = group_weights(weights, {k: universe[k].administradora for k in weights})
        by_class = group_weights(weights, {k: universe[k].clase_activo for k in weights})

        values: dict = {
            "pesos": weights,
            "hhi_vehiculos": hhi(weights),
            "pesos_por_administradora": by_manager,
            "pesos_por_clase": by_class,
            "contribucion_riesgo": risk_contributions(weights, cma.cov),
            "volatilidad_ex_ante": math.sqrt(cma.portfolio_variance(weights)),
            "correlaciones": {f"{i}-{j}": cma.corr[(i, j)]
                              for i in cma.keys for j in cma.keys if i < j},
        }

        alerts: list[str] = []
        max_hhi = parameter_value(case, "max_hhi")
        if max_hhi is not None and values["hhi_vehiculos"] > float(max_hhi):
            alerts.append(f"HHI {values['hhi_vehiculos']:.3f} sobre el máximo {float(max_hhi):.3f}")
        max_mgr = parameter_value(case, "max_concentration_per_manager_pct")
        if max_mgr is not None:
            for mgr, w in by_manager.items():
                if w > float(max_mgr) / 100 + 1e-9:
                    alerts.append(f"{mgr} concentra {w:.1%}, sobre el máximo {float(max_mgr):.0f}% por administradora")
        values["alertas"] = alerts
        return EngineResult(engine_name=self.name, values=values)
