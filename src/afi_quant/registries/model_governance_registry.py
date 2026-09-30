"""
Model Governance Registry (M23).

Clasificación CORE / ADVANCED / RESEARCH / REJECTED de cada modelo
cuantitativo, con responsable institucional y estado de validación.
Exigido por ESFS-01 Parte 9.10 y AFI Quantitative Methodology Parte XIV.

Los datos de este seed se tomaron de:
  - AFI_Quantitative_Methodology_v1.0, Parte III.1 (matriz de clasificación)
  - AFI_Quantitative_Methodology_v1.0, Parte XXII (Matriz Maestra Final)

y reproducen exactamente el registro ya validado con AfiTrading
(M23_Model_Governance_Registry.xlsx). Donde la fuente no da un
responsable institucional explícito, el campo queda vacío y marcado
como OPEN — no se inventa un responsable.

Los campos operativos (fecha de última validación, resultados de
backtesting/sensitivity/parameter stability/out-of-sample) no se
completan aquí: los llena el Comité de Model Risk a medida que corren
(ver Parte XIV — mínimo anual para todo modelo CORE y ADVANCED).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ModelClassification(str, Enum):
    CORE = "CORE"
    ADVANCED = "ADVANCED"
    ADVANCED_CONDICIONADO = "ADVANCED — condicionado"
    RESEARCH = "RESEARCH"
    REJECTED = "REJECTED"


VALIDATES_PERIODICALLY = {
    ModelClassification.CORE,
    ModelClassification.ADVANCED,
    ModelClassification.ADVANCED_CONDICIONADO,
}


@dataclass
class ValidationRecord:
    """Completado operativamente por el Comité de Model Risk — no se prellena."""

    last_validated: date | None = None
    backtesting_result: str | None = None
    sensitivity_result: str | None = None
    parameter_stability_result: str | None = None
    out_of_sample_result: str | None = None
    next_review: date | None = None


@dataclass
class ModelEntry:
    motor: str
    modelo: str
    clasificacion: ModelClassification
    formula_resumen: str
    decision_soportada: str
    responsable_institucional: str  # "" si no consta explícito en la fuente (OPEN)
    limitaciones: str
    fuente: str
    notas: str = ""
    validation: ValidationRecord = field(default_factory=ValidationRecord)

    @property
    def requires_periodic_validation(self) -> bool:
        return self.clasificacion in VALIDATES_PERIODICALLY

    @property
    def is_open_responsable(self) -> bool:
        return self.requires_periodic_validation and not self.responsable_institucional


# fmt: off
_C = ModelClassification

MODEL_GOVERNANCE_REGISTRY: list[ModelEntry] = [
    # Performance
    ModelEntry("Performance", "TWR (geométrico)", _C.CORE,
               "∏(1+R_t)−1 ; R_t=(EMV−BMV−CF)/(BMV+CF)", "D2, D3, D11",
               "Motor de Performance", "Requiere flujos correctamente clasificados",
               "[QM Parte XXII]"),
    ModelEntry("Performance", "MWR / IRR (XIRR)", _C.CORE,
               "Tasa que iguala VP de flujos a cero", "Comunicación al cliente",
               "Motor de Performance", "Sensible al timing de flujos del cliente",
               "[QM Parte XXII]"),
    ModelEntry("Performance", "CAGR / Annualized TWR", _C.CORE,
               "(1+TWR)^(1/años)−1", "D2",
               "Motor de Performance", "Menos informativo en periodos cortos (<3 años)",
               "[QM Parte XXII]", "Sin validación propia — deriva de TWR"),
    ModelEntry("Performance", "Excess Return", _C.CORE,
               "TWR portafolio − TWR benchmark", "D3, D10",
               "Performance + Benchmark", "Sin sentido si el benchmark no es elegible",
               "[QM Parte XXII]", "Depende del gate del Motor de Benchmark"),
    ModelEntry("Performance", "Brinson-Fachler (atribución)", _C.ADVANCED,
               "Descomposición asignación/selección", "D3, D11",
               "Motor de Performance", "Requiere transparencia de holdings",
               "[QM Parte XXII]"),
    ModelEntry("Performance", "Factor Attribution", _C.ADVANCED,
               "Contribución por factor sobre exposiciones factoriales",
               "Verificar consistencia con proceso declarado del gestor",
               "", "Requiere modelo de factores calibrado",
               "[QM Parte III.1]",
               "OPEN: sin responsable explícito en Parte XXII — sin fila en la Matriz "
               "Maestra Final, verificar con Comité de Model Risk"),
    # Riesgo
    ModelEntry("Riesgo", "Volatilidad histórica", _C.CORE,
               "σ(retornos) anualizada", "D8",
               "Motor de Riesgo", "Trata upside/downside igual",
               "[QM Parte XXII]", "Ventana 3-5 años"),
    ModelEntry("Riesgo", "Downside Deviation", _C.CORE,
               "σ solo bajo MAR", "D8, comunicación cliente",
               "Motor de Riesgo", "Requiere definición consistente de MAR",
               "[QM Parte XXII]"),
    ModelEntry("Riesgo", "Maximum Drawdown", _C.CORE,
               "max(peak−trough)/peak", "D8, calibración tolerancia",
               "Motor de Riesgo", "No distingue causa; combinar con Recovery Time",
               "[QM Parte XXII]"),
    ModelEntry("Riesgo", "Tracking Error", _C.CORE,
               "σ(retorno activo)", "D3, D10",
               "Motor de Riesgo", "TE alto puede ser factor bet, no selección",
               "[QM Parte XXII]", "Mín. 36-60 obs. mensuales; depende del gate de Benchmark"),
    ModelEntry("Riesgo", "Beta", _C.CORE,
               "Regresión lineal vs. benchmark", "D7, D8",
               "Motor de Riesgo", "Variable en el tiempo",
               "[QM Parte XXII]"),
    ModelEntry("Riesgo", "VaR histórico", _C.CORE,
               "Percentil empírico de pérdidas", "D8",
               "Motor de Riesgo", "No informa magnitud más allá del percentil",
               "[QM Parte XXII]", "Confianza 95% cliente / 99% Comité; horizonte 1m y 1a"),
    ModelEntry("Riesgo", "Expected Shortfall histórico", _C.CORE,
               "Media de pérdidas > VaR", "D8",
               "Motor de Riesgo", "Requiere muestra suficiente",
               "[QM Parte XXII]"),
    ModelEntry("Riesgo", "EWMA (volatilidad)", _C.ADVANCED,
               "σ ponderada exponencialmente", "Alertas tempranas",
               "Motor de Riesgo", "Complementa, no reemplaza la σ oficial",
               "[QM Parte XXII]", "Requiere calibrar factor de decaimiento λ"),
    ModelEntry("Riesgo", "Factor Risk básico", _C.ADVANCED,
               "Regresión multi-factor (equity/tasas/crédito/FX)", "D7, D11",
               "Motor de Riesgo", "Calibración más compleja que métricas CORE",
               "[QM Parte XXII]", "Estabilidad de betas factoriales"),
    ModelEntry("Riesgo", "GARCH", _C.RESEARCH,
               "Volatilidad condicional, clustering", "No recomendado para uso rutinario",
               "", "Impracticable con NAV mensual/trimestral de la mayoría del universo AFI",
               "[QM Parte III.0 Rev.3, III.1]",
               "Confirmado en RESEARCH; no requiere validación periódica mientras no se active"),
    # Diversificación
    ModelEntry("Diversificación", "Correlation Matrix + Rolling", _C.CORE,
               "Correlación de Pearson", "D7",
               "Motor de Diversificación", "Inestable en crisis (sube justo cuando más importa)",
               "[QM Parte XXII]", "Ventana 3-5 años"),
    ModelEntry("Diversificación", "HHI (Herfindahl-Hirschman)", _C.CORE,
               "Σ(peso_i)²", "D7",
               "Motor de Diversificación", "Sensible a cómo se agrupan los buckets",
               "[QM Parte XXII]"),
    ModelEntry("Diversificación", "Risk Contribution / Marginal", _C.CORE,
               "Contribución marginal vía covarianzas", "D7",
               "Motor de Diversificación", "Requiere matriz de covarianzas (Σ) estable",
               "[QM Parte XXII]"),
    ModelEntry("Diversificación", "Shrinkage (Ledoit-Wolf)", _C.ADVANCED,
               "Combinación de Σ muestral y target estructurado", "Insumo para MVO, BL",
               "Motor de Diversificación", "Requiere calibrar intensidad de shrinkage",
               "[QM Parte XXII]"),
    ModelEntry("Diversificación", "Cluster Analysis / HRP diagnóstico", _C.ADVANCED,
               "Dendrograma/clusters sobre matriz de correlación",
               "Visualizar concentraciones ocultas", "",
               "Promovido desde RESEARCH (III.0 Rev.4) — lente de análisis, no decisión "
               "de asignación de capital",
               "[QM Parte III.0 Rev.4, III.1]",
               "OPEN: sin fila propia en Parte XXII, responsable no explícito"),
    ModelEntry("Diversificación", "HRP como constructor de portafolio", _C.RESEARCH,
               "Pesos óptimos vía jerarquía de covarianzas",
               "No recomendado como motor principal aún", "",
               "Promete mejor diversificación out-of-sample, sin prueba suficiente en "
               "contexto AFI",
               "[QM Parte III.0 Rev.4, III.1]",
               "Distinto de HRP diagnóstico (ese sí es ADVANCED)"),
    # Construcción
    ModelEntry("Construcción", "MVO robusto (shrinkage + constraints)", _C.CORE,
               "max(w'μ − δ/2·w'Σw) s.a. constraints", "D4, D5",
               "Motor de Construcción", "Sensible a error de estimación de μ sin constraints fuertes",
               "[QM Parte XXII]", "Bandas por asset class, límites de concentración"),
    ModelEntry("Construcción", "Goal-Based Monte Carlo", _C.CORE,
               "Simulación de trayectorias", "D2, Motor Cliente/Goal",
               "Motor de Cliente/Goal", "Depende de calidad de supuestos de retorno",
               "[QM Parte XXII]", "5.000-20.000 simulaciones"),
    ModelEntry("Construcción", "Black-Litterman", _C.ADVANCED_CONDICIONADO,
               "Π=δΣw; posterior bayesiano con views", "D4 (versión avanzada)",
               "Motor de Construcción + Comité", "No se activa sin proceso de views disciplinado",
               "[QM Parte XXII, III.0 Rev.5]",
               "CONDICIÓN DE ENTRADA (Parte VIII): solo promovible si el Comité sostiene "
               "el proceso Evidencia→View→Convicción con 2-3 ciclos documentados. No "
               "proyecta automáticamente a CORE. τ 0.025-0.05, δ, Ω"),
    ModelEntry("Construcción", "Risk Parity / ERC", _C.ADVANCED,
               "Igualar contribución de riesgo", "D4 (comparador)",
               "Motor de Construcción", "Rezagado en bull markets de equity",
               "[QM Parte XXII]", "Sensible a estimación de volatilidad"),
    ModelEntry("Construcción", "Bayesian Optimization (general)", _C.RESEARCH,
               "—", "No recomendado, poco interpretable",
               "", "Complejidad no justificada para WM estándar",
               "[QM Parte III.1]"),
    ModelEntry("Construcción", "Constraints complejos no interpretables", _C.REJECTED,
               "—", "—", "", "Soluciones ininterpretables para el cliente",
               "[QM Parte III.1]"),
    # Liquidez
    ModelEntry("Liquidez", "Liquidity Coverage Ratio", _C.CORE,
               "Activos líquidos disponibles / obligaciones por bucket", "D6, D9",
               "Motor de Liquidez", "Depende de calidad de estimación de flujos del cliente",
               "[QM Parte XXII]", "Horizontes 0-3m, 3-12m, >12m"),
    ModelEntry("Liquidez", "Liquidity Ladder", _C.CORE,
               "Matching de vencimientos vs. necesidades", "D6, D9",
               "Motor de Liquidez", "Requiere clasificación correcta de cada vehículo",
               "[QM Parte XXII]"),
    ModelEntry("Liquidez", "Stress Liquidity (mercado + flujos)", _C.ADVANCED,
               "Déficit proyectado bajo estrés conjunto", "Evitar ventas forzadas en crisis",
               "", "Depende de la calidad del Motor de Escenarios",
               "[QM Parte III.1]",
               "OPEN: sin fila propia en Parte XXII, responsable no explícito"),
    # Alternativos
    ModelEntry("Alternativos", "TVPI / DPI / RVPI / IRR", _C.CORE,
               "Múltiplos sobre capital pagado; TIR sobre cashflows",
               "D3, D11 (vehículos privados)",
               "Motor de Alternativos", "Requiere cashflows completos, no siempre disponibles",
               "[QM Parte XXII]", "Condicionado a existencia de cashflows completos por fondo"),
    ModelEntry("Alternativos", "PME / Direct Alpha", _C.ADVANCED,
               "Alpha ajustado por timing vs. índice público",
               "Comparar PE vs. alternativa líquida", "",
               "Requiere índice público comparable", "[QM Parte III.1]",
               "OPEN: sin fila propia en Parte XXII, responsable no explícito"),
    ModelEntry("Alternativos", "Pacing / Simulación de NAV", _C.ADVANCED,
               "Cash flow proyectado a partir de curvas históricas y vintage",
               "Planificar ritmo de commitments", "",
               "Depende de supuestos de J-curve por estrategia", "[QM Parte III.1]",
               "OPEN: sin fila propia en Parte XXII, responsable no explícito"),
    # Escenarios
    ModelEntry("Escenarios", "Historical Simulation", _C.CORE,
               "Aplicar shocks observados al portafolio actual", "D13",
               "Motor de Escenarios", "La próxima crisis no es idéntica a la anterior",
               "[QM Parte XXII]"),
    ModelEntry("Escenarios", "Hypothetical Stress", _C.CORE,
               "Shocks definidos por Comité", "D13",
               "Motor de Escenarios", "Depende del juicio macro del Comité",
               "[QM Parte XXII]"),
    ModelEntry("Escenarios", "Reverse Stress Testing", _C.ADVANCED,
               "Combinación de shocks que rompe límites del portafolio",
               "Gobernanza de riesgo proactiva", "",
               "Requiere definición clara de \"ruptura\"", "[QM Parte III.1]",
               "OPEN: sin fila propia en Parte XXII, responsable no explícito"),
    ModelEntry("Escenarios", "Monte Carlo / Block Bootstrap", _C.CORE,
               "Simulación de trayectorias con dependencia preservada",
               "D2, Motor Cliente/Goal",
               "Motor de Escenarios", "Depende de la representatividad del histórico usado",
               "[QM Parte XXII, III.0 Rev.6]",
               "Bootstrap por bloques promovido a la par de MC tradicional dentro de CORE"),
    ModelEntry("Escenarios", "Regime Switching / fat tails", _C.RESEARCH,
               "Distribución condicional a régimen",
               "No recomendado para uso rutinario aún", "",
               "Complejidad de calibración alta", "[QM Parte III.1]"),
    # Benchmark
    ModelEntry("Benchmark", "AFI Benchmark Eligibility Framework", _C.CORE,
               "Verificación de 8 dimensiones (regla, no fórmula)", "D10",
               "Motor de Benchmark", "Puede no existir benchmark razonablemente cercano",
               "[QM Parte XXII]", "Revisión anual de la definición"),
    # Governance
    ModelEntry("Governance", "Explicación por reglas + plantillas", _C.CORE,
               "Regla fija → plantilla parametrizada", "Todas (capa transversal)",
               "Todos los motores", "Menos \"natural\" que texto libre — trade-off aceptado",
               "[QM Parte XXII]", "Reproducibilidad exacta ante mismos inputs"),
    ModelEntry("Governance", "SHAP / LIME como núcleo", _C.REJECTED,
               "—", "—", "", "Viola Principio 3 (explicabilidad determinística)",
               "[QM Parte III.0 Rev.1, III.1]"),
    ModelEntry("Governance", "Auto-Commentary tipo LLM", _C.REJECTED,
               "—", "—", "", "Viola Principio 3; no auditable de forma determinística",
               "[QM Parte III.0 Rev.2, III.1]"),
    ModelEntry("Governance", "Ranking directo sin eligibility check", _C.REJECTED,
               "—", "—", "", "Viola Principio 7",
               "[QM Parte III.1]"),
]
# fmt: on


def open_items() -> list[ModelEntry]:
    """Modelos CORE/ADVANCED sin responsable institucional explícito en la fuente."""
    return [m for m in MODEL_GOVERNANCE_REGISTRY if m.is_open_responsable]


def by_classification(clasificacion: ModelClassification) -> list[ModelEntry]:
    return [m for m in MODEL_GOVERNANCE_REGISTRY if m.clasificacion == clasificacion]
