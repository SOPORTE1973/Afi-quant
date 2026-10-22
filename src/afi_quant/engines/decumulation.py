"""
Fase de desembolso de una meta de jubilación (desacumulación).

Pregunta que responde: si el cliente LLEGA al monto objetivo en la fecha de
jubilación, ¿cuánto puede retirar cada mes y hasta qué edad le alcanza?

Usa el mismo Monte Carlo con bootstrap por bloques del Motor de Cliente/Goal
(`engines/goals.py`): misma historia re-centrada en la CMA, mismo largo de
bloque, misma semilla. No introduce modelos de mercado nuevos (ESFS 11.10).

Retiro: se paga a fin de cada mes, después del retorno, y crece con la
inflación (`decumulation_inflation_pct`) para mantener poder de compra:

    V_m = V_{m-1}·(1 + r_m) − W·(1 + g)^{m-1}

Como V_m es lineal en W, cada trayectoria se resume en dos series:
A_m = C·Π(1+r) (el capital sin retiros) y B_m = B_{m-1}·(1+r_m) + (1+g)^{m-1}
(el costo acumulado de retirar 1 peso indexado). La trayectoria alcanza hasta
la edad final si y solo si W ≤ min_m A_m/B_m. Con eso, el retiro sostenible a
un nivel de confianza p es el percentil (1−p) de ese máximo por trayectoria:
exacto, sin búsqueda iterativa.

Variante "preservando el capital": el mayor retiro que deja, a la edad final, el
capital inicial con su mismo poder de compra (C·(1+g)^N) — vivir de la
rentabilidad real. También es lineal en W: W ≤ (A_N − C·(1+g)^N)/B_N.

No elige el nivel de confianza: muestra varios y el WM decide con el cliente
(DF 4.3). La edad final y la inflación son parámetros del registro.

Limitaciones declaradas:
  - no modela longevidad (edad final fija, sin tablas de mortalidad);
  - no considera pensión AFP, impuestos ni rentas vitalicias;
  - la cartera de desembolso se mantiene constante (sin glide path posterior).
"""

from __future__ import annotations

import math
import random
from datetime import date

from afi_quant.clients.profile import months_between
from afi_quant.engines.goals import SEED


def _age_date(birth: date, age: int) -> date:
    try:
        return birth.replace(year=birth.year + age)
    except ValueError:                      # 29 de febrero
        return birth.replace(year=birth.year + age, day=28)


def max_withdrawals(port: list[float], capital: float, months: int, n_sims: int, block: int,
                    g: float, checkpoints: list[int], seed: int = SEED):
    """
    Para cada trayectoria: el mayor retiro inicial que alcanza hasta `months` y, en
    cada checkpoint, (A, B, mínimo de A/B hasta ese mes) para reconstruir el saldo
    con cualquier retiro W: saldo = A − W·B si W ≤ mínimo, si no la plata ya se acabó.
    """
    n = len(port)
    rng = random.Random(seed)
    cps = set(checkpoints)
    wmax, marks = [], []
    for _ in range(n_sims):
        a, b, low, m, idx = capital, 0.0, math.inf, 0, 1.0
        row = {}
        while m < months:
            start = rng.randrange(n)
            for j in range(block):
                if m >= months:
                    break
                r = port[(start + j) % n]
                a *= 1 + r
                b = b * (1 + r) + idx
                idx *= 1 + g
                m += 1
                low = min(low, a / b)
                if m in cps:
                    row[m] = (a, b, low)
        wmax.append(low)
        marks.append(row)
    return wmax, marks


def decumulation_plan(*, capital: float, start: date, birth: date, end_age: int, inflation_pct: float,
                      weights: dict[str, float], returns: dict[str, list[float]], expected_return: float,
                      n_sims: int, block: int, levels: list[float], as_of: date, seed: int = SEED) -> dict:
    months = months_between(start, _age_date(birth, end_age))
    if months <= 0:
        return {"no_calculado": f"La jubilación ocurre después de los {end_age} años: no hay período de desembolso."}
    g = (1 + inflation_pct / 100) ** (1 / 12) - 1
    n_hist = len(next(iter(returns.values())))
    port = [sum(weights[k] * returns[k][t] for k in weights) for t in range(n_hist)]
    checkpoints = list(range(12, months, 12)) + [months]
    wmax, marks = max_withdrawals(port, capital, months, n_sims, block, g, checkpoints, seed)
    srt = sorted(wmax)

    # Referencia determinística: retorno esperado constante (μ/12, como el re-centrado)
    r = expected_return / 12
    a, b, low = capital, 0.0, math.inf
    for m in range(months):
        a *= 1 + r
        b = b * (1 + r) + (1 + g) ** m
        low = min(low, a / b)
    deterministic = low
    # Preservando el capital: al final debe quedar el capital inicial con su poder de compra
    # (C·(1+g)^N), sin agotarse antes. Lineal en W: W ≤ (A_N − K)/B_N y W ≤ min A_m/B_m.
    keep = capital * (1 + g) ** months
    deterministic_keep = max(0.0, min(low, (a - keep) / b))
    wkeep = sorted(max(0.0, min(row[months][2], (row[months][0] - keep) / row[months][1])) for row in marks)

    # Pesos de hoy: deflactar con la misma inflación desde la fecha de los datos
    to_today = (1 + inflation_pct / 100) ** (months_between(as_of, start) / 12)
    start_age = months_between(birth, start) / 12
    out_levels = []
    for p in levels:
        w = srt[min(len(srt) - 1, int(math.floor((1 - p) * len(srt))))]
        path = []
        for cp in checkpoints:
            vals = sorted(max(0.0, row[cp][0] - w * row[cp][1]) if w <= row[cp][2] else 0.0 for row in marks)
            alive = sum(1 for row in marks if w <= row[cp][2]) / len(marks)
            path.append({"mes": cp, "edad": round(start_age + cp / 12, 1), "vigente": alive,
                         "p10": vals[int(0.1 * (len(vals) - 1))], "p50": vals[int(0.5 * (len(vals) - 1))],
                         "p90": vals[int(0.9 * (len(vals) - 1))],
                         "retiro_mes": w * (1 + g) ** (cp - 1)})
        wk = wkeep[min(len(wkeep) - 1, int(math.floor((1 - p) * len(wkeep))))]
        finals = sorted(max(0.0, row[months][0] - wk * row[months][1]) / (1 + g) ** months
                        if wk <= row[months][2] else 0.0 for row in marks)
        out_levels.append({
            "preservando": {"retiro_inicial": wk, "retiro_inicial_hoy": wk / to_today,
                            "retiro_final": wk * (1 + g) ** (months - 1),
                            "capital_final_real_p50": finals[int(0.5 * (len(finals) - 1))],
                            "capital_final_real_p10": finals[int(0.1 * (len(finals) - 1))]},
            "confianza": p, "retiro_inicial": w, "retiro_inicial_hoy": w / to_today,
            "retiro_anual_inicial": w * 12, "retiro_final": w * (1 + g) ** (months - 1),
            "total_retirado": w * sum((1 + g) ** m for m in range(months)),
            "trayectoria": [{"mes": 0, "edad": round(start_age, 1), "vigente": 1.0, "p10": capital, "p50": capital,
                             "p90": capital, "retiro_mes": w}] + path,
        })
    return {
        "capital_inicial": capital, "inicio": start, "fin": _age_date(birth, end_age),
        "edad_inicio": round(start_age, 1), "edad_fin": end_age, "meses": months,
        "inflacion_pct": inflation_pct, "deflactor_a_hoy": to_today,
        "cartera": weights, "retorno_esperado": expected_return,
        "retiro_deterministico": deterministic, "retiro_deterministico_hoy": deterministic / to_today,
        "retiro_deterministico_preservando": deterministic_keep,
        "retiro_deterministico_preservando_hoy": deterministic_keep / to_today,
        "niveles": out_levels,
        "simulaciones": n_sims, "bloque_meses": block,
    }


def retirement_decumulation(goal, birth: date, ips_vol_pct: float | None, universe, parameter_of, as_of: date) -> dict:
    """
    Desembolso de una meta de jubilación con dos carteras, para ver la sensibilidad:
      - la de largo plazo que arma el Construction Engine (tope de horizonte largo y del IPS),
        porque los retiros se reparten en décadas;
      - 100% en la subclase elegible de corto plazo, la cartera con la que la meta llega a
        su fecha por el glide path del motor.
    """
    from afi_quant.engines.cma import build_cma, monthly_history
    from afi_quant.engines.construction import optimize_grid
    from afi_quant.engines.goals import recentered_returns
    from afi_quant.simulation.lifecycle import CMA_WINDOW_MONTHS

    P = parameter_of
    needed = ["decumulation_end_age", "decumulation_inflation_pct", "decumulation_confidence_levels",
              "mc_simulations", "mc_block_months"]
    missing = [p for p in needed if P(p) is None]
    if missing:
        return {"no_calculado": f"Parámetros sin valor en el Parameter Registry: {missing}."}
    if birth is None or goal.fecha is None:
        return {"no_calculado": "Falta la fecha de nacimiento del cliente o la fecha de jubilación."}
    cma = build_cma(universe, as_of, CMA_WINDOW_MONTHS, P)
    returns = recentered_returns(monthly_history(universe, as_of), cma)
    cap = float(P("vol_cap_long_pct")) / 100
    source = "horizonte largo"
    if ips_vol_pct is not None and ips_vol_pct / 100 < cap:
        cap, source = ips_vol_pct / 100, "IPS"
    max_w = float(P("max_weight_per_vehicle_pct")) / 100
    long_w = optimize_grid(cma, list(universe), float(P("risk_aversion_delta")), cap,
                           {k: max_w for k in universe})
    short = [k for k, v in universe.items() if v.subclase == P("short_horizon_eligible_subclass")]
    carteras = {}
    if long_w:
        carteras["largo"] = {"nombre": f"Cartera de largo plazo del motor (tope {cap:.1%}, {source})", "pesos": long_w}
    if short:
        carteras["corto"] = {"nombre": f"100% {P('short_horizon_eligible_subclass')}",
                             "pesos": {k: 1 / len(short) for k in short}}
    levels = [float(x) for x in str(P("decumulation_confidence_levels")).split(",")]
    out = {"meta": goal.key, "nombre": goal.nombre, "carteras": {}}
    for key, c in carteras.items():
        plan = decumulation_plan(
            capital=goal.monto_objetivo, start=goal.fecha, birth=birth, end_age=int(P("decumulation_end_age")),
            inflation_pct=float(P("decumulation_inflation_pct")), weights=c["pesos"], returns=returns,
            expected_return=cma.portfolio_return(c["pesos"]), n_sims=int(P("mc_simulations")),
            block=int(P("mc_block_months")), levels=levels, as_of=as_of)
        plan["nombre"] = c["nombre"]
        plan["volatilidad_ex_ante"] = math.sqrt(cma.portfolio_variance(c["pesos"]))
        out["carteras"][key] = plan
    out["supuestos"] = {
        "edad_final": int(P("decumulation_end_age")), "inflacion_pct": float(P("decumulation_inflation_pct")),
        "niveles": levels, "cma_al": as_of,
        "limitaciones": ["edad final fija, sin tablas de mortalidad", "sin pensión AFP, impuestos ni rentas vitalicias",
                         "cartera constante durante el desembolso", "CMAs de simulación, no institucionales"],
    }
    return out
