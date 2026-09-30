"""
Completeness Gate (M08).

Principio rector (QM Principio 8 / ESFS-01 Parte XIV): si no hay
información suficiente, el sistema declara explícitamente
"Información insuficiente para producir una estimación confiable" —
nunca calcula sobre datos pobres y lo presenta con la misma confianza
visual que un resultado robusto.

Este módulo no decide SI un dato es CRITICAL — esa clasificación vive
en el Data Dictionary / Parte 9.3-9.4 de ESFS-01 y depende del motor.
Lo que este módulo hace es aplicar esa clasificación ya declarada y
producir un CompletenessReport auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompletenessReport:
    """
    Resultado de la verificación de completitud para un DecisionCase.

    `missing` lista, por dato, qué falta y por qué es bloqueante —
    nunca se omite en silencio: un dato faltante que no bloquea el
    caso igual debe aparecer aquí, marcado como no-crítico.
    """

    required: list[str]
    available: list[str]
    missing: list[str] = field(default_factory=list)
    non_critical_gaps: list[str] = field(default_factory=list)

    @property
    def is_sufficient(self) -> bool:
        return len(self.missing) == 0

    @classmethod
    def evaluate(
        cls,
        required_critical: list[str],
        required_optional: list[str],
        available: list[str],
    ) -> "CompletenessReport":
        available_set = set(available)
        missing = [d for d in required_critical if d not in available_set]
        non_critical_gaps = [d for d in required_optional if d not in available_set]
        return cls(
            required=required_critical + required_optional,
            available=available,
            missing=missing,
            non_critical_gaps=non_critical_gaps,
        )
