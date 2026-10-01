# Mesa Central

Aplicación del motor centralizado, con diseño basado en Carbon Design System (IBM):

- **Libro**: monitoreo de las cuentas en seis dimensiones, sin puntaje por cliente (DF 2.1).
- **Clientes**: espacio de trabajo por cliente con nueve pestañas: resumen, gráfico tipo TradingView con las decisiones como noticias, construcción (Ledoit-Wolf, frontera, alternativas), cartera, riesgo y stress (incluye reverse stress), benchmark y tracking error, flujos, decisiones con trade-offs y datos y supuestos.
- **Due diligence** por fondo (M10), compartido por todos los clientes que lo tienen.
- **Presentaciones** para clientes: selección de láminas, liberación por el asesor y PPTX.

```bash
python apps/mesa_central/build.py
python -m http.server -d apps/mesa_central/dist 8000
```

Los datos de cada cliente se cargan al abrirlo (`data/clientes/<id>.json`). Publicada como artifact de claude.ai con `db` (registro de liberaciones), `user` y `downloads`; fuera de claude.ai funciona sin registro ni descarga.
