"""
Capital Market Assumptions (CMA) estimadas desde la historia de NAV.

IMPORTANTE: el Parameter Registry exige CMAs INSTITUCIONALES (nunca un
supuesto individual del asesor). Mientras el Comité no las publique, esta
estimación histórica es un reemplazo PROVISIONAL, marcado como tal en su
resultado. Se estima solo con datos hasta `as_of` — nunca con datos
posteriores a la fecha de la decisión (sin look-ahead).

Método:
  - retornos mensuales (último NAV de cada mes) comunes a todo el universo
  - μ anual = media mensual × 12, acercada con intensidad
    `cma_return_shrinkage` a un prior de Sharpe común: el retorno del
    activo menos volátil más un premio proporcional a la volatilidad de
    cada clase (mediana del Sharpe de las demás). Acercar μ a un promedio
    simple subiría el retorno esperado de las clases de bajo riesgo; el
    prior de Sharpe común conserva la relación riesgo-retorno.
  - Σ anual = Σ muestral mensual × 12, con shrinkage hacia un target de
    correlación constante con intensidad `cma_covariance_shrinkage`
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, replace
from datetime import date

from afi_quant.engines.series import month_end_points, period_returns

CMA_NOTE = (
    "CMA histórica PROVISIONAL: estimada desde la historia de NAV hasta la fecha de "
    "decisión. No reemplaza las CMAs institucionales que debe publicar el Comité."
)


@dataclass
class MonthlyHistory:
    keys: list[str]
    months: list[date]                 # fecha de cierre de cada retorno
    returns: dict[str, list[float]]    # key -> retornos mensuales alineados con `months`

    def __len__(self) -> int:
        return len(self.months)


def monthly_history(universe, as_of: date, months: int | None = None) -> MonthlyHistory:
    """Retornos mensuales comunes a todo el universo, con cierres <= as_of."""
    ends = {
        k: {(p.fecha.year, p.fecha.month): p
            for p in month_end_points([p for p in v.series.points if p.fecha <= as_of])}
        for k, v in universe.items()
    }
    common = sorted(set.intersection(*(set(e) for e in ends.values())))
    if months is not None:
        common = common[-(months + 1):]
    keys = list(universe)
    returns = {k: period_returns([ends[k][m] for m in common]) for k in keys}
    month_dates = [ends[keys[0]][m].fecha for m in common[1:]]
    return MonthlyHistory(keys=keys, months=month_dates, returns=returns)


@dataclass
class CMA:
    keys: list[str]
    mu: dict[str, float]            # retorno esperado anual (post shrinkage)
    mu_historico: dict[str, float]  # antes del shrinkage
    ancla: str                      # activo menos volátil, base del prior de Sharpe común
    sharpe_comun: float
    cov: dict[tuple[str, str], float]  # anual (post shrinkage)
    corr: dict[tuple[str, str], float]  # muestral
    n_obs: int
    desde: date
    hasta: date
    nota: str = CMA_NOTE

    def vol(self, k: str) -> float:
        return math.sqrt(self.cov[(k, k)])

    def portfolio_variance(self, w: dict[str, float]) -> float:
        return sum(w[i] * w[j] * self.cov[(i, j)] for i in w for j in w)

    def portfolio_return(self, w: dict[str, float]) -> float:
        return sum(w[k] * self.mu[k] for k in w)


def estimate_cma(history: MonthlyHistory, return_shrinkage: float, cov_shrinkage: float) -> CMA:
    keys, R = history.keys, history.returns
    mu_hist = {k: statistics.fmean(R[k]) * 12 for k in keys}
    s = {(i, j): statistics.covariance(R[i], R[j]) for i in keys for j in keys}
    sd = {k: math.sqrt(s[(k, k)]) for k in keys}

    vol_hist = {k: sd[k] * math.sqrt(12) for k in keys}
    anchor = min(keys, key=lambda k: vol_hist[k])
    # Mediana, no promedio: un NAV suavizado (p. ej. deuda privada de facturas,
    # valorizada sin precio de mercado diario) muestra una volatilidad muy baja
    # y un Sharpe atípico que arrastraría el prior de todas las clases.
    sharpe = statistics.median(
        (mu_hist[k] - mu_hist[anchor]) / vol_hist[k] for k in keys if k != anchor
    )
    prior = {k: mu_hist[anchor] + sharpe * vol_hist[k] for k in keys}
    mu = {k: (1 - return_shrinkage) * mu_hist[k] + return_shrinkage * prior[k] for k in keys}

    corr = {(i, j): s[(i, j)] / (sd[i] * sd[j]) for i in keys for j in keys}
    off = [corr[(i, j)] for i in keys for j in keys if i != j]
    rbar = statistics.fmean(off)
    target = {(i, j): s[(i, j)] if i == j else rbar * sd[i] * sd[j] for i in keys for j in keys}
    cov = {ij: ((1 - cov_shrinkage) * s[ij] + cov_shrinkage * target[ij]) * 12 for ij in s}

    return CMA(
        keys=keys, mu=mu, mu_historico=mu_hist, ancla=anchor, sharpe_comun=sharpe,
        cov=cov, corr=corr,
        n_obs=len(history), desde=history.months[0], hasta=history.months[-1],
    )


INSTITUTIONAL_NOTE = (
    "Retornos esperados y volatilidades tomados del Parameter Registry "
    "(cma_expected_return / cma_expected_volatility); correlaciones históricas "
    "con shrinkage."
)


def apply_registry_assumptions(cma: CMA, universe, expected_returns_pct: dict | None,
                               expected_vols_pct: dict | None) -> CMA:
    """
    Reemplaza μ y/o σ por los valores del Parameter Registry (por subclase de
    la taxonomía) cuando existen. La estructura de correlaciones sigue siendo
    la histórica. Si el registro no trae valores, la CMA queda como estaba
    (histórica provisional) — nunca se mezcla en silencio.
    """
    if not expected_returns_pct and not expected_vols_pct:
        return cma
    mu = dict(cma.mu)
    if expected_returns_pct:
        mu = {k: expected_returns_pct[universe[k].subclase] / 100 for k in cma.keys}
    vol = {k: cma.vol(k) for k in cma.keys}
    if expected_vols_pct:
        vol = {k: expected_vols_pct[universe[k].subclase] / 100 for k in cma.keys}
    cov = {}
    for i in cma.keys:
        for j in cma.keys:
            rho = cma.cov[(i, j)] / (cma.vol(i) * cma.vol(j))
            cov[(i, j)] = rho * vol[i] * vol[j]
    return replace(cma, mu=mu, cov=cov, nota=INSTITUTIONAL_NOTE)


def build_cma(universe, as_of: date, window_months: int, parameter_of) -> CMA:
    """CMA en la fecha de decisión, con lo que el Parameter Registry tenga cargado."""
    cma = estimate_cma(
        monthly_history(universe, as_of, window_months),
        float(parameter_of("cma_return_shrinkage")),
        float(parameter_of("cma_covariance_shrinkage")),
    )
    return apply_registry_assumptions(
        cma, universe, parameter_of("cma_expected_return"), parameter_of("cma_expected_volatility"),
    )
