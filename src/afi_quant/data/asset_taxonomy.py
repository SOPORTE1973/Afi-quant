"""
Taxonomía de asset classes de AfiTrading — Fase 0, entregable 5.

SNAPSHOT tomado en vivo del conector MCP_Afitrading (herramienta
`taxonomia`) el 2026-09-30. Son categorías PROPIAS de AfiTrading para
clasificar fondos — no son las de la CMF. La `subclase` es la llave
con la que el Comité ubica cada fondo en su matriz de límites.

IMPORTANTE — esto es un snapshot, no una integración en vivo:
- Esta aplicación (el backend de afi-quant) no tiene todavía una ruta
  confirmada para llamar al conector MCP_Afitrading directamente —
  ese conector vive en la sesión de Claude, no necesariamente como
  API REST disponible para este servicio. Cuando TI confirme cómo
  integrar esta fuente en producción (Solicitud C del documento de
  audit), este snapshot se reemplaza por una llamada real.
- Los datos en sí SÍ son reales (no inventados): vienen de la
  respuesta real del conector, copiados tal cual.
- Lo que todavía falta y NO está en este snapshot: el registro de
  rescatabilidad por vehículo (periodicidad de valuación, ventana de
  redención, lock-ups) — eso resuelve los buckets de liquidez
  (0-3m/3-12m/+12m) y sigue pendiente (ver Solicitud C).
"""

from __future__ import annotations

from dataclasses import dataclass

SNAPSHOT_DATE = "2026-09-30"
SOURCE = "mcp__MCP_Afitrading__taxonomia (conector en vivo de AfiTrading)"


@dataclass(frozen=True)
class Subclase:
    id: int
    nombre: str


CATEGORIAS: tuple[str, ...] = ("Alternativo", "Tradicional", "Multifondo de Pensiones")

CATEGORIAS_MERCADO: tuple[dict, ...] = (
    {"label": "Renta Fija / Deuda Publica", "slug": "renta-fija"},
    {"label": "Deuda Privada Rescatable", "slug": "deuda-rescatable"},
    {"label": "Deuda Privada No Rescatable", "slug": "deuda-no-rescatable"},
    {"label": "Deuda Privada Extranjera", "slug": "deuda-extranjera"},
    {"label": "Semi-Liquidos", "slug": "semi-liquidos"},
    {"label": "Mixto / Multi-activo", "slug": "mixto"},
    {"label": "Renta Variable Global", "slug": "rv-global"},
    {"label": "Renta Variable Local", "slug": "rv-local"},
    {"label": "RV Local - Small/Mid Cap", "slug": "rv-local-otros"},
    {"label": "Otros / Sin clasificar", "slug": "otros"},
)

CLASES_ACTIVO: tuple[str, ...] = (
    "Deuda Privada",
    "Renta Variable",
    "Renta Fija",
    "Real Estate",
    "Private Equity",
    "Criptomonedas",
    "Balanceado",
    "Multifondos",
)

SUBCLASES: dict[str, tuple[Subclase, ...]] = {
    "Balanceado": (
        Subclase(21, "Balanceado"),
    ),
    "Deuda Privada": (
        Subclase(26, "Automotriz"),
        Subclase(2, "Facturas"),
        Subclase(27, "Gtia Inmobiliaria No Rescatable"),
        Subclase(3, "Gtia Inmobiliaria Rescatable"),
        Subclase(28, "Multiestrategia No Rescatable"),
        Subclase(1, "Multiestrategia Rescatable"),
        Subclase(22, "Preferente"),
        Subclase(20, "Semiliquido Dolar"),
    ),
    "Private Equity": (
        Subclase(16, "Primario"),
        Subclase(17, "Secundario"),
        Subclase(18, "Semiliquido"),
        Subclase(19, "Venture Capital"),
    ),
    "Real Estate": (
        Subclase(14, "Desarrollo Inmobiliario"),
        Subclase(15, "Infraestructura"),
        Subclase(13, "Rentas Comerciales"),
        Subclase(12, "Rentas Inmobiliaria"),
        Subclase(32, "Rentas Residencial"),
    ),
    "Renta Fija": (
        Subclase(10, "Deuda Corporativa Global"),
        Subclase(11, "Deuda Corporativa Latam"),
        Subclase(8, "Deuda Corporativa Local"),
        Subclase(9, "Money Market"),
    ),
    "Renta Variable": (
        Subclase(7, "Global"),
        Subclase(6, "Latam"),
        Subclase(4, "Local"),
        Subclase(5, "Local Small Cap"),
        Subclase(23, "Tematica"),
    ),
}


def subclase_by_id(subclase_id: int) -> Subclase | None:
    for subclases in SUBCLASES.values():
        for s in subclases:
            if s.id == subclase_id:
                return s
    return None
