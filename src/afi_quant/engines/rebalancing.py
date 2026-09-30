"""
Motor de Monitoreo y Rebalanceo — compara la cartera real de cada meta
contra su asignación objetivo.

Regla: si algún vehículo de una meta se desvía de su peso objetivo más
que `rebalancing_band_pct` (puntos porcentuales), se propone volver esa
meta a su objetivo. Si ningún desvío supera la banda, no se propone nada
(cardinalidad cero es una respuesta válida, ESFS-01 M13).
"""

from __future__ import annotations

from afi_quant.engines.base import EngineResult, parameter_value


class RebalancingEngine:
    name = "rebalancing"
    required_critical_data = ["sleeve_holdings", "target_sleeves"]

    def run(self, case) -> EngineResult:
        band = parameter_value(case, "rebalancing_band_pct")
        if band is None:
            return EngineResult(
                engine_name=self.name, insufficient_data=True,
                insufficient_data_reason=(
                    "El Parameter Registry no tiene 'rebalancing_band_pct': sin banda no se "
                    "puede decidir si un desvío amerita rebalancear."
                ),
            )
        band = float(band) / 100
        holdings = case.input_data["sleeve_holdings"]     # meta -> {vehículo: CLP}
        targets = case.input_data["target_sleeves"]       # meta -> {vehículo: peso}

        sleeves = {}
        for goal, values in holdings.items():
            total = sum(values.values())
            if total <= 0 or goal not in targets:
                continue
            keys = set(values) | set(targets[goal])
            drift = {k: values.get(k, 0.0) / total - targets[goal].get(k, 0.0) for k in keys}
            worst = max(keys, key=lambda k: abs(drift[k]))
            breach = abs(drift[worst]) > band + 1e-12
            trades = {}
            if breach:
                trades = {k: targets[goal].get(k, 0.0) * total - values.get(k, 0.0) for k in keys}
                trades = {k: v for k, v in trades.items() if abs(v) >= 1}
            sleeves[goal] = {
                "valor": total,
                "desvios": drift,
                "mayor_desvio_vehiculo": worst,
                "mayor_desvio": drift[worst],
                "fuera_de_banda": breach,
                "operaciones_propuestas": trades,
            }
        return EngineResult(
            engine_name=self.name,
            values={"banda": band, "metas": sleeves,
                    "rebalancear": [g for g, s in sleeves.items() if s["fuera_de_banda"]]},
        )
