"""
Simulación del ciclo de vida de un cliente sobre datos REALES de mercado.

Recorre mes a mes, desde el onboarding hasta el último dato disponible:

  onboarding (M01) -> construcción por meta, diversificación, liquidez,
  proyección de metas -> implementación (compra de cuotas)
  cada mes: valorización con NAV ajustado real, aportes dirigidos a los
            vehículos bajo su peso objetivo, control de caída
  cada trimestre: revisión (drift vs banda -> rebalanceo o nada),
            chequeo de horizonte de cada meta (glide path)
  cada año: reestimación de CMA y reoptimización
  fecha de una meta: retiro del objetivo, excedente y aportes a otra meta
  cierre: TWR, XIRR, riesgo realizado, proyección de las metas vigentes

Cada decisión pasa por un Decision Case (plan -> gate -> motores). El
cliente y los parámetros son ficticios (`simulation/parameters.py`); los
precios son reales. No hay look-ahead: toda decisión en la fecha t usa
solo datos hasta t. No se modelan costos de transacción ni impuestos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from afi_quant.clients.profile import ClientProfile, months_between
from afi_quant.engines.base import EngineRegistry
from afi_quant.engines.cma import build_cma, monthly_history
from afi_quant.engines.construction import ConstructionEngine
from afi_quant.engines.diversification import DiversificationEngine
from afi_quant.engines.goals import GoalsEngine
from afi_quant.engines.liquidity import LiquidityEngine
from afi_quant.engines.performance import twr_with_flows, xirr
from afi_quant.engines.rebalancing import RebalancingEngine
from afi_quant.engines.risk import RiskEngine
from afi_quant.engines.series import AdjustedSeries, NavPoint, month_end_points
from afi_quant.pipeline import run_case
from afi_quant.simulation.narrative import clp, lifecycle_layer, weights_text

CMA_WINDOW_MONTHS = 36
REVIEW_MONTHS = (1, 4, 7, 10)
ANNUAL_REVIEW_MONTH = 10


@dataclass
class Event:
    fecha: date
    tipo: str
    titulo: str
    explicacion: str
    detalle: dict = field(default_factory=dict)
    case_id: str | None = None


@dataclass
class MonthRow:
    fecha: date
    valor_por_meta: dict[str, float]
    total: float
    aportes: float
    retiros: float
    indice_twr: float


@dataclass
class LifecycleResult:
    client: ClientProfile
    onboarding: date
    events: list[Event]
    rows: list[MonthRow]
    onboarding_results: dict
    closing_results: dict
    summary: dict
    cases: list = field(default_factory=list)


def engine_registry() -> EngineRegistry:
    registry = EngineRegistry()
    for engine in (ConstructionEngine(), DiversificationEngine(), LiquidityEngine(),
                   GoalsEngine(), RebalancingEngine(), RiskEngine()):
        registry.register(engine)
    return registry


class LifecycleSimulation:
    def __init__(self, client: ClientProfile, universe: dict, registry_params, onboarding: date):
        self.client = client
        self.universe = universe
        self.params = registry_params
        self.onboarding = onboarding
        self.engines = engine_registry()
        self.explainer = lifecycle_layer()

        self.nav = {
            k: {(p.fecha.year, p.fecha.month): p for p in month_end_points(v.series.points)}
            for k, v in universe.items()
        }
        common = sorted(set.intersection(*(set(m) for m in self.nav.values())))
        self.calendar = [ym for ym in common if ym > (onboarding.year, onboarding.month)]

        self.units: dict[str, dict[str, float]] = {}
        self.targets: dict[str, dict[str, float]] = {}
        self.horizons: dict[str, str] = {}
        self.contributions = {g.key: g.aporte_mensual for g in client.goals}
        self.active = [g.key for g in client.goals]
        self.events: list[Event] = []
        self.rows: list[MonthRow] = []
        self.cases = []
        self.flows: list[tuple[date, float]] = []
        self.twr_periods: list[tuple[float, float]] = []

    # --- utilidades -------------------------------------------------------

    def price(self, k: str, ym) -> float:
        return self.nav[k][ym].valor_cuota

    def sleeve_values(self, ym) -> dict[str, dict[str, float]]:
        return {g: {k: u * self.price(k, ym) for k, u in hold.items()}
                for g, hold in self.units.items()}

    def buy(self, goal: str, amounts: dict[str, float], ym) -> None:
        hold = self.units.setdefault(goal, {})
        for k, amount in amounts.items():
            hold[k] = hold.get(k, 0.0) + amount / self.price(k, ym)
            if abs(hold[k]) < 1e-9:
                del hold[k]

    def input_data(self, as_of: date, **extra) -> dict:
        data = {
            "client_profile": self.client,
            "vehicle_universe": self.universe,
            "as_of_date": as_of,
            "parameter_registry": self.params,
        }
        data.update(extra)
        return data

    def explain(self, ctx: dict) -> str:
        return self.explainer.explain(ctx)

    def log(self, fecha, tipo, titulo, ctx, case=None, detalle=None) -> None:
        text = self.explain(ctx)
        if case is not None:
            case.explanation = text
            self.cases.append(case)
        self.events.append(Event(fecha, tipo, titulo, text, detalle or {},
                                 case.case_id if case is not None else None))

    def construct(self, as_of: date, sleeve_values: dict[str, float], trigger: str):
        cma = build_cma(self.universe, as_of, CMA_WINDOW_MONTHS, self.params_value)
        case = run_case(
            self.engines, ["construction", "diversification", "liquidity", "goals"],
            self.input_data(
                as_of, cma_estimate=cma, sleeve_values=sleeve_values,
                scenario_history=monthly_history(self.universe, as_of),
                monthly_contributions=dict(self.contributions),
            ),
            trigger=trigger, client_ref=self.client.client_id,
        )
        return case, cma

    def params_value(self, name):
        from afi_quant.registries.parameter_registry import get_parameter
        return get_parameter(name, self.params).value

    # --- ciclo de vida ----------------------------------------------------

    def run(self) -> LifecycleResult:
        t0 = self.onboarding
        ym0 = (t0.year, t0.month)
        capital = {g.key: g.capital_inicial for g in self.client.goals}
        case, cma = self.construct(t0, capital, "onboarding — construcción de cartera por meta")
        c = case.engine_results["construction"].values
        for g, sleeve in c["sleeves"].items():
            self.targets[g] = dict(sleeve["pesos"])
            self.horizons[g] = sleeve["horizonte"]
            self.buy(g, {k: w * capital[g] for k, w in sleeve["pesos"].items()}, ym0)
        total0 = sum(capital.values())
        self.flows.append((t0, -total0))
        onboarding_results = {n: r.values for n, r in case.engine_results.items()}
        alerts = (case.engine_results["diversification"].values["alertas"]
                  + case.engine_results["liquidity"].values["alertas"])
        self.log(t0, "onboarding", "Onboarding y construcción de cartera", {
            "evento": "onboarding",
            "cma_n_obs": cma.n_obs, "cma_desde": cma.desde.isoformat(), "cma_hasta": cma.hasta.isoformat(),
            "asignacion": weights_text(c["asignacion_total"]),
            "retorno_esperado": c["retorno_esperado_total"],
            "volatilidad": c["volatilidad_ex_ante_total"],
            "nota_cma": cma.nota,
            "alertas": "; ".join(alerts),
            **self._projection_ctx(case),
        }, case, {"capital": capital})
        self.rows.append(MonthRow(t0, dict(capital), total0, total0, 0.0, 1.0))

        prev_total_after = total0
        index = 1.0
        peak_index, peak_date, in_alert = 1.0, t0, False

        for ym in self.calendar:
            as_of = self.nav["MM"][ym].fecha
            values = self.sleeve_values(ym)
            total_before = sum(sum(v.values()) for v in values.values())
            self.twr_periods.append((prev_total_after, total_before))
            index *= total_before / prev_total_after
            contributed = withdrawn = 0.0

            # Fecha de una meta: retiro del objetivo
            for g in list(self.active):
                goal = self.client.goal(g)
                if goal.fecha is not None and (goal.fecha.year, goal.fecha.month) == ym:
                    withdrawn += self._settle_goal(goal, ym, as_of)

            # Aportes del mes, dirigidos a lo que está bajo su objetivo
            for g in self.active:
                amount = self.contributions.get(g, 0.0)
                if amount > 0:
                    self._invest_flow(g, amount, ym)
                    contributed += amount
            if contributed:
                self.flows.append((as_of, -contributed))

            # Revisión trimestral / anual
            if ym[1] in REVIEW_MONTHS:
                self._review(ym, as_of, annual=ym[1] == ANNUAL_REVIEW_MONTH)

            values = self.sleeve_values(ym)
            total_after = sum(sum(v.values()) for v in values.values())
            prev_total_after = total_after
            self.rows.append(MonthRow(
                as_of, {g: sum(v.values()) for g, v in values.items()},
                total_after, contributed, withdrawn, index,
            ))

            # Control de caída (regla de escalamiento)
            if index > peak_index:
                peak_index, peak_date, in_alert = index, as_of, False
            dd = index / peak_index - 1
            threshold = float(self.params_value("drawdown_alert_pct")) / 100
            if dd < -threshold and not in_alert:
                in_alert = True
                self.log(as_of, "alerta_caida", "Alerta de caída: revisión extraordinaria", {
                    "evento": "alerta_caida", "caida": dd, "umbral": threshold,
                    "fecha_maximo": peak_date.isoformat(),
                })
                self._review(ym, as_of, annual=False, extraordinary=True)

        closing = self._close()
        return LifecycleResult(
            client=self.client, onboarding=t0, events=self.events, rows=self.rows,
            onboarding_results=onboarding_results, closing_results=closing["results"],
            summary=closing["summary"], cases=self.cases,
        )

    def _projection_ctx(self, case) -> dict:
        goals = case.engine_results.get("goals")
        if goals is None or goals.insufficient_data:
            return {}
        parts = []
        for g in goals.values["metas"].values():
            if g["tipo"] == "reserva":
                parts.append(f"{g['meta']}: reserva cubierta al {g['cobertura']:.0%}")
            else:
                parts.append(f"{g['meta']}: {g['prob_exito']:.0%}")
        return {"probabilidades": "; ".join(parts), "simulaciones": goals.values["simulaciones"]}

    def _invest_flow(self, goal: str, amount: float, ym) -> None:
        """Aporte dirigido: compra lo que está bajo su peso objetivo (rebalanceo con flujos)."""
        target = self.targets[goal]
        current = {k: self.units.get(goal, {}).get(k, 0.0) * self.price(k, ym) for k in target}
        new_total = sum(current.values()) + amount
        gaps = {k: max(0.0, target[k] * new_total - current[k]) for k in target}
        gap_sum = sum(gaps.values())
        if gap_sum <= 0:
            gaps, gap_sum = dict(target), 1.0
        self.buy(goal, {k: amount * gaps[k] / gap_sum for k in gaps if gaps[k] > 0}, ym)

    def _settle_goal(self, goal, ym, as_of: date) -> float:
        values = self.sleeve_values(ym)[goal.key]
        available = sum(values.values())
        withdraw = min(goal.monto_objetivo, available)
        surplus = available - withdraw
        destination = next(g for g in self.active if g != goal.key and self.client.goal(g).fecha is not None)
        del self.units[goal.key]
        del self.targets[goal.key]
        self.active.remove(goal.key)
        if surplus > 0:
            self._invest_flow(destination, surplus, ym)
        moved = self.contributions.pop(goal.key, 0.0)
        self.contributions[destination] = self.contributions.get(destination, 0.0) + moved
        self.flows.append((as_of, withdraw))
        dest_name = self.client.goal(destination).nombre
        if withdraw >= goal.monto_objetivo:
            ctx = {"evento": "meta_cumplida", "meta": goal.nombre, "valor": clp(available),
                   "objetivo": clp(goal.monto_objetivo), "excedente": clp(surplus),
                   "destino": dest_name, "aporte": clp(moved)}
            self.log(as_of, "meta_cumplida", f"Meta cumplida: {goal.nombre}", ctx,
                     detalle={"retiro": withdraw, "excedente": surplus})
        else:
            ctx = {"evento": "meta_deficit", "meta": goal.nombre, "valor": clp(available),
                   "objetivo": clp(goal.monto_objetivo), "deficit": clp(goal.monto_objetivo - available),
                   "destino": dest_name, "aporte": clp(moved)}
            self.log(as_of, "meta_deficit", f"Meta con déficit: {goal.nombre}", ctx,
                     detalle={"retiro": withdraw, "deficit": goal.monto_objetivo - available})
        return withdraw

    def _review(self, ym, as_of: date, annual: bool, extraordinary: bool = False) -> None:
        values = self.sleeve_values(ym)
        sleeve_totals = {g: sum(v.values()) for g, v in values.items()}

        # 1) Horizontes (glide path) y revisión anual: reconstrucción por el Motor de Construcción
        case, cma = self.construct(
            as_of, sleeve_totals,
            "revisión anual — reestimación de CMA" if annual else "revisión — chequeo de horizontes",
        )
        sleeves = case.engine_results["construction"].values["sleeves"]
        changed = [g for g in sleeves if sleeves[g]["horizonte"] != self.horizons.get(g)]
        if annual:
            for g, s in sleeves.items():
                self.targets[g] = dict(s["pesos"])
                self.horizons[g] = s["horizonte"]
            total_w = case.engine_results["construction"].values["asignacion_total"]
            self.log(as_of, "revision_anual", "Revisión anual de la asignación", {
                "evento": "revision_anual", "cma_n_obs": cma.n_obs,
                "cma_desde": cma.desde.isoformat(), "cma_hasta": cma.hasta.isoformat(),
                "nota_cma": cma.nota,
                "asignacion": weights_text(total_w), **self._projection_ctx(case),
            }, case, {"asignacion_total": total_w,
                      "metas": {g: s["pesos"] for g, s in sleeves.items()}})
        else:
            for g in changed:
                s = sleeves[g]
                before = self.horizons.get(g)
                self.targets[g] = dict(s["pesos"])
                self.horizons[g] = s["horizonte"]
                goal = self.client.goal(g)
                self.log(as_of, "cambio_horizonte", f"Cambio de horizonte: {goal.nombre}", {
                    "evento": "cambio_horizonte", "meta": goal.nombre,
                    "horizonte_antes": before, "horizonte_despues": s["horizonte"],
                    "meses": months_between(as_of, goal.fecha), "tope": s["tope_volatilidad"],
                    "pesos": weights_text(s["pesos"]), **self._projection_ctx(case),
                }, case, {"pesos": s["pesos"]})

        # 2) Drift vs banda -> rebalanceo
        rcase = run_case(
            self.engines, ["rebalancing"],
            self.input_data(as_of, sleeve_holdings=values, target_sleeves=self.targets),
            trigger=("revisión extraordinaria por caída" if extraordinary else "revisión trimestral")
                    + " — drift vs banda",
            client_ref=self.client.client_id,
        )
        r = rcase.engine_results["rebalancing"].values
        traded = 0.0
        for g in r["rebalancear"]:
            trades = r["metas"][g]["operaciones_propuestas"]
            self.buy(g, trades, ym)
            traded += sum(abs(v) for v in trades.values()) / 2
        worst_goal = max(r["metas"], key=lambda g: abs(r["metas"][g]["mayor_desvio"]))
        worst = r["metas"][worst_goal]
        title = "Revisión extraordinaria" if extraordinary else (
            "Revisión trimestral" if not annual else "Revisión trimestral (rebalanceo)")
        self.log(as_of, "revision", title, {
            "evento": "revision", "banda": r["banda"],
            "rebalanceadas": ", ".join(self.client.goal(g).nombre for g in r["rebalancear"]),
            "mayor_desvio": worst["mayor_desvio"], "mayor_desvio_vehiculo": worst["mayor_desvio_vehiculo"],
            "mayor_desvio_meta": self.client.goal(worst_goal).nombre,
            "monto_operado": clp(traded),
        }, rcase, {"monto_operado": traded,
                   "desvios": {g: m["desvios"] for g, m in r["metas"].items()}})

    def _close(self) -> dict:
        ym = self.calendar[-1]
        as_of = self.nav["MM"][ym].fecha
        values = self.sleeve_values(ym)
        sleeve_totals = {g: sum(v.values()) for g, v in values.items()}
        total = sum(sleeve_totals.values())
        flows = self.flows + [(as_of, total)]

        rets = twr_with_flows(self.twr_periods)
        twr = 1.0
        for r in rets:
            twr *= 1 + r
        twr -= 1
        years = (as_of - self.onboarding).days / 365.25

        # Riesgo realizado: el índice TWR de la cartera como serie para el Motor de Riesgo
        index_series = AdjustedSeries(
            rut="SIM-001", serie="CARTERA", nemotecnico="CARTERA-SIM-001",
            points=[NavPoint(r.fecha, r.indice_twr) for r in self.rows],
            source="Índice TWR de la cartera simulada (precios reales, cliente ficticio)",
        )
        by_vehicle: dict[str, float] = {}
        for v in values.values():
            for k, x in v.items():
                by_vehicle[k] = by_vehicle.get(k, 0.0) + x
        weights = {k: x / total for k, x in by_vehicle.items()}
        cma = build_cma(self.universe, as_of, CMA_WINDOW_MONTHS, self.params_value)
        case = run_case(
            self.engines, ["risk", "diversification", "liquidity", "goals"],
            self.input_data(
                as_of, nav_series_native_frequency=index_series, cma_estimate=cma,
                current_weights=weights, current_values=by_vehicle,
                target_sleeves=self.targets, sleeve_values=sleeve_totals,
                scenario_history=monthly_history(self.universe, as_of),
                monthly_contributions=dict(self.contributions),
            ),
            trigger="cierre de la simulación — estado y proyección",
            client_ref=self.client.client_id,
        )
        risk = case.engine_results["risk"].values
        div = case.engine_results["diversification"].values
        contributed = -sum(cf for _, cf in self.flows if cf < 0)
        withdrawn = sum(cf for _, cf in self.flows[1:] if cf > 0)
        summary = {
            "fecha": as_of.isoformat(),
            "valor_final": total,
            "valor_por_meta": sleeve_totals,
            "pesos_actuales": weights,
            "aportado": contributed,
            "retirado": withdrawn,
            "twr": twr,
            "twr_anual": (1 + twr) ** (1 / years) - 1,
            "xirr": xirr(flows),
            "max_drawdown": risk["max_drawdown"],
            "volatilidad_ex_ante": div["volatilidad_ex_ante"],
            "riesgo_no_calculado": risk["no_calculado"],
            "meses": len(rets),
        }
        blocked = risk["no_calculado"].get("volatilidad_anual")
        self.log(as_of, "cierre", "Cierre: estado de la cartera y proyección", {
            "evento": "cierre", "fecha": as_of.isoformat(), "valor": clp(total),
            "twr": twr, "twr_anual": summary["twr_anual"], "xirr": summary["xirr"],
            "aportes": clp(contributed), "retiros": clp(withdrawn),
            "riesgo_bloqueado": blocked.rstrip(".") if blocked else None,
            "vol_ex_ante": div["volatilidad_ex_ante"],
            **self._projection_ctx(case),
        }, case)
        return {"results": {n: r.values for n, r in case.engine_results.items()}, "summary": summary}


def run_lifecycle(client=None, universe=None, params=None, onboarding=None) -> LifecycleResult:
    from afi_quant.portfolio.universe import default_universe
    from afi_quant.simulation.parameters import ONBOARDING_DATE, simulation_registry, synthetic_client

    return LifecycleSimulation(
        client or synthetic_client(),
        universe or default_universe(),
        params or simulation_registry(),
        onboarding or ONBOARDING_DATE,
    ).run()
