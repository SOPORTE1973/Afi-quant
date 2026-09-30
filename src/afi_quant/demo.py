"""
Demo del MVP del motor — corre dos Decision Cases de punta a punta con
datos reales del conector MCP_Afitrading (fixtures en data/fixtures/):

  1. Revisión de FI Falcom Tactical Chilean Equities con el ETF Singular
     IPSA como benchmark candidato -> el caso llega a explicación.
  2. El mismo caso sin serie de NAV -> el Completeness Gate lo bloquea.

Uso:  python -m afi_quant.demo
"""

from __future__ import annotations

import sys

from afi_quant.data.fixtures import etf_ipsa, falcom_tactical
from afi_quant.pipeline import run_fund_review


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def print_case(case) -> None:
    print(f"Caso {case.case_id}")
    print(f"  Disparador: {case.trigger}")
    print(f"  Estado final: {case.state.value}")
    if case.completeness_report and case.completeness_report.missing:
        print(f"  Datos CRITICAL faltantes: {case.completeness_report.missing}")

    for name, result in case.engine_results.items():
        print(f"\n  Motor '{name}'")
        if result.insufficient_data:
            print(f"    insufficient_data: {result.insufficient_data_reason}")
            continue
        for key, value in result.values.items():
            if key in ("fuente", "nota_elegibilidad"):
                continue
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    print(f"    {key}.{sub_key}: {sub_value}")
            else:
                print(f"    {key}: {_fmt(value)}")

    if case.explanation:
        print("\n  Explicación (M15, reglas fijas):")
        for line in case.explanation.split("\n"):
            print(f"    - {line}")

    print("\n  Historial:")
    for entry in case.history:
        print(f"    {entry}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    fund = falcom_tactical()
    bench = etf_ipsa()

    print("=" * 78)
    print("CASO 1 — revisión de fondo con datos completos")
    print("=" * 78)
    print(f"Fuente fondo:     {fund.source}")
    print(f"Fuente benchmark: {bench.source}\n")
    print_case(
        run_fund_review(
            {
                "nav_series_native_frequency": fund,
                # Serie de fondo: sin flujos externos, declarado explícitamente.
                "cash_flows_dated_classified": [],
                "benchmark_index_series": bench,
            },
            trigger="revisión periódica — FI Falcom Tactical Chilean Equities",
        )
    )

    print("\n" + "=" * 78)
    print("CASO 2 — mismo fondo, sin serie de NAV (el gate debe bloquear)")
    print("=" * 78)
    print_case(
        run_fund_review(
            {"cash_flows_dated_classified": [], "benchmark_index_series": bench},
            trigger="revisión periódica — sin datos de NAV",
        )
    )


if __name__ == "__main__":
    main()
