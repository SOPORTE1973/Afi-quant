"""
Fixture de datos reales — ETF Singular IPSA, serie UNICA.

Fuente: `mcp__MCP_Afitrading__nav_ajustado` (rut=10748, serie=UNICA,
desde=2026-09-15, hasta=2026-09-29), consultado en vivo el 2026-09-30.
`nav_ajustado` devuelve la serie ya "materializada" (un punto por fecha
de mercado, ajustado por dividendos) — a diferencia del log crudo de
snapshots de `rentabilidades`/`historial`, no requiere `dedupe_snapshots`
porque el conector ya entrega un solo valor por día.

Estos 12 puntos son datos reales de mercado, no sintéticos. Los huecos
de calendario (2026-09-17, 2026-09-18, 2026-09-25) corresponden a días
no hábiles bursátiles (incluye Fiestas Patrias) — no son datos
faltantes.

Este fixture existe solo para tener un caso de prueba reproducible con
datos reales sin depender de que el conector esté disponible al correr
los tests. El motor de producción (`BenchmarkEngine`) debe consultar el
conector en vivo, no este fixture.
"""

from __future__ import annotations

from datetime import date

from afi_quant.engines.series import AdjustedSeries, NavPoint

SOURCE = (
    "mcp__MCP_Afitrading__nav_ajustado(rut=10748, serie=UNICA, "
    "desde=2026-09-15, hasta=2026-09-29) — consultado 2026-09-30"
)

ETF_SINGULAR_IPSA_SERIES = AdjustedSeries(
    rut="10748",
    serie="UNICA",
    nemotecnico="CFIETFIPSA",
    source=SOURCE,
    points=[
        NavPoint(fecha=date(2026, 9, 15), valor_cuota=1369.4591),
        NavPoint(fecha=date(2026, 9, 16), valor_cuota=1358.9392),
        NavPoint(fecha=date(2026, 9, 19), valor_cuota=1376.5316),
        NavPoint(fecha=date(2026, 9, 20), valor_cuota=1376.5285),
        NavPoint(fecha=date(2026, 9, 21), valor_cuota=1373.7042),
        NavPoint(fecha=date(2026, 9, 22), valor_cuota=1382.0335),
        NavPoint(fecha=date(2026, 9, 23), valor_cuota=1384.7968),
        NavPoint(fecha=date(2026, 9, 24), valor_cuota=1366.6832),
        NavPoint(fecha=date(2026, 9, 26), valor_cuota=1361.4758),
        NavPoint(fecha=date(2026, 9, 27), valor_cuota=1361.4723),
        NavPoint(fecha=date(2026, 9, 28), valor_cuota=1347.0146),
        NavPoint(fecha=date(2026, 9, 29), valor_cuota=1337.1848),
    ],
)
