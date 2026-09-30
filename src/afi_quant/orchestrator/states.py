"""
Estados del Decision Case (Orchestrator, módulo M02).

El pipeline sigue el orden de módulos descrito en ESFS-01 Parte 25
(Fase 2 — Core Functional Architecture, Fase 4 — Decision Layer):

    M01 Decision Intake
      -> M02 Orchestrator (arma el AnalysisPlan)
      -> M08 Completeness Gate (declara qué falta, nunca calcula en silencio)
      -> [motores cuantitativos según el AnalysisPlan]
      -> M11 Diagnostic Synthesis
      -> M12 Trade-off
      -> M13 Alternatives (incluye cardinalidad cero)
      -> M14 Recommendation Layer
      -> M15 Explanation Layer (determinística, reglas + plantillas)
      -> M18 Decision History (registro append-only)

Principio rector (Decision Framework, DF 2.2): el Orchestrator NUNCA
contiene lógica de cálculo. Solo enruta, según el AnalysisPlan, hacia
los motores correspondientes.

NOTA DE FUENTE: los nombres exactos de los estados internos entre
Analysis y Diagnosis (más allá del pipeline de módulos ya confirmado)
no están fijados en este commit — el detalle línea por línea de la
máquina de estados vive en ESFS-01 Parte 19 y debe confirmarse contra
el documento fuente antes de cerrar esta enumeración. Lo que sigue es
el esqueleto mínimo defendible con lo ya verificado; no se inventan
transiciones no confirmadas.
"""

from __future__ import annotations

from enum import Enum


class DecisionCaseState(str, Enum):
    """Estado de un Decision Case a lo largo del pipeline del Orchestrator."""

    INTAKE = "intake"                    # M01 — se recibió la solicitud / disparador
    PLANNED = "planned"                  # M02 — AnalysisPlan armado (qué motores correr)
    DATA_BLOCKED = "data_blocked"        # M08 — Completeness Gate detuvo el caso, con CompletenessReport
    ANALYZING = "analyzing"              # motores cuantitativos en ejecución
    DIAGNOSED = "diagnosed"              # M11 — Diagnostic Synthesis completa
    TRADE_OFF = "trade_off"              # M12 — trade-offs entre hallazgos
    ALTERNATIVES = "alternatives"        # M13 — alternativas generadas (puede ser cardinalidad cero)
    RECOMMENDED = "recommended"          # M14 — recomendación producida
    EXPLAINED = "explained"              # M15 — explicación determinística adjunta
    DECIDED = "decided"                  # el Wealth Manager registró una decisión (con o sin override)
    CLOSED = "closed"                    # M18 — caso archivado en Decision History


class RecommendationLevel(int, Enum):
    """
    Niveles de profundidad de una recomendación (ESFS-01 Parte 24 / MVP Definition).

    El sistema nunca fuerza un nivel que no puede sostener con evidencia —
    declara el bloqueo en vez de rellenarlo. Ejemplo confirmado en la
    fuente: un caso de revisión periódica puede alcanzar Nivel 3; un caso
    de cambio de fondo sin evidencia de proceso/equipo/ODD se detiene en
    Nivel 2, explicando por qué.
    """

    NIVEL_0 = 0  # sin base suficiente para diagnosticar
    NIVEL_1 = 1  # diagnóstico sin alternativas sostenibles
    NIVEL_2 = 2  # diagnóstico + alternativas, sin recomendación cerrada
    NIVEL_3 = 3  # recomendación completa con los nueve elementos del trade-off
