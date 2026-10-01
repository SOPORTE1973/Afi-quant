"""Arma la Mesa Central en dist/: corre el libro, exporta los datos y copia la aplicación.

    python apps/mesa_central/build.py

dist/ queda listo para servirse como sitio estático (index.html + app.js + client.js +
pres.js + data/). Para publicarlo como artifact de claude.ai, index.html va sin
<!doctype>: el servicio agrega el esqueleto.
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_data import main as build_data  # noqa: E402

DIST = HERE / "dist"
DIST.mkdir(exist_ok=True)
build_data(str(DIST / "data"))
for f in ("index.html", "app.js", "client.js", "pres.js"):
    shutil.copy(HERE / f, DIST / f)
print(DIST)
