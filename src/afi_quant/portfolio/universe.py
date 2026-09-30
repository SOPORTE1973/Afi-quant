"""
Universo de inversión — un vehículo real por clase de activo.

Cada vehículo es un fondo real del conector MCP_Afitrading, clasificado
con la taxonomía de AfiTrading (`data/asset_taxonomy.py`). Las series son
NAV ajustado real (fixtures en `data/fixtures/`).

Atributos según la entidad `Vehiculo` de ESFS-01 8.3: tipo, liquidez
(periodicidad de valuación, ventana de redención, lock-up), gestor,
costo total, moneda. Lo que el conector no entrega queda en None y el
catálogo de información lo declara faltante — no se completa con
supuestos:
  - `costo_total_pct` (TAC): no disponible en el conector.
  - `estado_approved_list`: depende de M10 (IDD/ODD), inexistente aún.

LIQUIDEZ: el texto de `liquidez` viene del campo homónimo del conector.
Los ETF de Singular no traen ese campo; se registran como "Bursátil
(ETF)". El plazo de pago exacto sigue pendiente del registro de
rescatabilidad (Solicitud C del audit): `dias_liquidez` es una cota
declarada, no un dato confirmado.
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
    moneda: str = "CLP"
    periodicidad_valuacion: str = "diaria"
    ventana_rescate: str | None = None
    lockup: str | None = None
    costo_total_pct: float | None = None
    estado_approved_list: str | None = None
    precio_de_mercado: bool = True   # False = NAV valorizado sin precio diario (suavizado)

    @property
    def nemotecnico(self) -> str:
        return self.series.nemotecnico


def default_universe() -> dict[str, Vehicle]:
    vehicles = [
        Vehicle("MM", "ETF Singular Chile Corta Duración", "Singular", "Renta Fija",
                "Money Market", "Bursátil (ETF)", 3, fixtures.singular_corta_duracion(),
                ventana_rescate="venta en bolsa, T+2"),
        Vehicle("RF", "ETF Singular Chile Corporativo", "Singular", "Renta Fija",
                "Deuda Corporativa Local", "Bursátil (ETF)", 3, fixtures.singular_corporativo(),
                ventana_rescate="venta en bolsa, T+2"),
        Vehicle("DP", "BTG Pactual Liquidez Alternativa FI (serie A)", "BTG Pactual",
                "Deuda Privada", "Facturas", "Rescatable - Semanal", 10,
                fixtures.btg_liquidez_alternativa(), ventana_rescate="semanal",
                precio_de_mercado=False),
        Vehicle("RVL", "FI Falcom Tactical Chilean Equities", "Falcom", "Renta Variable",
                "Local", "Rescatable - Diario", 10, fixtures.falcom_tactical(desde=None),
                ventana_rescate="diaria"),
        Vehicle("RVG", "ETF Singular Global Equities", "Singular", "Renta Variable",
                "Global", "Rescatable - Diario", 10, fixtures.singular_global_equities(),
                ventana_rescate="diaria"),
    ]
    return {v.key: v for v in vehicles}


@dataclass(frozen=True)
class BenchmarkProxy:
    """Serie pasiva que representa una clase de activo dentro de un benchmark."""

    key: str             # clase del universo que representa
    nombre: str
    series: AdjustedSeries
    nota: str = ""


def policy_benchmark_proxies() -> dict[str, BenchmarkProxy]:
    """
    Componentes pasivos del Policy Benchmark: cada clase del universo se
    representa con un vehículo indexado. La deuda privada de facturas no
    tiene índice público: se representa con money market, y el benchmark
    lo declara (dimensión Asset Allocation queda "parcial").
    """
    cd = fixtures.singular_corta_duracion()
    return {
        "MM": BenchmarkProxy("MM", "ETF Singular Chile Corta Duración", cd),
        "RF": BenchmarkProxy("RF", "ETF Singular Chile Corporativo", fixtures.singular_corporativo()),
        "DP": BenchmarkProxy("DP", "ETF Singular Chile Corta Duración (sustituto)", cd,
                             nota="Facturas sin índice público: se usa money market como sustituto."),
        "RVL": BenchmarkProxy("RVL", "FM Security Index Fund S&P/CLX IPSA (serie A)",
                              fixtures.security_ipsa_index()),
        "RVG": BenchmarkProxy("RVG", "ETF Singular Global Equities", fixtures.singular_global_equities()),
    }
