"""
Cobertura de todos los fondos del conector: screening de Etapa 1-2 (Vol II 12.2-12.3).

El universo de CONSTRUCCIÓN sigue siendo el de los fondos modelo: un fondo entra a una
propuesta de cartera solo si está Approved-Active (ESFS 10.6) y su subclase tiene CMAs en
el Parameter Registry. El resto queda en COBERTURA: ficha, rentabilidades de mercado y
señales de screening, con la IDD de riesgo (volatilidad, caída, cartera) calculada a
pedido desde el conector.

Las rentabilidades del conector vienen en porcentaje y acumuladas (y1, y3, desde el
inicio de la serie); aquí se pasan a decimales y se anualizan las de más de un año.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "fund_catalog.json"
REFERENCE_TYPES = {"AFP": "Referencia: multifondo de pensiones", "UF": "Referencia: UF / benchmark"}
ALTERNATIVE_CLASSES = {"Private Equity", "Real Estate", "Deuda Privada"}


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _years(a: str | None, b: date) -> float | None:
    if not a:
        return None
    try:
        d = date.fromisoformat(a[:10])
    except ValueError:
        return None
    return (b - d).days / 365.25


def main_series(fund: dict) -> dict | None:
    """La serie con más historia (la que permite el screening más largo)."""
    s = [x for x in fund.get("series", []) if x.get("seguimiento")]
    return min(s, key=lambda x: x.get("desde") or "9999") if s else None


def screen_fund(fund: dict, as_of: date, params: dict, model_ruts: dict[str, str], held: set[str]) -> dict:
    s = main_series(fund)
    kind = REFERENCE_TYPES.get(fund["tipo"])
    rets = {}
    if s:
        rets["y1"] = s["y1"] / 100 if s.get("y1") is not None else None
        rets["y3_anual"] = (1 + s["y3"] / 100) ** (1 / 3) - 1 if s.get("y3") is not None else None
        yrs = _years(s.get("desde"), date.fromisoformat(s["hasta"])) if s.get("hasta") else None
        rets["inicio_anual"] = ((1 + s["inicio"] / 100) ** (1 / yrs) - 1) if s.get("inicio") is not None and yrs and yrs >= 1 else None
        rets["ytd"] = s["ytd"] / 100 if s.get("ytd") is not None else None
    signals = []

    def add(tipo, texto):
        signals.append({"tipo": tipo, "senal": texto})

    track = _years(fund.get("inicio_operaciones"), as_of)
    min_tr = params.get("dd_min_track_record_years")
    if not kind:
        if min_tr is not None and track is not None and track < float(min_tr):
            add("Trayectoria", f"{track:.1f} años de operación, bajo el mínimo de {min_tr}")
        if not fund.get("clase") or not fund.get("subclase"):
            add("Clasificación", "Sin clase o subclase en la taxonomía AFI: no entra a la matriz de límites del Comité")
        if not fund.get("liquidez"):
            add("Liquidez", "Sin dato de liquidez de rescate en la ficha")
        elif fund["liquidez"].startswith("No Rescatable"):
            add("Alternativo", f"{fund['liquidez']}: requiere el Motor de Alternativos (TVPI, DPI, IRR, capital calls)")
        if not s:
            add("Datos", "Sin serie con rentabilidad en seguimiento: no hay screening cuantitativo")
        if fund.get("inversionista") and "Calificado" in fund["inversionista"]:
            add("Acceso", "Solo inversionistas calificados: verificar idoneidad del cliente")
    model = model_ruts.get(fund["rut"])
    return {
        "rut": fund["rut"], "nombre": fund.get("nombre"), "nombre_corto": fund.get("nombre_corto"),
        "administradora": fund.get("administradora"), "clase": fund.get("clase"), "subclase": fund.get("subclase"),
        "tipo": fund.get("tipo"), "liquidez": fund.get("liquidez"), "inversionista": fund.get("inversionista"),
        "inicio_operaciones": fund.get("inicio_operaciones"), "anios_operacion": track, "vigencia": fund.get("vigencia"),
        "referencia": kind, "serie": s, "series": [x["serie"] for x in fund.get("series", [])],
        "rentabilidad": rets, "senales": signals,
        "alternativo": (fund.get("clase") in ALTERNATIVE_CLASSES and (fund.get("liquidez") or "").startswith("No Rescatable")),
        "universo": "construcción" if model else ("referencia" if kind else "cobertura"),
        "clave_modelo": model, "en_cartera_de_clientes": fund["rut"] in held,
        "estado": "Propuesto",
        "etapa": ("IDD cuantitativa completa" if model else
                  "Screening con rentabilidades; riesgo y cartera a pedido" if s else "Solo ficha"),
    }


def screen_catalog(as_of: date, params: dict, model_ruts: dict[str, str], held: set[str]) -> dict:
    cat = load_catalog()
    rows = [screen_fund(f, as_of, params, model_ruts, held) for f in cat["fondos"]]
    return {"fuente": cat["fuente"], "nota": cat["nota"], "fondos": rows,
            "resumen": {"total": len(rows), "fondos": sum(1 for r in rows if not r["referencia"]),
                        "referencias": sum(1 for r in rows if r["referencia"]),
                        "con_rentabilidad": sum(1 for r in rows if r["serie"]),
                        "universo_construccion": sum(1 for r in rows if r["universo"] == "construcción"),
                        "alternativos": sum(1 for r in rows if r["alternativo"])}}
