"""
Libro de clientes SINTÉTICOS para el motor centralizado.

Ninguno es una persona real. Cubren perfiles distintos para que el
monitoreo del libro tenga algo que priorizar: cerca de la jubilación,
joven y agresivo, empresario con evento de liquidez, y un onboarding
reciente con el IPS incompleto (para ver cómo se degrada el análisis
cuando falta información, en vez de inventarla).

Los onboardings parten en oct-2024 o después: antes no hay 36 meses
comunes de historia para estimar la CMA (el fondo de facturas parte en
oct-2021).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from afi_quant.clients.ips import IPS, ExpectedFlow, LifeBalanceSheet, RiskLimits
from afi_quant.clients.profile import ClientProfile, Goal
from afi_quant.simulation.parameters import ONBOARDING_DATE, synthetic_client, synthetic_ips

NOTE = "Cliente ficticio del libro de simulación; no es una persona real."


@dataclass
class BookClient:
    client: ClientProfile
    ips: IPS
    onboarding: date
    asesor: str


def _ips(cid, since, perfil, tol, cap, limits, patrimonio, fuera, flows, lbs, admin_pct=60.0, firmado=True):
    return IPS(
        ips_id=f"IPS-{cid}-v1", vigente_desde=since, revisar_antes_de=date(since.year + 3, since.month, since.day),
        firmado=firmado, moneda_base="CLP", pais_residencia="Chile", segmento="Wealth, persona natural",
        perfil_riesgo=perfil, tolerancia_riesgo=tol, capacidad_riesgo=cap, limites_riesgo=limits,
        patrimonio_total=patrimonio, inversiones_fuera_afi=fuera, flujos_esperados=flows,
        restricciones_esg=["sin exclusiones declaradas"],
        restricciones_regulatorias=["persona natural, sin restricciones de inversión"],
        restricciones_familiares=["ninguna declarada"],
        limites_concentracion={"administradora": admin_pct}, life_balance_sheet=lbs,
    )


def sim_002() -> BookClient:
    on = date(2024, 12, 31)
    c = ClientProfile(
        "SIM-002", "Cliente Sintético 002", date(1961, 5, 20), "Conservador", 28, 3_000_000, nota=NOTE,
        goals=[
            Goal("emergencia", "Fondo de emergencia", "esencial", 20_000_000, None, 20_000_000, 0,
                 liquidez_requerida="disponible en 3 días hábiles"),
            Goal("apoyo_hija", "Apoyo para el pie de la hija", "importante", 40_000_000, date(2026, 12, 31),
                 36_000_000, 0, probabilidad_deseada=0.85, liquidez_requerida="efectivo en la fecha"),
            Goal("retiro", "Capital de retiro a los 68", "esencial", 450_000_000, date(2029, 12, 31),
                 400_000_000, 2_000_000, probabilidad_deseada=0.75, liquidez_requerida="retiros desde 2030"),
        ],
    )
    ips = _ips("SIM-002", on, "Conservador", "Baja (cuestionario 28/100)", "Media: 5 años a la jubilación",
               RiskLimits(5.0, 3.0, 4.0, 8.0), 900_000_000, 300_000_000,
               [ExpectedFlow(date(2025, 1, 31), 2_000_000, "aporte", "mensual", date(2029, 12, 31), "retiro"),
                ExpectedFlow(date(2026, 12, 31), -40_000_000, "retiro", meta="apoyo_hija")],
               LifeBalanceSheet(150_000_000, 250_000_000, 0.0, 40_000_000))
    return BookClient(c, ips, on, "Asesor B")


def sim_003() -> BookClient:
    on = date(2025, 3, 31)
    c = ClientProfile(
        "SIM-003", "Cliente Sintético 003", date(1993, 2, 11), "Agresivo", 81, 1_800_000, nota=NOTE,
        goals=[
            Goal("emergencia", "Fondo de emergencia", "esencial", 8_000_000, None, 8_000_000, 0,
                 liquidez_requerida="disponible en 3 días hábiles"),
            Goal("magister", "Magíster en el extranjero", "importante", 35_000_000, date(2027, 6, 30),
                 15_000_000, 600_000, probabilidad_deseada=0.80, liquidez_requerida="efectivo en la fecha"),
            Goal("independencia", "Independencia financiera a los 59", "aspiracional", 1_800_000_000,
                 date(2052, 3, 31), 25_000_000, 1_000_000, probabilidad_deseada=0.60),
        ],
    )
    ips = _ips("SIM-003", on, "Agresivo", "Alta (cuestionario 81/100)", "Alta: 27 años de horizonte",
               RiskLimits(15.0, 7.0, 10.0, 25.0), 60_000_000, 12_000_000,
               [ExpectedFlow(date(2025, 4, 30), 1_600_000, "aporte", "mensual", date(2052, 3, 31))],
               LifeBalanceSheet(700_000_000, 0.0, 0.0, 0.0))
    return BookClient(c, ips, on, "Asesor A")


def sim_004() -> BookClient:
    on = date(2025, 6, 30)
    c = ClientProfile(
        "SIM-004", "Cliente Sintético 004", date(1970, 8, 3), "Moderado", 47, 6_000_000, nota=NOTE,
        goals=[
            Goal("emergencia", "Reserva de liquidez", "esencial", 60_000_000, None, 60_000_000, 0,
                 liquidez_requerida="disponible en 3 días hábiles"),
            Goal("educacion", "Educación universitaria de los hijos", "esencial", 160_000_000,
                 date(2030, 3, 31), 130_000_000, 0, probabilidad_deseada=0.85),
            Goal("patrimonio", "Preservación del patrimonio tras la venta de la empresa", "importante",
                 1_500_000_000, date(2040, 12, 31), 700_000_000, 0, probabilidad_deseada=0.70),
        ],
    )
    ips = _ips("SIM-004", on, "Moderado", "Moderada (cuestionario 47/100)", "Alta: patrimonio líquido tras la venta",
               RiskLimits(8.0, 4.0, 6.0, 12.0), 1_600_000_000, 710_000_000,
               [ExpectedFlow(date(2030, 3, 31), -160_000_000, "retiro", meta="educacion")],
               LifeBalanceSheet(200_000_000, 650_000_000, 0.0, 160_000_000), admin_pct=40.0)
    return BookClient(c, ips, on, "Asesor A")


def sim_005() -> BookClient:
    """Onboarding reciente: el IPS no trae límites de VaR/ES ni caída tolerada, ni balance de vida."""
    on = date(2026, 3, 31)
    c = ClientProfile(
        "SIM-005", "Cliente Sintético 005", date(1986, 11, 30), "Moderado", 55, 2_200_000, nota=NOTE,
        goals=[
            Goal("emergencia", "Fondo de emergencia", "esencial", 12_000_000, None, 12_000_000, 0,
                 liquidez_requerida="disponible en 3 días hábiles"),
            Goal("jubilacion", "Capital para jubilación a los 65", "importante", 900_000_000,
                 date(2051, 11, 30), 60_000_000, 800_000, probabilidad_deseada=0.70),
        ],
    )
    ips = _ips("SIM-005", on, "Moderado", "Moderada (cuestionario 55/100)", None,
               RiskLimits(10.0, None, None, None), None, None,
               [ExpectedFlow(date(2026, 4, 30), 800_000, "aporte", "mensual", date(2051, 11, 30))], None)
    return BookClient(c, ips, on, "Asesor B")


def book_clients() -> list[BookClient]:
    return [BookClient(synthetic_client(), synthetic_ips(), ONBOARDING_DATE, "Asesor A"),
            sim_002(), sim_003(), sim_004(), sim_005()]
