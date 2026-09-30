# AFI QUANTITATIVE METHODOLOGY v1.0

**Consolidación institucional — Volúmenes I, II, III y III‑B**
**Herramienta de síntesis:** Claude · **Tipo de trabajo:** síntesis metodológica y diseño institucional (no investigación nueva, no código definitivo, no arquitectura tecnológica completa)

---

## Cómo leer este documento

Este documento consolida cuatro fuentes previas (Volumen I: First Principles; Volumen II: Selección de Gestores; Volumen III: Arquitectura Cuantitativa; Volumen III‑B: Validación y Especificación Cuantitativa) en una única metodología institucional. Sigue tres reglas de tratamiento de fuentes:

1. **Las fuentes son material de trabajo, no verdad automática.** Donde el Volumen III‑B ya proponía una clasificación 🟢/🟡/🔵/🔴, esa clasificación se revisó contra los criterios de no‑sobreingeniería (valor para la decisión, robustez, calidad de datos, interpretabilidad, auditabilidad, implementabilidad, consistencia institucional) antes de aceptarse. En **6 casos** el resultado de esa revisión difiere de la propuesta original; cada uno está señalado explícitamente con 🔁 **Revisado** y su justificación.
2. **Las contradicciones se resuelven, no se ocultan.** Donde los volúmenes se contradicen entre sí, la sección correspondiente lo declara, explica la contradicción y propone una resolución — marcada como pendiente de aprobación institucional si AFI debe decidir formalmente.
3. **La incertidumbre se declara, no se rellena.** Donde ninguno de los cuatro volúmenes ofrece base suficiente para una decisión responsable, la Parte XXIII (Decisiones Pendientes) lo registra en vez de inventar una respuesta.

---

## 0. Resumen Ejecutivo

AFI Quantitative Methodology v1.0 responde una pregunta: **¿cómo debe AFI transformar datos de clientes, portafolios, fondos y gestores en información que permita a un Wealth Manager tomar mejores decisiones?**

La respuesta tiene una estructura fija que gobierna todo el documento:

```
DATOS → CÁLCULOS → MÉTRICAS → DIAGNÓSTICO → ESCENARIOS → ALTERNATIVAS → EVIDENCIA → DECISIÓN DEL EJECUTIVO
```

El sistema calcula, detecta, compara, simula, alerta, propone y documenta. **El sistema no decide.** El Wealth Manager decide, y esa separación es el principio organizador de toda la metodología — no una limitación técnica, sino una posición institucional deliberada consistente con el rol fiduciario descrito en el Volumen I.

**Qué contiene este documento:**

- **10 motores cuantitativos** (Performance, Riesgo, Diversificación, Construcción, Liquidez, Alternativos, Escenarios, Monitoreo, Benchmark, Cliente/Goal) con objetivo, inputs, modelos, outputs, dependencias y prioridad.
- Un **stack cuantitativo** que clasifica cada metodología en 🟢 CORE / 🟡 ADVANCED / 🔵 RESEARCH / 🔴 REJECTED, con la lógica detrás de cada clasificación — no solo la etiqueta.
- Una **Decision Library** de ~15 decisiones institucionales recurrentes, cada una con sus inputs, reglas y el punto exacto donde el sistema entrega la decisión al humano.
- Un **Data Dictionary conceptual**, reglas de calidad de datos, y un **Model Governance** framework.
- Una **matriz maestra** que consolida motor × modelo × fórmula × inputs × output × decisión × prioridad × validación × limitaciones × responsable.
- Una sección de **decisiones metodológicas pendientes**, sin rellenos artificiales.

**Qué NO contiene, por diseño explícito del mandato:** trading, derivados, un CRM, un stock picker, un algoritmo autónomo de inversión, o un LLM como componente necesario de ningún motor.

**El hallazgo más importante de la consolidación:** el Volumen III propone un núcleo de explicabilidad basado en SHAP/LIME y una hoja de ruta hacia "Auto Commentary" tipo LLM (Fase 4 de su roadmap). El Volumen III‑B, en cambio, clasifica explícitamente los "modelos opacos sin explicabilidad" como 🔴 REJECTED. El prompt fundacional de este trabajo prohíbe agregar LLM al motor. Esta metodología resuelve la contradicción a favor del Volumen III‑B y el mandato: la explicabilidad de AFI es **determinística, basada en reglas, auditable y reproducible** — no hay SHAP, no hay LIME, no hay generación de lenguaje natural como parte del cálculo. Ver Parte XIX.

---

## PARTE I — PRINCIPIOS CUANTITATIVOS AFI

Estos son los principios extraídos y consolidados de los cuatro volúmenes que gobiernan todo diseño posterior. No son aspiracionales: cada uno tiene una implicancia operativa concreta para modelos, software y el Wealth Manager.

### Principio 1 — Centralidad de los objetivos del cliente sobre los benchmarks

**Qué significa.** Ninguna métrica cuantitativa tiene valor por sí misma; tiene valor en la medida en que informa si el cliente está más o menos cerca de sus metas vitales (Volumen I, Principio 1).

**Por qué existe.** La evidencia de CFA Institute y goal-based investing muestra que maximizar retorno aislado o minimizar riesgo absoluto, sin referencia a metas, produce decisiones subóptimas — el objetivo normativo es la utilidad intertemporal del cliente, no el índice.

**Qué implica para los modelos.** Todo motor debe poder conectar su output con el IPS del cliente, no solo con un benchmark de mercado. El Motor de Cliente/Goal (Parte II.10) no es opcional: es el punto de referencia de todos los demás.

**Qué implica para el software.** Cada `MotorResultado` debe llevar un campo de trazabilidad hacia el `IPS.id_ips` correspondiente, no solo hacia el `Portafolio.id_portafolio`.

**Qué implica para el Wealth Manager.** Una alerta de riesgo o de underperformance solo es accionable si se interpreta contra el IPS del cliente específico — un VaR "alto" para un perfil agresivo puede ser normal; el mismo VaR para un perfil conservador es una desviación.

---

### Principio 2 — Separación estricta entre cálculo y decisión (Human-in-the-Loop)

**Qué significa.** El sistema calcula, detecta, compara, simula, alerta, propone y documenta. El sistema nunca decide, ejecuta ni comunica autónomamente al cliente.

**Por qué existe.** Es un mandato explícito del marco AFI (Parte XX del prompt fundacional) y consistente con el Volumen I, Principio 9: el asesor es arquitecto de decisiones, no un ejecutor automatizado. Ciertas decisiones —priorización entre metas en conflicto, gestión de crisis del cliente, gobernanza familiar— requieren juicio humano que ningún modelo captura.

**Qué implica para los modelos.** Ningún motor puede producir una "recomendación final"; produce evidencia, alternativas y una recomendación *sugerida* con nivel de convicción, siempre con opción de override.

**Qué implica para el software.** Cada decisión de la Decision Library (Parte XVIII) debe tener un campo `Human_Override` obligatorio, y cada override debe registrar su justificación en el log de auditoría (Parte XXI).

**Qué implica para el Wealth Manager.** El WM conserva —y no puede delegar— la responsabilidad última de toda recomendación comunicada al cliente.

---

### Principio 3 — Explicabilidad determinística, no basada en LLM

**Qué significa.** La explicación de cualquier resultado cuantitativo debe ser reconstruible mediante reglas fijas y auditables: "el portafolio presenta una desviación de X respecto de la SAA objetivo; la banda institucional es Y; el sistema clasifica el evento como revisión de rebalanceo" — no una narrativa generada por un modelo de lenguaje.

**Por qué existe.** Mandato explícito del prompt fundacional (Parte XIX, Regla Final). Es también la posición correcta tras revisar la contradicción entre Volumen III (que propone XAI vía SHAP/LIME y roadmap hacia Auto-Commentary) y Volumen III‑B (que clasifica modelos opacos sin explicabilidad como 🔴 REJECTED). Un output fiduciario debe poder reconstruirse sin depender de la estabilidad de un modelo probabilístico de lenguaje.

**Qué implica para los modelos.** Ningún motor puede usar SHAP, LIME, ni ningún mecanismo de atribución basado en aproximación de caja negra como fuente única de explicación. La atribución de riesgo y performance (Brinson-Fachler, factor decomposition) es aceptable porque es determinística y reproducible; SHAP/LIME sobre modelos no lineales no lo es en el mismo grado y además introduce una dependencia innecesaria.

**Qué implica para el software.** El motor de narrativas (si existe) es una capa de plantillas parametrizadas sobre resultados ya calculados —nunca un generador de texto libre—. Ver Parte XIX para el detalle de esta resolución.

**Qué implica para el Wealth Manager.** Toda cifra que ve el WM puede rastrearse hasta la regla exacta que la produjo, sin caja negra intermedia.

---

### Principio 4 — No sobreingeniería: complejidad solo si agrega valor neto

**Qué significa.** Un modelo no se selecciona por ser más avanzado matemáticamente; se selecciona porque mejora la decisión de forma que la complejidad adicional justifica el costo de interpretabilidad, auditabilidad y mantenimiento que introduce.

**Por qué existe.** Es el criterio explícito del prompt fundacional y también un principio del Volumen I (Principio 15: "simplicidad inteligible sobre complejidad innecesaria"). Es el criterio que se aplicó para revisar (y en 6 casos, corregir) las clasificaciones CORE/ADVANCED heredadas del Volumen III‑B.

**Qué implica para los modelos.** Todo modelo candidato a CORE debe responder siete preguntas antes de ser aceptado: ¿agrega valor a la decisión? ¿es robusto? ¿los datos disponibles lo soportan? ¿es interpretable para el WM? ¿es auditable? ¿es implementable con los recursos de AFI? ¿es consistente con el resto del stack institucional? Ver Parte III.0 para el detalle de este filtro aplicado.

**Qué implica para el software.** Un modelo puede degradarse de CORE a RESEARCH si su desempeño en producción no confirma su promesa teórica (Model Governance, Parte XIV).

**Qué implica para el Wealth Manager.** La matemática puede ser avanzada; la interpretación que llega al WM debe ser simple.

---

### Principio 5 — La matemática puede ser avanzada; la interpretación debe ser simple

**Qué significa.** Es aceptable que el cálculo interno de un modelo (p. ej. Black-Litterman, factor risk) sea sofisticado, siempre que su salida se traduzca a un lenguaje de decisión que el WM entienda sin formación cuantitativa avanzada.

**Por qué existe.** Mandato explícito del prompt fundacional; también reflejado en el Volumen III-B (Parte XVIII: "la matemática se oculta en gran parte" del dashboard del WM).

**Qué implica para los modelos.** Todo modelo ADVANCED o superior necesita una capa de traducción documentada (ver plantilla en Parte XVIII) antes de exponerse al WM.

**Qué implica para el software.** Separación de capas: motor de cálculo (interno, técnico) vs. capa de presentación (WM-facing, simplificada).

**Qué implica para el Wealth Manager.** Nunca necesita resolver una fórmula para usar un resultado del sistema; sí puede, si quiere, acceder a la fórmula completa en una vista técnica.

---

### Principio 6 — Diversificación económica, no nominal

**Qué significa.** El objetivo no es contar cuántos fondos tiene un portafolio, sino cuántas fuentes de riesgo genuinamente distintas lo componen.

**Por qué existe.** Explícito en el Volumen I (Principio 4) y desarrollado con detalle en el Motor de Diversificación (Volumen III, 2.3) y la Parte VI de este documento: 20 fondos concentrados en el mismo factor (p. ej. large-cap US) son diversificación aparente, no real.

**Qué implica para los modelos.** HHI y correlación nominal son insuficientes solos; deben combinarse con contribución al riesgo y exposición a factores.

**Qué implica para el software.** El Motor de Diversificación necesita acceso a un modelo de factores básico (equity, tasas, crédito, FX), no solo a series de retornos.

**Qué implica para el Wealth Manager.** Una alerta de concentración debe decir *en qué factor* está la concentración, no solo que existe.

---

### Principio 7 — Ningún benchmark se usa sin verificar elegibilidad primero

**Qué significa.** Antes de comparar un portafolio contra cualquier referencia (índice, AFP, peer group), el sistema verifica ocho dimensiones de comparabilidad. Si el benchmark no es elegible, el sistema no genera ranking — solo diferencias cualitativas.

**Por qué existe.** Mandato explícito del prompt fundacional (Parte XII) y del Volumen III-B (Parte XI): comparar un cliente con exposición significativa a alternativos contra una AFP con regulación distinta no es informativo, es engañoso.

**Qué implica para los modelos.** El Motor de Benchmark es un *gate*, no solo un cálculo — puede bloquear un output de otro motor.

**Qué implica para el software.** `Benchmark.eligibility_status` es un campo obligatorio que otros motores deben consultar antes de mostrar una comparación.

**Qué implica para el Wealth Manager.** Si el sistema no muestra un ranking, es una señal deliberada, no un error o dato faltante.

---

### Principio 8 — Ante evidencia insuficiente, el sistema lo declara — nunca inventa

**Qué significa.** Cuando los datos no permiten estimar una métrica con confianza razonable, la respuesta correcta del sistema es "información insuficiente para producir una estimación confiable", no un número calculado sobre datos pobres presentado con la misma confianza que uno robusto.

**Por qué existe.** Regla de oro explícita del Volumen III-B, Parte XIV, y mandato del prompt fundacional (Parte XIV): "nunca inventar datos".

**Qué implica para los modelos.** Todo modelo necesita un umbral mínimo de datos documentado (tamaño de muestra, frecuencia, completitud) bajo el cual se bloquea, no se degrada silenciosamente.

**Qué implica para el software.** Un estado explícito `Model_Blocked: insufficient_data` distinto de un resultado válido, con la razón específica visible.

**Qué implica para el Wealth Manager.** Nunca debe interpretar el silencio del sistema como "todo está bien" — el sistema declara activamente cuándo no puede opinar.

---

### Principio 9 — Toda recomendación debe poder reconstruirse (auditabilidad total)

**Qué significa.** Dado un output cualquiera del sistema, debe ser posible reconstruir qué datos se usaron, qué modelo se aplicó, con qué parámetros, qué regla se activó y qué decisión tomó el WM al respecto — en cualquier momento futuro.

**Por qué existe.** Mandato explícito del prompt fundacional (Parte XXI) y consistente con el deber fiduciario del Volumen I (Principio 13).

**Qué implica para los modelos.** Todo modelo debe versionar sus parámetros y registrar su fecha de última validación.

**Qué implica para el software.** Un log de auditoría es tan importante como el motor de cálculo mismo — no es una función accesoria, es un requisito de primera clase (ver Parte XXI).

**Qué implica para el Wealth Manager.** Puede —y en un contexto regulatorio, debe poder— justificar cualquier recomendación pasada con los datos exactos que la originaron.

---

### Principio 10 — Convicción ex ante, no solo ex post (aplicado a gestores y a modelos)

**Qué significa.** La confianza en un gestor —o en un modelo cuantitativo— se construye principalmente evaluando si el proceso que generó resultados pasados seguirá siendo válido, no solo mirando el track record.

**Por qué existe.** Es el principio rector completo del Volumen II: el desempeño histórico es necesario pero no suficiente. Este documento extiende el mismo principio a los propios modelos cuantitativos de AFI: un modelo no se valida solo por su backtest, sino por su robustez estructural (Parte XIV, Model Governance).

**Qué implica para los modelos.** Ningún modelo CORE se acepta solo por evidencia de papers; necesita, además, robustez fuera de muestra y estabilidad de parámetros.

**Qué implica para el software.** El due diligence de gestores (Motor de Diligencia, ligado a Volumen II) y el model governance de AFI comparten estructura: ambos exigen entender el "por qué" antes de confiar en el "qué pasó".

**Qué implica para el Wealth Manager.** Debe desconfiar tanto de un fondo que solo muestra "top quartile últimos 3 años" como de un modelo cuantitativo que solo muestra un buen backtest.

---

## PARTE II — ARQUITECTURA CUANTITATIVA AFI

Diez motores especializados, orquestados sobre una capa de datos institucional común. Ningún motor opera de forma aislada — todos dependen, en distinto grado, del Motor de Cliente/Goal como punto de referencia (Principio 1) y del Motor de Benchmark como *gate* de comparabilidad (Principio 7).

```
Cliente/WM/Comité
        ↓ ↑
┌───────────────────────────────────────────────────┐
│  MOTOR      MOTOR       MOTOR         MOTOR        │
│  Performance Riesgo     Diversificación Construcción│
│                                                     │
│  MOTOR      MOTOR       MOTOR         MOTOR        │
│  Liquidez   Alternativos Escenarios   Monitoreo    │
│                                                     │
│  MOTOR                  MOTOR                      │
│  Benchmark               Cliente/Goal               │
└───────────────────────────────────────────────────┘
        ↓ ↑
Capa de datos institucional (NAV, flujos, benchmarks, factores, FX)
```

### II.1 — Motor de Performance

| Campo | Contenido |
|---|---|
| **Objetivo** | Evaluación robusta, multi-nivel y explicable de performance por cliente, asset class, gestor y vehículo, alineada a GIPS. |
| **Problemas que resuelve** | Falta de medición homogénea de resultados entre clientes, vehículos y gestores; imposibilidad de separar habilidad de gestión de decisiones de flujo del cliente. |
| **Decisiones que soporta** | ¿Cumplió el portafolio los objetivos de retorno ajustado por riesgo del IPS? ¿Qué parte del resultado viene de asignación, selección de gestor o timing? ¿Debe revisarse la combinación de vehículos/gestores? |
| **Inputs** | Series diarias/mensuales de NAV y flujos (cash in/out, fees); series de benchmarks (política, compuesto, peer group); metadatos de jerarquía de agregación. |
| **Modelos** | TWR geométricamente encadenado (CORE); MWR/IRR (XIRR) (CORE); atribución Brinson-Fachler (ADVANCED); atribución por factores (ADVANCED). Detalle completo en Parte IV. |
| **Outputs** | Cuadros multi-periodo (YTD, 1-3-5-10 años, desde inicio); atribución jerárquica; hit ratio vs benchmark. |
| **Dependencias** | Motor de Benchmark (definición de referencias elegibles); Motor de Construcción (separar asignación de selección). |
| **Limitaciones** | Requiere flujos correctamente fechados; fondos de valorización trimestral (privados) necesitan tratamiento distinto (Parte IV). |
| **Frecuencia** | Cálculo diario/mensual (posiciones y TWR); consolidación mensual y trimestral para reporting. |
| **Prioridad** | 🔴 Crítica — base de todo reporting y gobierno; MVP obligatorio. |

### II.2 — Motor de Riesgo

| Campo | Contenido |
|---|---|
| **Objetivo** | Medir y descomponer riesgo de portafolios multi-asset (incluyendo alternativos) de forma granular y accionable. |
| **Problemas que resuelve** | Riesgo evaluado de forma agregada sin visibilidad de qué lo genera; incapacidad de anticipar concentraciones de riesgo antes de que se materialicen en pérdida. |
| **Decisiones que soporta** | ¿El riesgo actual es coherente con el IPS? ¿Qué factores o gestores son los principales drivers de riesgo? ¿Debe ajustarse el presupuesto de riesgo? |
| **Inputs** | Posiciones detalladas por instrumento; curvas de mercado (tasas, spreads, FX, volatilidad implícita); matriz de covarianzas con shrinkage; parámetros de riesgo para alternativos. |
| **Modelos** | Volatilidad histórica (CORE); downside deviation (CORE); máximo drawdown (CORE); tracking error (CORE); beta (CORE); VaR y ES históricos (CORE); VaR/ES paramétrico y EWMA (ADVANCED); factor risk básico (ADVANCED); GARCH (🔁 revisado a RESEARCH — ver Parte V). Detalle completo en Parte V. |
| **Outputs** | Tableros de riesgo a nivel portafolio, cliente y book of business; mapas de contribución a riesgo por dimensión; panel de riesgo de cola. |
| **Dependencias** | Motor de Escenarios (definición de shocks); Motor de Liquidez (riesgo de liquidez). |
| **Limitaciones** | Modelos para alternativos requieren ajuste por smoothing y baja frecuencia de valuación; no confundir NAV privado con precio de mercado. |
| **Frecuencia** | Cálculo diario en batch; capacidad on-demand para análisis ad-hoc del Comité. |
| **Prioridad** | 🔴 Crítica — núcleo del deber fiduciario; MVP obligatorio. |

### II.3 — Motor de Diversificación

| Campo | Contenido |
|---|---|
| **Objetivo** | Cuantificar diversificación real (no aparente) en correlaciones, factores y concentración. |
| **Problemas que resuelve** | Portafolios que parecen diversificados por número de fondos pero concentran riesgo en el mismo factor. |
| **Decisiones que soporta** | ¿El portafolio está verdaderamente diversificado? ¿Dónde hay concentraciones ocultas? ¿Qué cambio marginal mejora más la diversificación? |
| **Inputs** | Matrices de correlación y covarianza (forward-looking CMAs); pesos actuales y objetivo por asset class/factor/estilo/liquidez. |
| **Modelos** | Correlation matrix y rolling correlation (CORE); HHI (CORE); risk contribution y marginal contribution (CORE); shrinkage correlation (ADVANCED); cluster analysis y effective number of bets (ADVANCED); HRP como constructor principal (🔁 revisado — mantenido en RESEARCH, ver Parte VI). Detalle completo en Parte VI. |
| **Outputs** | Índices de diversificación por portafolio vs. modelo; recomendaciones de cambios marginales de peso. |
| **Dependencias** | Motor de Riesgo (matriz de covarianzas compartida); Motor de Construcción (para simular "what-if"). |
| **Limitaciones** | Correlaciones históricas son inestables; requiere shrinkage para uso en optimización. |
| **Frecuencia** | Mensual/trimestral, alineado a revisiones de portafolio. |
| **Prioridad** | 🟠 Alta — mejora resiliencia pero no es bloqueante para MVP mínimo. |

### II.4 — Motor de Construcción de Portafolios

| Campo | Contenido |
|---|---|
| **Objetivo** | Producir propuestas de portafolio consistentes con IPS, filosofía institucional y restricciones prácticas de implementación. |
| **Problemas que resuelve** | Construcción ad-hoc sin trazabilidad hacia objetivos, restricciones o house view institucional. |
| **Decisiones que soporta** | ¿Qué combinación de asset classes y vehículos proponer dado un IPS? ¿Qué tilts tácticos están permitidos? ¿Qué desviaciones del modelo de referencia se justifican? |
| **Inputs** | IPS del cliente; Capital Market Assumptions (retornos esperados, volatilidad, correlaciones); inventario de productos con costos, liquidez, tracking error, capacidad. |
| **Modelos** | Mean-Variance robusto con shrinkage y constraints (CORE); goal-based Monte Carlo (CORE); Black-Litterman centralizado (ADVANCED); Risk Parity/ERC (ADVANCED); HRP (RESEARCH). Detalle completo en Parte VII y VIII. |
| **Outputs** | Propuesta de portafolio objetivo (weights, vehículos, buckets de liquidez); métricas esperadas; sensibilidades. |
| **Dependencias** | Motor de Riesgo, Motor de Diversificación, Motor de Liquidez, Motor de Benchmark. |
| **Limitaciones** | Sensible a errores de estimación de retornos esperados; requiere constraints fuertes para evitar concentración espuria. |
| **Frecuencia** | Trimestral/anual para revisión formal; on-demand para simulación. |
| **Prioridad** | 🔴 Crítica — decisión central del ciclo de vida del cliente; MVP obligatorio. |

### II.5 — Motor de Liquidez

| Campo | Contenido |
|---|---|
| **Objetivo** | Asegurar que el patrimonio puede cumplir sus obligaciones de liquidez bajo escenarios adversos sin comprometer el objetivo estratégico. |
| **Problemas que resuelve** | Ventas forzadas de activos ilíquidos o mal valorados por falta de planificación de flujos. |
| **Decisiones que soporta** | ¿Cuál debe ser el tamaño del colchón de liquidez? ¿Cómo componer los buckets (daily/monthly/illiquid)? ¿A qué ritmo comprometer capital en alternativos? |
| **Inputs** | Calendario de flujos esperados (retiros, impuestos, capital calls, distribuciones, gastos); estructura de liquidez de cada vehículo; escenarios de estrés. |
| **Modelos** | Liquidity Coverage Ratio por bucket (CORE); Liquidity Ladder / cash flow matching (CORE); stress liquidity (mercado + flujos simultáneos) (ADVANCED). Detalle en Parte IX. |
| **Outputs** | Mapas de liquidez por horizonte; alertas de déficit potencial; recomendaciones de reasignación líquido↔ilíquido. |
| **Dependencias** | Motor de Alternativos (curvas de capital calls/distribuciones); Motor de Escenarios (stress conjunto). |
| **Limitaciones** | Depende de calidad de estimación de flujos futuros del cliente, que suele ser incierta. |
| **Frecuencia** | Trimestral, y ante eventos de cliente o mercado. |
| **Prioridad** | 🟠 Alta — crítico en crisis, no bloqueante para el MVP más mínimo. |

### II.6 — Motor de Alternativos

| Campo | Contenido |
|---|---|
| **Objetivo** | Gestionar cuantitativamente asignación, diversificación y pacing en PE, private credit, real estate, infraestructura, VC y hedge funds. |
| **Problemas que resuelve** | Tratamiento de activos privados como si fueran líquidos; sobrecompromiso de capital sin visibilidad de cash flow futuro. |
| **Decisiones que soporta** | ¿Cuál es el tamaño del programa de alternativos por cliente? ¿Qué ritmo de commitments es sostenible? ¿Cómo afecta esto la liquidez y el riesgo total? |
| **Inputs** | Curvas de cash flow históricos por estrategia/vintage; modelos de J-curve; NAV reportado; supuestos de retorno y beta por estrategia. |
| **Modelos** | TVPI, DPI, RVPI, IRR (CORE); PME, Direct Alpha (ADVANCED); modelos de pacing y simulación de NAV futuro (ADVANCED). Detalle en Parte X. |
| **Outputs** | Perfil de cash flow proyectado; contribución a retorno esperado del portafolio total; exposición factorial aproximada. |
| **Dependencias** | Motor de Liquidez (integración de cash flows); Motor de Riesgo (traducción a exposición factorial). |
| **Limitaciones** | NAV privado no es equivalente a precio de mercado; valuaciones trimestrales introducen smoothing artificial. |
| **Frecuencia** | Trimestral (alineado a reporting de NAV de los fondos). |
| **Prioridad** | 🟡 Media para MVP — alta importancia estratégica de posicionamiento, pero puede lanzarse en versión simple. |

### II.7 — Motor de Escenarios

| Campo | Contenido |
|---|---|
| **Objetivo** | Permitir evaluar "qué pasaría si" bajo shocks de mercado, macro y eventos extremos. |
| **Problemas que resuelve** | Decisiones de riesgo tomadas sin visibilidad de resiliencia bajo condiciones adversas plausibles. |
| **Decisiones que soporta** | ¿Es necesario un rebalanceo extraordinario? ¿Debe cubrirse una exposición específica? ¿Debe ajustarse la SAA? |
| **Inputs** | Librería de escenarios históricos e hipotéticos; mapeo a factores de riesgo. |
| **Modelos** | Historical Simulation (CORE); Hypothetical Stress (CORE); Reverse Stress Testing (ADVANCED); Monte Carlo/bootstrap (CORE para planificación de metas, ver Parte XI); Regime Switching (RESEARCH). Detalle en Parte XI. |
| **Outputs** | Impacto proyectado en retorno, riesgo, liquidez y concentración bajo cada escenario. |
| **Dependencias** | Motor de Riesgo, Motor de Liquidez, Motor de Construcción. |
| **Limitaciones** | Escenarios históricos no garantizan representar la próxima crisis; escenarios hipotéticos dependen del juicio del Comité. |
| **Frecuencia** | Trimestral, y ante señales de régimen cambiante. |
| **Prioridad** | 🟠 Alta — crítico en momentos de estrés, versión limitada aceptable en MVP. |

### II.8 — Motor de Monitoreo

| Campo | Contenido |
|---|---|
| **Objetivo** | Proveer una vista consolidada ("book of business") con alertas de riesgo, performance, liquidez y cumplimiento de IPS. |
| **Problemas que resuelve** | Asesor sin visibilidad priorizada de en qué cuentas actuar hoy entre docenas o cientos de clientes. |
| **Decisiones que soporta** | ¿En qué cuentas debe actuar el asesor hoy? ¿Qué excepciones escalar al Comité? |
| **Inputs** | Resultados consolidados de todos los demás motores; umbrales y triggers configurados. |
| **Modelos** | Reglas de triggers cuantitativos y cualitativos (CORE); no introduce modelos matemáticos propios — orquesta los de otros motores. |
| **Outputs** | Lista priorizada de cuentas; heatmap de desviaciones; panel de watchlist. |
| **Dependencias** | Todos los demás motores (es un motor de orquestación y agregación). |
| **Limitaciones** | Su calidad depende enteramente de la calidad de los triggers definidos en cada motor subyacente. |
| **Frecuencia** | Diaria/semanal. |
| **Prioridad** | 🔴 Crítica una vez existen 2+ motores fuente — no tiene sentido en aislamiento pero escala mal sin él. |

### II.9 — Motor de Benchmark

| Campo | Contenido |
|---|---|
| **Objetivo** | Definir y mantener benchmarks de política, y actuar como *gate* de elegibilidad antes de cualquier comparación. |
| **Problemas que resuelve** | Comparaciones engañosas contra referencias no comparables (p. ej. AFP vs. cliente con exposición relevante a alternativos). |
| **Decisiones que soporta** | ¿Es elegible este benchmark para esta comparación? ¿Qué tipo de benchmark corresponde (market/policy/custom/peer)? |
| **Inputs** | Definición de universo, riesgo, moneda, liquidez, horizonte, costos y restricciones del portafolio y del benchmark candidato. |
| **Modelos** | AFI Benchmark Eligibility Framework (CORE) — verificación de 8 dimensiones antes de generar cualquier ranking. Detalle en Parte XII. |
| **Outputs** | Estado de elegibilidad (elegible/no elegible/parcial); benchmark asignado por cliente/estrategia. |
| **Dependencias** | Consumido por Motor de Performance y Motor de Riesgo (tracking error, IR). |
| **Limitaciones** | Un benchmark "razonablemente cercano" no siempre existe; en ese caso el sistema debe decirlo, no forzar una comparación. |
| **Frecuencia** | Revisión anual de la definición; consulta on-demand por otros motores. |
| **Prioridad** | 🔴 Crítica — gate necesario para que Performance y Riesgo no produzcan comparaciones engañosas; MVP obligatorio. |

### II.10 — Motor de Cliente / Goal Intelligence

| Campo | Contenido |
|---|---|
| **Objetivo** | Consolidar objetivos, restricciones y probabilidad de éxito del cliente como referencia central de todos los demás motores. |
| **Problemas que resuelve** | Motores operando con referencia solo a benchmarks de mercado, perdiendo de vista el objetivo real del cliente (Principio 1). |
| **Decisiones que soporta** | ¿Cuál es la probabilidad de alcanzar la meta X bajo la estrategia actual? ¿Debe reconsiderarse el IPS? |
| **Inputs** | IPS (objetivos, horizonte, restricciones); life balance sheet; resultados de Monte Carlo goal-based. |
| **Modelos** | Monte Carlo / bootstrap sobre probabilidad de meta (CORE, comparte metodología con Parte XI); no introduce modelos de mercado propios. |
| **Outputs** | Probabilidad de éxito por meta; dashboard cliente simplificado. |
| **Dependencias** | Motor de Construcción y Motor de Escenarios (inputs de retorno/riesgo proyectado). |
| **Limitaciones** | La calidad de la salida depende enteramente de qué tan bien se definió el IPS inicial. |
| **Frecuencia** | Actualización trimestral; revisión completa ante eventos de vida del cliente. |
| **Prioridad** | 🟠 Alta — consistente con Principio 1, pero requiere que exista primero un IPS estructurado; secuencialmente posterior a Performance/Riesgo/Construcción en el roadmap. |

---

## PARTE III — STACK CUANTITATIVO AFI v1.0

### III.0 — El filtro de no-sobreingeniería aplicado

El Volumen III-B ya proponía clasificaciones 🟢/🟡/🔵/🔴 para la mayoría de los modelos. Por instrucción explícita, esas clasificaciones no se heredaron automáticamente: cada una se sometió a las siete preguntas del Principio 4 antes de confirmarse. En **seis casos** el resultado difirió del original. Se documentan aquí antes de la matriz, porque el *porqué* de un cambio de clasificación importa tanto como la clasificación misma.

**🔁 Revisión 1 — Núcleo XAI (SHAP/LIME), Volumen III → de "propuesto como núcleo" a 🔴 REJECTED.**
Justificación: viola directamente el Principio 3 (explicabilidad determinística) y la Regla Final del mandato ("NO agregar LLM"). SHAP/LIME son técnicas de aproximación sobre modelos no necesariamente interpretables por sí mismos; introducen una capa de caja negra exactamente donde el deber fiduciario exige lo contrario. Se reemplaza por explicación basada en reglas y plantillas (Parte XIX).

**🔁 Revisión 2 — "Auto Commentary" tipo LLM, Volumen III (Fase 4 del roadmap) → eliminado del roadmap.**
Justificación: mismo motivo que la Revisión 1. La generación de narrativa libre no es auditable de forma determinística. El roadmap de este documento (Parte XXII) no incluye esta fase.

**🔁 Revisión 3 — GARCH → confirmado en 🔵 RESEARCH, pero con nota de bloqueo explícito.**
El Volumen III-B ya lo clasificaba RESEARCH; se confirma, pero se agrega una razón operativa que el volumen original no hacía explícita: GARCH exige series de alta frecuencia y estimación estadística sofisticada que la mayoría de los vehículos de AFI (fondos con NAV mensual/trimestral) simplemente no tienen. No es solo "poco interpretable" — es *impracticable con los datos disponibles* para la mayoría del universo de inversión de AFI. Esto lo hace un candidato aún más débil de lo que sugería el volumen original.

**🔁 Revisión 4 — HRP (Hierarchical Risk Parity) → confirmado en 🔵 RESEARCH, con matiz.**
El Volumen III-B lo mantenía en RESEARCH como "constructor principal" pero lo mencionaba como herramienta de diagnóstico ya utilizable en el Motor de Diversificación. Tras revisión, se separa explícitamente: **HRP como método de construcción de portafolios permanece en RESEARCH** (evidencia de mejora out-of-sample existe pero no está probada en el contexto específico de AFI); **HRP como técnica de clustering para diagnóstico de diversificación se promueve a 🟡 ADVANCED**, porque ahí el riesgo de un resultado mal interpretado es mucho menor — es una lente de análisis, no una decisión de asignación de capital.

**🔁 Revisión 5 — Black-Litterman → confirmado en 🟡 ADVANCED, pero con una condición de entrada más estricta que la propuesta original.**
El Volumen III-B lo marcaba ADVANCED con "🟢 CORE futuro". Tras revisión, se elimina esa proyección automática a CORE: BL solo debe promoverse a CORE si AFI demuestra, con datos propios, que su Comité de Inversiones puede sostener el proceso de generación de views documentado en la Parte VIII (evidencia → view → convicción → BL → portafolio) de forma disciplinada y no ad-hoc. Sin ese proceso institucionalizado, BL con views mal fundamentadas es peor que MVO simple — la sofisticación matemática amplifica un input de mala calidad en vez de corregirlo.

**🔁 Revisión 6 — Bootstrap / Block Bootstrap para Monte Carlo → promovido de mención lateral (Volumen III-B lo trataba como variante) a componente CORE explícito, junto con Monte Carlo tradicional.**
Justificación: el Volumen III-B ya recomendaba block bootstrap para preservar dependencias de corto plazo, pero lo dejaba como nota secundaria bajo "Monte Carlo". Al aplicar el criterio de robustez del Principio 4, el bootstrap por bloques es *más* robusto que el Monte Carlo paramétrico simple para el tipo de series con las que trabaja AFI (autocorrelación y clustering de volatilidad reales en retornos mensuales/trimestrales) y no añade complejidad de implementación significativa. Se eleva su estatus a la par de Monte Carlo tradicional dentro de CORE, no como alternativa secundaria.

Todas las demás clasificaciones del Volumen III-B se revisaron contra el mismo filtro y se confirmaron sin cambios; se listan en la matriz que sigue sin marca 🔁.

### III.1 — Matriz maestra de clasificación

| Motor | Problema | Modelo | Input | Output | Decisión que soporta | Prioridad | Limitaciones |
|---|---|---|---|---|---|---|---|
| Performance | Medir desempeño del gestor | 🟢 TWR geométrico | NAV, flujos | Retorno acumulado/anualizado | Evaluar habilidad de gestión | CORE | Requiere NAV y flujos fiables |
| Performance | Medir retorno del cliente | 🟢 MWR/IRR (XIRR) | Flujos, valor inicial/final | Retorno personal | Comunicar "tu resultado" al cliente | CORE | Sensible a timing de flujos |
| Performance | Atribuir exceso de retorno | 🟡 Brinson-Fachler | Pesos, retornos por asset class vs benchmark | Contribución por asignación/selección | ¿De dónde vino el resultado? | ADVANCED | Requiere benchmark elegible (Motor IX) |
| Performance | Atribuir por factores | 🟡 Factor attribution | Retornos, exposiciones factoriales | Contribución por factor | Verificar consistencia con proceso declarado del gestor | ADVANCED | Requiere modelo de factores calibrado |
| Riesgo | Riesgo total | 🟢 Volatilidad histórica | Retornos | σ anualizada | ¿Riesgo coherente con IPS? | CORE | Ventana de 3-5 años ideal |
| Riesgo | Riesgo downside | 🟢 Downside deviation | Retornos, MAR | Semivarianza | Comunicar riesgo de pérdida al cliente | CORE | Requiere definición consistente de MAR |
| Riesgo | Severidad de pérdida | 🟢 Maximum drawdown | Serie NAV/TWR | % pérdida peak-to-trough | Calibrar tolerancia real del cliente | CORE | No distingue causa de mercado vs. idiosincrática |
| Riesgo | Riesgo activo | 🟢 Tracking Error | Retornos vs. benchmark | Desviación estándar del exceso | Clasificar intensidad de gestión activa | CORE | Requiere benchmark elegible |
| Riesgo | Riesgo sistemático | 🟢 Beta | Retornos vs. benchmark | Sensibilidad al mercado | Stress testing, construcción multi-gestor | CORE | Beta variable en el tiempo |
| Riesgo | Pérdida esperada extrema | 🟢 VaR histórico | Retornos | Pérdida al percentil de confianza | Límites de riesgo por perfil | CORE | No captura magnitud más allá del percentil |
| Riesgo | Riesgo de cola | 🟢 Expected Shortfall histórico | Retornos | Pérdida promedio condicional | Complemento a VaR para cola | CORE | Sensible a tamaño de muestra |
| Riesgo | Riesgo con mayor sensibilidad reciente | 🟡 EWMA | Retornos | σ ponderada exponencial | Alertas más sensibles a cambios recientes | ADVANCED | Requiere calibrar factor de decaimiento |
| Riesgo | Riesgo por fuente sistemática | 🟡 Factor risk básico | Retornos, índices | Exposición a equity/tasas/crédito/FX | Evitar concentraciones factoriales ocultas | ADVANCED | Calibración más compleja que métricas CORE |
| Riesgo | Clustering de volatilidad | 🔵 GARCH | Retornos alta frecuencia | Volatilidad condicional | — (no recomendado para uso rutinario) | RESEARCH 🔁 | Impracticable con NAV mensual/trimestral (ver III.0) |
| Diversificación | Correlación entre activos | 🟢 Correlation matrix + rolling | Retornos | Matriz de correlación | Detectar diversificación aparente | CORE | Correlaciones inestables en el tiempo |
| Diversificación | Concentración | 🟢 HHI | Pesos económicos/de riesgo/factor | Índice 0-1 | Medir concentración por dimensión | CORE | Sensible a cómo se definen los "buckets" |
| Diversificación | Contribución al riesgo total | 🟢 Risk contribution / marginal | Pesos, covarianzas | % de riesgo por activo | Detectar activos que concentran riesgo pese a bajo peso | CORE | Requiere matriz de covarianzas estable |
| Diversificación | Estabilidad de correlación | 🟡 Shrinkage (Ledoit-Wolf) | Retornos históricos | Matriz de covarianzas ajustada | Insumo más estable para optimización | ADVANCED | Requiere calibrar intensidad de shrinkage |
| Diversificación | Agrupar activos por comportamiento | 🟡 Cluster analysis / HRP diagnóstico | Matriz de correlación | Dendrograma / clusters | Visualizar concentraciones ocultas | ADVANCED 🔁 | Promovido desde RESEARCH — ver III.0 Revisión 4 |
| Diversificación | Construir portafolio jerárquico | 🔵 HRP como constructor | Covarianzas | Pesos óptimos | — (no recomendado como motor principal aún) | RESEARCH | Promete mejor diversificación out-of-sample, sin prueba suficiente en contexto AFI |
| Construcción | Portafolio óptimo con restricciones | 🟢 MVO robusto (shrinkage + constraints) | CMAs, covarianzas | Pesos óptimos | Propuesta de portafolio objetivo | CORE | Sensible a errores de estimación de retornos esperados |
| Construcción | Probabilidad de alcanzar metas | 🟢 Goal-based Monte Carlo | Retornos, cashflows, horizonte | Probabilidad de éxito | ¿La estrategia actual alcanza la meta? | CORE | Depende de calidad de supuestos de retorno |
| Construcción | Incorporar house views | 🟡 Black-Litterman | Índices, Σ, views del CIO | Expected returns posteriores | Ajustar portafolio con convicción institucional documentada | ADVANCED 🔁 | Condición de entrada más estricta — ver III.0 Revisión 5 |
| Construcción | Portafolio balanceado por riesgo | 🟡 Risk Parity / ERC | Volatilidades por asset class | Pesos con contribución de riesgo igualada | Alternativa defensiva de referencia | ADVANCED | Sensible a estimación de volatilidad |
| Construcción | Optimización bayesiana general | 🔵 Bayesian Optimization | — | — | — (no recomendado, poco interpretable) | RESEARCH | Complejidad no justificada para WM estándar |
| Construcción | Optimización no lineal extrema | 🔴 Constraints complejos no interpretables | — | — | — | REJECTED | Soluciones ininterpretables para el cliente |
| Liquidez | Cobertura de obligaciones | 🟢 Liquidity Coverage Ratio | Calendario de flujos, liquidez por vehículo | LCR por bucket horizonte | ¿Puede el patrimonio soportar sus necesidades bajo estrés? | CORE | Depende de calidad de estimación de flujos del cliente |
| Liquidez | Matching de vencimientos | 🟢 Liquidity Ladder | Flujos esperados, ventanas de redención | Escalera de cobertura | Dimensionar colchón de liquidez | CORE | Requiere clasificación correcta de cada vehículo |
| Liquidez | Estrés conjunto | 🟡 Stress liquidity (mercado + flujos) | Escenarios de shock + calendario de flujos | Déficit proyectado bajo estrés | Evitar ventas forzadas en crisis | ADVANCED | Depende de calidad del Motor de Escenarios |
| Alternativos | Valor de fondo PE | 🟢 TVPI / DPI / RVPI / IRR | Cashflows del fondo | Múltiplos y tasa interna de retorno | Evaluar fondos individuales | CORE | Requiere cashflows completos por fondo |
| Alternativos | Comparar contra público | 🟡 PME / Direct Alpha | Cashflows + índice público | Alpha ajustado por timing | Comparar PE vs. alternativa líquida | ADVANCED | Requiere índice público comparable |
| Alternativos | Proyectar compromisos futuros | 🟡 Pacing / simulación NAV | Curvas históricas, vintage | Cash flow proyectado | Planificar ritmo de commitments | ADVANCED | Depende de supuestos de J-curve por estrategia |
| Escenarios | Impacto de crisis pasadas | 🟢 Historical Simulation | Movimientos observados de índices/tasas | Impacto proyectado en portafolio actual | Credibilidad ("¿qué pasó en 2008?") | CORE | Historia no garantiza repetirse |
| Escenarios | Impacto de shocks plausibles futuros | 🟢 Hypothetical Stress | Shocks definidos por Comité | Impacto proyectado | Evaluar resiliencia a futuro | CORE | Depende del juicio macro del Comité |
| Escenarios | Identificar fragilidades estructurales | 🟡 Reverse Stress Testing | Portafolio actual, límites | Combinación de shocks que rompe límites | Gobernanza de riesgo proactiva | ADVANCED | Requiere definición clara de "ruptura" |
| Escenarios | Probabilidad de metas bajo incertidumbre | 🟢 Monte Carlo / Block Bootstrap | Retornos históricos, cashflows | Distribución de resultados futuros | Evaluar éxito de meta bajo incertidumbre | CORE 🔁 | Bootstrap por bloques promovido a la par de MC — ver III.0 Revisión 6 |
| Escenarios | Cambios de régimen | 🔵 Regime Switching / fat tails | Retornos históricos por régimen | Distribución condicional a régimen | — (no recomendado para uso rutinario aún) | RESEARCH | Complejidad de calibración alta |
| Benchmark | Verificar comparabilidad | 🟢 AFI Benchmark Eligibility Framework | Definición de universo, riesgo, moneda, liquidez, horizonte, costos | Estado elegible/no elegible | Bloquear rankings engañosos | CORE | Puede no existir benchmark "razonablemente cercano" |
| Governance | Explicar resultados | 🟢 Reglas determinísticas + plantillas | Resultado de motores | Narrativa reproducible | Auditabilidad fiduciaria | CORE | Menos "natural" que texto generado — es la contrapartida aceptada |
| Governance | Atribución de caja negra | 🔴 SHAP / LIME como núcleo | — | — | — | REJECTED 🔁 | Viola Principio 3 — ver III.0 Revisión 1 |
| Governance | Generación de narrativa libre | 🔴 Auto-Commentary tipo LLM | — | — | — | REJECTED 🔁 | Viola Principio 3 — ver III.0 Revisión 2 |
| Governance | Comparar contra AFP sin verificar | 🔴 Ranking directo sin eligibility check | — | — | — | REJECTED | Viola Principio 7 |

*Nota: esta matriz resume clasificación y decisión soportada. La matriz completa con fórmula, parámetros, validación y responsable está en la Parte XXII (Matriz Maestra Final).*

---

## PARTE IV — PERFORMANCE

### Métrica principal institucional

**TWR (Time-Weighted Return), geométricamente encadenado.** Es el estándar GIPS para evaluar gestores y estrategias porque elimina el efecto del timing de los flujos del cliente — mide la habilidad de gestión, no las decisiones de aportes y retiros del cliente. Se usa en los motores de Performance, Benchmarking y evaluación de gestores.

**Fórmula:**

Para cada subperíodo *t*: R_t = (EMV_t − BMV_t − CF_t) / (BMV_t + CF_t)

TWR total: TWR = ∏(1 + R_t) − 1, para t = 1...n

Donde EMV = valor de mercado al cierre, BMV = valor de mercado al inicio, CF = flujo de caja neto del subperíodo.

### Métricas complementarias

- **CAGR / Annualized TWR** — para comparabilidad entre periodos de distinta duración.
- **Excess Return vs. benchmark** — TWR del portafolio menos TWR del benchmark elegible (sujeto al gate del Motor de Benchmark, Parte XII).
- **Rolling Returns (3-5 años)** — para evaluar consistencia y evitar conclusiones basadas en una sola ventana ("period picking").

### Uso para cliente (comunicación)

**MWR/IRR (XIRR)** sobre la cuenta consolidada, interpretado como "tu retorno personal" — incorpora el timing real de los aportes y retiros del cliente. Se complementa con el TWR para explicar qué habría obtenido el cliente sin sus propias decisiones de timing ("así gestionamos tu dinero" vs. "así te fue a ti").

### Uso para Wealth Manager

TWR y CAGR a nivel de sub-portafolio y de gestor individual, más rolling returns para consistencia. El WM no necesita ver la fórmula — ve el resultado más una nota de qué ventana se usó y desde cuándo.

### Uso para evaluación de fondos

TWR, CAGR, Excess Return y rolling returns a nivel de fondo/gestor, para due diligence y monitoreo continuo (integrado con el marco de selección de gestores del Volumen II).

### Uso para evaluación de portafolio

TWR consolidado por cliente/estrategia; MWR para explicar la experiencia real; atribución (Brinson-Fachler, ADVANCED) para explicar el origen del resultado cuando la desviación vs. benchmark elegible es significativa.

### Tratamiento de flujos

- **TWR:** dividir el período en subperíodos entre cada flujo significativo, calcular el retorno de cada uno ajustando por el flujo, encadenar geométricamente.
- **MWR/IRR:** XIRR sobre todos los cash flows (aportes negativos, retiros positivos, valor final positivo).
- **Supuesto crítico:** flujos correctamente fechados y clasificados; tratamiento separado para fees cuando sea posible.

### Tratamiento de fondos ilíquidos

Fondos privados con NAV trimestral usan **TWR trimestral** sobre NAVs reportados y flujos (capital calls, distribuciones), clasificado como 🟡 ADVANCED por la complejidad adicional de los datos. Se complementa con las métricas específicas de PE (TVPI, DPI, RVPI, IRR, PME, Direct Alpha — Parte X), no se fuerza una comparación mensual/diaria que los datos no soportan.

Al comparar vehículos con distinta frecuencia de valorización, la regla CORE es comparar siempre **a la frecuencia más baja común** (mensual o trimestral), reportando explícitamente la frecuencia usada y advirtiendo sobre las limitaciones de comparabilidad — nunca comparar volatilidad de un fondo diario contra uno trimestral sin ajustar por smoothing.

**No se permiten métricas redundantes sin propósito diferenciado.** Cada métrica de esta parte responde una pregunta distinta (habilidad de gestión, experiencia del cliente, consistencia en el tiempo, comparabilidad); ninguna se agrega "porque también existe".

---

## PARTE V — RISK ENGINE

Para cada metodología: fórmula, inputs, parámetros, horizonte, ventana, interpretación, limitaciones, uso institucional y decisión que soporta.

### Volatilidad (σ)
- **Fórmula:** desviación estándar de retornos históricos, anualizada.
- **Inputs:** serie de retornos (mensual preferido para fondos abiertos).
- **Parámetros:** ventana de 3-5 años cuando disponible.
- **Horizonte:** equivalencia a 1 año.
- **Interpretación:** dispersión total de resultados, sin distinguir dirección.
- **Limitaciones:** trata ganancias y pérdidas por igual; no captura asimetría.
- **Decisión que soporta:** ¿el riesgo total es coherente con el perfil del IPS?
- **Método principal seleccionado:** histórico. **Alternativa:** EWMA (🟡 ADVANCED) cuando se necesita mayor sensibilidad a cambios recientes para alertas — no reemplaza a la histórica, la complementa en el módulo de alertas.

### Downside Deviation (semivarianza)
- **Fórmula:** desviación estándar calculada solo sobre retornos por debajo de un Minimum Acceptable Return (MAR).
- **Inputs:** retornos, MAR (típicamente 0% o tasa libre de riesgo).
- **Interpretación:** riesgo de pérdida, no de volatilidad general — más alineado con cómo los clientes perciben el riesgo.
- **Limitaciones:** requiere definir MAR de forma consistente entre comparaciones.
- **Decisión que soporta:** comunicar riesgo downside al cliente de forma más intuitiva que la volatilidad total.

### Maximum Drawdown
- **Fórmula:** pérdida máxima peak-to-trough sobre la serie de NAV/TWR.
- **Horizonte:** rolling 3-5 años y "desde inicio".
- **Interpretación:** severidad máxima históricamente observada.
- **Limitaciones:** muy dependiente del período elegido; no distingue si la causa fue de mercado o idiosincrática — combinar con Recovery Time cuando esté disponible.
- **Decisión que soporta:** calibrar la tolerancia real del cliente a pérdidas, más allá de lo que declara en un cuestionario.

### Tracking Error (TE)
- **Fórmula:** desviación estándar del exceso de retorno frente al benchmark de política/referencia elegible.
- **Horizonte:** mínimo 36-60 observaciones mensuales.
- **Interpretación:** intensidad del riesgo activo tomado.
- **Limitaciones:** un TE alto puede venir de apuestas factoriales más que de selección de activos; un TE bajo puede esconder closet indexing. No mide la *calidad* del riesgo activo, solo su magnitud.
- **Decisión que soporta:** clasificar estrategias (closet index vs. alto riesgo activo) y diseñar presupuesto de riesgo activo.
- **Dependencia:** requiere que el benchmark haya pasado el gate de elegibilidad (Parte XII).

### Beta
- **Fórmula:** regresión lineal simple de los retornos del portafolio/fondo contra el benchmark relevante.
- **Interpretación:** sensibilidad al movimiento del mercado.
- **Limitaciones:** varía en el tiempo; una ventana puede subestimar el riesgo real — combinar con análisis de régimen (Motor de Escenarios).
- **Decisión que soporta:** stress testing y construcción de portafolios multi-gestor.

### VaR (Value at Risk)
- **Fórmula (histórico, método principal):** percentil empírico de la distribución de retornos observados.
- **Fórmula (paramétrico, alternativa 🟡 ADVANCED):** asume distribución normal o t-Student sobre media y desviación estándar estimadas.
- **Parámetros:** niveles de confianza 95% (comunicación a cliente) y 99% (Comité de Inversiones).
- **Horizonte:** 1 mes y 1 año.
- **Interpretación:** pérdida máxima esperada al nivel de confianza dado, en condiciones normales de mercado.
- **Limitaciones:** no dice nada sobre la magnitud de la pérdida más allá del percentil — para eso está ES.
- **Método principal seleccionado:** histórico, con paramétrico como cross-check cuando la distribución es razonablemente simétrica. Monte Carlo y GARCH **no** se usan como primera línea para VaR de cliente — se reservan para análisis internos avanzados (ver clasificación GARCH en Parte III.0, Revisión 3).

### Expected Shortfall (ES / CVaR)
- **Fórmula:** pérdida promedio condicional a superar el percentil de VaR.
- **Interpretación:** conceptualmente superior al VaR para riesgo de cola porque sí captura la magnitud esperada más allá del umbral.
- **Limitaciones:** más sensible al tamaño de muestra que el VaR; con series cortas, poco confiable.
- **Decisión que soporta:** gestión de riesgo de cola, especialmente relevante en estrategias con distribuciones asimétricas.
- **Método principal seleccionado:** histórico, mismo criterio que VaR.

### Factor Risk
- **Fórmula:** regresión de retornos contra un conjunto de factores básicos (equity, tasas, crédito, FX), inferidos vía índices públicos dado que AFI trabaja principalmente con fondos y ETF.
- **Clasificación:** 🟡 ADVANCED — datos disponibles pero calibración más compleja que las métricas CORE.
- **Decisión que soporta:** evitar concentraciones factoriales ocultas al combinar múltiples gestores (conecta directamente con Principio 6 y el Motor de Diversificación).

### Tail Risk
- **Medida recomendada:** ES histórico + análisis de escenarios (Motor de Escenarios, Parte XI). No se introduce un modelo de colas extremas (EVT) separado en esta versión — la combinación ES + stress testing cubre la necesidad sin la complejidad adicional de calibrar una distribución de valores extremos con series cortas.

### Selección de método principal vs. alternativas — resumen

| Métrica | Método principal (CORE) | Alternativa (ADVANCED+) | Por qué la alternativa no reemplaza a la principal |
|---|---|---|---|
| Volatilidad | Histórica | EWMA | EWMA es más reactiva pero menos estable; se usa para alertas, no para el número "oficial" |
| VaR / ES | Histórico | Paramétrico | Paramétrico asume una forma de distribución que puede no cumplirse; se usa como cross-check |
| Factor risk | — (no hay CORE) | Regresión sobre factores básicos | Complejidad de calibración justifica dejarlo en ADVANCED hasta validar estabilidad |

---

## PARTE VI — DIVERSIFICATION ENGINE

**Objetivo del motor completo:** detectar la diferencia entre **diversificación nominal** (número de fondos, número de posiciones) y **diversificación económica** (número de fuentes de riesgo genuinamente distintas) — Principio 6.

### Correlación y Rolling Correlation
- **Método:** correlación histórica de retornos mensuales, con ventanas rolling de 3-5 años.
- **Uso:** primera línea de defensa para medir diversificación aparente vs. real entre fondos.
- **Limitación:** las correlaciones son inestables — suben precisamente en los momentos de crisis en que más se necesita que se mantengan bajas. Por eso no se usan solas para decisiones de asignación de capital; se combinan con Risk Contribution.

### Risk Contribution y Marginal Contribution
- **Método:** descomposición de la varianza total del portafolio por activo/fondo; contribución marginal vía la matriz de covarianzas.
- **Uso:** este es el modelo que realmente detecta concentraciones ocultas — un activo con peso nominal pequeño puede aportar una fracción desproporcionada del riesgo total si está altamente correlacionado con el resto del portafolio.

### Diversification Ratio y Effective Number of Bets
- **Método:** el "número efectivo de apuestas" se aproxima como el inverso de la suma de cuadrados de las contribuciones al riesgo (una extensión razonable de la lógica de HHI aplicada a contribuciones de riesgo en vez de a pesos nominales — no hay un paper único citado para esta fórmula específica en las fuentes consolidadas; se declara como inferencia metodológica razonable, no como hallazgo empírico).
- **Uso:** traduce una matriz de correlación completa a un solo número interpretable: "tu portafolio de 20 fondos se comporta, en términos de riesgo, como si tuvieras 4 apuestas independientes".

### HHI (Herfindahl-Hirschman Index)
- **Método:** aplicado sobre tres dimensiones distintas, no una sola: pesos económicos, aportes al riesgo, y exposición por factor.
- **Uso:** simple de calcular y de explicar al Comité y al cliente — es intencionalmente la métrica "de entrada" antes de pasar a las más técnicas.

### Factor Exposure
- Comparte metodología con el Factor Risk del Motor de Riesgo (Parte V) — no se duplica el modelo, se reutiliza su output desde la perspectiva de diversificación en vez de la perspectiva de riesgo total.

### Cluster Analysis (cuando corresponda)
- **Método:** clustering jerárquico básico sobre la matriz de correlación, inspirado en la lógica de HRP pero usado únicamente como herramienta de diagnóstico visual — no como método de asignación de capital (ver distinción explícita en Parte III.0, Revisión 4).
- **Clasificación:** 🟡 ADVANCED.

### Cómo AFI identifica concentraciones ocultas — metodología integrada

El proceso combina, en este orden:

1. **HHI nominal** — primer filtro simple, detecta concentración obvia por peso.
2. **Correlación y beta frente a índices clave** (MSCI, FTSE, Bloomberg) — detecta si fondos nominalmente distintos están en realidad expuestos a los mismos índices subyacentes (el caso clásico de "20 fondos large-cap US distintos").
3. **Risk Contribution** — confirma si esa correlación se traduce en concentración real de riesgo, no solo aparente.
4. **Cluster analysis** (ADVANCED) — agrupa visualmente los activos por comportamiento similar para presentación al Comité.
5. **Effective Number of Bets** — resume todo lo anterior en un número único para comunicación simplificada al WM.

Ningún paso reemplaza al anterior; cada uno responde una pregunta distinta y el motor los reporta en conjunto, no de forma aislada.

---

## PARTE VII — PORTFOLIO CONSTRUCTION

Esta parte recibe el mismo rigor especial que exige el mandato: ningún modelo se declara "modelo AFI" por default.

### Comparación de enfoques

| Enfoque | Fundamento | Ventaja principal | Riesgo/limitación | Clasificación AFI |
|---|---|---|---|---|
| Mean Variance (con shrinkage + constraints) | Markowitz, robustez estadística sobre covarianzas | Tradición institucional, transparente, computacionalmente simple | Sensible a errores de estimación de retornos esperados sin constraints fuertes | 🟢 **CORE** |
| Robust Optimization | Extensión de MVO para incorporar incertidumbre en los inputs | Reduce sensibilidad a errores de estimación | Mayor complejidad de calibración | Incorporado dentro de MVO CORE como práctica (shrinkage + bandas), no como modelo separado |
| Black-Litterman | Bayesiano, combina equilibrio de mercado con views | Retornos esperados más estables e intuitivos que MVO con inputs subjetivos directos | Requiere views bien fundamentadas y proceso institucional disciplinado | 🟡 **ADVANCED** (condicionado — ver Parte VIII) |
| Risk Parity / Equal Risk Contribution | Contribución de riesgo igualada, no capital igualado | Alta diversificación, resiliente a distintos entornos macro | Dependencia de estimación de volatilidad; rezagado en mercados alcistas de renta variable | 🟡 **ADVANCED** |
| Hierarchical Risk Parity (HRP) | Clustering jerárquico, evita invertir la matriz de covarianzas | Mejor diversificación out-of-sample según la literatura | No probado aún en el contexto específico de datos de AFI | 🔵 **RESEARCH** |
| Goal Based Optimization | Metas discretas con funciones de utilidad específicas | Se conecta directamente con el IPS y el Principio 1 | Requiere IPS bien estructurado como input; sin eso, es tan bueno como los datos que recibe | 🟢 **CORE** (vía Monte Carlo goal-based, Motor de Cliente/Goal) |

### Modelo CORE
**Mean-Variance con shrinkage y constraints fuertes**, alimentado por Capital Market Assumptions institucionales (no individuales del asesor) y complementado con **Goal-Based Monte Carlo** para traducir el resultado de la optimización en probabilidad de éxito de la meta del cliente. Este es el modelo de entrada para todo cliente de AFI.

### Modelo complementario
**Risk Parity / Equal Risk Contribution** como portafolio de referencia — no reemplaza al MVO, sirve como comparador de "máxima diversificación de riesgo" para perfiles donde tiene sentido evaluar una alternativa defensiva.

### Modelo avanzado
**Black-Litterman**, con la condición de entrada estricta descrita en la Parte VIII — no se activa hasta que el proceso de generación de views esté institucionalizado.

### Modelo experimental
**HRP**, como herramienta de investigación y diagnóstico (ver Parte VI), con posibilidad de promoción futura a ADVANCED como constructor si la evidencia empírica en el contexto de AFI lo confirma.

### Cómo encaja la optimización en el principio AFI

Todo modelo de construcción debe poder responder, no solo "cuál es el peso óptimo de cada activo", sino cómo ese peso se relaciona con:

- **Objetivos** — vía el input del Motor de Cliente/Goal (IPS).
- **Riesgo** — vía constraints alimentados por el Motor de Riesgo (límites de VaR, TE, volatilidad por perfil).
- **Liquidez** — vía constraints de peso máximo en ilíquidos, alimentados por el Motor de Liquidez.
- **Horizonte** — vía el horizonte declarado en el IPS, que determina la ventana de CMAs relevante.
- **Restricciones** — ESG, regulatorias, de concentración por emisor/gestor/país.
- **Comportamiento** — bandas de rebalanceo diseñadas para no gatillar intervención por ruido de corto plazo (Volumen I, Principio 10).
- **Incertidumbre** — vía shrinkage sobre covarianzas y, en el caso de BL, vía la matriz de confianza Ω sobre las views.

Ningún output de este motor es un número aislado — siempre llega acompañado de estas siete referencias.

---

## PARTE VIII — BLACK-LITTERMAN

### Componentes del modelo

| Componente | Definición para AFI |
|---|---|
| **Prior** | Retornos de equilibrio institucional, no una opinión individual |
| **Equilibrium Returns (Π)** | Π = δΣw, derivados de pesos de mercado (índices MSCI/FTSE) y matriz de covarianzas Σ; δ = aversión al riesgo institucional, definida por política |
| **Views** | Opiniones documentadas sobre retornos relativos o absolutos de segmentos específicos, generadas únicamente por el Comité de Inversiones/CIO — nunca por el asesor individual |
| **Confidence (Ω)** | Matriz de varianzas de error de las views, proporcional a la volatilidad histórica del segmento, reducida según la fuerza de la evidencia que sustenta la view |
| **Tau (τ)** | Escala de incertidumbre del prior; valor de referencia 0.025-0.05, fijado por política y revisado anualmente |
| **Covariance** | Con shrinkage (Ledoit-Wolf), consistente con el resto del stack de diversificación (Parte VI) |
| **Constraints** | Los mismos límites de concentración, liquidez e ilíquidos que aplican al MVO base |

### Cómo deben generarse las views — la arquitectura exigida por el mandato

El mandato prohíbe explícitamente: **opinión subjetiva → número arbitrario → optimización**. La arquitectura que reemplaza ese patrón:

```
EVIDENCIA (research documentado, macro, fundamental)
        ↓
VIEW (relativa o absoluta, redactada y justificada por escrito)
        ↓
CONVICCIÓN (traducida a Ω — no es un número que el asesor "siente")
        ↓
BLACK-LITTERMAN (ejecución centralizada, no en manos del asesor)
        ↓
PORTAFOLIO (expected returns posteriores entran al Motor de Construcción)
```

Cada view debe cumplir tres condiciones antes de entrar al modelo:

1. **Documentación de evidencia** — research macro o fundamental por escrito, no una intuición de mesa.
2. **Tipo explícito** — relativa ("EM equity tendrá 150 bps más que DM equity") o absoluta ("IG credit USD tendrá 4% anual"), nunca ambigua.
3. **Aprobación del Comité** — el asesor puede *sugerir* un tema para investigación, pero no parametriza el modelo directamente. El asesor ve el output de BL como "house view ya consolidada", no como un panel donde introduce sus propias opiniones.

### Por qué esto queda marcado como decisión pendiente parcial

El proceso descrito arriba es la arquitectura *correcta* según la evidencia consolidada en los cuatro volúmenes, pero **la existencia misma de un Comité de Inversiones con la disciplina para sostener este proceso de forma no ad-hoc no está confirmada como una capacidad actual de AFI** — es una condición organizacional, no solo técnica. Por eso:

> 🔶 **DECISIÓN PENDIENTE (institucional, no metodológica):** Black-Litterman se clasifica 🟡 ADVANCED y **no se activa en producción** hasta que AFI confirme, con evidencia operativa propia (actas de Comité, documentación de views a lo largo de al menos 2-3 ciclos de revisión), que el proceso Evidencia→View→Convicción→BL descrito arriba se sostiene en la práctica y no colapsa en el patrón prohibido de opinión→número arbitrario. Ver Parte XXIII para el registro formal de este pendiente.

---

## PARTE IX — LIQUIDITY ENGINE

**Pregunta que responde el motor:** ¿puede el patrimonio soportar sus necesidades de liquidez bajo escenarios adversos?

### Liquidity Ladder
Escalera de vencimientos/flujos de caja construida por horizonte (0-3 meses, 3-12 meses, >12 meses), contra la cual se hace matching de necesidades previstas del cliente.

### Liquidity Coverage
Liquidity Coverage Ratio (LCR) por bucket de horizonte, considerando qué proporción de activos es vendible a distintos plazos (día, semana, mes, trimestre) sin destrucción de valor significativa.

### Cash Flow Forecasting
Proyección de flujos esperados: retiros de clientes, capital calls de alternativos, distribuciones, gastos declarados en el IPS.

### Capital Calls y Distributions
Integradas desde el Motor de Alternativos (Parte X) — el Motor de Liquidez no recalcula estas curvas, las consume.

### Stress Liquidity
Escenarios de estrés combinado: caída de mercado simultánea con llamadas de capital (el caso más peligroso — precisamente cuando los activos líquidos valen menos es cuando pueden llegar más obligaciones de capital call).

### Liquidity Horizon
Clasificación de cada vehículo por: periodicidad de valuación, ventana de redención (si aplica), lock-ups, y comportamiento típico de cash flow (para alternativos, basado en historial de vintage similar).

### Integración de activos líquidos e ilíquidos

Reglas AFI CORE:
- El peso en activos ilíquidos no puede exceder un límite definido como función del **life balance sheet completo** del cliente (no solo del portafolio financiero visible), consistente con el Principio 2 del Volumen I (visión de balance extendido).
- El colchón de liquidez en activos líquidos debe dimensionarse para cubrir capital calls y gastos esperados bajo escenarios razonables de estrés, no solo bajo el escenario central.

---

## PARTE X — ALTERNATIVE INVESTMENTS

### Private Equity

| Métrica | Qué mide | Clasificación |
|---|---|---|
| TVPI (Total Value to Paid-In) | Múltiplo total sobre capital invertido | 🟢 CORE (si hay cashflows por fondo) |
| DPI (Distributions to Paid-In) | Múltiplo ya realizado/distribuido | 🟢 CORE |
| RVPI (Residual Value to Paid-In) | Múltiplo aún no realizado (NAV residual) | 🟢 CORE |
| IRR | Tasa interna de retorno sobre cashflows del fondo | 🟢 CORE |
| PME (Public Market Equivalent) | Comparación contra índice público equivalente | 🟡 ADVANCED |
| Direct Alpha | Alpha ajustado por timing frente a índice público | 🟡 ADVANCED |
| Vintage Analysis | Comparación de cohortes por año de inicio | 🟡 ADVANCED |
| J-Curve | Modelo de forma típica de cash flow en el tiempo | Insumo para pacing (Motor de Liquidez), no una métrica de evaluación en sí misma |

### Private Credit

Métricas núcleo: **default rate, recovery, LGD (Loss Given Default), yield, spread, duration, liquidez.** Uso principal a través de métricas agregadas de los fondos y análisis de la gestora — AFI no opera a nivel de préstamo individual, consistente con el alcance de un Multi Family Office (no un originador directo de crédito).

### Real Estate e Infrastructure

Métricas núcleo: cap rate, NOI (Net Operating Income), LTV, DSCR, IRR, equity multiple — trabajadas a nivel de fondo consolidado (NAV, income, leverage, DSCR promedio), no a nivel de activo único.

### Integración con el portafolio completo

Toda métrica de alternativos se traduce a tres formatos de consumo por otros motores:

1. **Perfil de cash flow** → alimenta el Motor de Liquidez.
2. **Beta y exposición factorial aproximada** → alimenta el Motor de Riesgo.
3. **Contribución al retorno esperado** → alimenta el Motor de Construcción.

### Regla explícita sobre NAV privado

**El NAV reportado por un fondo privado NO se trata como equivalente a un precio de mercado.** Las valuaciones trimestrales introducen smoothing artificial que subestima la volatilidad real y sobreestima la correlación con activos líquidos si no se ajusta. Todo cálculo de riesgo o correlación que incluya vehículos privados debe declarar explícitamente este ajuste o su ausencia.

---

## PARTE XI — SCENARIO ENGINE

| Método | Clasificación | Uso |
|---|---|---|
| Historical Simulation | 🟢 CORE | Aplicar el portafolio actual a episodios históricos observados (2008, COVID, taper tantrum, crisis local) — da credibilidad ("esto ya pasó") |
| Monte Carlo / Bootstrap tradicional | 🟢 CORE | Evaluar probabilidad de alcanzar metas del cliente (Motor de Cliente/Goal) |
| Block Bootstrap | 🟢 CORE 🔁 | Preserva autocorrelación y clustering de volatilidad — promovido a la par de Monte Carlo tradicional (ver Parte III.0, Revisión 6) |
| Stress Testing (hipotético) | 🟢 CORE | Shocks plausibles diseñados por el Comité (p. ej. +200bps tasas, −30% equity EM) |
| Reverse Stress Testing | 🟡 ADVANCED | Identificar qué combinación de shocks rompería los límites del portafolio — gobernanza proactiva |
| Regime Analysis | 🔵 RESEARCH | Modelos de dos o más regímenes (normal vs. crisis); complejidad de calibración no justificada aún para uso rutinario |

### Cómo los escenarios afectan cada dimensión

Cada escenario ejecutado debe reportar su impacto proyectado en, como mínimo, estas cinco dimensiones — nunca solo en retorno:

- **Retorno** — impacto directo en el valor del portafolio.
- **Riesgo** — cómo cambia VaR/ES bajo el escenario.
- **Liquidez** — si el escenario coincide con necesidades de capital call, según integración con el Motor de Liquidez.
- **Concentración** — si el escenario golpea desproporcionadamente algún factor concentrado (conecta con Motor de Diversificación).
- **Objetivos del cliente** — traducción final a probabilidad de éxito de la meta (Motor de Cliente/Goal), que es la métrica que el WM realmente comunica.

La moneda se trata como una dimensión transversal dentro de "riesgo", no como una categoría separada — todo escenario que incluya activos en distinta denominación debe simular el componente FX explícitamente, no asumir cobertura implícita.

**Combinación recomendada:** Historical (credibilidad) + Hypothetical (relevancia futura) + Reverse (fragilidades estructurales) — los tres, no uno solo, porque cada uno responde una pregunta distinta que los otros dos no cubren.

---

## PARTE XII — BENCHMARK ENGINE

### AFI Benchmark Eligibility Framework

**Regla central: antes de cualquier comparación, verificar ocho dimensiones. Si el benchmark no es elegible, el sistema NO genera ranking.**

| Dimensión | Qué se verifica |
|---|---|
| Objetivo | ¿El benchmark persigue el mismo tipo de objetivo que el portafolio (crecimiento, ingreso, preservación)? |
| Asset Allocation | ¿La composición de activos es razonablemente comparable? |
| Riesgo | ¿El nivel de riesgo esperado es del mismo orden de magnitud? |
| Moneda | ¿Está denominado en la misma moneda o se ajusta el FX explícitamente? |
| Liquidez | ¿El benchmark asume el mismo nivel de liquidez que el portafolio real (relevante cuando hay alternativos)? |
| Horizonte | ¿El horizonte temporal de referencia coincide? |
| Costos | ¿Se comparan retornos netos contra netos, o se está mezclando bruto vs. neto? |
| Restricciones | ¿El benchmark opera bajo restricciones regulatorias o de universo comparables (relevante para el caso AFP)? |

### Tipos de benchmark

- **Market Benchmark** — índices amplios (MSCI, FTSE).
- **Strategic/Policy Benchmark** — combinación de índices que refleja la SAA específica del cliente.
- **Custom Benchmark** — adaptado a restricciones específicas del cliente.
- **Peer Benchmark** — comparación contra pares (p. ej. AFP) **solo cuando existe comparabilidad demostrada** en las ocho dimensiones.

### La comparación contra AFP — aplicación explícita de la regla

Este es el caso de uso que motivó originalmente el framework y donde el mandato es más explícito: un cliente de AFI con exposición relevante a activos alternativos e ilíquidos **no es comparable** contra una AFP sujeta a regulación de inversión distinta, sin estructura de liquidez equivalente y con objetivo de acumulación previsional (no goal-based multi-objetivo). Salvo que las ocho dimensiones se verifiquen explícitamente y se documenten como comparables, el sistema no debe producir un ranking direccional ("tu portafolio superó/no superó a la AFP") — solo puede mostrar diferencias cualitativas descriptivas.

Este es también el ejemplo del modelo explícitamente 🔴 REJECTED de la Parte III.1: "ranking directo sin eligibility check".

---

## PARTE XIII — REBALANCING ENGINE

### Metodología completa

```
PORTAFOLIO ACTUAL
        ↓
DRIFT (medir desviación vs. SAA/bandas configuradas)
        ↓
SAA (¿la desviación es respecto al objetivo estratégico vigente?)
        ↓
RISK (¿cómo cambia σ, TE, VaR, ES si no se actúa?)
        ↓
LIQUIDITY (¿el rebalanceo es ejecutable sin generar ventas forzadas?)
        ↓
COSTS (estimación de costos de transacción y, donde aplique, impacto fiscal)
        ↓
SCENARIOS (¿cómo se comporta cada alternativa bajo shocks plausibles?)
        ↓
ALTERNATIVES (2-3 propuestas de rebalanceo con sus trade-offs)
        ↓
EXECUTIVE DECISION (el Wealth Manager decide y ejecuta)
```

### Tipos de trigger — cuáles son CORE y cuáles ADVANCED

| Tipo | Clasificación | Descripción |
|---|---|---|
| Calendar-Based | 🟢 CORE | Revisión mínima trimestral/semestral, independiente del drift observado |
| Threshold-Based (bandas) | 🟢 CORE | Rebalanceo cuando un peso se sale de bandas configuradas por asset class |
| Risk-Based / Volatility-Based | 🟡 ADVANCED | Rebalanceo adicional cuando el riesgo (σ, TE, VaR) supera umbrales relacionados con el perfil del cliente, incluso sin drift de peso significativo |
| Liquidity-Based | Integrado | No es un trigger independiente — es una restricción que se aplica sobre cualquier propuesta generada por los triggers anteriores, para evitar rebalanceos que generen brechas de liquidez |

### Lo que el sistema debe hacer

- **Detectar** desviaciones (drift) de forma sistemática y consistente.
- **Cuantificar** las consecuencias de no actuar (impacto en riesgo, no solo el porcentaje de desviación).
- **Simular** 2-3 alternativas de rebalanceo, no solo "la" solución óptima.
- **Mostrar** costos de transacción y, donde sea relevante, consideraciones fiscales de cada alternativa.
- **Mostrar** impactos proyectados en riesgo y en probabilidad de meta (vía Motor de Cliente/Goal) para cada alternativa.
- **Presentar** opciones — nunca una única recomendación sin alternativas visibles.

### Lo que el sistema NO hace

**El sistema no ejecuta operaciones.** Genera propuestas con evidencia y alternativas; la ejecución es siempre un acto humano del Wealth Manager, consistente con el Principio 2 (separación cálculo/decisión). Esto no es una limitación técnica temporal — es una posición institucional permanente de este documento.

---

## PARTE XIV — MODEL GOVERNANCE

### Reglas por tipo de validación

- **Backtesting.** Todo modelo CORE y ADVANCED debe compararse contra resultados realizados (p. ej. pronóstico de riesgo vs. riesgo efectivamente observado; probabilidad proyectada de alcanzar meta vs. trayectoria real). Frecuencia mínima: anual.
- **Sensitivity Analysis.** Variar parámetros clave (ventana de estimación, τ y δ en Black-Litterman, bandas de rebalanceo) y observar la magnitud del impacto en el output. Un modelo cuyo resultado cambia drásticamente ante variaciones razonables de parámetros es un modelo frágil, no uno preciso.
- **Parameter Stability.** Verificar que los parámetros elegidos producen resultados razonables en distintos períodos históricos — no ajustados a un único episodio (evitar sobreajuste retrospectivo).
- **Out-of-Sample Testing.** Todo modelo debe probarse en un período de datos que no participó en su calibración original.
- **Stress Testing de modelos** (distinto del Motor de Escenarios de portafolio — aquí se testea el modelo mismo). Cómo se comporta el modelo bajo condiciones extremas: colapsos de correlación, shocks de volatilidad no vistos en el período de calibración.
- **Data Quality.** Ver Parte XVII para el detalle completo de los controles.
- **Model Risk.** Cada modelo tiene un responsable institucional designado (no una persona individual sin respaldo) y una fecha de última validación registrada.

### ¿Qué sucede cuando el modelo no tiene suficiente información?

El sistema devuelve explícitamente: **"Información insuficiente para producir una estimación confiable."** — nunca un número calculado sobre datos pobres presentado con la misma confianza visual que uno robusto (Principio 8). Este es un estado de sistema de primera clase, no un error genérico ni un campo vacío.

### Criterio de degradación

Un modelo puede — y debe — degradarse de una clasificación superior a una inferior (p. ej. de ADVANCED a RESEARCH) si su desempeño en producción no confirma su promesa teórica, si el backtesting muestra sesgo sistemático, o si el out-of-sample testing revela inestabilidad de parámetros no anticipada en la calibración original. La degradación no es un fracaso del proceso — es el proceso funcionando correctamente. Ningún modelo CORE es CORE de forma permanente por definición; lo es mientras la evidencia lo sostenga.

---

## PARTE XV — PARAMETER GOVERNANCE

Cada parámetro del sistema pertenece a exactamente una categoría, con un propietario único de la decisión de cambiarlo:

| Categoría | Definición | Ejemplos | Quién puede modificarlo |
|---|---|---|---|
| **Matemático** | Constante calculada automáticamente, sin discrecionalidad | Factor de anualización (√12 para mensual→anual) | Nadie — se deriva, no se decide |
| **Sistema** | Calculado automáticamente a partir de datos, sin input humano directo | Volatilidad histórica, TE, skewness | Nadie directamente — cambia solo si cambian los datos de entrada |
| **Institucional** | Definido por política de AFI, aplicable a todos los clientes de un perfil | Niveles de confianza de VaR (95%/99%), δ en Black-Litterman, τ | Comité de Inversiones, revisión anual mínima |
| **Cliente** | Definido mediante el IPS de cada cliente específico | Horizonte, tolerancia a la pérdida, restricciones ESG | Asesor + Cliente, con validación del Comité |
| **Comité** | Decisión colegiada específica, no una política general | Views de Black-Litterman, cambios de CMAs, SAA institucional | Investment Committee exclusivamente |
| **Wealth Manager** | Ajuste operativo limitado, siempre dentro de rangos pre-aprobados | Preferencia de frecuencia de comunicación de riesgo al cliente | Asesor, dentro de límites institucionales — nunca fuera de ellos |

### Regla de auditoría de parámetros

**Toda modificación de un parámetro de categoría Institucional, Comité o Cliente debe quedar registrada** con: quién la propuso, quién la aprobó, fecha, valor anterior, valor nuevo, y justificación escrita. Los parámetros Matemáticos y de Sistema no requieren este registro porque no involucran discrecionalidad humana — cambian solo si cambia el dato subyacente, lo cual ya queda registrado por el propio cálculo.

---

## PARTE XVI — DATA REQUIREMENTS (Data Dictionary conceptual)

Para cada categoría de dato: nombre, definición, fuente, frecuencia, tipo, calidad mínima, transformaciones, dependencias, motor que lo utiliza.

| Dato | Definición | Fuente | Frecuencia | Calidad mínima | Motor(es) que lo usa |
|---|---|---|---|---|---|
| **NAV** | Valor de activo neto por unidad/participación | Custodio, administrador de fondo | Diaria (líquidos) / mensual / trimestral (privados) | Sin gaps no explicados; reconciliado contra fuente secundaria cuando sea posible | Performance, Riesgo, Diversificación |
| **Returns** | Retornos derivados de NAV, ajustados por flujos | Calculado desde NAV + Flujos | Igual a NAV | Consistente con la frecuencia nativa del vehículo (no interpolar) | Todos |
| **Factsheets** | Documentación descriptiva del fondo (estrategia, universo, restricciones) | Gestora / administradora | Actualización ante cambios materiales | Debe existir versión vigente antes de aprobar el vehículo | Construcción, Due Diligence (Volumen II) |
| **Reglamento / Prospecto** | Documento legal del vehículo | Gestora / regulador | Ante cambios | Vigente y consistente con factsheet | Due Diligence, Compliance |
| **Holdings** (cuando existan) | Composición detallada de posiciones subyacentes | Gestora (transparencia variable según vehículo) | Mensual/trimestral cuando disponible | Look-through suficiente para factor risk | Riesgo, Diversificación |
| **Benchmarks** | Series de índices de referencia | Proveedores de índices (MSCI, FTSE, Bloomberg) | Diaria | Metodología documentada y estable | Performance, Riesgo, Benchmark |
| **Índices** | Series de mercado para CMAs y factor risk | Proveedores de índices | Diaria/mensual | Serie histórica suficientemente larga | Riesgo, Construcción, Diversificación |
| **FX** | Tipos de cambio | Proveedor de datos de mercado | Diaria | Consistente entre todos los cálculos multi-moneda | Riesgo, Escenarios, Performance |
| **Tasas** | Curvas de tasas de interés | Bancos centrales, proveedores de datos | Diaria | Curva completa, no solo puntos aislados | Riesgo, Escenarios |
| **Cash flows** | Flujos de entrada/salida a nivel de cliente/fondo | Custodio, administrador | Por evento | Fecha y monto exactos, clasificación correcta (aporte/retiro/fee) | Performance, Liquidez, Alternativos |
| **Capital Calls** | Llamadas de capital de vehículos privados | Gestora del vehículo privado | Por evento | Fecha, monto, vehículo identificado | Liquidez, Alternativos |
| **Distributions** | Distribuciones de vehículos privados | Gestora del vehículo privado | Por evento | Fecha, monto, vehículo identificado | Liquidez, Alternativos |
| **Fees** | Comisiones de gestión y éxito | Gestora, custodio | Según estructura del vehículo | Separadas del retorno bruto cuando sea posible | Performance, Construcción |
| **Client Objectives** | Metas declaradas del cliente | Cliente, vía asesor | Ante cambios / revisión periódica | Documentadas en el IPS, no informales | Cliente/Goal, Construcción |
| **IPS** | Investment Policy Statement formal | Asesor + Cliente, aprobado por Comité | 1-3 años o ante eventos de vida | Firmado y vigente | Todos (referencia central, Principio 1) |

---

## PARTE XVII — REGLAS DE CALIDAD DE DATOS

**Regla de oro AFI:** *"Si los datos no permiten estimar la métrica con un nivel de confianza razonable, el sistema debe declarar explícitamente que la evidencia es insuficiente."*

Cada problema sigue el patrón: **Detection → Action → Warning → Fallback o Model Block.**

| Problema | Detection | Action | Warning | Fallback / Model Block |
|---|---|---|---|---|
| **Missing Data** | Días/meses sin NAV registrado | Evaluar impacto de la brecha en el cálculo específico | Flag visible en el output indicando el gap | Imputación prudente si el gap es menor y no afecta el resultado materialmente; **Model Block** si el gap es significativo |
| **Outliers** | Retornos extremos fuera de rango histórico razonable | Validar contra fuente secundaria o custodio antes de aceptar | Flag de "retorno atípico pendiente de validación" | Excluir del cálculo hasta validación; nunca incluir silenciosamente |
| **Stale Prices** | NAV repetido de forma improbable en periodos consecutivos | Verificar si corresponde a vehículo de baja frecuencia legítima o a un error de carga | Flag distinguiendo "baja frecuencia esperada" vs. "posible error" | Model Block si no se puede distinguir con confianza |
| **NAV inconsistentes** | Cambios de NAV improbables dado el perfil de riesgo del vehículo | Contraste con administrador/custodio | Flag crítico, prioridad alta | Model Block hasta reconciliación |
| **Frequency Mismatch** | Combinación de series con distinta frecuencia nativa | Agregar siempre a la frecuencia más baja común (Parte IV) | Nota explícita de la frecuencia usada en cualquier comparación | Nunca interpolar frecuencia faltante — usar la frecuencia nativa disponible |
| **Currency Mismatch** | Series en distinta moneda combinadas sin ajuste | Documentar y aplicar FX explícitamente | Nota de qué tipo de cambio y fecha se usó | Model Block si no hay serie FX confiable para el ajuste |
| **Look-Ahead Bias** | Uso de información no disponible en el momento histórico simulado | Verificar que todo dato usado en backtesting estaba disponible en esa fecha | — (control de diseño, no de runtime) | Rechazar el backtest si se detecta la fuga |
| **Survivorship Bias** | Universos de fondos que excluyen fondos cerrados/liquidados | Usar bases con histórico de fondos cerrados, no solo activos actuales | Nota metodológica en cualquier análisis de universo | Advertir explícitamente si la fuente de datos disponible no cubre fondos cerrados |
| **Backfill Bias** | Historial "reconstruido" antes del lanzamiento real de un fondo | Identificar fecha de lanzamiento real vs. fecha de inicio de la serie | Flag de "historial parcialmente reconstruido" | Excluir el período pre-lanzamiento del cálculo de habilidad del gestor |
| **Selection Bias** | Comparaciones que seleccionan implícitamente solo los mejores casos | Revisar criterio de inclusión del universo de comparación | Nota metodológica visible | Rechazar la comparación si el criterio de selección no está documentado |

---

## PARTE XVIII — DECISION LIBRARY

Cada decisión institucional recurrente, con: inputs, modelos, reglas, evidencia, resultado, alternativas, y el punto exacto de Human Override.

### D1 — ¿Rebalancear?
- **Inputs:** posiciones actuales, bandas SAA, costos de transacción estimados.
- **Modelos:** Motor de Rebalanceo (Parte XIII) — drift, riesgo, liquidez, costos, escenarios.
- **Regla:** trigger calendar-based O threshold-based activado.
- **Evidencia:** magnitud del drift, impacto proyectado en riesgo si no se actúa.
- **Resultado del sistema:** 2-3 alternativas de rebalanceo con costos e impactos.
- **Human Override:** el WM elige la alternativa, la modifica, o decide no actuar — siempre con justificación registrada si difiere de la sugerencia con mayor convicción.

### D2 — ¿Mantener estrategia?
- **Inputs:** performance vs. IPS, cambios de circunstancias del cliente, cambios estructurales de mercado.
- **Modelos:** Motor de Performance + Motor de Cliente/Goal.
- **Regla:** mantener por default; revisar solo ante evento de vida del cliente, cambio de horizonte de meta, o cambio de régimen macro estructural — **nunca ante volatilidad de corto plazo aislada** (Volumen I, Principio 10).
- **Resultado del sistema:** clasificación de la señal como "ruido" o "cambio estructural" según el árbol de decisión de la Parte III.4 del Volumen III.
- **Human Override:** el WM confirma la clasificación o la impugna con evidencia adicional.

### D3 — ¿Cambiar fondo? / D4 — ¿Agregar fondo? / D5 — ¿Reducir exposición?
- **Inputs:** due diligence cuantitativa y cualitativa (Volumen II completo — pilares People/Philosophy/Process/Parent/Price), estado en Approved List.
- **Modelos:** tabla de métricas del Volumen II (Sharpe, Sortino, IR, Active Share, TE, etc.), Motor de Diligencia.
- **Regla:** ningún cambio se basa solo en performance reciente — el memo de recomendación debe incluir proceso, equipo y ODD (Operational Due Diligence), no solo cuantitativa.
- **Estados posibles:** Approved-Active / Watchlist / Restricted / Removed (Volumen II, Tabla 2).
- **Human Override:** decisión final siempre del Comité de Inversiones, no del asesor individual ni del sistema.

### D6 — ¿Aumentar liquidez?
- **Inputs:** Liquidity Coverage Ratio proyectado, calendario de flujos, escenarios de estrés.
- **Modelos:** Motor de Liquidez (Parte IX).
- **Regla:** déficit proyectado bajo escenario de estrés razonable → alerta automática.
- **Resultado del sistema:** plan de liquidez con alternativas de reasignación líquido↔ilíquido.
- **Human Override:** el WM decide el timing y la composición exacta de la reasignación.

### D7 — ¿Existe concentración excesiva?
- **Inputs:** HHI, risk contribution, factor exposure.
- **Modelos:** Motor de Diversificación (Parte VI).
- **Regla:** HHI o risk contribution superan umbral institucional por dimensión (emisor, gestor, país, factor).
- **Resultado del sistema:** identificación de la dimensión específica de concentración (no solo "existe concentración").
- **Human Override:** el WM decide si la concentración es aceptable dado un objetivo específico del cliente (p. ej. concentración intencional en capital humano/empresa familiar).

### D8 — ¿El riesgo es compatible con el IPS?
- **Inputs:** VaR/ES actual, límites definidos en el IPS por perfil.
- **Modelos:** Motor de Riesgo (Parte V).
- **Regla:** violación de límite de VaR/ES/volatilidad del perfil → alerta, no bloqueo automático.
- **Human Override:** el Comité puede aprobar una excepción documentada; el sistema nunca ajusta el portafolio automáticamente.

### D9 — ¿La liquidez es suficiente?
- Ver D6 — misma infraestructura, formulada como pregunta de estado en vez de acción.

### D10 — ¿El benchmark es elegible?
- **Inputs:** las ocho dimensiones del Benchmark Eligibility Framework (Parte XII).
- **Modelos:** Motor de Benchmark — actúa como *gate*, no solo como cálculo.
- **Regla:** si cualquier dimensión crítica falla (particularmente moneda, liquidez o restricciones regulatorias), el benchmark es no-elegible.
- **Resultado del sistema:** estado binario elegible/no-elegible con el detalle de qué dimensión falló.
- **Human Override:** el Comité puede documentar una excepción para un uso específico y acotado, nunca de forma general.

### D11 — ¿Existe deterioro (de un gestor)?
- **Inputs:** triggers cuantitativos (alpha rolling negativo persistente, TE no explicado) y cualitativos (salida de PM clave, cambio de dueño, hallazgos de ODD) del Volumen II, Bloque VI.
- **Modelos:** Motor de Monitoreo + framework de señales tempranas (style drift, team drift, process drift, capacity drift, liquidity deterioration, fee changes, cambios de propiedad).
- **Regla:** combinación de triggers cuantitativos + cualitativos → Watchlist automática; hallazgo operacional crítico → prioridad alta independiente de la performance.
- **Resultado del sistema:** clasificación causa raíz — cíclico/temporal vs. estructural vs. operacional/integridad.
- **Human Override:** el Comité de Inversiones decide mantener/watchlist/eliminar; el sistema solo propone la clasificación.

### D12 — ¿Existe una oportunidad?
- **Inputs:** desviaciones favorables vs. modelo institucional, cambios de mercado que favorecen el perfil del cliente.
- **Modelos:** Motor de Monitoreo (agregador), consumiendo señales de Performance y Escenarios.
- **Regla:** menos codificable que las señales de riesgo — requiere mayor peso del juicio del WM.
- **Human Override:** alto — esta es una de las decisiones donde el sistema aporta menos valor relativo y el WM aporta más, consistente con el Volumen I (decisiones que no deben automatizarse completamente).

### D13 — ¿Rebalanceo extraordinario por evento?
- **Inputs:** VaR/drawdown observado, escenario de mercado activado.
- **Modelos:** Motor de Riesgo + Motor de Escenarios.
- **Regla:** movimiento extremo que excede umbrales pre-definidos de VaR o drawdown.
- **Human Override:** siempre requiere aprobación explícita del Comité dado el carácter extraordinario — no es un flujo automático como D1.

### D14 — Aprobación de nuevos gestores/fondos
- Corresponde íntegramente al framework de 7 etapas del Volumen II (Universo → Screening → IDD → ODD → Integración → Comité → Approved List). No se resume aquí en detalle para evitar duplicación — ver Volumen II, Sección 12, incorporado como referencia normativa de este documento.

### D15 — Gobernanza de modelos
- Ver Parte XIV (Model Governance) — esta decisión es sobre los modelos mismos, no sobre portafolios de clientes, y su Human Override recae en el Comité de Model Risk, no en el WM individual.

---

## PARTE XIX — EXPLICABILIDAD

### La contradicción identificada, explicada formalmente

**Contradicción:** El Volumen III (Sección 3) propone un "Núcleo de Inteligencia Cuantitativa Explicable" basado en SHAP/LIME para atribución de riesgo, con una hoja de ruta hacia una Fase 4 de "Auto Commentary" — generación de narrativa tipo LLM inspirada en herramientas comerciales existentes. El Volumen III-B (Parte XV), en cambio, clasifica explícitamente "modelos de ML opacos (black-box) para sugerir portafolios sin explicabilidad y sin gobernanza robusta" como 🔴 REJECTED. El mandato fundacional de este documento (Parte XIX y Regla Final) prohíbe expresamente el uso de LLM como componente del motor y exige que la explicación principal sea **determinística, auditable y reproducible**.

**Resolución:** se adopta la posición del Volumen III-B y del mandato fundacional. El diseño de explicabilidad del Volumen III **no se implementa como está propuesto**. Esta no es una decisión ambigua que requiera aprobación adicional del Comité — el mandato fundacional ya la resuelve de forma inequívoca; se documenta aquí para que quede trazable por qué el diseño de un volumen previo no sobrevivió a la consolidación.

**Por qué la resolución es correcta y no solo "la que pide el mandato":** SHAP y LIME son técnicas de *aproximación* sobre modelos que pueden no ser interpretables por sí mismos — explican una predicción local, pero la explicación misma es una estimación estadística, no una regla exacta. Para un output que puede terminar respaldando una recomendación fiduciaria auditada por un regulador, esa capa de aproximación adicional introduce exactamente el tipo de opacidad que el deber fiduciario busca evitar. Un LLM generando comentario libre agrava el problema: dos ejecuciones del mismo cálculo podrían producir narrativas distintas, lo cual es inaceptable para un sistema que debe poder reconstruirse (Principio 9).

### Cómo se explica un resultado en AFI — el reemplazo determinístico

```
Resultado numérico del motor
        ↓
Regla de clasificación (umbral fijo, documentado, versionado)
        ↓
Plantilla de narrativa parametrizada (texto fijo con variables numéricas insertadas)
        ↓
Mensaje final
```

**Ejemplo conceptual** (igual al del mandato fundacional, para consistencia): *"El portafolio presenta una desviación de X respecto de la SAA objetivo. La banda institucional es Y. El riesgo permanece dentro de Z. El sistema clasifica el evento como revisión de rebalanceo."*

Cada elemento de esa frase —X, Y, Z, y la clasificación final— proviene de un cálculo y una regla fija, no de un modelo generativo. Ejecutar el mismo cálculo dos veces con los mismos datos produce exactamente la misma explicación.

### Qué debe mostrar toda explicación

- **Qué ocurrió** — el resultado numérico, en el lenguaje del motor correspondiente.
- **Por qué ocurrió** — la regla o umbral específico que se activó.
- **Qué regla se activó** — trazable hasta la Parte de este documento que la define.
- **Qué evidencia existe** — los datos de entrada exactos usados en el cálculo.
- **Qué alternativas existen** — cuando la decisión lo amerita (Decision Library, Parte XVIII).

### Estratificación por stakeholder — sin generación de lenguaje libre

El Volumen III proponía correctamente adaptar la profundidad del mensaje según el destinatario (WM, Comité, cliente) — esa idea se conserva, pero se reimplementa sin generación libre: cada stakeholder tiene una **plantilla distinta con distinto nivel de detalle numérico expuesto**, no una narrativa generada de forma independiente para cada uno.

| Stakeholder | Qué ve | Cómo se construye |
|---|---|---|
| Wealth Manager | Resultado + driver principal + regla activada + alternativas | Plantilla técnica con acceso a la fórmula subyacente si la solicita |
| Comité de Inversiones | Enfoque en consistencia con políticas, límites y concentración sistémica | Plantilla orientada a gobernanza, con foco en excepciones y approved list |
| Cliente | Progreso hacia metas, explicación intuitiva sin tecnicismos | Plantilla simplificada — mismo cálculo subyacente, distinto vocabulario, nunca distinto número |

---

## PARTE XX — HUMAN-IN-THE-LOOP

Esta separación es el Principio 2, aplicado de forma exhaustiva a cada verbo posible:

### SISTEMA
- **Calcula** — todas las métricas de las Partes IV-XII.
- **Detecta** — drift, deterioro de gestores, violaciones de límites, concentraciones.
- **Compara** — solo contra benchmarks que pasaron el gate de elegibilidad (Parte XII).
- **Simula** — escenarios (Parte XI), alternativas de rebalanceo (Parte XIII), Monte Carlo de metas.
- **Alerta** — según los triggers definidos en cada motor y consolidados en el Motor de Monitoreo.
- **Propone** — alternativas con evidencia, nunca una única recomendación sin opciones visibles.
- **Documenta** — todo cálculo queda registrado en el log de auditoría (Parte XXI), sin excepción.

### EJECUTIVO (Wealth Manager / Comité, según la decisión)
- **Interpreta** — el resultado en el contexto específico del cliente, más allá de lo que el sistema puede saber.
- **Contextualiza** — con información cualitativa que el sistema no captura (dinámica familiar, eventos no declarados aún, matices de la relación).
- **Decide** — toda acción final sobre el patrimonio del cliente.
- **Acepta/rechaza** — cada propuesta del sistema, explícitamente.
- **Justifica overrides** — con una nota registrada, no de forma silenciosa.
- **Comunica al cliente** — el sistema nunca comunica de forma autónoma al cliente final.

### Decisiones que el mandato reserva explícitamente al juicio humano — sin excepción

Recuperado del Volumen I (Sección 7): definición de objetivos vitales, gestión de crisis y eventos extremos del cliente, priorización entre metas en conflicto, y elección de estructuras de gobernanza familiar. Ningún motor de este documento intenta automatizar estas cuatro áreas, ni parcialmente.

---

## PARTE XXI — AUDITORÍA Y COMPLIANCE

**Toda recomendación cuantitativa debe poder reconstruirse** (Principio 9). El registro mínimo obligatorio para cada output de cualquier motor:

| Campo | Contenido |
|---|---|
| Datos utilizados | Referencia exacta a las series/valores de entrada (no solo "NAV del fondo X" sino la versión y fecha de extracción específica) |
| Fecha | Momento del cálculo |
| Modelo | Identificador del modelo y versión (ver Parte XIV) |
| Parámetros | Valores exactos usados (ventana, nivel de confianza, τ, δ, bandas, etc.) |
| Resultado | Output numérico completo, no solo el resumen mostrado al usuario |
| Regla activada | Qué regla de negocio de la Decision Library (Parte XVIII) se disparó, si aplica |
| Recomendación | Alternativas presentadas y cuál tenía mayor convicción sugerida |
| Decisión del ejecutivo | Qué eligió el WM/Comité |
| Override | Si difirió de la sugerencia del sistema |
| Justificación | Nota escrita del override, obligatoria cuando existe |
| Fecha de revisión | Próxima fecha programada de reevaluación de esa decisión/modelo |

Este registro no es una función accesoria del sistema — es, junto con el motor de cálculo mismo, uno de los dos componentes de primera clase de la arquitectura (Principio 9). Un output sin este registro asociado no es un output válido del sistema AFI, independientemente de qué tan correcto sea matemáticamente.

---

## PARTE XXII — MATRIZ MAESTRA FINAL

Esta es la matriz cuantitativa principal de AFI. Consolida motor, modelo, fórmula, inputs, parámetros, output, decisión, prioridad, validación, limitaciones y responsable para cada metodología CORE y ADVANCED del stack. (RESEARCH y REJECTED no llevan fila propia aquí — están completamente cubiertos en la Parte III.1; se listan solo si tienen una nota de gobernanza relevante.)

| Motor | Modelo | Fórmula (resumen) | Inputs | Parámetros | Output | Decisión soportada | Prioridad | Validación | Limitaciones | Responsable |
|---|---|---|---|---|---|---|---|---|---|---|
| Performance | TWR | ∏(1+R_t)−1, R_t=(EMV−BMV−CF)/(BMV+CF) | NAV, flujos fechados | Frecuencia de subperíodo | Retorno acumulado/anualizado | D2, D3, D11 | CORE / MVP | Backtest anual vs. fuentes externas | Requiere flujos correctamente clasificados | Motor de Performance |
| Performance | MWR/IRR (XIRR) | Tasa que iguala VP de flujos a cero | Flujos con fecha, valor inicial/final | — | Retorno experimentado por el cliente | Comunicación al cliente | CORE / MVP | Reconciliación con custodio | Sensible al timing de flujos del cliente | Motor de Performance |
| Performance | CAGR / Annualized TWR | (1+TWR)^(1/años)−1 | TWR total, número de años | — | Tasa anualizada comparable | D2 | CORE | — | Menos informativo en periodos cortos (<3 años) | Motor de Performance |
| Performance | Excess Return | TWR portafolio − TWR benchmark | TWR ambos, benchmark elegible | — | Diferencial vs. referencia | D3, D10 | CORE | Depende de gate del Motor de Benchmark | Sin sentido si el benchmark no es elegible | Performance + Benchmark |
| Performance | Brinson-Fachler (atribución) | Descomposición asignación/selección | Pesos y retornos por asset class, benchmark | Jerarquía de agregación | Contribución por decisión | D3, D11 | ADVANCED | Reconciliación con el total (CFA) | Requiere transparencia de holdings | Motor de Performance |
| Riesgo | Volatilidad histórica | σ(retornos) anualizada | Serie de retornos | Ventana 3-5 años | σ anualizada | D8 | CORE / MVP | Backtest, sensitivity a ventana | Trata upside/downside igual | Motor de Riesgo |
| Riesgo | Downside Deviation | σ solo bajo MAR | Retornos, MAR | MAR (0% o rf) | Semivarianza | D8, comunicación cliente | CORE | Consistencia de MAR entre comparaciones | Requiere definición consistente de MAR | Motor de Riesgo |
| Riesgo | Maximum Drawdown | max(peak−trough)/peak | Serie NAV/TWR | Ventana rolling + since inception | % pérdida máxima | D8, calibración tolerancia | CORE | Comparación multi-periodo | No distingue causa; combinar con Recovery Time | Motor de Riesgo |
| Riesgo | Tracking Error | σ(retorno activo) | Retornos vs. benchmark elegible | Mín. 36-60 obs. mensuales | TE anualizado | D3, D10 | CORE | Depende de gate de Benchmark | TE alto puede ser factor bet, no selección | Motor de Riesgo |
| Riesgo | Beta | Regresión lineal vs. benchmark | Retornos portafolio y benchmark | Ventana, frecuencia | Sensibilidad sistemática | D7, D8 | CORE | Estabilidad en distintas ventanas | Variable en el tiempo | Motor de Riesgo |
| Riesgo | VaR histórico | Percentil empírico de pérdidas | Serie de retornos | Confianza 95%/99%, horizonte 1m/1a | Pérdida máxima al percentil | D8 | CORE / MVP | Backtest de excepciones (breaches) | No informa magnitud más allá del percentil | Motor de Riesgo |
| Riesgo | ES histórico | Media de pérdidas > VaR | Serie de retornos | Igual a VaR | Pérdida promedio de cola | D8 | CORE | Sensible a tamaño de muestra | Requiere muestra suficiente | Motor de Riesgo |
| Riesgo | EWMA (volatilidad) | σ ponderada exponencialmente | Retornos | Factor de decaimiento λ | σ más reactiva | Alertas tempranas | ADVANCED | Comparación vs. histórica | Complementa, no reemplaza la σ oficial | Motor de Riesgo |
| Riesgo | Factor Risk básico | Regresión multi-factor | Retornos, índices de factores | Conjunto de factores (equity/tasas/crédito/FX) | Exposición por factor | D7, D11 | ADVANCED | Estabilidad de betas factoriales | Calibración más compleja | Motor de Riesgo |
| Diversificación | Correlation Matrix + Rolling | Correlación de Pearson | Retornos mensuales | Ventana 3-5 años | Matriz de correlación | D7 | CORE | Comparación entre ventanas | Inestable en crisis (sube justo cuando más importa) | Motor de Diversificación |
| Diversificación | HHI | Σ(peso_i)² | Pesos por dimensión | Definición de "bucket" | Índice 0-1 | D7 | CORE / MVP | — | Sensible a cómo se agrupan los buckets | Motor de Diversificación |
| Diversificación | Risk Contribution | Contribución marginal vía covarianzas | Pesos, matriz Σ | — | % de riesgo por activo | D7 | CORE | Consistencia con volatilidad total | Requiere Σ estable | Motor de Diversificación |
| Diversificación | Shrinkage (Ledoit-Wolf) | Combinación de Σ muestral y target estructurado | Retornos históricos | Intensidad de shrinkage | Σ ajustada | Insumo para MVO, BL | ADVANCED | Out-of-sample vs. Σ muestral | Requiere calibrar intensidad | Motor de Diversificación |
| Construcción | MVO robusto | max(w'μ − δ/2·w'Σw) s.a. constraints | CMAs, Σ con shrinkage | Bandas por asset class, límites de concentración | Pesos óptimos | D4, D5 | CORE / MVP | Backtest, sensitivity a μ | Sensible a error de estimación de μ sin constraints fuertes | Motor de Construcción |
| Construcción | Goal-Based Monte Carlo | Simulación de trayectorias | Retornos, cashflows, horizonte | # simulaciones (5.000-20.000) | Probabilidad de éxito de meta | D2, Motor Cliente/Goal | CORE / MVP | Backtest vs. trayectoria real | Depende de calidad de supuestos de retorno | Motor de Cliente/Goal |
| Construcción | Black-Litterman | Π=δΣw; posterior bayesiano con views | Índices, Σ, views documentadas del CIO | τ (0.025-0.05), δ, Ω | Expected returns posteriores | D4 (versión avanzada) | ADVANCED — condicionado (Parte VIII) | Requiere ≥2-3 ciclos de proceso institucionalizado documentado | No se activa sin proceso de views disciplinado | Motor de Construcción + Comité |
| Construcción | Risk Parity / ERC | Igualar contribución de riesgo | Volatilidades por asset class | Target vol | Pesos con riesgo igualado | D4 (comparador) | ADVANCED | Comparación vs. MVO | Rezagado en bull markets de equity | Motor de Construcción |
| Liquidez | Liquidity Coverage Ratio | Activos líquidos disponibles / obligaciones por bucket | Calendario de flujos, liquidez por vehículo | Horizontes (0-3m, 3-12m, >12m) | LCR por bucket | D6, D9 | CORE / MVP | Backtest vs. necesidades reales | Depende de calidad de estimación de flujos del cliente | Motor de Liquidez |
| Liquidez | Liquidity Ladder | Matching de vencimientos vs. necesidades | Flujos esperados, ventanas de redención | — | Escalera de cobertura | D6, D9 | CORE | — | Requiere clasificación correcta de cada vehículo | Motor de Liquidez |
| Alternativos | TVPI/DPI/RVPI/IRR | Múltiplos sobre capital pagado; TIR sobre cashflows | Cashflows completos por fondo | — | Múltiplos y tasa de retorno | D3, D11 (para vehículos privados) | CORE (si hay cashflows) | Comparación con vintage similar | Requiere cashflows completos, no siempre disponibles | Motor de Alternativos |
| Escenarios | Historical Simulation | Aplicar shocks observados al portafolio actual | Movimientos históricos de índices/tasas | Episodio elegido (2008, COVID, etc.) | Impacto proyectado | D13 | CORE | Comparación entre episodios | La próxima crisis no es idéntica a la anterior | Motor de Escenarios |
| Escenarios | Hypothetical Stress | Shocks definidos por Comité | Definición de shock, exposiciones actuales | Magnitud del shock (p. ej. +200bps) | Impacto proyectado | D13 | CORE | Revisión de plausibilidad por el Comité | Depende del juicio macro del Comité | Motor de Escenarios |
| Escenarios | Monte Carlo / Block Bootstrap | Simulación de trayectorias con dependencia preservada | Retornos históricos, cashflows | # simulaciones, tamaño de bloque | Distribución de resultados futuros | D2, Motor Cliente/Goal | CORE | Backtest vs. trayectoria real | Depende de la representatividad del histórico usado | Motor de Escenarios |
| Benchmark | AFI Benchmark Eligibility Framework | Verificación de 8 dimensiones (regla, no fórmula) | Definición de universo, riesgo, moneda, liquidez, horizonte, costos, objetivo, restricciones | Umbrales de comparabilidad por dimensión | Estado elegible/no-elegible | D10 | CORE / MVP | Revisión anual de la definición | Puede no existir benchmark razonablemente cercano | Motor de Benchmark |
| Governance | Explicación por reglas + plantillas | Regla fija → plantilla parametrizada | Resultado de cualquier motor | Umbrales de clasificación versionados | Narrativa reproducible | Todas (capa transversal) | CORE | Reproducibilidad exacta ante mismos inputs | Menos "natural" que texto libre — trade-off aceptado | Todos los motores |

---

## PARTE XXIII — DECISIONES METODOLÓGICAS PENDIENTES

Todo lo que no puede resolverse responsablemente con los cuatro volúmenes consolidados. Ninguno de estos vacíos se rellenó con una suposición — se declaran explícitamente.

### Pendiente 1 — Activación de Black-Litterman
**Clasificación:** Política AFI / Investment Committee.
**Qué falta definir:** si el Comité de Inversiones de AFI puede sostener, en la práctica y no solo en el diseño, el proceso Evidencia→View→Convicción→BL descrito en la Parte VIII. Ningún volumen consolidado aporta evidencia operativa de que este proceso ya funcione en AFI.
**Quién debe resolverlo:** Investment Committee, con al menos 2-3 ciclos de documentación de views antes de activar BL en producción.

### Pendiente 2 — Umbral exacto de "gap significativo" en Missing Data
**Clasificación:** Metodológico / Datos.
**Qué falta definir:** la Parte XVII establece el patrón Detection→Action→Warning→Fallback/Block para datos faltantes, pero ningún volumen consolidado especifica el umbral numérico exacto (¿cuántos días consecutivos sin NAV constituyen un "gap significativo" que bloquea el modelo vs. uno menor que permite imputación prudente?). Este umbral depende de la frecuencia nativa de cada tipo de vehículo y no debe fijarse de forma genérica sin conocer el universo real de datos de AFI.
**Quién debe resolverlo:** equipo de datos de AFI, calibrado contra el universo real de vehículos una vez que exista.

### Pendiente 3 — Definición operacional de "Effective Number of Bets"
**Clasificación:** Metodológico.
**Qué falta definir:** la Parte VI declara explícitamente que la fórmula propuesta (inverso de la suma de cuadrados de contribuciones al riesgo) es una inferencia metodológica razonable, no un hallazgo respaldado por un paper específico en las fuentes consolidadas. Antes de exponerla como métrica CORE al Comité, debería validarse contra al menos una fuente académica adicional o aceptarse explícitamente como convención propia de AFI.
**Quién debe resolverlo:** Investment Committee, como decisión de convención metodológica propia.

### Pendiente 4 — Umbrales exactos de triggers de rebalanceo y deterioro de gestores
**Clasificación:** Política AFI.
**Qué falta definir:** las bandas de rebalanceo (Parte XIII) y los triggers de deterioro de gestores (Decision Library, D11) se describen estructuralmente, pero ningún volumen fija los números exactos (¿banda de ±3% o ±5%? ¿cuántos trimestres consecutivos de alpha negativo activan Watchlist?). Fijar estos números sin el contexto de riesgo real de la cartera de clientes de AFI sería inventar precisión donde no existe evidencia.
**Quién debe resolverlo:** Investment Committee, calibrado contra el perfil real de riesgo de los clientes de AFI.

### Pendiente 5 — Capacidad tecnológica real vs. diseño conceptual
**Clasificación:** Tecnológico.
**Qué falta definir:** este documento es metodología, no arquitectura de software (por mandato explícito). La Parte XXIV traduce cada motor a especificación conceptual, pero no evalúa si la infraestructura de datos actual de AFI (fuentes, APIs de custodios, calidad histórica disponible) soporta la implementación tal como está diseñada. Ningún volumen consolidado incluye un audit de la infraestructura actual de AFI.
**Quién debe resolverlo:** equipo técnico de AFI, como paso previo obligatorio a cualquier desarrollo de software derivado de este documento.

### Pendiente 6 — Alcance exacto de "cliente" para efectos de ESG/exclusiones
**Clasificación:** Cliente / Política AFI.
**Qué falta definir:** el Volumen II menciona filtros ESG y exclusiones temáticas como parte del due diligence de gestores, pero ningún volumen consolidado define si AFI aplica una política ESG institucional uniforme o si esto es enteramente definido caso a caso por cada IPS de cliente. La Parte XV (Parameter Governance) asume que existe una categoría de parámetro para esto, pero no resuelve a cuál pertenece.
**Quién debe resolverlo:** Investment Committee — es una decisión de posicionamiento institucional, no una decisión técnica.

---

## PARTE XXIV — TRADUCCIÓN FUTURA A SOFTWARE

Sin escribir código: Module, Inputs, Calculation, Parameters, Outputs, Rules, Alerts, Visualization, Audit Trail, Human Override, Dependencies, Error Handling — para cada motor. Este es el input directo para la futura **AFI Expert System Functional Specification (ESFS)**.

### AFI.Performance.Engine
- **Inputs:** NAV, flujos, benchmarks elegibles, metadatos de jerarquía.
- **Calculation:** TWR, MWR/IRR, CAGR, Excess Return (Parte IV); Brinson-Fachler (ADVANCED).
- **Parameters:** ventana de subperíodo, frecuencia de consolidación.
- **Outputs:** cuadros multi-periodo, atribución jerárquica.
- **Rules:** frecuencia de comparación = frecuencia nativa más baja común entre vehículos comparados.
- **Alerts:** underperformance significativa sostenida vs. benchmark elegible.
- **Visualization:** dashboard WM (por cliente), dashboard Comité (agregado), vista cliente simplificada.
- **Audit Trail:** ver estructura de registro obligatoria, Parte XXI.
- **Human Override:** N/A directo — este motor informa, no decide; alimenta D2, D3, D11.
- **Dependencies:** AFI.Benchmark.Engine (gate de elegibilidad), AFI.Construction.Engine (separar asignación de selección).
- **Error Handling:** estado `insufficient_data` si flujos no están correctamente fechados/clasificados (Principio 8).

### AFI.Risk.Engine
- **Inputs:** posiciones, curvas de mercado, matriz de covarianzas con shrinkage.
- **Calculation:** volatilidad, downside deviation, max drawdown, TE, beta, VaR/ES históricos (CORE); EWMA, factor risk (ADVANCED) — Parte V.
- **Parameters:** ventana (3-5 años), niveles de confianza (95%/99%), horizonte (1m/1a).
- **Outputs:** tableros de riesgo por dimensión, panel de riesgo de cola.
- **Rules:** violación de límite de perfil → alerta; sin ajuste automático de portafolio.
- **Alerts:** exceso vs. límites IPS, concentraciones sobre umbral, incrementos bruscos de VaR.
- **Visualization:** mapas de calor de contribución a riesgo.
- **Audit Trail:** parámetros y ventana usados en cada cálculo, versionados.
- **Human Override:** D8 — el Comité aprueba excepciones documentadas.
- **Dependencies:** AFI.Scenario.Engine (shocks), AFI.Liquidity.Engine (riesgo de liquidez).
- **Error Handling:** `insufficient_data` si la muestra es menor al mínimo definido por modelo (p. ej. <36 obs. mensuales para TE).

### AFI.Diversification.Engine
- **Inputs:** matrices de correlación/covarianza, pesos actuales y objetivo.
- **Calculation:** HHI, risk contribution, correlation matrix (CORE); shrinkage, cluster analysis (ADVANCED) — Parte VI.
- **Parameters:** definición de "buckets" para HHI, ventana de correlación rolling.
- **Outputs:** índices de diversificación, recomendaciones de cambios marginales.
- **Rules:** HHI o risk contribution sobre umbral institucional por dimensión → flag de concentración.
- **Alerts:** concentración detectada, especificando la dimensión (D7).
- **Visualization:** dendrograma de clusters (ADVANCED), mapa de contribución al riesgo.
- **Audit Trail:** matriz de covarianzas usada y su fecha de estimación.
- **Human Override:** D7 — el WM decide si la concentración es aceptable dado el objetivo del cliente.
- **Dependencies:** AFI.Risk.Engine (matriz de covarianzas compartida).
- **Error Handling:** `insufficient_data` si la ventana de correlación no tiene suficientes observaciones.

### AFI.Construction.Engine
- **Inputs:** IPS, CMAs, inventario de productos con costos/liquidez/capacidad.
- **Calculation:** MVO robusto, Goal-Based Monte Carlo (CORE); Black-Litterman, Risk Parity (ADVANCED, condicionado) — Parte VII-VIII.
- **Parameters:** bandas por asset class, límites de concentración, τ/δ/Ω para BL.
- **Outputs:** propuesta de portafolio objetivo, métricas esperadas, sensibilidades.
- **Rules:** BL no se ejecuta sin views documentadas y aprobadas por Comité (Parte VIII).
- **Alerts:** N/A directo — este motor propone, no monitorea en curso.
- **Visualization:** frontera eficiente, comparación de portafolios candidatos.
- **Audit Trail:** CMAs y constraints usados en cada propuesta, versionados.
- **Human Override:** D4, D5 — el Comité aprueba la propuesta final.
- **Dependencies:** AFI.Risk.Engine, AFI.Diversification.Engine, AFI.Liquidity.Engine, AFI.Benchmark.Engine.
- **Error Handling:** `insufficient_data` si el IPS del cliente no está completo/vigente.

### AFI.Liquidity.Engine
- **Inputs:** calendario de flujos esperados, estructura de liquidez por vehículo.
- **Calculation:** LCR por bucket, Liquidity Ladder (CORE); stress liquidity (ADVANCED) — Parte IX.
- **Parameters:** horizontes (0-3m, 3-12m, >12m).
- **Outputs:** mapas de liquidez, alertas de déficit.
- **Rules:** peso máximo en ilíquidos como función del life balance sheet completo (Principio 2, Volumen I).
- **Alerts:** déficit proyectado bajo escenario de estrés (D6, D9).
- **Visualization:** escalera de vencimientos.
- **Audit Trail:** supuestos de cash flow usados por vehículo.
- **Human Override:** D6 — el WM decide timing y composición de la reasignación.
- **Dependencies:** AFI.Alternatives.Engine (curvas de capital calls), AFI.Scenario.Engine (estrés conjunto).
- **Error Handling:** `insufficient_data` si un vehículo privado no reporta historial de cash flow suficiente.

### AFI.Alternatives.Engine
- **Inputs:** cashflows históricos por fondo/vintage, NAV reportado.
- **Calculation:** TVPI/DPI/RVPI/IRR (CORE); PME/Direct Alpha, pacing (ADVANCED) — Parte X.
- **Parameters:** horizonte de vintage, curva de J-curve asumida por estrategia.
- **Outputs:** perfil de cash flow proyectado, contribución a retorno esperado.
- **Rules:** NAV privado nunca se trata como equivalente a precio de mercado (Parte X).
- **Alerts:** desviación significativa del cash flow proyectado vs. realizado.
- **Visualization:** curva J-curve real vs. modelo.
- **Audit Trail:** fuente y fecha de cada cashflow usado.
- **Human Override:** D14 (aprobación de nuevos vehículos) vía Comité.
- **Dependencies:** alimenta a AFI.Liquidity.Engine y AFI.Risk.Engine.
- **Error Handling:** `insufficient_data` si el fondo no reporta cashflows completos — no se calculan métricas parciales sin advertencia.

### AFI.Scenario.Engine
- **Inputs:** librería de escenarios históricos e hipotéticos, mapeo a factores de riesgo.
- **Calculation:** Historical Simulation, Hypothetical Stress, Monte Carlo/Block Bootstrap (CORE); Reverse Stress Testing (ADVANCED) — Parte XI.
- **Parameters:** episodio histórico seleccionado, magnitud de shock hipotético, # simulaciones.
- **Outputs:** impacto proyectado en retorno/riesgo/liquidez/concentración/objetivos (las cinco dimensiones de Parte XI).
- **Rules:** todo escenario reporta impacto en las cinco dimensiones, no solo retorno.
- **Alerts:** escenario que rompe límites institucionales (alimenta Reverse Stress Testing).
- **Visualization:** distribución de resultados, comparación entre escenarios.
- **Audit Trail:** definición exacta del escenario ejecutado, versionada.
- **Human Override:** D13 — rebalanceo extraordinario requiere aprobación explícita del Comité.
- **Dependencies:** AFI.Risk.Engine, AFI.Liquidity.Engine, AFI.Construction.Engine.
- **Error Handling:** N/A típico — los escenarios son hipotéticos por diseño, no dependen de completitud de datos en el mismo sentido que otros motores.

### AFI.Monitoring.Engine
- **Inputs:** resultados consolidados de todos los demás motores, triggers configurados.
- **Calculation:** orquestación de reglas — no introduce modelos matemáticos propios (Parte II.8).
- **Parameters:** umbrales de cada trigger, heredados de los motores fuente.
- **Outputs:** lista priorizada de cuentas, heatmap de desviaciones, watchlist.
- **Rules:** combinación de triggers cuantitativos + cualitativos → escalamiento (D11).
- **Alerts:** consolidación de todas las alertas de los demás motores.
- **Visualization:** panel "book of business".
- **Audit Trail:** hereda el de cada motor fuente; no duplica el registro.
- **Human Override:** N/A directo — este motor prioriza, el WM actúa sobre lo priorizado.
- **Dependencies:** todos los demás motores.
- **Error Handling:** si un motor fuente está en `insufficient_data`, ese componente se excluye de la priorización con nota explícita, no se omite silenciosamente.

### AFI.Benchmark.Engine
- **Inputs:** definición de universo, riesgo, moneda, liquidez, horizonte, costos, objetivo, restricciones — del portafolio y del benchmark candidato.
- **Calculation:** AFI Benchmark Eligibility Framework (Parte XII) — regla de verificación, no modelo matemático.
- **Parameters:** umbrales de comparabilidad por dimensión.
- **Outputs:** estado elegible/no-elegible/parcial.
- **Rules:** benchmark no elegible → no se genera ranking (Principio 7).
- **Alerts:** intento de comparación contra benchmark no verificado.
- **Visualization:** ficha de elegibilidad por dimensión.
- **Audit Trail:** verificación de las 8 dimensiones, registrada y fechada.
- **Human Override:** D10 — el Comité puede documentar una excepción acotada.
- **Dependencies:** consumido por AFI.Performance.Engine y AFI.Risk.Engine.
- **Error Handling:** si falta información para verificar una dimensión, esa dimensión se marca como "no verificable" — no se asume comparabilidad por defecto.

### AFI.ClientGoal.Engine
- **Inputs:** IPS, life balance sheet, resultados de Monte Carlo goal-based.
- **Calculation:** comparte metodología de Monte Carlo/Bootstrap con AFI.Scenario.Engine, aplicada a la probabilidad de meta específica.
- **Parameters:** horizonte y metas definidas en el IPS.
- **Outputs:** probabilidad de éxito por meta, dashboard cliente simplificado.
- **Rules:** ninguna meta se evalúa sin un IPS vigente como input.
- **Alerts:** probabilidad de éxito cae bajo umbral institucional.
- **Visualization:** dashboard cliente (probabilidad de meta en lenguaje simple).
- **Audit Trail:** versión del IPS usada en cada cálculo de probabilidad.
- **Human Override:** D2 — revisión de IPS es siempre decisión de asesor + cliente, validada por Comité.
- **Dependencies:** AFI.Construction.Engine, AFI.Scenario.Engine.
- **Error Handling:** `insufficient_data` si el IPS no está vigente o no tiene metas cuantificables.

---

## ROADMAP DE EVOLUCIÓN

Secuencia de implementación basada en dependencias reales entre motores (no en orden de aparición en este documento) y en la prioridad asignada en la Parte II. Cada fase requiere que la anterior esté operativa antes de comenzar, porque los motores de fases posteriores consumen outputs de los de fases anteriores.

### Fase 1 — Núcleo fiduciario mínimo
**Motores:** AFI.Performance.Engine, AFI.Risk.Engine (submétricas CORE), AFI.Benchmark.Engine.
**Por qué primero:** son los tres motores marcados 🔴 Crítica/MVP obligatorio en la Parte II, y Performance/Riesgo no pueden reportarse de forma responsable sin que Benchmark ya esté funcionando como gate — de lo contrario cualquier comparación temprana arriesga ser engañosa (Principio 7).
**Entregable de fase:** reporting de performance y riesgo por cliente, con comparaciones solo contra benchmarks verificados como elegibles.

### Fase 2 — Construcción y diversificación
**Motores:** AFI.Construction.Engine (MVO robusto + Goal-Based Monte Carlo), AFI.Diversification.Engine.
**Por qué en esta fase:** ambos dependen de que exista ya una matriz de covarianzas y un motor de riesgo estable (Fase 1) para operar con confianza.
**Entregable de fase:** capacidad de proponer portafolios objetivo y detectar concentraciones ocultas.

### Fase 3 — Liquidez y monitoreo consolidado
**Motores:** AFI.Liquidity.Engine, AFI.Monitoring.Engine.
**Por qué en esta fase:** Monitoring requiere que ya existan al menos dos o tres motores fuente generando triggers (Fases 1-2) para que la consolidación tenga sentido; Liquidity puede desarrollarse en paralelo pero su integración completa depende de tener el Motor de Alternativos (Fase 4) para el manejo de capital calls.
**Entregable de fase:** book of business priorizado; primera versión de mapas de liquidez (sin integración completa de alternativos aún).

### Fase 4 — Alternativos y escenarios
**Motores:** AFI.Alternatives.Engine, AFI.Scenario.Engine.
**Por qué en esta fase:** requieren que Liquidez (Fase 3) ya exista para consumir sus curvas de cash flow proyectado, y que Riesgo (Fase 1) esté maduro para traducir exposición a alternativos en términos de riesgo total.
**Entregable de fase:** integración completa de vehículos privados al reporting; capacidad de stress testing sobre el portafolio total.

### Fase 5 — Cliente/Goal Intelligence
**Motores:** AFI.ClientGoal.Engine.
**Por qué al final:** consume outputs de Construction y Scenario (Fases 2 y 4) y requiere que exista un proceso de IPS suficientemente maduro y estructurado en AFI — es tanto una dependencia técnica como organizacional (ver Pendiente 5, Parte XXIII).
**Entregable de fase:** dashboard de probabilidad de metas por cliente, cerrando el círculo hacia el Principio 1.

### Nota explícita sobre lo que este roadmap NO incluye

No hay una fase de "explicabilidad avanzada vía SHAP/LIME" ni una fase de "Auto-Commentary". El roadmap del Volumen III las incluía como Fase 3 y Fase 4 respectivamente; se eliminaron íntegramente al resolver la contradicción de la Parte XIX. La capa de explicación por reglas y plantillas (también Parte XIX) no es una fase separada — se construye *junto con* cada motor desde la Fase 1, porque un motor sin su capa de explicación determinística no es un motor completo según el Principio 3.

Black-Litterman (Parte VIII) no tiene una fase asignada en este roadmap porque su activación depende de una condición organizacional, no de una secuencia técnica — se activa cuando el Pendiente 1 (Parte XXIII) se resuelva, independientemente de en qué fase técnica se encuentre el resto del sistema.

---

## CIERRE

Volviendo a la pregunta que este documento debía responder: *si mañana AFI quisiera comenzar a construir su motor cuantitativo, ¿qué modelos debe implementar, qué datos necesita, cómo debe calcularlos, qué reglas debe aplicar, qué resultados debe mostrar y qué decisiones debe dejar en manos del Wealth Manager?*

La respuesta está distribuida a lo largo de las 24 partes de este documento, pero se puede resumir así: **AFI debe implementar diez motores especializados, empezando por los tres del núcleo fiduciario mínimo (Fase 1), cada uno con su propia capa de explicación determinística incorporada desde el diseño — no añadida después —, alimentados por un Data Dictionary con reglas de calidad de datos explícitas, y organizados de forma que ninguna salida del sistema llegue al cliente sin pasar antes por la decisión de un Wealth Manager.**

Donde la respuesta honesta era "todavía no sabemos", este documento no la inventó — la Parte XXIII registra seis decisiones pendientes específicas, cada una con quién debe resolverla y qué evidencia falta. Ese es, junto con la matriz maestra de la Parte XXII, el entregable más directamente accionable de esta consolidación: no solo qué construir, sino también qué **no** construir todavía.

Este documento es la base metodológica que alimentará la **AFI Expert System Functional Specification (ESFS)** y, posteriormente, su implementación en Claude Code.
