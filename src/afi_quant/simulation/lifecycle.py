"""
Simulación del ciclo de vida de un cliente sobre datos REALES de mercado.

Recorre mes a mes, desde el onboarding hasta el último dato disponible:

  onboarding (M01) -> construcción por meta, diversificación, liquidez,
  proyección de metas -> implementación (compra de cuotas)
  cada mes: valorización con NAV ajustado real, aportes dirigidos a los
            vehículos bajo su peso objetivo, control de caída
  cada trimestre: Rebalancing Decision Flow (drift -> materialidad ->
            alternativas A/B/C -> recomendación analítica -> decisión del
            WM), chequeo de horizonte de cada meta (glide path)
  cada año: reestimación de CMA y reoptimización
  fecha de una meta: retiro del objetivo, excedente y aportes a otra meta
  cierre: análisis de asesoría completo (`simulation/advisory.py`)

El sistema no ejecuta operaciones (QM XIII): en esta simulación, cada
operación es la decisión de un Wealth Manager SIMULADO que acepta la
alternativa recomendada, y queda registrada como tal en el Decision Case.

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
from afi_quant.engines.benchmark import BenchmarkEngine
from afi_quant.engines.cma import build_cma, monthly_history
from afi_quant.engines.construction import ConstructionEngine
from afi_quant.engines.diversification import DiversificationEngine
from afi_quant.engines.goals import ClientGoalEngine
from afi_quant.engines.liquidity import LiquidityEngine
from afi_quant.engines.performance import PerformanceEngine
from afi_quant.engines.risk import RiskEngine
from afi_quant.engines.scenario import ScenarioEngine
from afi_quant.flows.construction import construction_alternatives
from afi_quant.flows.rebalancing import rebalancing_flow
from afi_quant.orchestrator.states import DecisionCaseState, RecommendationLevel
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
    valor_por_vehiculo: dict[str, float] = field(default_factory=dict)
    pesos_politica: dict[str, float] = field(default_factory=dict)   # SAA vigente agregada
    # Cuotas en poder de cada meta DESPUÉS de los flujos del día: con esto y el NAV
    # diario se reconstruye la valorización diaria entre cierres de mes.
    unidades: dict[str, dict[str, float]] = field(default_factory=dict)


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
    ledger: list[dict] = field(default_factory=list)
    advisory: dict = field(default_factory=dict)
    positions: list = field(default_factory=list)   # una fila por meta y fondo al cierre


def engine_registry() -> EngineRegistry:
    registry = EngineRegistry()
    for engine in (ConstructionEngine(), DiversificationEngine(), LiquidityEngine(),
                   ClientGoalEngine(), RiskEngine(), ScenarioEngine(), BenchmarkEngine(),
                   PerformanceEngine()):
        registry.register(engine)
    return registry


class LifecycleSimulation:
    def __init__(self, client: ClientProfile, universe: dict, registry_params, onboarding: date,
                 ips=None, scenario_library=None):
        self.client = client
        self.universe = universe
        self.params = registry_params
        self.onboarding = onboarding
        if ips is None or scenario_library is None:
            from afi_quant.simulation.parameters import SCENARIO_LIBRARY, synthetic_ips
            ips = ips or synthetic_ips()
            scenario_library = scenario_library or SCENARIO_LIBRARY
        self.ips = ips
        self.scenario_library = scenario_library
        self.engines = engine_registry()
        self.explainer = lifecycle_layer()

        self.nav = {
            k: {(p.fecha.year, p.fecha.month): p for p in _month_ends(v.series.points)}
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
        self.flows: list[tuple[date, float]] = []          # solo flujos EXTERNOS (XIRR)
        self.twr_periods: list[tuple[float, float]] = []
        self.ledger: list[dict] = []                        # todos los movimientos, clasificados
        self.invested: dict[str, float] = {k: 0.0 for k in universe}
        # Lotes por (meta, fondo) a costo promedio: base para posiciones y ganancia realizada
        self.lots: dict[tuple[str, str], dict] = {}

    # --- utilidades -------------------------------------------------------

    def price(self, k: str, ym) -> float:
        return self.nav[k][ym].valor_cuota

    def sleeve_values(self, ym) -> dict[str, dict[str, float]]:
        return {g: {k: u * self.price(k, ym) for k, u in hold.items()}
                for g, hold in self.units.items()}

    def vehicle_values(self, ym) -> dict[str, float]:
        out: dict[str, float] = {}
        for hold in self.sleeve_values(ym).values():
            for k, v in hold.items():
                out[k] = out.get(k, 0.0) + v
        return out

    def units_snapshot(self) -> dict[str, dict[str, float]]:
        return {g: dict(hold) for g, hold in self.units.items()}

    def policy_weights(self, ym) -> dict[str, float]:
        """SAA vigente agregada: objetivos de cada meta ponderados por su valor."""
        values = {g: sum(v.values()) for g, v in self.sleeve_values(ym).items()}
        total = sum(values.values())
        out: dict[str, float] = {}
        for g, w in self.targets.items():
            for k, x in w.items():
                out[k] = out.get(k, 0.0) + x * values.get(g, 0.0) / total
        return out

    def buy(self, goal: str, amounts: dict[str, float], ym) -> None:
        hold = self.units.setdefault(goal, {})
        for k, amount in amounts.items():
            units = amount / self.price(k, ym)
            lot = self.lots.setdefault((goal, k), {"unidades": 0.0, "costo": 0.0, "realizado": 0.0,
                                                   "primera_compra": None, "ultima_operacion": None})
            if units > 0:
                lot["costo"] += amount
                lot["primera_compra"] = lot["primera_compra"] or self.nav[k][ym].fecha
            elif lot["unidades"] > 0:
                share = min(1.0, -units / lot["unidades"])
                cost_out = lot["costo"] * share
                lot["realizado"] += -amount - cost_out
                lot["costo"] -= cost_out
            lot["unidades"] += units
            lot["ultima_operacion"] = self.nav[k][ym].fecha
            hold[k] = hold.get(k, 0.0) + units
            self.invested[k] += amount
            if abs(hold[k]) < 1e-9:
                del hold[k]

    def record(self, fecha, tipo, monto, meta, externo, detalle=None) -> None:
        self.ledger.append({"fecha": fecha, "tipo": tipo, "monto": monto, "meta": meta,
                            "externo": externo, "detalle": detalle or {}})

    def input_data(self, as_of: date, **extra) -> dict:
        data = {
            "client_profile": self.client,
            "vehicle_universe": self.universe,
            "as_of_date": as_of,
            "parameter_registry": self.params,
            "ips": self.ips,
        }
        data.update(extra)
        return data

    def log(self, fecha, tipo, titulo, ctx, case=None, detalle=None) -> None:
        text = self.explainer.explain(ctx)
        if case is not None:
            case.explanation = text
            self.cases.append(case)
        self.events.append(Event(fecha, tipo, titulo, text, detalle or {},
                                 case.case_id if case is not None else None))

    def construct(self, as_of: date, sleeve_values: dict[str, float], trigger: str):
        cma = build_cma(self.universe, as_of, CMA_WINDOW_MONTHS, self.params_value)
        case = run_case(
            self.engines, ["construction", "diversification", "liquidity", "clientgoal"],
            self.input_data(
                as_of, cma_estimate=cma, sleeve_values=sleeve_values,
                scenario_history=monthly_history(self.universe, as_of),
                monthly_contributions=dict(self.contributions),
            ),
            trigger=trigger, client_ref=self.client.client_id,
        )
        con = case.engine_results["construction"]
        if not con.insufficient_data:
            case.alternatives = self.construction_alternatives(as_of, con.values["sleeves"], sleeve_values, cma)
        return case, cma

    def adverse_shocks(self) -> dict[str, float]:
        if not self.scenario_library:
            return {k: 0.0 for k in self.universe}
        shocks = self.scenario_library["escenarios"]["adverso"]["shocks"]
        return {k: shocks[v.subclase] / 100 for k, v in self.universe.items()}

    def construction_alternatives(self, as_of, sleeves, sleeve_values, cma) -> dict:
        """Carteras alternativas por meta (DF v1.1 caso 3) — el WM simulado acepta la recomendada."""
        p = self.params_value
        max_w = float(p("max_weight_per_vehicle_pct")) / 100
        history = monthly_history(self.universe, as_of)
        out = {}
        for g, s in sleeves.items():
            if s["horizonte"] == "corto":
                keys = [k for k, v in self.universe.items() if v.subclase == p("short_horizon_eligible_subclass")]
                caps = {k: 1.0 for k in keys}
            else:
                keys, caps = list(self.universe), {k: max_w for k in self.universe}
            out[g] = construction_alternatives(
                goal=self.client.goal(g), sleeve=s, keys=keys, caps=caps, cma=cma,
                delta=float(p("risk_aversion_delta")), adverse_shocks=self.adverse_shocks(),
                history=history, n_sims=int(p("mc_simulations")), block=int(p("mc_block_months")),
                value=sleeve_values[g], contribution=self.contributions.get(g, 0.0), as_of=as_of,
                missing_data=["CMAs institucionales del Comité", "costos y comisiones por vehículo"],
            )
        return out

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
            self.record(t0, "aporte", capital[g], g, True, {"motivo": "capital inicial"})
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
        self.rows.append(MonthRow(t0, dict(capital), total0, total0, 0.0, 1.0,
                                  self.vehicle_values(ym0), self.policy_weights(ym0),
                                  self.units_snapshot()))

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

            for g in list(self.active):
                goal = self.client.goal(g)
                if goal.fecha is not None and (goal.fecha.year, goal.fecha.month) == ym:
                    withdrawn += self._settle_goal(goal, ym, as_of)

            for g in self.active:
                amount = self.contributions.get(g, 0.0)
                if amount > 0:
                    self._invest_flow(g, amount, ym)
                    self.record(as_of, "aporte", amount, g, True, {"motivo": "aporte mensual"})
                    contributed += amount
            if contributed:
                self.flows.append((as_of, -contributed))

            if ym[1] in REVIEW_MONTHS:
                self._review(ym, as_of, annual=ym[1] == ANNUAL_REVIEW_MONTH)

            values = self.sleeve_values(ym)
            total_after = sum(sum(v.values()) for v in values.values())
            prev_total_after = total_after
            self.rows.append(MonthRow(
                as_of, {g: sum(v.values()) for g, v in values.items()},
                total_after, contributed, withdrawn, index,
                self.vehicle_values(ym), self.policy_weights(ym), self.units_snapshot(),
            ))

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
        last = self.calendar[-1] if self.calendar else ym0
        positions = []
        for (g, k), lot in sorted(self.lots.items()):
            value = max(0.0, lot["unidades"]) * self.price(k, last) if lot["unidades"] > 1e-9 else 0.0
            positions.append({"meta": g, "vehiculo": k, "unidades": max(0.0, lot["unidades"]),
                              "valor_cuota": self.price(k, last), "valor": value,
                              "costo": lot["costo"] if value else 0.0,
                              "ganancia_no_realizada": value - lot["costo"] if value else 0.0,
                              "ganancia_realizada": lot["realizado"], "primera_compra": lot["primera_compra"],
                              "ultima_operacion": lot["ultima_operacion"], "vigente": value > 0})
        return LifecycleResult(positions=positions,
            client=self.client, onboarding=t0, events=self.events, rows=self.rows,
            onboarding_results=onboarding_results, closing_results=closing["results"],
            summary=closing["summary"], cases=self.cases, ledger=self.ledger,
            advisory=closing["advisory"],
        )

    def _projection_ctx(self, case) -> dict:
        goals = case.engine_results.get("clientgoal")
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
        self.buy(goal.key, {k: -v for k, v in values.items()}, ym)   # venta total de la meta
        del self.units[goal.key]
        del self.targets[goal.key]
        self.active.remove(goal.key)
        self.record(as_of, "retiro", -withdraw, goal.key, True, {"motivo": "meta cumplida en su fecha"})
        if surplus > 0:
            self._invest_flow(destination, surplus, ym)
            self.record(as_of, "transferencia_interna", surplus, destination, False,
                        {"desde": goal.key, "motivo": "excedente de la meta"})
        moved = self.contributions.pop(goal.key, 0.0)
        self.contributions[destination] = self.contributions.get(destination, 0.0) + moved
        self.flows.append((as_of, withdraw))
        dest_name = self.client.goal(destination).nombre
        key = "meta_cumplida" if withdraw >= goal.monto_objetivo else "meta_deficit"
        ctx = {"evento": key, "meta": goal.nombre, "valor": clp(available),
               "objetivo": clp(goal.monto_objetivo), "excedente": clp(surplus),
               "deficit": clp(max(0.0, goal.monto_objetivo - available)),
               "destino": dest_name, "aporte": clp(moved)}
        title = f"Meta cumplida: {goal.nombre}" if key == "meta_cumplida" else f"Meta con déficit: {goal.nombre}"
        self.log(as_of, key, title, ctx, detalle={"retiro": withdraw, "excedente": surplus})
        return withdraw

    def _review(self, ym, as_of: date, annual: bool, extraordinary: bool = False) -> None:
        values = self.sleeve_values(ym)
        sleeve_totals = {g: sum(v.values()) for g, v in values.items()}

        # 1) Horizontes (glide path) y revisión anual: Motor de Construcción
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

        # 2) Rebalancing Decision Flow por meta
        band = float(self.params_value("rebalancing_band_pct")) / 100
        adverse = {k: self.scenario_library["escenarios"]["adverso"]["shocks"][v.subclase] / 100
                   for k, v in self.universe.items()} if self.scenario_library else {k: 0.0 for k in self.universe}
        history = monthly_history(self.universe, as_of)
        flows = {}
        caps = {g: s["tope_volatilidad"] for g, s in sleeves.items()}
        for g, vals in values.items():
            flows[g] = rebalancing_flow(
                vol_cap=caps.get(g),
                goal=self.client.goal(g), values=vals, target=self.targets[g], band=band, cma=cma,
                universe=self.universe, adverse_shocks=adverse, history=history,
                n_sims=int(self.params_value("mc_simulations")),
                block=int(self.params_value("mc_block_months")),
                contribution=self.contributions.get(g, 0.0), as_of=as_of,
                missing_data=["costos de transacción", "impacto tributario", "estado en Approved List (M10)"],
            )
        material = [g for g, f in flows.items() if f["material"]]
        worst_goal = max(flows, key=lambda g: abs(flows[g]["mayor_desvio"]))
        worst = flows[worst_goal]
        trigger = ("revisión extraordinaria por caída" if extraordinary else "revisión trimestral") + " — drift vs banda"
        rcase = run_case(self.engines, ["liquidity", "diversification"],
                         self.input_data(as_of, current_values=self.vehicle_values(ym), cma_estimate=cma),
                         trigger=trigger, client_ref=self.client.client_id)
        rcase.alternatives = {g: f for g, f in flows.items() if f["material"]}
        traded = 0.0
        decisions = {}
        for g in material:
            f = flows[g]
            # WM simulado: acepta la recomendación de Nivel 3; sin ella, no opera.
            choice = f["recomendada"] or "A"
            alt = f["alternativas"][choice]
            self.buy(g, alt["operaciones"], ym)
            traded += alt["rotacion_clp"]
            decisions[g] = choice
            self.record(as_of, "rebalanceo", alt["rotacion_clp"], g, False,
                        {"alternativa": choice, "operaciones": alt["operaciones"]})
        if material:
            rcase.recommendation_level = RecommendationLevel(min(flows[g]["nivel"] for g in material))
            rcase.wm_decision = {"decision": decisions, "simulada": True,
                                 "justificacion": ("WM simulado: acepta la alternativa recomendada; sin "
                                                   "recomendación de Nivel 3, mantiene la cartera.")}
            rcase.state = DecisionCaseState.DECIDED
            rcase._log(f"Decisión del WM (simulada): {decisions}")

        title = "Revisión extraordinaria" if extraordinary else (
            "Revisión trimestral (rebalanceo)" if material else "Revisión trimestral")
        ctx = {
            "evento": "revision", "banda": band,
            "rebalanceadas": " y ".join(self.client.goal(g).nombre for g in material),
            "verbo": "superaron" if len(material) > 1 else "superó",
            "meta_detalle": self.client.goal(max(material, key=lambda x: abs(flows[x]["mayor_desvio"]))).nombre
            if material else None,
            "mayor_desvio": worst["mayor_desvio"], "mayor_desvio_vehiculo": worst["mayor_desvio_vehiculo"],
            "mayor_desvio_meta": self.client.goal(worst_goal).nombre,
            "monto_operado": clp(traded),
        }
        if material:
            g = max(material, key=lambda x: abs(flows[x]["mayor_desvio"]))
            f = flows[g]
            alts = f["alternativas"]
            ctx.update({
                "alternativas_texto": "; ".join(
                    f"{k} {a['nombre'].lower()} (vol {a['volatilidad_ex_ante']:.1%}"
                    + (f", rota {clp(a['rotacion_clp'])} CLP)" if a["rotacion_clp"] else ")")
                    for k, a in alts.items()),
                "descartadas": "; ".join(f"{k} {m}" for k, m in f.get("descartadas", {}).items()),
                "n_tradeoffs": len(f["tradeoffs"]["tradeoffs"]),
                "recomendacion": f["recomendacion"] or f["motivo_nivel"],
            })
        self.log(as_of, "revision", title, ctx, rcase, {
            "monto_operado": traded,
            "desvios": {g: f["desvios"] for g, f in flows.items()},
            "flujos": {g: f for g, f in flows.items() if f["material"]},
            "decision_wm": decisions,
        })

    def _close(self) -> dict:
        from afi_quant.simulation.advisory import closing_advisory

        return closing_advisory(self)


def _month_ends(points):
    from afi_quant.engines.series import month_end_points
    return month_end_points(points)


def run_lifecycle(client=None, universe=None, params=None, onboarding=None, ips=None) -> LifecycleResult:
    from afi_quant.portfolio.universe import default_universe
    from afi_quant.simulation.parameters import (
        ONBOARDING_DATE, SCENARIO_LIBRARY, simulation_registry, synthetic_client, synthetic_ips,
    )

    return LifecycleSimulation(
        client or synthetic_client(),
        universe or default_universe(),
        params or simulation_registry(),
        onboarding or ONBOARDING_DATE,
        ips=ips or synthetic_ips(),
        scenario_library=SCENARIO_LIBRARY,
    ).run()
