"""
Contrato base de motor (M25) y registro de motores disponibles.

Cada motor:
  - declara qué datos CRITICAL necesita (para el Completeness Gate, M08)
  - nunca calcula sobre datos insuficientes — devuelve un EngineResult
    con `insufficient_data=True` en vez de un número con falsa confianza
    (QM Principio 8)
  - no contiene lógica de explicación (eso es M15) ni de enrutamiento
    (eso es M02/Orchestrator)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class EngineResult:
    engine_name: str
    values: dict[str, Any] = field(default_factory=dict)
    insufficient_data: bool = False
    insufficient_data_reason: str | None = None


class Engine(Protocol):
    name: str
    required_critical_data: list[str]

    def run(self, case: "Any") -> EngineResult:
        ...


class EngineRegistry(dict):
    """dict[str, Engine] con un helper de registro explícito."""

    def register(self, engine: Engine) -> None:
        self[engine.name] = engine
