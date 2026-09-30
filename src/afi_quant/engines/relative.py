"""
Métricas relativas contra un benchmark elegible (Motor de Performance +
Motor de Riesgo, QM IV y V). Solo se calculan si el gate de elegibilidad
habilitó la comparación — quien llama es responsable de pasar ese gate.

  - Excess Return anualizado (TWR portafolio − TWR benchmark)
  - Tracking Error: σ(retorno activo) · √12, con mínimo 36-60
    observaciones mensuales (QM V). Con menos, se declara bloqueado.
  - Information Ratio: exceso anualizado / TE (métrica de Vol. II para
    evaluación de gestores; D3-D5 en QM XVIII).
  - Beta: regresión lineal simple contra el benchmark (QM V).
  - Hit ratio: fracción de meses con retorno activo positivo (ESFS 11.1).
  - Descomposición del TE por componente: cuánto de la varianza activa
    aporta cada clase. Responde "de dónde viene el riesgo activo"
    (QM V: un TE alto puede venir de apuestas factoriales, uno bajo puede
    esconder closet indexing).
  - TE rolling de 36 meses, para ver si el riesgo activo es estable.
"""

from __future__ import annotations

import math
import statistics

MIN_TE_OBS = 36


def _annualize(r_monthly_mean: float) -> float:
    return (1 + r_monthly_mean) ** 12 - 1


def chain(rets: list[float]) -> float:
    out = 1.0
    for r in rets:
        out *= 1 + r
    return out - 1


def relative_metrics(port: list[float], bench: list[float], months: list) -> dict:
    """port/bench: retornos mensuales alineados; months: fechas de cierre."""
    n = len(port)
    active = [p - b for p, b in zip(port, bench)]
    years = n / 12
    out: dict = {
        "n_obs": n,
        "desde": months[0].isoformat() if n else None,
        "hasta": months[-1].isoformat() if n else None,
        "retorno_portafolio_anual": (1 + chain(port)) ** (1 / years) - 1 if n else None,
        "retorno_benchmark_anual": (1 + chain(bench)) ** (1 / years) - 1 if n else None,
    }
    if n:
        out["exceso_anual"] = out["retorno_portafolio_anual"] - out["retorno_benchmark_anual"]
        out["hit_ratio"] = sum(a > 0 for a in active) / n
    if n < MIN_TE_OBS:
        out["tracking_error_bloqueado"] = (
            f"Solo {n} retornos mensuales comunes; el mínimo para Tracking Error es "
            f"{MIN_TE_OBS} (QM V)."
        )
        return out
    te = statistics.stdev(active) * math.sqrt(12)
    out["tracking_error"] = te
    out["information_ratio"] = out["exceso_anual"] / te if te > 0 else None
    out["beta"] = statistics.covariance(port, bench) / statistics.variance(bench)
    out["correlacion"] = statistics.correlation(port, bench)
    return out


def te_decomposition(component_active: dict[str, list[float]], weights: dict[str, float]) -> dict:
    """
    Aporte de cada componente a la varianza activa total. component_active[k]
    es el retorno activo mensual del componente k (fondo − su proxy);
    el activo total es Σ w_k · a_k. Aporte_k = w_k · cov(a_k, a) / var(a).
    """
    keys = [k for k in weights if weights[k] > 0 and k in component_active]
    n = len(next(iter(component_active.values())))
    total = [sum(weights[k] * component_active[k][t] for k in keys) for t in range(n)]
    var = statistics.variance(total)
    if var == 0:
        return {k: 0.0 for k in keys}
    return {k: weights[k] * statistics.covariance(component_active[k], total) / var for k in keys}


def rolling_te(port: list[float], bench: list[float], months: list, window: int = MIN_TE_OBS) -> list[dict]:
    out = []
    for end in range(window, len(port) + 1):
        a = [p - b for p, b in zip(port[end - window:end], bench[end - window:end])]
        out.append({"hasta": months[end - 1].isoformat(), "te": statistics.stdev(a) * math.sqrt(12)})
    return out
