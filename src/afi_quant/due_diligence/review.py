"""
Due diligence centralizado por fondo (M10; ESFS 10.6; Volumen II).

Se hace UNA vez por vehículo y lo consumen todos los clientes que lo tienen:
el Monitoring Engine lee el estado de cada fondo para la dimensión
"vehículos" de cada cuenta.

Qué hace el sistema y qué no (Vol II; QM XX):
  - Calcula la IDD cuantitativa (Etapa 2 — screening): trayectoria, retorno,
    riesgo, retorno relativo contra el índice pasivo cuando existe, y la
    concentración de la cartera informada a la CMF.
  - Evalúa las señales tempranas cuantitativas de deterioro (Checklist 2) con
    umbrales del Parameter Registry. Una señal no cambia el estado: propone
    análisis de causa raíz (Vol II 7.2).
  - Los pilares cualitativos (People, Philosophy, Process, Parent, Price) y la
    ODD requieren DDQ, entrevistas y verificación con proveedores: el sistema
    no los infiere de la performance (anti performance-chasing, Vol II B11 P4).
    Sin ellos quedan "pendientes" y, por la regla de veto, el vehículo no es
    institucionalmente elegible (ESFS 10.6).
  - El estado en la Approved List lo decide el Comité. Sin decisión registrada,
    el estado es "Propuesto" (ESFS-05 sobre la lista única de estados).
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from afi_quant.engines.relative import chain, relative_metrics
from afi_quant.engines.risk import max_drawdown
from afi_quant.engines.series import month_end_points, period_returns

DOSSIERS = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "fund_dossiers.json"

PILLARS = {
    "People": "Equipo, estabilidad, riesgo de persona clave y sucesión (Vol II B2)",
    "Philosophy": "Fuente de ventaja declarada y coherencia con el mandato (Vol II B1)",
    "Process": "Proceso de inversión documentado y consistente con la atribución (Vol II B3)",
    "Parent": "Administradora: propiedad, incentivos, recursos de riesgo y compliance (Vol II B5)",
    "Price": "Comisiones y costos totales frente a alternativas comparables (Vol II B1.2)",
}
ODD_ITEMS = ("Valorización independiente", "Controles de caja y segregación de funciones",
             "Proveedores: custodio, auditor, administrador", "Legal y cumplimiento",
             "Continuidad operacional y tecnología", "Riesgo de contraparte")
STAGES = ("Universo y elegibilidad", "Screening cuantitativo", "IDD profunda", "ODD",
          "Tesis integrada", "Comité y Approved List", "Monitoreo")
PARAMS = ("dd_min_track_record_years", "dd_underperformance_months", "dd_te_increase_ratio",
          "dd_top5_max_pct", "dd_single_position_max_pct")


@dataclass
class ApprovedListEntry:
    """Decisión del Comité. Sin registro, el vehículo está 'Propuesto'."""
    estado: str = "Propuesto"
    fecha: date | None = None
    acta: str | None = None
    limites_uso: str | None = None


@dataclass
class FundReview:
    key: str
    ficha: dict
    idd: dict
    senales: list[dict]
    pilares: dict
    odd: dict
    etapas: dict
    approved_list: ApprovedListEntry
    elegibilidad: dict
    no_evaluado: list[str] = field(default_factory=list)


def load_dossiers() -> dict:
    return json.loads(DOSSIERS.read_text(encoding="utf-8"))


def _years(p0, p1) -> float:
    return (p1.fecha - p0.fecha).days / 365.25


def quantitative_idd(vehicle, as_of: date, index_series=None, rf_series=None) -> dict:
    """Screening cuantitativo (Vol II Bloque IV, QM IV-V) sobre NAV ajustado mensual."""
    pts = month_end_points([p for p in vehicle.series.points if p.fecha <= as_of])
    rets = period_returns(pts)
    out = {"desde_datos": pts[0].fecha, "hasta": pts[-1].fecha, "meses": len(rets),
           "anios_datos": _years(pts[0], pts[-1])}
    for label, n in (("1a", 12), ("3a", 36), ("5a", 60)):
        if len(rets) >= n:
            out[f"retorno_{label}"] = (1 + chain(rets[-n:])) ** (12 / n) - 1
    window = rets[-36:]
    if len(window) >= 36:
        out["volatilidad_3a"] = statistics.stdev(window) * math.sqrt(12)
        dd = max_drawdown(pts[-37:])
        out["max_drawdown_3a"] = dd["max_drawdown"]
        if rf_series is not None:
            rf_pts = month_end_points([p for p in rf_series.points if p.fecha <= as_of])
            rf = dict(zip([p.fecha for p in rf_pts[1:]], period_returns(rf_pts)))
            ex = [r - rf[p.fecha] for p, r in zip(pts[1:], rets) if p.fecha in rf][-36:]
            if len(ex) >= 36 and statistics.stdev(ex) > 0:
                out["sharpe_3a"] = statistics.fmean(ex) * 12 / (statistics.stdev(ex) * math.sqrt(12))
        if dd["max_drawdown"] < 0:
            out["calmar_3a"] = out["retorno_3a"] / -dd["max_drawdown"]
        if not getattr(vehicle, "precio_de_mercado", True):
            # NAV suavizado (QM X): un Sharpe o Calmar sobre esa volatilidad no es comparable.
            out.pop("sharpe_3a", None)
            out.pop("calmar_3a", None)
            out["advertencia"] = ("NAV sin precio de mercado diario: volatilidad y drawdown subestiman el "
                                  "riesgo; Sharpe y Calmar no se informan (QM X, AD-07).")
    if index_series is not None:
        idx = {p.fecha.replace(day=1): p for p in month_end_points(
            [p for p in index_series.points if p.fecha <= as_of])}
        common = [p for p in pts if p.fecha.replace(day=1) in idx]
        fr = period_returns(common)
        ir = period_returns([idx[p.fecha.replace(day=1)] for p in common])
        months = [p.fecha for p in common[1:]]
        rel = relative_metrics(fr[-60:], ir[-60:], months[-60:])
        out["relativo"] = rel
        roll = [chain(fr[i - 12:i]) - chain(ir[i - 12:i]) for i in range(12, len(fr) + 1)]
        out["exceso_12m_rolling"] = [{"hasta": months[i - 1], "exceso": x}
                                     for i, x in zip(range(12, len(fr) + 1), roll)]
        tes = [statistics.stdev([a - b for a, b in zip(fr[i - 36:i], ir[i - 36:i])]) * math.sqrt(12)
               for i in range(36, len(fr) + 1)]
        out["te_36m_rolling"] = [{"hasta": months[i - 1], "te": t}
                                 for i, t in zip(range(36, len(fr) + 1), tes)]
    return out


def early_warnings(idd: dict, ficha: dict, params: dict, data_quality: dict | None) -> tuple[list[dict], list[str]]:
    """Checklist 2 del Vol II con lo que es medible. Cada señal trae su evidencia."""
    out, skipped = [], [p for p in PARAMS if params.get(p) is None]
    cart = ficha.get("cartera") or {}

    def add(tipo, texto, evidencia):
        out.append({"tipo": tipo, "senal": texto, "evidencia": evidencia})

    min_tr = params.get("dd_min_track_record_years")
    if min_tr is not None:
        inicio = date.fromisoformat(ficha["inicio_operaciones"])
        years = (idd["hasta"] - inicio).days / 365.25
        if years < float(min_tr):
            add("Trayectoria", f"Trayectoria de {years:.1f} años, bajo el mínimo de {min_tr} años",
                f"inicio de operaciones {inicio.isoformat()} (ficha CMF)")
    n_under = params.get("dd_underperformance_months")
    roll = idd.get("exceso_12m_rolling") or []
    if n_under is not None and roll:
        streak = 0
        for r in reversed(roll):
            if r["exceso"] >= 0:
                break
            streak += 1
        if streak >= int(n_under):
            add("Underperformance persistente", f"{streak} meses seguidos con exceso 12m negativo contra el índice",
                f"último exceso 12m {roll[-1]['exceso']:+.1%}")
    ratio = params.get("dd_te_increase_ratio")
    tes = idd.get("te_36m_rolling") or []
    if ratio is not None and len(tes) >= 12:
        med = statistics.median(t["te"] for t in tes)
        if tes[-1]["te"] > float(ratio) * med:
            add("Aumento de tracking error", f"TE 36m de {tes[-1]['te']:.1%}, más de {ratio}× su mediana ({med:.1%})",
                "rolling 36 meses contra el índice pasivo")
    top5 = params.get("dd_top5_max_pct")
    if top5 is not None and cart.get("top5_pct") is not None and cart["top5_pct"] > float(top5):
        add("Concentración", f"Las 5 mayores posiciones suman {cart['top5_pct']:.0f}% (umbral {top5}%)",
            f"cartera IFRS {cart['periodo']}")
    single = params.get("dd_single_position_max_pct")
    if single is not None and cart.get("mayor_emisor_pct") is not None and cart["mayor_emisor_pct"] > float(single):
        add("Concentración en una posición", f"{cart['mayor_emisor']}: {cart['mayor_emisor_pct']:.1f}% del fondo",
            cart.get("look_through") or f"cartera IFRS {cart['periodo']}")
    if ficha.get("cartera", {}).get("look_through") and "privado" in ficha["cartera"]["detalle"]:
        add("Liquidez", "Activo subyacente privado dentro de un fondo rescatable",
            f"{ficha['cartera']['detalle']}; rescate {ficha.get('liquidez_declarada') or 'sin dato'}")
    if data_quality and data_quality.get("estado") == "pending_validation":
        add("Calidad de NAV", "Datos de NAV pendientes de validación (ESFS 8.4)",
            f"{len(data_quality.get('outliers', []))} saltos revertidos, {len(data_quality.get('stale', []))} tramos repetidos")
    return out, skipped


def review_fund(key, vehicle, ficha, as_of, params, index_series=None, rf_series=None,
                data_quality=None, entry: ApprovedListEntry | None = None) -> FundReview:
    idd = quantitative_idd(vehicle, as_of, index_series, rf_series)
    senales, skipped = early_warnings(idd, ficha, params, data_quality)
    pilares = {p: {"estado": "pendiente", "que_falta": d, "fuente_requerida": "DDQ + reuniones con el gestor"}
               for p, d in PILLARS.items()}
    pilares["Price"]["fuente_requerida"] = "reglamento / factsheet (TAC y comisiones por serie)"
    odd = {"estado": "pendiente", "items": {i: "pendiente" for i in ODD_ITEMS},
           "regla": "ODD Fail/High-Risk ⇒ inelegible con independencia de la IDD; sin ODD no hay elegibilidad"}
    etapas = {s: "pendiente" for s in STAGES}
    etapas["Universo y elegibilidad"] = "completa" if ficha.get("vigencia") == "Vigente" else "pendiente"
    etapas["Screening cuantitativo"] = "completa" if idd.get("volatilidad_3a") is not None else "parcial"
    etapas["Monitoreo"] = "señales activas" if senales else "sin señales"
    entry = entry or ApprovedListEntry()
    faltan = [p for p, v in pilares.items() if v["estado"] == "pendiente"] + (["ODD"] if odd["estado"] == "pendiente" else [])
    elegible = entry.estado == "Approved-Active" and odd["estado"] not in ("pendiente", "Fail", "High-Risk")
    return FundReview(
        key=key, ficha=ficha, idd=idd, senales=senales, pilares=pilares, odd=odd, etapas=etapas,
        approved_list=entry,
        elegibilidad={
            "elegible": elegible,
            "motivo": ("Approved-Active con ODD aprobada" if elegible else
                       f"Estado '{entry.estado}' sin decisión del Comité; pendiente: {', '.join(faltan)}"),
            "nivel_maximo_decisiones_de_fondo": 3 if elegible else 2,
            "propuesta": ("Análisis de causa raíz antes del Comité (Vol II 7.2)" if senales
                          else "Completar IDD cualitativa y ODD para presentar al Comité"),
        },
        no_evaluado=skipped,
    )
