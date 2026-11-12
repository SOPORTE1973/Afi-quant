@echo off
rem Abre la Mesa Central con el motor Python (plataforma local).
cd /d "%~dp0..\.."
if not exist ".venv\Scripts\python.exe" (
  echo No se encontro el entorno .venv en %cd%. Crealo con: python -m venv .venv ^&^& .venv\Scripts\pip install -e .
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "apps\mesa_central\plataforma.py"
pause
