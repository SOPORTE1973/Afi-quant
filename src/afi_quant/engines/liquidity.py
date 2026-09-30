"""
Motor de Liquidez (CORE) — Liquidity Ladder y Liquidity Coverage Ratio.

Buckets 0-3m / 3-12m / >12m: los tramos SÍ están confirmados en la fuente
(`liquidity_bucket_short_days`, `liquidity_bucket_medium_days` ya tienen
valor en el Parameter Registry).

  - Obligaciones por bucket: el monto objetivo de cada meta cuya fecha cae
    en el bucket. Una reserva permanente (fondo de emergencia) cuenta como
    obligación contingente del bucket 0-3m.
  - Activos disponibles por bucket: valor de los vehículos que se pueden
    liquidar dentro del plazo del bucket (`dias_liquidez` del universo).
  - LCR acumulado = activos disponibles hasta ese plazo / obligaciones
    acumuladas hasta ese plazo. Se evalúa contra `min_lcr_ratio` solo en
    0-3m y 3-12m: una meta a más de 12 meses se financia también con
    aportes futuros y rentabilidad, y su suficiencia la mide el Motor de
    Cliente/Goal (probabilidad de éxito), no una razón de cobertura.
"""

from __future__ import annotations

from afi_quant.engines.base import EngineResult, parameter_value

BUCKETS = ("0-3m", "3-12m", ">12m")


class LiquidityEngine:
    name = "liquidity"
    required_critical_data = ["client_profile", "vehicle_universe", "as_of_date"]

    def run(self, case) -> EngineResult:
        short_days = parameter_value(case, "liquidity_bucket_short_days")
        medium_days = parameter_value(case, "liquidity_bucket_medium_days")
        client = case.input_data["client_profile"]
        universe = case.input_data["vehicle_universe"]
        as_of = case.input_data["as_of_date"]

        values_by_vehicle = case.input_data.get("current_values")
        if values_by_vehicle is None:
            construction = case.engine_results.get("construction")
            if construction is None or construction.insufficient_data:
                return EngineResult(
                    engine_name=self.name, insufficient_data=True,
                    insufficient_data_reason="No hay cartera sobre la cual medir liquidez.",
                )
            capital = sum(construction.values["capital_por_meta"].values())
            values_by_vehicle = {k: w * capital
                                 for k, w in construction.values["asignacion_total"].items()}

        limits = (int(short_days), int(medium_days), 10**9)

        def bucket_of_days(days: int) -> int:
            return next(i for i, lim in enumerate(limits) if days <= lim)

        assets = [0.0, 0.0, 0.0]
        for k, v in values_by_vehicle.items():
            assets[bucket_of_days(universe[k].dias_liquidez)] += v
        obligations = [0.0, 0.0, 0.0]
        detail = []
        for g in client.goals:
            if g.fecha is not None and g.fecha <= as_of:
                continue
            days = 0 if g.fecha is None else (g.fecha - as_of).days
            b = bucket_of_days(days)
            obligations[b] += g.monto_objetivo
            detail.append({"meta": g.nombre, "bucket": BUCKETS[b], "monto": g.monto_objetivo})

        ladder = []
        cum_a = cum_o = 0.0
        for i, name in enumerate(BUCKETS):
            cum_a += assets[i]
            cum_o += obligations[i]
            ladder.append({
                "bucket": name,
                "activos_disponibles": assets[i],
                "obligaciones": obligations[i],
                "lcr_acumulado": (cum_a / cum_o) if cum_o and i < 2 else None,
            })

        alerts = []
        min_lcr = parameter_value(case, "min_lcr_ratio")
        if min_lcr is None:
            alerts.append("Sin 'min_lcr_ratio' en el Parameter Registry: el LCR se informa pero no se evalúa.")
        else:
            for row in ladder:
                if row["lcr_acumulado"] is not None and row["lcr_acumulado"] < float(min_lcr):
                    alerts.append(f"LCR {row['bucket']} = {row['lcr_acumulado']:.2f}, bajo el mínimo {float(min_lcr):.2f}")

        return EngineResult(
            engine_name=self.name,
            values={"escalera": ladder, "obligaciones": detail, "alertas": alerts},
        )
