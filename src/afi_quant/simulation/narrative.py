"""
Reglas de explicación (M15) para los eventos del ciclo de vida.

Una regla por tipo de evento: condición fija -> plantilla fija. Mismos
datos, mismo texto (Principio 3).
"""

from __future__ import annotations

from afi_quant.explanation.layer import ExplanationLayer, ExplanationRule


def _is(event_type: str):
    return lambda c: c.get("evento") == event_type


LIFECYCLE_RULES = [
    ExplanationRule(
        "onboarding", _is("onboarding"),
        "Se construyó una cartera por meta con MVO robusto sobre {cma_n_obs} meses de historia "
        "({cma_desde} a {cma_hasta}). Asignación total: {asignacion}. Retorno esperado "
        "{retorno_esperado:.1%} y volatilidad ex-ante {volatilidad:.1%}. {nota_cma}",
    ),
    ExplanationRule(
        "onboarding_alertas", lambda c: c.get("evento") == "onboarding" and c.get("alertas"),
        "Alertas de diversificación y liquidez: {alertas}.",
    ),
    ExplanationRule(
        "revision_sin_cambios", lambda c: c.get("evento") == "revision" and not c.get("rebalanceadas"),
        "Revisión trimestral: ningún vehículo se desvió más de {banda:.0%} de su peso objetivo; "
        "no se propone operar (cardinalidad cero). Mayor desvío: {mayor_desvio:+.1%} en "
        "{mayor_desvio_vehiculo} ({mayor_desvio_meta}).",
    ),
    ExplanationRule(
        "revision_rebalanceo", lambda c: c.get("evento") == "revision" and c.get("rebalanceadas"),
        "Revisión trimestral: {rebalanceadas} superó la banda de {banda:.0%} (mayor desvío "
        "{mayor_desvio:+.1%} en {mayor_desvio_vehiculo}); se rebalanceó a su objetivo moviendo "
        "{monto_operado} CLP.",
    ),
    ExplanationRule(
        "cambio_horizonte", _is("cambio_horizonte"),
        "La meta '{meta}' pasó de horizonte {horizonte_antes} a {horizonte_despues} ({meses} meses "
        "para su fecha). Su cartera se reconstruyó con el tope de volatilidad del nuevo horizonte "
        "({tope:.1%}): {pesos}.",
    ),
    ExplanationRule(
        "revision_anual", _is("revision_anual"),
        "Revisión anual: se reestimó la historia de la CMA con los últimos {cma_n_obs} meses "
        "({cma_desde} a {cma_hasta}) y se reoptimizaron las carteras. {nota_cma} Nueva "
        "asignación total: {asignacion}.",
    ),
    ExplanationRule(
        "proyeccion", lambda c: c.get("probabilidades"),
        "Probabilidad de alcanzar cada meta (Monte Carlo por bloques, {simulaciones} "
        "trayectorias): {probabilidades}.",
    ),
    ExplanationRule(
        "alerta_caida", _is("alerta_caida"),
        "La cartera total cayó {caida:.1%} desde su máximo del {fecha_maximo}, más que el umbral "
        "de {umbral:.0%}: se abrió una revisión extraordinaria.",
    ),
    ExplanationRule(
        "meta_cumplida", _is("meta_cumplida"),
        "La meta '{meta}' llegó a su fecha con {valor} CLP y se retiró el monto objetivo de "
        "{objetivo} CLP. El excedente de {excedente} CLP pasó a '{destino}', que además recibe "
        "desde ahora el aporte mensual de {aporte} CLP.",
    ),
    ExplanationRule(
        "meta_deficit", _is("meta_deficit"),
        "La meta '{meta}' llegó a su fecha con {valor} CLP, {deficit} CLP bajo el objetivo de "
        "{objetivo} CLP. Se retiró todo lo disponible; el aporte mensual de {aporte} CLP pasa a "
        "'{destino}'.",
    ),
    ExplanationRule(
        "cierre", _is("cierre"),
        "Al {fecha}: cartera de {valor} CLP. TWR acumulado {twr:.2%} ({twr_anual:.2%} anual) y "
        "XIRR {xirr:.2%} anual, considerando {aportes} CLP aportados y {retiros} CLP retirados.",
    ),
    ExplanationRule(
        "cierre_riesgo", lambda c: c.get("evento") == "cierre" and c.get("riesgo_bloqueado"),
        "La volatilidad realizada no se informa: {riesgo_bloqueado}. Se usa la volatilidad "
        "ex-ante de {vol_ex_ante:.1%}.",
    ),
]


def lifecycle_layer() -> ExplanationLayer:
    return ExplanationLayer(rules=list(LIFECYCLE_RULES))


def clp(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def weights_text(weights: dict[str, float]) -> str:
    return ", ".join(f"{k} {w:.0%}" for k, w in sorted(weights.items(), key=lambda kv: -kv[1]) if w > 0)
