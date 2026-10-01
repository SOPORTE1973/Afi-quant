"""
Recommendation Layer (M14; DF v1.1 Parte 2.3 y 4.4).

Trabaja solo sobre lo que los motores ya calcularon y responde una pregunta:
¿alcanza la evidencia para una recomendación analítica de Nivel 3? No
calcula métricas, no completa vacíos y no asigna gobernanza (DF 3.1): no
dice si la decisión es del WM, de un Senior o del Investment Committee.

  Nivel 1  sin alternativas evaluables: lo declara con la frase del DF 4.2.
  Nivel 2  hay alternativas, pero falta evidencia (datos que bloquean, ninguna
           alternativa cumple el criterio, o algún elemento obligatorio vacío).
  Nivel 3  todo lo anterior se cumple y los nueve elementos tienen contenido.

Cada nivel declara por qué no alcanzó uno mayor (ESFS 15.2).
"""

from __future__ import annotations

LEVEL3_ELEMENTS = ("criterios", "inputs", "resultados", "supuestos", "restricciones",
                   "escenarios", "sensibilidad", "datos_faltantes", "limitaciones")

NO_ALTERNATIVES = "No existen alternativas cuantitativamente evaluables con la información disponible."


def recommendation_layer(*, alternatives: dict[str, dict], candidates: list[str], criterion: str,
                         choose, elements: dict, blocking_missing: list[str] | None = None) -> dict:
    """
    `candidates`: alternativas que cumplen el criterio declarado (las filtra el
    flujo, que es quien conoce la regla de negocio). `choose`: función que
    elige entre candidatas según el mismo criterio.
    """
    out = {"nivel": None, "recomendada": None, "criterio": criterion, "recomendacion": None,
           "motivo_nivel": None, "elementos_nivel_3": {}}
    if not alternatives:
        out.update(nivel=1, motivo_nivel=NO_ALTERNATIVES, recomendacion=NO_ALTERNATIVES)
        return out
    if blocking_missing:
        out.update(nivel=2, motivo_nivel=(
            "Nivel 2: se muestran las alternativas, pero faltan datos que bloquean una "
            f"recomendación: {', '.join(blocking_missing)}."))
        return out
    if not candidates:
        out.update(nivel=2, motivo_nivel=(
            f"Nivel 2: ninguna alternativa cumple el criterio ({criterion}); el WM decide entre "
            "las alternativas mostradas sin recomendación analítica."))
        return out
    empty = [e for e in LEVEL3_ELEMENTS if not elements.get(e)]
    if empty:
        out.update(nivel=2, motivo_nivel=(
            f"Nivel 2: la recomendación quedaría sin {', '.join(empty)}, y el Nivel 3 exige los "
            "nueve elementos (DF 4.4)."))
        return out
    chosen = choose(candidates)
    name = alternatives[chosen].get("nombre", chosen)
    out.update(
        nivel=3, recomendada=chosen, elementos_nivel_3={e: elements[e] for e in LEVEL3_ELEMENTS},
        motivo_nivel="Nivel 3 es el techo: el sistema no ejecuta (Nivel 4 no existe) ni asigna quién decide.",
        recomendacion=(f"Bajo el criterio de {criterion} y los supuestos declarados, la alternativa "
                       f"{chosen} ({name}) presenta el resultado más consistente con los objetivos "
                       "analizados."),
    )
    return out
