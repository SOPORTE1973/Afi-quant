"""
Decision Case y Orchestrator (M02).

DF 2.2 (Decision Framework): el Orchestrator NUNCA contiene lógica de
cálculo. Solo arma el AnalysisPlan (qué motores correr, en qué orden,
según el tipo de caso) y enruta el caso a través de los estados de
`states.py`. Todo cálculo vive en los motores (`engines/`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from afi_quant.completeness.gate import CompletenessReport
from afi_quant.orchestrator.states import DecisionCaseState, RecommendationLevel


@dataclass
class AnalysisPlan:
    """Qué motores debe correr el caso y por qué, versionado."""

    engines: list[str]
    reason: str
    version: int = 1


@dataclass
class DecisionCase:
    """
    Unidad central de trabajo del sistema: una pregunta institucional
    que recorre Intake -> Plan -> Data Gate -> Analysis -> Diagnosis ->
    Trade-off -> Alternatives -> Recommendation -> Explanation -> Decision.

    No se persiste aquí (ver decision_history/store.py) — este es el
    objeto en memoria que el Orchestrator mueve de estado en estado.
    """

    case_id: str = field(default_factory=lambda: str(uuid4()))
    trigger: str = ""                      # qué disparó el caso (revisión periódica, alerta, etc.)
    client_ref: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: DecisionCaseState = DecisionCaseState.INTAKE
    plan: AnalysisPlan | None = None
    completeness_report: CompletenessReport | None = None
    engine_results: dict[str, Any] = field(default_factory=dict)
    recommendation_level: RecommendationLevel | None = None
    explanation: str | None = None
    history: list[str] = field(default_factory=list)

    def _log(self, message: str) -> None:
        self.history.append(f"[{datetime.now(timezone.utc).isoformat()}] {message}")


class Orchestrator:
    """
    M02 — enruta un DecisionCase a través del pipeline.

    Deliberadamente no importa ningún motor cuantitativo por nombre:
    recibe un registro de motores disponibles (engine_registry) y
    decide solo a cuáles llamar según el AnalysisPlan. Esto es lo que
    impide que la lógica de cálculo se filtre aquí (DF 2.2).
    """

    def __init__(self, engine_registry: dict[str, Any]):
        self._engines = engine_registry

    def build_plan(self, case: DecisionCase, engines: list[str], reason: str) -> None:
        unknown = [e for e in engines if e not in self._engines]
        if unknown:
            raise ValueError(
                f"AnalysisPlan referencia motores no registrados: {unknown}. "
                "Un motor debe existir en el engine_registry antes de poder planearse."
            )
        case.plan = AnalysisPlan(engines=engines, reason=reason)
        case.state = DecisionCaseState.PLANNED
        case._log(f"AnalysisPlan armado: {engines} ({reason})")

    def apply_completeness_gate(self, case: DecisionCase, report: CompletenessReport) -> None:
        case.completeness_report = report
        if not report.is_sufficient:
            case.state = DecisionCaseState.DATA_BLOCKED
            case._log(
                "Completeness Gate bloqueó el caso — "
                f"faltantes declarados: {report.missing}"
            )
            return
        case.state = DecisionCaseState.ANALYZING
        case._log("Completeness Gate aprobó el caso — todos los datos CRITICAL disponibles")

    def run_engines(self, case: DecisionCase) -> None:
        if case.state != DecisionCaseState.ANALYZING:
            raise RuntimeError(
                f"No se pueden correr motores en estado '{case.state.value}'. "
                "El caso debe estar en ANALYZING (Completeness Gate ya aprobado)."
            )
        if case.plan is None:
            raise RuntimeError("El caso no tiene AnalysisPlan.")

        for engine_name in case.plan.engines:
            engine = self._engines[engine_name]
            case.engine_results[engine_name] = engine.run(case)
            case._log(f"Motor '{engine_name}' ejecutado")
