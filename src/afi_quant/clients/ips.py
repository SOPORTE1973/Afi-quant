"""
IPS, life balance sheet y catálogo de información de asesoría.

Fuentes:
  - ESFS-01 8.3 (entidades `Cliente`, `IPS`, `LifeBalanceSheet`) y 9.1
    (Data Requirement Matrix de M03 / Goals).
  - Decision Framework v1.0 5.2 (catálogo de información que puede
    solicitarse) y 5.3 (atributos de cada objetivo).
  - Decision Framework v1.0 4.1 (tres comportamientos: BLOQUEO /
    ADVERTENCIA / SIN IMPACTO MATERIAL) y ESFS-01 8.2 / 8.5 (criticidad
    C / NC / CP y estados de dato).

El catálogo NO inventa variables: cada fila cita la sección que la exige.
`evaluate_catalog` recorre el catálogo para un cliente y declara qué hay,
qué falta y qué bloquea cada faltante — Principio 2.3 del DF: la ausencia
de información es visible, nunca silenciosa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RiskLimits:
    """Límites de riesgo por perfil (ESFS 9.1: C para D8). Violación -> alerta, nunca ajuste automático."""

    volatilidad_max_pct: float | None = None
    var95_1m_max_pct: float | None = None
    es95_1m_max_pct: float | None = None
    drawdown_tolerado_pct: float | None = None


@dataclass
class LifeBalanceSheet:
    """ESFS 8.3 / Vol. I P2: C para el límite de ilíquidos (QM IX)."""

    capital_humano: float | None = None           # VP de ingresos laborales futuros
    activos_no_financieros: float | None = None   # inmuebles, empresa familiar
    pasivos: float | None = None                  # explícitos
    compromisos_futuros: float | None = None      # implícitos (educación, apoyo familiar)


@dataclass
class ExpectedFlow:
    """Calendario de flujos esperados del cliente (ESFS 9.1 / 9.7: C para LCR y Ladder)."""

    fecha: date | None
    monto: float                 # + entra al portafolio, − sale
    clasificacion: str           # aporte / retiro / impuesto / gasto IPS / capital call / distribución
    recurrencia: str = "única"   # única / mensual / anual
    hasta: date | None = None
    meta: str | None = None


@dataclass
class IPS:
    """Investment Policy Statement (ESFS 8.3). Referencia central de todo motor (QM I.1)."""

    ips_id: str
    vigente_desde: date
    revisar_antes_de: date                   # 1-3 años o ante eventos de vida (QM XVI)
    firmado: bool
    moneda_base: str
    pais_residencia: str
    segmento: str
    perfil_riesgo: str
    tolerancia_riesgo: str                   # declarada (cuestionario)
    capacidad_riesgo: str | None             # objetiva (balance, horizonte, estabilidad de ingresos)
    limites_riesgo: RiskLimits
    patrimonio_total: float | None           # incluye lo que está fuera de AFI
    inversiones_fuera_afi: float | None
    flujos_esperados: list[ExpectedFlow] = field(default_factory=list)
    restricciones_esg: list[str] | None = None
    restricciones_regulatorias: list[str] | None = None
    restricciones_familiares: list[str] | None = None
    limites_concentracion: dict[str, float] | None = None   # emisor / gestor / país
    life_balance_sheet: LifeBalanceSheet | None = None
    sintetico: bool = True

    def vigente(self, as_of: date) -> bool:
        return self.firmado and self.vigente_desde <= as_of <= self.revisar_antes_de


# ---------------------------------------------------------------------------
# Catálogo de información de asesoría
# ---------------------------------------------------------------------------

C, NC, CP = "CRITICAL", "NON-CRITICAL", "COMPLEMENTARIO"
BEHAVIOR = {C: "BLOQUEO", NC: "ADVERTENCIA", CP: "SIN IMPACTO MATERIAL"}


@dataclass(frozen=True)
class CatalogItem:
    grupo: str
    variable: str
    criticidad: str
    habilita: str          # qué cálculo o decisión habilita (regla de admisión ESFS 9)
    fuente_doc: str
    getter: object         # callable(ctx) -> valor o None

    def value(self, ctx):
        try:
            return self.getter(ctx)
        except (AttributeError, KeyError, TypeError, StopIteration):
            return None


def _goals(ctx):
    return ctx["client"].goals


def _vehicles(ctx):
    return list(ctx["universe"].values())


def _all_or_none(values):
    values = list(values)
    return values if values and all(v is not None for v in values) else None


CATALOG: list[CatalogItem] = [
    # Cliente e IPS
    CatalogItem("Cliente e IPS", "IPS vigente y firmado", C, "Referencia central; sin IPS no hay ClientGoal ni Construction",
                "ESFS 9.1; QM I.1", lambda c: c["ips"].ips_id if c["ips"].vigente(c["as_of"]) else None),
    CatalogItem("Cliente e IPS", "Moneda base", C, "Consistencia multi-moneda; sin FX confiable → Model Block",
                "ESFS 9.1", lambda c: c["ips"].moneda_base),
    CatalogItem("Cliente e IPS", "País de residencia y segmento", CP, "Contexto regulatorio y tributario",
                "ESFS 8.3", lambda c: f"{c['ips'].pais_residencia} · {c['ips'].segmento}"),
    CatalogItem("Cliente e IPS", "Perfil y tolerancia al riesgo declarada", C, "Compatibilidad riesgo-IPS (D8)",
                "DF 5.2; ESFS 9.1", lambda c: f"{c['ips'].perfil_riesgo} · {c['ips'].tolerancia_riesgo}"),
    CatalogItem("Cliente e IPS", "Capacidad de riesgo (objetiva)", NC, "Contrasta la tolerancia declarada con el balance",
                "DF 5.2", lambda c: c["ips"].capacidad_riesgo),
    CatalogItem("Cliente e IPS", "Límites de riesgo por perfil (vol / VaR / ES)", C, "D8: ¿el riesgo es compatible con el IPS?",
                "ESFS 9.1; QM XVIII D8",
                lambda c: _all_or_none([c["ips"].limites_riesgo.volatilidad_max_pct,
                                        c["ips"].limites_riesgo.var95_1m_max_pct,
                                        c["ips"].limites_riesgo.es95_1m_max_pct])),
    CatalogItem("Cliente e IPS", "Drawdown tolerado", NC, "Calibrar tolerancia real a pérdidas (QM V)",
                "QM V — Maximum Drawdown", lambda c: c["ips"].limites_riesgo.drawdown_tolerado_pct),
    CatalogItem("Cliente e IPS", "Patrimonio total (incluye fuera de AFI)", NC, "Unidad de análisis Patrimonio",
                "DF 5.1, 5.2", lambda c: c["ips"].patrimonio_total),
    CatalogItem("Cliente e IPS", "Inversiones existentes fuera de AFI", NC, "Liquidez consolidada; sin ellas → ADVERTENCIA",
                "DF 5.2; DF 7 paso 2", lambda c: c["ips"].inversiones_fuera_afi),
    CatalogItem("Cliente e IPS", "Life balance sheet (capital humano, activos, pasivos, compromisos)", C,
                "Límite máximo de ilíquidos (QM IX)", "ESFS 9.1; Vol. I P2",
                lambda c: _all_or_none([c["ips"].life_balance_sheet.capital_humano,
                                        c["ips"].life_balance_sheet.activos_no_financieros,
                                        c["ips"].life_balance_sheet.pasivos,
                                        c["ips"].life_balance_sheet.compromisos_futuros])),
    CatalogItem("Cliente e IPS", "Restricciones ESG / regulatorias / familiares", NC,
                "Constraints de optimización (C si el IPS las declara vinculantes)", "ESFS 9.1; QM XXIII P6",
                lambda c: _all_or_none([c["ips"].restricciones_esg, c["ips"].restricciones_regulatorias,
                                        c["ips"].restricciones_familiares])),
    CatalogItem("Cliente e IPS", "Límites de concentración (emisor / gestor / país)", NC, "D7 y constraints",
                "ESFS 9.1", lambda c: c["ips"].limites_concentracion),
    # Metas
    CatalogItem("Metas", "Monto y fecha de cada meta", C, "Probabilidad de éxito por meta",
                "DF 5.3; ESFS 9.1", lambda c: _all_or_none(g.monto_objetivo for g in _goals(c))),
    CatalogItem("Metas", "Horizonte de cada meta (corto / medio / largo)", C, "Etiquetado obligatorio por horizonte",
                "ESFS 9.1; DF 5.4", lambda c: c.get("horizons") or None),
    CatalogItem("Metas", "Moneda de cada meta", C, "Meta y cartera en la misma moneda o FX explícito",
                "DF 5.3", lambda c: _all_or_none(g.moneda for g in _goals(c))),
    CatalogItem("Metas", "Probabilidad deseada de cada meta", NC, "Umbral de alerta de ClientGoal",
                "DF 5.3; ESFS 11.10",
                lambda c: _all_or_none(g.probabilidad_deseada for g in _goals(c) if g.fecha is not None)),
    CatalogItem("Metas", "Prioridad relativa de cada meta", C, "Trade-off entre metas (decisión humana)",
                "DF 5.3; QM XX", lambda c: _all_or_none(g.prioridad for g in _goals(c))),
    CatalogItem("Metas", "Liquidez requerida en la fecha de cada meta", C, "Liquidity Ladder",
                "DF 5.3", lambda c: _all_or_none(g.liquidez_requerida for g in _goals(c))),
    # Flujos
    CatalogItem("Flujos", "Calendario de flujos esperados (aportes, retiros, impuestos, gastos)", C,
                "LCR por bucket, Ladder, cash flow forecasting", "ESFS 9.1, 9.7; QM IX",
                lambda c: c["ips"].flujos_esperados or None),
    CatalogItem("Flujos", "Flujos realizados fechados y clasificados", C, "TWR (subperíodos) y XIRR",
                "ESFS 9.3; QM IV", lambda c: c.get("realized_flows")),
    CatalogItem("Flujos", "Fees separados del retorno bruto", NC, "Comparación neto contra neto",
                "ESFS 9.3; QM XVI", lambda c: _all_or_none(v.costo_total_pct for v in _vehicles(c))),
    # Cartera y vehículos
    CatalogItem("Cartera y vehículos", "Posiciones por instrumento", C, "Pesos, exposición, base de todo cálculo",
                "ESFS 9.2", lambda c: c.get("positions")),
    CatalogItem("Cartera y vehículos", "SAA vigente y bandas", C, "Drift y materialidad (D1)",
                "ESFS 9.2", lambda c: c.get("saa") if c.get("band") is not None else None),
    CatalogItem("Cartera y vehículos", "Mapeo a clase / subclase (taxonomía)", C, "Agregación y HHI por dimensión",
                "ESFS 9.2", lambda c: _all_or_none(v.subclase for v in _vehicles(c))),
    CatalogItem("Cartera y vehículos", "Serie de NAV a frecuencia nativa", C, "TWR, riesgo, correlaciones",
                "ESFS 9.3; QM XVI", lambda c: _all_or_none(v.series.points or None for v in _vehicles(c))),
    CatalogItem("Cartera y vehículos", "Clasificación de liquidez del vehículo (valuación, rescate, lock-up)", C,
                "Buckets 0-3m / 3-12m / >12m", "ESFS 9.2; QM IX",
                lambda c: _all_or_none(v.ventana_rescate for v in _vehicles(c))),
    CatalogItem("Cartera y vehículos", "Costo total por vehículo (TAC)", NC, "Dimensión Costos del benchmark; alternativas de rebalanceo",
                "ESFS 8.3, 9.2", lambda c: _all_or_none(v.costo_total_pct for v in _vehicles(c))),
    CatalogItem("Cartera y vehículos", "Costos de transacción e impacto fiscal", NC, "Comparación de alternativas de rebalanceo",
                "ESFS 9.2; QM XIII", lambda c: c.get("transaction_costs")),
    CatalogItem("Cartera y vehículos", "Estado en Approved List + ODD", C, "D3-D5 y Nivel 3 en decisiones de fondo",
                "ESFS 9.9", lambda c: _all_or_none(v.estado_approved_list for v in _vehicles(c))),
    CatalogItem("Cartera y vehículos", "Holdings subyacentes (look-through)", NC, "Factor risk y concentración oculta",
                "ESFS 9.4; DF 4.3", lambda c: c.get("look_through")),
    # Mercado y supuestos
    CatalogItem("Mercado y supuestos", "CMAs institucionales (μ, σ, correlaciones)", C, "MVO robusto; nunca del asesor",
                "ESFS 9.6; QM VII", lambda c: c.get("cma_institucional")),
    CatalogItem("Mercado y supuestos", "Benchmark candidato + EligibilityCheck (8 dimensiones)", C,
                "Excess Return, TE, Beta, IR, atribución", "ESFS 9.8; QM XII", lambda c: c.get("benchmark_check")),
    CatalogItem("Mercado y supuestos", "Serie FX", C, "Todo cálculo multi-moneda",
                "ESFS 9.4; QM XVII", lambda c: "no requerida: cartera 100% CLP" if c.get("single_currency") else None),
    CatalogItem("Mercado y supuestos", "Escenarios de stress del Comité (versionados)", C, "Hypothetical Stress (D13)",
                "ESFS 9.8; QM XI", lambda c: c.get("scenario_library")),
    CatalogItem("Mercado y supuestos", "Curvas de tasas completas", C, "Sensibilidad a tasas y escenarios",
                "ESFS 9.4; QM XVI", lambda c: c.get("rate_curves")),
]


def evaluate_catalog(ctx: dict) -> list[dict]:
    """Estado de cada variable del catálogo para este cliente y comportamiento si falta."""
    rows = []
    for item in CATALOG:
        value = item.value(ctx)
        synthetic = ctx.get("synthetic_fields", set())
        if value is None:
            estado = "missing_critical" if item.criticidad == C else "missing_non_critical"
            comportamiento = BEHAVIOR[item.criticidad]
        elif item.variable in synthetic:
            estado = "degraded"
            comportamiento = "ADVERTENCIA"
        else:
            estado = "available"
            comportamiento = "—"
        rows.append({
            "grupo": item.grupo, "variable": item.variable, "criticidad": item.criticidad,
            "estado": estado, "comportamiento": comportamiento, "habilita": item.habilita,
            "fuente_doc": item.fuente_doc,
            "valor": value if isinstance(value, (str, int, float)) else None,
        })
    return rows
