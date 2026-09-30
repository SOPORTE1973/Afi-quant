"""
AFI Benchmark Eligibility Framework (QM XII) — la regla de 8 dimensiones.

"Antes de cualquier comparación, verificar ocho dimensiones. Si el
benchmark no es elegible, el sistema NO genera ranking." (QM XII)

Dimensiones y qué se verifica (texto de QM XII):
  Objetivo         mismo tipo de objetivo (crecimiento, ingreso, preservación)
  Asset Allocation composición razonablemente comparable
  Riesgo           riesgo esperado del mismo orden de magnitud
  Moneda           misma moneda o FX ajustado explícitamente
  Liquidez         mismo nivel de liquidez que el portafolio real
  Horizonte        horizonte temporal de referencia coincidente
  Costos           neto contra neto, nunca bruto contra neto
  Restricciones    restricciones regulatorias o de universo comparables

Cada dimensión termina en `cumple`, `no_cumple` o `no_verificable`. Si
falta información para verificar una dimensión, se marca no verificable:
"no se asume comparabilidad por defecto" (QM XXIV, ESFS 8.5).

Estado final (D10 + ESFS-14):
  - no_elegible: alguna dimensión no cumple, o una dimensión CRÍTICA
    (`benchmark_critical_dimensions`) es no verificable.
  - parcial: todo cumple salvo dimensiones no críticas no verificables o
    con sustitutos declarados. Si habilita comparación lo decide
    `benchmark_partial_allows_comparison` (ESFS-14 lo deja abierto).
  - elegible: las ocho cumplen.

Es una regla de verificación, no un modelo matemático (ESFS 11.9).
"""

from __future__ import annotations

from dataclasses import dataclass, field

DIMENSIONS = ("objetivo", "asset_allocation", "riesgo", "moneda", "liquidez",
              "horizonte", "costos", "restricciones")
DIMENSION_LABEL = {
    "objetivo": "Objetivo", "asset_allocation": "Asset Allocation", "riesgo": "Riesgo",
    "moneda": "Moneda", "liquidez": "Liquidez", "horizonte": "Horizonte",
    "costos": "Costos", "restricciones": "Restricciones",
}
OK, FAIL, NV = "cumple", "no_cumple", "no_verificable"


@dataclass
class ComparableProfile:
    """Descripción de un portafolio o benchmark en las ocho dimensiones. None = sin información."""

    nombre: str
    tipo: str                                  # portafolio / market / policy / custom / peer
    objetivo: str | None = None
    composicion: dict[str, float] | None = None   # peso por clase de activo
    volatilidad: float | None = None              # anual
    moneda: str | None = None
    peso_fuera_0_3m: float | None = None          # liquidez
    horizonte: str | None = None
    costos: str | None = None                     # "neto" / "bruto"
    restricciones: str | None = None              # régimen de inversión / universo
    sustitutos: list[str] = field(default_factory=list)   # clases representadas por un sustituto
    notas: dict[str, str] = field(default_factory=dict)


def _allocation_distance(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys) / 2


def check_eligibility(portfolio: ComparableProfile, bench: ComparableProfile, params: dict) -> dict:
    risk_ratio_max = params.get("benchmark_risk_ratio_max")
    alloc_max = params.get("benchmark_allocation_max_distance_pct")
    liq_gap_max = params.get("benchmark_liquidity_max_gap_pct")
    critical_raw = params.get("benchmark_critical_dimensions")
    critical = {c.strip() for c in critical_raw.split(",")} if critical_raw else set()

    dims: dict[str, dict] = {}

    def put(dim, status, detail):
        dims[dim] = {"estado": status, "detalle": detail, "critica": dim in critical,
                     "nota": bench.notas.get(dim)}

    # Objetivo
    if portfolio.objetivo is None or bench.objetivo is None:
        put("objetivo", NV, "Falta el objetivo de alguno de los dos.")
    elif portfolio.objetivo == bench.objetivo:
        put("objetivo", OK, f"Ambos: {bench.objetivo}.")
    else:
        put("objetivo", FAIL, f"Portafolio: {portfolio.objetivo}. Benchmark: {bench.objetivo}.")

    # Asset Allocation
    if portfolio.composicion is None or bench.composicion is None or alloc_max is None:
        put("asset_allocation", NV, "Sin composición verificable" if alloc_max is not None
            else "Sin umbral de distancia en el Parameter Registry.")
    else:
        dist = _allocation_distance(portfolio.composicion, bench.composicion)
        if dist > float(alloc_max) / 100 + 1e-9:
            put("asset_allocation", FAIL, f"Distancia de composición {dist:.0%} (máximo {float(alloc_max):.0f}%).")
        elif bench.sustitutos:
            put("asset_allocation", NV, f"Distancia {dist:.0%}, pero {', '.join(bench.sustitutos)} "
                "se representa con un sustituto sin índice público.")
        else:
            put("asset_allocation", OK, f"Distancia de composición {dist:.0%} (máximo {float(alloc_max):.0f}%).")

    # Riesgo
    if portfolio.volatilidad is None or bench.volatilidad is None or risk_ratio_max is None:
        put("riesgo", NV, "Sin volatilidad de alguno de los dos o sin umbral.")
    else:
        ratio = max(bench.volatilidad, portfolio.volatilidad) / min(bench.volatilidad, portfolio.volatilidad)
        status = OK if ratio <= float(risk_ratio_max) + 1e-9 else FAIL
        put("riesgo", status, f"Volatilidad {bench.volatilidad:.1%} vs {portfolio.volatilidad:.1%} del "
            f"portafolio: {ratio:.1f} veces (máximo {float(risk_ratio_max):.1f}).")

    # Moneda
    if portfolio.moneda is None or bench.moneda is None:
        put("moneda", NV, "Moneda no informada.")
    elif portfolio.moneda == bench.moneda:
        put("moneda", OK, f"Ambos en {bench.moneda}.")
    else:
        put("moneda", FAIL, f"{bench.moneda} vs {portfolio.moneda} sin ajuste FX explícito.")

    # Liquidez
    if portfolio.peso_fuera_0_3m is None or bench.peso_fuera_0_3m is None or liq_gap_max is None:
        put("liquidez", NV, "Sin perfil de liquidez de alguno de los dos.")
    else:
        gap = abs(portfolio.peso_fuera_0_3m - bench.peso_fuera_0_3m)
        status = OK if gap <= float(liq_gap_max) / 100 + 1e-9 else FAIL
        put("liquidez", status, f"Peso fuera de 0-3m: {bench.peso_fuera_0_3m:.0%} vs "
            f"{portfolio.peso_fuera_0_3m:.0%} (diferencia máxima {float(liq_gap_max):.0f}%).")

    # Horizonte
    if portfolio.horizonte is None or bench.horizonte is None:
        put("horizonte", NV, "El benchmark no declara un horizonte de referencia.")
    elif portfolio.horizonte == bench.horizonte:
        put("horizonte", OK, f"Ambos: {bench.horizonte}.")
    else:
        put("horizonte", FAIL, f"Portafolio: {portfolio.horizonte}. Benchmark: {bench.horizonte}.")

    # Costos
    if portfolio.costos is None or bench.costos is None:
        put("costos", NV, "No se sabe si el benchmark es neto o bruto.")
    elif portfolio.costos == bench.costos:
        put("costos", OK, f"{bench.costos.capitalize()} contra {portfolio.costos}.")
    else:
        put("costos", FAIL, f"{bench.costos} contra {portfolio.costos}.")

    # Restricciones
    if portfolio.restricciones is None or bench.restricciones is None:
        put("restricciones", NV, "Sin información del régimen de inversión.")
    elif portfolio.restricciones == bench.restricciones:
        put("restricciones", OK, f"Mismo régimen: {bench.restricciones}.")
    else:
        put("restricciones", FAIL, f"Benchmark: {bench.restricciones}. Portafolio: {portfolio.restricciones}.")

    failed = [d for d in DIMENSIONS if dims[d]["estado"] == FAIL]
    nv_critical = [d for d in DIMENSIONS if dims[d]["estado"] == NV and dims[d]["critica"]]
    nv_other = [d for d in DIMENSIONS if dims[d]["estado"] == NV and not dims[d]["critica"]]
    if failed or nv_critical:
        estado = "no_elegible"
    elif nv_other:
        estado = "parcial"
    else:
        estado = "elegible"

    allows = params.get("benchmark_partial_allows_comparison")
    comparison = estado == "elegible" or (estado == "parcial" and str(allows).lower() in ("si", "sí", "true"))
    return {
        "benchmark": bench.nombre,
        "tipo": bench.tipo,
        "dimensiones": dims,
        "estado": estado,
        "no_cumple": failed,
        "no_verificables": nv_critical + nv_other,
        "habilita_comparacion": comparison,
        "regla": ("Benchmark no elegible: no se genera ranking; solo diferencias cualitativas "
                  "descriptivas (QM XII)." if not comparison else
                  "Comparación relativa habilitada" + (" con advertencia (estado parcial)."
                                                       if estado == "parcial" else ".")),
    }
