"""
Series de NAV ajustado — utilidades compartidas para Benchmark/Performance/Risk.

El conector MCP_Afitrading (`rentabilidades`, `nav_ajustado`) devuelve un
LOG de snapshots: el mismo día `hasta` puede aparecer varias veces con
distinto `valor_cuota` porque el fondo se revalúa más de una vez al día
(y a veces se restata). Para cualquier cálculo de retorno hay que
quedarse con un solo punto por fecha de mercado — el más reciente
(`fecha_snapshot` más nueva) — antes de calcular nada. No hacerlo
duplica información y distorsiona el retorno.

Implementa además la fórmula CORE ya confirmada y clasificada en el
Model Governance Registry para TWR geométrico:

    TWR = ∏(1+R_t) − 1 ,  R_t = (EMV−BMV−CF)/(BMV+CF)

Para una serie de precio de referencia (un benchmark, sin flujos
externos), R_t se reduce a un retorno simple entre dos NAV
consecutivos. `geometric_chain_return` encadena esos retornos diarios;
`total_return` lo calcula directo entre el primer y el último punto.
Ambos deben coincidir (salvo redondeo) — eso es lo que valida el test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class NavPoint:
    fecha: date
    valor_cuota: float


@dataclass
class AdjustedSeries:
    """
    Una serie de NAV ajustado ya deduplicada, lista para calcular.

    `source` documenta de dónde vino cada serie — nunca se construye
    una AdjustedSeries sin decir su procedencia (fixture, conector en
    vivo, etc.), para que cualquiera pueda distinguir dato real de
    ejemplo sintético.
    """

    rut: str
    serie: str
    nemotecnico: str
    points: list[NavPoint]
    source: str

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            return
        dates = [p.fecha for p in self.points]
        if dates != sorted(dates):
            raise ValueError("AdjustedSeries.points debe estar ordenado por fecha ascendente")

    @property
    def start(self) -> NavPoint:
        return self.points[0]

    @property
    def end(self) -> NavPoint:
        return self.points[-1]


def dedupe_snapshots(raw_historial: list[dict]) -> list[NavPoint]:
    """
    Recibe el `historial` crudo tal como lo devuelve
    `mcp__MCP_Afitrading__rentabilidades` / `nav_ajustado` (ordenado
    por `fecha_snapshot` descendente, con posibles duplicados por
    `hasta`) y devuelve un punto por fecha de mercado, quedándose con
    el snapshot más reciente de cada una. El resultado sale ordenado
    ascendente por fecha, listo para `AdjustedSeries`.
    """
    latest_by_date: dict[date, tuple[datetime, float]] = {}
    for row in raw_historial:
        fecha = datetime.strptime(row["hasta"], "%Y-%m-%d").date()
        snapshot_ts = datetime.strptime(row["fecha_snapshot"], "%Y-%m-%d %H:%M:%S")
        valor = float(row["valor_cuota"])
        current = latest_by_date.get(fecha)
        if current is None or snapshot_ts > current[0]:
            latest_by_date[fecha] = (snapshot_ts, valor)

    return [
        NavPoint(fecha=fecha, valor_cuota=valor)
        for fecha, (_, valor) in sorted(latest_by_date.items())
    ]


def simple_return(p0: NavPoint, p1: NavPoint) -> float:
    return p1.valor_cuota / p0.valor_cuota - 1


def geometric_chain_return(points: list[NavPoint]) -> float:
    """TWR encadenado: ∏(1+R_t) − 1 sobre retornos diarios consecutivos."""
    if len(points) < 2:
        raise ValueError("Se necesitan al menos 2 puntos para encadenar retornos")
    product = 1.0
    for p0, p1 in zip(points, points[1:]):
        product *= 1 + simple_return(p0, p1)
    return product - 1


def total_return(series: AdjustedSeries) -> float:
    """Retorno directo entre el primer y el último punto de la serie."""
    return simple_return(series.start, series.end)


# ---------------------------------------------------------------------------
# Remuestreo y ventanas — compartido por Performance y Risk
# ---------------------------------------------------------------------------

DAYS_PER_YEAR = 365.25


def years_between(p0: NavPoint, p1: NavPoint) -> float:
    """Años calendario entre dos puntos (base 365,25 — los fondos chilenos
    publican NAV también fines de semana, así que no se usa base 252)."""
    return (p1.fecha - p0.fecha).days / DAYS_PER_YEAR


def month_end_points(points: list[NavPoint]) -> list[NavPoint]:
    """
    Última observación disponible de cada mes calendario. El mes en curso
    (si la serie termina a mitad de mes) queda representado por su último
    dato disponible — quien consume esto debe declararlo, no ocultarlo.
    """
    by_month: dict[tuple[int, int], NavPoint] = {}
    for p in points:
        by_month[(p.fecha.year, p.fecha.month)] = p  # points viene ascendente
    return [by_month[k] for k in sorted(by_month)]


def period_returns(points: list[NavPoint]) -> list[float]:
    """Retornos simples entre puntos consecutivos (R_t sin flujos externos)."""
    return [simple_return(p0, p1) for p0, p1 in zip(points, points[1:])]


def trailing_window(points: list[NavPoint], years: int) -> list[NavPoint] | None:
    """
    Puntos de los últimos `years` años terminando en el último dato. Parte
    del último punto disponible en o antes de la fecha de inicio exacta.
    Devuelve None si la serie no cubre la ventana completa — nunca se
    anualiza ni se reporta una ventana parcial como si fuera completa.
    """
    if not points:
        return None
    end = points[-1].fecha
    try:
        start = end.replace(year=end.year - years)
    except ValueError:  # 29-feb
        start = end.replace(year=end.year - years, day=28)
    if points[0].fecha > start:
        return None
    anchor = max(i for i, p in enumerate(points) if p.fecha <= start)
    return points[anchor:]


def align_on_common_dates(
    a: list[NavPoint], b: list[NavPoint]
) -> tuple[list[NavPoint], list[NavPoint]]:
    """Recorta dos series a las fechas que tienen ambas (para métricas relativas)."""
    common = {p.fecha for p in a} & {p.fecha for p in b}
    return (
        [p for p in a if p.fecha in common],
        [p for p in b if p.fecha in common],
    )
