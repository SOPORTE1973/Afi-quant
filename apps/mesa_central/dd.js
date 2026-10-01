/* Mesa Central — Due diligence de TODOS los fondos del conector.
   Catálogo con screening (Vol II etapas 1-2) + dossier completo para el universo de construcción
   + riesgo y cartera calculados en vivo desde el conector MCP Afitrading para cualquier fondo. */
"use strict";
const MCP_SERVER = "MCP Afitrading";
const dds = { sel: null, q: "", clase: "", uni: "", liq: "", solo: false, sort: "nombre", dir: 1 };
const live = {};   // rut -> {riesgo, cartera, error}
let mcpApi; const mcpReady = (async () => { try { mcpApi = await window.claude?.use?.("mcp"); } catch (e) { mcpApi = null; } return mcpApi; })();

RENDER.dd = function () {
  const C = L.catalogo, rows = C.fondos, S = C.resumen;
  if (!dds.sel) { const m = rows.find(r => r.clave_modelo === app.fund); dds.sel = (m || rows.find(r => r.clave_modelo)).rut; }
  if (app.fund && rows.some(r => r.clave_modelo === app.fund) && app._ddFromLink) { dds.sel = rows.find(r => r.clave_modelo === app.fund).rut; app._ddFromLink = false; }
  const clases = [...new Set(rows.map(r => r.clase).filter(Boolean))].sort();
  const liqs = [...new Set(rows.map(r => r.liquidez || "Sin dato"))].sort();
  $("v-dd").innerHTML = `
    <div class="pagehead"><span class="lbl">Due diligence centralizado · ${esc(C.fuente)}</span><div class="row"><h1>Fondos</h1></div>
      <p class="muted" style="max-width:100ch">Cada fondo se evalúa una vez y lo heredan todos los clientes que lo tienen. Las carteras se construyen solo con el universo aprobado (hoy ${S.universo_construccion} fondos modelo); el resto está en cobertura: ficha, rentabilidades y señales, con riesgo y cartera calculados a pedido desde el conector.</p></div>
    <div class="kpis">${kpi("Fondos en el conector", S.fondos, `${S.referencias} referencias más (AFP y UF)`)}${kpi("Con rentabilidades", S.con_rentabilidad, "series en seguimiento")}${kpi("Universo de construcción", S.universo_construccion, "fondos modelo usados en carteras")}${kpi("Alternativos ilíquidos", S.alternativos, "requieren el Motor de Alternativos")}${kpi("Approved-Active", 0, "ningún fondo con decisión del Comité")}</div>
    <div class="tile"><div style="display:flex;flex-wrap:wrap;gap:8px 16px;align-items:end">
        <label style="display:grid;gap:4px"><span class="lbl">Buscar</span><input id="dd-q" class="sel" style="min-width:220px" placeholder="Nombre, administradora o RUT" value="${esc(dds.q)}"></label>
        <label style="display:grid;gap:4px"><span class="lbl">Clase</span><select id="dd-clase" class="sel"><option value="">Todas</option>${clases.map(c => `<option ${c === dds.clase ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
        <label style="display:grid;gap:4px"><span class="lbl">Universo</span><select id="dd-uni" class="sel"><option value="">Todos</option>${["construcción", "cobertura", "referencia"].map(u => `<option ${u === dds.uni ? "selected" : ""}>${u}</option>`).join("")}</select></label>
        <label style="display:grid;gap:4px"><span class="lbl">Liquidez</span><select id="dd-liq" class="sel"><option value="">Todas</option>${liqs.map(c => `<option ${c === dds.liq ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
        <label style="display:flex;gap:6px;align-items:center;height:40px"><input type="checkbox" id="dd-solo" ${dds.solo ? "checked" : ""}> Solo con señales</label>
        <span class="helper" id="dd-count" style="margin-left:auto"></span></div>
      <div class="tw" style="max-height:460px;overflow-y:auto"><table class="dt" id="dd-table"></table></div></div>
    <div id="dd-detail" class="view"></div>`;
  const rerender = () => { drawTable(); };
  $("dd-q").addEventListener("input", e => { dds.q = e.target.value; rerender(); });
  $("dd-clase").addEventListener("change", e => { dds.clase = e.target.value; rerender(); });
  $("dd-uni").addEventListener("change", e => { dds.uni = e.target.value; rerender(); });
  $("dd-liq").addEventListener("change", e => { dds.liq = e.target.value; rerender(); });
  $("dd-solo").addEventListener("change", e => { dds.solo = e.target.checked; rerender(); });
  drawTable(); drawDetail();
};
const COLS = [["nombre", "Fondo"], ["administradora", "Administradora"], ["clase", "Clase · subclase"], ["liquidez", "Liquidez"], ["anios", "Años"], ["y1", "1 año"], ["y3", "3 años (anual)"], ["inicio", "Desde inicio (anual)"], ["senales", "Señales"], ["universo", "Universo"]];
function sortVal(r, k) { return k === "nombre" ? (r.nombre_corto || r.nombre || "") : k === "anios" ? (r.anios_operacion ?? -1) : k === "y1" ? (r.rentabilidad.y1 ?? -9) : k === "y3" ? (r.rentabilidad.y3_anual ?? -9) : k === "inicio" ? (r.rentabilidad.inicio_anual ?? -9) : k === "senales" ? r.senales.length : k === "clase" ? `${r.clase || "~"} ${r.subclase || ""}` : (r[k] || "~"); }
function drawTable() {
  const q = dds.q.trim().toLowerCase();
  let rows = L.catalogo.fondos.filter(r => (!q || `${r.nombre} ${r.nombre_corto} ${r.administradora} ${r.rut}`.toLowerCase().includes(q))
    && (!dds.clase || r.clase === dds.clase) && (!dds.uni || r.universo === dds.uni) && (!dds.liq || (r.liquidez || "Sin dato") === dds.liq) && (!dds.solo || r.senales.length));
  rows = rows.slice().sort((a, b) => { const x = sortVal(a, dds.sort), y = sortVal(b, dds.sort); return (x > y ? 1 : x < y ? -1 : 0) * dds.dir; });
  $("dd-count").textContent = `${rows.length} de ${L.catalogo.fondos.length}`;
  const uniTag = u => u === "construcción" ? `<span class="tag info">construcción</span>` : u === "referencia" ? `<span class="tag">referencia</span>` : `<span class="tag">cobertura</span>`;
  $("dd-table").innerHTML = `<thead><tr>${COLS.map(([k, n]) => `<th><button class="link" data-sort="${k}" style="font-weight:600;color:var(--text);font-size:13px">${n}${dds.sort === k ? (dds.dir > 0 ? " ▲" : " ▼") : ""}</button></th>`).join("")}</tr></thead><tbody>${rows.map(r => `<tr data-rut="${esc(r.rut)}" style="cursor:pointer${r.rut === dds.sel ? ";background:var(--highlight)" : ""}" tabindex="0"><td class="tx"><b>${esc(r.nombre_corto || r.nombre)}</b>${r.en_cartera_de_clientes ? ' <span class="tag info">en clientes</span>' : ""}<br><span class="helper">RUT ${esc(r.rut)} · ${esc(r.tipo || "")}</span></td><td class="tx helper">${esc(r.administradora || "—")}</td><td class="tx">${esc(r.clase || "—")}<br><span class="helper">${esc(r.subclase || "sin subclase")}</span></td><td class="tx helper">${esc(r.liquidez || "sin dato")}</td><td class="n">${r.anios_operacion == null ? "—" : nf(r.anios_operacion, 1)}</td><td class="n${cls(r.rentabilidad.y1)}">${pct(r.rentabilidad.y1, 1)}</td><td class="n${cls(r.rentabilidad.y3_anual)}">${pct(r.rentabilidad.y3_anual, 1)}</td><td class="n${cls(r.rentabilidad.inicio_anual)}">${pct(r.rentabilidad.inicio_anual, 1)}</td><td>${r.referencia ? '<span class="helper">—</span>' : r.senales.length ? si("atencion", String(r.senales.length)) : si("ok", "0")}</td><td>${uniTag(r.universo)}</td></tr>`).join("") || `<tr><td colspan="${COLS.length}" class="muted">Ningún fondo calza con los filtros.</td></tr>`}</tbody>`;
  $("dd-table").querySelectorAll("[data-sort]").forEach(b => b.addEventListener("click", () => { dds.dir = dds.sort === b.dataset.sort ? -dds.dir : 1; dds.sort = b.dataset.sort; drawTable(); }));
  $("dd-table").querySelectorAll("tr[data-rut]").forEach(tr => { const pick = () => { dds.sel = tr.dataset.rut; drawTable(); drawDetail(); $("dd-detail").scrollIntoView({ block: "start", behavior: reduceMotion() ? "auto" : "smooth" }); }; tr.addEventListener("click", pick); tr.addEventListener("keydown", e => { if (e.key === "Enter") pick(); }); });
}
function drawDetail() {
  const r = L.catalogo.fondos.find(x => x.rut === dds.sel); const host = $("dd-detail"); if (!r) { host.innerHTML = ""; return; }
  if (r.clave_modelo) { app.fund = r.clave_modelo; store.set("fund", app.fund); host.innerHTML = `<div class="notif"><span>${si("info", "Universo de construcción")}</span><span>Fondo modelo con IDD cuantitativa completa, cartera IFRS y look-through precalculados.</span></div><div id="dd-model"></div>`; renderModelDossier($("dd-model")); return; }
  const s = r.serie, rt = r.rentabilidad;
  host.innerHTML = `
    <div class="tile"><div class="th"><div><span class="lbl">RUT ${esc(r.rut)} · ${esc(r.tipo || "")} · ${esc(r.vigencia || "")}</span><h2>${esc(r.nombre)}</h2></div><div style="display:flex;gap:12px;flex-wrap:wrap">${r.referencia ? si("info", r.referencia) : si("sin_datos", "Approved List: " + r.estado)}${r.senales.length ? si("atencion", `${r.senales.length} señal${r.senales.length > 1 ? "es" : ""}`) : ""}</div></div>
      <div class="notif ${r.referencia ? "" : "warn"}"><span>${si(r.referencia ? "info" : "sin_datos", r.referencia ? "Referencia" : "Cobertura")}</span><span>${r.referencia ? "Se usa como referencia de comparación (sujeta al Benchmark Eligibility Framework), no como vehículo de inversión." : `No está en el universo de construcción: para entrar necesita IDD cualitativa, ODD, decisión del Comité (Approved-Active) y CMAs para su subclase (${esc(r.subclase || "sin subclase")}). Etapa actual: ${esc(r.etapa)}.`}</span></div></div>
    <div class="g2">
      <div class="tile"><h3>Ficha</h3><dl class="kv">${[["Administradora", r.administradora || "—"], ["Clase y subclase (taxonomía AFI)", `${r.clase || "sin clase"} · ${r.subclase || "sin subclase"}`], ["Tipo", r.tipo || "—"], ["Inversionista", r.inversionista || "—"], ["Liquidez de rescate", r.liquidez || "sin dato"], ["Inicio de operaciones", fdate(r.inicio_operaciones)], ["Series", r.series.join(", ") || "—"]].map(([a, b]) => `<dt>${a}</dt><dd>${esc(b)}</dd>`).join("")}</dl></div>
      <div class="tile"><h3>Rentabilidades (resumen del conector)</h3>${s ? `<dl class="kv">${[["Serie analizada", `${s.serie} (${s.nemo || ""}) · desde ${fdate(s.desde)}`], ["Último valor cuota", `${nf(s.valor_cuota, 2)} al ${fdate(s.hasta)}`], ["Año a la fecha", pct(rt.ytd, 1)], ["1 año", pct(rt.y1, 1)], ["3 años (anualizado)", pct(rt.y3_anual, 1)], ["Desde el inicio (anualizado)", pct(rt.inicio_anual, 1)]].map(([a, b]) => `<dt>${a}</dt><dd class="num">${esc(b)}</dd>`).join("")}</dl><p class="helper">${esc(L.catalogo.nota)} Se toma la serie con más historia.</p>` : `<div class="notif warn"><span>${si("sin_datos", "Sin datos")}</span><span>El conector no tiene una serie con rentabilidad en seguimiento para este fondo.</span></div>`}</div>
    </div>
    ${r.senales.length ? `<div class="tile"><h3>Señales de screening</h3>${r.senales.map(x => `<div class="sig"><b>${esc(x.tipo)}</b><span>${esc(x.senal)}</span></div>`).join("")}</div>` : ""}
    ${s && !r.referencia ? `<div class="tile" id="dd-live"></div>` : ""}
    ${r.referencia ? "" : `<div class="g2"><div class="tile"><h3>Pilares cualitativos</h3><div class="chk">${["People", "Philosophy", "Process", "Parent", "Price"].map(p => `${si("sin_datos", "Pendiente")}<span><b>${p}</b></span>`).join("")}</div><p class="helper">Requieren DDQ y reuniones; no se infieren de la rentabilidad (Vol. II, principio 4).</p></div><div class="tile"><h3>Revisión operacional (ODD)</h3><div class="notif err"><span>${si("alerta", "Veto")}</span><span>Sin ODD aprobada el fondo no es elegible, con independencia de su rentabilidad (ESFS 10.6).</span></div></div></div>`}`;
  if (s && !r.referencia) drawLive(r);
}

/* ---------- Cálculo en vivo con el conector ---------- */
function mcpMessage(e) {
  const c = e && e.code;
  return c === "needs_reauth" ? `Reconecta ${MCP_SERVER} en claude.ai → Configuración → Conectores.`
    : c === "server_not_connected" ? `Agrega el conector ${MCP_SERVER} en claude.ai → Configuración → Conectores.`
    : c === "selection_required" ? `Hay más de un conector ${MCP_SERVER}: elige uno en el aviso de claude.ai.`
    : c === "not_in_manifest" ? "No diste permiso a esta página para usar el conector. Puedes habilitarlo desde el menú de permisos de la página."
    : c === "blocked_by_policy" || c === "approval_required" ? "La política de tu organización no permite esta consulta desde la página."
    : c === "tool_error" ? `El conector respondió con un error: ${e.message}`
    : c === "server_unavailable" ? "El conector no respondió. Intenta de nuevo en unos segundos."
    : `No se pudo consultar el conector (${c || "error"}).`;
}
async function callMcp(tool, input) {
  try { return (await mcpApi.callTool(MCP_SERVER, tool, input, { cache: { staleTime: 300000, gcTime: 86400000 } })).payload; }
  catch (e) { if (e && e.retryable) { await new Promise(r => setTimeout(r, (e.retryAfterMs || 1500) + Math.random() * 500)); return (await mcpApi.callTool(MCP_SERVER, tool, input, { cache: { staleTime: 300000, gcTime: 86400000 } })).payload; } throw e; }
}
function monthEnds(points) { const out = []; for (let i = 0; i < points.length; i++) if (i === points.length - 1 || points[i].fecha.slice(0, 7) !== points[i + 1].fecha.slice(0, 7)) out.push(points[i]); return out; }
function riskFromNav(data) {
  // Mismas reglas que el motor (QM IV-V): retornos mensuales de fin de mes, volatilidad 36m anualizada, caída sobre 3 años.
  const pts = data.filter(p => p.nav_ajustado != null).map(p => ({ fecha: p.fecha, v: +p.nav_ajustado }));
  const me = monthEnds(pts), rets = me.slice(1).map((p, i) => p.v / me[i].v - 1), out = { meses: rets.length, desde: pts[0]?.fecha, hasta: pts[pts.length - 1]?.fecha, puntos: pts };
  const chain = a => a.reduce((x, r) => x * (1 + r), 1) - 1;
  [["r1", 12], ["r3", 36], ["r5", 60]].forEach(([k, n]) => { if (rets.length >= n) out[k] = Math.pow(1 + chain(rets.slice(-n)), 12 / n) - 1; });
  if (rets.length >= 36) { const w = rets.slice(-36), m = w.reduce((a, b) => a + b, 0) / 36; out.vol3 = Math.sqrt(w.reduce((a, b) => a + (b - m) ** 2, 0) / 35) * Math.sqrt(12);
    let peak = me[me.length - 37].v, dd = 0; me.slice(-37).forEach(p => { peak = Math.max(peak, p.v); dd = Math.min(dd, p.v / peak - 1); }); out.dd3 = dd; }
  return out;
}
function cartSignals(payload, params) {
  const res = payload?.data?.resumen; if (!res) return null;
  const may = res.mayores || [], top5 = may.slice(0, 5).reduce((a, x) => a + (x.pct_fondo || 0), 0), top1 = may[0];
  const sig = [];
  if (params.dd_top5_max_pct != null && top5 > params.dd_top5_max_pct) sig.push(`Las 5 mayores posiciones suman ${nf(top5, 0)}% (umbral ${params.dd_top5_max_pct}%)`);
  if (top1 && params.dd_single_position_max_pct != null && top1.pct_fondo > params.dd_single_position_max_pct) sig.push(`${top1.emisor || top1.etiqueta}: ${nf(top1.pct_fondo, 1)}% del fondo`);
  return { periodo: payload.data.cierre?.periodo, n: res.n_posiciones, top5, mayores: may.slice(0, 8), categorias: res.por_categoria || [], senales: sig };
}
async function drawLive(r) {
  const box = $("dd-live"); if (!box) return;
  const st = live[r.rut] || {};
  await mcpReady;
  const title = `<div><span class="lbl">En vivo · conector ${MCP_SERVER}</span><h3>Riesgo y cartera informada</h3></div>`;
  if (!mcpApi) { box.innerHTML = `<div class="th">${title}</div><div class="notif"><span>${si("sin_datos", "No disponible aquí")}</span><span>El cálculo en vivo funciona al abrir la Mesa Central en claude.ai con el conector ${MCP_SERVER} conectado. Usa la serie ${esc(r.serie.serie)} y la cartera IFRS del fondo.</span></div>`; return; }
  const head = `<div class="th">${title}<button class="btn primary sm" id="dd-run">${st.riesgo ? "Actualizar" : "Calcular con el conector"}</button></div>`;
  const p = L.parametros;
  let body = "";
  if (st.loading) body = `<p class="muted">Consultando el conector…</p>`;
  else if (st.error) body = `<div class="notif err"><span>${si("alerta", "Sin datos")}</span><span>${esc(st.error)}</span></div>`;
  else if (!st.riesgo) body = `<p class="muted">Trae la serie diaria (5 años) y la última cartera informada a la CMF, y calcula volatilidad, caída máxima, rentabilidades anualizadas y concentración con las reglas del motor. Se consulta solo este fondo.</p>`;
  if (st.riesgo) { const k = st.riesgo;
    body += `<div class="kpis">${kpi("Retorno 1 año", pct(k.r1, 1), "valor cuota ajustado")}${kpi("Retorno 3 años (anual)", pct(k.r3, 1), "")}${kpi("Retorno 5 años (anual)", pct(k.r5, 1), "")}${kpi("Volatilidad 3 años", k.vol3 == null ? "insuficiente" : pct(k.vol3, 1), k.vol3 == null ? `${k.meses} meses; mínimo 36 (QM V)` : "mensual anualizada")}${kpi("Caída máxima 3 años", k.dd3 == null ? "insuficiente" : pct(k.dd3, 1), "sobre cierres de mes")}</div><div class="chart" id="dd-live-chart"></div><p class="helper">Serie ${esc(r.serie.serie)} desde ${fdate(k.desde)} hasta ${fdate(k.hasta)}.${r.liquidez && r.liquidez.startsWith("No Rescatable") ? " Fondo no rescatable: su valor cuota no es precio de mercado diario y la volatilidad subestima el riesgo (QM X)." : ""}</p>`; }
  if (st.cartera) { const c = st.cartera;
    body += `<h4 style="margin-top:12px">Cartera informada (IFRS ${esc(c.periodo || "")}) · ${nf(c.n)} posiciones · 5 mayores ${nf(c.top5, 0)}%</h4><div class="bars">${c.mayores.map(x => `<div class="brow" style="grid-template-columns:240px minmax(0,1fr) 60px"><span>${esc(x.emisor || x.etiqueta)}</span><div class="track"><i style="left:0;width:${Math.min(100, x.pct_fondo).toFixed(1)}%;background:var(--interactive)"></i></div><span class="num">${nf(x.pct_fondo, 1)}%</span></div>`).join("")}</div>${c.senales.length ? c.senales.map(s => `<div class="sig"><b>Concentración</b><span>${esc(s)}</span></div>`).join("") : '<p class="helper">Sin señales de concentración con los umbrales vigentes.</p>'}`; }
  else if (st.riesgo && st.carteraError) body += `<p class="helper">Cartera: ${esc(st.carteraError)}</p>`;
  box.innerHTML = head + body;
  $("dd-run").addEventListener("click", async () => {
    live[r.rut] = { loading: true }; drawLive(r);
    const desde = new Date(L.as_of); desde.setFullYear(desde.getFullYear() - 5);
    try {
      const nav = await callMcp("nav_ajustado", { rut: r.rut, serie: r.serie.serie, desde: desde.toISOString().slice(0, 10) });
      const riesgo = riskFromNav((nav && nav.data) || []);
      let cartera = null, carteraError = null;
      try { let cp = await callMcp("cartera", { rut: r.rut, limite: 10 }); if (!cp?.data?.cierre) cp = await callMcp("cartera", { rut: r.rut, limite: 10, ambito: "ext" }); cartera = cartSignals(cp, p); if (!cartera) carteraError = "el fondo no informa cartera en el conector"; }
      catch (e) { carteraError = mcpMessage(e); }
      live[r.rut] = { riesgo, cartera, carteraError };
    } catch (e) { live[r.rut] = { error: mcpMessage(e) }; }
    if (dds.sel === r.rut) drawLive(r);
  });
  if (st.riesgo && $("dd-live-chart")) { const pts = st.riesgo.puntos.filter((_, i, a) => i % Math.max(1, Math.floor(a.length / 300)) === 0 || i === a.length - 1); const hst = $("dd-live-chart");
    const W = Math.max(320, hst.clientWidth || 700), H = 170, m = { l: 44, r: 10, t: 8, b: 20 }, b0 = pts[0].v, vals = pts.map(p => p.v / b0 * 100), lo = Math.min(...vals), hi = Math.max(...vals);
    const x = i => m.l + i / (pts.length - 1) * (W - m.l - m.r), y = v => m.t + (1 - (v - lo) / (hi - lo || 1)) * (H - m.t - m.b);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Valor cuota base 100" }, hst);
    [lo, (lo + hi) / 2, hi].forEach(v => { el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: css("--border") }, svg); txt(svg, m.l - 6, y(v) + 4, nf(v, 0), { "text-anchor": "end" }); });
    el("path", { d: vals.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(""), fill: "none", stroke: css("--interactive"), "stroke-width": 2 }, svg);
    txt(svg, m.l, H - 4, fdate(pts[0].fecha)); txt(svg, W - m.r, H - 4, fdate(pts[pts.length - 1].fecha), { "text-anchor": "end" }); }
}
