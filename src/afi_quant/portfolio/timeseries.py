"""
Serie temporal DIARIA de la cartera simulada, para gráficos tipo TradingView.

La simulación decide y mueve dinero solo en cierres de mes. Entre dos
cierres, las cuotas de cada meta no cambian: el valor diario es
cuotas × NAV ajustado real de ese día. En un cierre con flujos, el TWR usa
el valor ANTES de los flujos (cuotas del cierre anterior) y la serie de
valor muestra el valor DESPUÉS de los flujos.

Salidas por día:
  valor total, por vehículo y por meta (CLP, después de flujos)
  índice TWR (base 1 al onboarding) y su drawdown
  policy benchmark (SAA vigente del cierre anterior, compra y mantención
  dentro del mes sobre los proxies pasivos)
  aportes netos acumulados (flujos externos)
Los cierres de mes coinciden exactamente con `MonthRow.indice_twr`.
"""

from __future__ import annotations

from bisect import bisect_right
from datetime import date


class _Nav:
    def __init__(self, points):
        self.dates = [p.fecha for p in points]
        self.values = [p.valor_cuota for p in points]

    def at(self, d: date) -> float:
        i = bisect_right(self.dates, d) - 1
        if i < 0:
            raise ValueError(f"Sin NAV al {d}")
        return self.values[i]


def daily_portfolio(rows, universe, proxies) -> list[dict]:
    navs = {k: _Nav(v.series.points) for k, v in universe.items()}
    pnav = {k: _Nav(p.series.points) for k, p in proxies.items()}
    start, end = rows[0].fecha, rows[-1].fecha
    calendar = [p.fecha for p in universe["MM"].series.points if start <= p.fecha <= end]
    row_dates = [r.fecha for r in rows]

    out = []
    index = 1.0
    bench = 1.0
    bench_base_value = 1.0
    net = 0.0
    prev_post = None
    for d in calendar:
        i = bisect_right(row_dates, d) - 1
        row = rows[i]
        is_close = d == row.fecha
        units_after = row.unidades
        per_goal = {g: sum(u * navs[k].at(d) for k, u in hold.items()) for g, hold in units_after.items()}
        per_vehicle: dict[str, float] = {}
        for hold in units_after.values():
            for k, u in hold.items():
                per_vehicle[k] = per_vehicle.get(k, 0.0) + u * navs[k].at(d)
        post = sum(per_goal.values())

        if prev_post is None:
            pre = post
            net = row.total                       # capital inicial
        else:
            if is_close and i >= 1:
                before = rows[i - 1].unidades
                pre = sum(u * navs[k].at(d) for hold in before.values() for k, u in hold.items())
                net += row.aportes - row.retiros
            else:
                pre = post
            index *= pre / prev_post

        # Policy benchmark: pesos del cierre vigente, compra y mantención dentro del mes
        anchor = rows[i] if not is_close or i == 0 else rows[i - 1]
        anchor_i = i if not is_close or i == 0 else i - 1
        if prev_post is None:
            bench = 1.0
        else:
            w = anchor.pesos_politica
            growth = sum(x * pnav[k].at(d) / pnav[k].at(anchor.fecha) for k, x in w.items())
            bench = _bench_base(rows, pnav, anchor_i) * growth

        out.append({
            "fecha": d.isoformat(), "valor": post, "valor_pre_flujos": pre,
            "por_vehiculo": per_vehicle, "por_meta": per_goal,
            "indice_twr": index, "benchmark": bench, "aportes_netos": net,
            "flujo_externo": (row.aportes - row.retiros) if (is_close and i >= 1) else (row.total if i == 0 and prev_post is None else 0.0),
            "cierre": is_close,
        })
        prev_post = post

    peak = 0.0
    for p in out:
        peak = max(peak, p["indice_twr"])
        p["drawdown"] = p["indice_twr"] / peak - 1
    return out


_BENCH_CACHE: dict = {}


def _bench_base(rows, pnav, upto: int) -> float:
    """Valor del benchmark en el cierre `upto`, encadenando los meses completos anteriores."""
    key = (id(rows), upto)
    if key in _BENCH_CACHE:
        return _BENCH_CACHE[key]
    value = 1.0
    for j in range(upto):
        a, b = rows[j], rows[j + 1]
        value *= sum(x * pnav[k].at(b.fecha) / pnav[k].at(a.fecha) for k, x in a.pesos_politica.items())
    _BENCH_CACHE[key] = value
    return value


def normalized(series, start: date, end: date, base: float = 100.0) -> list[dict]:
    """Serie de NAV rebasada a `base` en `start` (modo comparar)."""
    nav = _Nav(series.points)
    b = nav.at(start)
    return [{"fecha": p.fecha.isoformat(), "valor": base * p.valor_cuota / b}
            for p in series.points if start <= p.fecha <= end]
