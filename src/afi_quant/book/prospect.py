"""
Prospecto desde la Mesa Central -> motor real.

El asistente "Nuevo cliente" construye la propuesta en el navegador con una copia
de las reglas del motor. Esta es la entrada formal: lee la ficha que descarga el
asistente (formato `afi-prospecto-v1`), arma el ClientProfile y el IPS, y corre la
construcción de onboarding con `LifecycleSimulation.construct`, el mismo camino
que usa el libro. Si la ficha trae la propuesta del navegador, la compara.

    python -m afi_quant.book.prospect prospecto-PRO-XXXXX.json

No inventa datos: lo que el asesor no declaró queda en None y el catálogo lo
reporta como faltante. El IPS queda sin firmar hasta que se firme con el cliente.
"""

from __future__ import annotations

import json
import sys
from datetime import date

from afi_quant.clients.ips import IPS, LifeBalanceSheet, RiskLimits
from afi_quant.clients.profile import ClientProfile, Goal

FORMAT = "afi-prospecto-v1"


def _num(x):
    return None if x in (None, "") else float(x)


def _text_list(x):
    return None if x in (None, "") else [str(x)]


def from_ficha(ficha: dict) -> tuple[ClientProfile, IPS, date]:
    if ficha.get("formato") != FORMAT:
        raise ValueError(f"Formato desconocido: {ficha.get('formato')!r} (se espera {FORMAT})")
    p, as_of = ficha["prospecto"], date.fromisoformat(ficha["datos_al"])
    c, r, pat = p["cliente"], p["riesgo"], p["patrimonio"]
    goals = []
    for m in p["metas"]:
        fecha = None if m.get("reserva") or not m.get("fecha") else date.fromisoformat(m["fecha"])
        prob = _num(m.get("prob_deseada"))
        goals.append(Goal(m["key"], m.get("nombre") or m["key"], m.get("prioridad") or "importante",
                          float(m["objetivo"]), fecha, float(m["capital"]), _num(m.get("aporte")) or 0.0,
                          probabilidad_deseada=None if prob is None or fecha is None else prob / 100,
                          liquidez_requerida=m.get("liquidez") or None))
    client = ClientProfile(p["id"], c.get("nombre") or p["id"],
                           date.fromisoformat(c["nacimiento"]) if c.get("nacimiento") else None,
                           r.get("perfil") or None, int(_num(r.get("puntaje"))) if _num(r.get("puntaje")) is not None else None,
                           None, goals=goals, nota="Prospecto ingresado desde la Mesa Central.")
    lbs_vals = [_num(pat.get(k)) for k in ("capital_humano", "activos_nf", "pasivos", "compromisos")]
    ips = IPS(
        ips_id=f"IPS-{p['id']}-borrador", vigente_desde=as_of, revisar_antes_de=date(as_of.year + 3, as_of.month, 1),
        firmado=False, moneda_base="CLP", pais_residencia=c.get("pais") or None, segmento=c.get("segmento") or None,
        perfil_riesgo=r.get("perfil") or None,
        tolerancia_riesgo=f"{r.get('perfil')} (cuestionario {r.get('puntaje')}/100)" if r.get("puntaje") not in (None, "") else r.get("perfil"),
        capacidad_riesgo=r.get("capacidad") or None,
        limites_riesgo=RiskLimits(_num(r.get("vol")), _num(r.get("var")), _num(r.get("es")), _num(r.get("dd"))),
        patrimonio_total=_num(pat.get("total")), inversiones_fuera_afi=_num(pat.get("fuera")),
        restricciones_esg=_text_list(pat.get("esg")), restricciones_regulatorias=_text_list(pat.get("regulatorias")),
        restricciones_familiares=_text_list(pat.get("familiares")),
        limites_concentracion={"administradora": _num(pat["admin"])} if _num(pat.get("admin")) is not None else None,
        life_balance_sheet=LifeBalanceSheet(*lbs_vals) if any(v is not None for v in lbs_vals) else None,
    )
    return client, ips, as_of


def construct_prospect(ficha: dict) -> dict:
    from afi_quant.portfolio.universe import default_universe
    from afi_quant.simulation.lifecycle import LifecycleSimulation
    from afi_quant.simulation.parameters import SCENARIO_LIBRARY, simulation_registry

    client, ips, as_of = from_ficha(ficha)
    sim = LifecycleSimulation(client, default_universe(), simulation_registry(), as_of, ips=ips,
                              scenario_library=SCENARIO_LIBRARY)
    case, _ = sim.construct(as_of, {g.key: g.capital_inicial for g in client.goals},
                            "onboarding — prospecto de la Mesa Central")
    con = case.engine_results["construction"]
    if con.insufficient_data:
        return {"insuficiente": con.insufficient_data_reason}
    goals = case.engine_results.get("clientgoal")
    metas = goals.values["metas"] if goals is not None and not goals.insufficient_data else {}
    return {
        "datos_al": as_of.isoformat(),
        "sleeves": {k: {"horizonte": s["horizonte"], "tope": s["tope_volatilidad"], "pesos": s["pesos"]}
                    for k, s in con.values["sleeves"].items()},
        "no_calculado": con.values["no_calculado"],
        "total": con.values["asignacion_total"],
        "probabilidades": {k: m.get("prob_exito") for k, m in metas.items()},
        "niveles": {k: a.get("nivel") for k, a in (case.alternatives or {}).items()},
    }


def compare(engine: dict, browser: dict | None) -> list[str]:
    """Diferencias entre el motor y la propuesta calculada en el navegador (vacía = idénticas)."""
    if not browser:
        return ["la ficha no trae propuesta del navegador"]
    diffs = []
    for k in set(engine["total"]) | set(browser["total"]):
        if abs(engine["total"].get(k, 0) - browser["total"].get(k, 0)) > 1e-9:
            diffs.append(f"peso total {k}")
    for k, p in engine["probabilidades"].items():
        b = browser["probabilidades"].get(k)
        if (p is None) != (b is None) or (p is not None and abs(p - b) > 1e-9):
            diffs.append(f"probabilidad {k}")
    for k, n in engine["niveles"].items():
        if browser["niveles"].get(k) != n:
            diffs.append(f"nivel {k}")
    return diffs


def main(path: str) -> None:
    with open(path, encoding="utf-8") as fh:
        ficha = json.load(fh)
    out = construct_prospect(ficha)
    if "insuficiente" in out:
        print("Sin construcción:", out["insuficiente"])
        return
    print(f"Prospecto {ficha['prospecto']['id']} · datos al {out['datos_al']}")
    for k, s in out["sleeves"].items():
        pesos = ", ".join(f"{v} {w:.0%}" for v, w in s["pesos"].items())
        prob = out["probabilidades"].get(k)
        print(f"  {k}: horizonte {s['horizonte']}, tope {s['tope']:.1%} -> {pesos}"
              + (f" · prob. {prob:.0%}" if prob is not None else "") + f" · nivel {out['niveles'].get(k)}")
    for k, why in out["no_calculado"].items():
        print(f"  {k}: sin cartera — {why}")
    diffs = compare(out, ficha.get("propuesta_navegador"))
    print("Propuesta del navegador:", "idéntica al motor" if not diffs else "difiere en " + ", ".join(diffs))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
