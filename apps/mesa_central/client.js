/* Mesa Central — espacio de trabajo del cliente: nueve pestañas generalizadas para cualquier cliente. */
"use strict";
const CTABS = [["resumen", "Resumen"], ["grafico", "Gráfico"], ["construccion", "Construcción"], ["cartera", "Cartera"],
  ["riesgo", "Riesgo y stress"], ["benchmark", "Benchmark"], ["flujos", "Flujos"], ["decisiones", "Decisiones"], ["datos", "Datos y supuestos"]];
const cv = { tab: store.get("ctab", "resumen"), C: null, charts: {} };
const GC = ["--g1", "--g2", "--g3", "--c4", "--c5"];
let GOALS = [], gname = {}, gcol = {};
const CAT_STYLE = {
  "Onboarding": { c: "--info", l: "O", shape: "circle" }, "Rebalanceo": { c: "--warn", l: "R", shape: "arrowDown" },
  "Glide path": { c: "--warn", l: "G", shape: "arrowDown" }, "Revisión anual": { c: "--info", l: "A", shape: "circle" },
  "Meta cumplida": { c: "--ok", l: "M", shape: "arrowUp" }, "Meta con déficit": { c: "--err", l: "M", shape: "arrowDown" },
  "Alerta": { c: "--err", l: "!", shape: "arrowDown" }, "Cierre": { c: "--info", l: "C", shape: "circle" }, "Sin operar": { c: "--idle", l: "·", shape: "circle" } };
const kpi = (l, v, n, c = "") => `<div class="kpi"><span class="lbl">${l}</span><span class="v sm${c}">${v}</span><span class="helper">${esc(n)}</span></div>`;
function killCharts() { Object.values(cv.charts).forEach(ch => { try { ch.remove(); } catch (e) {} }); cv.charts = {}; }
const hasLW = () => typeof LightweightCharts !== "undefined";
function baseChart(host, extra = {}) {
  const LW = LightweightCharts;
  return LW.createChart(host, Object.assign({ autoSize: true,
    layout: { background: { type: "solid", color: css("--layer") }, textColor: css("--text-2"), fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
      panes: { separatorColor: css("--border"), separatorHoverColor: css("--highlight"), enableResize: true } },
    grid: { vertLines: { color: css("--border") }, horzLines: { color: css("--border") } },
    rightPriceScale: { borderColor: css("--border") }, timeScale: { borderColor: css("--border"), rightOffset: 4, fixLeftEdge: true },
    crosshair: { mode: LW.CrosshairMode.Normal }, localization: { locale: "es-CL", dateFormat: "dd MMM yyyy" } }, extra));
}
const fmtM = { type: "custom", formatter: v => nf(v / 1e6, 1) + "M", minMove: 1e4 };
const fmtP = { type: "custom", formatter: v => nf(v, 1) + "%", minMove: 0.01 };
const timeStr = t => typeof t === "string" ? t : (t && t.year ? `${t.year}-${String(t.month).padStart(2, "0")}-${String(t.day).padStart(2, "0")}` : null);

RENDER.cliente = async function (opts = {}) {
  if (opts.tab) cv.tab = opts.tab;
  const host = $("v-cliente");
  const M = L.monitoreo;
  const pick = `<div class="cpick" role="group" aria-label="Clientes">${M.map(a => `<button data-c="${a.id}" aria-pressed="${a.id === app.client}"><span class="helper num">${a.id} · ${esc(a.asesor)}</span><span>${esc(L.clientes[a.id].nombre)}</span><span class="helper">${esc(a.perfil)} · ${mm(a.valor)}</span></button>`).join("")}</div>`;
  if (!cv.C || cv.C.id !== app.client) { host.innerHTML = pick + `<div class="loading">Cargando ${esc(app.client)}…</div>`; bindPick(); }
  try { cv.C = await loadClient(app.client); } catch (e) { host.innerHTML = pick + `<div class="notif err"><span>${si("alerta", "Error")}</span><span>${esc(e.message)}</span></div>`; bindPick(); return; }
  const C = cv.C;
  GOALS = C.cliente.metas.map(g => g.key); gname = {}; gcol = {};
  C.cliente.metas.forEach((g, i) => { gname[g.key] = g.nombre; gcol[g.key] = GC[i % GC.length]; });
  killCharts();
  host.innerHTML = pick + `
    <div class="pagehead"><span class="lbl">${C.id} · ${esc(C.asesor)} · IPS ${esc(C.ips.id)}</span><div class="row"><h1>${esc(C.cliente.nombre)}</h1>
      <div class="meta"><span>${C.cliente.edad} años · perfil <b>${esc(C.cliente.perfil)}</b></span><span>Onboarding <b>${fdate(C.onboarding)}</b></span><span>Datos al <b>${fdate(C.resumen.fecha)}</b></span><span><b>${C.n_casos}</b> Decision Cases</span></div></div></div>
    <div class="tabs" role="tablist">${CTABS.map(([k, n]) => `<button role="tab" data-t="${k}" aria-selected="${k === cv.tab}">${n}</button>`).join("")}</div>
    <div id="ctab" class="view"></div>`;
  bindPick();
  host.querySelectorAll("[data-t]").forEach(b => b.addEventListener("click", () => { cv.tab = b.dataset.t; store.set("ctab", cv.tab); host.querySelectorAll("[data-t]").forEach(x => x.setAttribute("aria-selected", String(x === b))); renderCTab(); }));
  renderCTab();
};
function bindPick() { document.querySelectorAll("#v-cliente .cpick button").forEach(b => b.addEventListener("click", () => { app.client = b.dataset.c; store.set("client", app.client); document.querySelectorAll("#snav [data-client]").forEach(x => x.setAttribute("aria-current", x.dataset.client === app.client ? "page" : "false")); RENDER.cliente(); })); }
function renderCTab() { killCharts(); const h = $("ctab"); h.innerHTML = ""; try { CT[cv.tab](h, cv.C); } catch (e) { console.error(e); h.innerHTML = `<div class="notif err"><span>${si("alerta", "Error")}</span><span>${esc(e.message)}</span></div>`; } }
const CT = {};

/* ---------- Resumen ---------- */
CT.resumen = function (h, C) {
  const S = C.resumen, F = C.flujos, rl = retLabel(S);
  const live = C.cliente.metas.filter(g => !g.cerrada && g.fecha && C.metas_cierre[g.key]);
  const worst = live.slice().sort((a, b) => (C.metas_cierre[a.key].prob_exito - (a.prob_deseada || 0)) - (C.metas_cierre[b.key].prob_exito - (b.prob_deseada || 0)))[0];
  const st = C.stress.hipoteticos.stress, inv = C.stress.inverso;
  const dims = C.monitoreo.dimensiones;
  h.innerHTML = `
    <div class="kpis">${kpi("Valor de la cartera", mm(S.valor_final), `aportado ${mm(S.aportado)} · retirado ${mm(S.retirado)}`)}${kpi("Ganancia acumulada", smm(F.ganancia_neta), "valor − aportes + retiros", F.ganancia_neta >= 0 ? " pos" : " neg")}${kpi(rl.l, rl.v, rl.n)}${worst ? kpi(`Probabilidad: ${worst.nombre}`, pct(C.metas_cierre[worst.key].prob_exito, 0), worst.prob_deseada != null ? `deseada ${pct(worst.prob_deseada, 0)}` : "sin probabilidad deseada en el IPS") : kpi("Retorno personal (XIRR)", pct(S.xirr, 1), "con el momento de sus aportes")}</div>
    <div class="tile"><h3>Estado de la cuenta</h3><div class="dims">${Object.entries(dims).map(([d, x]) => `<div class="dim">${si(x.estado, L.dimensiones[d] + " · " + ST_LABEL[x.estado])}<span>${esc(x.resumen)}</span><span class="helper">${esc(x.evidencia.slice(0, 3).join(" · "))}</span></div>`).join("")}</div></div>
    <div class="g2">
      <div class="tile"><div class="th"><h3>Aportado frente al valor</h3><button class="link" data-goto-tab="grafico">Abrir en el gráfico</button></div><div class="legend"><span><i style="--c:var(--interactive)"></i>Valor</span><span><i class="line"></i>Aportes netos</span></div><div id="mini" style="height:240px"></div></div>
      <div class="tile"><h3>Metas</h3><div id="goals"></div></div>
    </div>
    <div class="tile"><h3>Lo que conviene mirar</h3><div class="g3" id="ins"></div></div>
    <div class="tile"><div class="th"><h3>Últimas decisiones</h3><button class="link" data-goto-tab="decisiones">Ver todas</button></div><div id="lastn"></div></div>`;
  $("goals").innerHTML = C.cliente.metas.map(g => {
    const m = C.metas_cierre[g.key];
    if (g.cerrada) return `<div class="goalrow"><div class="th" style="display:flex;justify-content:space-between"><b>${esc(g.nombre)}</b>${si("ok", "Cumplida")}</div><span class="helper">${mm(g.objetivo)} al ${fdate(g.fecha)}</span></div>`;
    if (!m) return "";
    if (m.tipo === "reserva") return `<div class="goalrow"><div style="display:flex;justify-content:space-between;gap:8px"><b>${esc(g.nombre)}</b>${si(m.cobertura >= 1 ? "ok" : "alerta", "Cobertura " + pct(m.cobertura, 0))}</div><div class="prog"><i style="width:${Math.min(100, m.cobertura * 100).toFixed(0)}%;background:var(--ok)"></i></div><span class="helper">Reserva de ${mm(g.objetivo)}</span></div>`;
    const below = g.prob_deseada != null && m.prob_exito < g.prob_deseada;
    return `<div class="goalrow"><div style="display:flex;justify-content:space-between;gap:8px"><b>${esc(g.nombre)}</b>${si(g.prob_deseada == null ? "sin_datos" : below ? "alerta" : "ok", `${pct(m.prob_exito, 0)}${g.prob_deseada != null ? " · deseada " + pct(g.prob_deseada, 0) : ""}`)}</div>
      <div class="prog"><i style="width:${(m.prob_exito * 100).toFixed(0)}%"></i>${g.prob_deseada != null ? `<b style="left:${(g.prob_deseada * 100).toFixed(0)}%"></b>` : ""}</div>
      <span class="helper">${mm(g.objetivo)} al ${fdate(g.fecha)} · hoy ${mm(C.resumen.valor_por_meta[g.key])} · mediana proyectada ${mm(m.p50)}</span></div>`; }).join("");
  const ins = [];
  if (worst && worst.prob_deseada != null && C.metas_cierre[worst.key].prob_exito < worst.prob_deseada) ins.push({ st: "--err", t: `${worst.nombre} bajo lo deseado`, b: `Probabilidad ${pct(C.metas_cierre[worst.key].prob_exito, 0)} frente a ${pct(worst.prob_deseada, 0)} pedida en el IPS. Las palancas son aporte, plazo, monto o riesgo: decide el WM con el cliente.`, go: "riesgo" });
  if (inv && inv.escenario_stress_escalado && inv.escenario_stress_escalado.multiplicador < 1) ins.push({ st: "--err", t: "El escenario Stress rompe el límite del IPS", b: `Perdería ${pct(inv.escenario_stress_escalado.perdida_escenario, 1)} frente a ${pct(inv.limite, 0)} tolerado: basta el ${nf(inv.escenario_stress_escalado.multiplicador * 100, 0)}% de ese escenario.`, go: "riesgo" });
  else if (inv && inv.no_calculado) ins.push({ st: "--idle", t: "Reverse stress sin calcular", b: inv.no_calculado, go: "riesgo" });
  if (dims.concentracion.estado === "alerta") ins.push({ st: "--err", t: "Concentración por administradora", b: dims.concentracion.resumen + ".", go: "cartera" });
  if ((S.pesos_actuales.DP || 0) > 0.2) ins.push({ st: "--warn", t: "Concentración escondida en deuda privada", b: `Facturas pesa ${pct(S.pesos_actuales.DP, 0)} y es 99,98% una cuota de un fondo privado: su valor cuota no es precio de mercado y su volatilidad subestima el riesgo.`, go: "datos" });
  ins.push({ st: "--info", t: "El riesgo diario es mayor que el mensual", b: `Máxima caída con datos diarios ${pct(C.max_dd_diario, 1)}; con cierres de mes ${pct(S.max_drawdown, 1)}.`, go: "grafico" });
  const miss = C.catalogo.filter(r => r.estado === "missing_critical");
  if (miss.length) ins.push({ st: "--idle", t: `Faltan ${miss.length} datos críticos`, b: miss.map(r => r.variable).join("; ") + ".", go: "datos" });
  $("ins").innerHTML = ins.map(x => `<div class="tile insight" style="--st:var(${x.st});background:var(--layer-2)"><h4>${esc(x.t)}</h4><p class="muted">${esc(x.b)}</p><button class="link" data-goto-tab="${x.go}">Ver detalle</button></div>`).join("");
  $("lastn").innerHTML = C.noticias.filter(n => !n.quiet).slice(-4).reverse().map(n => { const s = CAT_STYLE[n.categoria] || CAT_STYLE.Cierre; return `<div style="display:grid;grid-template-columns:auto 1fr;gap:12px;padding:8px 0;border-top:1px solid var(--border)"><span class="nb" style="--bc:var(${s.c})">${n.n}</span><div><span class="helper num">${fdate(n.fecha)} · ${esc(n.categoria)}</span><div><b>${esc(n.titulo)}</b></div><span class="helper">${esc(n.resumen)}</span></div></div>`; }).join("");
  if (hasLW()) { const ch = baseChart($("mini"), { handleScroll: false, handleScale: false }); const LW = LightweightCharts;
    const a = ch.addSeries(LW.AreaSeries, { lineColor: css("--interactive"), topColor: alpha(css("--interactive"), .3), bottomColor: alpha(css("--interactive"), .02), lineWidth: 2, priceFormat: fmtM, priceLineVisible: false });
    a.setData(C.ts.fechas.map((t, i) => ({ time: t, value: C.ts.valor[i] })));
    ch.addSeries(LW.LineSeries, { color: css("--text-2"), lineWidth: 2, lineStyle: 2, lineType: 1, priceFormat: fmtM, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false }).setData(C.ts.fechas.map((t, i) => ({ time: t, value: C.ts.neto[i] })));
    ch.timeScale().fitContent(); cv.charts.mini = ch; }
};
document.addEventListener("click", e => { const g = e.target.closest("[data-goto-tab]"); if (g && app.view === "cliente") { cv.tab = g.dataset.gotoTab; store.set("ctab", cv.tab); document.querySelectorAll("#v-cliente [data-t]").forEach(x => x.setAttribute("aria-selected", String(x.dataset.t === cv.tab))); renderCTab(); if (g.dataset.news) setTimeout(() => focusNews(g.dataset.news, true), 50); } });

/* ---------- Gráfico (terminal) ---------- */
const tvs = { mode: "valor", view: "veh", layers: { bench: true, net: true, dd: false, flow: false }, range: "all", focus: "RVL", newsFilter: "all", active: null };
let tv = null, tvPrimary = null, tvMarkers = null, idxOf = {};
CT.grafico = function (h, C) {
  idxOf = Object.fromEntries(C.ts.fechas.map((d, i) => [d, i]));
  const seg = (id, items, key, multi) => `<div class="seg" id="${id}">${items.map(([v, n]) => `<button data-v="${v}" aria-pressed="${multi ? !!tvs.layers[v] : tvs[key] === v}">${n}</button>`).join("")}</div>`;
  h.innerHTML = `<div class="term"><div style="min-width:0">
    <div class="tbar"><div class="grp"><span class="lbl">Modo</span>${seg("s-mode", [["valor", "Valor CLP"], ["rent", "Rentabilidad"], ["comp", "Comparar"]], "mode")}</div>
      <div class="grp"><span class="lbl">Vista</span>${seg("s-view", [["total", "Total"], ["veh", "Por fondo"], ["meta", "Por meta"], ["sep", "Separado"]], "view")}</div>
      <div class="grp"><span class="lbl">Capas</span>${seg("s-lay", [["bench", "Benchmark"], ["net", "Aportes"], ["dd", "Drawdown"], ["flow", "Flujos"]], null, true)}</div>
      <div class="grp"><span class="lbl">Rango</span>${seg("s-range", [["3", "3M"], ["6", "6M"], ["12", "1A"], ["all", "Todo"]], "range")}</div></div>
    <div style="position:relative"><div class="tvleg" id="tvleg"></div><div id="tv"></div></div>
    <div class="chips" id="chips" hidden></div></div>
    <aside class="news" aria-label="Decisiones como noticias"><div class="nh"><h4>Decisiones</h4>${seg("s-news", [["all", "Todas"], ["act", "Con operación"]], "newsFilter")}</div><div class="nlist" id="nlist"></div><div class="helper" style="padding:8px 16px;border-top:1px solid var(--border)">Clic en un marcador o en una noticia para sincronizarlos.</div></aside></div>
    <div class="legend">${Object.entries(CAT_STYLE).filter(([k]) => C.noticias.some(n => n.categoria === k)).map(([k, s]) => `<span><span class="nb" style="--bc:var(${s.c})">${s.l}</span>${k}</span>`).join("")}</div>`;
  const bind = (id, key) => document.querySelectorAll(`#${id} button`).forEach(b => b.addEventListener("click", () => {
    if (b.disabled) return;
    if (key === "layers") { tvs.layers[b.dataset.v] = !tvs.layers[b.dataset.v]; b.setAttribute("aria-pressed", String(tvs.layers[b.dataset.v])); }
    else { tvs[key] = b.dataset.v; document.querySelectorAll(`#${id} button`).forEach(x => x.setAttribute("aria-pressed", String(x === b))); }
    if (key === "range") return applyRange(C);
    if (key === "newsFilter") { renderNews(C); if (tvMarkers) tvMarkers.setMarkers(markersFor(C)); return; }
    buildTv(C);
  }));
  bind("s-mode", "mode"); bind("s-view", "view"); bind("s-lay", "layers"); bind("s-range", "range"); bind("s-news", "newsFilter");
  const compLabel = { ...VNAME, IPSA: "IPSA (índice)", AFP: "AFP Fondo C" };
  $("chips").innerHTML = `<span class="lbl" style="align-self:center">Destacar</span>` + Object.keys(C.ts.norm).map(k => `<button class="chip" data-k="${k}" aria-pressed="${k === tvs.focus}" style="--c:${VCOL[k] ? `var(${VCOL[k]})` : "var(--text)"}"><i></i>${k} · ${esc(compLabel[k] || k)}</button>`).join("");
  document.querySelectorAll("#chips .chip").forEach(b => b.addEventListener("click", () => { tvs.focus = b.dataset.k; document.querySelectorAll("#chips .chip").forEach(c => c.setAttribute("aria-pressed", String(c.dataset.k === tvs.focus))); buildTv(C); }));
  buildTv(C); renderNews(C);
};
function markersFor(C) { return C.noticias.filter(n => (tvs.newsFilter === "all" || !n.quiet) && idxOf[n.fecha] != null).map(n => { const s = CAT_STYLE[n.categoria] || CAT_STYLE.Cierre; return { id: n.id, time: n.fecha, position: s.shape === "arrowUp" ? "belowBar" : "aboveBar", shape: s.shape, color: css(s.c), text: n.quiet ? "" : `${n.n} ${s.l}`, size: n.quiet ? 0.6 : 1 }; }); }
function buildTv(C) {
  const host = $("tv"); if (!host) return;
  if (!hasLW()) { host.innerHTML = '<p class="loading">No se pudo cargar la librería de gráficos.</p>'; return; }
  if (tv) { try { tv.remove(); } catch (e) {} tv = null; }
  const LW = LightweightCharts; tv = baseChart(host); cv.charts.tv = tv;
  const TS = C.ts, ser = arr => TS.fechas.map((t, i) => arr[i] == null ? { time: t } : { time: t, value: arr[i] });
  const add = (type, o, pane = 0) => tv.addSeries(LW[type], o, pane);
  document.querySelectorAll("#s-view button").forEach(b => b.disabled = tvs.mode !== "valor");
  $("s-lay").querySelector('[data-v="bench"]').disabled = tvs.mode === "valor"; $("s-lay").querySelector('[data-v="net"]').disabled = tvs.mode !== "valor";
  $("chips").hidden = tvs.mode !== "comp";
  let pane = 0;
  if (tvs.mode === "valor") {
    if (tvs.view === "total" || tvs.view === "sep") { tvPrimary = add("AreaSeries", { lineColor: css("--interactive"), topColor: alpha(css("--interactive"), .3), bottomColor: alpha(css("--interactive"), .03), lineWidth: 2, priceFormat: fmtM }); tvPrimary.setData(ser(TS.valor)); }
    else { const keys = tvs.view === "veh" ? VEH : GOALS, src = tvs.view === "veh" ? TS.veh : TS.meta, col = k => css(tvs.view === "veh" ? VCOL[k] : gcol[k]);
      const cum = TS.fechas.map(() => 0); const stacks = keys.map(k => ({ k, v: src[k].map((x, i) => (cum[i] += (x || 0))) }));
      stacks.slice().reverse().forEach(({ k, v }, j) => { const s = add("AreaSeries", { lineColor: col(k), topColor: col(k), bottomColor: col(k), lineWidth: 1, priceFormat: fmtM, lastValueVisible: j === 0, priceLineVisible: false, crosshairMarkerVisible: false }); s.setData(ser(v)); if (j === 0) tvPrimary = s; }); }
    if (tvs.layers.net) add("LineSeries", { color: css("--text-2"), lineWidth: 2, lineStyle: 2, lineType: 1, priceFormat: fmtM, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false }).setData(ser(TS.neto));
    if (tvs.view === "sep") VEH.forEach(k => { if (!TS.veh[k].some(v => v > 0)) return; pane += 1; const c = vc(k); add("AreaSeries", { lineColor: c, topColor: alpha(c, .35), bottomColor: alpha(c, .05), lineWidth: 2, priceFormat: fmtM, priceLineVisible: false }, pane).setData(ser(TS.veh[k].map(v => v || null)));
      if (LW.createTextWatermark) LW.createTextWatermark(tv.panes()[pane], { horzAlign: "left", vertAlign: "top", lines: [{ text: `${k} · ${VNAME[k]}`, color: css("--text-3"), fontSize: 11 }] }); });
  } else if (tvs.mode === "rent") {
    tvPrimary = add("BaselineSeries", { baseValue: { type: "price", price: 0 }, topLineColor: css("--interactive"), topFillColor1: alpha(css("--interactive"), .27), topFillColor2: alpha(css("--interactive"), .03), bottomLineColor: css("--err"), bottomFillColor1: alpha(css("--err"), .03), bottomFillColor2: alpha(css("--err"), .27), lineWidth: 2, priceFormat: fmtP });
    tvPrimary.setData(ser(TS.twr.map(v => (v - 1) * 100)));
    if (tvs.layers.bench) add("LineSeries", { color: css("--text-2"), lineWidth: 2, lineStyle: 2, priceFormat: fmtP, priceLineVisible: false }).setData(ser(TS.bench.map(v => (v - 1) * 100)));
  } else {
    Object.entries(TS.norm).forEach(([k, n]) => { const f = k === tvs.focus; const color = f ? (VCOL[k] ? vc(k) : css("--text")) : css("--border-strong");
      add("LineSeries", { color, lineWidth: f ? 2 : 1, priceFormat: fmtP, lastValueVisible: f, priceLineVisible: false, crosshairMarkerVisible: f }).setData(n.fechas.map((t, i) => ({ time: t, value: n.valores[i] - 100 }))); });
    if (tvs.layers.bench) add("LineSeries", { color: css("--text-2"), lineWidth: 2, lineStyle: 2, priceFormat: fmtP, priceLineVisible: false }).setData(ser(TS.bench.map(v => (v - 1) * 100)));
    tvPrimary = add("LineSeries", { color: css("--interactive"), lineWidth: 3, priceFormat: fmtP }); tvPrimary.setData(ser(TS.twr.map(v => (v - 1) * 100)));
  }
  if (tvs.layers.dd) { pane += 1; add("AreaSeries", { lineColor: css("--err"), topColor: alpha(css("--err"), .05), bottomColor: alpha(css("--err"), .35), lineWidth: 1, priceFormat: fmtP, invertFilledArea: true, priceLineVisible: false }, pane).setData(ser(TS.dd.map(v => v * 100))); }
  if (tvs.layers.flow) { pane += 1; add("HistogramSeries", { priceFormat: fmtM, priceLineVisible: false }, pane).setData(TS.fechas.map((t, i) => ({ time: t, value: TS.flujo[i], color: TS.flujo[i] < 0 ? css("--err") : css("--interactive") }))); }
  const panes = tv.panes(); if (panes.length > 1) { panes[0].setStretchFactor(tvs.view === "sep" && tvs.mode === "valor" ? 2.2 : 3); for (let i = 1; i < panes.length; i++) panes[i].setStretchFactor(1); }
  host.style.height = (panes.length > 3 ? 760 : panes.length > 1 ? 620 : 520) + "px";
  tvMarkers = LW.createSeriesMarkers(tvPrimary, markersFor(C));
  tv.subscribeCrosshairMove(p => onCross(C, p));
  tv.subscribeClick(p => { const id = p.hoveredObjectId || (p.hoveredInfo && p.hoveredInfo.objectId); if (id && String(id).startsWith("ev")) return focusNews(id, false); if (p.time) { const n = C.noticias.find(x => x.fecha === timeStr(p.time) && !x.quiet); if (n) focusNews(n.id, false); } });
  applyRange(C); onCross(C, {});
}
function onCross(C, p) {
  const TS = C.ts, t = p && p.time ? timeStr(p.time) : TS.fechas[TS.fechas.length - 1], i = idxOf[t] ?? TS.fechas.length - 1, day = TS.fechas[i], parts = [];
  if (tvs.mode === "valor") { parts.push(`<span><i style="background:${css("--interactive")}"></i>Cartera <b class="num">${mm(TS.valor[i])}</b></span>`);
    if (tvs.view === "veh") VEH.forEach(k => TS.veh[k][i] && parts.push(`<span><i style="background:${vc(k)}"></i>${k} <b class="num">${mm(TS.veh[k][i])}</b></span>`));
    if (tvs.view === "meta") GOALS.forEach(g => TS.meta[g][i] != null && parts.push(`<span><i style="background:${css(gcol[g])}"></i>${esc(gname[g])} <b class="num">${mm(TS.meta[g][i])}</b></span>`));
    if (tvs.layers.net) parts.push(`<span>Aportes netos <b class="num">${mm(TS.neto[i])}</b></span><span>Ganancia <b class="num">${smm(TS.valor[i] - TS.neto[i])}</b></span>`); }
  else { parts.push(`<span><i style="background:${css("--interactive")}"></i>Cartera <b class="num">${spct(TS.twr[i] - 1, 2)}</b></span>`); if (tvs.layers.bench) parts.push(`<span>Policy <b class="num">${spct(TS.bench[i] - 1, 2)}</b></span>`); }
  if (tvs.layers.dd) parts.push(`<span>Drawdown <b class="num">${pct(TS.dd[i], 2)}</b></span>`);
  if (TS.flujo[i]) parts.push(`<span>Flujo <b class="num">${smm(TS.flujo[i])}</b></span>`);
  const ev = C.noticias.filter(n => n.fecha === day && !n.quiet).map(n => n.categoria);
  const l = $("tvleg"); if (l) l.innerHTML = `<div class="helper num">${fdate(day)}${ev.length ? " · " + ev.join(", ") : ""}</div><div class="l2">${parts.join("")}</div>`;
}
function applyRange(C) { if (!tv) return; const last = C.ts.fechas[C.ts.fechas.length - 1]; if (tvs.range === "all" || tvs.range === "custom") { if (tvs.range === "all") tv.timeScale().fitContent(); return; }
  const d = new Date(last + "T00:00:00Z"); d.setUTCMonth(d.getUTCMonth() - Number(tvs.range)); const f = d.toISOString().slice(0, 10); tv.timeScale().setVisibleRange({ from: f < C.ts.fechas[0] ? C.ts.fechas[0] : f, to: last }); }
function renderNews(C) {
  const list = C.noticias.filter(n => tvs.newsFilter === "all" || !n.quiet).slice().reverse(); const box = $("nlist"); if (!box) return;
  box.innerHTML = list.map(n => { const s = CAT_STYLE[n.categoria] || CAT_STYLE.Cierre; return `<button class="nitem${n.quiet ? " quiet" : ""}${tvs.active === n.id ? " active" : ""}" data-id="${n.id}"><span class="nt"><span class="nb" style="--bc:var(${s.c})">${n.quiet ? "·" : n.n}</span>${fdate(n.fecha)} · ${esc(n.categoria)}</span><span class="ti">${esc(n.titulo)}</span><span class="su">${esc(tvs.active === n.id ? n.texto : n.resumen)}</span></button>`; }).join("");
  box.querySelectorAll(".nitem").forEach(b => b.addEventListener("click", () => focusNews(b.dataset.id, true)));
}
function focusNews(id, move) {
  const C = cv.C; tvs.active = id; renderNews(C); const e = document.querySelector(`#nlist [data-id="${id}"]`); if (e) e.scrollIntoView({ block: "nearest" });
  const n = C.noticias.find(x => x.id === id); if (!n || !move || !tv || idxOf[n.fecha] == null) return;
  tvs.range = "custom"; document.querySelectorAll("#s-range button").forEach(x => x.setAttribute("aria-pressed", "false"));
  const d = new Date(n.fecha + "T00:00:00Z"), a = new Date(d), b = new Date(d); a.setUTCDate(a.getUTCDate() - 50); b.setUTCDate(b.getUTCDate() + 50);
  const min = C.ts.fechas[0], max = C.ts.fechas[C.ts.fechas.length - 1], f = a.toISOString().slice(0, 10), t = b.toISOString().slice(0, 10);
  tv.timeScale().setVisibleRange({ from: f < min ? min : f, to: t > max ? max : t }); onCross(C, { time: n.fecha });
}

/* ---------- Construcción ---------- */
const cst = { m: 0, corr: "usada", front: null, wt: "actual" };
CT.construccion = function (h, C) {
  const K = C.construccion; if (cst.m >= K.momentos.length) cst.m = 0;
  const Mo = K.momentos[cst.m]; const fronts = Object.keys(Mo.frontera); if (!fronts.includes(cst.front)) cst.front = fronts[fronts.length - 1] || null;
  const stack = w => VEH.filter(k => w[k]).map(k => `<i style="width:${(w[k] * 100).toFixed(1)}%;background:${vc(k)}" title="${k} ${pct(w[k], 0)}"></i>`).join("");
  h.innerHTML = `
    <div class="pagehead"><h2>Cómo se construyó la cartera</h2><p class="muted" style="max-width:96ch">Cada meta tiene su propia cartera, optimizada con media-varianza robusta (QM VII): máximo μ − ${nf(K.delta, 0)}/2·σ² con el tope de volatilidad del horizonte o del IPS y ${pct(K.tope_peso, 0)} por fondo. Las covarianzas usan shrinkage Ledoit-Wolf (QM XXII).</p></div>
    <div class="steps">${[["Historia", `${Mo.n_obs} retornos mensuales`, `${fmonth(Mo.desde.slice(0, 7))} – ${fmonth(Mo.hasta.slice(0, 7))}`], ["Supuestos μ, σ", "Parameter Registry (simulación)", "por subclase"], ["Covarianzas", `shrinkage ${Mo.metodo && Mo.metodo.startsWith("Ledoit") ? "Ledoit-Wolf" : "fijo"}`, `intensidad ${nf(Mo.intensidad, 2)} · ρ̄ ${nf(Mo.rbar, 2)}`], ["Optimización", `máx μ − ${nf(K.delta, 0)}/2·σ²`, `grilla ${nf(K.paso * 100, 0)} pp`], ["Carteras por meta", "tope de vol por horizonte e IPS", Object.values(Mo.sleeves).map(s => pct(s.tope, 1)).join(" / ")], ["Cartera total", "ponderada por capital", ""]].map(([a, b, c]) => `<div class="step" style="--sc:var(--interactive)"><b>${a}</b><span>${b}</span><span class="num">${c}</span></div>`).join("")}</div>
    <div class="grp" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span class="lbl">Momento</span><div class="seg" id="c-mom">${K.momentos.map((m, i) => `<button data-v="${i}" aria-pressed="${i === cst.m}">${esc(m.trigger.split("—")[0].trim())} · ${fdate(m.fecha)}</button>`).join("")}</div></div>
    <div class="g2">
      <div class="tile"><div class="th"><h3>Correlaciones entre fondos</h3><div class="seg" id="c-corr"><button data-v="muestral" aria-pressed="${cst.corr === "muestral"}">Muestral</button><button data-v="usada" aria-pressed="${cst.corr === "usada"}">Usada</button></div></div><div id="corr"></div><p class="helper" id="corr-n"></p></div>
      <div class="tile"><div class="th"><h3>Frontera y carteras alternativas</h3><div class="seg" id="c-front">${fronts.map(g => `<button data-v="${g}" aria-pressed="${g === cst.front}">${esc(gname[g])}</button>`).join("")}</div></div>
        <div class="legend"><span><i style="--c:var(--bar)"></i>Grilla</span><span><i style="--c:var(--text-2)"></i>Frontera</span><span><i class="line" style="border-color:var(--err)"></i>Tope</span><span><i style="--c:var(--interactive)"></i>MVO elegida</span><span><i style="--c:var(--text)"></i>Alternativas</span></div><div class="chart" id="front"></div></div>
    </div>
    <div class="tile"><h3>Carteras alternativas por meta</h3><div id="alts" style="display:grid;gap:16px"></div></div>
    <div class="g2">
      <div class="tile"><h3>Composición de cada meta</h3>${Object.entries(Mo.sleeves).map(([g, s]) => `<div style="display:grid;gap:4px"><div style="display:flex;justify-content:space-between;gap:8px"><span>${esc(gname[g])}</span><span class="helper num">μ ${pct(s.ret, 1)} · σ ${pct(s.vol, 1)} · tope ${pct(s.tope, 1)} (${s.fuente === "IPS" ? "IPS" : "horizonte " + s.horizonte})</span></div><div class="stack">${stack(s.pesos)}</div></div>`).join("")}
        <div style="display:grid;gap:4px;border-top:1px solid var(--border);padding-top:8px"><b>Total</b><div class="stack">${stack(Mo.total)}</div></div><div class="legend">${VEH.map(k => `<span><i style="--c:${vc(k)}"></i>${k} · ${VNAME[k]}</span>`).join("")}</div></div>
      <div class="tile"><h3>Supuestos de mercado (CMA)</h3><div class="tw"><table class="dt"><thead><tr><th>Fondo</th><th>μ usado</th><th>μ histórico</th><th>σ usado</th></tr></thead><tbody>${VEH.map(k => `<tr><td><span class="sw" style="--c:${vc(k)}"></span>${k} · ${VNAME[k]}</td><td class="n">${pct(Mo.mu[k], 1)}</td><td class="n">${pct(Mo.mu_historico[k], 1)}</td><td class="n">${pct(Mo.vol[k], 1)}</td></tr>`).join("")}</tbody></table></div><p class="helper">μ y σ son valores de simulación del Parameter Registry: el Comité aún no publica CMAs. La historia solo aporta correlaciones.</p></div>
    </div>
    ${Object.keys(K.momentos[0].sensibilidad).length ? `<div class="tile"><h3>¿Cambia la cartera según el shrinkage? (onboarding)</h3><div class="tw"><table class="dt" id="sens"></table></div></div>` : ""}
    <div class="tile"><div class="th"><h3>Pesos por fondo en el tiempo</h3><div class="seg" id="c-wt"><button data-v="actual" aria-pressed="${cst.wt === "actual"}">Reales</button><button data-v="politica" aria-pressed="${cst.wt === "politica"}">Objetivo</button></div></div><div id="wt" style="height:300px"></div></div>`;
  const rebind = (id, key) => document.querySelectorAll(`#${id} button`).forEach(b => b.addEventListener("click", () => { cst[key] = key === "m" ? +b.dataset.v : b.dataset.v; renderCTab(); }));
  rebind("c-mom", "m"); rebind("c-corr", "corr"); rebind("c-front", "front"); rebind("c-wt", "wt");
  const mat = cst.corr === "usada" ? Mo.corr_usada : Mo.corr_muestral;
  const cc = v => { const a = Math.min(1, Math.abs(v)); return `background:color-mix(in srgb, var(${v >= 0 ? "--div-pos" : "--div-neg"}) ${Math.round(a * 100)}%, var(--div-0));color:${a > 0.55 ? "#ffffff" : "var(--text)"}`; };
  $("corr").innerHTML = `<div class="corr" style="grid-template-columns:44px repeat(${VEH.length}, minmax(0,1fr))"><div class="h"></div>${VEH.map(k => `<div class="h">${k}</div>`).join("")}${VEH.map((ki, i) => `<div class="h" style="text-align:left">${ki}</div>` + VEH.map((kj, j) => `<div style="${cc(mat[i][j])}">${nf(mat[i][j], 2)}</div>`).join("")).join("")}</div>`;
  $("corr-n").textContent = cst.corr === "usada" ? `Con ${Mo.n_obs} meses, Ledoit-Wolf calcula intensidad ${nf(Mo.intensidad, 2)}: ${Mo.intensidad > 0.9 ? "las correlaciones muestrales no se distinguen del ruido y casi todas se reemplazan por el promedio" : "se mezclan con el promedio"} (ρ̄ = ${nf(Mo.rbar, 2)}). Las varianzas no se tocan.` : `Correlaciones observadas en ${Mo.n_obs} meses; error estándar cercano a ±${nf(1 / Math.sqrt(Mo.n_obs), 2)} cada una.`;
  // Frontera
  const F0 = Mo.frontera[cst.front], fh = $("front");
  if (F0) { const AL = (Mo.alternativas[cst.front] || {}).alternativas || {}; const allp = F0.nube.concat(Object.values(AL).map(a => [a.volatilidad_ex_ante, a.retorno_esperado]));
    const W = Math.max(320, fh.clientWidth), H = 280, m = { t: 12, r: 16, b: 34, l: 46 };
    const vmax = Math.min(0.2, Math.max(...allp.map(p => p[0]), F0.tope) * 1.05), r0 = Math.min(...allp.map(p => p[1])), r1 = Math.max(...allp.map(p => p[1])), pad = (r1 - r0) * .06;
    const x = v => m.l + v / vmax * (W - m.l - m.r), y = r => m.t + (1 - (r - (r0 - pad)) / (r1 - r0 + 2 * pad)) * (H - m.t - m.b);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Frontera eficiente y carteras alternativas" }, fh);
    for (let v = 0; v <= vmax + 1e-9; v += vmax > 0.12 ? 0.04 : 0.02) { el("line", { x1: x(v), x2: x(v), y1: m.t, y2: H - m.b, stroke: css("--border") }, svg); txt(svg, x(v), H - m.b + 14, pct(v, 0), { "text-anchor": "middle" }); }
    for (let r = Math.ceil(r0 / .01) * .01; r <= r1 + 1e-9; r += .01) { el("line", { x1: m.l, x2: W - m.r, y1: y(r), y2: y(r), stroke: css("--border") }, svg); txt(svg, m.l - 6, y(r) + 4, pct(r, 0), { "text-anchor": "end" }); }
    txt(svg, W - m.r, H - 4, "volatilidad esperada", { "text-anchor": "end" });
    F0.nube.forEach(p => { if (p[0] <= vmax) el("circle", { cx: x(p[0]), cy: y(p[1]), r: 1.6, fill: css("--bar") }, svg); });
    el("path", { d: F0.envolvente.filter(p => p[0] <= vmax).map((p, i) => `${i ? "L" : "M"}${x(p[0])},${y(p[1])}`).join(""), fill: "none", stroke: css("--text-2"), "stroke-width": 1.5 }, svg);
    el("rect", { x: x(F0.tope), y: m.t, width: Math.max(0, W - m.r - x(F0.tope)), height: H - m.t - m.b, fill: css("--err"), "fill-opacity": .06 }, svg);
    el("line", { x1: x(F0.tope), x2: x(F0.tope), y1: m.t, y2: H - m.b, stroke: css("--err"), "stroke-dasharray": "5 4", "stroke-width": 1.5 }, svg); txt(svg, x(F0.tope) + 4, m.t + 12, `tope ${pct(F0.tope, 1)}`, { style: `fill:${css("--err")}` });
    Object.entries(AL).filter(([k]) => k !== "MVO").forEach(([k, a]) => { if (a.volatilidad_ex_ante > vmax) return; el("rect", { x: x(a.volatilidad_ex_ante) - 5, y: y(a.retorno_esperado) - 5, width: 10, height: 10, fill: css("--text"), transform: `rotate(45 ${x(a.volatilidad_ex_ante)} ${y(a.retorno_esperado)})` }, svg); txt(svg, x(a.volatilidad_ex_ante) + 10, y(a.retorno_esperado) + (k === "ERC" ? 12 : -6), k === "ERC" ? "ERC (ref.)" : "Mín. vol", { style: `fill:${css("--text")}` }); });
    el("circle", { cx: x(F0.elegida[0]), cy: y(F0.elegida[1]), r: 7, fill: css("--interactive"), stroke: css("--layer"), "stroke-width": 2.5 }, svg);
    txt(svg, x(F0.elegida[0]) - 10, y(F0.elegida[1]) - 10, `${pct(F0.elegida[1], 1)} · σ ${pct(F0.elegida[0], 1)}`, { "text-anchor": "end", style: `fill:${css("--text")};font-weight:600` });
  } else fh.innerHTML = '<p class="muted">Sin frontera: un solo vehículo elegible.</p>';
  // Alternativas
  $("alts").innerHTML = Object.entries(Mo.alternativas).map(([g, a]) => {
    if (!Object.keys(a.alternativas).length) return `<div style="display:flex;gap:12px;flex-wrap:wrap"><b>${esc(gname[g])}</b>${si("sin_datos", "Nivel " + a.nivel)}<span class="helper">${esc(a.motivo_nivel)}</span></div>`;
    return `<div style="display:grid;gap:8px"><div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center"><b>${esc(gname[g])}</b>${si(a.nivel === 3 ? "ok" : "atencion", "Nivel " + a.nivel)}</div>
      <div class="tw"><table class="dt"><thead><tr><th>Cartera</th><th style="text-align:left">Pesos</th><th>μ</th><th>σ</th><th>Adverso</th><th>Prob. meta</th><th>Mayor aporte al riesgo</th><th>Admisible</th></tr></thead><tbody>${Object.entries(a.alternativas).map(([k, x]) => `<tr class="${k === a.recomendada ? "hl" : ""}"><td class="tx"><b>${esc(x.nombre)}</b>${k === a.recomendada ? " " + si("ok", "Recomendada") : ""}</td><td style="min-width:140px"><div class="stack">${stack(x.pesos)}</div></td><td class="n">${pct(x.retorno_esperado, 1)}</td><td class="n">${pct(x.volatilidad_ex_ante, 1)}</td><td class="n${cls(x.retorno_escenario_adverso)}">${spct(x.retorno_escenario_adverso, 1)}</td><td class="n">${x.prob_exito == null ? "—" : pct(x.prob_exito, 0)}</td><td class="n">${pct(x.max_contribucion_riesgo, 0)}</td><td>${x.admisible ? si("ok", "Sí") : si("alerta", "No") + `<div class="helper" style="white-space:normal">${esc(x.motivo_inadmisible)}</div>`}</td></tr>`).join("")}</tbody></table></div>
      ${a.tradeoffs.map(t => `<div class="to"><b>${esc(t.conflicto)}</b><div class="cols"><div><span class="pos">Mejora</span><ul>${t.mejora.map(s => `<li>${esc(s)}</li>`).join("")}</ul></div><div><span class="neg">Empeora</span><ul>${t.empeora.map(s => `<li>${esc(s)}</li>`).join("")}</ul></div></div></div>`).join("")}
      <p class="helper">${esc(a.recomendacion || a.motivo_nivel)}</p></div>`; }).join("");
  // Sensibilidad
  const SE = K.momentos[0].sensibilidad, tags = Object.keys(SE);
  if (tags.length && $("sens")) { const gs = Object.keys(SE[tags[0]].sleeves).filter(g => Object.keys(SE[tags[0]].sleeves[g].pesos).length > 1);
    $("sens").innerHTML = `<thead><tr><th>Meta</th><th style="text-align:left">Shrinkage</th><th>Intensidad</th>${VEH.map(k => `<th>${k}</th>`).join("")}<th>μ</th><th>σ</th></tr></thead><tbody>` + gs.map(g => tags.map((tg, i) => { const s = SE[tg].sleeves[g]; if (!s) return ""; return `<tr class="${tg === "Ledoit-Wolf" ? "hl" : ""}">${i === 0 ? `<td rowspan="${tags.length}">${esc(gname[g])}</td>` : ""}<td style="text-align:left">${tg}</td><td class="n">${nf(SE[tg].intensidad, 2)}</td>${VEH.map(k => { const w = s.pesos[k] || 0; return w ? `<td class="n w" style="--pct:${(w * 100).toFixed(0)}%">${pct(w, 0)}</td>` : '<td class="n helper">·</td>'; }).join("")}<td class="n">${pct(s.ret, 2)}</td><td class="n">${pct(s.vol, 2)}</td></tr>`; }).join("")).join("") + "</tbody>"; }
  // Pesos en el tiempo
  if (hasLW()) { const LW = LightweightCharts, ch = baseChart($("wt"), { handleScroll: false, handleScale: false }); const P = K.pesos_t, cum = P.map(() => 0);
    const st = VEH.map(k => ({ k, v: P.map((p, i) => (cum[i] += p[cst.wt][k] * 100)) })); let top = null;
    st.slice().reverse().forEach(({ k, v }, j) => { const c = vc(k); const s = ch.addSeries(LW.AreaSeries, { lineColor: c, topColor: c, bottomColor: c, lineWidth: 1, priceFormat: fmtP, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false, autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }) }); s.setData(P.map((p, i) => ({ time: p.fecha, value: v[i] }))); if (j === 0) top = s; });
    LW.createSeriesMarkers(top, K.momentos.map((m, i) => ({ time: P.find(p => p.fecha >= m.fecha)?.fecha || m.fecha, position: "aboveBar", shape: "arrowDown", color: css("--text"), text: String(i + 1) })));
    ch.timeScale().fitContent(); cv.charts.wt = ch; }
};

/* ---------- Cartera ---------- */
CT.cartera = function (h, C) {
  const S = C.resumen, Dr = C.drift, dv = C.div_cierre, R = C.rentabilidad;
  h.innerHTML = `
    <div class="g2">
      <div class="tile"><h3>Peso actual frente al objetivo</h3><div class="legend"><span><i style="--c:var(--interactive)"></i>Actual</span><span><i style="--c:var(--layer-2);outline:1px solid var(--border-strong)"></i>Banda ±${pct(Dr.banda, 0)}</span><span><i class="line" style="border-top-style:solid;border-color:var(--text)"></i>Objetivo</span></div><div class="chart" id="drift"></div><p class="helper">Cartera total. Dentro de la banda no se propone operar; fuera, el flujo de rebalanceo genera alternativas por meta.</p></div>
      <div class="tile"><h3>Peso frente a aporte al riesgo</h3><div class="legend"><span><i style="--c:var(--bar)"></i>Peso</span><span><i style="--c:var(--interactive)"></i>Aporte al riesgo</span></div><div class="chart" id="riskw"></div><p class="helper" id="riskw-n"></p></div>
    </div>
    <div class="tile"><h3>Retorno mensual de la cartera</h3><div id="heat" style="overflow-x:auto"></div><p class="helper">Sin efecto de aportes ni retiros (TWR).</p></div>
    <div class="tile"><h3>Rentabilidad por fondo</h3><div class="tw"><table class="dt" id="rent"></table></div><p class="helper">Valor cuota ajustado (repartos reinvertidos). BTG Liquidez Alternativa parte el 04-10-2021.</p></div>
    <div class="g2">
      <div class="tile"><h3>Qué aportó cada fondo</h3><div class="tw"><table class="dt" id="pnl"></table></div></div>
      <div class="tile"><h3>Atribución frente al policy benchmark</h3><div class="tw"><table class="dt" id="brin"></table></div><p class="helper">Brinson-Fachler (ADVANCED). Suma aritmética mensual.</p></div>
    </div>`;
  const ks = VEH.filter(k => (Dr.actual[k] || 0) > 0 || (Dr.objetivo[k] || 0) > 0), dh = $("drift");
  const W = Math.max(320, dh.clientWidth), rh = 30, m = { t: 6, r: 16, b: 24, l: 150 }, H = m.t + m.b + rh * ks.length, x = v => m.l + v * (W - m.l - m.r);
  const s1 = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Peso actual frente al objetivo" }, dh);
  [0, .25, .5].forEach(v => { el("line", { x1: x(v * 2), x2: x(v * 2), y1: m.t, y2: H - m.b, stroke: css("--border") }, s1); txt(s1, x(v * 2), H - 6, pct(v * 2, 0), { "text-anchor": "middle" }); });
  ks.forEach((k, i) => { const cy = m.t + i * rh + rh / 2, a = Dr.actual[k] || 0, o = Dr.objetivo[k] || 0, out = Math.abs(a - o) > Dr.banda;
    txt(s1, m.l - 8, cy + 4, `${k} · ${VNAME[k]}`, { "text-anchor": "end", style: `fill:${css("--text-2")}` });
    el("rect", { x: x(Math.max(0, o - Dr.banda)), y: cy - 7, width: x(Math.min(1, o + Dr.banda)) - x(Math.max(0, o - Dr.banda)), height: 14, fill: css("--layer-2"), stroke: css("--border-strong") }, s1);
    el("line", { x1: x(o), x2: x(o), y1: cy - 9, y2: cy + 9, stroke: css("--text"), "stroke-width": 2 }, s1);
    el(out ? "rect" : "circle", out ? { x: x(a) - 5, y: cy - 5, width: 10, height: 10, fill: css("--err"), transform: `rotate(45 ${x(a)} ${cy})` } : { cx: x(a), cy, r: 5.5, fill: css("--interactive") }, s1);
    txt(s1, x(a) + (a > .85 ? -10 : 10), cy + 4, `${pct(a, 1)} (${spct(a - o, 1)})`, { "text-anchor": a > .85 ? "end" : "start", style: `fill:${css("--text")}` }); });
  const keys = VEH.filter(k => dv.pesos[k]), rh2 = $("riskw"), W2 = Math.max(320, rh2.clientWidth), m2 = { t: 6, r: 60, b: 22, l: 110 }, H2 = m2.t + m2.b + 34 * keys.length;
  const top = Math.max(.6, ...keys.map(k => Math.max(dv.pesos[k], dv.contribucion_riesgo[k]))) , x2 = v => m2.l + v * (W2 - m2.l - m2.r) / top;
  const s2 = el("svg", { viewBox: `0 0 ${W2} ${H2}`, role: "img", "aria-label": "Peso frente a aporte al riesgo" }, rh2);
  keys.forEach((k, i) => { const cy = m2.t + i * 34 + 17; txt(s2, m2.l - 8, cy + 4, `${k} · ${VNAME[k]}`, { "text-anchor": "end", style: `fill:${css("--text-2")}` });
    el("rect", { x: x2(0), y: cy - 12, width: x2(dv.pesos[k]) - x2(0), height: 10, fill: css("--bar") }, s2); el("rect", { x: x2(0), y: cy + 1, width: Math.max(1, x2(Math.max(0, dv.contribucion_riesgo[k])) - x2(0)), height: 10, fill: css("--interactive") }, s2);
    txt(s2, x2(Math.max(dv.pesos[k], dv.contribucion_riesgo[k])) + 6, cy + 4, `${pct(dv.pesos[k], 0)} → ${pct(dv.contribucion_riesgo[k], 0)}`, { style: `fill:${css("--text")}` }); });
  const rv = (dv.contribucion_riesgo.RVL || 0) + (dv.contribucion_riesgo.RVG || 0), rvw = (dv.pesos.RVL || 0) + (dv.pesos.RVG || 0);
  $("riskw-n").textContent = `La renta variable pesa ${pct(rvw, 0)} y explica ${pct(rv, 0)} del riesgo.${dv.pesos.DP ? ` Facturas pesa ${pct(dv.pesos.DP, 0)} y casi no aporta riesgo medido: su valor cuota está suavizado.` : ""}`;
  const rets = Object.fromEntries(C.retornos_mensuales.map(r => [r.mes, r.r])), years = [...new Set(C.retornos_mensuales.map(r => r.mes.slice(0, 4)))];
  const col = v => { const a = Math.min(1, Math.abs(v) / 0.04); return `background:color-mix(in srgb, var(${v >= 0 ? "--div-pos" : "--div-neg"}) ${Math.round(a * 85)}%, var(--div-0));color:${a > .6 ? "#fff" : "var(--text)"}`; };
  $("heat").innerHTML = `<div class="heat" style="min-width:640px"><div class="h"></div>${MON.map(x => `<div class="h">${x}</div>`).join("")}${years.map(y => `<div class="h" style="text-align:left">${y}</div>` + MON.map((_, i) => { const k = `${y}-${String(i + 1).padStart(2, "0")}`, v = rets[k]; return v == null ? "<div></div>" : `<div style="${col(v)}" title="${fmonth(k)}: ${spct(v, 2)}">${spct(v, 1)}</div>`; }).join("")).join("")}</div>`;
  const rrow = (name, r) => `<tr><td class="tx">${name}</td>${["1m", "3m", "ytd", "1a", "3a", "5a", "desde_inicio_anual"].map(k => `<td class="n${cls(r[k])}">${pct(r[k], 1)}</td>`).join("")}<td class="n">${pct(r.volatilidad_3a, 1)}</td><td class="n neg">${pct(r.max_drawdown_3a, 1)}</td></tr>`;
  $("rent").innerHTML = `<thead><tr><th>Fondo</th><th>1 mes</th><th>3 meses</th><th>YTD</th><th>1 año</th><th>3 años</th><th>5 años</th><th>Inicio</th><th>Vol 3a</th><th>Caída 3a</th></tr></thead><tbody>${VEH.map(k => rrow(`<span class="sw" style="--c:${vc(k)}"></span>${k} · ${esc(R[k].nombre)}`, R[k])).join("")}<tr class="grp"><td colspan="10">Referencias (no elegibles como benchmark)</td></tr>${rrow(esc(L.referencias.IPSA.nombre), L.referencias.IPSA)}${rrow(esc(L.referencias.AFP_C.nombre), L.referencias.AFP_C)}</tbody>`;
  const mg = Math.max(...VEH.map(k => Math.abs(R[k].ciclo.ganancia_clp))) || 1;
  $("pnl").innerHTML = `<thead><tr><th>Fondo</th><th>Retorno del fondo</th><th>Invertido neto</th><th>Valor final</th><th>Ganancia</th></tr></thead><tbody>${VEH.map(k => { const c = R[k].ciclo; return `<tr><td>${k}</td><td class="n">${pct(c.retorno_vehiculo, 1)}</td><td class="n">${mm(c.invertido_neto)}</td><td class="n">${mm(c.valor_final)}</td><td class="n w" style="--pct:${(Math.abs(c.ganancia_clp) / mg * 100).toFixed(0)}%">${mm(c.ganancia_clp)}</td></tr>`; }).join("")}<tr><td><b>Total</b></td><td></td><td></td><td class="n">${mm(S.valor_final)}</td><td class="n"><b>${mm(C.flujos.ganancia_neta)}</b></td></tr></tbody>`;
  const B = (C.relativo.realizado || {}).atribucion;
  $("brin").innerHTML = B ? `<thead><tr><th>Fondo</th><th>Asignación</th><th>Selección</th><th>Interacción</th></tr></thead><tbody>${VEH.map(k => { const b = B.por_vehiculo[k]; return `<tr><td>${k}</td><td class="n${cls(b.asignacion)}">${spct(b.asignacion, 2)}</td><td class="n${cls(b.seleccion)}">${spct(b.seleccion, 2)}</td><td class="n${cls(b.interaccion)}">${spct(b.interaccion, 2)}</td></tr>`; }).join("")}<tr><td><b>Total</b></td><td class="n">${spct(B.total.asignacion, 2)}</td><td class="n"><b>${spct(B.total.seleccion, 2)}</b></td><td class="n">${spct(B.total.interaccion, 2)}</td></tr></tbody>` : "<tbody><tr><td class='muted'>Sin atribución.</td></tr></tbody>";
};

/* ---------- Riesgo ---------- */
const rst = { goal: null };
CT.riesgo = function (h, C) {
  const ST = C.stress, scen = [...Object.values(ST.hipoteticos).map(v => ({ v, t: "H" })), ...Object.values(ST.historicos).map(v => ({ v, t: "E" }))];
  const fans = Object.keys(C.abanico); if (!fans.includes(rst.goal)) rst.goal = fans[fans.length - 1] || null;
  const RS = ST.inverso, Lm = C.limites, gm = GOALS.filter(g => C.metas_cierre[g] && C.metas_cierre[g].prob_exito != null);
  h.innerHTML = `
    <div class="pagehead"><h2>Riesgo y stress</h2><p class="muted" style="max-width:96ch">Cartera actual en los cuatro escenarios del Comité (simulación) y en episodios reales, medida en retorno, riesgo, liquidez, concentración y metas.</p></div>
    <div class="g2">
      <div class="tile"><div class="th"><h3>Impacto por escenario</h3><span class="helper" id="st-ro"></span></div><div class="chart" id="stc"></div></div>
      <div class="tile"><div class="th"><h3>Rango de resultados en el tiempo</h3>${fans.length ? `<div class="seg" id="r-fan">${fans.map(g => `<button data-v="${g}" aria-pressed="${g === rst.goal}">${esc(gname[g])}</button>`).join("")}</div>` : ""}</div><div class="legend"><span><i style="--c:var(--g2);opacity:.3"></i>P10–P90</span><span><i style="--c:var(--g2);opacity:.55"></i>P25–P75</span><span><i style="--c:var(--g2)"></i>Mediana</span><span><i class="line"></i>Objetivo</span></div><div class="chart" id="fan"></div><p class="helper" id="fan-n"></p></div>
    </div>
    <div class="tile" id="rs"></div>
    <div class="tile"><h3>Cinco dimensiones por escenario</h3><div class="tw"><table class="dt" id="st5"></table></div><p class="helper">${esc(ST.moneda)} VaR base ${pct(ST.var95_1m_base, 2)}.</p></div>
    <div class="g2">
      <div class="tile"><h3>Riesgo frente a los límites del IPS</h3><div class="tw"><table class="dt" id="lim"></table></div><p class="helper">Exceder un límite genera una alerta, nunca un ajuste automático (D8). ${esc(Lm.nota)}</p></div>
      <div class="tile"><h3>Pérdida o ganancia por fondo (millones CLP)</h3><div class="tw"><table class="dt" id="stv"></table></div></div>
    </div>`;
  document.querySelectorAll("#r-fan button").forEach(b => b.addEventListener("click", () => { rst.goal = b.dataset.v; renderCTab(); }));
  const host = $("stc"), W = Math.max(320, host.clientWidth), rh = 30, m = { t: 6, r: 60, b: 22, l: 170 }, H = m.t + m.b + rh * scen.length;
  const ext = Math.max(.05, ...scen.map(s => Math.abs(s.v.retorno))) * 1.15, x = v => m.l + (v + ext) / (2 * ext) * (W - m.l - m.r);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Retorno por escenario" }, host);
  [-ext, -ext / 2, 0, ext / 2, ext].forEach(v => { el("line", { x1: x(v), x2: x(v), y1: m.t, y2: H - m.b, stroke: v === 0 ? css("--text-3") : css("--border") }, svg); txt(svg, x(v), H - 6, pct(v, 0), { "text-anchor": "middle" }); });
  scen.forEach(({ v }, i) => { const cy = m.t + i * rh + rh / 2; txt(svg, m.l - 8, cy + 4, v.nombre, { "text-anchor": "end", style: `fill:${css("--text-2")}` });
    el("rect", { x: Math.min(x(0), x(v.retorno)), y: cy - 9, width: Math.max(1, Math.abs(x(v.retorno) - x(0))), height: 18, fill: v.retorno < 0 ? css("--err") : css("--interactive") }, svg);
    txt(svg, v.retorno < 0 ? x(v.retorno) - 6 : x(v.retorno) + 6, cy + 4, spct(v.retorno, 1), { "text-anchor": v.retorno < 0 ? "end" : "start", style: `fill:${css("--text")}` });
    const hv = el("rect", { x: 0, y: cy - rh / 2, width: W, height: rh, fill: "transparent" }, svg); hv.addEventListener("pointerenter", () => { $("st-ro").textContent = `${v.nombre} · ${mm(v.pnl_clp)}`; }); });
  el("line", { x1: 0, x2: W, y1: m.t + rh * Object.keys(ST.hipoteticos).length, y2: m.t + rh * Object.keys(ST.hipoteticos).length, stroke: css("--border-strong"), "stroke-dasharray": "4 4" }, svg);
  // Abanico dinámico
  const fh = $("fan");
  if (rst.goal) { const path = C.abanico[rst.goal], goal = C.cliente.metas.find(g => g.key === rst.goal), Wf = Math.max(320, fh.clientWidth), Hf = 260, mf = { t: 12, r: 64, b: 26, l: 56 };
    const ymax = Math.max(goal.objetivo, ...path.map(p => p.p90)) * 1.08, xm = path[path.length - 1].mes, start = new Date(C.resumen.fecha);
    const xf = mth => mf.l + mth / xm * (Wf - mf.l - mf.r), yf = v => mf.t + (1 - v / ymax) * (Hf - mf.t - mf.b);
    const sf = el("svg", { viewBox: `0 0 ${Wf} ${Hf}`, role: "img", "aria-label": `Abanico de ${goal.nombre}` }, fh);
    for (let t = 0; t <= 4; t++) { const v = ymax * t / 4; el("line", { x1: mf.l, x2: Wf - mf.r, y1: yf(v), y2: yf(v), stroke: css("--border") }, sf); txt(sf, mf.l - 6, yf(v) + 4, nf(v / 1e6, 0) + "M", { "text-anchor": "end" }); }
    const yrs = []; for (let y = start.getFullYear() + 1; y <= new Date(goal.fecha).getFullYear(); y++) yrs.push(y);
    const stepY = Math.max(1, Math.ceil(yrs.length / 6)); yrs.forEach((y, i) => { if (i % stepY && y !== yrs[yrs.length - 1]) return; const mth = (y - start.getFullYear()) * 12 - start.getMonth(); if (mth > 0 && mth <= xm) txt(sf, xf(mth), Hf - 8, String(y), { "text-anchor": "middle" }); });
    const band = (a, b, op) => el("path", { d: path.map((p, i) => `${i ? "L" : "M"}${xf(p.mes)},${yf(p[a])}`).join("") + path.slice().reverse().map(p => `L${xf(p.mes)},${yf(p[b])}`).join("") + "Z", fill: css("--g2"), "fill-opacity": op }, sf);
    band("p90", "p10", .18); band("p75", "p25", .32);
    el("path", { d: path.map((p, i) => `${i ? "L" : "M"}${xf(p.mes)},${yf(p.p50)}`).join(""), fill: "none", stroke: css("--g2"), "stroke-width": 2.5 }, sf);
    el("line", { x1: mf.l, x2: Wf - mf.r, y1: yf(goal.objetivo), y2: yf(goal.objetivo), stroke: css("--text-2"), "stroke-width": 1.5, "stroke-dasharray": "5 4" }, sf); txt(sf, mf.l + 6, yf(goal.objetivo) - 6, `objetivo ${mm(goal.objetivo)}`, { style: `fill:${css("--text-2")}` });
    const last = path[path.length - 1]; txt(sf, Wf - mf.r + 4, yf(last.p50) + 4, mm(last.p50), { style: `fill:${css("--text")}` });
    $("fan-n").textContent = `Hoy ${mm(path[0].p50)}, aporte ${mm(goal.aporte)}/mes. Al ${fdate(goal.fecha)}: mediana ${mm(last.p50)}; en el 10% de peores trayectorias, ${mm(last.p10)} o menos. Probabilidad de lograrla: ${pct(C.metas_cierre[rst.goal].prob_exito, 0)}.`;
  } else fh.innerHTML = '<p class="muted">Sin metas con fecha para proyectar.</p>';
  // Reverse stress
  if (RS && !RS.no_calculado) { const br = RS.escenario_stress_escalado.multiplicador < 1;
    $("rs").innerHTML = `<div class="th"><h3>Reverse stress: ¿qué rompe el límite del IPS?</h3>${si(br ? "alerta" : "ok", br ? "El escenario Stress ya lo rompe" : "Stress dentro del límite")}</div>
      <p class="muted">Ruptura = ${esc(RS.definicion)}: ${mm(RS.perdida_clp)}. ${br ? `El escenario Stress implica ${pct(RS.escenario_stress_escalado.perdida_escenario, 1)}: con el ${nf(RS.escenario_stress_escalado.multiplicador * 100, 0)}% de su intensidad se alcanza el límite. Es una alerta para el WM (D8).` : ""}</p>
      <div class="tw"><table class="dt"><thead><tr><th>Dirección del shock</th><th style="text-align:left">Lo que haría falta</th></tr></thead><tbody><tr><td>Escenario Stress escalado</td><td class="tx num">${nf(RS.escenario_stress_escalado.multiplicador * 100, 0)}% de su intensidad</td></tr><tr><td>Renta variable en bloque</td><td class="tx num">${spct(RS.renta_variable_en_bloque.shock_necesario, 1)} (exposición ${pct(RS.renta_variable_en_bloque.exposicion, 0)})</td></tr>${Object.entries(RS.por_fondo).map(([k, v]) => `<tr><td>${k} · ${VNAME[k]} solo</td><td class="tx num">${v.posible ? `${spct(v.shock_necesario, 1)} (peso ${pct(v.exposicion, 0)})` : `imposible: exigiría ${spct(v.shock_necesario, 0)}`}</td></tr>`).join("")}</tbody></table></div><p class="helper">ADVANCED (QM XI). ${esc(RS.nota)}</p>`; }
  else $("rs").innerHTML = `<div class="th"><h3>Reverse stress</h3>${si("sin_datos", "Sin calcular")}</div><p class="muted">${esc(RS ? RS.no_calculado : "Sin datos")}</p>`;
  $("st5").innerHTML = `<thead><tr><th>Escenario</th><th>Retorno</th><th>CLP</th><th>VaR 95% 1m después</th><th>LCR 0-3m</th><th>HHI después</th>${gm.map(g => `<th>${esc(gname[g])}</th>`).join("")}<th>Mayor pérdida</th></tr></thead><tbody>` +
    scen.map(({ v, t }, i) => (i === 0 ? `<tr class="grp"><td colspan="${7 + gm.length}">Hipotéticos (${esc(ST.biblioteca_version)}, 12 meses)</td></tr>` : (t === "E" && scen[i - 1].t === "H") ? `<tr class="grp"><td colspan="${7 + gm.length}">Episodios históricos</td></tr>` : "") +
      `<tr><td class="tx">${esc(v.nombre)}${v.desde ? `<br><span class="helper">${fdate(v.desde)} a ${fdate(v.hasta)}</span>` : ""}</td><td class="n${cls(v.retorno)}">${spct(v.retorno, 1)}</td><td class="n${cls(v.pnl_clp)}">${mm(v.pnl_clp)}</td><td class="n">${pct(v.var95_1m_post, 2)}</td><td class="n">${nf(v.lcr_0_3m, 1)}×</td><td class="n">${nf(v.hhi_post, 3)}</td>${gm.map(g => `<td class="n">${pct(((v.metas || {})[g] || {}).prob_exito, 0)}</td>`).join("")}<td>${esc(v.mayor_perdida_vehiculo || "—")}</td></tr>`).join("") + "</tbody>";
  $("lim").innerHTML = `<thead><tr><th>Métrica</th><th>Valor</th><th>Límite</th><th>Estado</th></tr></thead><tbody>${Lm.controles.map(c => `<tr><td>${esc(c.metrica)}</td><td class="n">${pct(c.valor, 2)}</td><td class="n">${c.limite == null ? "—" : pct(c.limite, 0)}</td><td>${c.limite == null ? si("sin_datos", "Sin límite") : c.estado === "dentro" ? si("ok", "Dentro") : si("alerta", "Excede")}</td></tr>`).join("")}<tr><td>Máxima caída diaria</td><td class="n">${pct(-C.max_dd_diario, 2)}</td><td class="n">${C.ips.limites.dd == null ? "—" : pct(C.ips.limites.dd / 100, 0)}</td><td>${C.ips.limites.dd == null ? si("sin_datos", "Sin límite") : -C.max_dd_diario <= C.ips.limites.dd / 100 ? si("ok", "Dentro") : si("alerta", "Excede")}</td></tr></tbody>`;
  const held = VEH.filter(k => ST.hipoteticos.base.pnl_por_vehiculo[k] !== undefined);
  $("stv").innerHTML = `<thead><tr><th>Escenario</th>${held.map(k => `<th>${k}</th>`).join("")}</tr></thead><tbody>${scen.map(({ v }) => `<tr><td>${esc(v.nombre)}</td>${held.map(k => `<td class="n${cls(v.pnl_por_vehiculo[k])}">${nf(v.pnl_por_vehiculo[k] / 1e6, 1)}${!["observado", "hipotético"].includes(v.fuente_por_vehiculo[k]) ? '<sup title="' + esc(v.fuente_por_vehiculo[k]) + '">*</sup>' : ""}</td>`).join("")}</tr>`).join("")}</tbody>`;
};

/* ---------- Benchmark ---------- */
const DIM_LABEL = { objetivo: "Objetivo", asset_allocation: "Asset allocation", riesgo: "Riesgo", moneda: "Moneda", liquidez: "Liquidez", horizonte: "Horizonte", costos: "Costos", restricciones: "Restricciones" };
CT.benchmark = function (h, C) {
  const A = C.relativo.asignacion, RR = C.relativo.realizado, PF = L.relativo_por_fondo || {};
  const dimSt = { cumple: ["ok", "Cumple"], no_cumple: ["alerta", "No cumple"], no_verificable: ["atencion", "No verificable"] }, estSt = { elegible: ["ok", "Elegible"], parcial: ["atencion", "Parcial"], no_elegible: ["alerta", "No elegible"] };
  h.innerHTML = `
    <div class="pagehead"><h2>Benchmark y tracking error</h2><p class="muted" style="max-width:96ch">Antes de comparar se verifican las ocho dimensiones de QM XII; moneda, liquidez y restricciones son críticas (D10). Sin benchmark elegible no hay ranking.</p></div>
    <div class="g3">${C.benchmark.map(c => { const [s, l] = estSt[c.estado]; return `<div class="tile"><div class="th"><h4>${esc(c.benchmark)}</h4>${si(s, l)}</div><p class="helper">${esc(c.regla)}</p>${Object.entries(c.dimensiones).map(([d, v]) => { const [ds, dl] = dimSt[v.estado]; return `<div style="display:grid;grid-template-columns:120px 1fr;gap:8px;border-top:1px solid var(--border);padding-top:6px;font-size:13px"><span>${si(ds, dl)}${v.critica ? '<br><span class="helper">crítica</span>' : ""}</span><span><b>${DIM_LABEL[d]}</b><br><span class="helper">${esc(v.detalle)}</span></span></div>`; }).join("")}</div>`; }).join("")}</div>
    <div class="kpis">${kpi("Tracking error (asignación vigente)", pct(A.tracking_error, 2), `${A.n_obs} meses`)}${kpi("Exceso anual", spct(A.exceso_anual, 2), `${pct(A.retorno_portafolio_anual, 1)} vs ${pct(A.retorno_benchmark_anual, 1)}`)}${kpi("Information ratio", nf(A.information_ratio, 2), "exceso / TE")}${kpi("Beta", nf(A.beta, 2), `correlación ${nf(A.correlacion, 2)}`)}${kpi("Hit ratio", pct(A.hit_ratio, 0), "meses sobre el benchmark")}</div>
    <div class="g2"><div class="tile"><h3>¿De dónde viene el tracking error?</h3><div class="chart" id="ted"></div></div><div class="tile"><h3>Tracking error rolling 36 meses</h3><div id="ter" style="height:220px"></div></div></div>
    <div class="tile"><h3>Cada fondo contra su índice pasivo (60 meses)</h3><div class="tw"><table class="dt"><thead><tr><th>Fondo</th><th>Índice</th><th>Meses</th><th>Retorno</th><th>Índice</th><th>Exceso</th><th>TE</th><th>IR</th><th>Beta</th></tr></thead><tbody>${VEH.map(k => { const p = PF[k], ix = { MM: "sí mismo", RF: "sí mismo", RVG: "sí mismo", RVL: "S&P/CLX IPSA", DP: "money market (sustituto)" }[k]; if (!p || p.nota) return `<tr><td>${k}</td><td>${ix}</td><td colspan="7" class="tx helper">${p ? esc(p.nota) : ""}</td></tr>`; return `<tr><td>${k}</td><td>${ix}</td><td class="n">${p.n_obs}</td><td class="n">${pct(p.retorno_portafolio_anual, 1)}</td><td class="n">${pct(p.retorno_benchmark_anual, 1)}</td><td class="n">${spct(p.exceso_anual, 1)}</td><td class="n">${pct(p.tracking_error, 2)}</td><td class="n">${nf(p.information_ratio, 2)}</td><td class="n">${nf(p.beta, 2)}</td></tr>`; }).join("")}</tbody></table></div></div>
    ${RR ? `<div class="notif warn"><span>${si("atencion", "TE realizado")}</span><span>Entre ${fmonth(RR.desde.slice(0, 7))} y ${fmonth(RR.hasta.slice(0, 7))} la cartera rindió ${pct(RR.retorno_portafolio_anual, 2)} anual y el policy benchmark ${pct(RR.retorno_benchmark_anual, 2)}: exceso ${spct(RR.exceso_anual, 2)}. ${esc(RR.tracking_error_bloqueado || "")}</span></div>` : ""}`;
  const ent = Object.entries(A.descomposicion_te || {}).sort((a, b) => b[1] - a[1]), host = $("ted"), W = Math.max(300, host.clientWidth), m = { t: 6, r: 60, b: 20, l: 170 }, H = m.t + m.b + 30 * ent.length;
  const lo = Math.min(0, ...ent.map(e => e[1])), hi = Math.max(1, ...ent.map(e => e[1])), x = v => m.l + (v - lo) / (hi - lo) * (W - m.l - m.r);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Aporte al tracking error" }, host); el("line", { x1: x(0), x2: x(0), y1: m.t, y2: H - m.b, stroke: css("--text-3") }, svg);
  const lab = { MM: "MM · money market", RF: "RF · corporativa", DP: "DP · facturas vs MM", RVL: "RVL · Falcom vs IPSA", RVG: "RVG · global", drift: "Desvío de pesos" };
  ent.forEach(([k, v], i) => { const cy = m.t + i * 30 + 15; txt(svg, m.l - 8, cy + 4, lab[k] || k, { "text-anchor": "end", style: `fill:${css("--text-2")}` }); el("rect", { x: Math.min(x(0), x(v)), y: cy - 9, width: Math.max(1, Math.abs(x(v) - x(0))), height: 18, fill: v < 0 ? css("--err") : css("--interactive") }, svg); txt(svg, Math.max(x(0), x(v)) + 6, cy + 4, pct(v, 1), { style: `fill:${css("--text")}` }); });
  if (hasLW() && A.te_rolling_36m) { const ch = baseChart($("ter")); ch.addSeries(LightweightCharts.LineSeries, { color: css("--interactive"), lineWidth: 2, priceFormat: { type: "custom", formatter: v => nf(v, 2) + "%", minMove: .01 } }).setData(A.te_rolling_36m.map(p => ({ time: p.hasta, value: p.te * 100 }))); ch.timeScale().fitContent(); cv.charts.ter = ch; }
};

/* ---------- Flujos ---------- */
CT.flujos = function (h, C) {
  const F = C.flujos, tipo = { aporte: "Aporte", retiro: "Retiro", transferencia_interna: "Transferencia interna", rebalanceo: "Rebalanceo" };
  h.innerHTML = `
    <div class="pagehead"><h2>Flujos del cliente</h2><p class="muted">Los externos (aportes y retiros) cambian el patrimonio y entran a la XIRR; los internos (transferencias entre metas y rebalanceos) no.</p></div>
    <div class="kpis">${kpi("Aportes externos", mm(F.aportes_externos), "capital inicial y mensuales")}${kpi("Retiros externos", mm(F.retiros_externos), "metas cumplidas")}${kpi("Transferencias internas", mm(F.transferencias_internas), "entre metas")}${kpi("Rotación por rebalanceo", mm(F.rotacion_rebalanceo), "movimientos internos")}${kpi("Ganancia neta", smm(F.ganancia_neta), "valor − aportes + retiros", F.ganancia_neta >= 0 ? " pos" : " neg")}</div>
    <div class="notif"><span>${si("info", "TWR y XIRR")}</span><span>${esc(F.lectura)}</span></div>
    <div class="g2"><div class="tile"><h3>Calendario de flujos esperados (IPS)</h3><div class="tw"><table class="dt"><thead><tr><th>Desde</th><th>Monto</th><th>Tipo</th><th>Recurrencia</th><th>Hasta</th><th>Meta</th></tr></thead><tbody>${F.calendario_esperado.map(f => `<tr><td>${fdate(f.fecha)}</td><td class="n${cls(f.monto)}">${nf(f.monto)}</td><td>${f.clasificacion}</td><td>${f.recurrencia}</td><td>${fdate(f.hasta)}</td><td>${f.meta ? esc(gname[f.meta] || f.meta) : "—"}</td></tr>`).join("")}</tbody></table></div></div>
      <div class="tile"><h3>Escalera de liquidez</h3><div class="tw"><table class="dt"><thead><tr><th>Plazo</th><th>Disponible</th><th>Obligaciones</th><th>LCR acumulado</th></tr></thead><tbody>${F.escalera_liquidez.map(r => `<tr><td>${r.bucket}</td><td class="n">${mm(r.activos_disponibles)}</td><td class="n">${mm(r.obligaciones)}</td><td class="n">${r.lcr_acumulado == null ? "no aplica" : nf(r.lcr_acumulado, 1) + "×"}</td></tr>`).join("")}</tbody></table></div><p class="helper">LCR hasta 12 meses; lo más lejano lo mide la probabilidad de las metas.</p></div></div>
    <details class="tile"><summary style="cursor:pointer"><h4 style="display:inline">Libro de flujos completo (${F.libro.length})</h4></summary><div class="tw" style="margin-top:12px"><table class="dt"><thead><tr><th>Fecha</th><th>Tipo</th><th>Meta</th><th>Monto CLP</th><th>Externo</th><th style="text-align:left">Detalle</th></tr></thead><tbody>${F.libro.map(e => `<tr><td>${fdate(e.fecha)}</td><td>${tipo[e.tipo] || e.tipo}</td><td>${esc(gname[e.meta] || e.meta)}</td><td class="n${cls(e.monto)}">${nf(e.monto)}</td><td>${e.externo ? "sí" : "no"}</td><td class="tx helper">${esc(e.detalle.motivo || (e.detalle.alternativa ? "alternativa " + e.detalle.alternativa : ""))}</td></tr>`).join("")}</tbody></table></div></details>`;
};

/* ---------- Decisiones ---------- */
CT.decisiones = function (h, C) {
  const toH = l => (l || []).map(t => `<div class="to"><b>${esc(t.conflicto)}</b><div class="cols"><div><span class="pos">Mejora</span><ul>${t.mejora.map(s => `<li>${esc(s)}</li>`).join("")}</ul></div><div><span class="neg">Empeora</span><ul>${t.empeora.map(s => `<li>${esc(s)}</li>`).join("")}</ul></div></div></div>`).join("");
  h.innerHTML = `
    <div class="pagehead"><h2>Decisiones</h2><p class="muted" style="max-width:96ch">Cada decisión pasó por un Decision Case. El rebalanceo genera las alternativas evaluables, muestra sus trade-offs sin ponderarlos y la Recommendation Layer decide si hay evidencia para Nivel 3. El sistema no ejecuta ni asigna quién decide (DF v1.1).</p></div>
    ${C.rebalanceos.length ? C.rebalanceos.map(r => `<div class="tile"><div class="th"><h3>${fdate(r.fecha)} · ${esc(gname[r.meta] || r.meta)}</h3>${si(r.nivel === 3 ? "ok" : "atencion", "Nivel " + r.nivel)}</div>
      <p class="helper">Mayor desvío ${spct(r.desvio, 1)} en ${r.vehiculo}. Criterio: ${esc(r.criterio)}. Decisión del WM (simulada): ${r.recomendada || "A"}.${Object.keys(r.descartadas || {}).length ? " No se presenta: " + Object.entries(r.descartadas).map(([k, m]) => `${k} (${esc(m)})`).join("; ") + "." : ""}</p>
      <div class="tw"><table class="dt"><thead><tr><th>Alternativa</th><th>Rotación</th><th>Desvío restante</th><th>Vol ex-ante</th><th>Escenario adverso</th><th>Prob. meta</th><th>Admisible</th></tr></thead><tbody>${Object.entries(r.alternativas).map(([k, a]) => `<tr class="${k === r.recomendada ? "hl" : ""}"><td class="tx"><b>${k}</b> · ${esc(a.nombre)}${k === r.recomendada ? " " + si("ok", "Recomendada") : ""}</td><td class="n">${mm(a.rotacion_clp)}</td><td class="n">${pct(a.mayor_desvio_restante, 1)}</td><td class="n">${pct(a.volatilidad_ex_ante, 1)}</td><td class="n${cls(a.retorno_escenario_adverso)}">${spct(a.retorno_escenario_adverso, 1)}</td><td class="n">${a.prob_exito == null ? "—" : pct(a.prob_exito, 0)}</td><td>${a.admisible ? si("ok", "Sí") : si("alerta", "No") + `<div class="helper" style="white-space:normal">${esc(a.motivo_inadmisible)}</div>`}</td></tr>`).join("")}</tbody></table></div>
      <span class="lbl">Trade-offs frente a no rebalancear (se muestran, no se ponderan)</span>${toH(r.tradeoffs) || '<p class="helper">Sin conflictos.</p>'}<p class="helper">${esc(r.motivo_nivel || "")}</p></div>`).join("") : `<div class="notif"><span>${si("info", "Sin rebalanceos")}</span><span>Ninguna revisión superó la banda: cardinalidad cero es una respuesta válida (DF 4.2).</span></div>`}
    <div class="tile"><h3>Línea de tiempo completa</h3><ol class="timeline">${C.noticias.map(n => { const s = CAT_STYLE[n.categoria] || CAT_STYLE.Cierre; return `<li><span class="nb" style="--bc:var(${s.c});height:24px;min-width:24px">${n.quiet ? "·" : n.n}</span><div><div style="display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center"><span class="helper num">${fdate(n.fecha)}</span><span class="tag ${n.quiet ? "" : "info"}">${esc(n.categoria)}</span><b>${esc(n.titulo)}</b><button class="link" data-goto-tab="grafico" data-news="${n.id}">Ver en el gráfico</button></div><p class="muted" style="margin-top:4px;max-width:100ch">${esc(n.texto)}</p></div></li>`; }).join("")}</ol></div>`;
};

/* ---------- Datos y supuestos ---------- */
CT.datos = function (h, C) {
  const cnt = s => C.catalogo.filter(r => r.estado === s).length, I = C.ips, DQ = L.calidad_datos;
  const stP = { available: ["ok", "Disponible"], degraded: ["atencion", "Degradada"], missing_non_critical: ["atencion", "Falta"], missing_critical: ["alerta", "Falta"] };
  let lastG = "";
  h.innerHTML = `
    <div class="pagehead"><h2>Datos y supuestos</h2><p class="muted">Qué información usa el sistema, cuál falta y qué valores son de simulación.</p></div>
    <div class="kpis">${kpi("Variables", C.catalogo.length, "exigidas por la metodología")}${kpi("Disponibles", cnt("available"), "dato real")}${kpi("Degradadas", cnt("degraded"), "simulación o parcial")}${kpi("Faltan, advierten", cnt("missing_non_critical"), "el cálculo sigue con nota")}${kpi("Faltan, bloquean", cnt("missing_critical"), "el indicador no se muestra")}</div>
    <div class="tile"><h3>Variables de asesoría</h3><div class="tw"><table class="dt"><thead><tr><th>Variable</th><th>Criticidad</th><th>Estado</th><th>Si falta</th><th style="text-align:left">Habilita</th><th style="text-align:left">Fuente</th></tr></thead><tbody>${C.catalogo.map(r => { const g = r.grupo !== lastG ? `<tr class="grp"><td colspan="6">${esc(r.grupo)}</td></tr>` : ""; lastG = r.grupo; const [s, l] = stP[r.estado]; return g + `<tr><td class="tx">${esc(r.variable)}</td><td>${{ CRITICAL: "Crítica", "NON-CRITICAL": "Importante", COMPLEMENTARIO: "Complementaria" }[r.criticidad]}</td><td>${si(s, l)}</td><td>${r.estado.startsWith("missing") ? (r.comportamiento === "BLOQUEO" ? "Bloqueo" : "Advertencia") : "—"}</td><td class="tx">${esc(r.habilita)}</td><td class="tx helper">${esc(r.fuente_doc)}</td></tr>`; }).join("")}</tbody></table></div></div>
    <div class="g2">
      <div class="tile"><h3>IPS</h3><dl class="kv">${[["IPS", I.id + " (sintético)"], ["Vigencia", `${fdate(I.vigente_desde)} a ${fdate(I.revisar_antes_de)}`], ["Tolerancia", I.tolerancia], ["Capacidad", I.capacidad || "sin dato"], ["Límite de volatilidad", I.limites.vol == null ? "sin dato" : I.limites.vol + "%"], ["Límite VaR 95% 1m", I.limites.var == null ? "sin dato" : I.limites.var + "%"], ["Límite ES 95% 1m", I.limites.es == null ? "sin dato" : I.limites.es + "%"], ["Caída tolerada", I.limites.dd == null ? "sin dato" : I.limites.dd + "%"], ["Límite por administradora", I.admin_max == null ? "sin dato" : I.admin_max + "%"], ["Patrimonio total", I.patrimonio == null ? "sin dato" : mm(I.patrimonio)], ["Inversiones fuera de AFI", I.fuera_afi == null ? "sin dato" : mm(I.fuera_afi)]].map(([a, b]) => `<dt>${a}</dt><dd>${esc(b)}</dd>`).join("")}</dl></div>
      <div class="tile"><h3>Life balance sheet</h3>${I.lbs ? `<dl class="kv">${[["Capital humano", I.lbs.capital_humano], ["Activos no financieros", I.lbs.activos_no_financieros], ["Pasivos", I.lbs.pasivos], ["Compromisos futuros", I.lbs.compromisos_futuros], ["Cartera en AFI", C.resumen.valor_final]].map(([a, b]) => `<dt>${a}</dt><dd class="num">${mm(b)}</dd>`).join("")}</dl>` : `<div class="notif warn"><span>${si("sin_datos", "Sin datos")}</span><span>El IPS no trae balance de vida: el límite de ilíquidos no se puede calcular (QM IX).</span></div>`}</div>
    </div>
    <div class="tile"><h3>Calidad de datos (ESFS 8.4)</h3><p class="helper">${esc(DQ.regla)}</p><div class="tw"><table class="dt"><thead><tr><th>Serie</th><th>Estado</th><th style="text-align:left">Saltos que se revierten</th><th style="text-align:left">Valor cuota repetido</th><th>Impacto en vol 36m</th></tr></thead><tbody>${Object.entries(DQ.series).map(([k, s]) => { const im = s.impacto_36m; return `<tr><td>${k}</td><td>${si(s.estado === "available" ? "ok" : "atencion", { available: "Disponible", degraded: "Degradada", pending_validation: "Por validar" }[s.estado])}</td><td class="tx helper">${s.outliers.length ? s.outliers.map(o => `${fdate(o.fecha)}: ${spct(o.retorno, 2)} y luego ${spct(o.reversion, 2)}`).join("<br>") : "—"}</td><td class="tx helper">${s.stale.length ? s.stale.map(r => `${fdate(r.desde)} a ${fdate(r.hasta)} (${r.n_obs})`).join("<br>") : "—"}</td><td class="n">${!im ? "—" : im.n_en_ventana ? `${pct(im.vol_con, 2)} → ${pct(im.vol_sin, 2)}` : "fuera de ventana"}</td></tr>`; }).join("")}</tbody></table></div></div>
    <div class="g2">
      <div class="tile"><h3>Universo</h3><div class="tw"><table class="dt"><thead><tr><th>Clave</th><th style="text-align:left">Fondo</th><th>Liquidez</th></tr></thead><tbody>${VEH.map(k => { const u = L.universo[k]; return `<tr><td><span class="sw" style="--c:${vc(k)}"></span>${k}</td><td class="tx">${esc(u.nombre)}<br><span class="helper">${esc(u.clase)} · ${esc(u.subclase)} · RUN ${esc(u.rut)}${u.precio_mercado ? "" : " · sin precio de mercado"}</span></td><td>${esc(u.liquidez)}</td></tr>`; }).join("")}</tbody></table></div></div>
      <div class="tile"><h3>Lo que no se modela o se declara</h3><ul class="plain muted"><li>Sin costos de transacción ni impuestos: cada rebalanceo lo advierte.</li><li>El WM es simulado: acepta la alternativa recomendada.</li><li>Volatilidad y TE realizados no se informan con menos de 36 meses; se usan ex-ante y la asignación vigente.</li><li>Facturas no tiene índice público: el benchmark usa money market (parcial). Su valor cuota está suavizado.</li><li>La serie diaria mantiene las cuotas fijas entre cierres de mes.</li><li>Montos en pesos nominales: el Monte Carlo no simula inflación ni moneda (Vol. III-B lo pide).</li></ul></div>
    </div>
    <details class="tile"><summary style="cursor:pointer"><h4 style="display:inline">Parámetros de simulación</h4></summary><div class="tw" style="margin-top:12px"><table class="dt"><tbody>${Object.entries(L.parametros).map(([k, v]) => `<tr><td class="num">${k}</td><td class="tx">${esc(typeof v === "object" ? Object.entries(v).map(([a, b]) => `${a} ${b}`).join(" · ") : String(v))}</td></tr>`).join("")}</tbody></table></div></details>`;
};
