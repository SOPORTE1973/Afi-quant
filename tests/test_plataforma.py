"""Plataforma local: flujos extraordinarios en el ciclo de vida y validaciones de la API."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "mesa_central"))

from afi_quant.book.prospect import from_ficha  # noqa: E402
from afi_quant.portfolio.universe import default_universe  # noqa: E402
from afi_quant.simulation.lifecycle import run_lifecycle  # noqa: E402
from afi_quant.simulation.parameters import simulation_registry  # noqa: E402


def _ficha(cid="PRO-TEST1"):
    return {
        "formato": "afi-prospecto-v1", "datos_al": "2026-10-31",
        "prospecto": {
            "id": cid, "cliente": {"nombre": "Prueba", "nacimiento": "1985-06-01", "pais": "Chile", "segmento": "Wealth"},
            "riesgo": {"perfil": "Moderado", "puntaje": 55, "capacidad": "Media", "vol": 10, "var": 5, "es": 7, "dd": 15},
            "patrimonio": {"total": "", "fuera": "", "capital_humano": "", "activos_nf": "", "pasivos": "", "compromisos": "",
                           "esg": "", "regulatorias": "", "familiares": "", "admin": 60},
            "metas": [
                {"key": "emergencia", "nombre": "Emergencia", "prioridad": "esencial", "objetivo": 10e6, "fecha": "",
                 "reserva": True, "capital": 10e6, "aporte": 0, "prob_deseada": "", "liquidez": "3 días"},
                {"key": "retiro", "nombre": "Retiro", "prioridad": "esencial", "objetivo": 600e6, "fecha": "2046-09-28",
                 "reserva": False, "capital": 100e6, "aporte": 1e6, "prob_deseada": 75, "liquidez": ""},
            ],
        },
    }


@pytest.fixture(scope="module")
def runs():
    client, ips, _ = from_ficha(_ficha())
    u, reg = default_universe(), simulation_registry()
    base = run_lifecycle(client=client, universe=u, params=reg, onboarding=date(2026, 7, 31), ips=ips)
    flows = [{"fecha": "2026-09-15", "tipo": "aporte", "meta": "retiro", "monto": 20e6, "motivo": "bono"},
             {"fecha": "2026-10-10", "tipo": "retiro", "meta": "emergencia", "monto": 3e6, "motivo": "gasto"}]
    extra = run_lifecycle(client=client, universe=u, params=reg, onboarding=date(2026, 7, 31), ips=ips,
                          extra_flows=flows)
    return base, extra


def test_extra_flows_enter_ledger_and_totals(runs):
    base, extra = runs
    assert extra.summary["aportado"] == pytest.approx(base.summary["aportado"] + 20e6)
    assert extra.summary["retirado"] == pytest.approx(base.summary["retirado"] + 3e6)
    kinds = [e.tipo for e in extra.events]
    assert kinds.count("flujo_cliente") == 2
    sept = next(r for r in extra.rows if (r.fecha.year, r.fecha.month) == (2026, 9))
    sept_base = next(r for r in base.rows if (r.fecha.year, r.fecha.month) == (2026, 9))
    assert sept.aportes == pytest.approx(sept_base.aportes + 20e6)


def test_withdrawal_never_exceeds_goal():
    client, ips, _ = from_ficha(_ficha())
    r = run_lifecycle(client=client, universe=default_universe(), params=simulation_registry(),
                      onboarding=date(2026, 7, 31), ips=ips,
                      extra_flows=[{"fecha": "2026-08-20", "tipo": "retiro", "meta": "emergencia", "monto": 1e12}])
    paid = r.summary["retirado"]
    assert 0 < paid < 11e6
    assert "solo tenía" in next(e for e in r.events if e.tipo == "flujo_cliente").explicacion


def test_api_validations(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import plataforma
    monkeypatch.setattr(plataforma, "CLIENTS_DIR", tmp_path)
    monkeypatch.setattr(plataforma.worker, "submit", lambda *a: None)
    api = TestClient(plataforma.app)
    est = api.get("/api/estado").json()
    assert est["modo"] == "plataforma" and est["inicios"][0] == "2024-10-31"
    ok = {"ficha": _ficha(), "inicio": est["inicios"][-1], "asesor": "A"}
    assert api.post("/api/clientes", json={**ok, "inicio": "2026-10-15"}).status_code == 400
    bad = _ficha("SIM-001")
    assert api.post("/api/clientes", json={**ok, "ficha": bad}).status_code == 400
    assert api.post("/api/clientes", json=ok).status_code == 200
    assert api.post("/api/clientes", json=ok).status_code == 409
    rec = plataforma.load_records()["PRO-TEST1"]
    bc = plataforma.book_client(rec)
    assert bc.ips.firmado and bc.ips.vigente_desde == date.fromisoformat(est["inicios"][-1]) and bc.origen == "plataforma"
    flow = {"fecha": est["inicios"][-1], "tipo": "aporte", "meta": "retiro", "monto": 1e6}
    assert api.post("/api/clientes/PRO-TEST1/flujos", json=flow).status_code == 400   # mismo mes del inicio
    assert api.post("/api/clientes/PRO-TEST1/flujos", json={**flow, "fecha": est["datos_al"]}).status_code == 200
    assert api.post("/api/clientes/PRO-TEST1/flujos", json={**flow, "fecha": est["datos_al"], "meta": "x"}).status_code == 400
