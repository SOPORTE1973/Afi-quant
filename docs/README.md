# Documentos fuente

El código implementa estos documentos. Cuando el código y la fuente discrepan, manda la fuente y se corrige el código.

| Clave en el código | Documento | Rol |
|---|---|---|
| `[ESFS x.y]` | [ESFS-01 — Arquitectura funcional del sistema experto](ESFS-01_Arquitectura_Funcional.md) | Qué módulos existen, qué datos necesita cada uno, en qué orden se construyen y qué falta decidir (OPEN ISSUES ESFS-xx) |
| `[QM Parte X]` | [AFI Quantitative Methodology v1.0](AFI_Quantitative_Methodology_v1.0.md) | Los 10 motores, sus modelos y su clasificación CORE / ADVANCED / RESEARCH / REJECTED |
| `[DF x.y]` | [AFI Decision Framework v1.1](AFI_Decision_Framework_v1.1.md) | **Versión vigente (congelada según ESFS-01).** Tres capas: motores, Decision Orchestrator y Recommendation Layer; niveles de autonomía |
| `[DF v1.0 Parte X]` | [AFI Decision Framework v1.0](AFI_Decision_Framework_v1.0.md) | Documento base: los 11 Decision Flows, el caso de uso (cliente ficticio) y las matrices. v1.1 lo reorganiza sin cambiar la secuencia de ningún flujo |
| `[Vol I]` | [AFI Methodology Volumen I — First Principles](AFI_Methodology_Vol_I_First_Principles.md) | Principios de diseño del Multi Family Office |
| `[Vol II]` | [AFI Methodology Volumen II](AFI_Methodology_Vol_II.pdf) | Selección y convicción sobre gestores y vehículos |
| `[Vol III-B]` | [AFI Methodology Volumen III-B](AFI_Methodology_Vol_III-B.pdf) | Cierre de las decisiones matemáticas y estadísticas del Volumen III |

Jerarquía: ESFS-01 declara como autoridad de origen el Decision Framework v1.1 (congelado), la Quantitative Methodology v1.0 (preservada) y los Volúmenes I, II, III y III-B.

Falta en esta carpeta el **Volumen III** (el III-B lo referencia). Hubo además un borrador de v1.1 con formato de "patch de auditoría" sobre v1.0; se reemplazó por la versión consolidada que está aquí y no se incluye.
