# ESFS-01 — AFI EXPERT SYSTEM FUNCTIONAL ARCHITECTURE

**Versión:** 1.0 (funcional, no técnica)
**Estado:** READY FOR DATA ARCHITECTURE / READY FOR TECHNICAL ARCHITECTURE — CON OPEN ISSUES REGISTRADOS
**Autoridad de origen:** AFI Decision Framework v1.1 (congelado) + AFI Quantitative Methodology v1.0 (preservado) + Volúmenes I, II, III, III-B

**Convención de trazabilidad usada en todo el documento:**

| Marca | Significado |
|---|---|
| `[DF x.y]` | AFI Decision Framework v1.1, parte x.y |
| `[QM P]` | AFI Quantitative Methodology v1.0, Parte P |
| `[V1 Pn]` | Volumen I, Principio n |
| `[V2 Bn]` | Volumen II, Bloque n |
| `[V3]` / `[V3B]` | Volumen III / III-B |
| `DERIVADO` | Consecuencia funcional deducida de una regla fuente explícita, sin agregar metodología |
| `OPEN ISSUE` | Vacío que no puede cerrarse con los documentos fuente; registrado en la Parte 27 |

**Regla de escritura aplicada:** ninguna cifra, umbral, peso, motor, regla de gobernanza o fuente de datos aparece en este documento si no está en los documentos fuente. Donde falta, aparece un OPEN ISSUE, nunca un supuesto.

---

## 1. Executive Summary

ESFS-01 traduce el AFI Decision Framework v1.1 y la AFI Quantitative Methodology v1.0 en una arquitectura funcional implementable: qué módulos existen, qué hace cada uno, qué datos necesita cada uno, en qué orden deben construirse y qué falta decidir antes de construirlos.

El sistema es un **Decision Support System para Wealth Management**. No es un stock picker, no ejecuta órdenes, no incorpora LLM en el producto, no tiene Nivel 4 de autonomía y no etiqueta una inversión como buena o mala `[DF 4.4]` `[QM 0]`.

**Los cinco hallazgos estructurales de esta traducción:**

1. **El sistema es una máquina de estados sobre una decisión, no un pipeline de cálculo.** La unidad de vida del sistema es el *Decision Case*: nace de una pregunta, recorre datos → motores → diagnóstico → trade-offs → alternativas → nivel de recomendación, se detiene en el Analytical Output y queda registrada en History `[DF 4.1]`. Todo módulo de este documento se define por lo que aporta a un Decision Case.

2. **La capa que hoy no existe y sin la cual nada se puede construir es el registro de requerimientos de datos por métrica.** Data Completeness `[DF 6.1]` no es implementable como regla genérica: necesita, por cada métrica de cada motor, qué inputs consume, con qué mínimo histórico y qué comportamiento (BLOCK / WARNING / CONTINUE) corresponde si el input falta. La Parte 9 construye ese registro; la Parte 27 declara dónde la metodología no fija el mínimo.

3. **Tres inconsistencias internas de los documentos fuente afectan directamente la implementación** y se registran sin resolverse: el conteo de los "ocho elementos" de una recomendación de Nivel 3 (que enumera nueve) `[DF 2.3, 4.4]`, las "seis dimensiones" de un cliente que el Monitoring Engine no puede colapsar (nunca enumeradas) `[DF 2.1]`, y el estatus del "Motor de Rebalanceo" `[QM XIII]` frente a la lista canónica de diez motores `[DF 2.1]`.

4. **Existe un módulo funcional obligatorio que no es ninguno de los diez motores:** la Due Diligence de gestores y la Approved List `[V2 B1-B9]`, que el Decision Framework invoca como motor núcleo del caso "Nueva inversión" y del flujo de deterioro `[DF 7.1, 7.3]` y que gobierna D3/D4/D5/D11/D14 con poder de veto operacional `[V2 B6]`. Su ubicación arquitectónica no está definida en las fuentes: OPEN ISSUE ESFS-04.

5. **El MVP puede demostrar el flujo completo hasta Nivel 2, pero no hasta Nivel 3 en el caso de cambio de fondo**, porque la regla de negocio de D3 exige evidencia de proceso, equipo y ODD que el MVP no tendrá `[QM XVIII D3]`. Esa limitación no es un defecto del MVP: es la metodología funcionando. La Parte 24 lo especifica como bloqueo explícito, no como recorte silencioso.

**Qué habilita este documento:** un data engineer puede empezar a construir el modelo de datos (Partes 8, 9, 29); un desarrollador puede empezar por el Decision Case, el Data Completeness Gate y los tres motores de Fase 1 (Partes 10, 11, 24, 25); un Wealth Manager puede validar si los flujos corresponden a su trabajo real (Partes 17, 18).

**Qué NO habilita:** decisiones institucionales de AFI que el sistema no puede anticipar — umbrales de materialidad, reglas de escalamiento, activación de Black-Litterman, política ESG. Están en la Parte 27 con su responsable asignado.

---

## 2. Scope

### 2.1 — Dentro del alcance de ESFS-01

| Incluye | Referencia |
|---|---|
| Arquitectura funcional: qué módulos existen y qué hace cada uno | Objetivo A del mandato |
| Arquitectura de procesos: cómo fluye una decisión | `[DF 4.1]` |
| Arquitectura de información funcional: qué datos necesita cada módulo | `[QM XVI, XVII]` |
| Mapeo de los diez motores a especificación funcional | `[QM XXIV]` |
| Data Requirement Matrix por módulo / motor / métrica | Objetivo central del mandato |
| Estados, errores, trazabilidad y auditabilidad funcional | `[QM XXI]` |
| MVP, roadmap, dependencias y prioridades de adquisición de datos | Partes 24-29 |
| Registro explícito de vacíos | Parte 27 |

### 2.2 — Fuera del alcance de ESFS-01

- Arquitectura técnica (stack, servicios, bases de datos, APIs, latencias, despliegue). ESFS-01 es funcional; la arquitectura técnica es un documento posterior.
- Modelos de datos físicos. Se definen entidades y atributos funcionales, no esquemas.
- Cualquier metodología cuantitativa nueva. Cero modelos nuevos `[DF 8.2]`.
- Ejecución de órdenes, trading, derivados, CRM, stock picking, LLM como componente del producto `[QM 0]`.
- Nivel 4 de autonomía. No existe en ninguna versión del sistema `[DF 4.4]`.
- Reglas internas de escalamiento institucional. Es una decisión de AFI, no una salida del sistema `[DF 3.1]`; el sistema solo expone la interfaz (Parte 16.4).
- Explicabilidad vía SHAP/LIME y Auto-Commentary. Rechazados, y el rechazo es firme, no reevaluable en ESFS `[QM XIX]` `[QM III.0 Rev 1-2]`.

### 2.3 — Unidad de análisis del sistema

El sistema opera sobre cinco unidades de análisis, determinadas por el Orchestrator en su pregunta 2 `[DF 2.2]`:

| Unidad | Descripción | Ejemplo de pregunta |
|---|---|---|
| Cliente | Patrimonio consolidado, multi-portafolio, multi-moneda | "¿Está este cliente en riesgo de no alcanzar su meta?" |
| Portafolio | Una cuenta o mandato específico | "¿Hay que rebalancear esta cuenta?" |
| Vehículo / Fondo | Un instrumento individual | "¿Por qué cayó este fondo?" |
| Gestor | La organización detrás de uno o más vehículos | "¿Existe deterioro en este gestor?" |
| Book of business | El conjunto de clientes del WM | "¿En qué cuentas debo actuar hoy?" |

Ninguna métrica se calcula sin que la unidad de análisis esté declarada: la misma serie de retornos significa cosas distintas a nivel de vehículo (habilidad del gestor, TWR) y a nivel de cliente (experiencia del cliente, MWR) `[QM IV]`. **DERIVADO:** la unidad de análisis es un campo obligatorio de todo resultado de motor y de todo registro de auditoría.

---

## 3. Architectural Principles

Los diez principios cuantitativos `[QM I]` y el principio central `[DF 1]` se traducen aquí a restricciones de arquitectura verificables. Cada principio se acompaña de su **test de cumplimiento**: cómo se comprueba, mirando el sistema construido, que el principio se respetó.

| # | Principio (fuente) | Restricción arquitectónica | Test de cumplimiento |
|---|---|---|---|
| AP-1 | El sistema no reemplaza el juicio del WM `[DF 1]` | Ningún módulo puede producir una acción sobre el patrimonio. El grafo de módulos termina en Analytical Output | No existe ningún camino en el sistema desde un output de motor hasta una orden, instrucción de ejecución o comunicación al cliente |
| AP-2 | Objetivos del cliente sobre benchmarks `[QM I.1]` `[V1 P1]` | Todo resultado de motor lleva trazabilidad al `IPS.id_ips`, no solo al `Portafolio.id_portafolio` `[QM I.1]` | Un resultado sin referencia de IPS es un resultado inválido |
| AP-3 | Separación cálculo/decisión `[QM I.2]` | Tres capas computacionales con responsabilidad exclusiva: Engines / Orchestrator / Recommendation Layer `[DF 2]` | El Orchestrator no contiene ninguna fórmula; la Recommendation Layer no ejecuta ningún cálculo nuevo |
| AP-4 | Explicabilidad determinística `[QM I.3, XIX]` | Explicación = regla versionada + plantilla parametrizada. Dos ejecuciones con los mismos inputs producen texto idéntico | Reproducibilidad exacta byte a byte de la explicación ante mismos inputs y misma versión de regla |
| AP-5 | No sobreingeniería `[QM I.4]` | Ningún indicador entra al sistema sin una decisión de la Decision Library que habilite | Todo input de la Parte 9 responde "¿qué decisión o cálculo habilita?" |
| AP-6 | Matemática avanzada, interpretación simple `[QM I.5]` | La interfaz del WM se organiza por decisión, no por métrica disponible | La pantalla responde "¿qué necesito saber para decidir?" y no "¿qué métricas tiene el sistema?" |
| AP-7 | Diversificación económica, no nominal `[QM I.6]` | La concentración se evalúa en tres dimensiones (peso, riesgo, factor), nunca solo por número de posiciones `[QM VI]` | HHI nunca se reporta solo sobre pesos nominales |
| AP-8 | Benchmark gate antes de comparar `[QM I.7]` | Ninguna comparación relativa se computa sin estado de elegibilidad previo `[QM XII]` | No existe ruta de cálculo de Excess Return / TE / IR que no consulte primero al Benchmark Engine |
| AP-9 | Evidencia insuficiente se declara `[QM I.8, XIV]` | `insufficient_data` es un estado de sistema de primera clase, no un error genérico ni un campo vacío | Ningún output numérico se muestra con la misma confianza visual cuando se calculó sobre datos degradados |
| AP-10 | Auditabilidad total `[QM I.9, XXI]` | Un output sin su registro de auditoría asociado no es un output válido del sistema | Cada output es reconstruible: datos, versión, modelo, parámetros, regla, decisión |
| AP-11 | Convicción ex ante `[QM I.10]` `[V1 P10]` | Ninguna decisión de fondo/gestor se sostiene solo en performance reciente `[QM XVIII D3]` `[V2 B4]` | La Recommendation Layer bloquea Nivel 3 en D3/D4/D5 si no existe evidencia de proceso, equipo y ODD |
| AP-12 | Client-First y multi-horizonte `[DF 6.2]` | El sistema no obliga a completar todos los módulos; declara qué puede y qué no puede analizarse. Todo análisis relevante distingue corto, mediano y largo plazo y los muestra lado a lado sin promediarlos | Existe siempre una respuesta parcial declarada, nunca un bloqueo total por falta de un módulo no relacionado |
| AP-13 | Sin ponderación automática entre motores `[DF 4.3]` | No existe función de agregación que pondere motores entre sí, ni score único de cliente | No hay ningún campo de tipo "score global del portafolio" en ningún output |
| AP-14 | Gobernanza institucional fuera del núcleo `[DF 3.1]` | El sistema no asigna instancia de decisión para D1-D14, ni por defecto al WM | El Analytical Output no contiene ningún campo que nombre la instancia resolutoria |
| AP-15 | Simplicidad inteligible `[V1 P15]` `[QM I.4]` | Ante dos diseños equivalentes, se implementa el que el WM puede gobernar | — |

### 3.1 — Principio de diseño transversal: parámetros configurables desde el inicio

Los umbrales cuya calibración depende de evidencia operativa que aún no existe (materialidad de drift, activación de trade-off, bandas de rebalanceo, triggers de deterioro) **deben especificarse como parámetros configurables desde el primer día, no como constantes** `[DF READINESS]`. La Parte 8.6 define el Parameter Registry que lo hace posible, con las categorías de gobernanza de `[QM XV]`.

---

## 4. System Context

### 4.1 — Actores

| Actor | Rol frente al sistema | Qué puede hacer | Qué no puede hacer |
|---|---|---|---|
| **Wealth Manager** | Usuario principal; decide `[DF 1]` | Plantear preguntas, aportar contexto cualitativo, jerarquizar, aceptar/rechazar, justificar overrides `[QM XX]` | Modificar parámetros institucionales o de Comité `[QM XV]` |
| **Investment Committee** | Gobernanza de decisiones de cliente y de política | Aprobar propuestas, excepciones documentadas de benchmark y de límites de riesgo, views de BL, CMAs, SAA `[QM XV, XVIII]` | Ser asignado automáticamente por el sistema como instancia resolutoria `[DF 3.1]` |
| **Comité de Model Risk** | Methodology Governance (D15) `[DF 3.2]` | Validar, degradar o rehabilitar modelos `[QM XIV]` | Decidir sobre el patrimonio de un cliente |
| **Cliente** | Sujeto del análisis; receptor de comunicación | Aportar objetivos, restricciones, flujos esperados | Recibir comunicación autónoma del sistema — el sistema nunca comunica al cliente `[QM XX]` |
| **Equipo de datos / Operaciones** | Alimenta y reconcilia la capa de datos | Cargar, reconciliar, validar, marcar excepciones de datos | Imputar silenciosamente información faltante `[DF 6.1]` |
| **Equipo de Due Diligence (IDD / ODD)** | Evalúa gestores y vehículos `[V2 B1-B6]` | Emitir ratings IDD/ODD; ODD puede marcar un vehículo como no invertible con independencia del IDD `[V2 B6]` | — |

### 4.2 — Sistemas y fuentes externas (funcional, no técnico)

| Fuente externa | Qué provee | Referencia |
|---|---|---|
| Custodios / administradores | NAV, posiciones, flujos fechados y clasificados | `[QM XVI]` |
| Gestoras / administradoras | Factsheets, reglamento/prospecto, holdings cuando existan, capital calls, distribuciones, fees | `[QM XVI]` |
| Proveedores de índices | Series de benchmarks e índices de mercado, con metodología documentada | `[QM XVI]` |
| Proveedores de datos de mercado | FX, curvas de tasas | `[QM XVI]` |
| Reguladores | Documentación regulatoria del vehículo | `[QM XVI]` |
| Cliente (vía asesor) | Objetivos, restricciones, calendario de flujos esperados, life balance sheet | `[QM XVI]` `[V1 P2]` |
| Comité de Inversiones | CMAs, escenarios hipotéticos, views documentadas, SAA institucional, parámetros institucionales | `[QM XI, XV]` |

**DERIVADO — Regla de frontera de datos:** el sistema consume estas fuentes; no las corrige. Todo dato que falle una regla de calidad `[QM XVII]` genera una excepción visible y trazable hacia la fuente, no un ajuste silencioso.

### 4.3 — Diagrama de contexto funcional

```
   WEALTH MANAGER        INVESTMENT COMMITTEE        COMITÉ MODEL RISK
        │  ▲                    │  ▲                       │  ▲
   pregunta│ analytical     parámetros│ excepciones     validación│ estado
        │  │ output       institucionales│ y views       de modelos│ de modelo
        ▼  │                    ▼  │                       ▼  │
 ┌──────────────────────────────────────────────────────────────────┐
 │                    AFI EXPERT SYSTEM (núcleo)                    │
 │  Decision Case  ·  Orchestrator  ·  Data Completeness Gate       │
 │  10 Quantitative Engines  ·  Diagnostic Synthesis                │
 │  Trade-off  ·  Alternatives  ·  Recommendation Layer             │
 │  Audit & Decision History  ·  Parameter Registry                 │
 └──────────────────────────────────────────────────────────────────┘
        ▲                            ▲                      ▲
        │                            │                      │
  Capa de datos institucional   Módulo DD / Approved   GOVERNANCE &
  (NAV, flujos, holdings,       List (IDD/ODD, V2)     ESCALATION RULES
  benchmarks, índices, FX,                             (interfaz, reglas
  tasas, IPS, escenarios)                              internas externas
                                                        al sistema — DF 3.1)
        ▲
        │
  Custodios · Gestoras · Proveedores de índices y mercado · Reguladores · Cliente
```

El bloque `GOVERNANCE & ESCALATION RULES` aparece en el diagrama como **interfaz con contrato definido y reglas internas vacías** — exactamente el estatus que el framework le asigna `[DF READINESS]`.

---

## 5. End-to-End Functional Process

### 5.1 — La cadena de referencia

La cadena de `[DF 4.1]` es la columna vertebral del sistema y no se reemplaza. Se desarrolla aquí con el módulo responsable de cada paso y el artefacto funcional que produce.

| # | Paso `[DF 4.1]` | Módulo responsable | Artefacto producido | Puede omitirse |
|---|---|---|---|---|
| 1 | Client / Executive Question | Decision Intake (10.1) | `DecisionCase` (pregunta, unidad, objetivo, horizonte) | No |
| 2 | Decision Orchestrator | Orchestrator (7) | `AnalysisPlan` (11 respuestas) | No |
| 3 | Data Requirements | Data Requirement Registry (8.2) | `DataRequirementSet` del plan | No |
| 4 | Data Completeness | Completeness Gate (10.4) | `CompletenessReport` (BLOCK / WARNING / CONTINUE por dato) | No |
| 5 | Relevant Quantitative Engines | Engines (11) — subconjunto, nunca todos por default `[DF 4.1]` | `EngineResult` por motor activado | Sí, si el plan no los requiere |
| 6 | Engine Outputs | Engines | Métricas + diagnósticos + warnings `[DF 2.1]` | Sí |
| 7 | Diagnostic Synthesis | Diagnostic Synthesis (12) | `Diagnosis` multi-horizonte con trazabilidad | Sí, en Nivel 0 |
| 8 | Trade-off Detection | Trade-off Module (13) | `TradeOff` con nueve componentes | Sí, si no hay conflicto |
| 9 | Alternative Generation | Alternatives Module (14) | `AlternativeSet` (0..n) | Sí |
| 10 | Recommendation Layer | Recommendation Layer (15) | `AnalyticalOutput` con nivel alcanzado | No |
| 11 | Level 0 / 1 / 2 / 3 | Recommendation Layer | Etiqueta de nivel + elementos obligatorios | No |
| 12 | Wealth Manager | WM Interface (17) | `WMReview` (aceptación / rechazo / override justificado) | No |
| 13 | Final Decision | Decision Record (22.1) | `Decision` registrada | No |
| 14 | Decision History | History (22.1) | Registro completo situación→resultado `[DF 6.5]` | No |
| 15 | Learning Loop | Learning Loop (22.3) | Evidencia para calibración institucional | No (asíncrono) |

**Regla de recorrido `[DF 4.1]`:** la cadena es el mapa completo; cada pregunta recorre el subconjunto que le corresponde. Una consulta de Nivel 0 puede no generar trade-offs ni alternativas porque no hay decisión de por medio, solo información.

### 5.2 — Los tres cortes de responsabilidad que no se mezclan

```
ENGINES              →  INPUTS → CALCULATIONS → METRICS → DIAGNOSTICS → WARNINGS
                        nunca una instrucción de acción                  [DF 2.1]
ORCHESTRATOR         →  qué analizar, con qué datos, qué integrar
                        cero métricas propias                            [DF 2.2]
RECOMMENDATION LAYER →  ¿alcanza la evidencia para Nivel 3?
                        cero cálculos nuevos, cero gobernanza            [DF 2.3]
```

**Test funcional de la separación (DERIVADO, usable como criterio de aceptación):**

1. Si se elimina el Orchestrator, los motores siguen calculando pero nadie decide qué activar → la separación es real.
2. Si se elimina la Recommendation Layer, el sistema sigue llegando a Nivel 2 (alternativas) pero no puede afirmar superioridad analítica → la separación es real.
3. Si algún motor produce un verbo de acción ("vender", "reducir", "cambiar"), la separación está rota `[DF 2.1]`.

### 5.3 — Ejemplo de recorrido completo (trazable, sin números inventados)

Pregunta: *"¿Debemos rebalancear la cuenta X?"* → caso de uso 5 `[DF 7.3]`.

```
DecisionCase: unidad = portafolio; decisión = D1; horizontes = corto/mediano/largo
   ↓ Orchestrator: motores núcleo = Construction, Risk, Liquidity; opcional = Scenario [DF 7.3]
   ↓ DataRequirementSet: posiciones, SAA vigente y bandas, costos de transacción estimados [QM XVIII D1]
   ↓ Completeness: si falta SAA vigente → BLOCK (el drift no es computable sin objetivo) DERIVADO
   ↓ Rebalancing flow [DF 6.4]: Drift → Materiality → Risk → Liquidity → Costs → Taxes → Scenarios
   ↓ Diagnostic Synthesis: qué mejora / qué empeora por horizonte
   ↓ Trade-off: si Liquidity y Diversification compiten → nueve pasos [DF 4.3]
   ↓ Alternatives: patrón A/B/C (mantener / parcial / completo) — caso especial, no regla general [DF 4.2]
   ↓ Recommendation Layer: ¿Nivel 3 alcanzable? Si sí, ocho elementos [DF 4.4] (ver OPEN ISSUE ESFS-01)
   ↓ Analytical Output → WM → Decisión → History → Learning Loop
```

El paso de **Materiality** filtra desviaciones triviales antes de correr el análisis completo `[DF 6.4]`; su umbral es un parámetro configurable sin valor asignado (OPEN ISSUE ESFS-08).

---

## 6. Functional Architecture

### 6.1 — Catálogo de módulos funcionales

Doce grupos de módulos. La columna "Naturaleza" distingue lo que el framework separa: motor (calcula), coordinación (no calcula), registro (persiste), vista (presenta), interfaz externa (contrato sin reglas internas).

| ID | Módulo | Naturaleza | Responsabilidad exclusiva | Fuente | Prioridad |
|---|---|---|---|---|---|
| **M01** | Decision Intake | Coordinación | Capturar pregunta, unidad de análisis, objetivo y horizontes; crear el `DecisionCase` | `[DF 4.1]` paso 1 | MUST |
| **M02** | Decision Orchestrator | Coordinación | Responder las once preguntas y emitir el `AnalysisPlan` | `[DF 2.2]` | MUST |
| **M03** | Client / Investor Profile (IPS) | Registro | Mantener IPS vigente, objetivos, restricciones, horizonte, liquidez requerida, moneda, perfil | `[QM XVI]` `[V1 P1-P2]` | MUST |
| **M04** | Portfolio State | Registro | Estado actual del portafolio: posiciones, pesos, clases, vehículos, monedas, liquidez, histórico | `[V3 5.4]` `[QM XVI]` | MUST |
| **M05** | Instrument / Vehicle & Manager Registry | Registro | Ficha del vehículo y del gestor: estructura, liquidez, costos, frecuencia de valuación, factsheet, reglamento | `[QM XVI]` `[V2 B1]` | MUST |
| **M06** | Market & Reference Data | Registro | Benchmarks, índices, FX, curvas de tasas, CMAs | `[QM XVI]` | MUST |
| **M07** | Data Requirement Registry | Registro | Qué input necesita cada métrica de cada motor, con criticidad y mínimo histórico | Parte 9 de este documento | MUST |
| **M08** | Data Completeness Gate | Coordinación | Clasificar cada dato requerido en BLOCK / WARNING / CONTINUE y emitir el `CompletenessReport` | `[DF 6.1]` | MUST |
| **M09** | Quantitative Engines (×10) | Motor | Calcular, diagnosticar y emitir warnings. Nunca decidir | `[DF 2.1]` `[QM II, XXIV]` | MUST (subconjunto) |
| **M10** | Manager Due Diligence & Approved List | Registro + flujo (OPEN ISSUE ESFS-04) | IDD, ODD con poder de veto, estados de vehículo, memos, excepciones off-list | `[V2 B6, B7, B8]` `[QM XVIII D3, D14]` | MUST para D3/D4/D5/D11/D14 |
| **M11** | Diagnostic Synthesis | Coordinación | Integrar outputs de motores activados, por horizonte, con trazabilidad hasta la fuente | `[DF 4.1]` | MUST |
| **M12** | Trade-off Module | Coordinación | Detectar conflicto entre señales y presentar los nueve componentes obligatorios | `[DF 4.3]` | MUST |
| **M13** | Alternatives Module | Coordinación | Generar el conjunto (0..n) de alternativas cuantitativamente evaluables | `[DF 4.2]` | MUST |
| **M14** | Recommendation Layer | Coordinación | Evaluar suficiencia de evidencia para Nivel 3 y emitir el `AnalyticalOutput` | `[DF 2.3]` | MUST |
| **M15** | Explanation Layer (determinística) | Motor de reglas | Regla versionada + plantilla parametrizada por stakeholder | `[QM XIX]` | MUST (se construye con cada motor, no como fase aparte `[QM ROADMAP]`) |
| **M16** | WM Interface | Vista | Presentar lo necesario para decidir, por decisión y no por métrica | `[QM XIX]` `[QM I.5]` | MUST |
| **M17** | Audit & Traceability Log | Registro | Registro obligatorio de once campos por output `[QM XXI]` | `[QM XXI]` | MUST |
| **M18** | Decision History | Registro | Situación, datos, análisis, alternativas, recomendación, decisión, resultado posterior | `[DF 6.5]` | MUST |
| **M19** | Tracking & Monitoring Views | Vista | Seguimiento de portafolios, recomendaciones y evolución expectativa vs. resultado | `[DF 6.5]` `[QM II.8]` | SHOULD |
| **M20** | Learning Loop | Coordinación asíncrona | Consolidar evidencia para calibración institucional, sin modificar la metodología automáticamente | `[DF 6.5]` | SHOULD |
| **M21** | Rebalancing History View | Vista | Timeline de rebalanceos por cliente con el escenario de mercado vigente en cada caso | `[DF 6.6]` — clasificado SUPPORTING VIEW | COULD |
| **M22** | Parameter Registry | Registro | Todo parámetro con su categoría de gobernanza, valor, versión y trazabilidad de cambios | `[QM XV]` | MUST |
| **M23** | Model Governance Registry | Registro | Clasificación CORE/ADVANCED/RESEARCH/REJECTED, responsable, fecha de última validación, estado de degradación | `[QM XIV]` | MUST (mínimo: registro) |
| **M24** | Scenario Library | Registro | Escenarios históricos e hipotéticos definidos por el Comité, versionados | `[QM XI]` | SHOULD |
| **M25** | Governance & Escalation Interface | Interfaz externa | Contrato de entrega del Analytical Output hacia la capa de gobernanza. Sin reglas internas de asignación | `[DF 3.1]` `[DF READINESS]` | MUST (solo contrato) |

### 6.2 — Lo que deliberadamente no existe como módulo

| No existe | Por qué | Fuente |
|---|---|---|
| Execution Module | Nivel 4 no existe en ninguna versión del sistema | `[DF 4.4]` |
| Score global de cliente o de portafolio | Ningún motor se pondera contra otro; el Monitoring Engine prioriza entre cuentas pero nunca colapsa las dimensiones de un mismo cliente | `[DF 2.1, 4.3, 8.2]` |
| XAI Module (SHAP/LIME) | REJECTED — viola el Principio 3 | `[QM III.0 Rev 1]` `[QM XIX]` |
| Auto-Commentary / narrativa generativa | REJECTED — no auditable determinísticamente | `[QM III.0 Rev 2]` |
| Motor de ranking directo contra pares sin eligibility check | REJECTED | `[QM III.1]` `[QM XII]` |
| Escalation Rules Engine (con reglas internas) | Es decisión institucional de AFI, capa externa al sistema | `[DF 3.1]` |
| Client Communication Module autónomo | El sistema nunca comunica al cliente de forma autónoma | `[QM XX]` — ver OPEN ISSUE ESFS-12 sobre la vista de cliente |

### 6.3 — Vista en capas

```
┌─────────────────────────────────────────────────────────────────┐
│ CAPA 5 — PRESENTACIÓN Y GOBERNANZA                              │
│ M16 WM Interface · M19 Tracking · M21 Rebalancing History       │
│ M25 Governance & Escalation Interface (contrato, sin reglas)     │
├─────────────────────────────────────────────────────────────────┤
│ CAPA 4 — DECISIÓN (no calcula)                                  │
│ M11 Diagnostic Synthesis → M12 Trade-off → M13 Alternatives      │
│ → M14 Recommendation Layer (Nivel 0-3)                          │
├─────────────────────────────────────────────────────────────────┤
│ CAPA 3 — CÁLCULO (no decide)                                    │
│ M09 Diez motores  ·  M15 Explanation Layer (acoplada a cada     │
│ motor, no posterior)  ·  M10 DD & Approved List                 │
├─────────────────────────────────────────────────────────────────┤
│ CAPA 2 — HABILITACIÓN DE ANÁLISIS                               │
│ M02 Orchestrator · M07 Data Requirement Registry                │
│ M08 Data Completeness Gate · M22 Parameter Registry             │
│ M23 Model Governance Registry                                   │
├─────────────────────────────────────────────────────────────────┤
│ CAPA 1 — INFORMACIÓN                                            │
│ M03 IPS · M04 Portfolio State · M05 Vehículos y Gestores        │
│ M06 Market & Reference Data · M24 Scenario Library              │
├─────────────────────────────────────────────────────────────────┤
│ CAPA 0 — MEMORIA INSTITUCIONAL (transversal, siempre activa)    │
│ M01 Decision Case · M17 Audit Log · M18 Decision History        │
│ M20 Learning Loop                                               │
└─────────────────────────────────────────────────────────────────┘
```

La Capa 0 es transversal y no opcional: un output sin registro de auditoría no es un output válido del sistema `[QM XXI]`.

---

## 7. Decision Orchestrator

### 7.1 — Contrato funcional

| Campo | Contenido |
|---|---|
| **Función** | Coordinar el análisis: determinar qué debe analizarse, con qué datos y qué debe integrarse `[DF 2.2]` |
| **Inputs** | `DecisionCase` (pregunta, unidad de análisis, objetivo, horizontes), catálogo de motores y su estado de disponibilidad, `CompletenessReport`, Decision Library, Parameter Registry |
| **Procesamiento** | Resolver las once preguntas en secuencia; emitir el `AnalysisPlan` |
| **Outputs** | `AnalysisPlan` |
| **Prohibiciones absolutas** | No calcula ninguna métrica propia. Si necesitara un cálculo nuevo, eso sería por definición un motor nuevo, y no se introduce ninguno `[DF 2.2]`. No evalúa suficiencia de evidencia para Nivel 3 — esa pregunta migró a la Recommendation Layer `[DF 2.2 nota]`. No asigna instancia de gobernanza `[DF 3.1]` |
| **Frecuencia** | Por `DecisionCase`; re-ejecutable si cambian datos o parámetros (DERIVADO: la re-ejecución genera una nueva versión del plan, no sobrescribe la anterior — exigencia de `[QM XXI]`) |

### 7.2 — Las once preguntas como especificación funcional

| # | Pregunta `[DF 2.2]` | Input que consume | Output que produce | Falla si... |
|---|---|---|---|---|
| 1 | ¿Cuál es la pregunta? | Intake del WM | `decision_type` mapeado a la Decision Library (D1-D15) o a consulta informativa | La pregunta no mapea a ningún caso de uso conocido → estado `unmapped_question` (DERIVADO; ver OPEN ISSUE ESFS-06) |
| 2 | ¿Cuál es la unidad de análisis? | Intake + Portfolio State | `analysis_unit` ∈ {cliente, portafolio, vehículo, gestor, book} | Unidad ambigua → el sistema pregunta, no asume |
| 3 | ¿Cuál es el objetivo? | IPS (M03) | Referencia a `IPS.id_ips` y a la/las metas afectadas | Sin IPS vigente: el análisis continúa donde es posible pero Nivel 3 queda condicionado `[QM XXIV ClientGoal]` |
| 4 | ¿Qué información existe? | M03-M06, M10 | Inventario de inputs disponibles con fecha y versión | — |
| 5 | ¿Qué información falta? | M07 + M08 | Lista de faltantes con criticidad | — |
| 6 | ¿Qué motores son relevantes? | Matriz de orquestación `[DF 7.3]` | Lista de motores núcleo + opcionales | No se activan todos los motores por default `[DF 4.1, 7.2]` |
| 7 | ¿Qué motores están bloqueados? | `CompletenessReport` + Model Governance | Lista de motores bloqueados con la causa | — |
| 8 | ¿Qué outputs deben integrarse? | Definición del flujo `[DF 7.1]` | Secuencia de integración para el Diagnostic Synthesis | — |
| 9 | ¿Existen trade-offs? | Outputs de motores | Señal de conflicto para M12 (detección, no resolución) | El umbral que define "conflicto" es un parámetro sin valor asignado (OPEN ISSUE ESFS-07) |
| 10 | ¿Qué alternativas son cuantificables? | Outputs + restricciones | Espacio de alternativas admisible para M13 | Si es vacío, se declara explícitamente `[DF 4.2]` |
| 11 | ¿Qué limitaciones deben mostrarse? | `CompletenessReport` + limitaciones de modelo `[QM XXII]` | Lista de limitaciones a exhibir obligatoriamente | El sistema nunca presenta un análisis como completo si hay limitaciones materiales no declaradas `[DF 6.1]` |

### 7.3 — Estructura del `AnalysisPlan`

| Campo | Descripción |
|---|---|
| `case_id`, `plan_version` | Identificación y versión (auditable) |
| `decision_type` | D1-D15 o `information_query` |
| `use_case_id` | 1-18 `[DF 7.3]` |
| `flow_id` | Uno de los once flujos operativos `[DF 7.1]`, cuando aplica |
| `analysis_unit`, `entity_id` | Unidad y entidad concreta |
| `ips_ref` | Referencia obligatoria al IPS `[QM I.1]` |
| `horizons[]` | Corto / mediano / largo `[DF 6.2]` |
| `engines_core[]`, `engines_optional[]`, `engines_blocked[]` | Con causa de bloqueo por cada uno |
| `data_requirements[]` | Referencia al `DataRequirementSet` |
| `integration_sequence[]` | Orden de integración para el diagnóstico |
| `limitations[]` | Limitaciones a mostrar |
| `parameters_snapshot` | Valores y versiones de parámetros usados `[QM XXI]` |

### 7.4 — Regla de activación de motores

No se ejecutan todos los motores para toda pregunta `[DF 7.2]`. La selección se toma de la Decision Orchestration Matrix `[DF 7.3]` — dieciocho casos de uso con motores núcleo (indispensables) y opcionales (mejoran robustez, no bloquean el análisis).

| # | Caso de uso | Motores núcleo | Opcionales | Alternativas (típico, no fijo) |
|---|---|---|---|---|
| 1 | Nuevo cliente | Ninguno aún | — | 0 — paso de recopilación |
| 2 | Diagnóstico inicial | Subconjunto según disponibilidad | Los demás, según robustez deseada | 0-1 |
| 3 | Construcción de portafolio | Construction, ClientGoal | Diversification | 2-4 |
| 4 | Revisión periódica | Performance, Risk | Diversification, Scenario | 0-2 |
| 5 | Rebalanceo | Construction, Risk, Liquidity | Scenario | Variable, típicamente 3 |
| 6 | Deterioro de fondo | Performance, Monitoring | Risk (factor exposure) | 2-4 |
| 7 | Nueva inversión | Due diligence, Alternatives (si privado) | Diversification, Liquidity | 0-2 |
| 8 | Cambio de estrategia | Construction, ClientGoal | Todos, según alcance | 2-4 |
| 9 | Oportunidad | Performance/Risk (detección) | Benchmark, Diversification | 0-1 |
| 10 | Problema de liquidez | Liquidity, ClientGoal | Alternatives, Scenario | Variable |
| 11 | Cambio en objetivos | ClientGoal | Los que se activen tras el cambio | 0 |
| 12 | Cambio de riesgo | Risk | Construction (si implica rediseño) | 0-2 |
| 13 | Cambio de horizonte | ClientGoal | Construction (si afecta SAA) | 0-2 |
| 14 | Asset Allocation | Construction | Diversification, Scenario | 2-4 |
| 15 | Alternativos | Alternatives, Liquidity | Risk (factor aproximado) | 0-2 |
| 16 | Benchmark | Benchmark | — | 0 — es un gate |
| 17 | Stress Testing | Scenario | Todos, como inputs de qué estresar | 0-1 |
| 18 | Revisión patrimonial | Los 10, según relevancia | — | Variable, potencialmente varios trade-offs |

**Observación funcional (DERIVADO, no una modificación):** el caso 7 nombra "Due diligence" como motor núcleo y no es uno de los diez motores `[DF 2.1]`; el caso 6 y el flujo de deterioro `[DF 7.1]` incorporan Qualitative Due Diligence. Esto confirma la necesidad del módulo M10 y su OPEN ISSUE de ubicación (ESFS-04). El número de alternativas de la última columna es el patrón observado, no una regla: el número es dinámico `[DF 4.2]`.

### 7.5 — Los once flujos operativos como secuencias ejecutables

Cada flujo es una secuencia de motores en orden específico, no un modelo nuevo `[DF 7.1]`.

| Flujo | Secuencia (fuente) | Motores núcleo |
|---|---|---|
| Portfolio Diagnostic | Portfolio → Performance → Risk → Diversification → Liquidity → Goals → Benchmark → Allocation → Scenarios | Subconjunto relevante, nunca todos por default |
| Performance | Performance → Benchmark Eligibility → Benchmark Comparison → Relative Performance → Risk-adjusted → Time Horizon → Root Cause → Interpretation | Performance, Benchmark, Risk |
| Risk | Risk Measurement → Historical Context → Benchmark/Policy → Client Constraints → Horizon → Liquidity → Scenario → Interpretation | Risk, Benchmark, Liquidity, Scenario |
| Diversification | Holdings → Asset Class → Currency → Geography → Vintage → Correlation → Risk Contribution → Factor Exposure → Concentration → Interpretation | Diversification, Risk |
| Liquidity | Client Needs → Cash Flows → Ladder → Liquid → Illiquid → Capital Calls → Stress → Coverage → Interpretation → Alternatives | Liquidity, ClientGoal, Alternatives, Scenario |
| Alternative Investment | NAV → Cash Flows → Vintage → TVPI/DPI/RVPI/IRR → Liquidity → Risk → Benchmark/Peer (si elegible) → Portfolio Impact → Interpretation | Alternatives, Liquidity, Risk, Benchmark |
| Portfolio Construction | Objectives → Horizons → Risk → Liquidity → Constraints → Current Portfolio → Expected Returns → Risk Model → Correlations → Optimization → Scenarios → Alternative Portfolios → WM | ClientGoal, Construction, Risk, Liquidity, Diversification, Scenario |
| Rebalancing | Portfolio → Target → Drift → Materiality → Risk → Liquidity → Costs → Taxes/Restrictions → Scenarios → Alternatives → Analytical Recommendation → WM `[DF 6.4]` | Construction, Risk, Liquidity, Scenario |
| Fund/Manager Deterioration | Performance → Benchmark → Risk → Factor Exposure → Qualitative DD → ¿deterioro persistente? → causas → Portfolio Impact → Alternatives | Performance, Benchmark, Risk, Monitoring (+ M10) |
| Opportunity Analysis | Separación explícita entre Opportunity Identification e Investment Decision | Performance, Risk, Diversification, Benchmark en modo detección |
| Scenario | Base vs. Optimistic vs. Adverse vs. Stress → Return, Risk, Drawdown, Liquidity, Goal Probability, Currency, Concentration | Scenario |

**OPEN ISSUE ESFS-06:** los once flujos y los dieciocho casos de uso no tienen un mapeo uno a uno declarado en las fuentes; los casos 11, 12 y 13 (cambio de objetivos, de riesgo, de horizonte) no tienen flujo dedicado. El Orchestrator necesita ese mapeo canónico para enrutar de forma determinística.

---

## 8. Data Requirements Architecture

### 8.1 — Las nueve dimensiones de especificación de un dato

Cada input del sistema se especifica con las nueve dimensiones exigidas por el mandato. Los valores admisibles provienen de `[QM XVI]` y `[QM XVII]`.

| Dimensión | Valores admisibles | Fuente |
|---|---|---|
| **Input requerido** | Nombre del dato en el Data Dictionary | `[QM XVI]` |
| **Tipo de dato** | Numérico · categórico · temporal (serie) · documental · evento fechado · metadata | `[QM XVI]` |
| **Granularidad** | Cliente · portafolio · posición · vehículo/fondo · serie de vehículo · gestor · asset class · factor · mercado | `[QM XVI]` `[V3 5.4]` |
| **Frecuencia** | Tiempo real (no requerida por ninguna métrica de la metodología) · diaria · mensual · trimestral · anual · por evento · bajo demanda | `[QM XVI]` |
| **Histórico requerido** | Solo donde la metodología lo fija: 3-5 años (volatilidad, correlación) · 36-60 observaciones mensuales (TE) · desde inicio y rolling 3-5 años (max drawdown) · frecuencia nativa sin interpolar | `[QM V, VI]` |
| **Fuente** | Custodio · administrador · gestora · regulador/CMF · proveedor de índices · proveedor de mercado · cliente vía asesor · WM · Comité de Inversiones · calculado por el sistema | `[QM XVI]` |
| **Calidad mínima** | Las condiciones de `[QM XVI]` por dato y los ocho controles de `[QM XVII]` | `[QM XVI, XVII]` |
| **Dependencias** | Otros datos sin los cuales este dato no es utilizable (p. ej. Returns depende de NAV + Cash flows) | `[QM XVI]` |
| **Criticality** | CRITICAL (BLOCK) · NON-CRITICAL importante (WARNING) · complementario (CONTINUE) | `[DF 6.1]` |

### 8.2 — Regla de derivación de la criticidad

`[DF 6.1]` define los tres comportamientos pero no clasifica cada campo; `[QM XVII]` define Model Block por *tipo de problema de datos*, no por campo. Para que Data Completeness sea implementable, ESFS-01 aplica una **regla de derivación explícita** (DERIVADO — no agrega metodología, solo hace operable la ya existente):

| Nivel | Regla de derivación | Comportamiento | Ejemplo con fuente |
|---|---|---|---|
| **CRITICAL** | (a) la métrica es matemáticamente incomputable sin el dato, o (b) la metodología prohíbe explícitamente el sustituto o la imputación | BLOCK: el indicador no se muestra; se declara qué falta y por qué bloquea `[DF 6.1]` | Sin serie FX confiable no se combinan monedas → Model Block `[QM XVII]`. Sin benchmark elegible no hay Excess Return ni TE `[QM V, XII]` |
| **NON-CRITICAL (importante)** | El cálculo es posible pero su interpretación queda materialmente limitada | WARNING: el indicador se muestra con nota explícita de la limitación `[DF 6.1]` | Historial parcialmente reconstruido (backfill bias) → flag y exclusión del período pre-lanzamiento `[QM XVII]` |
| **COMPLEMENTARIO** | Su ausencia no altera el resultado ni su interpretación | CONTINUE: el indicador se muestra sin nota `[DF 6.1]` | Metadata descriptiva no usada por el cálculo solicitado |

**Límite declarado de esta regla:** no resuelve el umbral cuantitativo de "gap significativo" en datos faltantes, que la metodología deja explícitamente pendiente y que depende de la frecuencia nativa de cada tipo de vehículo `[QM XXIII Pendiente 2]`. Sin ese umbral, el Completeness Gate puede distinguir *ausencia total* de *presencia completa*, pero no *gap tolerable* de *gap bloqueante*: OPEN ISSUE ESFS-09, bloqueante para Fase 1.

### 8.3 — Entidades de información funcional

Derivadas del modelo conceptual de `[V3 5.4]` y del Data Dictionary `[QM XVI]`. Son entidades funcionales, no un esquema físico.

| Entidad | Atributos funcionales mínimos | Motores/módulos que la consumen |
|---|---|---|
| `Cliente` | id, segmento, perfil de riesgo, país de residencia, moneda base | Todos |
| `IPS` | id, id_cliente, objetivos cuantificados, restricciones, horizonte(s), límites de riesgo por perfil, necesidades de liquidez, vigencia, estado de firma | Todos (referencia central `[QM I.1]`) |
| `LifeBalanceSheet` | capital humano, activos no financieros, pasivos explícitos e implícitos, compromisos futuros | Liquidity (límite de ilíquidos), ClientGoal `[V1 P2]` `[QM IX]` |
| `Portafolio` | id, id_cliente, tipo, modelo de referencia (SAA vigente), bandas | Todos |
| `Posicion` | id, id_portafolio, id_activo, cantidad, fecha, moneda | Performance, Risk, Diversification, Liquidity |
| `Activo` / `Vehiculo` | id, tipo, liquidez (periodicidad de valuación, ventana de redención, lock-up), gestor, costo total, estructura, moneda | Todos |
| `SerieNAV` | id_activo, fecha, valor, frecuencia nativa, fuente, versión de extracción | Performance, Risk, Diversification, Alternatives |
| `Cashflow` | id, entidad, fecha, monto, clasificación (aporte/retiro/fee/capital call/distribución) | Performance, Liquidity, Alternatives |
| `Benchmark` | id, tipo (market/policy/custom/peer), definición, moneda, costos (bruto/neto), universo, restricciones | Benchmark, Performance, Risk |
| `EligibilityCheck` | id_benchmark, id_portafolio, resultado por cada una de las ocho dimensiones, estado, fecha, autor de excepción si existe | Benchmark `[QM XII]` |
| `Escenario` | id, tipo (histórico/hipotético/reverse), definición versionada, autor (Comité), fecha | Scenario `[QM XI]` |
| `CMA` | asset class, retorno esperado, volatilidad, correlaciones, versión, fecha, aprobador | Construction, Diversification |
| `CommitmentAlternativo` | id_vehículo, compromiso, vintage, llamadas y distribuciones realizadas y proyectadas | Alternatives, Liquidity |
| `Manager` | id, firma, equipo, pilares People/Philosophy/Process/Parent/Price, historial de rating | M10 `[V2 B2-B5]` |
| `ODDReview` / `IDDReview` | id, fecha, analista, resultado, hallazgos críticos, rating | M10 `[V2 B6]` |
| `ApprovedListEntry` | id_vehículo, estado (Approved-Active / Watchlist / Restricted / Removed), rating, límites de uso, excepciones | M10 `[QM XVIII D3]` `[V2 B7-B8]` |
| `MotorResultado` | id, tipo_motor, entidad, unidad de análisis, período, métricas, diagnósticos, warnings, `ips_ref`, versión de modelo, parámetros, estado (`ok` / `insufficient_data`) | Diagnostic Synthesis, Audit |
| `Parametro` | nombre, categoría de gobernanza `[QM XV]`, valor, versión, vigencia, propuesto por, aprobado por, justificación | Todos |
| `DecisionCase` | id, pregunta, unidad, decisión, estado, versiones de plan, outputs, decisión del WM, override y justificación | M01, M17, M18 |
| `Alerta` | id, origen (motor), tipo, severidad, entidad, fecha, estado | Monitoring, WM Interface |

### 8.4 — Reglas de calidad de datos como comportamiento del sistema

Los ocho controles de `[QM XVII]` se implementan con el patrón **Detection → Action → Warning → Fallback o Model Block**, sin excepción y sin silencios.

| Problema | Detección | Comportamiento del sistema | Fallback / Block |
|---|---|---|---|
| Missing Data | Días/meses sin NAV registrado | Evaluar impacto del gap en el cálculo específico; flag visible | Imputación prudente si el gap es menor y no afecta materialmente; **Model Block** si es significativo — umbral pendiente (ESFS-09) |
| Outliers | Retornos extremos fuera de rango histórico razonable | Validar contra fuente secundaria o custodio antes de aceptar; flag "retorno atípico pendiente de validación" | Excluir del cálculo hasta validación; nunca incluir silenciosamente |
| Stale Prices | NAV repetido de forma improbable | Distinguir baja frecuencia legítima de error de carga; flag diferenciado | Model Block si no se puede distinguir con confianza |
| NAV inconsistentes | Cambio improbable dado el perfil de riesgo del vehículo | Contraste con administrador/custodio; flag crítico, prioridad alta | Model Block hasta reconciliación |
| Frequency Mismatch | Series con distinta frecuencia nativa | Agregar a la frecuencia más baja común; nota explícita de la frecuencia usada | Nunca interpolar la frecuencia faltante |
| Currency Mismatch | Series en distinta moneda sin ajuste | Aplicar y documentar FX explícito (tipo y fecha) | Model Block si no hay serie FX confiable |
| Look-Ahead Bias | Uso de información no disponible en la fecha simulada | Control de diseño en backtesting, no de runtime | Rechazar el backtest si se detecta la fuga |
| Survivorship Bias | Universo que excluye fondos cerrados/liquidados | Usar bases con histórico de fondos cerrados; nota metodológica visible | Advertir explícitamente si la fuente no cubre fondos cerrados |
| Backfill Bias | Historial reconstruido antes del lanzamiento real | Identificar fecha de lanzamiento real; flag | Excluir el período pre-lanzamiento del cálculo de habilidad del gestor |
| Selection Bias | Criterio de inclusión del universo no documentado | Nota metodológica visible | Rechazar la comparación |

**Regla de oro AFI, implementada como comportamiento por defecto:** si los datos no permiten estimar la métrica con un nivel de confianza razonable, el sistema declara explícitamente que la evidencia es insuficiente `[QM XVII]`.

### 8.5 — Estados de dato y de resultado

| Estado | Significado | Efecto en el output |
|---|---|---|
| `available` | Dato presente y aprobado por las reglas de calidad | Cálculo normal |
| `degraded` | Dato presente con limitación declarada (gap menor, backfill, frecuencia agregada) | Cálculo con WARNING obligatorio |
| `pending_validation` | Dato presente pero sospechoso (outlier, stale) | Excluido del cálculo hasta validación |
| `missing_critical` | Dato ausente y CRITICAL | BLOCK del indicador con declaración de qué falta y por qué |
| `missing_non_critical` | Dato ausente, no crítico | WARNING o CONTINUE según 8.2 |
| `not_verifiable` | No hay información para verificar una dimensión (caso benchmark) | La dimensión se marca no verificable; **no se asume comparabilidad por defecto** `[QM XXIV Benchmark]` |
| `insufficient_data` | Estado de primera clase del resultado del motor | Se declara "información insuficiente para producir una estimación confiable" `[QM XIV]` |

### 8.6 — Parameter Registry

Todo parámetro pertenece a exactamente una categoría con un propietario único de la decisión de cambiarlo `[QM XV]`.

| Categoría | Quién puede modificarlo | Requiere registro de auditoría |
|---|---|---|
| Matemático (p. ej. factor de anualización) | Nadie — se deriva | No |
| Sistema (calculado de datos) | Nadie directamente | No |
| Institucional (niveles de confianza de VaR, δ, τ) | Comité de Inversiones, revisión anual mínima | Sí |
| Cliente (horizonte, tolerancia, restricciones ESG) | Asesor + Cliente, con validación del Comité | Sí |
| Comité (views de BL, CMAs, SAA institucional) | Investment Committee exclusivamente | Sí |
| Wealth Manager (ajuste operativo dentro de rangos pre-aprobados) | Asesor, nunca fuera de los límites | Sí |

Registro obligatorio de todo cambio en las tres últimas categorías: quién lo propuso, quién lo aprobó, fecha, valor anterior, valor nuevo y justificación escrita `[QM XV]`.

**Valores conocidos vs. pendientes (importante para implementación):**

| Parámetro | Valor en las fuentes | Estado |
|---|---|---|
| Niveles de confianza de VaR/ES | 95% (comunicación a cliente) y 99% (Comité) `[QM V]` | Definido |
| Horizonte de VaR | 1 mes y 1 año `[QM V]` | Definido |
| Ventana de volatilidad y correlación | 3-5 años cuando esté disponible `[QM V, VI]` | Definido como rango |
| Observaciones mínimas para TE | 36-60 mensuales `[QM V]` | Definido como rango |
| Buckets de liquidez | 0-3m, 3-12m, >12m `[QM IX, XXIV]` | Definido |
| Simulaciones Monte Carlo | 5.000-20.000 `[QM XXII]` | Definido como rango |
| τ de Black-Litterman | 0.025-0.05 como referencia, fijado por política `[QM VIII]` | Referencia, no fijado |
| Bandas de rebalanceo | — | **Pendiente** `[QM XXIII P4]` |
| Umbral de materialidad de drift | — | **Pendiente** `[DF 8.3 OQ4]` |
| Umbral de activación de trade-off | — | **Pendiente** `[DF 8.3 OQ4]` |
| Umbrales de HHI / risk contribution por dimensión | — | **Pendiente** `[QM XVIII D7]` |
| Trimestres de alpha negativo para Watchlist | — | **Pendiente** `[QM XXIII P4]` |
| Gap significativo de datos faltantes | — | **Pendiente** `[QM XXIII P2]` |
| MAR para downside deviation | 0% o tasa libre de riesgo `[QM V]` | Definido como opción, requiere fijar consistencia |
| δ (aversión al riesgo institucional) | Definida por política `[QM VIII]` | Pendiente de valor |

Nueve parámetros pendientes de valor no impiden construir el sistema, pero **sí impiden operarlo**: todos deben existir como campos configurables desde Fase 0 `[DF READINESS]`.

---

## 9. Data Requirement Matrix

**Regla de admisión de esta matriz:** cada fila existe porque habilita un cálculo o una decisión identificada. Ningún dato aparece por ser "interesante" `[QM I.4]`. La columna *Histórico requerido* dice "**No fijado**" cuando la metodología no especifica el período; esos casos están consolidados en el OPEN ISSUE ESFS-10 y no se rellenan con supuestos.

Abreviaturas de criticidad: **C** = CRITICAL (BLOCK) · **NC** = NON-CRITICAL importante (WARNING) · **CP** = complementario (CONTINUE).

### 9.1 — Client / Investor Profile (M03) y Goals

| Módulo | Decisión | Motor | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M03 | Todas | ClientGoal | IPS vigente y firmado | documental + estructurado | cliente | 1-3 años o ante eventos de vida `[QM XVI]` | Versión vigente + histórico de versiones para auditoría `[QM XXIV ClientGoal]` | Asesor + Cliente, aprobado por Comité | **C** | — | Referencia central de todo motor `[QM I.1]`; sin IPS vigente `insufficient_data` en ClientGoal y Construction |
| M03 | D2, D8 | ClientGoal, Risk | Objetivos cuantificados (metas, monto, fecha) | numérico + temporal | cliente / meta | Ante cambios | No fijado | Cliente vía asesor | **C** para probabilidad de meta | IPS | Probabilidad de éxito por meta |
| M03 | D8 | Risk | Límites de riesgo por perfil (VaR/ES/volatilidad) | numérico | cliente / perfil | Revisión anual mínima | — | IPS + política institucional `[QM XV]` | **C** para D8 | Parameter Registry | Evaluación de compatibilidad riesgo-IPS; alerta sin bloqueo automático `[QM XVIII D8]` |
| M03 | D6, D9 | Liquidity, ClientGoal | Necesidades y calendario de flujos esperados del cliente (retiros, impuestos, gastos declarados) | evento fechado | cliente | Por evento / revisión periódica | No fijado | Cliente vía asesor `[QM IX]` | **C** para LCR y Ladder | — | Liquidity Coverage Ratio, Liquidity Ladder |
| M03 | D6, D9 | Liquidity | Life balance sheet (capital humano, activos no financieros, pasivos y compromisos) | estructurado | cliente | Ante cambios | No fijado | Cliente vía asesor `[V1 P2]` | **C** para el límite de ilíquidos `[QM IX]` | — | Límite máximo de peso en ilíquidos como función del balance extendido |
| M03 | Construcción | Construction | Restricciones (ESG, regulatorias, concentración por emisor/gestor/país) | categórico | cliente | Ante cambios | — | IPS | **NC** (C si el IPS las declara vinculantes) | Parameter Registry — alcance ESG pendiente `[QM XXIII P6]` | Constraints de optimización |
| M03 | Todas | Todos | Horizonte(s) corto / mediano / largo | temporal | cliente / meta | Ante cambios | — | IPS `[DF 6.2]` | **C** | — | Etiquetado obligatorio por horizonte de todo análisis relevante |
| M03 | Todas | Todos | Moneda base del cliente | categórico | cliente | Estable | — | IPS | **C** | Serie FX | Consistencia multi-moneda; sin FX confiable → Model Block `[QM XVII]` |

### 9.2 — Portfolio State (M04)

| Módulo | Decisión | Motor | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M04 | D1, D7, D8 | Risk, Diversification | Posiciones detalladas por instrumento | numérico | posición | Diaria (líquidos) / mensual / trimestral `[QM XVI]` | Serie para evolución; punto para estado actual | Custodio | **C** | Activo/Vehículo | Pesos, exposición, base de todo cálculo de portafolio |
| M04 | D1 | Construction | SAA vigente (modelo de referencia) y bandas configuradas | numérico | portafolio / asset class | Revisión trimestral/anual `[QM II.4]` | Versionado (auditoría del objetivo vigente) | Comité de Inversiones | **C** para D1 | Parameter Registry (bandas pendientes) | Drift; materialidad; trigger threshold-based |
| M04 | Todas | Todos | Mapeo posición → asset class / clase / subclase | metadata | posición | Ante cambios | — | Interna | **C** | Taxonomía institucional | Agregación jerárquica, HHI por dimensión |
| M04 | D6, D9 | Liquidity | Clasificación de liquidez del vehículo (periodicidad de valuación, ventana de redención, lock-up, comportamiento de cash flow) | categórico | vehículo | Ante cambios | — | Gestora / reglamento `[QM IX]` | **C** | Reglamento vigente | Buckets 0-3m / 3-12m / >12m; Ladder |
| M04 | D1 | Construction, Liquidity | Costos de transacción estimados y, donde aplique, impacto fiscal | numérico | posición / vehículo | Bajo demanda | — | Interna / custodio `[QM XIII]` | **NC** | — | Comparación de costos entre alternativas de rebalanceo |
| M04 | Todas | Performance | Metadatos de jerarquía de agregación | metadata | portafolio / cliente | Ante cambios | — | Interna | **C** | — | TWR por sub-portafolio, gestor y cliente |
| M04 | D7 | Diversification | Pesos objetivo por asset class / factor / estilo / liquidez | numérico | portafolio | Trimestral | — | Comité / Construction | **NC** | CMAs | Comparación diversificación actual vs. modelo |

### 9.3 — Performance Engine

| Módulo | Decisión | Motor | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M09 | D2, D3, D11 | Performance | Serie de NAV | temporal numérico | vehículo / portafolio | Diaria (líquidos) / mensual / trimestral (privados) `[QM XVI]` | Sin gaps no explicados; frecuencia nativa sin interpolar | Custodio / administrador | **C** | — | TWR geométricamente encadenado `[QM IV]` |
| M09 | D2, D3, D11 | Performance | Cash flows fechados y clasificados (aporte/retiro/fee) | evento fechado | portafolio / vehículo | Por evento | Completos en el período medido | Custodio / administrador | **C** | NAV | Subperíodos de TWR; `insufficient_data` si no están correctamente fechados/clasificados `[QM XXIV]` |
| M09 | Comunicación al cliente | Performance | Flujos con fecha + valor inicial y final | evento + numérico | cliente | Por evento | Serie completa del período | Custodio | **C** | — | MWR / IRR (XIRR) — "tu retorno personal" `[QM IV]` |
| M09 | D2 | Performance | TWR total + número de años | numérico | portafolio / vehículo | Bajo demanda | Menos informativo bajo 3 años `[QM XXII]` | Calculado | **C** | TWR | CAGR / retorno anualizado |
| M09 | D3, D10 | Performance + Benchmark | Serie del benchmark elegible | temporal numérico | benchmark | Diaria `[QM XVI]` | Coincidente con el período del portafolio | Proveedor de índices | **C** | `EligibilityCheck` = elegible | Excess Return — sin sentido si el benchmark no es elegible `[QM XXII]` |
| M09 | D2, D3 | Performance | Series rolling de 3-5 años | temporal | portafolio / vehículo | Mensual | 3-5 años `[QM IV]` | Calculado | **NC** | NAV | Rolling returns para consistencia; evita "period picking" |
| M09 | D3, D11 | Performance | Pesos y retornos por asset class del portafolio y del benchmark | numérico | asset class | Mensual | No fijado | Custodio + índices | **NC** (ADVANCED) | Transparencia de holdings; benchmark elegible | Atribución Brinson-Fachler (asignación vs. selección) |
| M09 | D3, D11 | Performance | Exposiciones factoriales y retornos | numérico | vehículo / portafolio | Mensual | No fijado | Índices públicos | **NC** (ADVANCED) | Modelo de factores calibrado | Atribución por factores; consistencia con el proceso declarado del gestor |
| M09 | Performance neta | Performance, Construction | Fees de gestión y de éxito | numérico | vehículo | Según estructura del vehículo | — | Gestora / custodio | **NC** — separadas del retorno bruto cuando sea posible `[QM XVI]` | — | Comparación neto contra neto (dimensión "Costos" del gate de benchmark) |
| M09 | D3, D11 | Performance | NAV trimestral + capital calls + distribuciones de vehículos privados | temporal + evento | vehículo privado | Trimestral | Alineado al reporting del fondo | Gestora | **C** para el vehículo privado | — | TWR trimestral (ADVANCED); nunca se fuerza comparación mensual/diaria `[QM IV]` |

### 9.4 — Risk Engine

| Módulo | Decisión | Motor | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M09 | D8 | Risk | Serie de retornos (mensual preferido para fondos abiertos) | temporal numérico | vehículo / portafolio | Mensual | **Ventana 3-5 años cuando disponible** `[QM V]` | Calculado desde NAV + flujos | **C** | NAV, cash flows | Volatilidad anualizada |
| M09 | D8, comunicación | Risk | Retornos + MAR | temporal + numérico | vehículo / portafolio | Mensual | Igual a volatilidad | Calculado + Parameter Registry (MAR = 0% o rf) | **C** | Consistencia de MAR entre comparaciones | Downside deviation |
| M09 | D8, calibración de tolerancia | Risk | Serie de NAV / TWR | temporal | vehículo / portafolio | Mensual | **Rolling 3-5 años y desde inicio** `[QM V]` | Calculado | **C** | — | Maximum drawdown (combinar con Recovery Time cuando esté disponible) |
| M09 | D3, D10 | Risk | Retornos del portafolio y del benchmark elegible | temporal | portafolio vs. benchmark | Mensual | **Mínimo 36-60 observaciones mensuales** `[QM V]` | Calculado + índices | **C** | `EligibilityCheck` = elegible | Tracking Error anualizado |
| M09 | D7, D8 | Risk | Retornos del portafolio y del benchmark | temporal | portafolio / vehículo | Mensual | No fijado (evaluar estabilidad en distintas ventanas `[QM XXII]`) | Calculado | **C** | Benchmark elegible | Beta |
| M09 | D8 | Risk | Serie de retornos + nivel de confianza + horizonte | temporal + parámetros | portafolio | Diaria en batch / on-demand `[QM II.2]` | No fijado — ES y VaR son sensibles al tamaño de muestra `[QM V]`; mínimo no especificado (ESFS-10) | Calculado + Parameter Registry (95%/99%; 1m/1a) | **C** | Muestra suficiente | VaR histórico y Expected Shortfall histórico |
| M09 | D7, D8 | Risk, Diversification | Matriz de covarianzas (con shrinkage) | numérico | asset class / vehículo | Mensual/trimestral | Derivado de la ventana de retornos | Calculado (Ledoit-Wolf, ADVANCED) | **C** para risk contribution y MVO | Retornos históricos | Contribución al riesgo; insumo de optimización |
| M09 | Alertas tempranas | Risk | Retornos + factor de decaimiento λ | temporal + parámetro | portafolio | Mensual | No fijado | Calculado | **CP** (ADVANCED) | — | EWMA — complementa, no reemplaza la σ oficial `[QM V]` |
| M09 | D7, D11 | Risk, Diversification | Retornos + índices de factores (equity, tasas, crédito, FX) | temporal | vehículo / factor | Mensual | No fijado | Proveedor de índices | **NC** (ADVANCED) | Conjunto de factores definido | Factor risk básico; detección de concentraciones factoriales ocultas |
| M09 | D8 | Risk | Curvas de tasas | temporal | mercado | Diaria — **curva completa, no puntos aislados** `[QM XVI]` | No fijado | Bancos centrales / proveedores | **C** para riesgo de tasas y escenarios | — | Sensibilidad a tasas; input de escenarios |
| M09 | Multi-moneda | Risk, Performance, Scenario | Tipos de cambio | temporal | mercado | Diaria — consistente entre todos los cálculos `[QM XVI]` | Coincidente con el período | Proveedor de mercado | **C** | — | Ajuste FX explícito; sin serie confiable → Model Block `[QM XVII]` |
| M09 | D7, D8 | Risk | Holdings subyacentes (look-through) cuando existan | estructurado | vehículo → posición subyacente | Mensual/trimestral cuando disponible `[QM XVI]` | No fijado | Gestora (transparencia variable) | **NC** — su ausencia limita factor risk, no bloquea las métricas CORE (DERIVADO de la regla 8.2) | — | Factor risk y detección de concentración con look-through |
| M09 | D7, D8 | Risk | Parámetros de riesgo para alternativos (beta y exposición factorial aproximada) | numérico | vehículo privado | Trimestral | No fijado | Alternatives Engine | **NC** | Alternatives | Traducción de alternativos a riesgo total; declarar ajuste por smoothing o su ausencia `[QM X]` |

### 9.5 — Diversification Engine

| Módulo | Decisión | Motor | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M09 | D7 | Diversification | Retornos mensuales entre activos | temporal | vehículo | Mensual | **Ventanas rolling 3-5 años** `[QM VI]` | Calculado | **C** | — | Matriz de correlación y rolling correlation |
| M09 | D7 | Diversification | Pesos por dimensión + definición de buckets | numérico + metadata | portafolio / emisor / gestor / país / factor | Mensual | — | Posiciones + taxonomía | **C** | Definición de bucket (parámetro) | HHI aplicado sobre pesos económicos, aportes al riesgo y exposición por factor — nunca solo pesos nominales `[QM VI]` |
| M09 | D7 | Diversification | Pesos + matriz de covarianzas | numérico | posición | Mensual | Derivado de la ventana | Calculado | **C** | Σ estable | Risk contribution y marginal contribution — el modelo que realmente detecta concentraciones ocultas `[QM VI]` |
| M09 | D7 | Diversification | Contribuciones al riesgo | numérico | posición | Mensual | — | Calculado | **NC** | Risk contribution | Effective Number of Bets — **definición operacional pendiente** `[QM XXIII P3]` |
| M09 | D7 | Diversification | Matriz de correlación | numérico | vehículo | Mensual/trimestral | Derivado de la ventana | Calculado | **CP** (ADVANCED) | — | Cluster analysis como diagnóstico visual, nunca como asignación de capital `[QM III.0 Rev 4]` |
| M09 | D7 | Diversification | Correlación y beta frente a índices clave | numérico | vehículo vs. índice | Mensual | No fijado | Índices | **NC** | Índices disponibles | Detección del caso "20 fondos nominalmente distintos, mismo factor subyacente" `[QM VI]` |

### 9.6 — Construction Engine

| Módulo | Decisión | Motor | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M09 | D4, D5 | Construction | Capital Market Assumptions institucionales (retornos esperados, volatilidad, correlaciones) | numérico | asset class | Trimestral/anual, versionadas | — | Comité de Inversiones — **no individuales del asesor** `[QM VII]` | **C** | Parameter Registry | MVO robusto (shrinkage + constraints) |
| M09 | D4, D5 | Construction | Inventario de productos con costos, liquidez, tracking error y capacidad | estructurado | vehículo | Ante cambios | — | Interna + gestoras | **C** | Approved List (M10) | Propuesta implementable; los portafolios estándar solo usan vehículos Approved-Active `[V2 B8]` |
| M09 | D2, meta | Construction, ClientGoal | Retornos históricos + cashflows + horizonte + número de simulaciones | temporal + parámetros | cliente / meta | On-demand / trimestral | Histórico representativo (calidad del histórico es la limitación declarada `[QM XXII]`) | Calculado + Parameter Registry (5.000-20.000 sim.) | **C** | IPS con metas cuantificables | Goal-based Monte Carlo / Block Bootstrap → probabilidad de éxito |
| M09 | D4 (avanzada) | Construction | Índices de mercado + Σ + views documentadas del CIO + τ, δ, Ω | numérico + documental | asset class | Por ciclo de Comité | — | Comité de Inversiones `[QM VIII]` | **C** para BL — **BL no se ejecuta sin views documentadas y aprobadas** `[QM XXIV]` | Pendiente institucional de activación `[QM XXIII P1]` | Expected returns posteriores (ADVANCED, condicionado) |
| M09 | D4 (comparador) | Construction | Volatilidades por asset class + target vol | numérico | asset class | Trimestral | Derivado de la ventana | Calculado | **CP** (ADVANCED) | — | Risk Parity / ERC como portafolio de referencia defensivo |
| M09 | D4, D5 | Construction | Constraints: bandas por asset class, límites de concentración, peso máximo en ilíquidos | numérico | portafolio | Revisión anual | — | Comité + IPS + Liquidity | **C** — constraints fuertes son parte del modelo CORE `[QM VII]` | Parameter Registry (bandas pendientes) | Solución interpretable y no concentrada espuriamente |

### 9.7 — Liquidity Engine y Alternatives Engine

| Módulo | Decisión | Motor | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M09 | D6, D9 | Liquidity | Calendario de flujos esperados (retiros, impuestos, capital calls, distribuciones, gastos del IPS) | evento fechado | cliente / vehículo | Por evento; revisión trimestral | No fijado | Cliente vía asesor + Alternatives | **C** | IPS | Cash flow forecasting; LCR por bucket |
| M09 | D6, D9 | Liquidity | Estructura de liquidez por vehículo | categórico | vehículo | Ante cambios | — | Reglamento / gestora | **C** — requiere clasificación correcta de cada vehículo `[QM XXII]` | Reglamento vigente | Liquidity Ladder; proporción vendible por plazo sin destrucción de valor |
| M09 | D6, D9 | Liquidity, Scenario | Escenario de estrés combinado (caída de mercado + llamadas de capital simultáneas) | estructurado | portafolio | Trimestral y ante eventos | — | Scenario Library (Comité) | **NC** (ADVANCED) | Scenario Engine | Déficit proyectado bajo estrés → alerta D6 |
| M09 | D3, D11 (privados) | Alternatives | Cashflows completos por fondo | evento fechado | vehículo privado | Por evento / trimestral | **Completos** — sin cashflows completos no se calculan métricas parciales sin advertencia `[QM XXIV]` | Gestora | **C** | — | TVPI, DPI, RVPI, IRR |
| M09 | Alternativos | Alternatives | NAV reportado del vehículo privado | temporal | vehículo privado | Trimestral | Alineado al reporting | Gestora | **C** | — | RVPI; valor residual. **Nunca tratado como precio de mercado** `[QM X]` |
| M09 | Alternativos | Alternatives | Curvas de cash flow histórico por estrategia y vintage; J-curve asumida | temporal + supuesto | estrategia / vintage | Trimestral | No fijado | Interna / gestoras | **NC** (ADVANCED) | Vintage identificado | Pacing y simulación de NAV futuro; alimenta Liquidity |
| M09 | Alternativos | Alternatives, Benchmark | Índice público comparable | temporal | mercado | Diaria | Coincidente con los cashflows | Proveedor de índices | **NC** (ADVANCED) | `EligibilityCheck` | PME / Direct Alpha |
| M09 | Alternativos | Alternatives | Métricas de private credit (default rate, recovery, LGD, yield, spread, duration, liquidez) | numérico | fondo | Trimestral | No fijado | Gestora | **NC** | — | Evaluación agregada a nivel de fondo — AFI no opera a nivel de préstamo individual `[QM X]` |
| M09 | Alternativos | Alternatives | Métricas de real estate/infra (cap rate, NOI, LTV, DSCR, IRR, equity multiple) | numérico | fondo consolidado | Trimestral | No fijado | Gestora | **NC** | — | Evaluación a nivel de fondo, no de activo único `[QM X]` |

### 9.8 — Benchmark, Scenario, Monitoring y ClientGoal

| Módulo | Decisión | Motor | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M09 | D10 | Benchmark | Definición del portafolio y del benchmark candidato en las ocho dimensiones (objetivo, asset allocation, riesgo, moneda, liquidez, horizonte, costos, restricciones) | estructurado | portafolio + benchmark | Revisión anual de la definición; consulta on-demand | — | Índices + interna + reglamento | **C** — si falta información para verificar una dimensión, esa dimensión se marca **no verificable**; no se asume comparabilidad `[QM XXIV]` | — | Estado elegible / no elegible / parcial; gate de toda comparación relativa |
| M09 | D10 | Benchmark | Excepción documentada del Comité | documental | benchmark + uso | Por evento | — | Investment Committee | **CP** | — | Uso acotado y documentado, nunca general `[QM XVIII D10]` |
| M09 | D13 | Scenario | Movimientos observados de índices y tasas en episodios históricos | temporal | mercado | Por episodio | El episodio completo | Proveedores + Scenario Library | **C** | — | Historical Simulation |
| M09 | D13 | Scenario | Shocks hipotéticos definidos por el Comité | estructurado versionado | mercado / factor | Trimestral y ante cambio de régimen | — | Investment Committee | **C** | Scenario Library | Hypothetical Stress |
| M09 | D13 | Scenario | Portafolio actual + límites institucionales | numérico | portafolio | On-demand | — | Portfolio State + Parameter Registry | **NC** (ADVANCED) | Definición de "ruptura" de límite | Reverse Stress Testing |
| M09 | D13 | Scenario | Mapeo escenario → factores de riesgo | metadata | factor | Ante cambios | — | Interna | **C** | Factor risk | Impacto proyectado en las cinco dimensiones: retorno, riesgo, liquidez, concentración y objetivos `[QM XI]` |
| M09 | D11, D12 | Monitoring | Resultados consolidados de los demás motores | estructurado | cliente / book | Diaria/semanal | — | Motores | **C** | ≥2-3 motores operativos `[QM II.8]` | Lista priorizada de cuentas; heatmap; watchlist |
| M09 | D11 | Monitoring | Triggers configurados (cuantitativos y cualitativos) | parámetros + reglas | motor / dimensión | Ante cambios | — | Parameter Registry (valores pendientes) | **C** | Umbrales heredados de cada motor fuente | Watchlist automática ante combinación de triggers `[QM XVIII D11]` |
| M09 | D11 | Monitoring + M10 | Señales cualitativas: style drift, team drift, process drift, capacity drift, liquidity deterioration, fee changes, cambios de propiedad | categórico + evento | gestor / vehículo | Por evento | — | M10 (IDD/ODD) `[V2 B7]` | **C** para D11 | M10 operativo | Clasificación de causa raíz: cíclico/temporal · estructural · operacional/integridad |
| M09 | D2 | ClientGoal | IPS + life balance sheet + resultados de Monte Carlo goal-based | estructurado | cliente / meta | Trimestral; revisión completa ante eventos de vida | — | M03 + Construction/Scenario | **C** — ninguna meta se evalúa sin IPS vigente `[QM XXIV]` | Construction, Scenario | Probabilidad de éxito por meta; dashboard de cliente simplificado |

### 9.9 — Manager Due Diligence & Approved List (M10)

| Módulo | Decisión | Motor/Módulo | Input | Tipo | Granularidad | Frecuencia | Histórico requerido | Fuente | Crit. | Dependencia | Output habilitado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M10 | D14 | IDD | DDQ de inversión, descripción de estrategia, políticas internas, atribución histórica, análisis por régimen | documental + numérico | gestor / vehículo | Alta + revisión anual `[V2 B8]` | No fijado | Gestora | **C** | — | Rating IDD; mapa de consistencia proceso-atribución `[V2 B11]` |
| M10 | D14 | ODD | DDQ operacional, proveedores de servicios, auditorías, políticas de valuación, informes regulatorios | documental | gestor / vehículo | Alta + revisión anual + eventos | No fijado | Gestora / regulador / auditor | **C** — **poder de veto:** ODD Fail/High-Risk ⇒ vehículo inelegible con independencia del IDD `[V2 B11 P1]` | — | Estado de elegibilidad institucional del vehículo |
| M10 | D3, D4, D5 | M10 | Estado en Approved List (Approved-Active / Watchlist / Restricted / Removed) | categórico | vehículo | Ante cambios | Historial de estados | Investment Committee | **C** | IDD + ODD | Admisibilidad del vehículo en propuestas de portafolio |
| M10 | D3, D4, D5 | M10 | Memo de recomendación con proceso, equipo y ODD | documental | vehículo | Por evento | — | Analista + Comité | **C** — ningún cambio se basa solo en performance reciente `[QM XVIII D3]` | — | Habilita (o bloquea) Nivel 3 en decisiones de fondo — ver Parte 15.4 |
| M10 | D14 | M10 | Factsheet vigente y reglamento/prospecto | documental | vehículo | Ante cambios materiales | Versión vigente **antes de aprobar el vehículo** `[QM XVI]` | Gestora / regulador | **C** | — | Verificación de universo, restricciones y consistencia factsheet-reglamento |
| M10 | D14 | M10 | Excepción off-list documentada | documental | cliente + vehículo | Por evento | — | Comité + disclosure al cliente `[V2 B8]` | **CP** | — | Uso excepcional justificado y auditable |

### 9.10 — Módulos transversales

| Módulo | Decisión | Input | Tipo | Granularidad | Frecuencia | Fuente | Crit. | Output habilitado |
|---|---|---|---|---|---|---|---|---|
| M17 Audit Log | Todas | Datos utilizados (serie, versión y fecha de extracción), fecha de cálculo, modelo y versión, parámetros exactos, resultado completo, regla activada, alternativas presentadas, decisión del ejecutivo, override, justificación, fecha de próxima revisión | estructurado | por output | Por cálculo | Sistema `[QM XXI]` | **C** — un output sin este registro no es un output válido | Reconstrucción total de cualquier recomendación |
| M18 Decision History | Todas | Situación, datos, análisis, alternativas, recomendación, decisión, resultado posterior | estructurado | por `DecisionCase` | Por caso | Sistema + WM `[DF 6.5]` | **C** | Learning Loop; Rebalancing History View |
| M22 Parameter Registry | Todas | Parámetro, categoría, valor, versión, vigencia, propuesto por, aprobado por, justificación | estructurado | por parámetro | Ante cambios | `[QM XV]` | **C** | Auditoría de parámetros; configurabilidad desde Fase 0 |
| M23 Model Governance | D15 | Clasificación del modelo, responsable institucional, fecha de última validación, resultados de backtesting / sensitivity / parameter stability / out-of-sample, estado de degradación | estructurado | por modelo | Anual mínimo `[QM XIV]` | Comité de Model Risk | **C** | Habilitación o degradación de modelos; bloqueo de motores con modelo no vigente (DERIVADO) |

### 9.11 — Lectura consolidada: los datos que bloquean más funcionalidad

Conteo de cuántas métricas quedan bloqueadas si el dato no existe (derivado de las tablas anteriores). Esta es la base de la Parte 29.

| Dato | Métricas/motores que bloquea | Fuente del dato |
|---|---|---|
| Serie de NAV con frecuencia nativa | Performance completo, Risk completo, Diversification, Alternatives (RVPI) | Custodio / administrador |
| Cash flows fechados y clasificados | TWR, MWR, Liquidity, Alternatives | Custodio / gestora |
| IPS vigente | ClientGoal, Construction, y el juicio de compatibilidad de todo output `[QM I.1]` | Asesor + Cliente |
| Serie FX | Todo cálculo multi-moneda (Model Block) `[QM XVII]` | Proveedor de mercado |
| Benchmark + EligibilityCheck | Excess Return, TE, Beta, IR, atribución, comparación relativa | Índices + Benchmark Engine |
| SAA vigente y bandas | Drift, materialidad, D1 completo | Comité de Inversiones |
| Clasificación de liquidez por vehículo | LCR, Ladder, límite de ilíquidos | Reglamento / gestora |
| Estado en Approved List + ODD | D3, D4, D5, D14 y Nivel 3 en decisiones de fondo | M10 |

---

## 10. Functional Modules

Especificación funcional de los módulos que no son motores. Los diez motores están en la Parte 11.

### 10.1 — M01 Decision Intake

| Campo | Contenido |
|---|---|
| **Propósito** | Convertir una necesidad expresada por el WM o el cliente en un `DecisionCase` estructurado. Es el punto donde se aplica el principio Client-First: el sistema no pregunta qué indicadores puede calcular, pregunta qué decisión hay que apoyar `[DF 6.2]` |
| **Inputs** | Pregunta en lenguaje del WM; cliente/portafolio/vehículo/gestor de referencia; urgencia o evento disparador |
| **Procesamiento** | Clasificar la pregunta contra el catálogo de dieciocho casos de uso `[DF 7.3]` y la Decision Library (D1-D15) `[DF 5]`; declarar unidad de análisis y horizontes |
| **Outputs** | `DecisionCase` en estado `New` |
| **Condiciones de bloqueo** | Pregunta no mapeable → estado `unmapped_question`, que se registra y se eleva como caso a revisar, nunca se fuerza a un flujo aproximado (DERIVADO de `[QM I.8]`) |
| **Errores posibles** | Unidad de análisis ambigua; cliente inexistente; pregunta que mezcla dos decisiones (se divide en dos casos) |
| **Nota de diseño** | La clasificación es por reglas, no por modelo de lenguaje: el producto no incorpora LLM `[QM 0]` `[QM XIX]`. Si AFI quisiera asistencia de lenguaje en el intake, sería una herramienta externa al sistema y su output tendría que ser confirmado por el WM antes de crear el caso |

### 10.2 — M03 Client / Investor Profile

| Campo | Contenido |
|---|---|
| **Propósito** | Mantener el IPS como referencia central de todos los motores `[QM I.1]` `[V1 P1]` |
| **Información necesaria (C)** | IPS vigente y firmado; objetivos cuantificados; horizonte(s); límites de riesgo por perfil; necesidades de liquidez; moneda base |
| **Información opcional (NC/CP)** | Life balance sheet completo (C solo para el límite de ilíquidos `[QM IX]`); restricciones ESG (alcance pendiente `[QM XXIII P6]`); preferencias de comunicación (parámetro del WM `[QM XV]`) |
| **Reglas** | Ninguna meta se evalúa sin IPS vigente `[QM XXIV]`. Todo cálculo de probabilidad de meta registra la versión de IPS usada `[QM XXIV]` |
| **Outputs** | `ips_ref` obligatorio para todo `MotorResultado`; conjunto de constraints para Construction |
| **Estados** | `vigente` · `vencido` · `en revisión` · `incompleto` |
| **Efecto de la ausencia** | Sin IPS vigente el sistema no se detiene por completo: analiza lo que puede (Client-First `[DF 6.2]`) y declara que Nivel 3 no es alcanzable para decisiones que dependen de objetivos (DERIVADO de `[DF 2.4]`, que usa exactamente este ejemplo) |

### 10.3 — M04 Portfolio State

| Campo | Contenido |
|---|---|
| **Propósito** | Representar el estado actual y la evolución del portafolio: posiciones, pesos, asset classes, vehículos, monedas, liquidez, exposición e histórico |
| **Inputs** | Posiciones del custodio; mapeo a taxonomía institucional; clasificación de liquidez del vehículo; SAA vigente y bandas |
| **Procesamiento** | Consolidación multi-cuenta y multi-moneda; agregación jerárquica; cálculo de pesos; reconciliación con la fuente cuando sea posible `[QM XVI]` |
| **Outputs** | Estado a fecha; serie histórica de composición; drift respecto de la SAA |
| **Frecuencia** | Diaria para vehículos líquidos; mensual/trimestral donde la frecuencia nativa lo imponga; **la comparación entre vehículos se hace siempre a la frecuencia más baja común** `[QM IV]` |
| **Condiciones de bloqueo** | Posiciones sin mapeo de asset class (bloquea HHI y agregación); moneda sin serie FX (Model Block) |

### 10.4 — M08 Data Completeness Gate

| Campo | Contenido |
|---|---|
| **Propósito** | Determinar, antes de calcular, qué está disponible, qué falta, qué es crítico, qué indicadores quedan bloqueados y qué indicadores continúan con advertencia `[DF 6.1]` |
| **Inputs** | `AnalysisPlan` + `DataRequirementSet` (M07) + estado real de los datos (8.5) |
| **Procesamiento** | Por cada dato requerido: resolver estado → aplicar la regla de criticidad (8.2) → emitir comportamiento BLOCK / WARNING / CONTINUE |
| **Outputs** | `CompletenessReport`: lista de datos con estado, criticidad, comportamiento y **texto de declaración** de qué falta y por qué bloquea |
| **Reglas absolutas** | Nunca imputa silenciosamente. Nunca presenta un análisis como completo si existen limitaciones materiales no declaradas `[DF 6.1]` |
| **Dependencia crítica** | El umbral de "gap significativo" no existe en las fuentes (ESFS-09): sin él, el Gate opera en modo binario (dato presente / ausente) y toda tolerancia intermedia queda como decisión pendiente del equipo de datos `[QM XXIII P2]` |

### 10.5 — M15 Explanation Layer

| Campo | Contenido |
|---|---|
| **Propósito** | Producir la explicación determinística de cualquier resultado: regla fija → plantilla parametrizada → mensaje `[QM XIX]` |
| **Procesamiento** | `Resultado numérico → Regla de clasificación (umbral fijo, documentado, versionado) → Plantilla de narrativa parametrizada → Mensaje final` |
| **Qué debe mostrar toda explicación** | Qué ocurrió (resultado numérico) · por qué ocurrió (la regla o umbral que se activó) · qué regla se activó (trazable al documento que la define) · qué evidencia existe (los datos de entrada exactos) · qué alternativas existen cuando la decisión lo amerita `[QM XIX]` |
| **Estratificación por stakeholder** | Plantillas distintas con distinto nivel de detalle numérico expuesto — **mismo cálculo, mismo número, distinto vocabulario**: WM (resultado + driver + regla + alternativas, con acceso a la fórmula si la solicita) · Comité (consistencia con políticas, límites, concentración sistémica, excepciones y approved list) · Cliente (progreso hacia metas, sin tecnicismos) `[QM XIX]` |
| **Prohibiciones** | Sin SHAP, sin LIME, sin generación de lenguaje libre `[QM XIX]` `[QM III.0 Rev 1-2]` |
| **Criterio de aceptación** | Ejecutar el mismo cálculo dos veces con los mismos datos produce exactamente la misma explicación `[QM XIX]` |
| **Nota de secuencia** | No es una fase posterior del roadmap: se construye junto con cada motor desde Fase 1, porque un motor sin su capa de explicación determinística no es un motor completo `[QM ROADMAP]` |

### 10.6 — M10 Manager Due Diligence & Approved List

| Campo | Contenido |
|---|---|
| **Propósito** | Determinar si un gestor o vehículo es institucionalmente elegible antes de considerarlo para portafolios `[V2 B11 P1]` |
| **Proceso de incorporación** | Universo → screening cuantitativo → DDQ → reuniones → ODD on-site/virtual → informe integrado IDD+ODD → comité de rating → inclusión en Approved List con rating interno `[V2 B8]` `[QM XVIII D14]` |
| **Regla de veto** | `ODD_rating ∈ {Fail, High-Risk} ⇒ Vehicle_status = Ineligible`, con independencia del rating IDD `[V2 B11 P1]` |
| **Estados del vehículo** | Approved-Active · Watchlist · Restricted · Removed `[QM XVIII D3]`; Vol II añade Proposed y Exception `[V2 B11 P6]` — ver ESFS-05 sobre la reconciliación de ambas listas |
| **Regla de uso** | Los portafolios estándar solo pueden usar vehículos Approved-Active; las excepciones requieren justificación escrita, aprobación de Comité y disclosure al cliente `[V2 B8, B11 P6]` |
| **Regla anti performance-chasing** | Bloqueo de recomendación si el memo no incluye análisis de proceso, equipo y ODD `[V2 B11 P4]` `[QM XVIII D3]` |
| **Señales tempranas de deterioro** | Style drift · team drift · process drift · capacity drift · liquidity deterioration · fee changes · cambios de propiedad `[QM XVIII D11]` `[V2 B7]` |
| **Clasificación de causa raíz** | Cíclico/temporal (mantener con vigilancia) · estructural (considerar eliminación) · operacional/integridad (prioridad alta, normalmente salida) `[V2 B7]` |
| **OPEN ISSUE** | ESFS-04: este módulo es obligatorio pero no es uno de los diez motores; su ubicación arquitectónica (motor, módulo de flujo o registro con reglas) no está definida en las fuentes |

### 10.7 — M19 Tracking & Monitoring Views

| Campo | Contenido |
|---|---|
| **Propósito** | Seguimiento de portafolios, de recomendaciones, de decisiones, de evolución de indicadores y de la comparación entre expectativa y resultado `[DF 6.5]` |
| **Inputs** | `MotorResultado` históricos; `Decision` registradas; alertas del Monitoring Engine |
| **Outputs** | Evolución de indicadores por entidad; estado de cada recomendación emitida (aceptada / rechazada / modificada / pendiente); comparación expectativa vs. resultado observado |
| **Regla** | La comparación expectativa-resultado alimenta el Learning Loop institucional, no un modelo de aprendizaje automático `[DF 6.5]` |

### 10.8 — M25 Governance & Escalation Interface

| Campo | Contenido |
|---|---|
| **Propósito** | Entregar el Analytical Output a la capa de gobernanza institucional sin determinar la instancia resolutoria `[DF 3.1]` |
| **Contrato de entrada** | `AnalyticalOutput` completo: evidencia, magnitud, impacto, alternativas, recomendación si corresponde, limitaciones, datos faltantes |
| **Contrato de salida** | Identificación de la decisión y del caso; nada más. El sistema se detiene aquí `[DF 3.1]` |
| **Reglas internas** | **Vacías por diseño.** No dice "esto es Comité", no dice "esto requiere Senior", y con la misma disciplina tampoco asume que "esto puede decidirlo el WM solo" `[DF 3.1]` |
| **Excepción declarada** | D15 (Model Governance) sí tiene instancia fija: Comité de Model Risk. No es una excepción al principio, es gobernanza de otra naturaleza `[DF 3.2, 3.3]` |
| **OPEN ISSUE** | ESFS-21: las reglas de asignación son decisión institucional de AFI `[DF 8.3 OQ1]` |

---

## 11. Quantitative Engine Mapping

Los diez motores de `[QM II]` y `[QM XXIV]`, sin agregar ninguno. Para cada uno: propósito, inputs, procesamiento, outputs, dependencias, frecuencia, condiciones de activación, condiciones de bloqueo y errores posibles.

### 11.0 — Frontera común a los diez motores

```
INPUTS → CALCULATIONS → METRICS → DIAGNOSTICS → WARNINGS
```

Ningún motor produce una instrucción de acción como parte de su output `[DF 2.1]`. El Risk Engine puede decir que el drawdown esperado aumenta; no puede decir que debe venderse el fondo — eso es resultado de la Decision Library, nunca de un motor.

| Motor | Calcula | Diagnostica | Decide | Orquesta |
|---|---|---|---|---|
| `AFI.Performance.Engine` | Sí | Sí | No | No |
| `AFI.Risk.Engine` | Sí | Sí | No | No |
| `AFI.Diversification.Engine` | Sí | Sí | No | No |
| `AFI.Liquidity.Engine` | Sí | Sí | No | No |
| `AFI.Benchmark.Engine` | Sí | Sí | No | No |
| `AFI.Scenario.Engine` | Sí | Sí | No | No |
| `AFI.Construction.Engine` | Sí | Sí | No | No |
| `AFI.Alternatives.Engine` | Sí | Sí | No | No |
| `AFI.ClientGoal.Engine` | Sí | Sí | No | No |
| `AFI.Monitoring.Engine` | Sí (agregación) | Sí | No | No — prioriza entre cuentas, nunca colapsa las dimensiones de un mismo cliente en un score |

### 11.1 — `AFI.Performance.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Evaluación robusta, multi-nivel y explicable de performance por cliente, asset class, gestor y vehículo, alineada a GIPS `[QM II.1]` |
| Inputs | NAV, flujos fechados y clasificados, benchmarks elegibles, metadatos de jerarquía |
| Procesamiento CORE | TWR geométricamente encadenado; MWR/IRR (XIRR); CAGR; Excess Return `[QM IV]` |
| Procesamiento ADVANCED | Brinson-Fachler; atribución por factores; TWR trimestral para privados |
| Outputs | Cuadros multi-periodo (YTD, 1-3-5-10 años, desde inicio); atribución jerárquica; hit ratio vs. benchmark; rolling returns |
| Dependencias | Benchmark Engine (gate); Construction Engine (separar asignación de selección) |
| Frecuencia | Diaria/mensual para posiciones y TWR; consolidación mensual y trimestral |
| Activación | Casos 2, 4, 6, 9, 18; flujos Performance, Portfolio Diagnostic, Deterioration, Opportunity |
| Bloqueo | `insufficient_data` si los flujos no están correctamente fechados o clasificados `[QM XXIV]`; Excess Return bloqueado si el benchmark no es elegible |
| Errores posibles | Frecuencia mixta sin agregar a la más baja común; flujos duplicados o no clasificados; comparación de vehículos con distinta frecuencia de valorización sin ajuste por smoothing |
| Regla de frecuencia | La frecuencia de comparación es la frecuencia nativa más baja común entre los vehículos comparados `[QM XXIV]` |

### 11.2 — `AFI.Risk.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Medir y descomponer el riesgo de portafolios multi-asset, incluyendo alternativos, de forma granular y accionable `[QM II.2]` |
| Inputs | Posiciones detalladas, curvas de mercado (tasas, spreads, FX, volatilidad implícita), matriz de covarianzas con shrinkage, parámetros de riesgo para alternativos |
| Procesamiento CORE | Volatilidad histórica; downside deviation; maximum drawdown; tracking error; beta; VaR histórico; ES histórico `[QM V]` |
| Procesamiento ADVANCED | VaR/ES paramétrico como cross-check; EWMA para alertas; factor risk básico |
| Excluido | GARCH — RESEARCH, impracticable con NAV mensual/trimestral `[QM III.0 Rev 3]` |
| Outputs | Tableros de riesgo por portafolio, cliente y book; mapas de contribución al riesgo por dimensión; panel de riesgo de cola |
| Dependencias | Scenario Engine (shocks); Liquidity Engine (riesgo de liquidez); Benchmark Engine (TE, beta) |
| Frecuencia | Cálculo diario en batch; capacidad on-demand para análisis ad-hoc del Comité |
| Activación | Casos 4, 5, 6, 9, 12, 13, 17, 18 |
| Bloqueo | `insufficient_data` si la muestra es menor al mínimo definido por modelo (ejemplo de la fuente: menos de 36 observaciones mensuales para TE) `[QM XXIV]`; mínimos de VaR/ES no fijados (ESFS-10) |
| Reglas | Violación de límite de perfil → alerta, **sin ajuste automático del portafolio** `[QM XXIV]`. Todo cálculo que incluya vehículos privados declara el ajuste por smoothing o su ausencia `[QM X]` |
| Errores posibles | Combinar NAV privado trimestral con NAV diario sin ajuste; usar una sola ventana y subestimar el riesgo (beta variable en el tiempo) |

### 11.3 — `AFI.Diversification.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Cuantificar diversificación real, no aparente: cuántas fuentes de riesgo genuinamente distintas componen el portafolio `[QM II.3, VI]` |
| Inputs | Matrices de correlación y covarianza; pesos actuales y objetivo por asset class, factor, estilo y liquidez |
| Procesamiento CORE | Correlation matrix + rolling correlation (3-5 años); HHI sobre tres dimensiones (peso económico, aporte al riesgo, exposición factorial); risk contribution y marginal contribution |
| Procesamiento ADVANCED | Shrinkage (Ledoit-Wolf); cluster analysis y effective number of bets |
| Excluido | HRP como constructor de portafolios — RESEARCH `[QM III.0 Rev 4]` |
| Secuencia de detección de concentración oculta | 1) HHI nominal → 2) correlación y beta frente a índices clave → 3) risk contribution → 4) cluster analysis (ADVANCED) → 5) effective number of bets. Ningún paso reemplaza al anterior; se reportan en conjunto `[QM VI]` |
| Outputs | Índices de diversificación por portafolio vs. modelo; identificación de la dimensión específica de concentración, no solo su existencia `[QM XVIII D7]` |
| Dependencias | Risk Engine (matriz de covarianzas compartida); Construction Engine (simulación what-if) |
| Frecuencia | Mensual/trimestral, alineado a revisiones de portafolio |
| Bloqueo | `insufficient_data` si la ventana de correlación no tiene suficientes observaciones `[QM XXIV]` — mínimo no fijado (ESFS-10) |
| Errores posibles | HHI sensible a la definición de buckets; correlaciones inestables que suben en crisis; Effective Number of Bets con definición operacional pendiente `[QM XXIII P3]` |

### 11.4 — `AFI.Construction.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Producir propuestas de portafolio consistentes con el IPS, la filosofía institucional y las restricciones prácticas de implementación `[QM II.4]` |
| Inputs | IPS; CMAs institucionales; inventario de productos con costos, liquidez, TE y capacidad; Σ con shrinkage; constraints |
| Procesamiento CORE | MVO robusto (shrinkage + constraints fuertes); Goal-Based Monte Carlo `[QM VII]` |
| Procesamiento ADVANCED | Black-Litterman (condicionado, no activable aún `[QM XXIII P1]`); Risk Parity / ERC como comparador |
| Excluido | Bayesian Optimization — RESEARCH; optimización no lineal no interpretable — REJECTED `[QM III.1]` |
| Outputs | Propuesta de portafolio objetivo (pesos, vehículos, buckets de liquidez); métricas esperadas; sensibilidades |
| Regla de acompañamiento | Ningún output es un número aislado: todo peso llega acompañado de su relación con objetivos, riesgo, liquidez, horizonte, restricciones, comportamiento e incertidumbre — las siete referencias `[QM VII]` |
| Dependencias | Risk, Diversification, Liquidity, Benchmark; Approved List (M10) para admisibilidad de vehículos |
| Frecuencia | Trimestral/anual para revisión formal; on-demand para simulación |
| Bloqueo | `insufficient_data` si el IPS no está completo o vigente `[QM XXIV]`; **BL no se ejecuta sin views documentadas y aprobadas por Comité** `[QM XXIV]` |
| Errores posibles | Sensibilidad a errores de estimación de retornos esperados sin constraints fuertes; concentración espuria; CMAs individuales del asesor en lugar de institucionales (prohibido `[QM VII]`) |

### 11.5 — `AFI.Liquidity.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Asegurar que el patrimonio puede cumplir sus obligaciones de liquidez bajo escenarios adversos sin comprometer el objetivo estratégico `[QM II.5]` |
| Inputs | Calendario de flujos esperados (retiros, impuestos, capital calls, distribuciones, gastos del IPS); estructura de liquidez de cada vehículo; escenarios de estrés |
| Procesamiento CORE | Liquidity Coverage Ratio por bucket (0-3m, 3-12m, >12m); Liquidity Ladder / cash flow matching |
| Procesamiento ADVANCED | Stress liquidity: caída de mercado simultánea con llamadas de capital — el caso más peligroso `[QM IX]` |
| Outputs | Mapas de liquidez por horizonte; alertas de déficit potencial; opciones de reasignación líquido↔ilíquido |
| Reglas CORE | El peso en ilíquidos no puede exceder un límite definido como función del **life balance sheet completo**, no solo del portafolio financiero visible `[QM IX]` `[V1 P2]`. El colchón se dimensiona bajo escenarios razonables de estrés, no solo bajo el escenario central `[QM IX]` |
| Dependencias | Alternatives Engine (consume curvas de capital calls y distribuciones, **no las recalcula** `[QM IX]`); Scenario Engine |
| Frecuencia | Trimestral, y ante eventos de cliente o de mercado |
| Bloqueo | `insufficient_data` si un vehículo privado no reporta historial de cash flow suficiente `[QM XXIV]` |
| Errores posibles | Clasificación incorrecta de liquidez de un vehículo; estimación de flujos del cliente incierta (limitación declarada `[QM II.5]`) |

### 11.6 — `AFI.Alternatives.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Gestionar cuantitativamente asignación, diversificación y pacing en PE, private credit, real estate, infraestructura, VC y hedge funds `[QM II.6]` |
| Inputs | Cashflows históricos por fondo y vintage; NAV reportado; curvas de J-curve por estrategia; supuestos de retorno y beta |
| Procesamiento CORE | TVPI, DPI, RVPI, IRR (si hay cashflows completos) |
| Procesamiento ADVANCED | PME, Direct Alpha; vintage analysis; pacing y simulación de NAV futuro |
| Outputs | Tres formatos de consumo obligatorios: perfil de cash flow → Liquidity; beta y exposición factorial aproximada → Risk; contribución al retorno esperado → Construction `[QM X]` |
| Regla absoluta | **El NAV privado no se trata como equivalente a un precio de mercado** `[QM X]`; las valuaciones trimestrales introducen smoothing que subestima la volatilidad y sobreestima la correlación con activos líquidos si no se ajusta |
| Dependencias | Alimenta a Liquidity y Risk |
| Frecuencia | Trimestral, alineado al reporting de NAV de los fondos |
| Bloqueo | `insufficient_data` si el fondo no reporta cashflows completos — **no se calculan métricas parciales sin advertencia** `[QM XXIV]` |
| Errores posibles | Comparar contra índice público sin verificar elegibilidad (PME); vintage mal identificado |

### 11.7 — `AFI.Scenario.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Evaluar "qué pasaría si" bajo shocks de mercado, macro y eventos extremos `[QM II.7]` |
| Inputs | Librería de escenarios históricos e hipotéticos versionada; mapeo a factores de riesgo; portafolio actual; límites institucionales (para reverse) |
| Procesamiento CORE | Historical Simulation; Hypothetical Stress (shocks definidos por el Comité); Monte Carlo / Block Bootstrap |
| Procesamiento ADVANCED | Reverse Stress Testing |
| Excluido | Regime Switching / fat tails — RESEARCH `[QM XI]` |
| Regla de reporte | **Todo escenario reporta impacto en las cinco dimensiones**, nunca solo en retorno: retorno, riesgo, liquidez, concentración y objetivos del cliente `[QM XI]` `[QM XXIV]`. La moneda es una dimensión transversal dentro de riesgo y el componente FX se simula explícitamente, sin asumir cobertura implícita `[QM XI]` |
| Combinación recomendada | Historical (credibilidad) + Hypothetical (relevancia futura) + Reverse (fragilidades estructurales) — los tres, porque cada uno responde una pregunta distinta `[QM XI]` |
| Dependencias | Risk, Liquidity, Construction |
| Frecuencia | Trimestral, y ante señales de régimen cambiante |
| Bloqueo | Los escenarios son hipotéticos por diseño y no dependen de completitud de datos en el mismo sentido que otros motores `[QM XXIV]`; sí dependen del portafolio actual y del mapeo a factores |
| Errores posibles | Escenario sin definición versionada (rompe auditabilidad); reverse stress sin definición clara de "ruptura" de límite |

### 11.8 — `AFI.Monitoring.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Vista consolidada de book of business con alertas de riesgo, performance, liquidez y cumplimiento de IPS; responder en qué cuentas debe actuar el asesor hoy `[QM II.8]` |
| Inputs | Resultados consolidados de todos los demás motores; triggers configurados; señales cualitativas de M10 |
| Procesamiento | Reglas de triggers cuantitativos y cualitativos. **No introduce modelos matemáticos propios** — orquesta los de otros motores `[QM II.8]` |
| Outputs | Lista priorizada de cuentas; heatmap de desviaciones; panel de watchlist |
| Restricción crítica | **Prioriza entre cuentas, nunca colapsa las dimensiones de un mismo cliente en un score** `[DF 2.1]` — ver OPEN ISSUE ESFS-02 sobre la enumeración de esas dimensiones |
| Dependencias | Todos los motores; no tiene sentido con menos de dos o tres motores fuente operativos `[QM ROADMAP F3]` |
| Frecuencia | Diaria/semanal |
| Manejo de degradación | Si un motor fuente está en `insufficient_data`, ese componente **se excluye de la priorización con nota explícita, no se omite silenciosamente** `[QM XXIV]` |
| Errores posibles | Su calidad depende enteramente de la calidad de los triggers definidos en cada motor subyacente `[QM II.8]`; con umbrales pendientes de calibración, la priorización es provisional |

### 11.9 — `AFI.Benchmark.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Definir y mantener benchmarks de política y actuar como gate de elegibilidad antes de cualquier comparación `[QM II.9]` |
| Inputs | Definición de universo, riesgo, moneda, liquidez, horizonte, costos, objetivo y restricciones — del portafolio y del benchmark candidato |
| Procesamiento | AFI Benchmark Eligibility Framework: verificación de las ocho dimensiones. Es una regla de verificación, no un modelo matemático `[QM XII]` |
| Outputs | Estado elegible / no elegible / parcial, con el detalle de qué dimensión falló |
| Regla | Benchmark no elegible → **no se genera ranking**; solo diferencias cualitativas descriptivas `[QM XII]` `[QM I.7]` |
| Tipos | Market · Strategic/Policy · Custom · Peer (solo con comparabilidad demostrada en las ocho dimensiones) |
| Caso AFP | Un cliente con exposición relevante a alternativos e ilíquidos no es comparable contra una AFP con regulación de inversión distinta, sin estructura de liquidez equivalente y con objetivo previsional, salvo verificación y documentación explícita de las ocho dimensiones `[QM XII]` |
| Dependencias | Consumido por Performance y Risk |
| Frecuencia | Revisión anual de la definición; consulta on-demand |
| Manejo de faltantes | Si falta información para verificar una dimensión, esa dimensión se marca "no verificable" — **no se asume comparabilidad por defecto** `[QM XXIV]` |
| Gobernanza | El gate es automático porque es una verificación técnica de comparabilidad, no una decisión sobre el patrimonio `[DF 6.3]`. La excepción para un uso acotado la documenta el Comité `[QM XVIII D10]` |
| OPEN ISSUE | ESFS-14: qué dimensiones son "críticas" no está enumerado de forma cerrada, y la semántica operativa del estado "parcial" no está definida |

### 11.10 — `AFI.ClientGoal.Engine`

| Campo | Especificación |
|---|---|
| Propósito | Consolidar objetivos, restricciones y probabilidad de éxito del cliente como referencia central de todos los demás motores `[QM II.10]` |
| Inputs | IPS; life balance sheet; resultados de Monte Carlo goal-based |
| Procesamiento | Comparte la metodología de Monte Carlo / Block Bootstrap con el Scenario Engine, aplicada a la probabilidad de una meta específica. **No introduce modelos de mercado propios** `[QM XXIV]` |
| Outputs | Probabilidad de éxito por meta; dashboard de cliente simplificado |
| Reglas | Ninguna meta se evalúa sin un IPS vigente como input `[QM XXIV]` |
| Alertas | Probabilidad de éxito cae bajo umbral institucional — umbral pendiente de valor (M22) |
| Dependencias | Construction y Scenario (inputs de retorno/riesgo proyectado) |
| Frecuencia | Actualización trimestral; revisión completa ante eventos de vida del cliente |
| Bloqueo | `insufficient_data` si el IPS no está vigente o no tiene metas cuantificables `[QM XXIV]` |
| Nota de secuencia | Depende de que exista primero un proceso de IPS estructurado en AFI — es dependencia técnica y organizacional a la vez `[QM ROADMAP F5]` `[QM XXIII P5]` |

### 11.11 — Sobre el "Motor de Rebalanceo"

`[QM XIII]` especifica una metodología completa de rebalanceo bajo el título "Rebalancing Engine", pero la lista canónica de motores `[DF 2.1]` tiene exactamente diez y no lo incluye; `[DF 6.4]` y `[DF 7.1]` lo tratan como un **flujo** que activa Construction + Risk + Liquidity + Scenario.

**Tratamiento en ESFS-01:** se implementa como flujo (no como motor número once), porque crear un motor nuevo está explícitamente prohibido `[DF 20]` y porque la secuencia de `[DF 6.4]` no introduce ninguna fórmula que no pertenezca a los cuatro motores nombrados. Esta lectura se registra como **OPEN ISSUE ESFS-03** y no como decisión cerrada: si AFI considera que el rebalanceo debe tener identidad de módulo propio (con su propio registro de triggers, su propio estado y su propia vista histórica `[DF 6.6]`), esa es una decisión de arquitectura que corresponde a AFI, no a este documento.

Lo que el flujo de rebalanceo **hace**: detectar drift de forma sistemática; cuantificar las consecuencias de no actuar (impacto en riesgo, no solo el porcentaje de desviación); simular 2-3 alternativas; mostrar costos de transacción y consideraciones fiscales; mostrar impactos proyectados en riesgo y en probabilidad de meta; presentar opciones `[QM XIII]`.

Lo que **no hace**: ejecutar operaciones. No es una limitación técnica temporal, es una posición institucional permanente `[QM XIII]`.

Tipos de trigger: Calendar-Based (CORE) · Threshold-Based por bandas (CORE) · Risk/Volatility-Based (ADVANCED) · Liquidity-Based (no es trigger independiente: es una restricción que se aplica sobre cualquier propuesta) `[QM XIII]`.

---

## 12. Diagnostic Synthesis

### 12.1 — Contrato funcional

| Campo | Contenido |
|---|---|
| **Propósito** | Integrar los resultados de los motores activados en un diagnóstico legible, sin convertirse en una caja negra |
| **Inputs** | `EngineResult` de cada motor activado; `CompletenessReport`; `AnalysisPlan` (secuencia de integración) |
| **Procesamiento** | Ensamblar por horizonte y por dimensión; no calcular nada nuevo; no ponderar |
| **Outputs** | `Diagnosis`: hallazgos con magnitud, dimensión afectada, horizonte, regla activada, evidencia y limitaciones |
| **Prohibiciones** | No pondera motores entre sí `[DF 4.3]`. No produce score único. No promedia horizontes `[DF 6.2]`. No oculta qué falta `[DF 6.1]` |

### 12.2 — Trazabilidad obligatoria

Debe ser posible rastrear, cuando sea técnicamente posible:

```
resultado → indicador → dato → fuente
```

Implementado como cadena de referencias en el propio `Diagnosis`:

| Nivel | Contenido | De dónde sale |
|---|---|---|
| Resultado | Hallazgo declarado en lenguaje de decisión | Explanation Layer (M15) |
| Indicador | Métrica concreta, su valor y su versión de modelo | `MotorResultado` |
| Dato | Serie o valor de entrada, con versión y fecha de extracción | Audit Log `[QM XXI]` |
| Fuente | Custodio, gestora, proveedor, cliente, Comité | Data Dictionary `[QM XVI]` |

Cuando el rastreo no es técnicamente posible para algún eslabón, el `Diagnosis` lo declara en lugar de omitirlo (DERIVADO de `[QM I.8]` y `[DF 6.1]`).

### 12.3 — Estructura multi-horizonte

La misma inversión puede ser adecuada para un horizonte e inadecuada para otro simultáneamente. El sistema muestra ambas conclusiones **lado a lado, etiquetadas por horizonte**, y no las promedia ni elige la más favorable; resolver esa tensión es decisión del WM `[DF 6.2]`.

| Dimensión | Corto plazo | Mediano plazo | Largo plazo |
|---|---|---|---|
| Performance | Hallazgo + evidencia | Hallazgo + evidencia | Hallazgo + evidencia |
| Riesgo | … | … | … |
| Diversificación | … | … | … |
| Liquidez | … | … | … |
| Objetivos | … | … | … |

Cada celda puede además estar en estado `blocked` o `warning` según el `CompletenessReport`, y en ese caso muestra la declaración correspondiente en lugar del número.

**Nota:** los límites numéricos de corto / mediano / largo plazo no están fijados en las fuentes y dependen del IPS de cada cliente: parámetro de categoría Cliente `[QM XV]`, OPEN ISSUE ESFS-13.

### 12.4 — Lo que el diagnóstico nunca hace

| Prohibición | Fuente |
|---|---|
| Etiquetar una inversión como buena o mala | Mandato ESFS-01 §20 · `[DF 1]` |
| Producir un score consolidado de cliente o portafolio | `[DF 2.1, 4.3, 8.2]` |
| Presentar un análisis parcial como completo | `[DF 6.1]` |
| Elegir el horizonte más favorable | `[DF 6.2]` |
| Generar narrativa libre | `[QM XIX]` |

---

## 13. Trade-off Architecture

### 13.1 — El problema y la posición del framework

Distintos motores pueden generar señales simultáneas que compiten entre sí. **No existe, ni debe existir, una regla de ponderación automática entre motores** `[DF 4.3]`. El sistema explícitamente no crea una función de ponderación universal, no permite que un motor gane automáticamente sobre otro, y no pone a los motores a competir entre sí.

### 13.2 — Los nueve pasos obligatorios

Ningún trade-off se presenta al WM sin los nueve componentes `[DF 4.3]`:

| # | Paso | Contenido funcional | Origen del contenido |
|---|---|---|---|
| 1 | Identificar el conflicto | Qué dos o más señales compiten | Outputs de motores |
| 2 | Identificar las dimensiones involucradas | Riesgo, liquidez, concentración, retorno, horizonte, objetivos | `Diagnosis` |
| 3 | Cuantificar cada efecto | Valor de la métrica en cada dirección | Motores (sin recálculo nuevo) |
| 4 | Mostrar qué mejora | Métrica y magnitud de la mejora | Motores |
| 5 | Mostrar qué empeora | Métrica y magnitud del deterioro | Motores |
| 6 | Mostrar magnitud | Escala del efecto, no solo su signo | Motores |
| 7 | Mostrar escenarios | Comportamiento bajo Base / Adverse / Stress | Scenario Engine |
| 8 | Mostrar sensibilidad | Cómo cambia la conclusión si cambia un parámetro clave | Sensitivity del modelo `[QM XIV]` |
| 9 | Presentar las alternativas disponibles | El `AlternativeSet` generado | Alternatives Module |

El sistema muestra el conflicto. No lo resuelve: la jerarquización de qué dimensión importa más para ese cliente específico corresponde al Wealth Manager `[DF 4.3]`.

### 13.3 — Detección del conflicto

**Responsabilidad:** el Orchestrator detecta (pregunta 9) `[DF 2.2]`; el Trade-off Module presenta.

**Condición de activación:** dos o más motores producen señales que se mueven en direcciones opuestas sobre la misma alternativa. El **umbral que determina cuándo una oposición es materialmente un trade-off no está fijado numéricamente en ninguno de los documentos base** `[DF 8.3 OQ4]`. Debe implementarse como parámetro configurable desde el inicio `[DF READINESS]`: OPEN ISSUE ESFS-07.

**Consecuencia funcional de no tener el umbral:** el sistema puede detectar oposición de signo, pero no filtrar oposiciones triviales. Hasta que el umbral exista, la política por defecto debe ser mostrar el trade-off con su magnitud y dejar el filtro al WM — más ruido es preferible a ocultar un conflicto real, que es el sentido del principio `[DF 4.3]` (esta es una consecuencia derivada, no una regla nueva).

### 13.4 — Ejemplos conceptuales de pares en conflicto

Tomados de las fuentes, sin agregar pares nuevos: retorno vs. riesgo; liquidez vs. retorno; liquidez vs. concentración `[DF 4.3 ejemplo]`; concentración vs. convicción (concentración intencional en empresa familiar o capital humano, que el WM puede considerar aceptable `[QM XVIII D7]`); corto plazo vs. largo plazo `[DF 6.2]`.

### 13.5 — Extensión futura, fuera del núcleo

Un `AFI Priority / Trade-off Framework` que ayude a ponderar trade-offs de forma más estructurada queda abierto como posibilidad de investigación, clasificado RESEARCH, y **no forma parte de este documento** `[DF 4.3]` `[DF 8.3 OQ2-3]`.

---

## 14. Alternative Generation

### 14.1 — Regla central

El sistema genera las alternativas **cuantitativamente evaluables y relevantes** para la pregunta planteada. El número no es fijo: puede ser ninguna, una, dos, tres o más de tres, según la naturaleza del problema y la información disponible `[DF 4.2]`.

### 14.2 — De dónde surgen las alternativas

| Fuente de la alternativa | Cómo entra al conjunto |
|---|---|
| Diagnóstico | Cada hallazgo material abre un espacio de respuesta posible |
| Restricciones | IPS, liquidez, Approved List y constraints delimitan lo admisible |
| Objetivos | La meta afectada define qué cuenta como mejora |
| Trade-offs | Cada dirección del conflicto es una alternativa candidata |
| Información disponible | Una alternativa que no puede evaluarse cuantitativamente **no entra** `[DF 4.2]` |

### 14.3 — Patrones observados, no reglas universales

| Tipo de decisión | Patrón de alternativas | Estatus |
|---|---|---|
| Rebalanceo (D1) | A. Mantener / B. Rebalancear parcialmente / C. Rebalancear completamente | **Caso especial, el más frecuente en la práctica — no se extiende por default a otros tipos de decisión** `[DF 4.2]` |
| Problema de liquidez (D6) | Mantener estructura / aumentar liquidez con activos líquidos / modificar compromisos futuros / reestructurar exposición ilíquida | Cuatro alternativas de contenido distinto `[DF 4.2]` |
| Deterioro de fondo (D11) | Mantener / mantener bajo monitoreo / reducir exposición / evaluar sustitución | Cuatro alternativas `[DF 4.2]`; consistente con los estados institucionales de Vol II `[V2 B7]` |
| Construcción / Asset Allocation | 2-4 portafolios candidatos | Patrón de la matriz de orquestación `[DF 7.3]` |
| Benchmark (D10) | 0 — es un gate | `[DF 7.3]` |

**OPEN ISSUE ESFS-16:** reglas más granulares sobre cuándo el número correcto es 2 vs. 3 vs. 4 para un mismo tipo de decisión quedan explícitamente abiertas `[DF 8.3 OQ5]`.

### 14.4 — Regla de honestidad epistémica

Si el sistema no puede generar alternativas razonablemente sustentadas con la información y los modelos disponibles, **no las inventa para llenar un formato**. Muestra `[DF 4.2]`:

> *"No existen alternativas cuantitativamente evaluables con la información disponible."*

Funcionalmente, esto significa que `AlternativeSet` con cardinalidad cero es un resultado válido y completo del sistema, no un error ni un estado vacío. Debe presentarse acompañado de qué información permitiría avanzar `[DF 6.2]`.

### 14.5 — Contenido mínimo de cada alternativa

Derivado de lo que `[QM XIII]` exige mostrar para cada alternativa de rebalanceo y de los nueve pasos del trade-off `[DF 4.3]`:

| Campo | Obligatorio | Fuente |
|---|---|---|
| Descripción de la acción propuesta (sin ejecutarla) | Sí | `[DF 4.2]` |
| Impacto proyectado en riesgo | Sí | `[QM XIII]` |
| Impacto proyectado en probabilidad de meta | Sí, cuando ClientGoal está activo | `[QM XIII]` |
| Costos de transacción estimados y consideraciones fiscales donde sea relevante | Sí | `[QM XIII]` |
| Impacto en liquidez | Sí, cuando Liquidity está activo | `[QM XIII]` |
| Comportamiento bajo escenarios | Sí, cuando Scenario está activo | `[QM XIII]` `[DF 4.3 paso 7]` |
| Qué mejora y qué empeora, con magnitud | Sí | `[DF 4.3 pasos 4-6]` |
| Restricciones que la limitan | Sí | `[QM VII]` |
| Datos faltantes que afectan su evaluación | Sí | `[DF 6.1]` |

---

## 15. Recommendation Layer

### 15.1 — Contrato funcional

| Campo | Contenido |
|---|---|
| **Función única** | Integrar los resultados ya disponibles de los motores activados y determinar si existe suficiente evidencia para producir una recomendación analítica de Nivel 3 `[DF 2.3]` |
| **Inputs** | `Diagnosis`, `TradeOff`(s), `AlternativeSet`, `CompletenessReport`, limitaciones de modelo |
| **Outputs** | `AnalyticalOutput` con el nivel alcanzado (0, 1, 2 o 3) y los elementos obligatorios de ese nivel |
| **Límite 1** | **No ejecuta nuevas métricas cuantitativas** — trabaja únicamente sobre outputs que los motores ya calcularon `[DF 2.3]` |
| **Límite 2** | **No reemplaza a los motores** — si la evidencia es insuficiente, lo dice; no completa el vacío con un cálculo propio `[DF 2.3]` |
| **Límite 3** | **No determina gobernanza** — puede concluir que hay evidencia para Nivel 3, pero no decide si la recomendación va al WM, a un Senior o al Investment Committee `[DF 2.3]` |

### 15.2 — Por qué está separada del Orchestrator

El Orchestrator resuelve **qué activar y cómo combinarlo** (cobertura y selección); la Recommendation Layer resuelve **si lo ya combinado alcanza el umbral de evidencia para opinar** (suficiencia). Un sistema puede activar todos los motores correctos y combinarlos sin errores y aun así no tener evidencia suficiente para Nivel 3 — por ejemplo, si el IPS del cliente está incompleto. Fundir ambas capas esconde esa distinción exactamente donde más importa hacerla visible `[DF 2.4]`.

**Consecuencia funcional:** el `AnalyticalOutput` siempre declara el nivel alcanzado **y la razón por la que no alcanzó uno superior**, cuando corresponde (DERIVADO de `[DF 2.3]` + `[DF 6.1]`).

### 15.3 — Contenido obligatorio de una recomendación de Nivel 3

`[DF 2.3]` y `[DF 4.4]` establecen que toda recomendación de Nivel 3 muestra, sin excepción, "los ocho elementos" y a continuación enumeran: **criterios, inputs, resultados, supuestos, restricciones, escenarios, sensibilidad, datos faltantes y limitaciones** — que son nueve ítems enumerados bajo el rótulo de ocho.

**Tratamiento en ESFS-01:** se implementan los **nueve ítems enumerados**, porque omitir cualquiera de ellos violaría otra regla explícita del framework (los datos faltantes no pueden ocultarse `[DF 6.1]`; las limitaciones deben mostrarse `[DF 2.2 pregunta 11]`). El conteo se registra como **OPEN ISSUE ESFS-01** para que AFI fije la lista canónica: si "datos faltantes y limitaciones" es un solo elemento compuesto, la lista es de ocho; si son dos, el rótulo debe decir nueve. No se resuelve aquí porque afecta el contrato de un artefacto central y es el framework congelado el que debe corregir su propio conteo.

| # | Elemento | Contenido | De dónde sale |
|---|---|---|---|
| 1 | Criterios | Qué criterio se usó para comparar alternativas | `AnalysisPlan` + Decision Library |
| 2 | Inputs | Datos exactos usados, con versión y fecha | Audit Log `[QM XXI]` |
| 3 | Resultados | Métricas de cada alternativa | Motores |
| 4 | Supuestos | CMAs, MAR, parámetros, supuestos de cash flow | Parameter Registry |
| 5 | Restricciones | IPS, liquidez, Approved List, constraints | M03, M10, Construction |
| 6 | Escenarios | Comportamiento bajo Base / Adverse / Stress | Scenario Engine |
| 7 | Sensibilidad | Impacto de variar parámetros clave | `[QM XIV]` |
| 8 | Datos faltantes | Qué falta y qué habría cambiado si existiera | `CompletenessReport` |
| 9 | Limitaciones | Limitaciones de los modelos usados | `[QM XXII]` + Model Governance |

### 15.4 — Reglas de bloqueo de Nivel 3 (derivadas de reglas de negocio explícitas)

| Situación | Nivel máximo alcanzable | Regla fuente |
|---|---|---|
| IPS incompleto o no vigente | Nivel 2 para decisiones que dependen de objetivos | `[DF 2.4]` `[QM XXIV Construction/ClientGoal]` |
| Benchmark no elegible | Sin comparación relativa; Nivel 0/1 descriptivo | `[QM I.7, XII]` |
| Decisión de fondo (D3/D4/D5) sin memo con proceso, equipo y ODD | Nivel 2 — el sistema presenta alternativas pero no puede sostener superioridad analítica | `[QM XVIII D3]` `[V2 B11 P4]` |
| Vehículo con ODD Fail/High-Risk | La alternativa que lo incorpora es inadmisible, no una alternativa peor | `[V2 B11 P1]` |
| Motor núcleo del caso bloqueado por datos | Nivel según lo que sí se pudo analizar, declarando el resto | `[DF 6.1, 6.2]` |
| Black-Litterman sin views documentadas y aprobadas | El modelo no se ejecuta; Nivel 3 puede alcanzarse por la vía CORE (MVO + Monte Carlo) | `[QM XXIV]` `[QM XXIII P1]` |
| Modelo degradado a RESEARCH por Model Governance | Sus outputs no sostienen Nivel 3 | `[QM XIV]` (DERIVADO) |

### 15.5 — Redacción obligatoria

La recomendación evita categóricamente *"esta es la decisión correcta"*. Usa la forma condicional: *"bajo los criterios y supuestos definidos, la alternativa X presenta el resultado más consistente con los objetivos analizados"* `[DF 4.4]`.

Funcionalmente: la plantilla de Nivel 3 de la Explanation Layer tiene esta forma fija y no es editable por el usuario (DERIVADO de `[QM XIX]`).

---

## 16. Decision Levels

### 16.1 — Los cuatro niveles y su techo

| Nivel | Pregunta que responde | Existe en AFI | Módulos que se recorren |
|---|---|---|---|
| **Nivel 0 — Information** | ¿Qué está ocurriendo? | Sí | Intake → Orchestrator → Completeness → Motores → Diagnostic Synthesis (sin trade-off, sin alternativas) |
| **Nivel 1 — Diagnosis** | ¿Por qué está ocurriendo? | Sí | Igual que Nivel 0 + análisis de causa (atribución, factor exposure, root cause, clasificación de causa raíz) |
| **Nivel 2 — Alternatives** | ¿Qué opciones existen? | Sí | + Trade-off Module + Alternatives Module |
| **Nivel 3 — Analytical Recommendation** | Según los criterios definidos y la evidencia disponible, ¿qué alternativa parece superior? | Sí — **techo máximo** | + Recommendation Layer con los elementos obligatorios de 15.3 |
| **Nivel 4 — Execution** | — | **No existe. No forma parte de ninguna versión de este sistema** `[DF 4.4]` | — |

### 16.2 — Qué puede y qué no puede hacer el sistema en cada nivel

| Nivel | Puede | No puede |
|---|---|---|
| 0 | Mostrar métricas con su explicación determinística y sus limitaciones | Sugerir acción alguna |
| 1 | Atribuir, clasificar señal como ruido o cambio estructural `[QM XVIII D2]`, identificar dimensión de concentración `[QM XVIII D7]`, clasificar causa raíz de deterioro `[QM XVIII D11]` | Concluir qué hacer |
| 2 | Presentar el conjunto de alternativas con su impacto cuantificado y sus trade-offs | Jerarquizar cuál es preferible |
| 3 | Señalar qué alternativa es más consistente con los objetivos analizados, bajo criterios y supuestos declarados | Afirmar que es la decisión correcta; ejecutar; comunicar al cliente; asignar instancia de gobernanza |

### 16.3 — El reparto sistema / humano, verbo por verbo

| El sistema `[QM XX]` | El ejecutivo (WM / Comité según la decisión) `[QM XX]` |
|---|---|
| Calcula todas las métricas | Interpreta el resultado en el contexto específico del cliente |
| Detecta drift, deterioro, violaciones de límites, concentraciones | Contextualiza con información cualitativa que el sistema no captura |
| Compara solo contra benchmarks que pasaron el gate | Decide toda acción final sobre el patrimonio |
| Simula escenarios, alternativas de rebalanceo, Monte Carlo de metas | Acepta o rechaza cada propuesta, explícitamente |
| Alerta según los triggers definidos | Justifica overrides con nota registrada, no de forma silenciosa |
| Propone alternativas con evidencia, nunca una única recomendación sin opciones visibles | Comunica al cliente — el sistema nunca comunica de forma autónoma |
| Documenta todo cálculo en el log de auditoría, sin excepción | — |

**Cuatro áreas reservadas al juicio humano, que ningún motor intenta automatizar ni parcialmente** `[QM XX]` `[V1 §7]`: definición de objetivos vitales; gestión de crisis y eventos extremos del cliente; priorización entre metas en conflicto; elección de estructuras de gobernanza familiar.

### 16.4 — Gobernanza: lo que el sistema entrega y dónde se detiene

```
SYSTEM
   ↓
ANALYTICAL OUTPUT   (evidencia, magnitud, impacto, alternativas, recomendación si corresponde)
   ↓
WEALTH MANAGER
   ↓
INTERNAL AFI GOVERNANCE   ← capa externa al sistema  [DF 3.1]
   ↓
FINAL DECISION
```

Regla uniforme para D1-D14: en ningún caso el sistema asigna automáticamente si la decisión corresponde al WM, a un Senior o al Investment Committee `[DF 5]`. D15 es la excepción declarada, con instancia fija en el Comité de Model Risk por ser gobernanza de otra naturaleza `[DF 3.2, 3.3]`.

### 16.5 — Decision Library como registro funcional

| ID | Pregunta | Tipo de gobernanza | Motores/módulos principales | Nivel máximo típico |
|---|---|---|---|---|
| D1 | ¿Rebalancear? | Client Decision Governance | Construction, Risk, Liquidity, Scenario | 3 |
| D2 | ¿Mantener estrategia? | Client Decision Governance | Performance, ClientGoal | 3 (clasificación ruido vs. cambio estructural) |
| D3/D4/D5 | ¿Cambiar / agregar / reducir fondo? | Client Decision Governance | Performance, Risk, Diversification, Benchmark + **M10 obligatorio** | 2 sin memo IDD/ODD; 3 con memo `[QM XVIII D3]` |
| D6 | ¿Aumentar liquidez? | Client Decision Governance | Liquidity, ClientGoal, Alternatives, Scenario | 3 |
| D7 | ¿Existe concentración excesiva? | Client Decision Governance | Diversification, Risk | 3 (umbrales pendientes) |
| D8 | ¿El riesgo es compatible con el IPS? | Client Decision Governance | Risk | 3 — alerta, nunca bloqueo automático del portafolio `[QM XVIII D8]` |
| D9 | ¿La liquidez es suficiente? | Client Decision Governance | Liquidity | 3 — misma infraestructura que D6, formulada como estado `[QM XVIII D9]` |
| D10 | ¿El benchmark es elegible? | Gate técnico automático; la excepción es gobernanza | Benchmark | Estado binario elegible / no elegible con detalle de la dimensión que falló |
| D11 | ¿Existe deterioro de gestor? | Client Decision Governance | Monitoring, Performance, Benchmark, Risk + M10 | 3 (clasificación de causa raíz) |
| D12 | ¿Existe una oportunidad? | Client Decision Governance | Monitoring agregando Performance y Scenario | 1-2 — decisión menos codificable, mayor peso del juicio del WM `[QM XVIII D12]` |
| D13 | ¿Rebalanceo extraordinario por evento? | Client Decision Governance | Risk, Scenario | 3 — requiere aprobación explícita del Comité, no es flujo automático como D1 `[QM XVIII D13]` |
| D14 | Aprobación de nuevos gestores/fondos | Client Decision Governance | **M10 íntegro** (7 etapas de Vol II) | 2-3 según completitud del pack de Comité |
| D15 | Gobernanza de modelos | **Methodology Governance** | M23 Model Governance Registry | Instancia fija: Comité de Model Risk `[DF 3.2]` |

**OPEN ISSUE ESFS-05:** `[DF 3.1]` habla de "quince decisiones" y enumera D1 a D14 (catorce identificadores, quince decisiones si D3/D4/D5 cuentan por separado). El registro de decisiones necesita identificadores canónicos únicos para poder indexar el Decision History y el Audit Log.

---

## 17. Wealth Manager Workflow

### 17.1 — Principio de diseño de la interfaz

La interfaz responde *"¿qué necesito saber para tomar una decisión?"* y no *"¿qué métricas tiene el sistema disponibles?"* `[QM I.5]` `[QM XIX]`. Consecuencia directa: **la navegación principal se organiza por decisión y por cliente, no por motor**. Un motor no es una pantalla.

### 17.2 — Las cinco vistas necesarias

| Vista | Responde | Contenido | Fuente |
|---|---|---|---|
| **V1 — Book of business** | ¿En qué cuentas debo actuar hoy? | Lista priorizada de cuentas, heatmap de desviaciones, watchlist | `[QM II.8]` |
| **V2 — Decision workspace** | ¿Qué está ocurriendo aquí y qué opciones tengo? | El `AnalyticalOutput` completo del `DecisionCase`: diagnóstico por horizonte, trade-offs con sus nueve componentes, alternativas con impacto, nivel alcanzado y por qué | `[DF 4.1, 4.3, 4.4]` |
| **V3 — Evidence drill-down** | ¿Por qué el sistema muestra esto? | Cadena resultado → indicador → dato → fuente; regla activada; parámetros y versión; fórmula si el WM la solicita | `[QM XIX, XXI]` |
| **V4 — Completeness panel** | ¿Qué no puedo analizar todavía y qué falta para poder? | Lista de datos faltantes con criticidad, qué indicadores están bloqueados y qué información permitiría avanzar hacia un análisis más sofisticado | `[DF 6.1, 6.2]` |
| **V5 — Client view (release por el WM)** | ¿Cómo se lo explico al cliente? | Plantilla simplificada: progreso hacia metas, explicación intuitiva. **Mismo cálculo, mismo número, distinto vocabulario** | `[QM XIX]` — ver ESFS-12 sobre su canal de entrega |

### 17.3 — Ciclo de trabajo del WM

```
1. V1: revisar prioridades del día (Monitoring)
2. Seleccionar cuenta o alerta → se crea o se abre un DecisionCase
3. V4: ver qué se puede y qué no se puede analizar; completar datos si corresponde
4. V2: leer diagnóstico por horizonte, trade-offs y alternativas
5. V3: profundizar en la evidencia de cualquier hallazgo
6. Aportar contexto cualitativo (nota registrada, no un campo libre sin traza)
7. Aceptar / rechazar / modificar una alternativa, o decidir no actuar
8. Justificar el override si difiere de la alternativa con mayor convicción sugerida  [QM XVIII D1]
9. El caso pasa a la capa de gobernanza institucional (externa) y al Decision History
10. V5: preparar la comunicación al cliente — siempre con acto humano de liberación
```

### 17.4 — Lo que el WM puede y no puede modificar

| Puede | No puede | Fuente |
|---|---|---|
| Aportar contexto cualitativo y notas | Modificar parámetros institucionales o de Comité | `[QM XV]` |
| Elegir, modificar o rechazar una alternativa | Introducir views propias en Black-Litterman: ve el output de BL como house view ya consolidada, no como un panel donde introduce sus opiniones | `[QM VIII]` |
| Solicitar re-análisis con otro horizonte o supuesto declarado | Ocultar un trade-off o una limitación en la salida | `[DF 6.1]` |
| Ajustar preferencias operativas dentro de rangos pre-aprobados | Salir de los límites institucionales | `[QM XV]` |
| Decidir no actuar | Ejecutar desde el sistema | `[DF 4.4]` |

---

## 18. User Journeys

Formato por escenario: **Trigger → Input → Orchestrator → Data Requirements → Completeness → Engines → Diagnosis → Trade-offs → Alternatives → Recommendation → WM → Decision → Tracking.**

### 18.1 — Scenario A: Nuevo cliente (caso de uso 1)

| Paso | Contenido |
|---|---|
| Trigger | Ingreso de un nuevo cliente |
| Input | Datos de identificación; objetivos preliminares; patrimonio declarado |
| Orchestrator | Caso 1: **ningún motor aún** `[DF 7.3]` — es un paso de recopilación |
| Data Requirements | IPS (C), life balance sheet, calendario de flujos, moneda base, horizonte, límites de riesgo por perfil |
| Completeness | Todo faltante es visible; el sistema declara qué análisis se habilitará con cada dato que se complete `[DF 6.2]` |
| Engines | Ninguno |
| Diagnosis / Trade-offs / Alternatives | 0 alternativas `[DF 7.3]` |
| Recommendation | Nivel 0: estado de completitud del perfil |
| WM / Decision | Completar el IPS y llevarlo a firma y aprobación de Comité `[QM XVI]` |
| Tracking | El caso queda abierto hasta que el IPS esté vigente |

### 18.2 — Scenario B: Nuevo portafolio (casos 3 y 14)

| Paso | Contenido |
|---|---|
| Trigger | IPS vigente y necesidad de construir |
| Input | IPS; CMAs vigentes; inventario de productos Approved-Active |
| Orchestrator | Núcleo: Construction, ClientGoal. Opcional: Diversification `[DF 7.3]`. Flujo Portfolio Construction `[DF 7.1]` |
| Data Requirements | CMAs (C), constraints (C), Σ con shrinkage (C), universo admisible (C), horizonte (C) |
| Completeness | Sin CMAs vigentes → BLOCK de MVO; sin metas cuantificadas → BLOCK de probabilidad de meta |
| Engines | Construction (MVO robusto + Goal-Based Monte Carlo); ClientGoal; Diversification; Risk y Liquidity como fuentes de constraints |
| Diagnosis | Portafolios candidatos con métricas esperadas y sensibilidades, por horizonte |
| Trade-offs | Típicos: retorno vs. riesgo; liquidez vs. retorno esperado |
| Alternatives | 2-4 portafolios candidatos `[DF 7.3]` |
| Recommendation | Nivel 3 posible si IPS, CMAs y constraints están completos |
| WM / Decision | Propuesta al Comité, que aprueba la propuesta final `[QM XXIV Construction]` |
| Tracking | El portafolio aprobado se convierte en SAA vigente y base de drift futuro |

### 18.3 — Scenario C: Evaluación de portafolio existente (casos 2, 4, 18)

| Paso | Contenido |
|---|---|
| Trigger | Revisión periódica calendarizada o solicitud del cliente |
| Input | Portafolio actual; período a evaluar |
| Orchestrator | Caso 4: núcleo Performance, Risk; opcional Diversification, Scenario. Caso 18 (revisión patrimonial): los diez, según relevancia `[DF 7.3]`. Flujo Portfolio Diagnostic `[DF 7.1]` |
| Data Requirements | NAV, flujos, benchmark + eligibility, retornos, Σ, clasificación de liquidez |
| Completeness | Sin benchmark elegible: se calculan métricas absolutas y se declara por qué no hay comparación relativa `[QM XII]` |
| Engines | Subconjunto relevante, **nunca todos por default** `[DF 4.1]` |
| Diagnosis | Hallazgos por dimensión y por horizonte, con trazabilidad |
| Trade-offs | Los que surjan; posiblemente varios en el caso 18 `[DF 7.3]` |
| Alternatives | 0-2 en revisión periódica; variable en revisión patrimonial |
| Recommendation | Nivel 0-3 según hallazgos y evidencia |
| WM / Decision | Aceptación, rechazo o no acción, con justificación registrada si difiere |
| Tracking | Evolución de indicadores; comparación expectativa vs. resultado `[DF 6.5]` |

### 18.4 — Scenario D: Evaluación de una oportunidad de inversión (casos 7, 9, 15)

| Paso | Contenido |
|---|---|
| Trigger | Vehículo candidato propuesto, o señal de oportunidad detectada |
| Input | Ficha del vehículo; factsheet; reglamento; cashflows si es privado |
| Orchestrator | Caso 7: núcleo Due Diligence (M10) y Alternatives si es privado; opcional Diversification, Liquidity `[DF 7.3]`. Caso 9: Performance/Risk **en modo detección**, con separación explícita entre Opportunity Identification e Investment Decision `[DF 7.1]` |
| Data Requirements | DDQ IDD y ODD (C); estado en Approved List (C); factsheet y reglamento vigentes (C) `[QM XVI]`; cashflows completos si es privado (C) |
| Completeness | Sin factsheet vigente no se aprueba el vehículo `[QM XVI]`; sin cashflows completos, métricas de PE bloqueadas sin advertencia `[QM XXIV]` |
| Engines | Alternatives (TVPI/DPI/RVPI/IRR); Diversification (impacto en concentración); Liquidity (impacto en buckets); Risk (exposición factorial aproximada); Benchmark (elegibilidad del índice público para PME) |
| Diagnosis | Encaje con la arquitectura del portafolio: asset class, bucket de riesgo, correlaciones esperadas `[V2 B9]` |
| Trade-offs | Retorno esperado vs. iliquidez; diversificación vs. concentración de gestor |
| Alternatives | 0-2 `[DF 7.3]` |
| Recommendation | **Nivel 3 solo con memo completo (proceso, equipo y ODD)** `[QM XVIII D3]` `[V2 B11 P4]`; ODD Fail/High-Risk ⇒ inadmisible `[V2 B11 P1]` |
| WM / Decision | D14: pack al Comité de Inversiones (7 etapas de Vol II) |
| Tracking | Alta en Approved List con rating, límites de uso y condiciones; revisión anual |

### 18.5 — Scenario E: Rebalanceo (caso 5)

| Paso | Contenido |
|---|---|
| Trigger | Trigger calendar-based (revisión mínima trimestral/semestral) o threshold-based (peso fuera de bandas) `[QM XIII]` |
| Input | Portafolio actual; SAA vigente y bandas; costos estimados |
| Orchestrator | Núcleo: Construction, Risk, Liquidity. Opcional: Scenario `[DF 7.3]` |
| Data Requirements | Posiciones (C); SAA y bandas (C); costos (NC); liquidez por vehículo (C); escenarios (NC) |
| Completeness | Sin SAA vigente el drift no es computable → BLOCK |
| Flujo | Portfolio → Target → **Drift → Materiality** → Risk → Liquidity → Costs → Taxes/Restrictions → Scenarios → Alternatives `[DF 6.4]` |
| Diagnosis | Magnitud del drift e impacto proyectado en riesgo si no se actúa `[QM XVIII D1]` |
| Trade-offs | Frecuentes: liquidez vs. concentración; costos vs. reducción de riesgo |
| Alternatives | Patrón A/B/C, típicamente tres `[DF 4.2]` |
| Recommendation | Nivel 3 con los nueve elementos; el umbral de materialidad es parámetro pendiente (ESFS-08) |
| WM / Decision | El WM elige, modifica o decide no actuar — con justificación registrada si difiere de la alternativa con mayor convicción sugerida `[QM XVIII D1]`. **El rebalanceo nunca se convierte en ejecución automática** `[DF 6.4]` |
| Tracking | Registro en Decision History y en la Rebalancing History View con el escenario de mercado vigente `[DF 6.6]` |

### 18.6 — Scenario F: Monitoreo (casos 6, 11, 12, 13, 16, 17)

| Paso | Contenido |
|---|---|
| Trigger | Ciclo diario/semanal del Monitoring Engine; evento de mercado; evento de cliente; evento de modelo |
| Input | Resultados consolidados de los motores; triggers configurados; señales cualitativas de M10 |
| Orchestrator | Según el trigger: deterioro de fondo (caso 6) → Performance, Monitoring; cambio de objetivos (11) → ClientGoal; cambio de riesgo (12) → Risk; cambio de horizonte (13) → ClientGoal; stress testing (17) → Scenario `[DF 7.3]` |
| Data Requirements | Umbrales de trigger (C, valores pendientes); señales cualitativas (C para D11) |
| Completeness | Si un motor fuente está en `insufficient_data`, ese componente se excluye de la priorización **con nota explícita** `[QM XXIV]` |
| Engines | Monitoring como agregador; los motores fuente según el caso |
| Diagnosis | Clasificación de la señal: ruido vs. cambio estructural `[QM XVIII D2]`; causa raíz de deterioro: cíclico / estructural / operacional `[QM XVIII D11]` |
| Trade-offs | Los que surjan al evaluar respuestas |
| Alternatives | Deterioro: mantener / monitoreo / reducir / evaluar sustitución `[DF 4.2]` |
| Recommendation | Nivel 1-3 según evidencia; en D12 (oportunidad) el sistema aporta menos y el WM más `[QM XVIII D12]` |
| WM / Decision | Watchlist, plan de remediación, escalamiento a Comité `[V2 B7]` |
| Tracking | Estado del gestor/vehículo y su historial de ratings; alertas cerradas con resultado |

### 18.7 — Scenario G: Información insuficiente (transversal, no es un caso de uso separado)

Este escenario no corresponde a un caso de la matriz: es el comportamiento del sistema ante cualquier pregunta cuando los datos no alcanzan. Se especifica aparte porque es el escenario **más frecuente en las etapas iniciales** y el que más define la credibilidad del sistema.

| Paso | Contenido |
|---|---|
| Trigger | Cualquier pregunta |
| Completeness | Clasifica cada dato en BLOCK / WARNING / CONTINUE `[DF 6.1]` |
| Comportamiento del sistema | 1) Analiza **lo que sí puede** analizarse `[DF 6.2]`. 2) Declara qué no puede analizarse todavía. 3) Declara **qué información permitiría avanzar** hacia un análisis más sofisticado. 4) Nunca imputa silenciosamente. 5) Nunca presenta el análisis como completo |
| Engines | Solo los no bloqueados; los bloqueados aparecen listados con su causa |
| Alternatives | Puede ser 0, con el mensaje de honestidad epistémica `[DF 4.2]` |
| Recommendation | El nivel alcanzado y la razón por la que no se alcanzó uno superior |
| WM / Decision | El WM decide si completar datos o decidir con información parcial declarada |
| Tracking | El caso queda en estado de datos incompletos; al completarse el dato, se re-ejecuta generando una nueva versión del plan, sin borrar la anterior `[QM XXI]` |

---

## 19. System States

### 19.1 — Validación de los estados propuestos contra la metodología

El mandato propone una lista de estados y pide validarla. Resultado de la validación:

| Estado propuesto | ¿Justificable en las fuentes? | Evidencia / observación |
|---|---|---|
| New | Sí | Caso de uso 1 y creación del `DecisionCase` `[DF 7.3]` |
| Data Collection | Sí | Caso 1 es explícitamente "paso de recopilación" `[DF 7.3]` |
| Data Incomplete | Sí | Comportamiento BLOCK de Data Completeness `[DF 6.1]` |
| Ready for Analysis | Sí | Consecuencia del `CompletenessReport` sin BLOCK en motores núcleo (DERIVADO) |
| Analysis Running | **Parcial** | No es un estado metodológico sino operativo; se justifica solo porque la metodología distingue cálculo diario en batch de cálculo on-demand `[QM II.2]`. Se conserva como estado técnico, no decisional |
| Analysis Complete | Sí | Punto donde existen `EngineResult` para todos los motores activados |
| Diagnostic | Sí | Paso explícito de la cadena `[DF 4.1]` |
| Alternatives | Sí, **pero omitible** | Una pregunta de Nivel 0 puede no generar alternativas `[DF 4.1]` |
| Recommendation | Sí, **pero omitible** | Idem: depende del nivel alcanzado |
| Pending WM Decision | Sí | El sistema se detiene en el Analytical Output `[DF 3.1]` |
| Decided | Sí | Decisión registrada `[DF 6.5]` |
| Monitoring | Sí | Seguimiento posterior y Learning Loop `[DF 6.5]` |
| Closed | **No justificable** | Ninguna fuente define cuándo un caso se cierra. El Learning Loop implica que un caso sigue aportando evidencia después de la decisión `[DF 6.5]`. **OPEN ISSUE ESFS-11** |

### 19.2 — Estados adicionales exigidos por las fuentes y ausentes de la lista propuesta

| Estado | Por qué es necesario | Fuente |
|---|---|---|
| `insufficient_data` | Estado de sistema de **primera clase**, no un error genérico ni un campo vacío `[QM XIV]` | `[QM XIV]` `[QM I.8]` |
| `blocked_by_benchmark` | Una dimensión no verificable o benchmark no elegible impide la comparación relativa sin impedir el resto del análisis | `[QM XII, XXIV]` |
| `pending_governance` | El caso salió del sistema hacia la capa de gobernanza institucional; el sistema no sabe ni decide a qué instancia fue `[DF 3.1]` | `[DF 3.1]` |
| `override_registered` | El WM decidió distinto de la alternativa con mayor convicción sugerida y registró su justificación | `[QM XVIII D1]` `[QM XX]` |
| `model_degraded` | Un modelo usado por el caso fue degradado por Model Governance después del cálculo | `[QM XIV]` |
| `unmapped_question` | La pregunta no mapea a ningún caso de uso ni decisión conocida y no se fuerza a un flujo aproximado | DERIVADO de `[QM I.8]` |
| `re_analysis_requested` | Cambió un dato o un parámetro y el caso debe recalcularse generando una nueva versión, sin sobrescribir la anterior | DERIVADO de `[QM XXI]` |

### 19.3 — Máquina de estados (no lineal)

```
                   ┌──────────────► unmapped_question (registrado, revisión humana)
New ──► Data Collection ──► Data Incomplete ◄──┐
                   │                │          │ (dato completado)
                   ▼                └──────────┘
            Ready for Analysis
                   │
                   ▼
            Analysis Running ──► insufficient_data (por motor, parcial)
                   │            ──► blocked_by_benchmark (por comparación)
                   ▼
            Analysis Complete
                   │
                   ▼
              Diagnostic ──────────────────┐  (Nivel 0/1 termina aquí)
                   │                       │
                   ▼                       │
            [Trade-off detectado]          │
                   ▼                       │
              Alternatives ────────────────┤  (Nivel 2 termina aquí)
                   │                       │
                   ▼                       │
             Recommendation ───────────────┤  (Nivel 3)
                   │                       │
                   ▼                       ▼
            Pending WM Decision ◄──────────┘
                   │
        ┌──────────┼─────────────┐
        ▼          ▼             ▼
     Decided  override_    pending_governance
        │      registered        │
        └──────────┴─────────────┘
                   ▼
              Monitoring ──► re_analysis_requested ──► (vuelve a Ready for Analysis,
                   │                                    nueva versión del caso)
                   ▼
                 ??? (Closed — OPEN ISSUE ESFS-11)
```

**Regla de recorrido:** ningún caso está obligado a pasar por Alternatives ni Recommendation; la cadena es el mapa completo y cada pregunta recorre su subconjunto `[DF 4.1]`.

---

## 20. Error & Exception Handling

### 20.1 — Principio

El sistema debe fallar de forma **explícita y trazable, nunca silenciosamente**. Este principio ya existe en las fuentes como regla de oro: si los datos no permiten estimar la métrica con confianza razonable, el sistema lo declara `[QM XVII]` `[QM I.8]`.

### 20.2 — Catálogo de excepciones y comportamiento exigido

| Excepción | Detección | Comportamiento | Qué ve el WM | Fuente |
|---|---|---|---|---|
| **Datos faltantes** | Gap en la serie requerida | BLOCK si CRITICAL; WARNING si importante | Qué falta, por qué bloquea y qué habilitaría | `[DF 6.1]` `[QM XVII]` |
| **Datos inconsistentes** | NAV improbable dado el perfil de riesgo del vehículo | Flag crítico, prioridad alta; **Model Block hasta reconciliación** | Estado de reconciliación pendiente | `[QM XVII]` |
| **Datos desactualizados** | NAV repetido de forma improbable (stale) | Distinguir baja frecuencia legítima de error; Model Block si no se puede distinguir con confianza | Flag diferenciado | `[QM XVII]` |
| **Datos insuficientes (muestra corta)** | Observaciones bajo el mínimo del modelo | `insufficient_data` para esa métrica; el resto del análisis continúa | "Información insuficiente para producir una estimación confiable" | `[QM XIV, XXIV]` |
| **Engine no aplicable** | El caso de uso no requiere el motor, o el instrumento no admite el modelo | El motor no se activa; se declara por qué no era relevante | Lista de motores no activados con la causa | `[DF 7.2]` `[DF 2.2 q6-7]` |
| **Benchmark no elegible** | Falla una dimensión del framework de ocho | **No se genera ranking**; solo diferencias cualitativas descriptivas | Qué dimensión falló y por qué la comparación no es válida | `[QM XII]` `[DF 6.3]` |
| **Dimensión de benchmark no verificable** | Falta información para verificar una de las ocho dimensiones | Esa dimensión se marca "no verificable"; **no se asume comparabilidad por defecto** | Ficha de elegibilidad por dimensión | `[QM XXIV]` |
| **Información incompatible (frecuencia)** | Series con distinta frecuencia nativa | Agregar a la frecuencia más baja común; **nunca interpolar** | Nota explícita de la frecuencia usada | `[QM IV, XVII]` |
| **Información incompatible (moneda)** | Series en distinta moneda | Aplicar FX explícito y documentarlo; **Model Block si no hay serie FX confiable** | Tipo de cambio y fecha usados | `[QM XVII]` |
| **Cálculo imposible** | El modelo no converge o el input viola su dominio | `insufficient_data` o `calculation_failed` con la causa; jamás un número aproximado | Declaración explícita | `[QM XIV]` (DERIVADO para la variante técnica) |
| **Conflicto entre outputs** | Dos motores con señales opuestas | **No es un error**: es un trade-off y se presenta con los nueve pasos | El trade-off completo | `[DF 4.3]` |
| **Ausencia de histórico** | Serie inexistente o backfill reconstruido | Excluir el período pre-lanzamiento del cálculo de habilidad del gestor; flag de "historial parcialmente reconstruido" | Flag y alcance real del histórico | `[QM XVII]` |
| **Ausencia de información del cliente** | IPS inexistente, vencido o sin metas cuantificables | `insufficient_data` en ClientGoal y Construction; el resto continúa; Nivel 3 condicionado | Qué parte del análisis depende del IPS | `[QM XXIV]` `[DF 2.4]` |
| **Outlier no validado** | Retorno extremo fuera de rango razonable | Excluir del cálculo hasta validación contra fuente secundaria; **nunca incluir silenciosamente** | Flag "pendiente de validación" | `[QM XVII]` |
| **Modelo sin vigencia** | Model Governance degradó el modelo | Los outputs de ese modelo no sostienen Nivel 3; se marca el caso `model_degraded` | Estado del modelo y fecha de última validación | `[QM XIV]` (DERIVADO) |
| **Intento de comparación no verificada** | Se solicita ranking contra un benchmark sin eligibility check | Alerta y bloqueo de la comparación | Motivo del bloqueo | `[QM XXIV Benchmark]` |
| **Parámetro sin valor asignado** | Se requiere un umbral pendiente de calibración institucional | El indicador se calcula pero la **clasificación** que depende del umbral queda declarada como no disponible | "Umbral institucional pendiente de definición" | DERIVADO de `[DF READINESS]` |

### 20.3 — Lo que nunca es un comportamiento aceptable

| Prohibido | Fuente |
|---|---|
| Imputar silenciosamente un dato faltante | `[DF 6.1]` |
| Mostrar un número calculado sobre datos pobres con la misma confianza visual que uno robusto | `[QM XIV]` `[QM I.8]` |
| Presentar un análisis como completo con limitaciones materiales no declaradas | `[DF 6.1]` |
| Interpolar una frecuencia faltante | `[QM XVII]` |
| Forzar una comparación contra un benchmark no elegible | `[QM XII]` |
| Tratar el NAV privado como precio de mercado | `[QM X]` |
| Calcular métricas parciales de PE sin advertencia cuando faltan cashflows | `[QM XXIV]` |
| Omitir silenciosamente un motor degradado de la priorización del Monitoring | `[QM XXIV]` |

---

## 21. Auditability & Traceability

### 21.1 — La pregunta que la arquitectura debe poder responder

> ¿Por qué el sistema mostró esto?

Debe existir trazabilidad completa en la cadena:

```
Decision → Recommendation → Diagnostic → Engine → Indicator → Input → Source
```

### 21.2 — Registro mínimo obligatorio por output

Once campos, sin excepción `[QM XXI]`. Un output sin este registro **no es un output válido del sistema AFI, independientemente de qué tan correcto sea matemáticamente**.

| # | Campo | Contenido exigido |
|---|---|---|
| 1 | Datos utilizados | Referencia exacta a las series y valores de entrada: no solo "NAV del fondo X", sino la versión y fecha de extracción específica |
| 2 | Fecha | Momento del cálculo |
| 3 | Modelo | Identificador y versión del modelo |
| 4 | Parámetros | Valores exactos usados: ventana, nivel de confianza, τ, δ, bandas |
| 5 | Resultado | Output numérico completo, no solo el resumen mostrado al usuario |
| 6 | Regla activada | Qué regla de negocio de la Decision Library se disparó, si aplica |
| 7 | Recomendación | Alternativas presentadas y cuál tenía mayor convicción sugerida |
| 8 | Decisión del ejecutivo | Qué eligió el WM o el Comité |
| 9 | Override | Si difirió de la sugerencia del sistema |
| 10 | Justificación | Nota escrita del override, obligatoria cuando existe |
| 11 | Fecha de revisión | Próxima fecha programada de reevaluación de esa decisión o modelo |

### 21.3 — Registros adicionales exigidos por otras partes de las fuentes

| Registro | Contenido | Fuente |
|---|---|---|
| Auditoría de parámetros | Quién propuso, quién aprobó, fecha, valor anterior, valor nuevo, justificación escrita — obligatorio para parámetros Institucional, Comité y Cliente | `[QM XV]` |
| Verificación de elegibilidad de benchmark | Las ocho dimensiones, su resultado, fecha, y la excepción documentada si existe | `[QM XXIV Benchmark]` |
| Versión de IPS usada | En cada cálculo de probabilidad de meta | `[QM XXIV ClientGoal]` |
| Matriz de covarianzas usada y su fecha de estimación | En cada output de Diversification | `[QM XXIV Diversification]` |
| CMAs y constraints usados | En cada propuesta de Construction, versionados | `[QM XXIV Construction]` |
| Definición exacta del escenario ejecutado | Versionada | `[QM XXIV Scenario]` |
| Supuestos de cash flow por vehículo | En cada output de Liquidity | `[QM XXIV Liquidity]` |
| Fuente y fecha de cada cashflow | En cada output de Alternatives | `[QM XXIV Alternatives]` |
| Log de decisiones de ODD | Documentación revisada y justificación de ratings | `[V2 B11 P1]` |
| Casos anulados por falta de fundamento forward-looking | Registro de recomendaciones bloqueadas por performance-chasing | `[V2 B11 P4]` |
| Herencia del Monitoring Engine | Hereda el registro de cada motor fuente; **no duplica** | `[QM XXIV Monitoring]` |

### 21.4 — Requerimiento funcional de versionado

DERIVADO de `[QM XXI]` (reconstrucción en cualquier momento futuro) y de `[QM XIV]` (versión de modelo): el sistema no puede sobrescribir. Cada re-ejecución de un caso, cada cambio de parámetro y cada corrección de dato producen una **nueva versión**, y la versión anterior permanece consultable con el resultado que produjo en su momento. Sin esto, la reconstrucción retrospectiva es imposible y el registro de los once campos pierde sentido.

### 21.5 — Nivel de especificación

Este documento define **qué debe registrarse**, no cómo. La arquitectura técnica de logs (almacenamiento, retención, indexación, inmutabilidad) es parte de la arquitectura técnica posterior, con una excepción que sí es funcional: la retención mínima debe permitir la reconstrucción durante el período de deber fiduciario aplicable, y ese período no está definido en las fuentes — **OPEN ISSUE ESFS-23**.

---

## 22. Tracking & Learning Loop

### 22.1 — Decision History

Todo análisis relevante se registra: **situación, datos, análisis, alternativas, recomendación, decisión, resultado posterior** `[DF 6.5]`.

| Campo del registro | Contenido | Momento de captura |
|---|---|---|
| Situación | `DecisionCase` con pregunta, unidad, decisión y trigger | Al crear el caso |
| Datos | `CompletenessReport` + referencias de datos del Audit Log | Antes del cálculo |
| Análisis | `EngineResult` de cada motor activado, con versión y parámetros | Durante el cálculo |
| Alternativas | `AlternativeSet` completo, incluida la cardinalidad cero | Tras generación |
| Recomendación | `AnalyticalOutput` con el nivel alcanzado | Tras la Recommendation Layer |
| Decisión | Qué eligió el ejecutivo; override y justificación si existe | Tras la revisión del WM |
| Implementación | Que la decisión se implementó y cuándo (dato aportado, no ejecutado por el sistema) | Posterior |
| Resultado posterior | Evolución observada de los indicadores relevantes | Continuo |
| Post-analysis | Comparación entre expectativa declarada y resultado observado | Periódico |

### 22.2 — Tracking

| Objeto de seguimiento | Qué se sigue | Output |
|---|---|---|
| Portafolios | Evolución de composición, drift, indicadores por dimensión | Series históricas por portafolio |
| Recomendaciones | Estado (aceptada / rechazada / modificada / pendiente) y resultado posterior | Tasa de aceptación y su resultado, sin juicio automático sobre el WM |
| Decisiones | Qué se decidió, con qué evidencia, con qué override | Índice del Decision History |
| Indicadores | Evolución temporal de cada métrica relevante | Comparación expectativa vs. resultado |

### 22.3 — Learning Loop

```
Recommendation → Executive Decision → Outcome → Monitoring → Post-analysis → Methodology Improvement
```

El loop permite evaluar, con el tiempo, qué recomendaciones fueron aceptadas o rechazadas, por qué, con qué resultado posterior, y **si los umbrales institucionales resultaron demasiado agresivos o demasiado laxos en la práctica** — sin requerir Machine Learning como componente del propio sistema `[DF 6.5]`.

| Regla del loop | Contenido |
|---|---|
| No es aprendizaje automático | Es un loop institucional; no hay ML en el producto `[DF 6.5]` |
| No modifica la metodología automáticamente | Produce evidencia; la modificación es decisión humana de la instancia correspondiente `[DF 6.5]` `[QM XV]` |
| Alimenta específicamente | La calibración futura del umbral de materialidad de drift y de la magnitud de trade-off `[DF 6.5]` `[DF 8.3 OQ4]` |
| También alimenta | Los criterios de selección y monitoreo de gestores: registrar causas de remoción y ajustar criterios para capturar patrones similares antes `[V2 B7]` |

### 22.4 — Rebalancing History View

Vista de consulta —**no un motor, no un componente central de la lógica decisional**— que consolida los registros individuales del Decision History en una línea de tiempo de rebalanceos por cliente, con el contexto de mercado (escenario Base/Adverse/Stress vigente) de cada decisión pasada. Clasificada **SUPPORTING VIEW** `[DF 6.6]`.

**Regla explícita de no extensión:** el mismo patrón de vista longitudinal **no se extiende automáticamente** a otros módulos (liquidez, watchlist de gestores); hacerlo sin evidencia de que agrega valor equivalente sería añadir funcionalidad por similitud formal, no por necesidad demostrada `[DF 6.6]` `[DF 8.3 OQ7]`.

---

## 23. Functional Dependencies

### 23.1 — Cadena de dependencia principal

```
DATA ──► ENGINES ──► DIAGNOSTIC ──► TRADE-OFFS ──► ALTERNATIVES ──► RECOMMENDATION ──► INTERFACE ──► TRACKING
  ▲                                                                                                      │
  └──────────────────────── Learning Loop (evidencia para calibración) ◄─────────────────────────────────┘
```

### 23.2 — Dependencias entre motores (según las fuentes, no inferidas)

| Motor | Depende de | Tipo de dependencia | Fuente |
|---|---|---|---|
| Performance | Benchmark (gate), Construction (separar asignación de selección) | Bloqueante para métricas relativas | `[QM II.1]` |
| Risk | Benchmark (TE, beta), Scenario (shocks), Liquidity (riesgo de liquidez) | Bloqueante para TE/beta; no bloqueante para métricas absolutas | `[QM II.2]` |
| Diversification | Risk (matriz de covarianzas compartida), Construction (what-if) | Bloqueante para risk contribution | `[QM II.3]` |
| Construction | Risk, Diversification, Liquidity, Benchmark; Approved List | Bloqueante: sin constraints no hay MVO CORE | `[QM II.4]` `[QM VII]` |
| Liquidity | Alternatives (curvas de capital calls — las **consume**, no las recalcula), Scenario | Bloqueante para portafolios con privados | `[QM II.5, IX]` |
| Alternatives | Alimenta a Liquidity y a Risk | Es proveedor, no consumidor | `[QM II.6, X]` |
| Scenario | Risk, Liquidity, Construction | Bloqueante: estresa exposiciones existentes | `[QM II.7]` |
| Monitoring | **Todos** — no tiene sentido con menos de 2-3 motores fuente | Bloqueante total | `[QM II.8]` `[QM ROADMAP F3]` |
| Benchmark | Ninguno — es el gate inicial | Independiente | `[QM II.9]` |
| ClientGoal | Construction y Scenario (retorno/riesgo proyectado); IPS estructurado | Bloqueante técnico **y organizacional** | `[QM II.10]` `[QM ROADMAP F5]` |

### 23.3 — Clasificación de componentes

| Categoría | Componentes | Consecuencia para la construcción |
|---|---|---|
| **Bloqueantes absolutos** (nada funciona sin ellos) | Capa de datos (NAV, flujos, IPS, FX), Data Requirement Registry, Data Completeness Gate, Audit Log, Parameter Registry, Decision Case | Fase 0 y Fase 1; sin estos no hay sistema, hay una calculadora |
| **Bloqueantes de dominio** | Benchmark Engine (bloquea toda comparación relativa), M10/Approved List (bloquea D3/D4/D5/D14), IPS vigente (bloquea ClientGoal y Construction) | Deben construirse antes que lo que dependen de ellos |
| **Independientes / paralelizables** | Benchmark Engine, Scenario Library, Parameter Registry, Audit Log, Explanation Layer (por motor), M10 | Pueden desarrollarse en paralelo con otros frentes |
| **Cuellos de botella** | 1) Calidad de flujos fechados y clasificados (afecta Performance, Liquidity y Alternatives a la vez). 2) IPS estructurado (dependencia organizacional, no técnica `[QM XXIII P5]`). 3) Cashflows completos de vehículos privados (sin ellos, Alternatives no calcula y Liquidity queda incompleto). 4) Umbrales institucionales pendientes (el sistema calcula pero no clasifica) | Deben atacarse antes de que el desarrollo los encuentre |
| **Datos a conseguir primero** | Ver Parte 29 | — |

### 23.4 — Dependencias que no son técnicas

Registradas porque determinan el cronograma real y ninguna se resuelve programando:

| Dependencia | Naturaleza | Quién la resuelve | Fuente |
|---|---|---|---|
| Proceso de IPS estructurado y vigente | Organizacional | AFI / asesores | `[QM ROADMAP F5]` `[QM XXIII P5]` |
| Comité capaz de sostener el proceso Evidencia→View→Convicción para BL | Organizacional | Investment Committee, con 2-3 ciclos documentados | `[QM XXIII P1]` |
| CMAs institucionales (no individuales del asesor) | Institucional | Investment Committee | `[QM VII]` |
| Escenarios hipotéticos definidos por el Comité | Institucional | Investment Committee | `[QM XI]` |
| Umbrales de materialidad, bandas y triggers | Institucional, con evidencia operativa | Investment Committee | `[DF 8.3 OQ4]` `[QM XXIII P4]` |
| Reglas de escalamiento | Institucional | Investment Committee y Senior Management | `[DF 8.3 OQ1]` |
| Política ESG (institucional uniforme vs. por IPS) | Institucional | Investment Committee | `[QM XXIII P6]` |
| Audit de la infraestructura de datos actual de AFI | Tecnológico, **paso previo obligatorio a cualquier desarrollo** | Equipo técnico de AFI | `[QM XXIII P5]` |

---

## 24. MVP Definition

### 24.1 — Criterio del MVP

El MVP debe demostrar el flujo **Pregunta → Datos → Análisis → Diagnóstico → Alternativas → WM Decision** sin simplificar artificialmente la metodología. No es una demo: es el sistema, reducido a un subconjunto coherente de flujos.

### 24.2 — Contenido del MVP

| Componente | Alcance en el MVP | Justificación |
|---|---|---|
| M01 Decision Case | Completo para los flujos incluidos | Sin él no hay trazabilidad ni estado |
| M02 Orchestrator | Once preguntas, con enrutamiento limitado a los casos de uso incluidos | `[DF 2.2]` |
| M03 IPS | Captura estructurada, versión y vigencia; límites de riesgo por perfil | Referencia central obligatoria `[QM I.1]` |
| M04 Portfolio State | Posiciones, pesos, asset class, moneda, clasificación de liquidez | Base de todo cálculo |
| M05 Vehículos y gestores | Ficha mínima: tipo, liquidez, costos, frecuencia de valuación, factsheet vigente | `[QM XVI]` |
| M06 Market & Reference Data | Benchmarks, índices, FX | FX es bloqueante multi-moneda `[QM XVII]` |
| M07 + M08 Data Requirements y Completeness | Completos para las métricas incluidas | Es el diferencial del sistema, no un extra |
| **Motores: Performance (CORE), Risk (CORE), Benchmark** | TWR, MWR/IRR, CAGR, Excess Return; volatilidad, downside deviation, max drawdown, TE, beta, VaR y ES históricos; eligibility de 8 dimensiones | Los tres marcados MVP obligatorio y Fase 1 del roadmap `[QM II, ROADMAP F1]` |
| M15 Explanation Layer | Para cada métrica incluida | Un motor sin su explicación no es un motor completo `[QM ROADMAP]` |
| M11 Diagnostic Synthesis | Multi-horizonte, con trazabilidad | `[DF 4.1, 6.2]` |
| M12 Trade-off | Detección y presentación de nueve pasos para los conflictos posibles con dos motores | `[DF 4.3]` |
| M13 Alternatives | Generación dinámica, incluida cardinalidad cero | `[DF 4.2]` |
| M14 Recommendation Layer | Niveles 0-3 con las reglas de bloqueo de 15.4 | `[DF 2.3]` |
| M16 WM Interface | V1 (limitada), V2, V3, V4 | `[QM XIX]` |
| M17 + M18 Audit y History | Completos, once campos | No negociable `[QM XXI]` |
| M22 Parameter Registry | Completo, con los parámetros pendientes existiendo como campos vacíos | `[DF READINESS]` |
| M23 Model Governance Registry | Registro mínimo: clasificación, responsable, fecha de validación | `[QM XIV]` |
| M10 DD & Approved List | **Versión mínima**: estado del vehículo, rating IDD/ODD, existencia del memo | Necesaria para no violar la regla de D3 `[QM XVIII D3]` |
| M25 Governance Interface | Solo el contrato de entrega | `[DF 3.1]` |

### 24.3 — Casos de uso incluidos en el MVP

| Caso | Nombre | Nivel alcanzable en el MVP | Por qué |
|---|---|---|---|
| 4 | Revisión periódica | 0-3 | Núcleo Performance + Risk, ambos en el MVP `[DF 7.3]` |
| 16 | Benchmark | Gate | Solo requiere Benchmark Engine |
| 2 | Diagnóstico inicial | 0-1 | Subconjunto según disponibilidad `[DF 7.3]` |
| 6 | Deterioro de fondo | 0-2 (3 solo con memo IDD/ODD) | Núcleo Performance + Monitoring; Monitoring en versión reducida sobre dos motores fuente `[QM ROADMAP F3]`; el Nivel 3 lo bloquea la regla de D3 `[QM XVIII D3]` |
| 12 | Cambio de riesgo | 0-2 | Núcleo Risk; el rediseño requiere Construction, fuera del MVP |

### 24.4 — Qué queda fuera del MVP y por qué

| Fuera del MVP | Razón (dependencia, no recorte arbitrario) |
|---|---|
| Construction Engine (MVO, Goal-Based Monte Carlo) | Requiere CMAs institucionales versionadas y matriz de covarianzas estable; Fase 2 del roadmap `[QM ROADMAP F2]` |
| Diversification Engine | Depende de Σ estable del Risk Engine maduro; Fase 2 `[QM ROADMAP F2]` |
| Liquidity Engine | Requiere calendario de flujos del cliente y clasificación completa de liquidez; su integración total depende de Alternatives; Fase 3 `[QM ROADMAP F3]` |
| Alternatives Engine | Requiere cashflows completos por fondo y vintage; Fase 4 `[QM ROADMAP F4]` |
| Scenario Engine | Requiere librería de escenarios definida por el Comité; Fase 4 `[QM ROADMAP F4]` |
| ClientGoal Engine | Requiere Construction y Scenario, y un proceso de IPS maduro; Fase 5 `[QM ROADMAP F5]` |
| Monitoring completo | Requiere varios motores fuente; en el MVP opera reducido `[QM II.8]` |
| Black-Litterman | Pendiente institucional, no técnico `[QM XXIII P1]` |
| Rebalanceo (D1) | Requiere Construction + Liquidity + Scenario `[DF 7.3]` |
| Rebalancing History View | SUPPORTING VIEW, depende de que exista historial de rebalanceos `[DF 6.6]` |
| Learning Loop | Requiere volumen de casos cerrados para producir evidencia |
| Vista de cliente (V5) | Depende del alcance de producto y del canal de entrega (ESFS-12) |

### 24.5 — El límite honesto del MVP

El MVP demuestra la cadena completa hasta **Nivel 3 en revisión periódica** y hasta **Nivel 2 en deterioro de fondo**. No puede alcanzar Nivel 3 en decisiones de cambio de fondo porque la metodología lo prohíbe sin evidencia de proceso, equipo y ODD `[QM XVIII D3]` `[V2 B11 P4]`. Presentar ese bloqueo como una funcionalidad del MVP —y no como una carencia— es parte de lo que el MVP debe demostrar: **el sistema declara sus límites en lugar de rellenarlos**.

---

## 25. Implementation Roadmap

Ocho fases. Las fases 3 y siguientes respetan la secuencia de motores del roadmap de `[QM ROADMAP]`, que se basa en dependencias reales entre motores y no en orden de exposición.

### Phase 0 — Foundations

| Campo | Contenido |
|---|---|
| **Objetivo** | Tener resueltas las condiciones sin las cuales programar produce retrabajo garantizado |
| **Dependencias** | Ninguna técnica; todas institucionales |
| **Inputs** | Documentos fuente; decisiones institucionales de AFI |
| **Entregables** | 1) Audit de la infraestructura de datos actual de AFI — **paso previo obligatorio** `[QM XXIII P5]`. 2) Parameter Registry con las seis categorías de gobernanza y todos los parámetros declarados, aunque sin valor. 3) Model Governance Registry con la clasificación CORE/ADVANCED/RESEARCH/REJECTED y responsable por modelo. 4) Decisión sobre los OPEN ISSUES bloqueantes de Fase 1 (ESFS-01, 03, 04, 09, 10). 5) Taxonomía institucional de asset classes y buckets de liquidez |
| **Datos necesarios** | Inventario real de fuentes, cobertura histórica y calidad disponible |
| **Riesgos** | Comenzar a construir sin el audit de infraestructura: el diseño asume datos que pueden no existir |
| **Criterio de completion** | Existe un inventario de fuentes con cobertura y calidad documentadas, y los cinco OPEN ISSUES bloqueantes tienen decisión registrada |

### Phase 1 — Data Foundation

| Campo | Contenido |
|---|---|
| **Objetivo** | Que los datos que el sistema necesita existan, con calidad verificada y trazabilidad de versión |
| **Dependencias** | Fase 0 |
| **Inputs** | Custodios, administradores, gestoras, proveedores de índices y de mercado, cliente vía asesor |
| **Módulos** | M03 IPS, M04 Portfolio State, M05 Vehículos y gestores, M06 Market & Reference Data, M07 Data Requirement Registry, M17 Audit Log |
| **Datos prioritarios** | NAV con frecuencia nativa · cash flows fechados y clasificados · FX · benchmarks e índices · IPS estructurado · clasificación de liquidez por vehículo · SAA vigente y bandas (ver Parte 29) |
| **Entregables** | Data Dictionary implementado; los diez controles de calidad de `[QM XVII]` operativos con su patrón Detection→Action→Warning→Fallback/Block; versionado de series con fecha de extracción |
| **Riesgos** | Flujos mal clasificados (invalida TWR y MWR simultáneamente); ausencia de histórico suficiente para ventanas de 3-5 años; umbral de gap sin definir (ESFS-09) |
| **Criterio de completion** | Para al menos un subconjunto real de clientes, todos los datos CRITICAL de la Parte 9.3 y 9.4 están disponibles, reconciliados y versionados |

### Phase 2 — Core Functional Architecture

| Campo | Contenido |
|---|---|
| **Objetivo** | Que exista un Decision Case que recorra el sistema y se registre, incluso con pocos motores |
| **Dependencias** | Fase 1 |
| **Módulos** | M01 Decision Intake, M02 Orchestrator, M08 Completeness Gate, M11 Diagnostic Synthesis, M15 Explanation Layer, M18 Decision History, M22, M23, M25 (contrato) |
| **Entregables** | Máquina de estados de la Parte 19 operativa; `AnalysisPlan` versionado; `CompletenessReport` con declaración de faltantes; explicación determinística reproducible |
| **Riesgos** | Implementar el Orchestrator con lógica de cálculo dentro (rompe `[DF 2.2]`); implementar la explicación como paso posterior en lugar de acoplada a cada motor `[QM ROADMAP]` |
| **Criterio de completion** | Un caso puede crearse, planificarse, bloquearse por datos, explicarse y registrarse de punta a punta sin ningún motor completo |

### Phase 3 — Quantitative Engines (secuencia obligatoria)

| Sub-fase | Motores | Por qué en este orden | Entregable | Fuente |
|---|---|---|---|---|
| 3.1 | Performance (CORE), Risk (CORE), Benchmark | Los tres de prioridad crítica/MVP obligatorio; Performance y Risk no pueden reportarse de forma responsable sin que Benchmark ya opere como gate | Reporting de performance y riesgo por cliente, con comparaciones solo contra benchmarks verificados | `[QM ROADMAP F1]` |
| 3.2 | Construction (MVO robusto + Goal-Based Monte Carlo), Diversification | Ambos dependen de que exista ya una matriz de covarianzas y un motor de riesgo estable | Capacidad de proponer portafolios objetivo y detectar concentraciones ocultas | `[QM ROADMAP F2]` |
| 3.3 | Liquidity, Monitoring | Monitoring requiere 2-3 motores fuente generando triggers; Liquidity puede desarrollarse en paralelo pero su integración completa depende de Alternatives | Book of business priorizado; primera versión de mapas de liquidez | `[QM ROADMAP F3]` |
| 3.4 | Alternatives, Scenario | Requieren Liquidity para consumir curvas de cash flow proyectado y Risk maduro para traducir alternativos a riesgo total | Integración completa de vehículos privados; stress testing sobre el portafolio total | `[QM ROADMAP F4]` |
| 3.5 | ClientGoal | Consume outputs de Construction y Scenario y requiere IPS maduro — dependencia técnica y organizacional | Dashboard de probabilidad de metas, cerrando el círculo hacia el Principio 1 | `[QM ROADMAP F5]` |

**Black-Litterman no tiene fase asignada:** su activación depende de una condición organizacional, no de una secuencia técnica; se activa cuando se resuelva el Pendiente 1, con independencia de la fase técnica en curso `[QM ROADMAP]` `[QM XXIII P1]`.

**Lo que este roadmap no incluye, explícitamente:** no hay fase de explicabilidad avanzada vía SHAP/LIME ni fase de Auto-Commentary; se eliminaron íntegramente al resolver la contradicción de `[QM XIX]`. La capa de explicación por reglas y plantillas no es una fase separada: se construye junto con cada motor `[QM ROADMAP]`.

### Phase 4 — Decision Layer

| Campo | Contenido |
|---|---|
| **Objetivo** | Completar Orchestrator → Diagnosis → Trade-offs → Alternatives → Recommendation para los flujos habilitados por los motores existentes |
| **Dependencias** | Fase 3.1 mínimo; se amplía con cada sub-fase de motores |
| **Módulos** | M12 Trade-off, M13 Alternatives, M14 Recommendation Layer |
| **Entregables** | Trade-offs con sus nueve pasos; alternativas dinámicas incluida cardinalidad cero; Niveles 0-3 con reglas de bloqueo |
| **Riesgos** | Introducir una ponderación implícita entre motores al ordenar los hallazgos (viola `[DF 4.3]`); fijar el número de alternativas (viola `[DF 4.2]`) |
| **Criterio de completion** | Un caso de revisión periódica alcanza Nivel 3 con sus nueve elementos, y un caso con IPS incompleto se detiene en Nivel 2 declarando por qué |

### Phase 5 — Wealth Manager Interface

| Campo | Contenido |
|---|---|
| **Objetivo** | Que el WM pueda decidir con el sistema, no consultarlo |
| **Dependencias** | Fase 4 |
| **Módulos** | M16 (V1-V4); M10 en versión completa para los flujos de fondo |
| **Entregables** | Las cuatro vistas internas; drill-down completo resultado→indicador→dato→fuente; registro de override con justificación obligatoria |
| **Riesgos** | Organizar la navegación por motor en lugar de por decisión (viola `[QM I.5]`); exponer el score inexistente por presión de usabilidad (viola `[DF 4.3]`) |
| **Criterio de completion** | Un WM real recorre un caso completo sin asistencia y puede responder por qué el sistema mostró cada cosa |

### Phase 6 — Tracking & Learning

| Campo | Contenido |
|---|---|
| **Objetivo** | Convertir decisiones registradas en evidencia institucional |
| **Dependencias** | Fase 5 y volumen suficiente de casos cerrados |
| **Módulos** | M19 Tracking, M20 Learning Loop, M21 Rebalancing History View (cuando exista historial de rebalanceos) |
| **Entregables** | Comparación expectativa vs. resultado; insumos para calibrar el umbral de materialidad de drift con evidencia real `[DF 6.6]` |
| **Riesgos** | Convertir el loop en un mecanismo automático de ajuste de metodología (prohibido `[DF 6.5]`); extender la vista longitudinal a otros módulos sin evidencia de valor `[DF 6.6]` |
| **Criterio de completion** | Existe evidencia documentada suficiente para que el Comité pueda discutir la calibración de al menos un umbral pendiente |

### Phase 7 — Validation

| Campo | Contenido |
|---|---|
| **Objetivo** | Validar modelos y comportamiento del sistema, incluidos los casos límite |
| **Dependencias** | Los motores que se validen deben estar operativos |
| **Entregables** | Por modelo: backtesting (mínimo anual), sensitivity analysis, parameter stability, out-of-sample testing, stress testing del modelo mismo, y controles de data quality `[QM XIV]`. Por sistema: pruebas de los casos límite de la Parte 20; prueba de reproducibilidad exacta de la explicación `[QM XIX]`; prueba de reconstrucción retrospectiva de un output `[QM XXI]` |
| **Riesgos** | Look-ahead bias en los backtests (rechazar el backtest si se detecta la fuga `[QM XVII]`) |
| **Criterio de completion** | Cada modelo CORE tiene responsable institucional designado y fecha de última validación registrada `[QM XIV]`; la degradación de un modelo funciona como proceso normal, no como incidente `[QM XIV]` |

---

## 26. Implementation Dependencies

### 26.1 — Grafo de precedencia (qué habilita qué)

```
Audit de infraestructura (Fase 0)
        │
        ▼
Parameter Registry + Model Governance Registry ──────────┐
        │                                                │
        ▼                                                │
NAV + Cash flows + FX ──► Performance ──┐                │
        │                               │                │
        ├──► Retornos ──► Risk ──────────┤                │
        │                  │             │                │
Benchmark + Eligibility ───┴─────────────┤ (gate)         │
        │                                │                │
IPS ────┴──► ClientGoal ◄── Construction ◄── CMAs + Σ     │
                 ▲              │                         │
                 │              ▼                         │
Scenario Library ─┴──► Scenario ──► Liquidity ◄── Alternatives ◄── Cashflows PE
                                        ▲
                        Calendario de flujos del cliente
                                        │
        Todos los anteriores ──► Monitoring ──► Tracking ──► Learning Loop
                                        ▲
                        M10 (IDD/ODD/Approved List) ──► D3/D4/D5/D11/D14
```

### 26.2 — Prerrequisitos por módulo

| Módulo | No se puede construir hasta que exista |
|---|---|
| Performance | NAV + flujos fechados y clasificados |
| Métricas relativas (Excess Return, TE, beta, IR) | Benchmark Engine con eligibility resuelta |
| Risk CORE | Serie de retornos con ventana suficiente + FX |
| Diversification | Σ del Risk Engine + taxonomía de buckets |
| Construction | CMAs institucionales versionadas + constraints + Approved List |
| Liquidity | Calendario de flujos del cliente + clasificación de liquidez por vehículo |
| Alternatives | Cashflows completos por fondo y vintage |
| Scenario | Librería de escenarios definida y versionada por el Comité |
| Monitoring | 2-3 motores fuente operativos + umbrales de trigger |
| ClientGoal | IPS vigente con metas cuantificables + Construction + Scenario |
| Trade-off (filtrado) | Umbral de activación de conflicto (ESFS-07) |
| Rebalanceo (D1 completo) | SAA vigente + bandas + umbral de materialidad (ESFS-08) |
| Nivel 3 en D3/D4/D5 | Memo con proceso, equipo y ODD en M10 |
| Learning Loop | Volumen de casos cerrados con resultado observado |

### 26.3 — Componentes paralelizables desde el inicio

Benchmark Engine · Parameter Registry · Model Governance Registry · Audit Log · Scenario Library (captura, no ejecución) · M10 (proceso de DD, que es más organizacional que técnico) · Explanation Layer por métrica ya implementada.

---

## 27. Open Issues Register

### 27.1 — Issues detectados en esta traducción funcional (nuevos)

| ID | Issue | Por qué importa | Módulo afectado | Información necesaria | Prioridad | Decisión requerida de |
|---|---|---|---|---|---|---|
| **ESFS-01** | `[DF 2.3, 4.4]` habla de "ocho elementos" de una recomendación de Nivel 3 y enumera nueve ítems | Es el contrato de un artefacto central del sistema; un checklist ambiguo produce recomendaciones incompletas o inconsistentes | M14 Recommendation Layer | Lista canónica: ¿"datos faltantes y limitaciones" es un elemento o dos? | **Alta — bloqueante de Fase 4** | Autor/custodio del Decision Framework v1.1 |
| **ESFS-02** | `[DF 2.1]` prohíbe al Monitoring Engine colapsar "las seis dimensiones de un mismo cliente" en un score, pero nunca las enumera | Sin la enumeración no se puede verificar el cumplimiento de la prohibición ni diseñar el heatmap | M09 Monitoring, M16 V1 | Las seis dimensiones canónicas. Nota: `[QM XI]` define cinco dimensiones de escenario (retorno, riesgo, liquidez, concentración, objetivos), que no coinciden en número | Media | Autor/custodio del Decision Framework v1.1 |
| **ESFS-03** | `[QM XIII]` titula "Rebalancing Engine" una metodología completa, pero la lista canónica `[DF 2.1]` tiene diez motores y no lo incluye | Determina si el rebalanceo es un módulo con identidad propia (registro de triggers, estado, vista histórica) o un flujo sobre cuatro motores | Catálogo de módulos, M21 | Confirmación de si es flujo o motor | **Alta — bloqueante del catálogo** | Investment Committee / custodio de la metodología |
| **ESFS-04** | La Due Diligence de gestores y la Approved List `[V2]` son obligatorias (motor núcleo del caso 7 `[DF 7.3]`, reglas de D3/D14) pero no son uno de los diez motores | Sin ubicación arquitectónica definida, el módulo queda sin owner, sin contrato de interfaz y sin fase asignada | M10 | Definir si es motor, módulo de flujo, o registro con reglas de negocio | **Alta — bloqueante de Fase 5 y del Nivel 3 en decisiones de fondo** | Investment Committee |
| **ESFS-05** | Conteo e identificadores de la Decision Library: "quince decisiones" con identificadores D1-D14 `[DF 3.1, 5]`; estados de vehículo con dos listas distintas (`[QM XVIII D3]`: Approved-Active/Watchlist/Restricted/Removed; `[V2 B11 P6]`: Proposed/Approved/Watchlist/Removed/Exception) | El Decision History y el Audit Log necesitan identificadores canónicos únicos; los estados de vehículo necesitan una lista única | M10, M17, M18 | Identificadores canónicos y lista única de estados | Media | Investment Committee |
| **ESFS-06** | No existe mapeo declarado entre los once flujos operativos `[DF 7.1]` y los dieciocho casos de uso `[DF 7.3]`; los casos 11, 12 y 13 no tienen flujo dedicado | El Orchestrator no puede enrutar de forma determinística sin ese mapeo | M02 Orchestrator | Matriz caso de uso × flujo | **Alta — bloqueante de Fase 2** | Custodio de la metodología |
| **ESFS-10** | Mínimos de observaciones no fijados para varias métricas: VaR, ES, correlación, beta (sí están fijados para TE: 36-60 obs.; volatilidad y correlación: ventana 3-5 años "cuando disponible") | Sin mínimo, `insufficient_data` no es decidible para esas métricas y el Completeness Gate no puede bloquear ni advertir | M08, M09 Risk y Diversification | Mínimo de observaciones por métrica y por frecuencia nativa | **Alta — bloqueante de Fase 3.1** | Equipo de datos + Comité de Model Risk |
| **ESFS-11** | Ningún documento define cuándo un Decision Case se cierra, ni la retención del registro | Afecta la máquina de estados, el volumen de datos y la operación del Learning Loop | M18, M19, máquina de estados | Criterio de cierre y política de retención | Media | AFI (operaciones + compliance) |
| **ESFS-12** | El sistema nunca comunica al cliente de forma autónoma `[QM XX]`, pero existe una plantilla de cliente `[QM XIX]` y `[V3]` proponía un portal de cliente | Determina si la vista de cliente está dentro del producto (con acto humano de liberación) o fuera de él | M16 V5 | Decisión de alcance de producto y canal de entrega | Media | AFI (Senior Management) |
| **ESFS-13** | Los límites numéricos de corto, mediano y largo plazo no están definidos y dependen del IPS | Todo análisis relevante debe etiquetarse por horizonte `[DF 6.2]`; sin límites, el etiquetado no es consistente entre clientes | M03, M11 | Definición por defecto institucional + override por IPS | Media | Investment Committee |
| **ESFS-14** | En el Benchmark Eligibility Framework no está enumerado de forma cerrada qué dimensiones son "críticas" (`[QM XVIII D10]` dice "particularmente moneda, liquidez o restricciones regulatorias") y el estado "parcial" `[QM II.9]` no tiene semántica operativa definida | Determina cuándo se bloquea una comparación y qué puede hacerse con un benchmark parcialmente elegible | M09 Benchmark | Lista cerrada de dimensiones críticas y reglas de uso del estado parcial | **Alta — bloqueante de Fase 3.1** | Investment Committee |
| **ESFS-15** | El caso de uso 2 (Diagnóstico inicial) define sus motores como "subconjunto según disponibilidad" `[DF 7.3]`, sin mínimo declarado | El sistema no puede determinar cuándo un diagnóstico inicial está suficientemente completo para presentarse, ni qué declarar como pendiente | M02 Orchestrator, M11 | Mínimo de motores o de dimensiones que debe cubrir un diagnóstico inicial para ser presentable | Media | Custodio de la metodología |
| **ESFS-23** | El período de retención necesario para la reconstrucción fiduciaria no está definido en las fuentes | Afecta el diseño del versionado y del Audit Log, que es un componente de primera clase `[QM XXI]` | M17 | Período aplicable según el deber fiduciario y la regulación local | Media | AFI (compliance) |

### 27.2 — Issues heredados del Decision Framework v1.1 (`[DF 8.3]`), sin resolver en ESFS-01

| ID | Issue | Por qué importa para la implementación | Módulo afectado | Prioridad | Decisión requerida de |
|---|---|---|---|---|---|
| **ESFS-21** | Governance & Escalation Rules: qué umbral de monto, riesgo o tipo de cliente determina si una decisión corresponde al WM, a un Senior o al Investment Committee | Se implementa como interfaz con contrato definido y reglas internas vacías `[DF READINESS]`; sin las reglas, la escalada es manual | M25 | Alta para operación, no para construcción | Investment Committee y Senior Management de AFI |
| **ESFS-07** | Umbral de activación del Trade-Off Framework: qué constituye un conflicto activable | Sin él, el sistema no puede filtrar oposiciones triviales | M12 | Media (parámetro configurable desde el inicio) | AFI, con evidencia operativa |
| **ESFS-08** | Umbral de materialidad del drift `[DF 6.4]` | El paso de Materiality no puede filtrar desviaciones triviales; D1 queda incompleto | Flujo de rebalanceo | Alta para D1 | Investment Committee |
| **ESFS-16** | Reglas más granulares de generación de alternativas (2 vs. 3 vs. 4) | Sin ellas, el número queda a criterio del diseño de cada flujo, lo que es aceptable pero no verificable | M13 | Baja | Custodio de la metodología |
| **ESFS-17** | Formal Priority Framework y Formal Trade-Off Resolution Framework | Clasificados RESEARCH; requieren evidencia del Rebalancing History View y casos reales documentados | Fuera del núcleo | Baja | Metodológica / Governance |
| **ESFS-18** | Extensión futura de Historical Views a otros módulos | Explícitamente no evaluado por falta de evidencia de necesidad | M21 | Baja | Producto / Tecnología |
| **ESFS-22** | Parameter Governance: los valores numéricos específicos de los parámetros institucionales siguen pendientes de calibración | El sistema se construye pero no se opera sin ellos | M22 | Alta para operación | Investment Committee |

### 27.3 — Issues heredados de la Quantitative Methodology v1.0 (`[QM XXIII]`)

| ID | Issue | Impacto funcional | Módulo afectado | Prioridad | Decisión requerida de |
|---|---|---|---|---|---|
| **ESFS-19** | Activación de Black-Litterman: falta evidencia de que el Comité sostenga el proceso Evidencia→View→Convicción de forma disciplinada, con 2-3 ciclos documentados | BL se implementa como feature deshabilitada por gobernanza, no como funcionalidad ausente | M09 Construction | Baja para MVP | Investment Committee |
| **ESFS-09** | Umbral exacto de "gap significativo" en Missing Data | **El Completeness Gate no puede distinguir gap tolerable de gap bloqueante**; opera en modo binario hasta que exista | M08 | **Alta — bloqueante de Fase 1** | Equipo de datos de AFI, calibrado contra el universo real de vehículos |
| **ESFS-20** | Definición operacional de Effective Number of Bets: la fórmula propuesta es una inferencia metodológica razonable, no un hallazgo respaldado por un paper específico | La métrica no debería exponerse como CORE al Comité sin validación o sin aceptarla explícitamente como convención propia de AFI | M09 Diversification | Media | Investment Committee |
| **ESFS-08b** | Umbrales exactos de triggers de rebalanceo y de deterioro de gestores (bandas ±%; trimestres consecutivos de alpha negativo) | Monitoring y el flujo de rebalanceo calculan pero no clasifican | M09 Monitoring, flujo de rebalanceo | Alta para operación | Investment Committee |
| **ESFS-24** | Capacidad tecnológica real vs. diseño conceptual: no existe audit de la infraestructura de datos actual de AFI | **Paso previo obligatorio a cualquier desarrollo de software** `[QM XXIII P5]` | Todo | **Máxima — bloqueante de Fase 0** | Equipo técnico de AFI |
| **ESFS-25** | Alcance de ESG: ¿política institucional uniforme o definida caso a caso por IPS? La categoría de parámetro no está resuelta | Afecta el modelo de datos del IPS y los constraints de Construction | M03, M09 Construction, M22 | Media | Investment Committee |

### 27.4 — Los cinco issues bloqueantes del inicio de la construcción

Si mañana empezara el desarrollo, estos cinco deben resolverse primero:

| Orden | ID | Qué bloquea |
|---|---|---|
| 1 | ESFS-24 | Todo — sin audit de infraestructura, el diseño asume datos que pueden no existir |
| 2 | ESFS-09 | El Data Completeness Gate, que es el componente diferencial del sistema |
| 3 | ESFS-10 | La capacidad de declarar `insufficient_data` en las métricas de riesgo |
| 4 | ESFS-06 | El enrutamiento determinístico del Orchestrator |
| 5 | ESFS-03 y ESFS-04 | El catálogo de módulos y sus owners |

---

## 28. Architecture Decisions

Formato: **Decisión → Rationale → Source → Consequence → Open Issue.** Ninguna decisión técnica prematura: ESFS-01 es funcional.

| ID | Decisión | Rationale | Source | Consequence | Open Issue |
|---|---|---|---|---|---|
| **AD-01** | La unidad de vida del sistema es el `DecisionCase`, no el cálculo | La cadena del framework parte de una pregunta y termina en History; sin un objeto que la represente, la trazabilidad decisión→dato es imposible | `[DF 4.1, 6.5]` `[QM XXI]` | Todo output pertenece a un caso; todo caso tiene estado y versión | ESFS-11 (criterio de cierre) |
| **AD-02** | El Orchestrator no contiene ninguna fórmula | Si necesitara un cálculo nuevo, eso sería por definición un motor nuevo, y no se introduce ninguno | `[DF 2.2]` | Toda necesidad de cálculo detectada en el Orchestrator es un hallazgo que se eleva, no se implementa ahí | — |
| **AD-03** | La Recommendation Layer es una capa separada del Orchestrator | Resuelven preguntas de naturaleza distinta: cobertura/selección vs. suficiencia de evidencia | `[DF 2.3, 2.4]` | El `AnalyticalOutput` declara el nivel alcanzado y por qué no alcanzó uno superior | ESFS-01 (elementos de Nivel 3) |
| **AD-04** | El rebalanceo se implementa como flujo sobre cuatro motores, no como motor número once | Crear motores nuevos está prohibido y la secuencia de `[DF 6.4]` no introduce fórmulas ajenas a Construction, Risk, Liquidity y Scenario | `[DF 6.4, 7.1, 20]` `[QM XIII]` | El rebalanceo no tiene owner de motor; sus triggers viven en el Parameter Registry y su historial en M21 | **ESFS-03** |
| **AD-05** | La Due Diligence y la Approved List se modelan como módulo funcional obligatorio (M10), fuera de los diez motores | Es requisito de reglas de negocio explícitas (D3, D14) y aparece como motor núcleo del caso 7, pero no está en la lista canónica de motores | `[DF 7.3]` `[QM XVIII D3, D14]` `[V2]` | Sin M10, Nivel 3 queda bloqueado en decisiones de fondo; el MVP incluye su versión mínima | **ESFS-04** |
| **AD-06** | La criticidad de cada dato se deriva con una regla explícita (8.2), no se declara caso por caso | `[DF 6.1]` define los tres comportamientos pero no clasifica campos; sin regla de derivación, Data Completeness no es implementable | `[DF 6.1]` `[QM XVII]` | La matriz de la Parte 9 es auditable: cada criticidad se puede rebatir contra la regla | ESFS-09, ESFS-10 |
| **AD-07** | `insufficient_data` es un estado de primera clase del resultado, no un error | Exigido explícitamente: nunca un número calculado sobre datos pobres con la misma confianza visual | `[QM XIV]` `[QM I.8]` | La interfaz debe tener una representación visual distinta para este estado, no un campo vacío | — |
| **AD-08** | La Explanation Layer se acopla a cada motor y se construye con él | Un motor sin su capa de explicación determinística no es un motor completo | `[QM XIX]` `[QM ROADMAP]` | No existe una fase de "explicabilidad"; el costo se distribuye en cada motor | — |
| **AD-09** | Todo es versionado; nada se sobrescribe | La reconstrucción en cualquier momento futuro es imposible si el sistema sobrescribe resultados, parámetros o datos | `[QM XXI]` `[QM XV]` | Re-ejecución genera nueva versión del caso; el resultado anterior permanece consultable | ESFS-23 (retención) |
| **AD-10** | Los umbrales pendientes existen como parámetros vacíos desde Fase 0, no como constantes futuras | Deben especificarse como configurables desde el inicio, precisamente porque su calibración depende de evidencia que aún no existe | `[DF READINESS]` | El sistema puede calcular sin ellos y declara "umbral institucional pendiente" en lugar de clasificar | ESFS-22, ESFS-07, ESFS-08 |
| **AD-11** | No existe ningún campo de score agregado en ningún artefacto del sistema | Ningún motor se pondera contra otro; el Monitoring prioriza entre cuentas pero no colapsa dimensiones de un mismo cliente | `[DF 2.1, 4.3, 8.2]` | La interfaz debe resolver la priorización visual sin un número único, lo que es más difícil de diseñar y es el costo aceptado | ESFS-02 (cuáles son las dimensiones) |
| **AD-12** | El gate de benchmark es automático; la excepción es gobernanza | Es una verificación técnica de comparabilidad, no una decisión sobre el patrimonio | `[DF 6.3]` `[QM XVIII D10]` | Ninguna comparación relativa existe sin `EligibilityCheck` previo; la excepción requiere registro documentado del Comité | ESFS-14 |
| **AD-13** | El conflicto entre outputs de motores se trata como trade-off, no como error | El framework lo define como situación esperada con arquitectura de presentación propia | `[DF 4.3]` | El catálogo de errores excluye explícitamente este caso, para que nadie lo implemente como excepción | ESFS-07 |
| **AD-14** | `AlternativeSet` de cardinalidad cero es un resultado válido y completo | Regla de honestidad epistémica: el sistema no inventa alternativas para llenar un formato | `[DF 4.2]` | La interfaz debe tener un estado de presentación para "sin alternativas evaluables" acompañado de qué información permitiría avanzar | — |
| **AD-15** | El módulo de gobernanza se implementa como interfaz con reglas internas vacías | Es exactamente el estatus que el framework le asigna: contrato definible, reglas institucionales no anticipables | `[DF 3.1]` `[DF READINESS]` | La escalada es manual hasta que AFI defina las reglas; el sistema no sugiere instancia ni por defecto al WM | **ESFS-21** |
| **AD-16** | El intake clasifica preguntas por reglas, no por modelo de lenguaje | El producto no incorpora LLM; la clasificación debe ser auditable y reproducible | `[QM 0, XIX]` | Preguntas no mapeables van a `unmapped_question` y se revisan humanamente, en lugar de forzarse a un flujo aproximado | ESFS-06 |
| **AD-17** | La comparación entre vehículos se hace siempre a la frecuencia nativa más baja común, sin interpolar | Regla CORE explícita; interpolar crearía precisión inexistente y subestimaría el riesgo de los privados | `[QM IV, XVII]` | El sistema debe almacenar la frecuencia nativa por serie y calcular la frecuencia efectiva de cada comparación | — |
| **AD-18** | El NAV privado nunca se trata como precio de mercado, y todo cálculo que lo incluya declara el ajuste por smoothing o su ausencia | Las valuaciones trimestrales introducen smoothing que subestima volatilidad y sobreestima correlación | `[QM X]` | Todo output de Risk y Diversification que incluya privados lleva una declaración obligatoria | — |
| **AD-19** | Multi-horizonte se implementa como estructura del diagnóstico, no como filtro de la interfaz | Las conclusiones por horizonte se muestran lado a lado y no se promedian ni se elige la más favorable | `[DF 6.2]` | El artefacto `Diagnosis` tiene dimensión de horizonte obligatoria, no opcional | ESFS-13 |
| **AD-20** | El Learning Loop produce evidencia, no ajustes | Es un loop institucional, no un sistema de aprendizaje automático; la metodología no se modifica automáticamente | `[DF 6.5]` | Ningún parámetro cambia sin pasar por el Parameter Registry con aprobador y justificación | — |
| **AD-21** | ESFS-01 no decide arquitectura técnica | El mandato lo separa explícitamente; decidir técnica ahora sería decidir sin el audit de infraestructura | Mandato §18 · `[QM XXIII P5]` | Las decisiones de stack, almacenamiento y latencia quedan para el documento siguiente, con el audit como input | **ESFS-24** |

---

## 29. Data Acquisition Priorities

Prioridad de adquisición basada en cuánta funcionalidad desbloquea cada dato, tomada del conteo de 9.11 y del grafo de 26.1. No es una lista de deseos: es el orden en que conseguir datos produce sistema utilizable.

### 29.1 — Prioridad 1: sin estos datos no hay sistema

| Dato | Fuente | Qué desbloquea | Calidad mínima exigida |
|---|---|---|---|
| Serie de NAV por vehículo, con frecuencia nativa declarada | Custodio / administrador | Performance completo, Risk completo, Diversification, Alternatives (RVPI) | Sin gaps no explicados; reconciliado contra fuente secundaria cuando sea posible; frecuencia nativa preservada `[QM XVI]` |
| Cash flows fechados y clasificados (aporte / retiro / fee) | Custodio / administrador | TWR, MWR/IRR, Liquidity, Alternatives | Fecha y monto exactos, clasificación correcta `[QM XVI]` |
| Serie FX | Proveedor de mercado | Todo cálculo multi-moneda; su ausencia es Model Block | Consistente entre todos los cálculos multi-moneda `[QM XVI]` |
| IPS estructurado, vigente y firmado | Asesor + Cliente, aprobado por Comité | ClientGoal, Construction, y el juicio de compatibilidad de todo output | Documentado, no informal; firmado y vigente `[QM XVI]` |
| Series de benchmarks e índices | Proveedores de índices | Excess Return, TE, beta, atribución, toda comparación relativa | Metodología documentada y estable; serie histórica suficientemente larga `[QM XVI]` |
| Definición de las ocho dimensiones del portafolio y del benchmark candidato | Interna + índices + reglamento | El gate de elegibilidad, que condiciona Performance y Risk | Verificable dimensión por dimensión; lo no verificable se marca como tal `[QM XXIV]` |
| Clasificación de liquidez por vehículo (valuación, ventana de redención, lock-up) | Reglamento / gestora | Liquidity completo; constraints de Construction | Clasificación correcta por vehículo `[QM XXII]` |
| SAA vigente y bandas configuradas | Investment Committee | Drift, materialidad, D1 completo | Versionada, con fecha de vigencia |

### 29.2 — Prioridad 2: desbloquean motores de Fase 2 y 3

| Dato | Fuente | Qué desbloquea |
|---|---|---|
| Capital Market Assumptions institucionales versionadas | Investment Committee | MVO robusto, Goal-Based Monte Carlo, Risk Parity |
| Curvas de tasas completas (no puntos aislados) | Bancos centrales / proveedores | Riesgo de tasas, escenarios |
| Calendario de flujos esperados del cliente | Cliente vía asesor | LCR, Ladder, cash flow forecasting |
| Life balance sheet | Cliente vía asesor | El límite de peso en ilíquidos, que es función del balance extendido `[QM IX]` |
| Estado en Approved List + ratings IDD/ODD | M10 / Comité | D3, D4, D5, D14 y el Nivel 3 en decisiones de fondo |
| Factsheet vigente y reglamento/prospecto | Gestora / regulador | Aprobación del vehículo; verificación de universo y restricciones |
| Umbrales de trigger (aunque sean provisionales y declarados como tales) | Investment Committee | Monitoring con capacidad de clasificar, no solo de calcular |

### 29.3 — Prioridad 3: desbloquean motores de Fase 4 y 5

| Dato | Fuente | Qué desbloquea |
|---|---|---|
| Cashflows completos por fondo privado y vintage | Gestora | TVPI, DPI, RVPI, IRR; sin ellos no se calculan métricas parciales sin advertencia |
| Capital calls y distributions con fecha, monto y vehículo identificado | Gestora | Integración de privados en Liquidity |
| Curvas históricas de cash flow por estrategia y vintage | Interna / gestoras | Pacing y simulación de NAV futuro (ADVANCED) |
| Librería de escenarios históricos e hipotéticos versionada | Investment Committee | Scenario Engine completo |
| Holdings subyacentes (look-through) cuando existan | Gestora | Factor risk y detección de concentración con look-through |
| Índices públicos comparables para PME | Proveedores | PME / Direct Alpha (ADVANCED) |
| Metas cuantificadas por cliente | Cliente vía asesor | Probabilidad de éxito por meta |

### 29.4 — Datos que la metodología usa pero que no se adquieren: se producen internamente

Retornos derivados de NAV ajustados por flujos · matriz de covarianzas con shrinkage · TWR/MWR y derivados · HHI y risk contribution · estados de elegibilidad · resultados de motores. Todos son **calculados**, no fuentes: su calidad depende enteramente de la Prioridad 1 `[QM XVI]`.

---

## 30. Final Readiness Assessment

### 30.1 — Auditoría interna contra las catorce preguntas del mandato

| # | Pregunta | Respuesta | Evidencia / qué falta |
|---|---|---|---|
| 1 | ¿Puede un desarrollador entender qué debe construir? | **Sí, con cinco issues bloqueantes** | Partes 6, 10, 11 (contratos por módulo), 19 (estados), 20 (errores), 24-26 (qué primero). Falta: ESFS-03, 04, 06 definen catálogo y enrutamiento |
| 2 | ¿Puede un data engineer entender qué datos necesitamos? | **Sí, con dos issues bloqueantes** | Partes 8, 9 (matriz por métrica), 29 (prioridades). Falta: ESFS-09 (umbral de gap) y ESFS-10 (mínimos de observaciones) |
| 3 | ¿Puede un Wealth Manager entender cómo utilizará el sistema? | **Sí** | Partes 17 (cinco vistas y ciclo de trabajo), 18 (siete escenarios paso a paso) |
| 4 | ¿Cada engine tiene inputs y outputs identificados? | **Sí** | Parte 11: los diez motores con inputs, procesamiento CORE/ADVANCED, outputs, dependencias, frecuencia, activación, bloqueo y errores |
| 5 | ¿Cada input tiene una justificación funcional? | **Sí** | Parte 9: cada fila declara la decisión y el output que habilita; regla de admisión explícita |
| 6 | ¿Está clara la diferencia entre Orchestrator, Engines, Diagnostic y Recommendation Layer? | **Sí** | Partes 5.2 (con test de separación), 7, 11.0, 12, 15 |
| 7 | ¿Está preservado Decision Framework v1.1? | **Sí** | Cero modificaciones. Las tres inconsistencias detectadas se registran como OPEN ISSUES (ESFS-01, 02, 03), no se corrigen |
| 8 | ¿Está preservada la autonomía Level 0-3? | **Sí** | Parte 16, con reglas de bloqueo derivadas de reglas de negocio existentes |
| 9 | ¿Está excluida la ejecución automática? | **Sí** | AP-1, Parte 6.2, Parte 16.1: Nivel 4 no existe; el rebalanceo nunca se convierte en ejecución automática |
| 10 | ¿Está excluido el LLM del producto? | **Sí** | AP-4, Parte 6.2, AD-16: explicación determinística por reglas y plantillas; SHAP/LIME y Auto-Commentary rechazados |
| 11 | ¿Está identificada toda información faltante? | **Sí, hasta donde las fuentes permiten verificarlo** | Parte 27: 26 issues, con 13 nuevos detectados en esta traducción y 13 heredados, cada uno con responsable |
| 12 | ¿El documento permite pasar a Data Architecture? | **Sí** | Partes 8 (nueve dimensiones, entidades, estados, calidad), 9 (matriz), 29 (prioridades). Requisito previo: ESFS-24 (audit de infraestructura) |
| 13 | ¿El documento permite pasar a Technical Architecture? | **Sí** | Partes 6 (capas y módulos), 19 (estados), 21 (versionado y auditoría), 23-26 (dependencias). No se toma ninguna decisión técnica prematura (AD-21) |
| 14 | ¿Permite comenzar la implementación con Claude Code? | **Sí para Fases 0-2; condicionado para Fase 3** | Los contratos de módulo y la matriz de datos son suficientes para especificar tareas. Fase 3.1 requiere ESFS-10 y ESFS-14 resueltos para que los motores puedan declarar `insufficient_data` y operar el gate de benchmark correctamente |

### 30.2 — La pregunta central del mandato

> *"Si mañana tuviéramos que comenzar a construir esta aplicación, ¿sabemos exactamente qué debe hacer, qué información necesita y en qué orden debemos construirlo?"*

**Qué debe hacer:** sí. Los 25 módulos de la Parte 6 tienen responsabilidad exclusiva, contrato de entrada y salida, y prohibiciones explícitas; los diez motores están mapeados sin agregar ninguno; la cadena de decisión está desarrollada paso a paso con el artefacto que produce cada uno.

**Qué información necesita:** sí, con dos vacíos que impiden operar —no construir— el componente diferencial del sistema. La matriz de la Parte 9 especifica cada input con sus nueve dimensiones; lo que falta es el umbral de "gap significativo" (ESFS-09) y los mínimos de observaciones de varias métricas de riesgo (ESFS-10). Sin ellos el Data Completeness Gate se puede construir, pero solo puede distinguir presencia de ausencia, no tolerancia.

**En qué orden:** sí. Ocho fases con dependencias justificadas, cinco issues bloqueantes ordenados por prioridad, y una secuencia de motores que no es la de exposición de los documentos sino la de dependencia real entre ellos.

**Lo que no sabemos, y no se rellenó:** nueve parámetros institucionales sin valor; las reglas de escalamiento; la ubicación arquitectónica de la Due Diligence; el estatus del rebalanceo como módulo; el mapeo entre flujos y casos de uso; y si la infraestructura de datos actual de AFI soporta lo que este documento especifica. Los 26 issues de la Parte 27 tienen responsable asignado; ninguno tiene un supuesto en su lugar.

### 30.3 — Clasificación de cierre

**READY FOR DATA ARCHITECTURE AND TECHNICAL ARCHITECTURE — WITH FIVE BLOCKING OPEN ISSUES.**

El documento es suficiente para especificar tareas de construcción de las Fases 0 a 2 de inmediato. Las Fases 3 y siguientes requieren que se resuelvan ESFS-24, 09, 10, 06 y el par 03/04.

La pregunta que este documento deja abierta para AFI, y que ningún ejercicio de arquitectura puede responder por la organización, es la misma que el propio framework declaró al cerrar: **no si el sistema puede construirse, sino si AFI está lista para operarlo** — con IPS estructurados, CMAs institucionales, escenarios definidos por Comité, umbrales calibrados y reglas de escalamiento decididas `[QM XXIII P1, P4, P5]` `[DF 8.3]`.

---

## Anexo A — Índice de trazabilidad de reglas críticas

Reglas que un implementador puede violar sin darse cuenta, con su fuente exacta, para uso como checklist de revisión de código y de diseño.

| Regla | Fuente | Dónde puede romperse |
|---|---|---|
| Ningún motor produce una instrucción de acción | `[DF 2.1]` | Nombres de campos de output ("recommended_action" en un motor) |
| El Orchestrator no calcula | `[DF 2.2]` | Un promedio, un ranking o una normalización "de conveniencia" dentro del Orchestrator |
| La Recommendation Layer no calcula nada nuevo | `[DF 2.3]` | Un cálculo de "score de consistencia" entre alternativas |
| Sin ponderación automática entre motores | `[DF 4.3]` | El orden de presentación de hallazgos implicando jerarquía; cualquier peso implícito |
| Número de alternativas dinámico | `[DF 4.2]` | Un array de tamaño fijo tres, heredado del patrón de rebalanceo |
| Cardinalidad cero de alternativas es válida | `[DF 4.2]` | Tratar el conjunto vacío como error o como estado no renderizable |
| Nunca imputar silenciosamente | `[DF 6.1]` | `fillna()` o forward-fill en la preparación de series |
| Nunca interpolar frecuencia faltante | `[QM XVII]` | Resampleo automático al unir series de distinta frecuencia |
| Comparar a la frecuencia nativa más baja común | `[QM IV]` | Anualizar una serie trimestral y compararla con una diaria sin declararlo |
| Sin benchmark elegible no hay ranking | `[QM XII]` | Calcular Excess Return antes de consultar el gate |
| Dimensión no verificable ≠ dimensión aprobada | `[QM XXIV]` | Un valor por defecto "true" en la verificación de comparabilidad |
| NAV privado no es precio de mercado | `[QM X]` | Unir NAV trimestral de privados con series diarias en la misma matriz de covarianzas sin declarar el ajuste |
| Sin cashflows completos no hay métricas parciales de PE sin advertencia | `[QM XXIV]` | Calcular TVPI con cashflows incompletos |
| `insufficient_data` no es un campo vacío | `[QM XIV]` | Renderizar `null` como guion o como cero |
| Un output sin registro de auditoría no es válido | `[QM XXI]` | Cálculos ad-hoc, pruebas o vistas que no escriben el log |
| Nada se sobrescribe | `[QM XXI]` | Actualizar un resultado en lugar de crear una versión |
| Ningún score global de cliente o portafolio | `[DF 2.1, 4.3]` | Un indicador de "salud del portafolio" en la interfaz |
| El Monitoring excluye con nota, no omite en silencio | `[QM XXIV]` | Filtrar componentes en `insufficient_data` de la priorización |
| Sin memo de proceso, equipo y ODD no hay Nivel 3 en decisiones de fondo | `[QM XVIII D3]` `[V2 B11 P4]` | Permitir Nivel 3 con solo evidencia de performance |
| ODD Fail/High-Risk ⇒ vehículo inelegible | `[V2 B11 P1]` | Tratar el ODD como un input ponderable del rating global |
| BL no se ejecuta sin views documentadas y aprobadas | `[QM XXIV]` | Un valor por defecto de views vacías que deja correr el modelo |
| El sistema no comunica al cliente | `[QM XX]` | Cualquier envío automático de la vista de cliente |
| El sistema no asigna instancia de gobernanza, ni por defecto al WM | `[DF 3.1]` | Un campo `assigned_to` calculado |
| Horizontes lado a lado, sin promediar | `[DF 6.2]` | Consolidar horizontes en una única conclusión |
| Todo escenario reporta las cinco dimensiones | `[QM XI]` | Un escenario que devuelve solo impacto en retorno |
