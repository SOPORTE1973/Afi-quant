"""
Cliente ficticio y set de parámetros de SIMULACIÓN.

NADA de este archivo es institucional:
  - El cliente es sintético (no corresponde a ninguna persona).
  - Los valores de parámetros son ficticios, elegidos solo para poder
    correr el ciclo de vida de punta a punta. Viven en una COPIA del
    Parameter Registry marcada como simulación; el registro institucional
    (`PARAMETER_REGISTRY`) queda intacto, con sus parámetros sin valor
    hasta que el Comité los fije.

Cuando el Comité cargue los valores reales, la simulación se corre con el
registro institucional en vez de este, sin tocar los motores.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from afi_quant.clients.ips import IPS, ExpectedFlow, LifeBalanceSheet, RiskLimits
from afi_quant.clients.profile import ClientProfile, Goal
from afi_quant.registries.parameter_registry import PARAMETER_REGISTRY, ParameterRegistry

SIMULATION_SOURCE = "SIMULACIÓN — valor ficticio, no aprobado por el Comité"

SIMULATION_VALUES: dict[str, float | str | dict] = {
    "rebalancing_band_pct": 5,
    "max_concentration_per_manager_pct": 60,
    "max_hhi": 0.30,
    "min_lcr_ratio": 1.0,
    "risk_horizon_short_max_months": 12,
    "risk_horizon_medium_max_months": 36,
    "vol_cap_short_pct": 1.5,
    "vol_cap_medium_pct": 4,
    "vol_cap_long_pct": 10,
    "max_weight_per_vehicle_pct": 40,
    "short_horizon_eligible_subclass": "Money Market",
    "risk_aversion_delta": 3,
    "cma_return_shrinkage": 0.5,
    "cma_covariance_shrinkage": 0.3,
    "drawdown_alert_pct": 5,
    "mc_simulations": 5000,
    "mc_block_months": 6,
    "downside_deviation_mar_pct": 0,
    # Benchmark Eligibility Framework: D10 (QM XVIII) nombra como críticas moneda,
    # liquidez y restricciones regulatorias. Qué hacer con el estado "parcial" es
    # OPEN ISSUE ESFS-14: en la simulación, parcial permite comparar con advertencia.
    "benchmark_critical_dimensions": "moneda,liquidez,restricciones",
    "benchmark_partial_allows_comparison": "si",
    "benchmark_risk_ratio_max": 1.5,
    "benchmark_allocation_max_distance_pct": 20,
    "benchmark_liquidity_max_gap_pct": 10,
    # CMAs de largo plazo, CLP nominales, por subclase de la taxonomía. Ficticias:
    # reemplazan a las institucionales que el Comité aún no publica. La volatilidad
    # de Facturas corrige el NAV suavizado (sin precio de mercado diario).
    "cma_expected_return": {
        "Money Market": 5.0, "Deuda Corporativa Local": 6.0, "Facturas": 7.5,
        "Local": 9.5, "Global": 9.0,
    },
    "cma_expected_volatility": {
        "Money Market": 0.8, "Deuda Corporativa Local": 3.0, "Facturas": 4.0,
        "Local": 18.0, "Global": 15.0,
    },
}


def simulation_registry() -> ParameterRegistry:
    params = []
    for p in PARAMETER_REGISTRY.parameters:
        if p.name in SIMULATION_VALUES:
            p = replace(p, value=SIMULATION_VALUES[p.name], source=SIMULATION_SOURCE)
        params.append(p)
    missing = set(SIMULATION_VALUES) - {p.name for p in params}
    if missing:
        raise KeyError(f"Parámetros de simulación no declarados en el registro: {missing}")
    return ParameterRegistry(parameters=params)


ONBOARDING_DATE = date(2024, 10, 31)


def synthetic_client() -> ClientProfile:
    return ClientProfile(
        client_id="SIM-001",
        nombre="Cliente Sintético 001",
        fecha_nacimiento=date(1979, 10, 15),
        perfil_riesgo="Moderado",
        puntaje_cuestionario=52,
        gasto_mensual=2_500_000,
        nota="Cliente ficticio creado para simular el ciclo de vida; no es una persona real.",
        goals=[
            Goal("emergencia", "Fondo de emergencia (6 meses de gasto)", "esencial",
                 monto_objetivo=15_000_000, fecha=None,
                 capital_inicial=15_000_000, aporte_mensual=0,
                 liquidez_requerida="disponible en 3 días hábiles"),
            Goal("pie", "Pie de departamento", "importante",
                 monto_objetivo=60_000_000, fecha=date(2026, 6, 30),
                 capital_inicial=45_000_000, aporte_mensual=500_000,
                 probabilidad_deseada=0.85, liquidez_requerida="efectivo en la fecha de la escritura"),
            # Gasto actual × 12 × 25 años de jubilación = 750M CLP de hoy, indexado a
            # 3% anual de inflación hasta oct-2044 (20 años): ≈ 1.270M nominales.
            Goal("jubilacion", "Capital para jubilación a los 65", "importante",
                 monto_objetivo=1_270_000_000, fecha=date(2044, 10, 31),
                 capital_inicial=90_000_000, aporte_mensual=1_000_000,
                 probabilidad_deseada=0.70, liquidez_requerida="retiros programados desde 2044"),
        ],
    )


def synthetic_ips() -> IPS:
    """
    IPS ficticio del Cliente Sintético 001. Todo valor aquí es de simulación
    (el catálogo lo marca como degradado). Se deja SIN dato, a propósito, lo
    que un onboarding real suele no tener todavía (inversiones fuera de AFI):
    el catálogo muestra qué comportamiento activa esa falta.
    """
    return IPS(
        ips_id="IPS-SIM-001-v1",
        vigente_desde=date(2024, 10, 31),
        revisar_antes_de=date(2027, 10, 31),
        firmado=True,
        moneda_base="CLP",
        pais_residencia="Chile",
        segmento="Wealth, persona natural",
        perfil_riesgo="Moderado",
        tolerancia_riesgo="Moderada (cuestionario 52/100)",
        capacidad_riesgo="Media-alta: 20 años a la jubilación e ingresos laborales estables",
        limites_riesgo=RiskLimits(volatilidad_max_pct=10.0, var95_1m_max_pct=5.0,
                                  es95_1m_max_pct=7.0, drawdown_tolerado_pct=15.0),
        patrimonio_total=330_000_000,
        inversiones_fuera_afi=None,
        flujos_esperados=[
            ExpectedFlow(date(2024, 11, 30), 1_500_000, "aporte", "mensual", date(2044, 10, 31)),
            ExpectedFlow(date(2026, 6, 30), -60_000_000, "retiro", meta="pie"),
            ExpectedFlow(date(2044, 10, 31), -1_270_000_000, "retiro", meta="jubilacion"),
        ],
        restricciones_esg=["sin exclusiones declaradas"],
        restricciones_regulatorias=["persona natural, sin restricciones de inversión"],
        restricciones_familiares=["ninguna declarada"],
        limites_concentracion={"administradora": 60.0},
        life_balance_sheet=LifeBalanceSheet(
            capital_humano=520_000_000,          # VP de ingresos laborales hasta los 65
            activos_no_financieros=180_000_000,  # vivienda actual
            pasivos=0.0,
            compromisos_futuros=40_000_000,      # educación de un hijo
        ),
    )


# Escenarios hipotéticos: en producción los define y versiona el Comité
# (QM XI; ESFS 8.3 entidad `Escenario`). Aquí son valores de SIMULACIÓN:
# retornos a 12 meses (%) por subclase de la taxonomía. Son los cuatro
# escenarios en paralelo del Scenario Decision Flow (DF v1.0 6.11).
SCENARIO_LIBRARY = {
    "version": "SIM-2026-09",
    "autor": "Simulación (no aprobado por el Comité)",
    "escenarios": {
        "base": {"nombre": "Base", "shocks": {
            "Money Market": 5.0, "Deuda Corporativa Local": 6.0, "Facturas": 7.5,
            "Local": 9.5, "Global": 9.0}},
        "optimista": {"nombre": "Optimista", "shocks": {
            "Money Market": 5.0, "Deuda Corporativa Local": 8.0, "Facturas": 8.0,
            "Local": 25.0, "Global": 20.0}},
        "adverso": {"nombre": "Adverso", "shocks": {
            "Money Market": 4.0, "Deuda Corporativa Local": 2.0, "Facturas": 4.0,
            "Local": -15.0, "Global": -10.0}},
        "stress": {"nombre": "Stress", "shocks": {
            "Money Market": 3.0, "Deuda Corporativa Local": -5.0, "Facturas": -8.0,
            "Local": -35.0, "Global": -25.0},
            "rescates_suspendidos": ["Facturas"]},
    },
    # Episodios reales para Historical Simulation (fechas de mercado).
    "episodios": {
        "estallido": {"nombre": "Estallido social", "desde": "2019-10-17", "hasta": "2019-11-14"},
        "covid": {"nombre": "COVID-19", "desde": "2020-02-21", "hasta": "2020-03-23"},
        "constituyentes": {"nombre": "Elección de constituyentes", "desde": "2021-05-14",
                           "hasta": "2021-05-18"},
        "caida_2026": {"nombre": "Caída RV local 2026", "desde": "2026-02-03", "hasta": "2026-06-08"},
    },
}
