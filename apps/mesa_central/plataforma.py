"""
Plataforma local de la Mesa Central: la misma interfaz, con el motor Python detrás.

    python apps/mesa_central/plataforma.py            # abre http://127.0.0.1:8800
    python apps/mesa_central/plataforma.py --puerto 9000
    abrir_plataforma.bat                               # doble clic en Windows

Qué agrega frente a la página publicada (que no puede correr Python):
  - El alta de un prospecto lo valida el motor real y, con el IPS firmado, lo
    ingresa al libro: corre su ciclo de vida desde la fecha de inicio elegida y
    recalcula el monitoreo y los agregados del libro.
  - Flujos extraordinarios del cliente (aportes y retiros fuera del plan) que
    se aplican en su mes y recalculan la cuenta.
  - Archivar una cuenta la saca del libro sin borrar su ficha.

Todo queda en `apps/mesa_central/local/` (fuera de git): una ficha JSON por
cliente y los datos calculados. Los valores cuota son los de
`src/afi_quant/data/fixtures/`; al actualizarlos, el libro se recalcula solo
al iniciar (la huella de los datos cambia).

El motor trabaja con cierres mensuales: una cuenta parte en un cierre de mes y
avanza cada mes con datos. El sistema nunca ejecuta órdenes ni contacta al
cliente (QM XX): registra lo que el asesor decidió.
"""

from __future__ import annotations

import hashlib
import json
import queue
import re
import sys
import threading
import traceback
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from afi_quant.book.clients import BookClient, book_clients  # noqa: E402
from afi_quant.book.prospect import compare, construct_prospect, from_ficha  # noqa: E402
from afi_quant.book.run import (  # noqa: E402
    account_entry, book_aggregates, fund_reviews, holdings_entry, run_client,
)
from afi_quant.engines.monitoring import prioritize  # noqa: E402
from afi_quant.portfolio.universe import default_universe, policy_benchmark_proxies  # noqa: E402
from afi_quant.registries.parameter_registry import get_parameter  # noqa: E402
from afi_quant.simulation.lifecycle import CMA_WINDOW_MONTHS, _month_ends  # noqa: E402
from afi_quant.simulation.parameters import simulation_registry  # noqa: E402

LOCAL = HERE / "local"
CLIENTS_DIR = LOCAL / "clientes"
DATA = LOCAL / "data"
SCRIPTS = ("app.js", "client.js", "crisis.js", "cartera.js", "dd.js", "pres.js", "onboarding.js", "plataforma.js")
ID_RE = re.compile(r"^PRO-[A-Z0-9]{3,12}$")


# --- Fichas de clientes ---------------------------------------------------

def load_records() -> dict[str, dict]:
    CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(CLIENTS_DIR.glob("*.json"))}


def save_record(rec: dict) -> None:
    CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
    (CLIENTS_DIR / f"{rec['id']}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")


def book_client(rec: dict) -> BookClient:
    """Ficha del asistente + alta firmada -> cliente del libro. Lo no declarado sigue en None."""
    client, ips, _ = from_ficha(rec["ficha"])
    inicio = date.fromisoformat(rec["alta"]["inicio"])
    client = replace(client, sintetico=False, nota="Cliente ingresado desde la plataforma.")
    ips = replace(ips, ips_id=f"IPS-{rec['id']}-v1", firmado=True, vigente_desde=inicio,
                  revisar_antes_de=date(inicio.year + 3, inicio.month, min(inicio.day, 28)), sintetico=False)
    return BookClient(client, ips, inicio, rec["alta"].get("asesor") or "Sin asignar",
                      eventos=rec.get("eventos", []), origen="plataforma")


def active_clients() -> list[BookClient]:
    return book_clients() + [book_client(r) for r in load_records().values() if r.get("estado") == "activo"]


# --- Calendario de datos --------------------------------------------------

def month_closes(universe) -> list[date]:
    """Cierres de mes comunes a todo el universo (fecha del último dato de cada mes)."""
    ends = {k: {(p.fecha.year, p.fecha.month): p.fecha for p in _month_ends(v.series.points)}
            for k, v in universe.items()}
    common = sorted(set.intersection(*(set(e) for e in ends.values())))
    return [ends["MM"][ym] for ym in common]


def start_dates(universe) -> list[date]:
    """Fechas de inicio posibles: hay CMA (36 meses de historia común) y al menos un mes posterior."""
    closes = month_closes(universe)
    first_common = closes[0]
    min_start = date(first_common.year + CMA_WINDOW_MONTHS // 12, first_common.month, 1)
    return [d for d in closes[:-1] if d >= min_start]


def fingerprint() -> str:
    h = hashlib.sha256()
    for p in sorted((ROOT / "src" / "afi_quant").rglob("*")):
        if p.suffix in (".csv", ".json", ".py") and "__pycache__" not in p.parts:
            h.update(p.name.encode()); h.update(p.read_bytes())
    for p in (HERE / "build_data.py", HERE / "motor_data.py"):
        h.update(p.read_bytes())
    for rid, rec in load_records().items():
        h.update(json.dumps(rec, sort_keys=True).encode())
    return h.hexdigest()[:16]


# --- Cálculo del libro ----------------------------------------------------

def full_build() -> None:
    """Calcula en una carpeta aparte y la reemplaza al final: mientras tanto se sigue sirviendo el libro anterior."""
    import shutil
    from build_data import main as build_data
    tmp = LOCAL / "data_nuevo"
    shutil.rmtree(tmp, ignore_errors=True)
    build_data(str(tmp), clients=active_clients())
    (tmp / "_huella.json").write_text(json.dumps({"huella": fingerprint(), "calculado": datetime.now().isoformat()}),
                                      encoding="utf-8")
    shutil.rmtree(DATA, ignore_errors=True)
    tmp.rename(DATA)


def _context():
    u = default_universe()
    reg = simulation_registry()
    return u, reg, (lambda n: get_parameter(n, reg).value)


def update_client(cid: str) -> None:
    """Corre (o vuelve a correr) una cuenta y la integra al libro ya calculado."""
    from build_data import client_entry, client_payload, js
    rec = load_records()[cid]
    bc = book_client(rec)
    u, reg, P = _context()
    r = run_client(bc, u, reg)
    libro = json.loads((DATA / "libro.json").read_text(encoding="utf-8"))
    estado = json.loads((DATA / "_estado.json").read_text(encoding="utf-8"))
    as_of = date.fromisoformat(libro["as_of"])
    reviews = fund_reviews(u, as_of, P, r.advisory["calidad_datos"]["series"])
    account = account_entry(bc, r, u, P, reviews)
    payload = client_payload(bc, r, u, policy_benchmark_proxies(), P, account)
    (DATA / "clientes" / f"{cid}.json").write_text(
        json.dumps(js(payload), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    holdings = [h for h in estado["holdings"] if h["id"] != cid] + [js(holdings_entry(bc, r))]
    accounts = [a for a in libro["monitoreo"] if a["id"] != cid] + [js(account)]
    libro["clientes"][cid] = js(client_entry(bc, r))
    _write_book(libro, holdings, accounts, u)


def remove_client(cid: str) -> None:
    libro = json.loads((DATA / "libro.json").read_text(encoding="utf-8"))
    estado = json.loads((DATA / "_estado.json").read_text(encoding="utf-8"))
    libro["clientes"].pop(cid, None)
    (DATA / "clientes" / f"{cid}.json").unlink(missing_ok=True)
    _write_book(libro, [h for h in estado["holdings"] if h["id"] != cid],
                [a for a in libro["monitoreo"] if a["id"] != cid], default_universe())


def _write_book(libro: dict, holdings: list[dict], accounts: list[dict], u) -> None:
    from build_data import js
    F = libro["fondos"]
    agg = book_aggregates(holdings, u, {k: F[k]["elegibilidad"]["elegible"] for k in F},
                          {k: bool(F[k]["senales"]) for k in F})
    libro["agregados"] = js(agg)
    libro["monitoreo"] = js(prioritize(accounts))
    for k in F:
        F[k]["tenedores"] = libro["agregados"]["tenedores"][k]
    (DATA / "libro.json").write_text(json.dumps(libro, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA / "_estado.json").write_text(json.dumps({"holdings": holdings}, ensure_ascii=False), encoding="utf-8")
    (DATA / "_huella.json").write_text(json.dumps({"huella": fingerprint(), "calculado": datetime.now().isoformat()}),
                                       encoding="utf-8")


# --- Cola de trabajos (un cálculo a la vez) -------------------------------

class Worker:
    def __init__(self):
        self.q: queue.Queue = queue.Queue()
        self.state = {"estado": "libre", "tarea": None, "desde": None, "error": None, "ultimo": None, "version": 0}
        threading.Thread(target=self._loop, daemon=True).start()

    def submit(self, label: str, fn, *args) -> None:
        self.q.put((label, fn, args))

    def _loop(self):
        while True:
            label, fn, args = self.q.get()
            self.state.update(estado="calculando", tarea=label, desde=datetime.now().isoformat(), error=None)
            try:
                fn(*args)
                self.state.update(ultimo=label)
            except Exception as exc:  # el error queda visible en la interfaz, nunca en silencio
                traceback.print_exc()
                self.state.update(error=f"{label}: {exc}")
            self.state["version"] += 1
            if self.q.empty():
                self.state.update(estado="libre", tarea=None, desde=None)


worker = Worker()


def ensure_book() -> None:
    try:
        stored = json.loads((DATA / "_huella.json").read_text(encoding="utf-8"))["huella"]
    except (OSError, ValueError, KeyError):
        stored = None
    if stored != fingerprint() or not (DATA / "libro.json").exists():
        worker.submit("Calcular el libro completo (datos o motor cambiaron)", full_build)


# --- API ------------------------------------------------------------------

app = FastAPI(title="Mesa Central AFI Quant — plataforma local")


class Proposal(BaseModel):
    ficha: dict


class Onboard(BaseModel):
    ficha: dict
    inicio: str
    asesor: str = ""


class Flow(BaseModel):
    fecha: str
    tipo: str
    meta: str
    monto: float
    motivo: str = ""


@app.get("/api/estado")
def status() -> dict:
    u = default_universe()
    recs = load_records()
    closes = month_closes(u)
    return {
        "modo": "plataforma", "trabajo": worker.state, "datos_al": closes[-1].isoformat(),
        "inicios": [d.isoformat() for d in start_dates(u)],
        "clientes": [{"id": k, "nombre": r["ficha"]["prospecto"]["cliente"].get("nombre") or k,
                      "estado": r.get("estado"), "inicio": r["alta"]["inicio"], "eventos": len(r.get("eventos", []))}
                     for k, r in recs.items()],
    }


@app.post("/api/proponer")
def propose(req: Proposal) -> dict:
    try:
        out = construct_prospect(req.ficha)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(400, f"Ficha inválida: {exc}") from exc
    if "insuficiente" in out:
        return {"ok": False, "motivo": out["insuficiente"]}
    return {"ok": True, "motor": out, "diferencias": compare(out, req.ficha.get("propuesta_navegador"))}


@app.post("/api/clientes")
def onboard(req: Onboard) -> dict:
    p = req.ficha.get("prospecto") or {}
    cid = p.get("id", "")
    if not ID_RE.match(cid):
        raise HTTPException(400, "El identificador del prospecto no es válido.")
    if cid in load_records() or cid in {bc.client.client_id for bc in book_clients()}:
        raise HTTPException(409, f"{cid} ya existe en el libro.")
    if req.inicio not in {d.isoformat() for d in start_dates(default_universe())}:
        raise HTTPException(400, "La fecha de inicio debe ser un cierre de mes con datos posteriores.")
    if not p.get("metas") or not (p.get("riesgo") or {}).get("perfil") or not (p.get("cliente") or {}).get("nacimiento"):
        raise HTTPException(400, "Faltan metas, perfil de riesgo o fecha de nacimiento.")
    try:
        client, _, _ = from_ficha(req.ficha)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(400, f"Ficha inválida: {exc}") from exc
    late = [g.nombre for g in client.goals if g.fecha is not None and g.fecha <= date.fromisoformat(req.inicio)]
    if late:
        raise HTTPException(400, f"Estas metas vencen antes del inicio de la cartera: {', '.join(late)}.")
    rec = {"id": cid, "estado": "activo", "ficha": req.ficha, "eventos": [],
           "alta": {"inicio": req.inicio, "asesor": req.asesor.strip()[:60], "ips_firmado": date.today().isoformat(),
                    "registrado": datetime.now().isoformat()}}
    save_record(rec)
    worker.submit(f"Ingresar {cid} al libro", update_client, cid)
    return {"id": cid}


@app.post("/api/clientes/{cid}/flujos")
def add_flow(cid: str, req: Flow) -> dict:
    recs = load_records()
    if cid not in recs or recs[cid].get("estado") != "activo":
        raise HTTPException(404, "Cuenta no encontrada en la plataforma.")
    rec = recs[cid]
    if req.tipo not in ("aporte", "retiro") or req.monto <= 0:
        raise HTTPException(400, "Tipo debe ser aporte o retiro, con monto positivo.")
    goals = {m["key"] for m in rec["ficha"]["prospecto"]["metas"]}
    if req.meta not in goals:
        raise HTTPException(400, "La meta no existe en la ficha del cliente.")
    d = date.fromisoformat(req.fecha)
    inicio, last = date.fromisoformat(rec["alta"]["inicio"]), month_closes(default_universe())[-1]
    if not ((d.year, d.month) > (inicio.year, inicio.month) and d <= last):
        raise HTTPException(400, f"La fecha debe caer en un mes posterior al inicio y no después del {last:%d-%m-%Y}.")
    rec.setdefault("eventos", []).append({**req.model_dump(), "registrado": datetime.now().isoformat()})
    save_record(rec)
    worker.submit(f"Recalcular {cid} con el nuevo {req.tipo}", update_client, cid)
    return {"ok": True}


@app.post("/api/clientes/{cid}/archivar")
def archive(cid: str) -> dict:
    recs = load_records()
    if cid not in recs:
        raise HTTPException(404, "Cuenta no encontrada en la plataforma.")
    recs[cid]["estado"] = "archivado"
    save_record(recs[cid])
    worker.submit(f"Sacar {cid} del libro", remove_client, cid)
    return {"ok": True}


@app.post("/api/recalcular")
def rebuild() -> dict:
    worker.submit("Recalcular el libro completo", full_build)
    return {"ok": True}


@app.get("/data/{path:path}")
def data(path: str):
    f = (DATA / path).resolve()
    if DATA.resolve() not in f.parents or not f.is_file() or f.name.startswith("_"):
        raise HTTPException(404)
    if worker.state["estado"] == "calculando" and not (DATA / "libro.json").exists():
        raise HTTPException(503, "El libro se está calculando.")
    return FileResponse(f, headers={"Cache-Control": "no-store"})


@app.get("/{name}.js")
def script(name: str):
    if f"{name}.js" not in SCRIPTS:
        raise HTTPException(404)
    return FileResponse(HERE / f"{name}.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})


@app.get("/", response_class=HTMLResponse)
def index():
    html = (HERE / "index.html").read_text(encoding="utf-8")
    return HTMLResponse("<!doctype html><meta charset=\"utf-8\"><meta name=\"viewport\" "
                        "content=\"width=device-width,initial-scale=1\">" + html,
                        headers={"Cache-Control": "no-store"})


@app.exception_handler(Exception)
def unexpected(_, exc):
    return JSONResponse({"detail": f"Error interno: {exc}"}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    sys.stdout.reconfigure(encoding="utf-8")
    port = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 8800
    ensure_book()
    url = f"http://127.0.0.1:{port}"
    print(f"Mesa Central en {url}  (Ctrl+C para salir)")
    if "--sin-navegador" not in sys.argv:
        import webbrowser
        threading.Timer(1.5, webbrowser.open, (url,)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
