# AFI Quant

Acompañamiento cuantitativo al ejecutivo de AfiTrading, bajo marcos teóricos modernos que mejoren y transparenten los cambios en las carteras.

Implementa el **ESFS-01 (AFI Expert System Functional Architecture)**: un Orchestrator que nunca calcula, motores cuantitativos desacoplados, una capa de explicación determinística (nunca caja negra), y registros de gobernanza versionados.

## Estado actual

Arranque de **Fase 2 — Core Functional Architecture** (ver `ESFS-01` Parte 25), adelantado respecto al roadmap porque el equipo decidió empezar el software mientras se cierra la Fase 0 (datos) en paralelo. Lo que hay hoy:

| Módulo | Estado |
|---|---|
| M02 Orchestrator (`orchestrator/`) | Esqueleto funcional — arma el `AnalysisPlan`, enruta el `DecisionCase` por estados, nunca calcula (DF 2.2) |
| M08 Completeness Gate (`completeness/`) | Funcional — bloquea un caso y declara qué falta, en vez de calcular sobre datos pobres |
| M22 Parameter Registry (`registries/parameter_registry.py`) | Esquema listo; **vacío a propósito** — las seis categorías de gobernanza exactas aún no están confirmadas contra la fuente |
| M23 Model Governance Registry (`registries/model_governance_registry.py`) | **Completo** — 44 modelos, clasificación CORE/ADVANCED/RESEARCH/REJECTED, responsable institucional donde la fuente lo da, 6 items marcados OPEN donde no |
| M15 Explanation Layer (`explanation/`) | Motor de reglas determinístico, sin reglas cargadas todavía |
| M18 Decision History (`decision_history/`) | Store en memoria — la persistencia real depende de lo que resuelva el audit de infraestructura |
| Motores Performance / Risk / Benchmark (`engines/`) | **Stubs.** Declaran `insufficient_data` siempre — correcto hasta que exista Fase 1 (datos reales) |
| Taxonomía de asset classes (`data/asset_taxonomy.py`) | Snapshot real tomado del conector `MCP_Afitrading`, no inventado — pendiente confirmar ruta de integración en vivo con TI |

Lo que **no** existe todavía: persistencia real, autenticación, ningún motor con cálculo real, y las seis categorías del Parameter Registry.

## Por qué los motores no calculan nada todavía

No es un placeholder olvidado: es la postura correcta según el Principio 8 de la metodología (AFI Quantitative Methodology). Un motor sin datos CRITICAL confirmados **debe** declarar `insufficient_data`, nunca inventar un número. Los motores reales se implementan en Fase 3.1 una vez que el audit de infraestructura de datos (Fase 0) confirme qué existe.

## Desarrollo

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
uvicorn afi_quant.api.main:app --reload
```

## Documentos fuente

La arquitectura completa vive en los documentos del proyecto (ESFS-01, AFI Quantitative Methodology, AFI Decision Framework, AFI Methodology Volúmenes I-III). Este código es una implementación de esos documentos — cuando el código y la fuente discrepen, la fuente manda y el código se corrige, no al revés.
