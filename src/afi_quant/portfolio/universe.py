"""
Universo de inversión — un vehículo real por clase de activo.

Cada vehículo es un fondo real del conector MCP_Afitrading, clasificado
con la taxonomía de AfiTrading (`data/asset_taxonomy.py`). Las series son
NAV ajustado real (fixtures en `data/fixtures/`).

LIQUIDEZ: el texto de `liquidez` viene del campo homónimo del conector
(`buscar_fondos`). Los ETF de Singular no traen ese campo; se registran
como "Bursátil (ETF)" porque se liquidan vendiendo en bolsa. El plazo
de pago exacto por vehículo sigue pendiente del registro de
rescatabilidad (Solicitud C del audit) — por eso `dias_liquidez` es una
cota declarada, no un dato confirmado.
"""

from __future__ import annotations

from dataclasses import dataclass

from afi_quant.data import fixtures
from afi_quant.engines.series import AdjustedSeries


@dataclass(frozen=True)
class Vehicle:
    key: str
    nombre: str
    administradora: str
    clase_activo: str
    subclase: str
    liquidez: str
    dias_liquidez: int
    series: AdjustedSeries

    @property
    def nemotecnico(self) -> str:
        return self.series.nemotecnico


def default_universe() -> dict[str, Vehicle]:
    vehicles = [
        Vehicle("MM", "ETF Singular Chile Corta Duración", "Singular", "Renta Fija",
                "Money Market", "Bursátil (ETF)", 3, fixtures.singular_corta_duracion()),
        Vehicle("RF", "ETF Singular Chile Corporativo", "Singular", "Renta Fija",
                "Deuda Corporativa Local", "Bursátil (ETF)", 3, fixtures.singular_corporativo()),
        Vehicle("DP", "BTG Pactual Liquidez Alternativa FI (serie A)", "BTG Pactual",
                "Deuda Privada", "Facturas", "Rescatable - Semanal", 10,
                fixtures.btg_liquidez_alternativa()),
        Vehicle("RVL", "FI Falcom Tactical Chilean Equities", "Falcom", "Renta Variable",
                "Local", "Rescatable - Diario", 10, fixtures.falcom_tactical(desde=None)),
        Vehicle("RVG", "ETF Singular Global Equities", "Singular", "Renta Variable",
                "Global", "Rescatable - Diario", 10, fixtures.singular_global_equities()),
    ]
    return {v.key: v for v in vehicles}
