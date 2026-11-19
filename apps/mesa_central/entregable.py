"""
Entregable de la Mesa Central: UN archivo HTML con los datos congelados a una fecha de corte.

    python apps/mesa_central/build.py          # primero: recalcula dist/ con los datos al día
    python apps/mesa_central/entregable.py     # luego: dist/entregable/Mesa-Central-corte-AAAA-MM-DD.html

El archivo trae adentro el libro, los clientes y el motor del asistente; las
llamadas a `data/...` se responden desde esa copia, así que no cambia aunque
los datos se actualicen después. Se abre con doble clic en cualquier navegador.
Necesita internet solo para dos librerías públicas (gráficos y exportación a
PowerPoint). Lo que depende de claude.ai (conector en vivo, registro compartido)
o de la plataforma local (ingresar clientes) no está disponible y lo dice.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"


def _fdate(iso: str) -> str:
    y, m, d = iso[:10].split("-")
    return f"{d}-{m}-{y}"


def build(dist: Path = DIST) -> Path:
    data = {}
    for f in sorted((dist / "data").rglob("*.json")):
        if not f.name.startswith("_"):
            data[f.relative_to(dist).as_posix()] = json.loads(f.read_text(encoding="utf-8"))
    corte = data["data/libro.json"]["as_of"]
    html = (dist / "index.html").read_text(encoding="utf-8")

    def inline(m):
        return "<script>\n" + (dist / m.group(1)).read_text(encoding="utf-8").replace("</script", "<\\/script") + "\n</script>"
    html = re.sub(r'<script src="([a-z]+\.[0-9a-f]{8}\.js)"></script>', inline, html)

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    shim = (
        "<script>\n/* Entregable: datos congelados al corte; data/... se responde desde esta copia. */\n"
        f"window.__CORTE = {payload};\n"
        "(function () { const real = window.fetch.bind(window);\n"
        "  window.fetch = function (u, o) { const k = String(u).replace(/^\\.?\\//, '').split('?')[0];\n"
        "    if (k in window.__CORTE) return Promise.resolve(new Response(JSON.stringify(window.__CORTE[k]), "
        "{ status: 200, headers: { 'Content-Type': 'application/json' } }));\n"
        "    if (k.startsWith('api/')) return Promise.reject(new Error('Sin servidor en el entregable'));\n"
        "    return real(u, o); }; })();\n</script>\n")
    first_app = html.index("<script>\n", html.index("pptxgen.bundle.js"))
    html = html[:first_app] + shim + html[first_app:]
    html = html.replace('<span class="tag-sim">Simulación</span>',
                        f'<span class="tag-sim">Simulación</span><span class="tag-sim" style="background:#78a9ff">'
                        f'Entregable · datos al {_fdate(corte)}</span>', 1)
    html = html.replace(
        '<div class="foot helper">',
        f'<div class="foot helper"><b>Copia estática con datos al {_fdate(corte)}.</b> No se actualiza. '
        'El cálculo en vivo con el conector, el registro compartido y el ingreso de clientes al libro '
        'no están disponibles en esta copia.<br>', 1)
    title = re.search(r"<title>.*?</title>", html).group(0)
    html = html.replace(title, "", 1)
    doc = ('<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           + title.replace("</title>", f" · corte {_fdate(corte)}</title>") + '</head><body>\n'
           + html + "\n</body></html>\n")
    out = dist / "entregable" / f"Mesa-Central-corte-{corte[:10]}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    p = build()
    print(p, f"{p.stat().st_size / 1e6:.1f} MB")
