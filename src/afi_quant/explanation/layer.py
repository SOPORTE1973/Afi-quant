"""
Explanation Layer (M15).

Principio 3 (AFI Quantitative Methodology): la explicación es
determinística — regla fija -> plantilla parametrizada. Reproducible
exactamente ante los mismos inputs. Explícitamente REJECTED en el
Model Governance Registry: SHAP/LIME como núcleo, y Auto-Commentary
tipo LLM (ambos violan este principio).

Este módulo NUNCA debe llamar a un modelo generativo para producir la
explicación en sí. Un LLM puede ayudar a redactar la plantilla en
tiempo de diseño (como aquí), pero el texto que ve el Wealth Manager
en producción sale de reglas fijas, no de una generación libre.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ExplanationRule:
    """Una regla fija: si `condition` es verdadera, se aplica `template`."""

    name: str
    condition: Callable[[dict], bool]
    template: str  # usa str.format() con las keys del contexto

    def applies(self, context: dict) -> bool:
        return self.condition(context)

    def render(self, context: dict) -> str:
        return self.template.format(**context)


class ExplanationLayer:
    """
    Evalúa reglas en orden y concatena las que aplican. Determinística:
    mismo contexto -> mismo texto, siempre. Sin excepciones.
    """

    def __init__(self, rules: list[ExplanationRule] | None = None):
        self._rules = rules or []

    def register(self, rule: ExplanationRule) -> None:
        self._rules.append(rule)

    def explain_parts(self, context: dict) -> list[str]:
        return [rule.render(context) for rule in self._rules if rule.applies(context)]

    def explain(self, context: dict, separator: str = " ") -> str:
        parts = self.explain_parts(context)
        if not parts:
            return "No hay reglas de explicación aplicables a este contexto."
        return separator.join(parts)
