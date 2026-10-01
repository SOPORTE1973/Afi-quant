"""Arma la Mesa Central: corre el libro, exporta los datos y los inserta en la plantilla.

    python apps/mesa_central/build.py   ->   apps/mesa_central/dist/mesa-central.html
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
DIST.mkdir(exist_ok=True)
data = DIST / "platform_data.json"
subprocess.run([sys.executable, str(HERE / "build_data.py"), str(data)], check=True)
html = (HERE / "template.html").read_text(encoding="utf-8").replace("__DATA__", data.read_text(encoding="utf-8"))
(DIST / "mesa-central.html").write_text(html, encoding="utf-8")
print(DIST / "mesa-central.html")
