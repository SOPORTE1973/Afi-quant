# AFI DECISION FRAMEWORK v1.0

**Puente operativo entre AFI Quantitative Methodology v1.0 y la futura AFI Expert System Functional Specification (ESFS)**
**Herramienta de síntesis:** Claude · **Tipo de trabajo:** diseño metodológico y funcional (no código, no arquitectura tecnológica definitiva, no LLM dentro del sistema, no algoritmo autónomo de inversión)

---

## Cómo leer este documento

Este documento no recalcula ni redefine ningún modelo cuantitativo. Toda métrica, fórmula, motor o clasificación CORE/ADVANCED/RESEARCH/REJECTED ya está fijada en **AFI Quantitative Methodology v1.0** (en adelante, "el documento de metodología" o "v1.0") y se cita desde ahí, no se reescribe. Lo que este documento agrega es la capa que faltaba: **cómo el sistema recorre la información disponible** — con qué orden, con qué reglas de bloqueo/advertencia ante datos faltantes, y con qué alcance de autonomía — **para llegar a una recomendación analítica que el Wealth Manager (WM) pueda decidir usar.**

Tres reglas de tratamiento heredadas del mandato de v1.0 se mantienen aquí sin cambios:

1. **Las fuentes no se modifican silenciosamente.** Ninguna decisión ya tomada en v1.0 (los 10 motores de la Parte II, las clasificaciones de la Parte III, las 15 decisiones de la Decision Library en la Parte XVIII, la prohibición de LLM/SHAP/LIME de la Parte XIX) se altera aquí. Este documento las **usa**, no las **redecide**.
2. **Las contradicciones se resuelven, no se ocultan.** Donde el Volumen IV (el prompt que originó este documento) roza un límite ya fijado en v1.0, se declara explícitamente. Se identificó **un caso** — ver Parte 2.4.
3. **La incertidumbre se declara.** Donde ningún documento base ofrece base suficiente, la Parte 21 lo registra en vez de inventarlo.

---

## 1. Executive Summary

AFI Quantitative Methodology v1.0 respondió *qué calcular*. Este documento responde una pregunta distinta: **dado que ya existen diez motores capaces de calcular casi cualquier cosa sobre un cliente, un portafolio o un fondo, ¿en qué orden debe el sistema activarlos, qué debe hacer cuando falta información, y dónde termina exactamente su autonomía antes de que la decisión pase al Wealth Manager?**

El **AFI Decision Framework v1.0** es la capa de orquestación entre los datos y el juicio humano. No introduce ningún modelo matemático nuevo — organiza el uso de los que v1.0 ya definió. Su arquitectura central:

```
DATOS → MÉTRICAS → DIAGNÓSTICO → CONTEXTO → ESCENARIOS → ALTERNATIVAS → EVIDENCIA → WEALTH MANAGER → DECISIÓN
```

Esta secuencia es una elaboración de la cadena de v1.0 (Resumen Ejecutivo: *Datos → Cálculos → Métricas → Diagnóstico → Escenarios → Alternativas → Evidencia → Decisión del Ejecutivo*) — añade explícitamente el paso de **Contexto** entre Diagnóstico y Escenarios, porque el Volumen IV identifica un elemento que v1.0 no separaba con nombre propio: ningún número tiene significado sin el contexto del cliente (su IPS, su horizonte, sus restricciones) antes de decidir qué escenarios correr. No es una contradicción — es una capa que v1.0 daba por hecha (Principio 1: centralidad de los objetivos del cliente) y que aquí se hace explícita como paso operativo.

**Qué contiene este documento:**

- Un **Data Completeness Engine** conceptual, con tres comportamientos posibles ante información faltante (Bloqueo / Advertencia / Sin Impacto Material), aplicado de forma sistemática, no ad-hoc.
- Un **principio explícito contra el "Portfolio Health Score"**: el sistema nunca colapsa un portafolio a un semáforo único.
- Un **framework Client-First multi-horizonte**: el mismo activo puede ser adecuado a largo plazo y problemático para una necesidad de liquidez inmediata, y el sistema debe poder representar esa tensión sin resolverla por el WM.
- **Once decision flows operativos** (Parte 7), cada uno una secuencia concreta de motores de v1.0 activados en orden, con sus reglas de bloqueo específicas.
- Un **caso de uso completo narrado** end-to-end (Parte 8), mostrando el framework en funcionamiento sobre un cliente ficticio.
- Cuatro matrices (maestra de casos de uso, de datos, de reglas, de outputs) que consolidan el framework en formato consultable.
- Un **Recommendation Engine** que define con precisión el techo de autonomía del sistema — Nivel 3, nunca Nivel 4 — y qué debe acompañar siempre a una recomendación analítica para que no se lea como una instrucción.

**El límite más importante que fija este documento:** el sistema tiene, como máximo, autonomía de **Nivel 3 — Recomendación Analítica**. Puede decir *"según los criterios definidos y la evidencia disponible, la Alternativa B parece superior"*. No puede decir *"esta es la decisión correcta"*, y no existe — ni existirá en ninguna versión futura contemplada aquí — un Nivel 4 de ejecución. Esto no es una limitación técnica temporal: es, igual que en v1.0, una posición institucional permanente.

---

## 2. Principios

### 2.1 — Decision Support System, no asesor autónomo

**Qué significa.** El sistema organiza evidencia para que el WM decida mejor y más rápido. No es un robo-advisor, no hace stock picking, no ejecuta, y no genera recomendaciones automáticas sin contexto.

**Por qué existe.** Es el principio central explícito del mandato (Volumen IV, Sección 2) y una extensión directa del Principio 2 de v1.0 (separación cálculo/decisión). El Volumen IV lo hace más específico: no solo separa cálculo de decisión, sino que fija un techo de autonomía nombrado y numerado (Nivel 3 — ver Parte 6).

**Qué implica para el framework.** Todo flujo de decisión de este documento termina en "Wealth Manager decide", nunca en una acción ejecutada por el sistema.

**Qué implica para el software.** Ningún flujo puede tener un paso de "ejecución" en su especificación (Parte 19) — el último paso siempre es `Human_Decision`, seguido de `History`.

### 2.2 — Client-First: la unidad de análisis la define la pregunta, no el sistema

**Qué significa.** El sistema no impone un único punto de entrada (siempre "cliente completo" o siempre "portafolio"). La unidad de análisis —cliente, patrimonio, portafolio, cuenta, sociedad, fondo individual, asset class, estrategia, objetivo específico— depende de lo que el WM está tratando de resolver.

**Por qué existe.** Mandato explícito del Volumen IV, Sección 4. Es coherente con v1.0 pero lo extiende: v1.0 diseñó motores que pueden operar sobre distintas unidades (un fondo, un portafolio, un cliente), pero no especificaba cuál elegir primero. Este documento resuelve esa ambigüedad.

**Qué implica para el framework.** El primer paso de todo flujo (Parte 5, Flujo General) es identificar la unidad de análisis a partir de la pregunta — no asumir una por defecto.

**Qué implica para el Wealth Manager.** Puede empezar un análisis con la información que tiene a mano, sobre la unidad que le interesa, sin tener que "completar" primero un onboarding genérico.

### 2.3 — La ausencia de información es visible, nunca silenciosa

**Qué significa.** Cuando falta un dato, el sistema no estima en silencio ni lo ignora. Lo declara, y clasifica su impacto en exactamente uno de tres niveles: Bloqueo, Advertencia, o Sin Impacto Material (desarrollado en la Parte 4).

**Por qué existe.** Es una extensión directa y más granular del Principio 8 de v1.0 ("ante evidencia insuficiente, el sistema lo declara — nunca inventa"). v1.0 definía un estado binario (`Model_Blocked: insufficient_data` vs. resultado válido); este documento agrega el estado intermedio de Advertencia que v1.0 no nombraba explícitamente como tal, aunque sus reglas de calidad de datos (v1.0, Parte XVII) ya incluían "Warning" como paso del patrón Detection→Action→Warning→Fallback. Este documento simplemente formaliza ese paso intermedio como parte del vocabulario central del framework.

**Qué implica para el framework.** Todo dato usado por cualquier flujo se clasifica antes de ejecutarse: crítico, importante o complementario (Parte 4 y Parte 15, Matriz de Datos).

### 2.4 — Ninguna dimensión se colapsa en un score único — y por qué esto no contradice a v1.0

**Qué significa.** El sistema nunca presenta "Portfolio sano / Portfolio rojo" ni un score global. Cada dimensión (Performance, Risk, Liquidity, Diversification, Goals, Benchmark) se muestra por separado, con su resultado, contexto y riesgos propios. El WM es quien jerarquiza.

**Por qué existe — y la tensión con v1.0 que vale la pena hacer explícita.** El mandato del Volumen IV (Sección 6) es categórico: "NO crear un Portfolio Health Score". v1.0 no propone un score global explícito, pero sí incluye, en su Motor de Monitoreo (v1.0, Parte II.8), un "heatmap de desviaciones" y una "lista priorizada de cuentas" — una forma de priorización visual entre clientes. Esto **no es una contradicción real**, pero merece la distinción explícita que el mandato exige señalar: el heatmap del Motor de Monitoreo prioriza **entre cuentas distintas** ("¿en qué cliente debo mirar primero hoy?"), nunca **dentro de un mismo portafolio** colapsando Performance+Risk+Liquidity+Diversification+Goals+Benchmark en un solo número o color. La distinción que fija este documento: **priorización entre unidades de análisis es aceptable; agregación de dimensiones dentro de una misma unidad en un score único no lo es, en ningún nivel.** El Motor de Monitoreo de v1.0 se mantiene exactamente como fue diseñado — este documento solo aclara el límite que ya tenía implícito, sin modificarlo.

**Qué implica para el framework.** El `AFI.Monitoring.Engine` (v1.0) puede seguir mostrando qué cliente requiere atención primero. Ningún flujo de este documento puede mostrar "este cliente está en rojo" como conclusión de un solo número compuesto — debe mostrar seis resultados separados con sus contextos.

### 2.5 — Jerarquización humana, no algorítmica

**Qué significa.** El sistema puede mostrar severidad cuantitativa (p. ej. "esta desviación de VaR es 3x el umbral, esta otra es 1.1x"), pero no decide automáticamente cuál es "el problema más importante del cliente" cuando hay varios hallazgos simultáneos de naturaleza distinta.

**Por qué existe.** Mandato explícito del Volumen IV, Sección 7. Complementa el Principio 2.1 — no es solo que el sistema no ejecuta, es que tampoco prioriza problemas de distinta naturaleza entre sí (un problema de liquidez vs. uno de concentración vs. uno de underperformance) sin que el WM aplique juicio profesional y contexto relacional.

**Qué implica para el framework.** El Executive Workspace (Parte 9) presenta todos los hallazgos activados con su severidad individual visible, pero el orden final de atención lo decide el WM, no un ranking automático entre dimensiones distintas.

### 2.6 — Techo de autonomía: Nivel 3, nunca Nivel 4

**Qué significa.** El sistema puede llegar hasta la Recomendación Analítica (Nivel 3): "según los criterios definidos, esta alternativa parece superior". Nunca ejecuta. No existe Nivel 4 en ninguna versión contemplada por este documento.

**Por qué existe.** Mandato explícito del Volumen IV, Sección 8-9, y consistente con la separación cálculo/decisión de v1.0 (Principio 2). Ver desarrollo completo en la Parte 6.

**Qué implica para el framework.** Toda especificación de flujo (Parte 19) declara explícitamente su nivel máximo alcanzado — nunca asume Nivel 3 por default; muchos flujos (p. ej. escalamiento, Parte 32 del mandato) se detienen deliberadamente en Nivel 1 o 2.

### 2.7 — Multi-horizonte: un mismo activo puede ser correcto y problemático a la vez

**Qué significa.** El sistema separa explícitamente corto, mediano y largo plazo, porque un activo (p. ej. una posición en Private Equity) puede ser completamente adecuado para el objetivo patrimonial de largo plazo del cliente y, al mismo tiempo, un problema si el cliente necesita liquidez inmediata.

**Por qué existe.** Mandato explícito del Volumen IV, Sección 11. Es una extensión operativa de varios motores de v1.0 que ya trabajaban con horizontes distintos (Motor de Liquidez con buckets de corto plazo, Motor de Construcción con horizonte de largo plazo) pero sin una capa que los hiciera hablar entre sí sobre el mismo activo. Ver desarrollo en la Parte 5.2.

**Qué implica para el framework.** Ningún flujo evalúa "¿es esto bueno?" sin especificar "¿bueno para qué horizonte?" — la misma pregunta puede tener respuestas distintas y legítimamente contradictorias entre horizontes, y el sistema debe mostrar ambas, no promediarlas.

---

## 3. Arquitectura de Decisión

### 3.1 — La cadena central, expandida desde v1.0

```
CLIENT / QUESTION
        ↓
UNIT OF ANALYSIS           (Principio 2.2 — la pregunta define la unidad, no un default)
        ↓
OBJECTIVE                  (conecta con el IPS — v1.0 Principio 1)
        ↓
AVAILABLE DATA
        ↓
DATA COMPLETENESS          (Parte 4 de este documento)
        ↓
RELEVANT ENGINES           (subconjunto de los 10 motores de v1.0 Parte II — nunca todos por default)
        ↓
ANALYSIS                   (cálculos ejecutados por los motores activados)
        ↓
DIAGNOSTICS
        ↓
RISKS / LIMITATIONS
        ↓
SCENARIOS                  (AFI.Scenario.Engine, v1.0 Parte XI)
        ↓
ALTERNATIVES                (Parte 10 de este documento)
        ↓
ANALYTICAL RECOMMENDATION  (Nivel 3 máximo — Parte 6)
        ↓
WEALTH MANAGER
        ↓
DECISION
        ↓
TRACKING                   (Parte 14 — Decision History)
        ↓
LEARNING LOOP              (Parte 13)
```

Esta es la arquitectura final que pide el mandato (Volumen IV, Sección 41), presentada aquí en la Parte 3 en vez de al final, porque en este documento cumple una función distinta a la de v1.0: no es una conclusión de cierre sino el mapa de referencia que el resto del documento desarrolla paso a paso.

### 3.2 — Por qué "no todos los análisis ejecutan todos los motores"

v1.0 diseñó diez motores independientes con dependencias documentadas entre ellos (v1.0, Parte II, diagrama de arquitectura). Este documento fija la regla operativa que v1.0 no necesitaba fijar porque no se ocupaba de orquestación: **el sistema activa solo los motores relevantes a la pregunta específica, no el conjunto completo por default.**

Ejemplo: una pregunta sobre "¿puedo comprarme una propiedad en 8 meses?" activa `AFI.Liquidity.Engine` y `AFI.ClientGoal.Engine` como núcleo, con `AFI.Scenario.Engine` para el estrés de liquidez — pero no tiene por qué ejecutar `AFI.Alternatives.Engine` si el cliente no tiene posiciones en vehículos privados relevantes para esa pregunta específica. Ver el caso de uso completo en la Parte 8 para una ilustración extensa de esta selección de motores en acción.

---

## 4. Data Completeness Engine

### 4.1 — Los tres comportamientos ante información faltante

Para cada análisis, el sistema clasifica cada dato relevante en cinco estados de disponibilidad (disponible / faltante / crítico / relevante / complementario) y traduce esa clasificación en exactamente uno de tres comportamientos:

| Comportamiento | Cuándo se activa | Qué muestra el sistema |
|---|---|---|
| **A. BLOQUEO** | El dato es indispensable para calcular el indicador con robustez mínima | *"Este análisis no puede realizarse con suficiente robustez porque falta X."* — el indicador no se muestra en absoluto |
| **B. ADVERTENCIA** | El indicador puede calcularse, pero la ausencia reduce su robustez | El indicador se muestra, acompañado de: *"Interpretar con precaución: falta X."* |
| **C. SIN IMPACTO MATERIAL** | La ausencia no afecta significativamente este análisis específico | El indicador continúa normalmente, sin nota |

**Regla de diseño explícita:** estos tres comportamientos son mutuamente excluyentes para un mismo dato en un mismo cálculo — nunca un indicador se muestra parcialmente "un poco bloqueado". O se bloquea completo, o se muestra con advertencia, o se muestra sin nota. Esta es la extensión operativa del principio de v1.0 (Principio 8): v1.0 ya distinguía "resultado válido" de `insufficient_data`; este documento agrega el estado intermedio B como parte formal del vocabulario, consistente con el paso "Warning" que las reglas de calidad de datos de v1.0 (Parte XVII) ya usaban internamente para cada tipo de problema de datos.

### 4.2 — Relación con las Reglas de Calidad de Datos de v1.0

La Parte XVII de v1.0 ya definía, para cada problema de datos (Missing Data, Outliers, Stale Prices, etc.), el patrón `Detection → Action → Warning → Fallback o Model Block`. Este documento no crea una segunda taxonomía en paralelo — **mapea directamente ese patrón a los tres comportamientos**:

| Patrón v1.0 (Parte XVII) | Comportamiento de este documento |
|---|---|
| Termina en `Model Block` | A. BLOQUEO |
| Termina en `Warning` + `Fallback` (imputación prudente, uso de frecuencia nativa, etc.) | B. ADVERTENCIA |
| No genera flag porque el gap es menor y no afecta el resultado materialmente | C. SIN IMPACTO MATERIAL |

Esto asegura que ambos documentos describen el mismo comportamiento del sistema, en dos niveles de abstracción distintos: v1.0 a nivel de motor y tipo de problema de datos; este documento a nivel de framework de decisión completo, aplicable de forma uniforme sin importar qué motor esté evaluando.

### 4.3 — Ejemplos concretos de clasificación (Data Missing Logic)

| Si falta... | Comportamiento | Alcance del bloqueo |
|---|---|---|
| Horizonte del cliente | A. BLOQUEO | Bloquea todos los análisis dependientes de horizonte (Motor de Construcción, Motor de Cliente/Goal) |
| Benchmark elegible | A. BLOQUEO | Bloquea ranking relativo específicamente — no bloquea Performance ni Riesgo en términos absolutos (v1.0, Principio 7 y Parte XII) |
| Información de liquidez del cliente | B. ADVERTENCIA | Permite métricas de riesgo de mercado; advierte limitación específica en el análisis de liquidez |
| Holdings detallados (look-through) | B. ADVERTENCIA | Permite análisis a nivel de fondo agregado; advierte que el look-through completo no está disponible para factor exposure |
| NAV histórico suficiente | Depende de la cantidad — ver umbral por modelo en v1.0 Parte V/Parte XXII | Si es insuficiente para el mínimo del modelo específico (p. ej. <36 obs. mensuales para Tracking Error): A. BLOQUEO de ese indicador puntual |
| Un dato complementario (p. ej. preferencia de frecuencia de comunicación) | C. SIN IMPACTO MATERIAL | Ninguno — el análisis continúa sin nota |

**Nota de honestidad metodológica:** los umbrales numéricos exactos que determinan cuándo un gap de NAV pasa de "menor" a "significativo" no están fijados de forma genérica en ningún documento base — v1.0 ya declaró esto como Pendiente 2 (v1.0, Parte XXIII). Este documento no resuelve ese pendiente; lo hereda tal cual.

---

## 5. Client-First Framework

### 5.1 — Unidades de análisis soportadas

El sistema debe poder operar sobre cualquiera de las siguientes unidades, sin que ninguna sea la unidad por default:

| Unidad | Ejemplo de pregunta que la activa |
|---|---|
| Cliente completo | "¿Cómo está mi cliente en general este trimestre?" (poco frecuente — normalmente la pregunta real es más específica) |
| Patrimonio | "¿Cuál es la exposición total del patrimonio a renta variable, incluyendo lo que tiene fuera de AFI?" |
| Portafolio | "¿Cómo se comportó el portafolio gestionado por AFI este año?" |
| Cuenta | "¿Qué pasó específicamente en la cuenta mancomunada con su cónyuge?" |
| Sociedad | "¿Cómo impacta la sociedad de inversión familiar en la liquidez consolidada?" |
| Fondo individual | "¿Deberíamos mantener la posición en el Fondo X?" |
| Asset class | "¿Cuál es nuestra exposición a Private Equity en todos los clientes?" |
| Estrategia | "¿La estrategia de renta fija está funcionando como se diseñó?" |
| Objetivo específico | "¿Vamos a poder financiar la universidad de su hija en 2030?" |

### 5.2 — Client Onboarding / Initial Analysis — flujo opcional, no obligatorio

Cuando existe información suficiente para la pregunta específica, el sistema comienza directamente — no exige completar un onboarding genérico primero (Principio 2.2). Cuando se requiere mayor profundidad, el sistema muestra una sección claramente etiquetada como **"Información recomendada para profundizar el análisis"**, distinguiendo:

- **Información necesaria** — sin ella, el análisis específico solicitado cae en Bloqueo (A).
- **Información que aumenta la robustez** — sin ella, el análisis continúa pero con Advertencia (B), o simplemente sería más preciso con ella.

Catálogo de información que puede solicitarse (nunca todo a la vez, solo lo relevante a la pregunta): objetivo, horizonte, liquidez requerida, tolerancia al riesgo, capacidad de riesgo, patrimonio total, flujos futuros esperados, moneda, restricciones (ESG, regulatorias, familiares), inversiones existentes fuera de AFI, IPS vigente.

### 5.3 — Client Objectives como variable central

Los objetivos del cliente son un input de primera clase, no un campo opcional. El sistema permite **múltiples objetivos simultáneos** — un mismo cliente puede tener a la vez preservación patrimonial, generación de ingresos, y financiamiento de una compra futura, cada uno con su propia estructura:

| Atributo del objetivo | Ejemplo |
|---|---|
| Monto | USD 150.000 |
| Fecha | Marzo 2027 |
| Moneda | USD |
| Probabilidad deseada | 80% de confianza |
| Prioridad | Alta / Media / Baja, relativa a los otros objetivos del mismo cliente |
| Liquidez requerida | Disponible en efectivo en la fecha, sin tolerancia a iliquidez |

Esta estructura alimenta directamente a `AFI.ClientGoal.Engine` (v1.0, Parte II.10) y es la razón por la cual ese motor no puede operar sin un IPS mínimamente estructurado (v1.0 ya lo señalaba como limitación del motor).

### 5.4 — Multi-horizonte: representación explícita de la tensión, no su resolución automática

Todo análisis relevante se separa en tres horizontes, y el sistema muestra los tres cuando son relevantes a la pregunta — no los promedia ni elige uno:

| Horizonte | Dimensiones típicas | Motores de v1.0 involucrados |
|---|---|---|
| **Corto plazo** | Liquidez, cash flow, capital calls, drawdown, necesidades inmediatas | `AFI.Liquidity.Engine`, `AFI.Risk.Engine` (drawdown) |
| **Mediano plazo** | Rebalanceo, riesgo, performance, cambios de asset allocation, concentración | `AFI.Risk.Engine`, `AFI.Performance.Engine`, `AFI.Diversification.Engine` |
| **Largo plazo** | Objetivos patrimoniales, SAA, Private Equity, wealth preservation, probabilidad de alcanzar metas | `AFI.Construction.Engine`, `AFI.Alternatives.Engine`, `AFI.ClientGoal.Engine` |

**Regla de representación:** cuando un mismo activo aparece en más de un horizonte con evaluaciones distintas (p. ej. "adecuado para el objetivo de largo plazo" pero "problemático para la necesidad de liquidez en 6 meses"), el sistema muestra **ambas conclusiones lado a lado, explícitamente etiquetadas por horizonte** — nunca resuelve la tensión promediando o eligiendo la más favorable. Resolver esa tensión es, precisamente, una de las decisiones que le corresponden al WM.

---

## 6. Decision Flows

Cada flujo es una secuencia concreta de motores de v1.0 (citados por su identificador exacto, v1.0 Parte XXIV) activados en un orden específico, con sus reglas de bloqueo propias. Ningún flujo introduce un modelo nuevo — organiza el uso de los ya definidos.

### 6.1 — Portfolio Diagnostic Flow

```
PORTFOLIO → PERFORMANCE → RISK → DIVERSIFICATION → LIQUIDITY → GOALS → BENCHMARK → ALLOCATION → SCENARIOS
```

Este es el flujo "completo" de referencia, pero **el sistema activa solo las dimensiones relevantes a la pregunta específica** (Principio 3.2) — rara vez se ejecutan las ocho dimensiones para una pregunta puntual. Motores involucrados: potencialmente los diez, según cuáles dimensiones se activen.

### 6.2 — Performance Decision Flow

```
Performance → Benchmark Eligibility → Benchmark Comparison → Relative Performance → Risk-adjusted Performance → Time Horizon → Root Cause → Interpretation
```

**Motores:** `AFI.Performance.Engine` → `AFI.Benchmark.Engine` (gate, v1.0 Principio 7) → `AFI.Performance.Engine` (atribución) → `AFI.Risk.Engine` (para ajuste por riesgo).

**Regla explícita del flujo:** el sistema nunca concluye *"el fondo cayó 10%, por lo tanto es malo"*. La secuencia obliga a pasar por Root Cause antes de Interpretation, diferenciando explícitamente si la caída viene de mercado, benchmark, factores, estrategia, manager, o un evento específico — usando la atribución Brinson-Fachler o factorial de v1.0 (Parte IV) para esa distinción, no una lectura directa del número.

**Bloqueo crítico:** si `AFI.Benchmark.Engine` marca el benchmark como no-elegible (v1.0, Parte XII), el flujo **no puede avanzar a Relative Performance** — puede reportar Performance absoluta, pero el paso de comparación relativa queda en Bloqueo (A), no en Advertencia.

### 6.3 — Risk Decision Flow

```
Risk Measurement → Historical Context → Benchmark / Policy → Client Constraints → Horizon → Liquidity → Scenario Analysis → Interpretation
```

**Motores:** `AFI.Risk.Engine` → `AFI.Benchmark.Engine` → (constraints del IPS) → `AFI.Liquidity.Engine` → `AFI.Scenario.Engine`.

**Regla explícita:** cada indicador de riesgo se muestra con cuatro componentes obligatorios — Resultado, Contexto, Riesgo asociado, Limitación (heredado de v1.0, cada fila de la Parte V trae exactamente esta estructura). El flujo **nunca produce una clasificación global del portafolio** (Principio 2.4) — el resultado final es un conjunto de indicadores contextualizados, no un score.

### 6.4 — Diversification Decision Flow

```
Holdings → Asset Class → Currency → Geography → Vintage → Correlation → Risk Contribution → Factor Exposure → Concentration → Interpretation
```

**Motores:** `AFI.Diversification.Engine` (núcleo) → `AFI.Risk.Engine` (matriz de covarianzas compartida, v1.0 Parte VI).

**Objetivo del flujo, tal como lo fija v1.0 (Principio 6):** detectar diversificación nominal vs. diversificación económica. El orden Holdings→Correlation→Risk Contribution→Factor Exposure sigue exactamente la secuencia de identificación de concentraciones ocultas ya definida en v1.0 (Parte VI, "Cómo AFI identifica concentraciones ocultas") — este flujo no la redefine, la ejecuta.

### 6.5 — Liquidity Decision Flow

```
Client Needs → Cash Flows → Liquidity Ladder → Liquid Assets → Illiquid Assets → Capital Calls → Stress Liquidity → Coverage → Interpretation → Alternatives
```

**Motores:** `AFI.ClientGoal.Engine` (Client Needs, vía IPS) → `AFI.Liquidity.Engine` (núcleo) → `AFI.Alternatives.Engine` (Capital Calls) → `AFI.Scenario.Engine` (Stress Liquidity).

**Pregunta que responde** (idéntica a la que fija v1.0, Parte IX): *"¿puede el patrimonio financiar las necesidades del cliente bajo escenarios razonables y adversos?"*

Este es el flujo que se desarrolla en detalle, paso a paso, en el caso de uso completo de la Parte 8.

### 6.6 — Alternative Investment Decision Flow

```
NAV → Cash Flows → Vintage → TVPI/DPI/RVPI/IRR → Liquidity → Risk → Benchmark/Peer Comparison (si elegible) → Portfolio Impact → Interpretation
```

**Motores:** `AFI.Alternatives.Engine` (núcleo) → `AFI.Liquidity.Engine` → `AFI.Risk.Engine` → `AFI.Benchmark.Engine` (gate condicional).

**Regla explícita:** el fondo nunca se analiza aislado — el paso final obligatorio es Portfolio Impact, es decir, cómo esa posición específica afecta el patrimonio total del cliente (liquidez, riesgo, contribución a metas), no solo cómo le fue al fondo en sí mismo. Esto es consistente con v1.0 (Parte X): "no tratar automáticamente NAV privado como equivalente a precio de mercado" — aplicado aquí como "no evaluar el fondo aislado de su función en el patrimonio".

### 6.7 — Portfolio Construction Flow

```
Client Objectives → Horizons → Risk → Liquidity → Constraints → Current Portfolio → Expected Returns → Risk Model → Correlations → Optimization → Scenarios → Alternative Portfolios → Wealth Manager
```

**Motores:** `AFI.ClientGoal.Engine` → `AFI.Risk.Engine` → `AFI.Liquidity.Engine` → `AFI.Construction.Engine` (núcleo, incluyendo la optimización) → `AFI.Diversification.Engine` (correlaciones) → `AFI.Scenario.Engine`.

**Regla explícita y no negociable del flujo:** *la optimización nunca es el primer paso.* Ocho pasos preceden a Optimization en la secuencia — objetivos, horizontes, riesgo, liquidez, restricciones y el portafolio actual se establecen primero. Esto es la traducción operativa directa del Principio 4 de v1.0 (Parte VII): *"cómo encaja la optimización dentro del principio AFI de objetivos, riesgo, liquidez, horizonte, restricciones, comportamiento, incertidumbre"* — v1.0 fijó qué debe considerar la optimización; este flujo fija en qué **orden** se recopila antes de correrla.

### 6.8 — Rebalancing Decision Flow

```
Current Portfolio → Target Allocation → Drift → ¿Es material el drift? → Risk Impact → Liquidity Impact → Cost Impact → Tax/Restriction Data (cuando disponible) → Scenarios → Alternatives → Analytical Recommendation → Wealth Manager
```

**Motores:** `AFI.Construction.Engine` (target) → `AFI.Risk.Engine` → `AFI.Liquidity.Engine` → `AFI.Scenario.Engine`.

Este flujo es una elaboración operativa del `AFI.Rebalancing` conceptual ya definido en v1.0 (Parte XIII), con una adición explícita del mandato: el paso "¿Es material el drift?" como filtro previo antes de calcular impactos — evita ejecutar el análisis completo de costos y escenarios para desviaciones triviales. El sistema genera exactamente tres alternativas, tal como v1.0 ya especificaba en su Decision Library (D1):

- **Alternativa A** — No rebalancear.
- **Alternativa B** — Rebalanceo parcial.
- **Alternativa C** — Rebalanceo completo.

Cada una con sus consecuencias mostradas (retorno, riesgo, liquidez, costos) — nunca solo la alternativa que el modelo considera óptima (ver Parte 10, Alternative Generation).

### 6.9 — Fund / Manager Deterioration Flow

```
Performance → Benchmark → Risk → Factor Exposure → Qualitative Due Diligence → ¿Deterioro persistente? → Posibles causas → Portfolio Impact → Alternatives
```

**Motores:** `AFI.Performance.Engine` → `AFI.Benchmark.Engine` → `AFI.Risk.Engine` → (Due Diligence cualitativa, v1.0 heredado del Volumen II) → `AFI.Monitoring.Engine`.

Corresponde directamente a la decisión **D11** de la Decision Library de v1.0 ("¿Existe deterioro?"). Los outputs posibles son idénticos a los ya fijados ahí: Mantener / Mantener bajo monitoreo / Revisar / Evaluar sustitución — nunca "Sustituir" como acción ejecutada por el sistema.

### 6.10 — Opportunity Analysis Flow

Separación explícita entre **Opportunity Identification** e **Investment Decision** — el sistema puede señalar valoración atractiva, cambio de riesgo, mejora de liquidez, cambio de correlación, dislocación respecto de benchmark, cambio en expected return, o mejora de relación riesgo-retorno, pero la decisión de invertir corresponde siempre al WM/Comité.

Corresponde a la decisión **D12** de v1.0 ("¿Existe una oportunidad?"), donde v1.0 ya señalaba que este es un caso con "mayor peso relativo del juicio del WM". Este flujo no agrega motores nuevos — reutiliza `AFI.Performance.Engine`, `AFI.Risk.Engine`, `AFI.Diversification.Engine` y `AFI.Benchmark.Engine` en modo de detección, no de evaluación completa.

### 6.11 — Scenario Decision Flow

```
Base Case vs. Optimistic vs. Adverse vs. Stress → evaluar Return, Risk, Drawdown, Liquidity, Goal Probability, Currency, Concentration
```

**Motor:** `AFI.Scenario.Engine` (v1.0, Parte XI), ejecutado sobre cuatro escenarios en paralelo, nunca uno solo.

**Objetivo explícito, heredado sin modificación de v1.0:** *no predecir el futuro — entender qué tan robusta es una decisión frente a distintos futuros.* Este flujo puede insertarse dentro de cualquiera de los diez anteriores como paso de validación antes de Alternatives — no es un flujo aislado en la práctica, es el que valida a los demás.

---

## 7. Caso de Uso Completo

**Cliente ficticio:** María Elena Contreras, 52 años, empresaria retirada. Cliente de AFI desde hace 4 años. Portafolio gestionado por AFI: USD 2.400.000, con exposición a fondos líquidos de renta fija y variable (65%), y compromisos en dos vehículos de Private Equity vintage 2022 y 2024 (25%), más un colchón de liquidez en fondos money market (10%). IPS vigente, última revisión hace 14 meses.

**Pregunta que trae al WM:** *"María Elena me acaba de escribir — quiere comprar una casa de playa en Zapallar por USD 380.000 y necesita tener el dinero disponible en 7 meses. ¿Puede hacerlo sin desarmar su estrategia de largo plazo?"*

Este caso activa el **Liquidity Decision Flow** (6.5) como columna vertebral, con el **Scenario Decision Flow** (6.11) insertado antes de Alternatives, tal como se describe en 6.11. Se ejecuta paso a paso.

---

**PASO 1 — Unit of Analysis y Objective** (Principio 2.2, Parte 5.1)

El WM plantea la unidad de análisis como **Patrimonio** (no solo Portafolio AFI), porque la pregunta involucra si María Elena *"puede"* hacer la compra — lo cual requiere ver más allá de lo gestionado por AFI. El sistema pregunta si existen activos fuera de AFI relevantes para esta necesidad específica. El WM confirma: María Elena tiene además USD 90.000 en una cuenta corriente personal no gestionada por AFI, dato que no estaba en el IPS. Esto se registra como información nueva.

Objetivo declarado: nuevo objetivo de corto plazo — *Compra de activo (propiedad), USD 380.000, horizonte 7 meses, moneda USD, liquidez requerida: disponible en efectivo en la fecha, prioridad Alta según indica el WM en función de lo conversado con la clienta* — estructurado según el catálogo de la Parte 5.3, y añadido como objetivo simultáneo junto a los objetivos de largo plazo ya existentes en el IPS.

**PASO 2 — Available Data / Data Completeness** (Parte 4)

El sistema evalúa qué tiene y qué falta para este objetivo específico:

| Dato | Estado | Comportamiento |
|---|---|---|
| Horizonte (7 meses) | Disponible | — |
| Monto objetivo (USD 380.000) | Disponible | — |
| Liquidez actual gestionada por AFI | Disponible (custodio) | — |
| Cash flow personal fuera de AFI (gastos recurrentes, otros compromisos) | Faltante | **B. ADVERTENCIA** — el análisis de cobertura puede hacerse con los datos de AFI, pero no captura compromisos personales no declarados |
| Curva de capital calls proyectada de los dos vehículos PE | Disponible (histórico de vintages similares, v1.0 Parte X) | — |
| Actualización de tolerancia al riesgo post-evento (IPS de hace 14 meses) | Parcialmente desactualizado | **C. SIN IMPACTO MATERIAL** para esta pregunta específica de liquidez — sí sería relevante si la pregunta fuera sobre Construction |

Ninguna variable crítica está en Bloqueo — el análisis puede proceder con una nota de Advertencia visible sobre el cash flow personal no gestionado.

**PASO 3 — Relevant Engines** (Principio 3.2)

Se activan: `AFI.ClientGoal.Engine` (el nuevo objetivo), `AFI.Liquidity.Engine` (núcleo), `AFI.Alternatives.Engine` (curvas de capital calls de los dos vehículos PE), `AFI.Scenario.Engine` (estrés). **No se activan**: `AFI.Construction.Engine` (no se está replanteando la asignación estratégica todavía), `AFI.Diversification.Engine` (no es la pregunta), `AFI.Benchmark.Engine` (no hay comparación relativa en esta pregunta).

**PASO 4 — Análisis: Liquidity Ladder y Coverage**

`AFI.Liquidity.Engine` construye la escalera de vencimientos a 7 meses: el colchón money market (USD 240.000) cubre el 63% del monto necesario sin tocar nada más. Los USD 90.000 personales (dato nuevo del Paso 1) cubren otro 24%. Restan USD 50.000 (13%) que requerirían liquidar parte de la posición en fondos de renta fija líquidos — operación ejecutable en días, sin problema de liquidez estructural.

**Resultado del LCR a 7 meses: cobertura completa (113% del monto objetivo) usando solo activos líquidos, sin necesidad de tocar las posiciones en Private Equity.**

**PASO 5 — Diagnostics + Risks/Limitations**

El sistema señala dos elementos de contexto, no como bloqueos sino como parte del diagnóstico: (a) los dos vehículos de PE tienen capital calls proyectados en los próximos 12 meses (según curva de vintage histórica, v1.0 Parte X) que, combinados con el retiro de USD 50.000 de renta fija, reducirían el colchón de liquidez remanente a un nivel que amerita seguimiento — no crítico, pero visible; (b) el dato del Paso 2 (cash flow personal no declarado) significa que esta cobertura no incluye gastos personales recurrentes de María Elena fuera de AFI, que podrían competir por la misma liquidez.

**PASO 6 — Scenario Analysis** (Scenario Decision Flow, 6.11, insertado aquí)

`AFI.Scenario.Engine` corre los cuatro escenarios sobre esta necesidad específica de liquidez:

| Escenario | Impacto en cobertura del objetivo |
|---|---|
| Base Case | Cobertura 113%, sin fricción |
| Optimistic | Sin cambio material — el objetivo no depende de upside de mercado |
| Adverse (−15% en renta variable líquida) | Cobertura baja a 98% — todavía suficiente, pero con margen reducido; podría requerir liquidar una porción ligeramente mayor de renta fija |
| Stress (−15% equity + capital call simultáneo de ambos vehículos PE) | Cobertura baja a 81% — **insuficiente** sin recurrir a alguna fuente adicional (ej. línea de crédito con garantía de portafolio, o ajustar el monto/timing de la compra) |

**PASO 7 — Alternatives** (ver Parte 10 para el principio general)

- **Alternativa A — Proceder sin cambios.** Usar el colchón + fondos personales + venta parcial de renta fija. Funciona en Base y Optimistic; funciona con margen ajustado en Adverse; **no cubre completamente Stress**.
- **Alternativa B — Aumentar el colchón de liquidez ahora (2-3 meses antes de necesitarlo).** Vender una porción adicional de renta fija líquida hoy, para tener el 100% del monto en efectivo antes del escenario de stress. Reduce exposición a mercado durante el interín; costo de oportunidad si los mercados suben.
- **Alternativa C — Explorar línea de crédito con garantía del portafolio (Lombard) como respaldo.** No requiere liquidar nada ahora; mantiene la estrategia intacta incluso en Stress; introduce costo financiero y una nueva variable (tasa de la línea) que no estaba en el IPS original.

Cada alternativa se muestra con su impacto en retorno, riesgo, liquidez y objetivos de largo plazo — ninguna se presenta como "la respuesta".

**PASO 8 — Analytical Recommendation (Nivel 3)**

*"Según la evidencia disponible y el criterio de robustez frente a escenarios adversos, la Alternativa C presenta la mejor relación entre preservar la estrategia de largo plazo de María Elena y cubrir el escenario de Stress sin liquidar posiciones. Esta recomendación asume que una línea Lombard está disponible en condiciones razonables — dato no verificado en este análisis — y no considera la aversión personal de la clienta al endeudamiento, que el WM conoce mejor que el sistema."*

Nótese la estructura obligatoria de Nivel 3 (Parte 6 de este documento): la recomendación es condicional, declara sus supuestos, y señala explícitamente qué información cualitativa el WM tiene y el sistema no.

**PASO 9 — Wealth Manager decide**

El WM, que conoce a María Elena, decide combinar B y C: adelantar una venta parcial menor (no todo lo que sugería B) y, en paralelo, dejar pre-aprobada una línea Lombard como respaldo — una decisión mixta que ningún modelo propuso como alternativa pura, y que es exactamente el tipo de síntesis que corresponde al juicio profesional del ejecutivo, no al sistema.

**PASO 10 — Registro en Decision History** (Parte 14)

Se registra: fecha, cliente, unidad de análisis (Patrimonio), pregunta original, datos utilizados (incluyendo el flag de Advertencia sobre cash flow personal), motores activados, resultado del LCR, los cuatro escenarios, las tres alternativas, la recomendación de Nivel 3, y la decisión mixta real del WM — para que, en 7 meses, se pueda evaluar si la recomendación ayudó (Learning Loop, Parte 13).

---

## 8. Decision Library

Las 15 decisiones institucionales (D1-D15) ya están completamente definidas en v1.0 (Parte XVIII), cada una con sus inputs, modelos, reglas, evidencia y punto de Human Override. **Este documento no las redefine.** Lo que agrega es el mapeo hacia qué Decision Flow (Parte 6) las activa y en qué paso del flujo aparece el Human Override — la capa de "cómo se llega ahí", no "qué es la decisión".

| Decisión (v1.0) | Decision Flow que la activa (este documento) | Paso donde aparece el Human Override |
|---|---|---|
| D1 — ¿Rebalancear? | 6.8 Rebalancing Decision Flow | Tras "Analytical Recommendation", al elegir entre Alternativas A/B/C |
| D2 — ¿Mantener estrategia? | 6.1 Portfolio Diagnostic + 6.11 Scenario | Tras clasificar la señal como ruido vs. cambio estructural |
| D3/D4/D5 — ¿Cambiar/agregar/reducir fondo? | 6.9 Fund/Manager Deterioration | Tras "Alternatives", decisión siempre de Comité (v1.0) |
| D6 — ¿Aumentar liquidez? | 6.5 Liquidity Decision Flow | Tras "Alternatives", como en el Paso 7 del caso de uso (Parte 7) |
| D7 — ¿Existe concentración excesiva? | 6.4 Diversification Decision Flow | Tras "Concentration → Interpretation" |
| D8 — ¿El riesgo es compatible con el IPS? | 6.3 Risk Decision Flow | Tras "Client Constraints" — el Comité aprueba excepciones documentadas |
| D9 — ¿La liquidez es suficiente? | 6.5 Liquidity Decision Flow | Igual que D6 — comparten infraestructura (v1.0) |
| D10 — ¿El benchmark es elegible? | 6.2 Performance Decision Flow (gate inicial) | El Comité puede documentar una excepción acotada (v1.0) |
| D11 — ¿Existe deterioro? | 6.9 Fund/Manager Deterioration | Tras "Portfolio Impact → Alternatives" |
| D12 — ¿Existe una oportunidad? | 6.10 Opportunity Analysis | Al pasar de Identification a Investment Decision |
| D13 — ¿Rebalanceo extraordinario? | 6.8 Rebalancing + 6.11 Scenario | Requiere aprobación explícita del Comité (v1.0) — no es flujo automático |
| D14 — Aprobación de nuevos gestores | 6.6 Alternative Investment (para vehículos privados) o due diligence general (Volumen II) | Comité de Inversiones, framework de 7 etapas (v1.0, referenciando Volumen II) |
| D15 — Gobernanza de modelos | No corresponde a un Decision Flow de cliente — es transversal a todos (v1.0, Parte XIV) | Comité de Model Risk, no el WM individual |

**Por qué esta tabla no repite el contenido de v1.0:** cada fila de la Parte XVIII de v1.0 ya trae inputs, modelos, reglas y evidencia completos para su decisión. Repetirlos aquí sería exactamente el tipo de "modificación silenciosa por duplicación" que el mandato de este documento prohíbe evitar — si en el futuro v1.0 se actualiza, una copia aquí quedaría desactualizada sin que nadie lo note. Esta tabla existe solo para conectar decisión con flujo operativo.

---

## 9. Recommendation Engine — Niveles de Autonomía

### 9.1 — Los cinco niveles, con el cuarto explícitamente inexistente

| Nivel | Pregunta que responde | Ejemplo | ¿Existe en AFI? |
|---|---|---|---|
| **Nivel 0 — Información** | ¿Qué está ocurriendo? | "El portafolio tiene un TE de 4.2% vs. su banda institucional de 2-3%" | Sí |
| **Nivel 1 — Diagnóstico** | ¿Por qué está ocurriendo? | "El TE elevado viene de una sobreponderación táctica en EM equity, no de selección de fondos" | Sí |
| **Nivel 2 — Alternativas** | ¿Qué opciones existen? | Alternativas A/B/C con sus impactos (Parte 10) | Sí |
| **Nivel 3 — Recomendación** | Según los criterios definidos y la evidencia disponible, ¿qué alternativa parece superior? | Paso 8 del caso de uso (Parte 7) | Sí — techo máximo |
| **Nivel 4 — Ejecución** | — | — | **No existe. No está en el roadmap de ninguna versión futura contemplada por este documento.** |

### 9.2 — Qué debe acompañar siempre a una recomendación de Nivel 3

Ninguna recomendación de Nivel 3 se presenta como un veredicto aislado. Debe mostrar, sin excepción, los siete elementos que fija el mandato:

1. **Criterios utilizados** — qué se optimizó o priorizó para llegar a esa conclusión.
2. **Pesos** — si los criterios se combinaron con distinta importancia relativa, cuál fue esa ponderación.
3. **Restricciones** — qué límites (del IPS, institucionales) acotaron el espacio de alternativas evaluado.
4. **Escenarios** — bajo qué condiciones se validó la robustez de la recomendación (Parte 6.11).
5. **Sensibilidad** — qué tan frágil es la conclusión ante cambios razonables en los supuestos.
6. **Información faltante** — qué dato, de haber estado disponible, podría haber cambiado la recomendación (conectado con Parte 4).
7. **Limitaciones** — qué el sistema explícitamente no puede evaluar (típicamente, información cualitativa que el WM sí tiene — ver Paso 8 del caso de uso).

**Frase prohibida, de forma explícita y permanente:** el sistema nunca presenta *"esta es la decisión correcta"*. La forma correcta, en todos los casos, es una construcción condicional: *"según [criterios], [alternativa] parece [comparativo], considerando que [limitación]"* — exactamente el patrón usado en el Paso 8 de la Parte 7.

---

## 10. Alternative Generation

**Regla central:** cuando existe una decisión relevante, el sistema genera **el espacio de decisión, no un único óptimo**. El patrón mínimo es de tres alternativas (ilustrado en 6.8 con Mantener/Parcial/Completo, y en el caso de uso de la Parte 7 con A/B/C), aunque el número exacto depende del tipo de decisión.

Cada alternativa se presenta con la misma estructura, sin excepción — nunca se favorece visualmente una sobre otra mostrando más detalle de una que de las demás:

- **Descripción** de la alternativa.
- **Impacto en retorno.**
- **Impacto en riesgo.**
- **Impacto en liquidez.**
- **Impacto en objetivos** (vía `AFI.ClientGoal.Engine`).

**Por qué esto no es lo mismo que el Nivel 3:** Alternative Generation ocurre en el Nivel 2 — es la enumeración neutral del espacio de opciones. El Nivel 3 (Recommendation Engine, sección 9) es un paso posterior y opcional que *además* señala cuál de esas alternativas, ya generadas y mostradas todas por igual, parece superior según criterios explícitos. Un flujo puede detenerse en Nivel 2 (mostrar alternativas sin recomendar) cuando la naturaleza de la decisión lo amerita — típicamente en D12, Opportunity Analysis (6.10), donde v1.0 ya señalaba mayor peso relativo del juicio del WM.

---

## 11. Information Confidence

Toda conclusión se asocia, de forma explícita y en lenguaje natural (no necesariamente un score numérico), a uno de tres niveles de robustez:

| Nivel | Cuándo aplica |
|---|---|
| **Alta robustez** | Datos suficientes y metodología estable — sin flags de Advertencia (B) activos en los datos usados |
| **Robustez media** | Existen limitaciones relevantes — uno o más flags de Advertencia (B) activos |
| **Baja robustez** | La conclusión depende significativamente de información faltante o de supuestos no verificados |

**Relación explícita con la Parte 4 (Data Completeness Engine):** Information Confidence es, en la práctica, el resumen agregado de los flags de Bloqueo/Advertencia/Sin Impacto Material que se activaron durante el flujo. No es un cálculo independiente — es una traducción a lenguaje de decisión de algo que el sistema ya sabe desde el Paso 2 de cualquier flujo (ver Paso 2 del caso de uso, Parte 7, donde el flag de Advertencia sobre cash flow personal se traduce directamente en Robustez media para la conclusión final del LCR).

**Por qué no necesariamente un score numérico:** el mandato es explícito en que la explicación debe ser explícita, no reducida a un número — esto es coherente con el Principio 2.4 (no colapsar en un score) aplicado ahora a la confianza de la conclusión, no solo a la salud del portafolio.

---

## 12. Learning Loop

**Explícitamente, no requiere Machine Learning** — es un loop institucional, no un sistema de aprendizaje automático:

```
RECOMENDACIÓN → DECISIÓN EJECUTIVO → RESULTADO → SEGUIMIENTO → EVALUACIÓN → MEJORA DE METODOLOGÍA
```

Este loop permite estudiar, con el tiempo: qué recomendaciones fueron aceptadas, cuáles rechazadas y por qué, resultados posteriores, falsos positivos y falsos negativos, y si los umbrales institucionales (los mismos umbrales que v1.0 dejó como Pendiente 4 — "no fijar sin conocer el riesgo real de la cartera de AFI") resultaron demasiado agresivos o demasiado laxos en la práctica.

**Conexión directa con el Pendiente 4 de v1.0:** este es, precisamente, el mecanismo mediante el cual esos umbrales pendientes eventualmente se calibran con evidencia real en vez de fijarse por adivinanza — el Learning Loop no resuelve el Pendiente 4 hoy, pero es la infraestructura que permitiría resolverlo con datos propios de AFI en el futuro, tal como el propio Pendiente 4 de v1.0 exige.

**Qué NO es este loop:** no es un sistema que ajusta automáticamente parámetros o pesos de decisión basado en resultados pasados — eso sería introducir exactamente el tipo de aprendizaje automático que el mandato prohíbe ("NO utilizar Machine Learning necesariamente" se lee aquí, de forma conservadora, como "el mecanismo por defecto es institucional/humano, no algorítmico", consistente con el rechazo de ML por sofisticación ya fijado en v1.0 Principio 4).

---

## 13. Decision History

Cada decisión de cliente registrada, con los siguientes campos:

| Campo | Contenido |
|---|---|
| Fecha | Momento de la decisión |
| Cliente | Identificador del cliente |
| Unidad analizada | Cuál de las nueve unidades de la Parte 5.1 |
| Pregunta | La pregunta original del WM o del cliente, en su forma natural (ej. "¿puede comprarse la casa?") |
| Datos utilizados | Referencia a los datos del Paso 2 de cualquier flujo, incluyendo qué flags de Advertencia/Bloqueo estuvieron activos |
| Modelos | Qué motores de v1.0 se activaron (Principio 3.2) |
| Resultado | El diagnóstico/análisis producido |
| Alternativas | Las generadas en el Nivel 2 (Parte 10) |
| Recomendación | La de Nivel 3, si se llegó a ese nivel |
| Decisión del ejecutivo | Qué eligió el WM — incluyendo, como en el caso de uso (Paso 9), decisiones mixtas que combinan alternativas de formas que el sistema no propuso |
| Resultado posterior | A completarse en el seguimiento — alimenta el Learning Loop (Parte 12) |

**Relación con la Parte XXI de v1.0:** v1.0 ya define un registro de auditoría exhaustivo a nivel de cada output de motor (datos, fecha, modelo, parámetros, resultado, regla activada, recomendación, decisión, override, justificación, fecha de revisión). Decision History **no duplica ese registro técnico** — es un nivel de agregación distinto: mientras el log de v1.0 registra cada cálculo individual, Decision History registra la conversación completa de decisión de principio a fin, tal como se ilustra en el Paso 10 del caso de uso (Parte 7). Un WM consultando Decision History ve la historia de la decisión; un auditor técnico consultando el log de v1.0 ve la trazabilidad matemática exacta de cada número que la sostuvo.

---

## 14. Matriz Maestra de Casos de Uso

Los 18 casos de uso obligatorios del mandato (Volumen IV, Sección 34), mapeados a su Decision Flow correspondiente (Parte 6) y al nivel máximo de autonomía típicamente alcanzado (Parte 9). **Esta matriz remite al flujo correspondiente para el detalle operativo — no lo repite**, siguiendo el mismo principio anti-duplicación de la Parte 8.

| # | Caso de uso | Unidad de análisis típica | Decision Flow (Parte 6) | Motores núcleo activados | Nivel máx. típico |
|---|---|---|---|---|---|
| 1 | Nuevo cliente | Cliente completo | 5.2 Client Onboarding (no es un Decision Flow numerado — es el paso previo a cualquiera) | Ninguno aún — recopilación de datos | Nivel 0 |
| 2 | Diagnóstico inicial | Portafolio o Patrimonio | 6.1 Portfolio Diagnostic | Subconjunto de los 10, según lo que ya haya disponible | Nivel 1 |
| 3 | Construcción de portafolio | Portafolio | 6.7 Portfolio Construction | `AFI.Construction.Engine`, `AFI.ClientGoal.Engine` | Nivel 3 |
| 4 | Revisión periódica | Portafolio | 6.1 Portfolio Diagnostic (dimensiones relevantes) | Variable | Nivel 2-3 |
| 5 | Rebalanceo | Portafolio | 6.8 Rebalancing | `AFI.Construction.Engine`, `AFI.Risk.Engine`, `AFI.Liquidity.Engine` | Nivel 3 |
| 6 | Deterioro de fondo | Fondo individual | 6.9 Fund/Manager Deterioration | `AFI.Performance.Engine`, `AFI.Monitoring.Engine` | Nivel 2 (D11 exige Comité) |
| 7 | Cambio de estrategia | Portafolio o Estrategia | 6.1 + 6.7 combinados | `AFI.Construction.Engine`, `AFI.ClientGoal.Engine` | Nivel 3 |
| 8 | Evaluación de nueva inversión | Fondo individual | 6.6 Alternative Investment (si es vehículo privado) o due diligence general | `AFI.Alternatives.Engine` o Volumen II | Nivel 2 |
| 9 | Evaluación de oportunidad | Variable | 6.10 Opportunity Analysis | Detección, no evaluación completa | Nivel 1-2 (D12) |
| 10 | Problema de liquidez | Patrimonio o Portafolio | 6.5 Liquidity Decision Flow | `AFI.Liquidity.Engine`, `AFI.ClientGoal.Engine` | Nivel 3 — ver caso completo, Parte 7 |
| 11 | Cambio en objetivos del cliente | Cliente | 5.3 Client Objectives → dispara re-evaluación vía flujos relevantes | `AFI.ClientGoal.Engine` | Nivel 1 (recopilación) |
| 12 | Cambio de riesgo | Portafolio | 6.3 Risk Decision Flow | `AFI.Risk.Engine` | Nivel 2 |
| 13 | Cambio de horizonte | Objetivo específico | 5.4 Multi-horizonte → dispara 6.7 si afecta SAA | `AFI.ClientGoal.Engine`, `AFI.Construction.Engine` | Nivel 2 |
| 14 | Revisión de asset allocation | Portafolio | 6.7 Portfolio Construction | `AFI.Construction.Engine` | Nivel 3 |
| 15 | Monitoreo de alternativos | Asset class (PE/PC/RE) | 6.6 Alternative Investment | `AFI.Alternatives.Engine`, `AFI.Liquidity.Engine` | Nivel 1-2 |
| 16 | Benchmark review | Portafolio o Fondo | 6.2 Performance (gate inicial) | `AFI.Benchmark.Engine` | Nivel 0 (estado elegible/no-elegible) |
| 17 | Stress analysis | Portafolio o Patrimonio | 6.11 Scenario Decision Flow | `AFI.Scenario.Engine` | Nivel 1-2 |
| 18 | Revisión integral del patrimonio | Patrimonio | 6.1 Portfolio Diagnostic (todas las dimensiones) | Los 10 motores, según relevancia | Nivel 2-3 |

---

## 15. Matriz de Datos

Clasificación de variables por su impacto si faltan, consolidando el vocabulario de la Parte 4. Esta matriz no repite el Data Dictionary conceptual completo de v1.0 (Parte XVI, que ya cubre NAV, Returns, Factsheets, Holdings, Benchmarks, FX, Tasas, Cash flows, Capital Calls, Distributions, Fees, Client Objectives, IPS con su fuente y frecuencia) — se limita a mapear cada variable a su categoría de criticidad y comportamiento, que es lo que v1.0 no especificaba a este nivel de decisión operativa.

| Variable | Motor principal | Categoría | Si falta | Impacto | Fuente (heredada de v1.0 Parte XVI) |
|---|---|---|---|---|---|
| Horizonte del cliente | `AFI.ClientGoal.Engine`, `AFI.Construction.Engine` | **CRÍTICA** | Bloquea (A) | Bloquea todo análisis dependiente de horizonte | IPS |
| Benchmark elegible | `AFI.Benchmark.Engine` | **CRÍTICA** (para comparación relativa específicamente) | Bloquea (A) | Bloquea ranking relativo; no bloquea Performance/Riesgo absolutos | Proveedores de índices |
| NAV histórico (bajo el mínimo del modelo) | `AFI.Performance.Engine`, `AFI.Risk.Engine` | **CRÍTICA** (condicional al umbral del modelo específico) | Bloquea (A) ese indicador puntual | Depende del modelo — ver v1.0 Parte XXII para umbrales por métrica | Custodio, administrador |
| Flujos de caja fechados y clasificados | `AFI.Performance.Engine` | **CRÍTICA** | Bloquea (A) TWR/MWR | Sin retorno confiable | Custodio |
| Información de liquidez personal fuera de AFI | `AFI.Liquidity.Engine` | **IMPORTANTE** | Advertencia (B) | Cobertura calculada es parcial, no total del patrimonio (ver Paso 2, caso de uso) | Cliente, vía WM |
| Holdings detallados (look-through) | `AFI.Diversification.Engine`, `AFI.Risk.Engine` (factor) | **IMPORTANTE** | Advertencia (B) | Análisis a nivel de fondo agregado disponible; factor exposure limitado | Gestora (transparencia variable) |
| Curva de capital calls proyectada | `AFI.Liquidity.Engine`, `AFI.Alternatives.Engine` | **IMPORTANTE** | Advertencia (B) | Estimación basada en vintage similar en vez de curva propia del fondo | Gestora del vehículo privado |
| IPS desactualizado (>3 años o evento de vida no reflejado) | `AFI.ClientGoal.Engine` | **IMPORTANTE** (crítica si la pregunta específica depende de tolerancia al riesgo) | Advertencia (B) o Bloqueo (A) según la pregunta | Ver Paso 2 del caso de uso — depende de si la pregunta actual lo necesita | Asesor + Cliente |
| Preferencia de frecuencia de comunicación | `AFI.Monitoring.Engine` | **COMPLEMENTARIA** | Sin impacto (C) | Ninguno en el análisis cuantitativo | Cliente, vía WM |
| Datos ESG/exclusiones específicas (si no aplican al cliente) | `AFI.Construction.Engine` | **COMPLEMENTARIA** (para clientes sin restricción declarada) | Sin impacto (C) | Ninguno — ver v1.0 Pendiente 6 sobre si esto debería ser institucional | IPS |

**Nota:** la columna "Categoría" usa exactamente la terminología del mandato (CRÍTICA/IMPORTANTE/COMPLEMENTARIA), que este documento trata como sinónimo operativo de los tres comportamientos de la Parte 4 (A/B/C respectivamente) — se listan ambas nomenclaturas en la tabla para que sea consultable desde cualquiera de los dos vocabularios.

---

## 16. Matriz de Reglas

Triggers que conectan una condición detectada con el motor que la procesa, el output que produce, y el punto de decisión humana — formato pedido explícitamente por el mandato (Volumen IV, Sección 37), con el ejemplo del propio mandato como primera fila.

| Trigger | Condición | Motor | Output | Acción del sistema | Decisión humana |
|---|---|---|---|---|---|
| Drift material | Desviación de peso fuera de banda institucional | `AFI.Construction.Engine` → Risk Impact → `AFI.Rebalancing` (v1.0 Parte XIII) | 3 alternativas (No/Parcial/Completo) con impactos | Genera y muestra alternativas | Wealth Manager elige (D1) |
| Benchmark no elegible | Falla ≥1 de las 8 dimensiones (v1.0 Parte XII) | `AFI.Benchmark.Engine` | Estado no-elegible + dimensión que falló | Bloquea el ranking relativo | Comité puede documentar excepción acotada (D10) |
| VaR/ES sobre límite de perfil | Violación de límite IPS | `AFI.Risk.Engine` | Alerta con magnitud de la violación | Alerta, sin ajuste automático | Comité aprueba excepción documentada (D8) |
| Concentración sobre umbral | HHI o risk contribution excede umbral institucional en alguna dimensión | `AFI.Diversification.Engine` | Flag con la dimensión específica de concentración | Alerta especificando la dimensión | WM decide si es aceptable dado el objetivo del cliente (D7) |
| Déficit de liquidez proyectado bajo estrés | LCR bajo el mínimo en escenario adverso | `AFI.Liquidity.Engine` + `AFI.Scenario.Engine` | Plan de liquidez con alternativas de reasignación | Genera alternativas | WM decide timing y composición (D6/D9) — ver Paso 7 del caso de uso |
| Deterioro cuantitativo + cualitativo combinado | Alpha rolling negativo persistente + hallazgo de due diligence | `AFI.Performance.Engine` + `AFI.Monitoring.Engine` | Clasificación causa raíz (cíclico/estructural/operacional) | Watchlist automática | Comité decide mantener/watchlist/eliminar (D11) |
| Movimiento extremo de mercado | VaR/drawdown excede umbral pre-definido | `AFI.Risk.Engine` + `AFI.Scenario.Engine` | Evaluación de rebalanceo extraordinario | Alerta de alta prioridad | Requiere aprobación explícita del Comité — no es flujo automático (D13) |
| Nueva pregunta de cliente con unidad de análisis ambigua | El WM no especifica unidad (Parte 5.1) | Ninguno aún | Solicitud de clarificación | Pregunta la unidad antes de activar motores | WM especifica la unidad (Paso 1 del caso de uso) |

---

## 17. Matriz de Outputs

**Regla central del mandato: nunca entregar solamente un número.** Todo output que llega al WM incluye, como estructura mínima, estos ocho componentes — aunque algunos puedan estar vacíos cuando no aplican (p. ej. un output de Nivel 0 no tiene aún Recomendación ni Alternativas):

| Componente | Qué contiene | Ejemplo del caso de uso (Parte 7) |
|---|---|---|
| **Indicador** | El resultado numérico o cualitativo del motor | "LCR a 7 meses: 113%" |
| **Contexto** | Cómo interpretar ese número dado el cliente específico | "Cubre el monto objetivo sin tocar las posiciones en Private Equity" |
| **Riesgo** | Qué podría hacer que ese resultado cambie desfavorablemente | "Capital calls próximos de los dos vehículos PE reducirían el colchón remanente" |
| **Escenario** | Cómo se comporta el indicador bajo Base/Optimistic/Adverse/Stress | Tabla del Paso 6 — cae a 81% en Stress |
| **Alternativa** | Las opciones generadas en Nivel 2 | Alternativas A/B/C del Paso 7 |
| **Recomendación** | Si se llegó a Nivel 3, cuál alternativa parece superior y por qué | Paso 8 — Alternativa C, con sus condicionantes explícitos |
| **Limitación** | Qué el sistema no puede evaluar | "No considera la aversión personal de la clienta al endeudamiento" (Paso 8) |
| **Información faltante** | Qué dato adicional mejoraría el análisis | "Cash flow personal fuera de AFI" (Paso 2) |

Esta estructura de ocho componentes es el "envoltorio" universal — se aplica igual a un output de `AFI.Risk.Engine` que a uno de `AFI.Liquidity.Engine`, garantizando que el WM siempre recibe el mismo tipo de contenedor de información sin importar qué motor de v1.0 lo generó.

### 17.1 — Executive Workspace (interfaz de decisión conceptual)

El mandato pide definir, sin diseñar aún la UI, una interfaz de decisión conceptual — el lugar donde el WM efectivamente ve todo lo que este documento describe, ya ensamblado. No es un motor ni un flujo nuevo: es el contenedor visual de la estructura de 8 componentes anterior, organizado como una sesión de trabajo completa en vez de un output aislado.

| Sección del Workspace | Qué responde | De dónde viene |
|---|---|---|
| **Pregunta / Objetivo** | ¿Qué quiere analizar el WM? | Paso 1 de cualquier flujo — Unit of Analysis + Objective (Parte 3.1) |
| **Situación actual** | ¿Qué está ocurriendo? | Nivel 0 — Información (Parte 9.1) |
| **Evidencia** | ¿Qué muestran los datos? | El Indicador + Contexto de la Matriz de Outputs (arriba) |
| **Riesgos / Limitaciones** | ¿Qué debe tener presente el WM? | El Riesgo + Limitación de la Matriz de Outputs |
| **Escenarios** | ¿Qué ocurre bajo distintos futuros? | `AFI.Scenario.Engine`, Decision Flow 6.11 |
| **Alternativas** | ¿Qué opciones existen? | Nivel 2 — Alternative Generation (Parte 10) |
| **Recomendación analítica** | ¿Qué alternativa parece más consistente? | Nivel 3, con sus 7 elementos obligatorios (Parte 9.2) |
| **Información faltante** | ¿Qué podría mejorar el análisis? | Data Completeness Engine (Parte 4), flags de Bloqueo/Advertencia activos |
| **Decisión** | El WM decide | Registrado en Decision History (Parte 13) |

**Por qué esto no es una UI todavía:** cada fila de esta tabla es un contenido, no un layout — el mandato es explícito en que el diseño visual (dónde va cada sección, cómo se navega entre ellas) es una decisión posterior de producto, no parte de este documento metodológico. Lo que sí fija este documento es que **las nueve secciones deben estar presentes siempre que aplique**, en este orden lógico, independientemente de cómo se termine viendo en pantalla — el mismo orden, no coincidentemente, que sigue el caso de uso completo de la Parte 7 de principio a fin.

---

## 18. Traducción a Software

Sin código definitivo: para cada Decision Flow de la Parte 6, la secuencia `Trigger → Required Inputs → Optional Inputs → Data Validation → Models Activated → Business Rules → Outputs → Alternatives → Recommendation → Human Decision → History`. Se ilustra en detalle para los tres flujos más frecuentes en la práctica de un Multi Family Office; el resto sigue el mismo patrón aplicado a su propia secuencia de la Parte 6.

### 6.5 Liquidity Decision Flow → especificación
- **Trigger:** pregunta del WM/cliente sobre capacidad de cubrir una necesidad de liquidez (nueva o ya existente en el IPS).
- **Required Inputs:** monto, fecha, moneda del objetivo; posiciones líquidas actuales del portafolio AFI.
- **Optional Inputs:** liquidez personal fuera de AFI; curva propia de capital calls (si no está, usa vintage similar como proxy — con Advertencia).
- **Data Validation:** aplica el Data Completeness Engine (Parte 4) — ver Paso 2 del caso de uso como ejecución real de este paso.
- **Models Activated:** `AFI.Liquidity.Engine` (núcleo), `AFI.Alternatives.Engine` (si hay vehículos privados), `AFI.Scenario.Engine`, `AFI.ClientGoal.Engine`.
- **Business Rules:** el objetivo de liquidez no puede evaluarse sin horizonte y monto (ambos CRÍTICOS, Parte 15); LCR se calcula por bucket, no agregado (v1.0 Parte IX).
- **Outputs:** LCR proyectado en Base/Optimistic/Adverse/Stress, con la estructura de 8 componentes de la Parte 17.
- **Alternatives:** mínimo 2-3, generadas según la Parte 10 (ver Paso 7 del caso de uso).
- **Recommendation:** Nivel 3, con los 7 elementos obligatorios de la Parte 9.2.
- **Human Decision:** registrada explícitamente, incluyendo decisiones mixtas no anticipadas por el sistema (Paso 9 del caso de uso).
- **History:** registro completo según Parte 13.

### 6.8 Rebalancing Decision Flow → especificación
- **Trigger:** drift detectado sobre banda institucional, o solicitud directa del WM.
- **Required Inputs:** portafolio actual, target allocation vigente (SAA del IPS).
- **Optional Inputs:** datos fiscales o de restricción específicos del cliente (v1.0 ya los marca como "cuando disponible").
- **Data Validation:** verifica que el drift sea material antes de continuar (filtro explícito de 6.8) — evita ejecutar el resto del flujo para desviaciones triviales.
- **Models Activated:** `AFI.Construction.Engine`, `AFI.Risk.Engine`, `AFI.Liquidity.Engine`, `AFI.Scenario.Engine`.
- **Business Rules:** exactamente 3 alternativas generadas (No/Parcial/Completo, heredado de D1 en v1.0); ninguna se ejecuta automáticamente.
- **Outputs:** impacto en retorno/riesgo/liquidez/costos por alternativa.
- **Alternatives:** las 3 fijas del flujo 6.8.
- **Recommendation:** Nivel 3 opcional, según la magnitud del drift.
- **Human Decision:** WM elige, modifica, o decide no actuar (D1, v1.0).
- **History:** registro completo.

### 6.9 Fund/Manager Deterioration Flow → especificación
- **Trigger:** combinación de señal cuantitativa (alpha rolling negativo) y/o cualitativa (hallazgo de due diligence, cambio de equipo).
- **Required Inputs:** historial de performance del fondo, benchmark elegible, datos de due diligence cualitativa vigentes.
- **Optional Inputs:** factor exposure detallado (si hay look-through disponible).
- **Data Validation:** benchmark debe pasar el gate de elegibilidad antes de evaluar deterioro relativo (6.2, 6.9 comparten esta dependencia).
- **Models Activated:** `AFI.Performance.Engine`, `AFI.Benchmark.Engine`, `AFI.Risk.Engine`, `AFI.Monitoring.Engine`.
- **Business Rules:** deterioro cuantitativo aislado no es suficiente — requiere clasificación de causa raíz antes de proponer acción (Parte 6.9).
- **Outputs:** clasificación cíclico/estructural/operacional, con Portfolio Impact.
- **Alternatives:** Mantener / Mantener bajo monitoreo / Revisar / Evaluar sustitución (fijas, v1.0 D11).
- **Recommendation:** Nivel 2 típicamente — la decisión final es siempre de Comité (D11, v1.0), no una recomendación de Nivel 3 del sistema hacia el WM individual.
- **Human Decision:** Comité de Inversiones decide.
- **History:** registro completo, incluyendo el hallazgo cualitativo que originó el trigger.

---

## 19. Limitaciones

Este documento, igual que v1.0, declara honestamente lo que no resuelve — no por descuido, sino porque resolverlo sin evidencia sería precisamente el tipo de invención que el mandato prohíbe.

**Limitación 1 — Este framework no valida contra volumen real de consultas.** Los 11 decision flows y las 4 matrices están diseñados a partir de los documentos base, no probados contra el volumen y variedad reales de preguntas que los WM de AFI hacen día a día. Es plausible que la operación real revele preguntas que no encajan limpiamente en ninguno de los 18 casos de uso de la Parte 14, o flujos que en la práctica necesitan combinarse de formas no anticipadas aquí (como ya ocurrió parcialmente en el caso de uso de la Parte 7, que combinó 6.5 y 6.11).

**Limitación 2 — La frontera entre "Advertencia" y "Sin Impacto Material" depende de umbrales no fijados.** La Parte 4 define el vocabulario de los tres comportamientos, pero — igual que v1.0 (Pendiente 2) — no fija el umbral numérico exacto que separa un gap "menor" de uno "significativo" para cada tipo de dato. Este documento hereda ese pendiente explícitamente, no lo resuelve.

**Limitación 3 — La estructura de 8 componentes de la Matriz de Outputs (Parte 17) asume que todos los motores pueden producir los 8 en todos los casos.** En la práctica, algunos outputs de Nivel 0 (información pura) no tendrán Alternativas ni Recomendación de forma natural — el documento trata esto como "componente vacío cuando no aplica", pero no especifica una regla exhaustiva de cuándo cada componente es opcional vs. obligatorio para cada tipo de output.

**Limitación 4 — El Learning Loop (Parte 12) es conceptual, no operacional.** Se describe el ciclo y su relación con el Pendiente 4 de v1.0, pero no se especifica con qué frecuencia se ejecuta la fase de "Evaluación", quién es responsable de ella, ni qué constituye evidencia suficiente para ajustar un umbral institucional. Esto es, en parte, deliberado — depende de decisiones organizacionales de AFI que ningún documento metodológico puede fijar por adelantado.

---

## 20. Decisiones Metodológicas Pendientes

v1.0 ya registró seis pendientes (v1.0, Parte XXIII) que este documento hereda sin resolver — no se repiten aquí. Los siguientes son **pendientes nuevos**, específicos de la capa de orquestación que v1.0 no cubría porque no se ocupaba de cómo el sistema recorre la información.

### Pendiente 7 — Umbral de materialidad del drift (6.8) y de otros filtros de "¿es esto relevante?"
**Clasificación:** Metodológico / Datos.
**Qué falta definir:** el Rebalancing Decision Flow (6.8) exige explícitamente evaluar "¿Es material el drift?" antes de continuar el flujo completo — pero ningún documento base (ni v1.0 ni el Volumen IV) fija qué porcentaje de desviación constituye "material" versus "ruido que no amerita el análisis completo". Es la misma naturaleza de pendiente que el Pendiente 4 de v1.0 (umbrales de rebalanceo), pero aplicado ahora al filtro de entrada del flujo, no a la banda de rebalanceo en sí.
**Quién debe resolverlo:** Investment Committee, en conjunto con el Learning Loop (Parte 12) una vez haya evidencia operativa.

### Pendiente 8 — Qué ocurre cuando dos Decision Flows entregan recomendaciones en tensión
**Clasificación:** Metodológico.
**Qué falta definir:** el caso de uso de la Parte 7 combinó 6.5 (Liquidity) y 6.11 (Scenario) de forma coherente porque el escenario de Stress simplemente añadía información al mismo flujo. Pero no está definido qué hace el sistema cuando dos flujos activados por la misma pregunta entregan alternativas que compiten entre sí de forma más directa — por ejemplo, si el Liquidity Flow recomendara "vender renta fija" y, en paralelo, el Risk Flow señalara que esa venta específica rompe una banda de TE. Ningún documento base especifica un protocolo de resolución de conflictos entre outputs de motores distintos dentro de la misma pregunta — actualmente, por diseño (Principio 2.5, Jerarquización Humana), esto simplemente se muestra ambos al WM sin resolverlo, pero no está probado si eso es suficiente en casos de tensión más aguda que la del caso de uso.
**Quién debe resolverlo:** requiere observación de casos reales — es exactamente el tipo de aprendizaje que el Learning Loop (Parte 12) está diseñado para capturar, pero aún no hay evidencia operativa que lo alimente.

### Pendiente 9 — Alcance exacto de "Optional Inputs" en el Client Onboarding
**Clasificación:** Cliente / Política AFI.
**Qué falta definir:** la Parte 5.2 distingue información necesaria de información que aumenta robustez, pero el catálogo completo (objetivo, horizonte, liquidez, tolerancia, capacidad de riesgo, patrimonio, flujos futuros, moneda, restricciones, inversiones existentes, IPS) no especifica, para cada pregunta posible del WM, exactamente cuáles de esos diez elementos son necesarios versus deseables — eso varía según el flujo activado y no se puede fijar de forma genérica sin el riesgo de sobre-pedir o sub-pedir información en casos reales.
**Quién debe resolverlo:** equipo de producto/UX de AFI en conjunto con los WM, una vez exista una primera versión operativa del Executive Workspace (Parte 17.1).

---

## 21. Roadmap hacia ESFS

Este documento y v1.0 son, juntos, el input completo para la futura **AFI Expert System Functional Specification (ESFS)**. La secuencia de trabajo que queda pendiente, en orden de dependencia:

### Etapa 1 — Validación operativa mínima
Ejecutar manualmente (sin software) 2-3 de los 18 casos de uso de la Parte 14 con clientes reales de AFI, siguiendo el mismo nivel de detalle del caso de uso de la Parte 7, para confirmar que los Decision Flows de la Parte 6 realmente cubren la variedad de preguntas que llegan en la práctica (aborda directamente la Limitación 1, Parte 19).

### Etapa 2 — Resolución de pendientes numéricos
Con la evidencia de la Etapa 1, calibrar los umbrales que tanto v1.0 (Pendientes 2 y 4) como este documento (Pendiente 7) dejaron explícitamente sin fijar — este es el primer uso real del Learning Loop (Parte 12), aunque todavía de forma manual/institucional, no automatizada.

### Etapa 3 — Auditoría de infraestructura de datos
Corresponde directamente al Pendiente 5 de v1.0 (capacidad tecnológica real vs. diseño conceptual) — debe completarse antes de que la ESFS pueda especificar con qué sistemas se integra cada motor.

### Etapa 4 — Especificación funcional de la ESFS
Una vez resueltas las Etapas 1-3, la ESFS puede tomar: los 10 módulos de v1.0 (Parte XXIV) + los 11 Decision Flows de este documento (Parte 6) + la estructura de Traducción a Software de la Parte 18 + la Matriz de Reglas (Parte 16) como su input funcional directo, sin necesidad de reinterpretación adicional.

### Etapa 5 — Prototipo del Executive Workspace
Solo después de la Etapa 4 tiene sentido diseñar la UI real del Workspace descrito en la Parte 17.1 — diseñar la interfaz antes de tener la especificación funcional completa arriesgaría construir pantallas que no reflejen correctamente el flujo de datos subyacente.

**Nota explícita sobre lo que este roadmap NO incluye:** no hay, en ninguna etapa, una fase de "automatizar el Learning Loop con Machine Learning" ni una fase de "agregar generación de lenguaje natural para las recomendaciones". Ambas exclusiones son consistentes con — y una extensión directa de — la misma resolución que v1.0 ya fijó en su propio roadmap respecto a SHAP/LIME y Auto-Commentary (v1.0, Parte XIX y Roadmap de Evolución). Este documento no reabre esa decisión.

---

## CIERRE

Volviendo a la pregunta que este documento debía responder: *si mañana un Wealth Manager llega con cualquier problema relacionado con un cliente, ¿cómo debe recorrer el sistema AFI para obtener información suficiente, detectar qué está ocurriendo, entender los riesgos, analizar escenarios, comparar alternativas y llegar a una decisión profesional?*

La respuesta, desarrollada a lo largo de las 21 secciones de este documento, se puede resumir así: **el sistema identifica primero la unidad de análisis y el objetivo a partir de la pregunta del WM — nunca al revés —, evalúa qué información tiene y clasifica lo que falta en Bloqueo, Advertencia o Sin Impacto Material sin ocultarlo nunca, activa solo los motores de v1.0 relevantes a esa pregunta específica, genera el espacio completo de alternativas antes de sugerir cuál parece superior, y se detiene siempre en el Nivel 3 — nunca ejecuta, nunca decide por el WM, y nunca colapsa seis dimensiones distintas en un único número.**

Donde la respuesta honesta era "todavía no sabemos", este documento no la inventó: la Parte 20 registra tres pendientes nuevos, específicos de la capa de orquestación, que se suman —sin duplicarlos— a los seis que v1.0 ya había dejado abiertos. Ningún pendiente de v1.0 se resolvió aquí por conveniencia narrativa, y ninguna decisión ya tomada en v1.0 (los 10 motores, las 15 decisiones D1-D15, la prohibición de LLM/SHAP/LIME) se modificó silenciosamente — donde este documento tocó un límite cercano a uno ya fijado, como el heatmap del Motor de Monitoreo frente al principio de "no Health Score" (Parte 2.4), la tensión se declaró explícitamente en vez de resolverse por omisión.

Este documento, junto con AFI Quantitative Methodology v1.0, es la base metodológica completa que alimentará la **AFI Expert System Functional Specification (ESFS)** y, posteriormente, su implementación en Claude Code.
