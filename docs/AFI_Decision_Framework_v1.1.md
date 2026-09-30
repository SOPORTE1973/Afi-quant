# AFI DECISION FRAMEWORK v1.1

**Framework operativo consolidado — puente entre AFI Quantitative Methodology v1.0 y la AFI Expert System Functional Specification (ESFS)**

---

## Resumen Ejecutivo

AFI Decision Framework v1.1 define cómo el sistema AFI recorre la información disponible sobre un cliente, un portafolio o un fondo para transformarla en evidencia estructurada que el Wealth Manager (WM) pueda usar para decidir. El framework se apoya en diez motores cuantitativos ya especificados en AFI Quantitative Methodology v1.0 — Performance, Risk, Diversification, Liquidity, Benchmark, Scenario, Portfolio Construction, Alternatives, Goals y Monitoring — y organiza su activación, combinación y presentación mediante tres capas conceptuales separadas: los **Quantitative Engines**, que calculan y diagnostican sin decidir; el **Decision Orchestrator**, que coordina qué motores activar y cómo combinar sus outputs sin generar ninguna métrica propia; y la **Recommendation Layer**, que evalúa si existe evidencia suficiente para una recomendación analítica de Nivel 3 sin ejecutar cálculos ni determinar quién debe decidir.

El sistema nunca decide por el Wealth Manager. Presenta problema, evidencia, magnitud, impacto, alternativas cuando existen, y — cuando la evidencia lo sostiene — una recomendación analítica. La instancia de gobernanza que corresponde a cada decisión de cliente (¿la resuelve el WM, un Senior, el Investment Committee?) es una decisión institucional de AFI, no una salida del sistema. Esto es distinto de la gobernanza sobre los propios modelos cuantitativos —si un modelo sigue siendo válido, si sus parámetros siguen siendo razonables— que corresponde a un Comité de Model Risk y opera sobre una base completamente distinta: la integridad de la metodología, no el patrimonio de un cliente específico. El framework separa explícitamente estas dos gobernanzas para no confundirlas (Parte 3).

El número de alternativas que el sistema genera para una decisión no es fijo — depende de qué es efectivamente evaluable con la información disponible, y puede ser cero. Cuando dos o más motores producen señales que compiten entre sí — más liquidez a costa de más concentración, por ejemplo — el sistema no pondera automáticamente cuál dimensión importa más: identifica el trade-off, lo cuantifica en ambas direcciones, y lo entrega al WM para que decida según el cliente y sus objetivos específicos.

Este documento consolida en un único framework coherente el Decision Framework original y las cuatro correcciones metodológicas que una auditoría posterior identificó como necesarias antes de iniciar la especificación funcional del sistema (ESFS). No queda ninguna sección marcada como "parche" — donde el framework original decía algo que la auditoría corrigió, este documento dice directamente la versión corregida, con la evidencia de qué cambió y por qué reservada al aparato de validación al final del documento (Parte 8), no intercalada en el cuerpo.

**Clasificación de cierre:** READY WITH OPEN QUESTIONS. El framework está completo para iniciar la especificación funcional de sus componentes centrales — los diez motores, el Orchestrator, la Recommendation Layer, los flujos de decisión. Un componente específico, las reglas concretas de escalamiento institucional, queda deliberadamente sin diseñar porque es una decisión que corresponde a AFI, no a la metodología. Ver Parte 8.3 para el detalle completo.

---

## 1. Principio Central

> El sistema no reemplaza el juicio del Wealth Manager.

El sistema:

- calcula;
- diagnostica;
- detecta problemas;
- contextualiza cuantitativamente;
- compara;
- genera escenarios;
- identifica trade-offs;
- genera alternativas cuando es posible;
- produce recomendaciones analíticas cuando existe evidencia suficiente.

El Wealth Manager:

- incorpora contexto cualitativo;
- jerarquiza problemas;
- evalúa la situación particular del cliente;
- decide.

**La decisión final nunca es automática.** Este principio no es nuevo — es el mismo que ya gobernaba AFI Quantitative Methodology v1.0 (separación cálculo/decisión) y el Decision Framework original (techo de autonomía de Nivel 3). Lo que este documento agrega es precisión sobre *dónde exactamente* termina cada responsabilidad dentro del propio sistema, para que la frontera entre "el sistema analiza" y "un humano decide" no dependa de una convención implícita sino de una arquitectura declarada — la separación entre Engines, Orchestrator y Recommendation Layer que ocupa la Parte 2.

---

## 2. Arquitectura de Tres Capas

El sistema tiene tres capas computacionales, cada una con una responsabilidad exclusiva que no se superpone con las otras dos, y una cuarta capa humana que cierra el ciclo.

```
QUANTITATIVE ENGINES  →  calculan, diagnostican, generan warnings — nunca deciden
        ↓
DECISION ORCHESTRATOR  →  coordina qué motores activar y cómo combinar sus outputs — nunca calcula ni recomienda
        ↓
RECOMMENDATION LAYER  →  evalúa si hay evidencia para Nivel 3 — nunca ejecuta cálculos ni determina gobernanza
        ↓
WEALTH MANAGER  →  contextualiza, jerarquiza, decide
```

### 2.1 — Quantitative Engines

Los diez motores especificados en AFI Quantitative Methodology v1.0 (`AFI.Performance.Engine`, `AFI.Risk.Engine`, `AFI.Diversification.Engine`, `AFI.Construction.Engine`, `AFI.Liquidity.Engine`, `AFI.Alternatives.Engine`, `AFI.Scenario.Engine`, `AFI.Monitoring.Engine`, `AFI.Benchmark.Engine`, `AFI.ClientGoal.Engine`) comparten una frontera común, sin excepción:

```
INPUTS → CALCULATIONS → METRICS → DIAGNOSTICS → WARNINGS
```

Ningún motor produce, como parte de su propio output, una instrucción de acción. El Risk Engine puede decir *"el drawdown esperado bajo escenario adverso aumenta 4 puntos porcentuales"*; no puede decir *"debe venderse el fondo"*. El Liquidity Engine puede decir *"la cobertura proyectada cae a 81% bajo escenario de estrés"*; no puede decir *"vender este fondo"*. El Performance Engine puede decir *"el alpha rolling es negativo por tres trimestres consecutivos"*; no puede decir *"cambiar de fondo"*. Esas tres instrucciones de acción son, respectivamente, resultado de la Decision Library del sistema (decisiones D1, D6, D3/D4/D5 — Parte 5), nunca una salida directa de un motor.

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
| `AFI.Monitoring.Engine` | Sí (agregación) | Sí | No | No — prioriza entre cuentas, nunca colapsa las seis dimensiones de un mismo cliente en un score |

### 2.2 — Decision Orchestrator

El Orchestrator es la capa que coordina el análisis. No calcula ninguna métrica propia, independiente de los diez motores — si en algún momento necesitara un cálculo nuevo, eso sería, por definición, un motor nuevo, y ninguno se introduce aquí. Su función es responder once preguntas para cada pregunta que llega del cliente o del WM:

| # | Pregunta que responde el Orchestrator |
|---|---|
| 1 | ¿Cuál es la pregunta? |
| 2 | ¿Cuál es la unidad de análisis? |
| 3 | ¿Cuál es el objetivo? |
| 4 | ¿Qué información existe? |
| 5 | ¿Qué información falta? |
| 6 | ¿Qué motores son relevantes? |
| 7 | ¿Qué motores están bloqueados? |
| 8 | ¿Qué outputs deben integrarse? |
| 9 | ¿Existen trade-offs? |
| 10 | ¿Qué alternativas son cuantificables? |
| 11 | ¿Qué limitaciones deben mostrarse? |

**Nota de consolidación:** una versión anterior de este framework incluía una duodécima pregunta dentro de las responsabilidades del Orchestrator — *"¿puede alcanzarse Nivel 3?"*. Esa pregunta se reasigna aquí a la Recommendation Layer (2.3), porque evaluar si la evidencia sostiene una recomendación analítica es un juicio distinto de coordinar qué motores activar, y mantenerla en el Orchestrator difuminaba exactamente la frontera que esta arquitectura de tres capas existe para declarar con precisión.

### 2.3 — Recommendation Layer

La Recommendation Layer resuelve la ambigüedad que podría existir entre "coordinar el análisis" (Orchestrator) y "producir una recomendación" (esta capa). Su función:

> Integrar los resultados ya disponibles de los motores activados y determinar si existe suficiente evidencia para producir una recomendación analítica de Nivel 3.

Tres límites estrictos, sin excepción:

- **No ejecuta nuevas métricas cuantitativas** — trabaja únicamente sobre outputs que los motores ya calcularon.
- **No reemplaza a los motores** — si la evidencia es insuficiente, lo dice; no completa el vacío con un cálculo propio.
- **No determina gobernanza** — puede concluir que existe evidencia suficiente para una recomendación de Nivel 3, pero no decide si esa recomendación debe ir al WM, a un Senior, o al Investment Committee (esa distinción se desarrolla en la Parte 3).

Cuando concluye que sí existe evidencia suficiente, la recomendación de Nivel 3 debe mostrar, sin excepción, los ocho elementos: criterios, inputs, resultados, supuestos, restricciones, escenarios, sensibilidad, datos faltantes y limitaciones. (Ver Parte 4.4 para el desarrollo completo de los niveles de autonomía.)

### 2.4 — Por qué tres capas y no dos

Podría parecer suficiente separar "motores" de "todo lo demás". La razón para mantener el Orchestrator y la Recommendation Layer como capas distintas, y no fundirlas en una sola capa de "coordinación", es que resuelven preguntas de naturaleza diferente: el Orchestrator resuelve **qué información activar y cómo combinarla** — es un problema de cobertura y selección. La Recommendation Layer resuelve **si lo ya combinado alcanza el umbral de evidencia para opinar** — es un problema de suficiencia. Un sistema podría, en principio, activar todos los motores correctos, combinar sus outputs sin errores (Orchestrator funcionando perfectamente), y aun así no tener evidencia suficiente para una recomendación de Nivel 3 (por ejemplo, si el IPS del cliente está incompleto). Fundir ambas capas escondería esa distinción exactamente donde más importa hacerla visible.

---

## 3. Governance

El sistema nunca determina automáticamente qué instancia humana debe resolver un problema. Esto aplica de forma distinta según qué tipo de gobernanza está en juego — y confundir los dos tipos fue, en revisiones anteriores de este framework, una fuente real de ambigüedad que esta versión resuelve separándolos explícitamente.

### 3.1 — Client Decision Governance

Cubre las quince decisiones institucionales recurrentes sobre el patrimonio, portafolio o inversiones de un cliente específico (D1 a D14 de la Decision Library, Parte 5 — rebalanceo, cambio de fondo, aumento de liquidez, concentración excesiva, compatibilidad de riesgo con el IPS, elegibilidad de benchmark, deterioro de gestor, oportunidad, rebalanceo extraordinario, aprobación de nuevos gestores). Para cada una de estas decisiones, el sistema:

```
SYSTEM
    ↓
ANALYTICAL OUTPUT      (evidencia, magnitud, impacto, alternativas, recomendación si corresponde)
    ↓
WEALTH MANAGER
    ↓
INTERNAL AFI GOVERNANCE   (capa externa al sistema)
    ↓
FINAL DECISION
```

El sistema se detiene en el Analytical Output. No asigna la instancia de gobernanza — no dice "esto es Comité", no dice "esto es CEO", no dice "esto requiere Senior", y con la misma disciplina tampoco asume por defecto que "esto puede decidirlo el WM solo". La determinación de qué nivel de autoridad corresponde a cada tipo de decisión de cliente es, explícitamente, una capa externa al núcleo del sistema — una decisión institucional de AFI que puede, en el futuro, formalizarse como un componente `GOVERNANCE & ESCALATION RULES` (ver Parte 8.3, Open Question 1), pero que no es parte obligatoria de este framework.

### 3.2 — Methodology Governance

Cubre una pregunta categóricamente distinta: no "¿qué hacemos con el patrimonio de este cliente?", sino "¿siguen siendo válidos los modelos cuantitativos que todo el sistema usa?". Corresponde a la decisión D15 de la Decision Library (Gobernanza de modelos) y al framework de Model Governance ya especificado en AFI Quantitative Methodology v1.0 (backtesting, sensitivity analysis, parameter stability, out-of-sample testing, criterio de degradación de un modelo de CORE a RESEARCH).

Esta gobernanza **no opera sobre clientes** — opera sobre la integridad de la metodología misma, y su responsable institucional es un **Comité de Model Risk**, distinto en composición y función del Investment Committee que participa en decisiones de cliente. Que ambos puedan, en la práctica, incluir personas superpuestas no cambia que son dos autoridades con objetos de decisión distintos: una decide si vender un fondo a un cliente concreto; la otra decide si el modelo de VaR que todo el libro de clientes usa sigue siendo confiable.

### 3.3 — Por qué esta distinción importa para la consolidación

Una revisión anterior de este framework corrigió, de forma correcta pero uniforme, cada mención de "Comité decide automáticamente" a lo largo de las quince decisiones de la Decision Library — incluida la D15. Tratar D15 igual que D1-D14 fue, mirado con más cuidado, impreciso: la ambigüedad real en D1-D14 es *a qué nivel de autoridad escalar dentro de AFI* (Client Decision Governance, sin resolver — Parte 8.3, Open Question 1). La D15 no tiene esa misma ambigüedad de *nivel*: ya tenía, desde AFI Quantitative Methodology v1.0, un responsable institucional claro (Comité de Model Risk) para una pregunta de naturaleza distinta (validez del modelo, no destino del patrimonio). Este documento mantiene la corrección de D1-D14 (el sistema no asigna automáticamente la instancia) y, por separado, preserva sin modificación la asignación de D15 a Model Risk, porque esa asignación nunca fue el tipo de determinación automática de escalamiento que la corrección buscaba eliminar — es, sencillamente, gobernanza de otra naturaleza.

---

## 4. Decision Flow Consolidado

### 4.1 — Arquitectura general

```
CLIENT / EXECUTIVE QUESTION
        ↓
DECISION ORCHESTRATOR              (Parte 2.2 — once preguntas)
        ↓
DATA REQUIREMENTS
        ↓
DATA COMPLETENESS                  (Parte 6.1 — Block / Warning / Continue)
        ↓
RELEVANT QUANTITATIVE ENGINES      (subconjunto de los 10 — nunca todos por default)
        ↓
ENGINE OUTPUTS
        ↓
DIAGNOSTIC SYNTHESIS
        ↓
TRADE-OFF DETECTION                (Parte 4.3)
        ↓
ALTERNATIVE GENERATION             (Parte 4.2 — número variable)
        ↓
RECOMMENDATION LAYER               (Parte 2.3)
        ↓
LEVEL 0 / 1 / 2 / 3                (Parte 4.4)
        ↓
WEALTH MANAGER
        ↓
FINAL DECISION
        ↓
DECISION HISTORY                   (Parte 6.4)
        ↓
LEARNING LOOP                      (Parte 6.5)
```

Esta es la arquitectura de referencia para cualquier pregunta que el sistema procese, desde la más simple (una consulta de Nivel 0 sobre performance) hasta la más compleja (una revisión patrimonial completa que activa los diez motores). No todas las preguntas recorren la cadena completa con la misma intensidad — una pregunta de Nivel 0 puede no generar Trade-off Detection ni Alternative Generation porque no hay una decisión de por medio, solo información. La cadena es el mapa completo; cada pregunta específica recorre el subconjunto que le corresponde.

### 4.2 — Alternative Generation

**Regla central:** el sistema genera las alternativas cuantitativamente evaluables y relevantes para la pregunta planteada. El número no es fijo — puede ser ninguna, una, dos, tres, o más de tres, dependiendo de la naturaleza del problema y de la información disponible.

**Caso especial, no regla general — rebalanceo:** cuando la decisión es de rebalanceo, la estructura de tres alternativas (A. Mantener / B. Rebalancear parcialmente / C. Rebalancear completamente) sigue siendo válida y es, en la práctica, el patrón más frecuente. Pero esta estructura no es universal ni se extiende por default a otros tipos de decisión — un problema de liquidez, por ejemplo, puede requerir cuatro alternativas de contenido distinto (mantener estructura / aumentar liquidez con activos líquidos / modificar compromisos futuros / reestructurar exposición ilíquida), y un caso de deterioro de fondo, otras cuatro (mantener / mantener bajo monitoreo / reducir exposición / evaluar sustitución).

**Regla de honestidad epistémica:** si el sistema no puede generar alternativas razonablemente sustentadas con la información y los modelos disponibles, no las inventa para llenar un formato. Muestra:

> *"No existen alternativas cuantitativamente evaluables con la información disponible."*

### 4.3 — Trade-Off Framework

**El problema que resuelve:** los distintos motores pueden generar señales simultáneas que compiten entre sí — el Risk Engine detecta aumento de riesgo, el Liquidity Engine detecta necesidad de mantener activos líquidos, el Diversification Engine detecta concentración, y una alternativa que mejora una dimensión empeora otra. No existe, ni debe existir, una regla de ponderación automática entre motores.

**Lo que el sistema explícitamente no hace:**

- No crea una función de ponderación universal del tipo *Risk = 30%, Liquidity = 30%, Diversification = 20%, Scenario = 20%*.
- No permite que un motor "gane" automáticamente sobre otro.
- Los motores no compiten entre sí — no están diseñados para hacerlo, y el sistema no los pone a competir por él.

**Arquitectura de presentación, con nueve pasos obligatorios:**

```
ENGINE A → resultado
ENGINE B → resultado
ENGINE C → resultado
        ↓
TRADE-OFF IDENTIFIED
        ↓
1. identificar el conflicto
2. identificar las dimensiones involucradas
3. cuantificar cada efecto
4. mostrar qué mejora
5. mostrar qué empeora
6. mostrar magnitud
7. mostrar escenarios
8. mostrar sensibilidad
9. presentar las alternativas disponibles
        ↓
WEALTH MANAGER
```

**Ejemplo:** *"Existe un trade-off entre liquidez y riesgo. Aumentar liquidez mediante la reducción de la posición X mejora la cobertura de liquidez de 98% a 113%, pero incrementa la concentración restante en Y de HHI 0.14 a HHI 0.19 — dentro de banda institucional, pero acercándose al límite superior."* El sistema muestra el conflicto. No lo resuelve. La jerarquización de qué dimensión importa más para ese cliente específico corresponde al Wealth Manager.

**Extensión futura, explícitamente fuera del núcleo:** un `AFI Priority / Trade-off Framework` que ayude a ponderar trade-offs de forma más estructurada queda abierto como posibilidad de investigación (Parte 8.3, Open Question 2-3), pero no forma parte de este documento.

### 4.4 — Niveles de Autonomía

| Nivel | Pregunta que responde | ¿Existe en AFI? |
|---|---|---|
| **Nivel 0 — Information** | ¿Qué está ocurriendo? | Sí |
| **Nivel 1 — Diagnosis** | ¿Por qué está ocurriendo? | Sí |
| **Nivel 2 — Alternatives** | ¿Qué opciones existen? | Sí |
| **Nivel 3 — Analytical Recommendation** | Según los criterios definidos y la evidencia disponible, ¿qué alternativa parece superior? | Sí — techo máximo |
| **Nivel 4 — Execution** | — | **No existe. No forma parte de ninguna versión de este sistema.** |

Toda recomendación de Nivel 3 muestra, sin excepción, ocho elementos: criterios, inputs, resultados, supuestos, restricciones, escenarios, sensibilidad, datos faltantes y limitaciones. La redacción evita categóricamente *"esta es la decisión correcta"*; usa en su lugar una forma condicional: *"bajo los criterios y supuestos definidos, la alternativa X presenta el resultado más consistente con los objetivos analizados."*

---

## 5. Decision Library

Las quince decisiones institucionales recurrentes de AFI, cada una con sus inputs, modelos y regla de negocio ya definidos en AFI Quantitative Methodology v1.0. Aquí se resume el punto de gobernanza de cada una, aplicando la distinción de la Parte 3.

| Decisión | Pregunta | Tipo de gobernanza | Instancia |
|---|---|---|---|
| D1 | ¿Rebalancear? | Client Decision Governance | Capa externa al sistema (Parte 3.1) |
| D2 | ¿Mantener estrategia? | Client Decision Governance | Capa externa al sistema |
| D3/D4/D5 | ¿Cambiar / agregar / reducir fondo? | Client Decision Governance | Capa externa al sistema |
| D6 | ¿Aumentar liquidez? | Client Decision Governance | Capa externa al sistema |
| D7 | ¿Existe concentración excesiva? | Client Decision Governance | Capa externa al sistema |
| D8 | ¿El riesgo es compatible con el IPS? | Client Decision Governance | Capa externa al sistema |
| D9 | ¿La liquidez es suficiente? | Client Decision Governance | Capa externa al sistema |
| D10 | ¿El benchmark es elegible? | Client Decision Governance (gate técnico — ver Parte 6.3) | Capa externa al sistema para la excepción; el gate mismo es automático |
| D11 | ¿Existe deterioro de gestor? | Client Decision Governance | Capa externa al sistema |
| D12 | ¿Existe una oportunidad? | Client Decision Governance | Capa externa al sistema |
| D13 | ¿Rebalanceo extraordinario? | Client Decision Governance | Capa externa al sistema |
| D14 | Aprobación de nuevos gestores | Client Decision Governance | Capa externa al sistema |
| D15 | Gobernanza de modelos | **Methodology Governance** (Parte 3.2) | **Comité de Model Risk** — asignación preservada, no es escalamiento ambiguo |

**Regla uniforme para D1-D14:** en ningún caso el sistema asigna automáticamente si la decisión corresponde al WM, a un Senior, o al Investment Committee. El sistema entrega el Analytical Output completo (evidencia, magnitud, impacto, alternativas, recomendación si corresponde) y se detiene ahí — la escalada es Client Decision Governance, capa externa (Parte 3.1).

**Excepción declarada, no una inconsistencia:** D15 tiene una instancia fija (Comité de Model Risk) porque, como se desarrolla en la Parte 3.3, no es un caso de ambigüedad de escalamiento sino una gobernanza de naturaleza distinta, ya resuelta en AFI Quantitative Methodology v1.0.

---

## 6. Componentes Operativos

Estos seis componentes no requirieron corrección metodológica — se consolidan aquí en su forma vigente, sin cambios respecto a su especificación original.

### 6.1 — Data Completeness

Ante información faltante, el sistema clasifica cada dato relevante en uno de tres comportamientos, nunca de forma silenciosa:

| Comportamiento | Cuándo se activa | Qué muestra el sistema |
|---|---|---|
| **BLOCK** | Información crítica faltante | El indicador no se muestra; se declara qué falta y por qué bloquea |
| **WARNING** | Información importante faltante | El indicador se muestra, con nota explícita de la limitación |
| **CONTINUE** | Información complementaria faltante | El indicador se muestra sin nota |

El sistema nunca imputa silenciosamente información faltante, y nunca presenta un análisis como completo si existen limitaciones materiales que no se han declarado.

### 6.2 — Client-First y Multi-Horizonte

El sistema se adapta a la pregunta del cliente y a la información disponible — no obliga al Wealth Manager a completar todos los módulos ni a ejecutar el framework completo para cada consulta. Cuando el análisis solo puede ser parcial, el sistema lo declara: qué puede analizarse, qué no puede analizarse todavía, y qué información permitiría avanzar hacia un análisis más sofisticado.

Todo análisis relevante distingue corto, mediano y largo plazo. La misma inversión puede ser adecuada para un horizonte e inadecuada para otro simultáneamente — el sistema muestra ambas conclusiones lado a lado, etiquetadas por horizonte, y no las promedia ni elige la más favorable. Resolver esa tensión es una decisión del Wealth Manager.

### 6.3 — Benchmark Eligibility

Antes de cualquier comparación relativa, el sistema verifica ocho dimensiones de comparabilidad (objetivo, asset allocation, riesgo, moneda, liquidez, horizonte, costos, restricciones). Si el benchmark no es elegible, el sistema no produce un ranking engañoso — explica por qué la comparación no es válida. Este gate opera de forma automática porque es una verificación técnica de comparabilidad, no una decisión sobre el patrimonio del cliente — no entra en conflicto con el principio de Governance de la Parte 3, que rige sobre decisiones de acción, no sobre validaciones de comparabilidad de datos.

### 6.4 — Rebalancing

```
Portfolio → Target Allocation → Drift → Materiality → Risk → Liquidity → Costs →
Taxes/Restrictions → Scenarios → Alternatives → Analytical Recommendation → Wealth Manager
```

El rebalanceo nunca se convierte en ejecución automática. El paso de "Materiality" filtra desviaciones triviales antes de correr el análisis completo de riesgo, liquidez y costos — evita ejecutar el flujo completo para un drift que no lo amerita.

### 6.5 — Decision History y Learning Loop

Todo análisis relevante se registra: situación, datos, análisis, alternativas, recomendación, decisión, resultado posterior. Esto alimenta un loop institucional — no un sistema de aprendizaje automático:

```
Recommendation → Executive Decision → Outcome → Monitoring → Post-analysis → Methodology Improvement
```

El loop permite evaluar, con el tiempo, qué recomendaciones fueron aceptadas o rechazadas, por qué, con qué resultado posterior, y si los umbrales institucionales (de materialidad de drift, de magnitud de trade-off) resultaron demasiado agresivos o demasiado laxos en la práctica — sin requerir Machine Learning como componente del propio sistema.

### 6.6 — Rebalancing History View

Una vista de consulta —no un motor, no un componente central de la lógica decisional— que consolida los registros individuales del Decision History en una línea de tiempo de rebalanceos por cliente, con el contexto de mercado (escenario Base/Adverse/Stress vigente en cada caso) de cada decisión pasada. Se clasifica como **SUPPORTING VIEW**: útil como insumo del Learning Loop para eventualmente calibrar el umbral de materialidad de drift con evidencia real, pero no se extiende automáticamente el mismo patrón de vista longitudinal a los demás módulos — hacerlo sin evidencia de que agrega valor equivalente en, por ejemplo, decisiones de liquidez o de watchlist de gestores, sería añadir funcionalidad por similitud formal, no por necesidad demostrada.

---

## 7. Decision Flows y Orquestación de Casos de Uso

### 7.1 — Los once flujos operativos

Cada flujo es una secuencia de motores activados en orden específico, no un modelo nuevo — organiza el uso de los diez motores de AFI Quantitative Methodology v1.0.

| Flujo | Secuencia | Motores núcleo |
|---|---|---|
| **Portfolio Diagnostic** | Portfolio → Performance → Risk → Diversification → Liquidity → Goals → Benchmark → Allocation → Scenarios | Subconjunto relevante, nunca todos por default |
| **Performance** | Performance → Benchmark Eligibility → Benchmark Comparison → Relative Performance → Risk-adjusted Performance → Time Horizon → Root Cause → Interpretation | `AFI.Performance.Engine`, `AFI.Benchmark.Engine`, `AFI.Risk.Engine` |
| **Risk** | Risk Measurement → Historical Context → Benchmark/Policy → Client Constraints → Horizon → Liquidity → Scenario Analysis → Interpretation | `AFI.Risk.Engine`, `AFI.Benchmark.Engine`, `AFI.Liquidity.Engine`, `AFI.Scenario.Engine` |
| **Diversification** | Holdings → Asset Class → Currency → Geography → Vintage → Correlation → Risk Contribution → Factor Exposure → Concentration → Interpretation | `AFI.Diversification.Engine`, `AFI.Risk.Engine` |
| **Liquidity** | Client Needs → Cash Flows → Liquidity Ladder → Liquid Assets → Illiquid Assets → Capital Calls → Stress Liquidity → Coverage → Interpretation → Alternatives | `AFI.Liquidity.Engine`, `AFI.ClientGoal.Engine`, `AFI.Alternatives.Engine`, `AFI.Scenario.Engine` |
| **Alternative Investment** | NAV → Cash Flows → Vintage → TVPI/DPI/RVPI/IRR → Liquidity → Risk → Benchmark/Peer (si elegible) → Portfolio Impact → Interpretation | `AFI.Alternatives.Engine`, `AFI.Liquidity.Engine`, `AFI.Risk.Engine`, `AFI.Benchmark.Engine` |
| **Portfolio Construction** | Client Objectives → Horizons → Risk → Liquidity → Constraints → Current Portfolio → Expected Returns → Risk Model → Correlations → Optimization → Scenarios → Alternative Portfolios → Wealth Manager | `AFI.ClientGoal.Engine`, `AFI.Construction.Engine`, `AFI.Risk.Engine`, `AFI.Liquidity.Engine`, `AFI.Diversification.Engine`, `AFI.Scenario.Engine` |
| **Rebalancing** | Ver Parte 6.4 | `AFI.Construction.Engine`, `AFI.Risk.Engine`, `AFI.Liquidity.Engine`, `AFI.Scenario.Engine` |
| **Fund/Manager Deterioration** | Performance → Benchmark → Risk → Factor Exposure → Qualitative Due Diligence → ¿Deterioro persistente? → Posibles causas → Portfolio Impact → Alternatives | `AFI.Performance.Engine`, `AFI.Benchmark.Engine`, `AFI.Risk.Engine`, `AFI.Monitoring.Engine` |
| **Opportunity Analysis** | Separación explícita entre Opportunity Identification e Investment Decision | `AFI.Performance.Engine`, `AFI.Risk.Engine`, `AFI.Diversification.Engine`, `AFI.Benchmark.Engine`, en modo de detección |
| **Scenario** | Base Case vs. Optimistic vs. Adverse vs. Stress → Return, Risk, Drawdown, Liquidity, Goal Probability, Currency, Concentration | `AFI.Scenario.Engine` |

### 7.2 — Regla de activación de motores

No se ejecutan todos los motores para toda pregunta. Ejemplos:

- *"¿Por qué cayó este fondo?"* → Performance, Benchmark, Risk, Factor Analysis, Due Diligence. No necesariamente Liquidity, Portfolio Construction, o Goal Analysis.
- *"¿Debemos rebalancear?"* → Portfolio Construction, Risk, Liquidity, Diversification, Costs, Scenarios, Goals, Benchmark cuando corresponda.
- *"¿Podemos incorporar este fondo?"* → Fund Due Diligence, Risk, Performance, Benchmark, Portfolio Impact, Diversification, Liquidity, Alternatives.

Esta selección es, precisamente, la responsabilidad del Decision Orchestrator (Parte 2.2, preguntas 6-7).

### 7.3 — Decision Orchestration Matrix

Dieciocho casos de uso obligatorios, con la distinción entre motores núcleo (indispensables) y opcionales (mejoran robustez, no bloquean el análisis).

| # | Caso de uso | Motores núcleo | Motores opcionales | Alternativas (típico, no fijo) |
|---|---|---|---|---|
| 1 | Nuevo cliente | Ninguno aún | — | 0 — paso de recopilación |
| 2 | Diagnóstico inicial | Subconjunto según disponibilidad | Los demás, según robustez deseada | 0-1 |
| 3 | Construcción de portafolio | `Construction`, `ClientGoal` | `Diversification` | 2-4 |
| 4 | Revisión periódica | `Performance`, `Risk` | `Diversification`, `Scenario` | 0-2 |
| 5 | Rebalanceo | `Construction`, `Risk`, `Liquidity` | `Scenario` | Variable, típicamente 3 |
| 6 | Deterioro de fondo | `Performance`, `Monitoring` | `Risk` (factor exposure) | 2-4 |
| 7 | Nueva inversión | Due diligence, `Alternatives` (si privado) | `Diversification`, `Liquidity` | 0-2 |
| 8 | Cambio de estrategia | `Construction`, `ClientGoal` | Todos, según alcance | 2-4 |
| 9 | Oportunidad | `Performance`/`Risk` (detección) | `Benchmark`, `Diversification` | 0-1 |
| 10 | Problema de liquidez | `Liquidity`, `ClientGoal` | `Alternatives`, `Scenario` | Variable |
| 11 | Cambio en objetivos | `ClientGoal` | Los que se activen tras el cambio | 0 |
| 12 | Cambio de riesgo | `Risk` | `Construction` (si implica rediseño) | 0-2 |
| 13 | Cambio de horizonte | `ClientGoal` | `Construction` (si afecta SAA) | 0-2 |
| 14 | Asset Allocation | `Construction` | `Diversification`, `Scenario` | 2-4 |
| 15 | Alternativos | `Alternatives`, `Liquidity` | `Risk` (factor aproximado) | 0-2 |
| 16 | Benchmark | `Benchmark` | — | 0 — es un gate |
| 17 | Stress Testing | `Scenario` | Todos, como inputs de qué estresar | 0-1 |
| 18 | Revisión patrimonial | Los 10, según relevancia | — | Variable, potencialmente varios trade-offs |

---

## 8. Validación y Cierre

### 8.1 — Validación contra versiones anteriores

| Elemento | Estado | Acción |
|---|---|---|
| Quantitative Methodology | Preservado | Sin modificación — los diez motores, sus fórmulas y clasificaciones CORE/ADVANCED/RESEARCH/REJECTED permanecen exactamente como están especificados |
| Decision Framework | Consolidado | Reorganizado en arquitectura de tres capas; ningún Decision Flow cambió su secuencia de pasos ni sus motores activados |
| Governance | Corregido | Sin autoridad automática para D1-D14; distinción explícita Client Decision Governance vs. Methodology Governance (nueva en esta consolidación — Parte 3) |
| Alternatives | Corregido | Número dinámico, no fijo; regla de honestidad epistémica cuando no hay alternativas evaluables |
| Engine conflicts | Corregido | Trade-Off Framework con nueve pasos obligatorios, sin ponderación automática |
| Decision Orchestrator | Formalizado | Nuevo concepto arquitectónico — once preguntas, sin cálculo propio |
| Recommendation Layer | Formalizado | Separado del Orchestrator — la pregunta "¿puede alcanzarse Nivel 3?" migró aquí desde una versión anterior donde estaba, de forma imprecisa, dentro de las responsabilidades del Orchestrator |
| Data Completeness | Preservado | Sin modificación |
| Benchmark Eligibility | Preservado | Sin modificación — gate técnico automático, distinto de Client Decision Governance (Parte 6.3) |
| Human-in-the-loop | Preservado | Sin modificación |
| Learning Loop | Preservado | Sin modificación |
| Rebalancing History View | Preservado | Sin modificación — clasificado como Supporting View, no como componente central |
| D15 (Model Governance) | Precisado | Se distingue explícitamente de D1-D14 como Methodology Governance, no como caso de escalamiento ambiguo (Parte 3.3) — esta distinción no existía como tal antes de esta consolidación |

### 8.2 — Criterio de cierre

| Pregunta | Respuesta |
|---|---|
| ¿El sistema puede analizar sin decidir? | Sí — Parte 2, arquitectura de tres capas |
| ¿Los motores están separados de la coordinación? | Sí — Parte 2.1 vs. 2.2 |
| ¿El Orchestrator está separado de la Recommendation Layer? | Sí — Parte 2.2 vs. 2.3, con la migración explícita de la pregunta de Nivel 3 documentada |
| ¿Los conflictos se presentan como trade-offs? | Sí — Parte 4.3 |
| ¿Las alternativas son dinámicas? | Sí — Parte 4.2 |
| ¿El Wealth Manager conserva la decisión? | Sí — Parte 1, Principio Central, sin excepción en ningún flujo |
| ¿La gobernanza institucional está fuera del núcleo? | Sí, para Client Decision Governance (Parte 3.1). Methodology Governance (D15) tiene instancia fija por ser de naturaleza distinta, no por excepción a esta regla (Parte 3.3) |
| ¿Los datos faltantes son explícitos? | Sí — Parte 6.1 |
| ¿Se evita cualquier ranking o score arbitrario? | Sí — ningún motor se pondera contra otro (Parte 4.3); el Monitoring Engine prioriza entre cuentas, nunca colapsa dimensiones de un mismo cliente (Parte 2.1) |
| ¿No se introdujeron modelos nuevos? | Sí — cero cálculos cuantitativos nuevos; el Rebalancing History View consolida datos ya calculados, no introduce fórmulas |

### 8.3 — Open Methodological Questions

Estas cuestiones no se resuelven en este documento — resolverlas sin evidencia operativa real sería inventar precisión donde no existe.

1. **Governance & Escalation Rules** — qué umbral de monto, riesgo o tipo de cliente determina si una decisión de Client Decision Governance corresponde al WM, a un Senior, o al Investment Committee. *(Institucional — Investment Committee y Senior Management de AFI)*
2. **Formal Priority Framework** — si en el futuro tiene sentido un mecanismo más estructurado que "mostrar los nueve componentes del trade-off y dejarlo al WM". *(Metodológica / Governance — clasificado RESEARCH, no CORE)*
3. **Formal Trade-Off Resolution Framework** — extensión de la anterior; requiere evidencia del Rebalancing History View y de casos reales documentados antes de tener sentido. *(Metodológica / Governance)*
4. **Dynamic Threshold Governance** — el umbral de materialidad del drift (Parte 6.4) y el umbral de qué constituye un conflicto activable por el Trade-Off Framework (Parte 4.3) no están fijados numéricamente — ninguno de los documentos base lo hace sin evidencia operativa de AFI. *(Datos / Institucional)*
5. **Alternative Generation Rules más avanzadas** — reglas más granulares sobre cuándo el número correcto de alternativas es 2 vs. 3 vs. 4 para un mismo tipo de decisión, más allá del patrón observado. *(Metodológica)*
6. **Parameter Governance** — quién dentro de AFI puede modificar cada parámetro institucional (niveles de confianza de VaR, τ y δ de Black-Litterman, bandas de rebalanceo) ya tiene categorías definidas en AFI Quantitative Methodology v1.0, pero los valores numéricos específicos siguen pendientes de calibración institucional. *(Institucional)*
7. **Extensión futura de Historical Views** — si el patrón del Rebalancing History View (Parte 6.6) debería extenderse a otros tipos de decisión recurrente; explícitamente no evaluado todavía por falta de evidencia de necesidad. *(Tecnológica / Producto)*

Ninguna de estas siete cuestiones se resuelve artificialmente en esta versión. Donde un valor numérico o una regla institucional específica no tiene base en los documentos fuente, este framework declara **OPEN QUESTION / TBD** en vez de rellenar el vacío con una práctica genérica.

---

# READINESS FOR ESFS

## READY WITH OPEN QUESTIONS

El framework está completo para iniciar la especificación funcional de sus componentes centrales: los diez motores cuantitativos, la arquitectura de tres capas (Engines / Orchestrator / Recommendation Layer), los once Decision Flows, el Trade-Off Framework, la Decision Library con su distinción de gobernanza, y los seis componentes operativos preservados (Data Completeness, Client-First, Multi-Horizonte, Benchmark Eligibility, Decision History, Learning Loop).

Quedan explícitamente abiertos, y no bloquean el inicio de la ESFS para el resto del sistema, los siete elementos de la Parte 8.3 — de forma más concreta, dos merecen mención directa: el componente `GOVERNANCE & ESCALATION RULES` puede especificarse como una interfaz con un contrato definido (qué inputs recibe, qué necesita devolver) pero sin las reglas internas de asignación, que son una decisión institucional de AFI y no una decisión metodológica que este documento pueda anticipar; y los umbrales dinámicos de materialidad (drift, trade-off) deben especificarse en la ESFS como parámetros configurables desde el inicio, no como constantes, precisamente porque su calibración depende de evidencia operativa que todavía no existe.
