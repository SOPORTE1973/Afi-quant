"""
Trade-off Detection (M12; DF v1.1 Parte 4.3).

Compara alternativas ya calculadas por los motores dimensión por dimensión.
Cuando una alternativa mejora una dimensión y empeora otra frente a la
referencia, hay un trade-off. El módulo NO pondera dimensiones ni elige: no
existe una función del tipo "riesgo 30%, liquidez 30%". Solo arma los nueve
pasos obligatorios y entrega el conflicto al Wealth Manager.

No calcula métricas nuevas: cada dimensión es un campo que un motor o un
flujo ya produjo para la alternativa. Si falta en alguna, esa dimensión no
entra a la comparación.

El umbral de qué conflicto es material (`tradeoff_materiality_threshold`) es
una pregunta abierta del DF (8.3 OQ4). Sin valor, se muestran todos.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dimension:
    key: str             # campo de la alternativa
    nombre: str
    motor: str           # de dónde viene el dato
    mejor: str           # "menor" o "mayor"
    formato: str = "pct"  # "pct" o "clp"


REBALANCING_DIMENSIONS = (
    Dimension("volatilidad_ex_ante", "Volatilidad ex-ante", "Risk", "menor"),
    Dimension("retorno_escenario_adverso", "Retorno en escenario adverso", "Scenario", "mayor"),
    Dimension("prob_exito", "Probabilidad de lograr la meta", "ClientGoal", "mayor"),
    Dimension("hhi", "Concentración (HHI)", "Diversification", "menor", "num"),
    Dimension("mayor_desvio_restante", "Desvío restante frente al objetivo", "Construction", "menor"),
    Dimension("rotacion_clp", "Rotación (proxy de costos)", "Construction", "menor", "clp"),
)

CONSTRUCTION_DIMENSIONS = (
    Dimension("retorno_esperado", "Retorno esperado", "Construction", "mayor"),
    Dimension("volatilidad_ex_ante", "Volatilidad ex-ante", "Risk", "menor"),
    Dimension("retorno_escenario_adverso", "Retorno en escenario adverso", "Scenario", "mayor"),
    Dimension("prob_exito", "Probabilidad de lograr la meta", "ClientGoal", "mayor"),
    Dimension("hhi", "Concentración (HHI)", "Diversification", "menor", "num"),
    Dimension("max_contribucion_riesgo", "Mayor aporte al riesgo de un fondo", "Diversification", "menor"),
)

_EPS = {"pct": 1e-4, "num": 1e-4, "clp": 1.0}


def _fmt(d: Dimension, v: float) -> str:
    if d.formato == "clp":
        return f"{v:,.0f} CLP".replace(",", ".")
    if d.formato == "num":
        return f"{v:.3f}"
    return f"{v:.2%}"


def detect_tradeoffs(alternatives: dict[str, dict], reference: str, dimensions,
                     threshold: float | None = None, scenarios: str = "",
                     sensitivity: dict | None = None) -> dict:
    ref = alternatives[reference]
    found = []
    for key, alt in alternatives.items():
        if key == reference:
            continue
        effects = []
        for d in dimensions:
            a, b = ref.get(d.key), alt.get(d.key)
            if a is None or b is None:
                continue
            delta = b - a
            if abs(delta) <= _EPS[d.formato]:
                continue
            if threshold is not None and d.formato != "clp" and abs(delta) < threshold:
                continue
            better = delta < 0 if d.mejor == "menor" else delta > 0
            effects.append({"dimension": d.nombre, "motor": d.motor, "referencia": a, "alternativa": b,
                            "cambio": delta, "mejora": better,
                            "texto": f"{d.nombre}: {_fmt(d, a)} → {_fmt(d, b)}"})
        mejora = [e for e in effects if e["mejora"]]
        empeora = [e for e in effects if not e["mejora"]]
        if not (mejora and empeora):
            continue
        dims = sorted({e["dimension"] for e in mejora + empeora})
        found.append({
            "alternativa": key, "referencia": reference,
            # Los nueve pasos de DF 4.3, en orden
            "conflicto": (f"{alt.get('nombre', key)} frente a {ref.get('nombre', reference)}: mejora "
                          f"{', '.join(e['dimension'].lower() for e in mejora)} a cambio de "
                          f"{', '.join(e['dimension'].lower() for e in empeora)}."),
            "dimensiones": dims,
            "cuantificacion": effects,
            "mejora": [e["texto"] for e in mejora],
            "empeora": [e["texto"] for e in empeora],
            "magnitud": {e["dimension"]: e["cambio"] for e in effects},
            "escenarios": scenarios,
            "sensibilidad": sensitivity or {},
            "alternativas_disponibles": list(alternatives),
        })
    return {
        "tradeoffs": found,
        "umbral": threshold,
        "nota": ("Umbral de materialidad sin fijar (DF 8.3 OQ4): se muestran todos los conflictos."
                 if threshold is None else f"Se muestran conflictos con cambio ≥ {threshold}."),
        "regla": "El sistema muestra el conflicto; no pondera dimensiones ni lo resuelve (DF 4.3).",
    }
