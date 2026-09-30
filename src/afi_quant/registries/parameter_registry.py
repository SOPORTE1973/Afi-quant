"""
Parameter Registry (M22).

ESFS-01 exige un registro con "las seis categorías de gobernanza y
todos los parámetros declarados, aunque sin valor" (Fase 0, entregable 2).

ESTADO DE ESTE ARCHIVO: las seis categorías de abajo son una
PROPUESTA — armada cruzando las decisiones institucionales (D1-D13) y
los motores descritos en ESFS-01 y la Metodología Cuantitativa, no una
cita textual del documento. El usuario la revisó y aprobó como
estructura de trabajo (2026-09-30), pero sigue pendiente de
contrastarla contra el nombre y alcance exacto que ESFS-01 le da a
"las seis categorías de gobernanza" — si difieren, este archivo se
corrige para que coincida con la fuente, no al revés.

Cada parámetro declarado abajo tiene `value=None` a propósito: es una
DECLARACIÓN de qué parámetro debe existir y qué decisión alimenta —
nunca un umbral inventado. Los valores los define el Comité de
Inversiones (o quien corresponda por categoría) y se cargan después,
versionados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Parameter:
    name: str
    category: str
    description: str
    unit: str | None = None
    value: float | str | dict | None = None  # None = declarado, sin valor todavía
    version: int = 1
    effective_from: date | None = None
    proposed_by: str | None = None
    approved_by: str | None = None
    source: str | None = None


@dataclass
class ParameterRegistry:
    parameters: list[Parameter] = field(default_factory=list)

    def declare(self, parameter: Parameter) -> None:
        """Registra un parámetro sin valor — lo llena el Comité después."""
        self.parameters.append(parameter)

    def undeclared(self) -> list[Parameter]:
        return [p for p in self.parameters if p.value is None]

    def by_category(self, category: str) -> list[Parameter]:
        return [p for p in self.parameters if p.category == category]


# ---------------------------------------------------------------------------
# Las seis categorías propuestas (pendientes de confirmar contra ESFS-01)
# ---------------------------------------------------------------------------

CATEGORIES: tuple[str, ...] = (
    "Bandas y umbrales de rebalanceo",
    "Límites de concentración y riesgo",
    "Horizontes y buckets de liquidez",
    "CMAs institucionales",
    "Reglas de escalamiento",
    "Parámetros de escenarios y stress testing",
)

_PROPOSAL_NOTE = "Categoría propuesta — pendiente de confirmar contra ESFS-01."


def _seed_parameters() -> list[Parameter]:
    return [
        # 1. Bandas y umbrales de rebalanceo
        Parameter(
            name="rebalancing_band_pct",
            category="Bandas y umbrales de rebalanceo",
            description="Desviación permitida por asset class respecto al SAA antes de "
                        "considerar rebalanceo. " + _PROPOSAL_NOTE,
            unit="%",
            source="D1, D8",
        ),
        Parameter(
            name="materiality_threshold_pct",
            category="Bandas y umbrales de rebalanceo",
            description="Umbral que determina si un drift es material y dispara acción. "
                        + _PROPOSAL_NOTE,
            unit="%",
            source="D1, [QM Parte XXIII P4]",
        ),
        # 2. Límites de concentración y riesgo
        Parameter(
            name="max_concentration_per_issuer_pct",
            category="Límites de concentración y riesgo",
            description="Concentración máxima permitida en un solo emisor. " + _PROPOSAL_NOTE,
            unit="%",
            source="D4, D7",
        ),
        Parameter(
            name="max_concentration_per_asset_class_pct",
            category="Límites de concentración y riesgo",
            description="Concentración máxima permitida por asset class. " + _PROPOSAL_NOTE,
            unit="%",
            source="D4, D7",
        ),
        Parameter(
            name="max_concentration_per_manager_pct",
            category="Límites de concentración y riesgo",
            description="Concentración máxima permitida por gestor/AGF. " + _PROPOSAL_NOTE,
            unit="%",
            source="D7",
        ),
        Parameter(
            name="max_hhi",
            category="Límites de concentración y riesgo",
            description="Valor máximo aceptable del índice Herfindahl-Hirschman del "
                        "portafolio. " + _PROPOSAL_NOTE,
            source="D7, [QM Parte XXII — HHI]",
        ),
        Parameter(
            name="downside_deviation_mar_pct",
            category="Límites de concentración y riesgo",
            description="Minimum Acceptable Return (MAR) mensual contra el que se mide la "
                        "Downside Deviation. El Motor de Riesgo no calcula Downside "
                        "Deviation hasta que tenga valor. " + _PROPOSAL_NOTE,
            unit="%",
            source="[QM Parte XXII — Downside Deviation: requiere definición consistente de MAR]",
        ),
        Parameter(
            name="risk_horizon_short_max_months",
            category="Límites de concentración y riesgo",
            description="Meses hasta la fecha de una meta bajo los cuales la meta se trata "
                        "como horizonte de riesgo CORTO. " + _PROPOSAL_NOTE,
            unit="meses",
            source="Motor de Cliente/Goal, [QM Parte XXII — Goal-Based Monte Carlo]",
        ),
        Parameter(
            name="risk_horizon_medium_max_months",
            category="Límites de concentración y riesgo",
            description="Meses hasta la fecha de una meta bajo los cuales la meta se trata "
                        "como horizonte MEDIO (sobre esto, LARGO). " + _PROPOSAL_NOTE,
            unit="meses",
            source="Motor de Cliente/Goal",
        ),
        Parameter(
            name="vol_cap_short_pct",
            category="Límites de concentración y riesgo",
            description="Volatilidad ex-ante máxima de la cartera asignada a una meta de "
                        "horizonte corto. " + _PROPOSAL_NOTE,
            unit="%",
            source="D4, D5, D8",
        ),
        Parameter(
            name="vol_cap_medium_pct",
            category="Límites de concentración y riesgo",
            description="Volatilidad ex-ante máxima para una meta de horizonte medio. "
                        + _PROPOSAL_NOTE,
            unit="%",
            source="D4, D5, D8",
        ),
        Parameter(
            name="vol_cap_long_pct",
            category="Límites de concentración y riesgo",
            description="Volatilidad ex-ante máxima para una meta de horizonte largo, "
                        "según el perfil de riesgo del cliente. " + _PROPOSAL_NOTE,
            unit="%",
            source="D4, D5, D8",
        ),
        Parameter(
            name="max_weight_per_vehicle_pct",
            category="Límites de concentración y riesgo",
            description="Peso máximo de un solo vehículo dentro de la cartera de una meta "
                        "de horizonte medio o largo. " + _PROPOSAL_NOTE,
            unit="%",
            source="D4, D7",
        ),
        Parameter(
            name="short_horizon_eligible_subclass",
            category="Límites de concentración y riesgo",
            description="Subclase (taxonomía AfiTrading) elegible para metas de horizonte "
                        "corto. " + _PROPOSAL_NOTE,
            source="D6, D9",
        ),
        # 3. Horizontes y buckets de liquidez
        Parameter(
            name="liquidity_bucket_short_days",
            category="Horizontes y buckets de liquidez",
            description="Límite superior del bucket de liquidez corto (0–3 meses). "
                        + _PROPOSAL_NOTE,
            unit="días",
            value=90,  # el tramo en sí (0-3m) SÍ está confirmado en la fuente [QM Parte XXII]
            source="D6, D9, [QM Parte XXII — Liquidity Ladder]",
        ),
        Parameter(
            name="liquidity_bucket_medium_days",
            category="Horizontes y buckets de liquidez",
            description="Límite superior del bucket de liquidez medio (3–12 meses). "
                        + _PROPOSAL_NOTE,
            unit="días",
            value=365,  # el tramo en sí (3-12m) SÍ está confirmado en la fuente [QM Parte XXII]
            source="D6, D9, [QM Parte XXII — Liquidity Ladder]",
        ),
        Parameter(
            name="min_lcr_ratio",
            category="Horizontes y buckets de liquidez",
            description="Ratio mínimo de cobertura de liquidez (LCR) exigido por bucket. "
                        + _PROPOSAL_NOTE,
            source="D6, D9, [QM Parte XXII — Liquidity Coverage Ratio]",
        ),
        # 4. CMAs institucionales
        Parameter(
            name="cma_expected_return",
            category="CMAs institucionales",
            description="Retorno esperado institucional por asset class (nunca supuesto "
                        "individual del asesor). " + _PROPOSAL_NOTE,
            unit="%",
            source="[QM Parte VII], Construction Engine",
        ),
        Parameter(
            name="cma_expected_volatility",
            category="CMAs institucionales",
            description="Volatilidad esperada institucional por asset class. "
                        + _PROPOSAL_NOTE,
            unit="%",
            source="[QM Parte VII], Construction Engine",
        ),
        Parameter(
            name="cma_correlation_matrix",
            category="CMAs institucionales",
            description="Matriz de correlaciones institucional entre asset classes. "
                        + _PROPOSAL_NOTE,
            source="[QM Parte VII], Construction/Diversification Engine",
        ),
        Parameter(
            name="risk_aversion_delta",
            category="CMAs institucionales",
            description="Coeficiente de aversión al riesgo δ del MVO robusto: "
                        "max(w'μ − δ/2·w'Σw). " + _PROPOSAL_NOTE,
            source="[QM Parte XXII — MVO robusto]",
        ),
        Parameter(
            name="cma_return_shrinkage",
            category="CMAs institucionales",
            description="Intensidad (0-1) con que el retorno esperado de cada clase se "
                        "acerca al promedio de las clases antes de optimizar. " + _PROPOSAL_NOTE,
            source="[QM Parte XXII — MVO robusto: sensible a error de estimación de μ]",
        ),
        Parameter(
            name="cma_covariance_shrinkage",
            category="CMAs institucionales",
            description="Intensidad (0-1) del shrinkage de la matriz de covarianzas hacia "
                        "un target de correlación constante. " + _PROPOSAL_NOTE,
            source="[QM Parte XXII — Shrinkage (Ledoit-Wolf): requiere calibrar intensidad]",
        ),
        # 5. Reglas de escalamiento
        Parameter(
            name="escalation_level_2_threshold",
            category="Reglas de escalamiento",
            description="Condición que escala un caso a Nivel 2 (diagnóstico + "
                        "alternativas, sin recomendación cerrada). " + _PROPOSAL_NOTE,
            source="[DF 8.3 OQ1]",
        ),
        Parameter(
            name="escalation_level_3_threshold",
            category="Reglas de escalamiento",
            description="Condición que escala un caso a Nivel 3 (recomendación completa). "
                        + _PROPOSAL_NOTE,
            source="[DF 8.3 OQ1]",
        ),
        Parameter(
            name="escalation_approver_role",
            category="Reglas de escalamiento",
            description="Rol institucional que debe aprobar cada nivel de escalamiento. "
                        + _PROPOSAL_NOTE,
            source="[DF 8.3 OQ1]",
        ),
        Parameter(
            name="drawdown_alert_pct",
            category="Reglas de escalamiento",
            description="Caída desde el máximo de la cartera total que dispara una revisión "
                        "extraordinaria. " + _PROPOSAL_NOTE,
            unit="%",
            source="[DF 8.3 OQ1]",
        ),
        # 6. Parámetros de escenarios y stress testing
        Parameter(
            name="stress_scenario_definitions",
            category="Parámetros de escenarios y stress testing",
            description="Catálogo de shocks hipotéticos definidos por el Comité para el "
                        "Motor de Escenarios. " + _PROPOSAL_NOTE,
            source="D13, [QM Parte XI — Hypothetical Stress]",
        ),
        Parameter(
            name="stress_horizon_days",
            category="Parámetros de escenarios y stress testing",
            description="Horizonte temporal sobre el cual se proyecta cada escenario de "
                        "estrés. " + _PROPOSAL_NOTE,
            unit="días",
            source="D13, [QM Parte XI]",
        ),
        Parameter(
            name="mc_simulations",
            category="Parámetros de escenarios y stress testing",
            description="Número de trayectorias del Goal-Based Monte Carlo (el registro de "
                        "modelos indica 5.000-20.000). " + _PROPOSAL_NOTE,
            source="[QM Parte XXII — Goal-Based Monte Carlo]",
        ),
        Parameter(
            name="mc_block_months",
            category="Parámetros de escenarios y stress testing",
            description="Largo de bloque (meses) del bootstrap por bloques. " + _PROPOSAL_NOTE,
            unit="meses",
            source="[QM Parte XXII, III.0 Rev.6 — Block Bootstrap]",
        ),
    ]


# Instancia compartida — cargada con la propuesta de seis categorías
# aprobada por el usuario (2026-09-30), pendiente de validar contra
# ESFS-01. Casi todos los parámetros quedan con value=None: son
# declaraciones de qué debe existir, no umbrales inventados. Las dos
# excepciones (los tramos 0-3m / 3-12m del bucket de liquidez) SÍ
# están confirmadas textualmente en la fuente, por eso llevan valor.
PARAMETER_REGISTRY = ParameterRegistry(parameters=_seed_parameters())


def get_parameter(name: str, registry: ParameterRegistry = PARAMETER_REGISTRY) -> Parameter:
    for p in registry.parameters:
        if p.name == name:
            return p
    raise KeyError(f"Parámetro '{name}' no declarado en el Parameter Registry")
