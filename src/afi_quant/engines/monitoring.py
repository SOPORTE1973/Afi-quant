"""
Motor de Monitoreo (CORE) — "¿en qué cuentas debo actuar hoy?" (QM II.8; ESFS 11.8).

No introduce modelos propios: lee los resultados que los demás motores ya
produjeron para cada cliente y el estado de due diligence de cada fondo, y
aplica reglas fijas por dimensión.

Restricción crítica (DF 2.1): prioriza ENTRE cuentas, pero nunca colapsa las
dimensiones de un mismo cliente en un puntaje. Cada dimensión conserva su
propio estado y su evidencia. El orden de la lista es lexicográfico y
declarado: primero más dimensiones en alerta, luego más en atención, luego
mayor patrimonio. No hay pesos entre dimensiones.

Dimensiones: el DF menciona "seis dimensiones" sin enumerarlas (OPEN ISSUE
ESFS-02). Esta es una PROPUESTA, cada una ligada a una decisión de la
Decision Library:
  metas         D2  probabilidad de cada meta frente a la deseada en el IPS
  riesgo_ips    D8  volatilidad, VaR, ES y caída frente a los límites del IPS
  liquidez      D9  cobertura de liquidez (LCR) de los próximos 12 meses
  concentracion D7  peso por administradora frente al límite del IPS y HHI
  drift         D1  mayor desvío frente a la asignación objetivo
  vehiculos     D3  fondos en cartera sin due diligence completo o con señales
Un motor en `insufficient_data` deja su dimensión en "sin datos" con nota,
nunca la omite (ESFS 11.8).
"""

from __future__ import annotations

OK, ATTN, ALERT, NODATA = "ok", "atencion", "alerta", "sin_datos"
DIMENSIONS = ("metas", "riesgo_ips", "liquidez", "concentracion", "drift", "vehiculos")
DIMENSION_NAMES = {"metas": "Metas", "riesgo_ips": "Riesgo vs IPS", "liquidez": "Liquidez",
                   "concentracion": "Concentración", "drift": "Drift", "vehiculos": "Vehículos (DD)"}
PRIORITY_RULE = ("Orden lexicográfico: más dimensiones en alerta, luego más en atención, luego mayor "
                 "patrimonio. Sin pesos ni puntaje por cliente (DF 2.1).")


def _dim(status, resumen, evidencia=None):
    return {"estado": status, "resumen": resumen, "evidencia": evidencia or []}


def monitor_account(result, ips, universe, band: float, max_hhi: float | None, fund_reviews: dict) -> dict:
    """`result`: LifecycleResult del cliente; `fund_reviews`: FundReview por vehículo (M10)."""
    out = {}
    s, adv, close = result.summary, result.advisory, result.closing_results

    # metas (D2)
    goals = close.get("clientgoal", {}).get("metas", {})
    ev, worst = [], OK
    for key, g in goals.items():
        goal = result.client.goal(key)
        if g.get("tipo") == "reserva":
            cov = g.get("cobertura")
            ev.append(f"{goal.nombre}: cobertura {cov:.0%}")
            if cov is not None and cov < 1:
                worst = ALERT
        elif g.get("prob_exito") is not None:
            want = goal.probabilidad_deseada
            ev.append(f"{goal.nombre}: {g['prob_exito']:.0%}" + (f" (deseada {want:.0%})" if want else ""))
            if want is None:
                worst = NODATA if worst == OK else worst
            elif g["prob_exito"] < want:
                worst = ALERT
    out["metas"] = _dim(worst if goals else NODATA,
                        "Todas las metas en o sobre su probabilidad deseada" if worst == OK else
                        "Alguna meta bajo su probabilidad deseada" if worst == ALERT else
                        "Falta la probabilidad deseada de alguna meta", ev)

    # riesgo vs IPS (D8)
    checks = adv.get("limites_ips", {}).get("controles", [])
    exceed = [c for c in checks if c["estado"].startswith("excede")]
    missing = [c for c in checks if c["limite"] is None]
    inv = close.get("scenario", {}).get("inverso", {})
    stress_breaks = (inv.get("escenario_stress_escalado") or {}).get("multiplicador")
    ev = [f"{c['metrica']}: {c['valor']:.1%}" + (f" (límite {c['limite']:.0%})" if c["limite"] is not None else " (sin límite)")
          for c in checks]
    if stress_breaks is not None:
        ev.append(f"Escenario Stress del Comité alcanza el límite al {stress_breaks:.0%} de su intensidad")
    if exceed:
        st, txt = ALERT, f"{len(exceed)} límite(s) excedido(s)"
    elif missing:
        st, txt = NODATA, f"{len(missing)} límite(s) sin definir en el IPS"
    elif stress_breaks is not None and stress_breaks < 1:
        st, txt = ATTN, "Dentro de límites, pero el escenario Stress los rompe"
    else:
        st, txt = OK, "Dentro de los límites del IPS"
    out["riesgo_ips"] = _dim(st, txt, ev)

    # liquidez (D9)
    liq = close.get("liquidity", {})
    alerts = liq.get("alertas", [])
    out["liquidez"] = _dim(ALERT if alerts else OK, "; ".join(alerts) or "Cobertura suficiente a 12 meses",
                           [f"{r['bucket']}: LCR {r['lcr_acumulado']:.1f}×" for r in liq.get("escalera", [])
                            if r.get("lcr_acumulado") is not None])

    # concentración (D7)
    w = s["pesos_actuales"]
    by_admin = {}
    for k, x in w.items():
        by_admin[universe[k].administradora] = by_admin.get(universe[k].administradora, 0.0) + x
    limit = (ips.limites_concentracion or {}).get("administradora") if ips else None
    hhi = sum(x * x for x in w.values())
    ev = [f"{a}: {x:.0%}" for a, x in sorted(by_admin.items(), key=lambda t: -t[1])] + [f"HHI {hhi:.2f}"]
    over = {a: x for a, x in by_admin.items() if limit is not None and x > limit / 100}
    if over:
        st, txt = ALERT, f"{', '.join(over)} sobre el límite de {limit:.0f}% por administradora"
    elif limit is None:
        st, txt = NODATA, "El IPS no define límite por administradora"
    elif max_hhi is not None and hhi > max_hhi:
        st, txt = ATTN, f"HHI {hhi:.2f} sobre {max_hhi:.2f}"
    else:
        st, txt = OK, "Dentro de los límites de concentración"
    out["concentracion"] = _dim(st, txt, ev)

    # drift (D1): a nivel de cartera total, frente a la política vigente
    pol = s["pesos_politica"]
    drift = {k: w.get(k, 0.0) - pol.get(k, 0.0) for k in set(w) | set(pol)}
    k_max = max(drift, key=lambda k: abs(drift[k]))
    out["drift"] = _dim(ATTN if abs(drift[k_max]) > band else OK,
                        f"Mayor desvío {drift[k_max]:+.1%} en {k_max} (banda {band:.0%})",
                        [f"{k}: {v:+.1%}" for k, v in sorted(drift.items(), key=lambda t: -abs(t[1]))])

    # vehículos (D3): due diligence de cada fondo en cartera
    held = [k for k, x in w.items() if x > 0]
    not_eligible = [k for k in held if not fund_reviews[k].elegibilidad["elegible"]]
    signals = [k for k in held if fund_reviews[k].senales]
    removed = [k for k in held if fund_reviews[k].approved_list.estado in ("Removed", "Restricted")]
    if removed:
        st, txt = ALERT, f"Fondos restringidos o eliminados en cartera: {', '.join(removed)}"
    elif not_eligible or signals:
        st = ATTN
        txt = (f"{len(not_eligible)} de {len(held)} fondos sin due diligence completo"
               + (f"; señales en {', '.join(signals)}" if signals else ""))
    else:
        st, txt = OK, "Todos los fondos Approved-Active sin señales"
    out["vehiculos"] = _dim(st, txt, [f"{k}: {fund_reviews[k].approved_list.estado}"
                                      + (f", {len(fund_reviews[k].senales)} señal(es)" if fund_reviews[k].senales else "")
                                      for k in held])
    return out


def prioritize(accounts: list[dict]) -> list[dict]:
    """accounts: [{'id', 'valor', 'dimensiones': {...}}]. Devuelve la lista ordenada con su conteo."""
    for a in accounts:
        states = [d["estado"] for d in a["dimensiones"].values()]
        a["conteo"] = {st: states.count(st) for st in (ALERT, ATTN, NODATA, OK)}
    return sorted(accounts, key=lambda a: (-a["conteo"][ALERT], -a["conteo"][ATTN], -a["valor"]))
