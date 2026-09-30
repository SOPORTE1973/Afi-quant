"""
Demo del ciclo de vida de un cliente ficticio sobre precios reales.

Uso:
    python -m afi_quant.simulation.demo              # línea de tiempo en consola
    python -m afi_quant.simulation.demo --json out.json   # además exporta todo a JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date

from afi_quant.portfolio.universe import default_universe
from afi_quant.simulation.lifecycle import run_lifecycle
from afi_quant.simulation.narrative import clp
from afi_quant.simulation.parameters import SIMULATION_SOURCE, SIMULATION_VALUES


def _jsonable(x):
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


def export(result) -> dict:
    universe = default_universe()
    client = result.client
    return _jsonable({
        "cliente": {
            "id": client.client_id,
            "nombre": client.nombre,
            "nota": client.nota,
            "edad_onboarding": client.age(result.onboarding),
            "perfil_riesgo": client.perfil_riesgo,
            "puntaje_cuestionario": client.puntaje_cuestionario,
            "gasto_mensual": client.gasto_mensual,
            "metas": [asdict(g) for g in client.goals],
        },
        "universo": {
            k: {"nombre": v.nombre, "administradora": v.administradora,
                "clase_activo": v.clase_activo, "subclase": v.subclase,
                "liquidez": v.liquidez, "rut": v.series.rut, "serie": v.series.serie,
                "nemotecnico": v.nemotecnico}
            for k, v in universe.items()
        },
        "parametros_simulacion": {"fuente": SIMULATION_SOURCE, "valores": SIMULATION_VALUES},
        "onboarding": result.onboarding,
        "resultados_onboarding": result.onboarding_results,
        "resultados_cierre": result.closing_results,
        "resumen": result.summary,
        "eventos": [asdict(e) for e in result.events],
        "meses": [asdict(r) for r in result.rows],
        "casos": [{"case_id": c.case_id, "trigger": c.trigger, "estado": c.state.value,
                   "motores": c.plan.engines if c.plan else [], "historial": c.history}
                  for c in result.cases],
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", help="ruta donde exportar el resultado completo")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    result = run_lifecycle()
    client = result.client
    print("=" * 78)
    print(f"{client.nombre} ({client.client_id}) — {client.nota}")
    print(f"Perfil {client.perfil_riesgo}, {client.age(result.onboarding)} años al onboarding "
          f"({result.onboarding.isoformat()})")
    for g in client.goals:
        fecha = g.fecha.isoformat() if g.fecha else "permanente"
        print(f"  - {g.nombre}: objetivo {clp(g.monto_objetivo)} CLP, fecha {fecha}, "
              f"capital inicial {clp(g.capital_inicial)}, aporte {clp(g.aporte_mensual)}/mes")
    print(f"Parámetros: {SIMULATION_SOURCE}")
    print("=" * 78)
    for e in result.events:
        print(f"\n[{e.fecha.isoformat()}] {e.titulo}")
        print(f"  {e.explicacion}")
    s = result.summary
    print("\n" + "=" * 78)
    print(f"Valor final {clp(s['valor_final'])} CLP · TWR {s['twr']:.2%} · XIRR {s['xirr']:.2%} · "
          f"{len(result.cases)} Decision Cases registrados")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(export(result), fh, ensure_ascii=False, indent=1)
        print(f"Exportado a {args.json}")


if __name__ == "__main__":
    main()
