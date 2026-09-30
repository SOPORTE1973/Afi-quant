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
                 capital_inicial=15_000_000, aporte_mensual=0),
            Goal("pie", "Pie de departamento", "importante",
                 monto_objetivo=60_000_000, fecha=date(2026, 6, 30),
                 capital_inicial=45_000_000, aporte_mensual=500_000),
            # Gasto actual × 12 × 25 años de jubilación = 750M CLP de hoy, indexado a
            # 3% anual de inflación hasta oct-2044 (20 años): ≈ 1.270M nominales.
            Goal("jubilacion", "Capital para jubilación a los 65", "importante",
                 monto_objetivo=1_270_000_000, fecha=date(2044, 10, 31),
                 capital_inicial=90_000_000, aporte_mensual=1_000_000),
        ],
    )
