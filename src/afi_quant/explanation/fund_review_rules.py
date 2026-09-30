"""
Reglas de explicación para la revisión de un fondo (M15) — MVP.

Cada regla es condición fija -> plantilla fija. Nada de generación libre:
con los mismos resultados de motores, el texto es idéntico (Principio 3).
`build_context` aplana los EngineResult del caso a un dict plano
`<motor>_<clave>` que las plantillas consumen.
"""

from __future__ import annotations

from afi_quant.explanation.layer import ExplanationLayer, ExplanationRule


def build_context(case) -> dict:
    ctx: dict = {}
    for engine_name, result in case.engine_results.items():
        ctx[f"{engine_name}_ok"] = not result.insufficient_data
        ctx[f"{engine_name}_motivo"] = result.insufficient_data_reason
        for key, value in result.values.items():
            ctx[f"{engine_name}_{key}"] = value
    blocked = ctx.get("risk_no_calculado") or {}
    ctx["risk_bloqueos"] = "; ".join(f"{k}: {v.rstrip('.')}" for k, v in blocked.items())
    return ctx


def _has(*keys):
    return lambda c: all(c.get(k) is not None for k in keys)


FUND_REVIEW_RULES: list[ExplanationRule] = [
    ExplanationRule(
        name="performance_bloqueado",
        condition=lambda c: c.get("performance_ok") is False,
        template="Performance no calculado: {performance_motivo}",
    ),
    ExplanationRule(
        name="performance_periodo",
        condition=_has("performance_twr_periodo"),
        template=(
            "{performance_nemotecnico} rindió {performance_twr_periodo:.2%} entre "
            "{performance_desde} y {performance_hasta} (TWR sobre NAV ajustado, con "
            "repartos reinvertidos), equivalente a {performance_cagr:.2%} anual."
        ),
    ),
    ExplanationRule(
        name="cagr_periodo_corto",
        condition=lambda c: c.get("performance_cagr_periodo_corto") is True,
        template=(
            "El período es menor a 3 años, así que la cifra anualizada es poco "
            "informativa (Model Governance Registry)."
        ),
    ),
    ExplanationRule(
        name="performance_trailing",
        condition=_has("performance_twr_1a", "performance_twr_3a"),
        template="Últimos 12 meses: {performance_twr_1a:.2%}. Últimos 3 años: {performance_twr_3a:.2%}.",
    ),
    ExplanationRule(
        name="excess_return",
        condition=_has("performance_excess_return"),
        template="Contra el benchmark certificado, el exceso de retorno fue {performance_excess_return:.2%}.",
    ),
    ExplanationRule(
        name="excess_return_bloqueado",
        condition=_has("performance_excess_return_bloqueado"),
        template="No se compara contra benchmark: {performance_excess_return_bloqueado}",
    ),
    ExplanationRule(
        name="benchmark_candidato",
        condition=_has("benchmark_retorno_periodo_twr"),
        template=(
            "Como referencia no certificada, {benchmark_nemotecnico} rindió "
            "{benchmark_retorno_periodo_twr:.2%} entre {benchmark_desde} y {benchmark_hasta}."
        ),
    ),
    ExplanationRule(
        name="risk_bloqueado",
        condition=lambda c: c.get("risk_ok") is False,
        template="Riesgo no calculado: {risk_motivo}",
    ),
    ExplanationRule(
        name="volatilidad",
        condition=_has("risk_volatilidad_anual"),
        template=(
            "Volatilidad anualizada: {risk_volatilidad_anual:.2%}, sobre "
            "{risk_n_retornos_mensuales} retornos mensuales."
        ),
    ),
    ExplanationRule(
        name="drawdown_recuperado",
        condition=_has("risk_max_drawdown_recuperacion"),
        template=(
            "La mayor caída fue {risk_max_drawdown:.2%} (máximo el {risk_max_drawdown_peak}, "
            "mínimo el {risk_max_drawdown_trough}); se recuperó el "
            "{risk_max_drawdown_recuperacion}, {risk_max_drawdown_dias_recuperacion} días "
            "después del mínimo."
        ),
    ),
    ExplanationRule(
        name="drawdown_no_recuperado",
        condition=lambda c: c.get("risk_max_drawdown") is not None
        and c.get("risk_max_drawdown_recuperacion") is None,
        template=(
            "La mayor caída fue {risk_max_drawdown:.2%} (máximo el {risk_max_drawdown_peak}, "
            "mínimo el {risk_max_drawdown_trough}) y todavía no se recupera."
        ),
    ),
    ExplanationRule(
        name="var_es",
        condition=_has("risk_var_95_1m", "risk_var_99_1m"),
        template=(
            "En la historia mensual, el 5% de los peores meses perdió al menos "
            "{risk_var_95_1m:.2%} (VaR 95%), con una pérdida promedio de {risk_es_95_1m:.2%} "
            "en esos meses (ES 95%). Al 99%, el VaR mensual es {risk_var_99_1m:.2%} y el "
            "ES {risk_es_99_1m:.2%}. Observaciones en la cola: {risk_obs_cola_95} (95%) y "
            "{risk_obs_cola_99} (99%)."
        ),
    ),
    ExplanationRule(
        name="riesgo_no_calculado",
        condition=lambda c: bool(c.get("risk_bloqueos")),
        template="No calculado en riesgo — {risk_bloqueos}.",
    ),
    ExplanationRule(
        name="alcance",
        condition=lambda c: c.get("performance_ok") or c.get("risk_ok"),
        template=(
            "Alcance: diagnóstico descriptivo del fondo. Sin benchmark certificado ni "
            "parámetros del Comité, este caso no sostiene una recomendación."
        ),
    ),
]


def fund_review_layer() -> ExplanationLayer:
    return ExplanationLayer(rules=list(FUND_REVIEW_RULES))
