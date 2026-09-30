"""
API mínima — expone el Orchestrator para crear y consultar Decision
Cases. Deliberadamente delgada: toda la lógica vive en
orchestrator/engines/registries, no aquí.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from afi_quant.decision_history.store import DecisionHistoryStore
from afi_quant.engines.base import EngineRegistry
from afi_quant.engines.benchmark import BenchmarkEngine
from afi_quant.engines.performance import PerformanceEngine
from afi_quant.engines.risk import RiskEngine
from afi_quant.orchestrator.decision_case import DecisionCase, Orchestrator
from afi_quant.registries.model_governance_registry import (
    MODEL_GOVERNANCE_REGISTRY,
    open_items,
)

app = FastAPI(
    title="AFI Quant",
    description="Acompañamiento cuantitativo al ejecutivo — implementación de ESFS-01.",
    version="0.1.0",
)

_engine_registry = EngineRegistry()
_engine_registry.register(PerformanceEngine())
_engine_registry.register(RiskEngine())
_engine_registry.register(BenchmarkEngine())

_orchestrator = Orchestrator(_engine_registry)
_history = DecisionHistoryStore()
_cases: dict[str, DecisionCase] = {}


class CreateCaseRequest(BaseModel):
    trigger: str
    client_ref: str | None = None
    engines: list[str]
    reason: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/cases")
def create_case(req: CreateCaseRequest) -> dict:
    case = DecisionCase(trigger=req.trigger, client_ref=req.client_ref)
    try:
        _orchestrator.build_plan(case, engines=req.engines, reason=req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _cases[case.case_id] = case
    return {"case_id": case.case_id, "state": case.state.value}


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    case = _cases.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return {
        "case_id": case.case_id,
        "trigger": case.trigger,
        "state": case.state.value,
        "engine_results": {
            name: {
                "insufficient_data": r.insufficient_data,
                "reason": r.insufficient_data_reason,
                "values": r.values,
            }
            for name, r in case.engine_results.items()
        },
        "history": case.history,
    }


@app.get("/registries/model-governance")
def list_model_governance() -> dict:
    return {
        "total": len(MODEL_GOVERNANCE_REGISTRY),
        "open_items": [
            {"motor": m.motor, "modelo": m.modelo, "clasificacion": m.clasificacion.value}
            for m in open_items()
        ],
        "models": [
            {
                "motor": m.motor,
                "modelo": m.modelo,
                "clasificacion": m.clasificacion.value,
                "responsable_institucional": m.responsable_institucional,
                "requires_periodic_validation": m.requires_periodic_validation,
            }
            for m in MODEL_GOVERNANCE_REGISTRY
        ],
    }
