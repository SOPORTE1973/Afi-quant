# AFI Quant

Acompañamiento cuantitativo al ejecutivo de AfiTrading, bajo marcos teóricos modernos que mejoren y transparenten los cambios en las carteras.

Implementa el **ESFS-01 (AFI Expert System Functional Architecture)**: un Orchestrator que nunca calcula, motores cuantitativos desacoplados, una capa de explicación determinística (nunca caja negra), y registros de gobernanza versionados.

## Estado actual

Arranque de **Fase 2 — Core Functional Architecture** (ver `ESFS-01` Parte 25), adelantado respecto al roadmap porque el equipo decidió empezar el software mientras se cierra la Fase 0 (datos) en paralelo. Lo que hay hoy:

| Módulo | Estado |
|---|---|
| M02 Orchestrator (`orchestrator/`) | Esqueleto funcional — arma el `AnalysisPlan`, enruta el `DecisionCase` por estados, nunca calcula (DF 2.2) |
| M08 Completeness Gate (`completeness/`) | Funcional — bloquea un caso y declara qué falta, en vez de calcular sobre datos pobres |
| M22 Parameter Registry (`registries/parameter_registry.py`) | **Propuesta cargada** — 6 categorías + 17 parámetros declarados (15 sin valor, 2 confirmados en la fuente), aprobada por el usuario 2026-09-30, pendiente de contrastar contra ESFS-01 |
| M23 Model Governance Registry (`registries/model_governance_registry.py`) | **Completo** — 44 modelos, clasificación CORE/ADVANCED/RESEARCH/REJECTED, responsable institucional donde la fuente lo da, 6 items marcados OPEN donde no |
| M15 Explanation Layer (`explanation/`) | Motor de reglas determinístico, sin reglas cargadas todavía |
| M18 Decision History (`decision_history/`) | Store en memoria — la persistencia real depende de lo que resuelva el audit de infraestructura |
| Motor Benchmark (`engines/benchmark.py`) | **Cálculo real** — TWR geométrico y retorno directo sobre `AdjustedSeries` (deduplicada), corre sobre datos reales del conector `MCP_Afitrading` cuando `case.input_data["benchmark_index_series"]` está presente. La certificación de elegibilidad (8 dimensiones, ESFS-01) NO está implementada — el resultado se marca explícitamente "elegibilidad no verificada" |
| Motor Performance (`engines/performance.py`) | **MVP a nivel fondo** — TWR del período y trailing 1a/3a, CAGR, Excess Return (bloqueado hasta que el benchmark esté certificado). Validado contra las rentabilidades que publica el conector. Carteras de cliente con flujos siguen dependiendo de Fase 1 |
| Motor Risk (`engines/risk.py`) | **MVP a nivel fondo** — volatilidad (retornos mensuales, mín. 36), Max Drawdown con recuperación, VaR/ES históricos 95%/99% a 1 mes. Downside Deviation espera el MAR del Parameter Registry; TE/Beta esperan benchmark certificado |
| Pipeline (`pipeline.py`, `demo.py`) | **MVP de punta a punta** — Intake → Plan → Completeness Gate → Benchmark/Performance/Risk → Explanation Layer (`explanation/fund_review_rules.py`), sobre datos reales en `data/fixtures/` |
| Capa de series (`engines/series.py`) | `dedupe_snapshots` (colapsa snapshots intradía del conector a un punto por fecha), `geometric_chain_return`/`total_return` (fórmula CORE de TWR). Validada con datos reales de ETF Singular IPSA (`data/benchmark_fixtures/`) |
| Taxonomía de asset classes (`data/asset_taxonomy.py`) | Snapshot real tomado del conector `MCP_Afitrading`, no inventado — pendiente confirmar ruta de integración en vivo con TI |

Lo que **no** existe todavía: persistencia real, autenticación, Performance/Risk sobre carteras de cliente con flujos (dependen de datos de cartera vía TI), Diagnosis/Recommendation (M11-M14), el Benchmark Eligibility Framework completo (8 dimensiones), y la confirmación final de las seis categorías del Parameter Registry.

## Por qué los motores declaran lo que no calculan

No es un placeholder olvidado: es la postura correcta según el Principio 8 de la metodología (AFI Quantitative Methodology). Un motor sin datos CRITICAL confirmados **debe** declarar `insufficient_data`, nunca inventar un número. Los motores reales se implementan en Fase 3.1 una vez que el audit de infraestructura de datos (Fase 0) confirme qué existe.

## Desarrollo

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python -m afi_quant.demo      # caso de punta a punta con datos reales
uvicorn afi_quant.api.main:app --reload
```

## Documentos fuente

La arquitectura completa vive en los documentos del proyecto (ESFS-01, AFI Quantitative Methodology, AFI Decision Framework, AFI Methodology Volúmenes I-III). Este código es una implementación de esos documentos — cuando el código y la fuente discrepen, la fuente manda y el código se corrige, no al revés.
