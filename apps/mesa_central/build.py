"""Arma la Mesa Central en dist/: corre el libro, exporta los datos y copia la aplicación.

    python apps/mesa_central/build.py            # datos + aplicación
    python apps/mesa_central/build.py --solo-app # solo la aplicación (datos ya generados)

Cada script se copia con una huella de su contenido en el nombre (app.<hash>.js) y
index.html se reescribe para apuntar a esos nombres: un navegador nunca ejecuta una
versión vieja guardada en caché junto con un HTML nuevo.

dist/ queda listo para servirse como sitio estático. Para publicarlo como artifact de
claude.ai, index.html va sin <!doctype>: el servicio agrega el esqueleto.
"""
import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ("app.js", "client.js", "crisis.js", "cartera.js", "pres.js")


def stage_app(out: Path) -> dict[str, str]:
    """Copia index.html y los scripts con nombre versionado. Devuelve {nombre: nombre_versionado}."""
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.js"):
        old.unlink()
    html = (HERE / "index.html").read_text(encoding="utf-8")
    names = {}
    for f in SCRIPTS:
        body = (HERE / f).read_bytes()
        name = f"{f[:-3]}.{hashlib.sha256(body).hexdigest()[:8]}.js"
        (out / name).write_bytes(body)
        names[f] = name
        html, n = re.subn(rf'<script src="{re.escape(f)}"></script>', f'<script src="{name}"></script>', html)
        assert n == 1, f"index.html no referencia {f}"
    (out / "index.html").write_text(html, encoding="utf-8")
    return names


if __name__ == "__main__":
    DIST = HERE / "dist"
    if "--solo-app" not in sys.argv:
        sys.path.insert(0, str(HERE))
        from build_data import main as build_data  # noqa: E402
        build_data(str(DIST / "data"))
    print(stage_app(DIST))
