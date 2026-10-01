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


def effective_number_of_bets(rc: dict[str, float]) -> float:
    """1 / Σ rc² (ADVANCED). QM XXIII Pendiente 3: convención propia, falta validarla."""
    s = sum(x * x for x in rc.values())
    return 1 / s if s > 0 else float("nan")


def diversification_ratio(weights: dict[str, float], cov) -> float:
    """Σ w_i σ_i / σ_p: cuánto reduce la correlación el riesgo frente a sumar riesgos (ADVANCED)."""
    sig_p = math.sqrt(sum(weights[i] * weights[j] * cov[(i, j)] for i in weights for j in weights))
    return sum(w * math.sqrt(cov[(k, k)]) for k, w in weights.items()) / sig_p


def look_through_issuers(weights: dict[str, float], dossiers: dict) -> list[dict]:
    """
    Exposición de la cartera a cada emisor sumando lo que cada fondo informa a la CMF
    (QM VI: concentraciones ocultas). Lo no informado queda como 'resto' por fondo.
    """
    out: dict[str, dict] = {}
    for k, w in weights.items():
        exp = (dossiers.get(k) or {}).get("exposicion") or {}
        listed = 0.0
        for name, kind, pct in exp.get("emisores", []):
            row = out.setdefault(name, {"emisor": name, "tipo": kind, "peso": 0.0, "por_fondo": {}})
            row["peso"] += w * pct / 100
            row["por_fondo"][k] = row["por_fondo"].get(k, 0.0) + w * pct / 100
            listed += pct
        rest = max(0.0, 100 - listed)
        if rest > 0.5:
            name = f"Resto de {k} (posiciones menores)"
            out[name] = {"emisor": name, "tipo": "resto", "peso": w * rest / 100, "por_fondo": {k: w * rest / 100}}
    return sorted(out.values(), key=lambda r: -r["peso"])


def exposure_breakdown(weights: dict[str, float], universe, dossiers: dict) -> dict[str, dict[str, float]]:
    """Diversificación por dimensión (DF 7.1: asset class, moneda, geografía, liquidez, gestor)."""
    dims: dict[str, dict[str, float]] = {k: {} for k in ("clase", "subclase", "moneda", "geografia", "liquidez",
                                                          "administradora")}

    def add(dim, key, x):
        dims[dim][key] = dims[dim].get(key, 0.0) + x

    for k, w in weights.items():
        v = universe[k]
        ext = ((dossiers.get(k) or {}).get("exposicion") or {}).get("extranjero_pct", 0.0) / 100
        add("clase", v.clase_activo, w)
        add("subclase", v.subclase, w)
        add("moneda", "USD (subyacente)" if ext else "CLP", w)
        add("geografia", "Extranjero" if ext else "Chile", w)
        add("liquidez", v.liquidez, w)
        add("administradora", v.administradora, w)
    return dims


def factor_exposure(weights: dict[str, float], universe, dossiers: dict) -> dict[str, float]:
    """
    Exposición a factores básicos por CLASIFICACIÓN de cada fondo (acciones, crédito, tasa,
    moneda). El Factor Risk por regresión es ADVANCED y no se calcula aquí (QM V).
    """
    out = {"Acciones locales": 0.0, "Acciones globales": 0.0, "Crédito corporativo": 0.0,
           "Crédito privado": 0.0, "Liquidez": 0.0, "Moneda extranjera": 0.0, "Tasa (duración ponderada, años)": 0.0}
    for k, w in weights.items():
        v, exp = universe[k], ((dossiers.get(k) or {}).get("exposicion") or {})
        if v.clase_activo == "Renta Variable":
            out["Acciones globales" if exp.get("extranjero_pct") else "Acciones locales"] += w
        elif v.subclase == "Money Market":
            out["Liquidez"] += w
        elif v.clase_activo == "Deuda Privada":
            out["Crédito privado"] += w
        else:
            out["Crédito corporativo"] += w
        out["Tasa (duración ponderada, años)"] += w * (exp.get("duracion_anios") or 0.0)
        out["Moneda extranjera"] += w * (exp.get("extranjero_pct") or 0.0) / 100
    return out


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
