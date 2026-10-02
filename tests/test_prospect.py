"""Prospecto de la Mesa Central -> motor real (afi_quant.book.prospect)."""

import pytest

from afi_quant.book.prospect import compare, construct_prospect, from_ficha


def _ficha(**riesgo):
    return {
        "formato": "afi-prospecto-v1", "datos_al": "2026-09-29",
        "prospecto": {
            "id": "PRO-T", "cliente": {"nombre": "Prueba", "nacimiento": "1985-06-01", "pais": "Chile", "segmento": "Wealth"},
            "riesgo": {"perfil": "Moderado", "puntaje": 55, "capacidad": "", "vol": 8, "var": "", "es": "", "dd": "", **riesgo},
            "patrimonio": {"total": "", "fuera": "", "capital_humano": "", "activos_nf": "", "pasivos": "", "compromisos": "",
                           "esg": "", "regulatorias": "", "familiares": "", "admin": ""},
            "metas": [
                {"key": "emergencia", "nombre": "Emergencia", "prioridad": "esencial", "objetivo": 15e6, "fecha": "",
                 "reserva": True, "capital": 15e6, "aporte": 0, "prob_deseada": "", "liquidez": "3 días"},
                {"key": "retiro", "nombre": "Retiro", "prioridad": "esencial", "objetivo": 600e6, "fecha": "2046-09-28",
                 "reserva": False, "capital": 120e6, "aporte": 1e6, "prob_deseada": 75, "liquidez": ""},
            ],
        },
    }


def test_from_ficha_keeps_missing_as_none():
    client, ips, as_of = from_ficha(_ficha())
    assert [g.fecha for g in client.goals][0] is None
    assert client.goals[1].probabilidad_deseada == 0.75
    assert ips.firmado is False and ips.life_balance_sheet is None and ips.limites_riesgo.var95_1m_max_pct is None
    assert ips.limites_riesgo.volatilidad_max_pct == 8.0


def test_ips_volatility_caps_long_goal_and_compare():
    out = construct_prospect(_ficha())
    assert out["sleeves"]["retiro"]["tope"] == pytest.approx(0.08)
    assert out["sleeves"]["emergencia"]["pesos"] == {"MM": 1.0}
    assert compare(out, {"total": out["total"], "probabilidades": out["probabilidades"], "niveles": out["niveles"]}) == []


def test_rejects_unknown_format():
    with pytest.raises(ValueError):
        from_ficha({"formato": "otro"})
