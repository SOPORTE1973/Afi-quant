"""
Parameter Registry (M22).

ESFS-01 exige un registro con "las seis categorías de gobernanza y
todos los parámetros declarados, aunque sin valor" (Fase 0, entregable 2).

ESTADO DE ESTE ARCHIVO: el esquema (abajo) está listo para recibir
parámetros. Las seis categorías institucionales de gobernanza en sí
—sus nombres exactos— no se fijan en este commit: ese detalle vive en
ESFS-01 y debe confirmarse contra el documento fuente antes de cargar
parámetros reales. Cargar categorías inventadas aquí violaría el
mismo principio que gobierna todo este proyecto (nunca rellenar un
vacío de la fuente con un supuesto). Por eso el registro arranca vacío
y tipado, no con seis categorías adivinadas.

Cada Parameter tiene versión, vigencia, quién propone y quién aprueba
— eso sí está confirmado (ESFS-01 Parte 25, Fase 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Parameter:
    name: str
    category: str  # ver nota de estado arriba — pendiente de confirmar contra ESFS-01
    description: str
    unit: str | None = None
    value: float | str | None = None       # None = declarado, sin valor todavía
    version: int = 1
    effective_from: date | None = None
    proposed_by: str | None = None
    approved_by: str | None = None
    source: str | None = None


@dataclass
class ParameterRegistry:
    parameters: list[Parameter] = field(default_factory=list)

    def declare(self, parameter: Parameter) -> None:
        """Registra un parámetro sin valor — lo llena el Comité después."""
        self.parameters.append(parameter)

    def undeclared(self) -> list[Parameter]:
        return [p for p in self.parameters if p.value is None]

    def by_category(self, category: str) -> list[Parameter]:
        return [p for p in self.parameters if p.category == category]


# Instancia compartida — arranca vacía a propósito (ver docstring del módulo).
PARAMETER_REGISTRY = ParameterRegistry()
