"""
Decision History (M18).

Registro append-only de Decision Cases cerrados. Es lo que Fase 6
(Tracking & Learning) usa después para comparar expectativa vs.
resultado — nunca se edita un caso ya cerrado, solo se agregan nuevos.

Esta implementación es en memoria (para desarrollo/tests). El
almacenamiento real (base de datos) se decide en Fase 1/2 según lo
que resuelva el audit de infraestructura — no se asume una tecnología
aquí.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from afi_quant.orchestrator.decision_case import DecisionCase
from afi_quant.orchestrator.states import DecisionCaseState


class DecisionHistoryError(Exception):
    pass


@dataclass
class DecisionHistoryStore:
    _records: dict[str, DecisionCase] = field(default_factory=dict)

    def close(self, case: DecisionCase) -> None:
        if case.state == DecisionCaseState.CLOSED:
            raise DecisionHistoryError(f"Caso {case.case_id} ya está cerrado.")
        case.state = DecisionCaseState.CLOSED
        case.history.append(f"[{datetime.now(timezone.utc).isoformat()}] Caso cerrado y archivado")
        self._records[case.case_id] = case

    def get(self, case_id: str) -> DecisionCase | None:
        return self._records.get(case_id)

    def all(self) -> list[DecisionCase]:
        return list(self._records.values())
