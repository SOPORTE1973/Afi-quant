/* Mesa Central — constructor de presentaciones para clientes (QM XIX: mismo número, otro vocabulario;
   QM XX: el sistema no comunica al cliente, libera el asesor; QM XXI: cada liberación queda registrada). */
"use strict";
const SLIDES = [
  { id: "portada", t: "Portada", d: "Nombre, fecha de los datos y asesor", fixed: true },
  { id: "resumen", t: "Su patrimonio hoy", d: "Valor, aportes, ganancia y rentabilidad" },
  { id: "evolucion", t: "Cómo ha evolucionado", d: "Patrimonio por fondo mes a mes" },
  { id: "metas", t: "Sus metas", d: "Probabilidad de lograr cada una" },
  { id: "cartera", t: "Cómo está invertido", d: "Distribución actual y objetivo" },
  { id: "rentabilidad", t: "Rentabilidad frente a su referencia", d: "Cartera frente a su benchmark" },
  { id: "riesgo", t: "Qué pasaría en un mal escenario", d: "Escenarios y episodios históricos" },
  { id: "crisis", t: "Si se repitiera una crisis", d: "La peor crisis histórica con su cartera actual" },
  { id: "movimientos", t: "Sus aportes y retiros", d: "Flujos y retorno personal" },
  { id: "decisiones", t: "Lo que hicimos en el período", d: "Revisiones y rebalanceos" },
  { id: "proximos", t: "Próximos pasos", d: "Texto que escribe el asesor" },
  { id: "aviso", t: "Supuestos, riesgos y aviso", d: "Cómo se calcularon las cifras", fixed: true },
];
const DEFAULT_ON = ["portada", "resumen", "evolucion", "metas", "cartera", "riesgo", "crisis", "proximos", "aviso"];
const PAL = { MM: "6929C4", RF: "1192E8", DP: "005D5D", RVL: "9F1853", RVG: "FA4D56" };
const pres = { order: [], on: new Set(), idx: 0, notes: "", C: null, client: null };

function deckModel(C) {
  const S = C.resumen, last = C.construccion.momentos[C.construccion.momentos.length - 1];
  return {
    id: C.id, nombre: C.cliente.nombre, asesor: C.asesor, onboarding: C.onboarding,
    r: { valor: S.valor_final, aportado: S.aportado, retirado: S.retirado, twr: S.twr, twr_anual: S.twr_anual, xirr: S.xirr, meses: S.meses, pesos: S.pesos_actuales, politica: S.pesos_politica },
    metas: C.cliente.metas.map(g => { const m = C.metas_cierre[g.key] || {}; return { ...g, estado: g.cerrada ? "cumplida" : "activa", prob: m.prob_exito ?? null, cobertura: m.cobertura ?? null, p50: m.p50, valor: S.valor_por_meta[g.key] }; }),
    sleeves: last.sleeves,
    stress: { ...C.stress.hipoteticos, ...C.stress.historicos },
    flujos: C.flujos, rel: C.relativo.realizado, noticias: C.noticias, ts: C.ts,
    faltantes: C.catalogo.filter(r => r.estado === "missing_critical").map(r => r.variable),
    crisis: Object.values(C.stress.historicos).filter(e => e.trayectoria).sort((a, b) => a.trayectoria.caida_maxima - b.trayectoria.caida_maxima)[0] || null,
    ddIPS: C.ips.limites.dd,
  };
}
function loadSel() {
  const saved = store.get("pres-" + pres.client, null);
  pres.order = saved && saved.order ? saved.order.filter(id => SLIDES.some(s => s.id === id)) : SLIDES.map(s => s.id);
  SLIDES.forEach(s => { if (!pres.order.includes(s.id)) pres.order.push(s.id); });
  pres.on = new Set(saved && saved.on ? saved.on : DEFAULT_ON); SLIDES.filter(s => s.fixed).forEach(s => pres.on.add(s.id));
  pres.order = ["portada", ...pres.order.filter(x => x !== "portada" && x !== "aviso"), "aviso"];
  pres.notes = store.get("notes-" + pres.client, "");
}
const saveSel = () => store.set("pres-" + pres.client, { order: pres.order, on: [...pres.on] });
const chosen = () => pres.order.filter(id => pres.on.has(id));
const monthIdx = ts => { const o = [], f = ts.fechas; for (let i = 0; i < f.length; i++) if (i === f.length - 1 || f[i].slice(0, 7) !== f[i + 1].slice(0, 7)) o.push(i); return o; };
function goalSentence(g) {
  if (g.estado === "cumplida") return `Meta cumplida el ${fdate(g.fecha)}.`;
  if (g.fecha == null) return `Reserva disponible: cubre el ${pct(g.cobertura, 0)} del monto definido.`;
  return `En ${Math.round(g.prob * 100)} de cada 100 escenarios simulados se alcanza la meta${g.prob_deseada != null ? ` (usted pidió al menos ${Math.round(g.prob_deseada * 100)})` : ""}.`;
}
function slideHTML(id, c, num, total) {
  const r = c.r, rl = retLabel(r), gain = r.valor - r.aportado + r.retirado;
  const foot = `<div class="foot"><span>${esc(c.nombre)} · datos al ${fdate(L.as_of)}</span><span>Cliente ficticio · simulación</span><span>${num} / ${total}</span></div>`;
  const wrap = (k, t, b) => `<div class="slide"><div class="in"><div><div class="kick">${k}</div><h2>${t}</h2></div><div class="body">${b}</div>${foot}</div></div>`;
  const tiles = arr => `<div class="tiles" style="grid-template-columns:repeat(${arr.length},1fr)">${arr.map(([l, v]) => `<div class="tl"><span>${l}</span><b class="big">${v}</b></div>`).join("")}</div>`;
  switch (id) {
    case "portada": return `<div class="slide cover"><div class="in"><div style="display:grid;gap:1.4cqw;align-content:end"><div class="kick">Revisión de su patrimonio</div><h1>${esc(c.nombre)}</h1><div style="font-size:1.7cqw;color:#c6c6c6">Datos al ${fdate(L.as_of)} · ${esc(c.asesor)}</div></div><div></div>${foot}</div></div>`;
    case "resumen": return wrap("Resumen", "Su patrimonio hoy", tiles([["Valor actual", mm(r.valor)], ["Aportado (neto)", mm(r.aportado - r.retirado)], ["Ganancia", mm(gain)], [rl.l, rl.v]]) + `<p>Desde ${fmonth(c.onboarding.slice(0, 7))} usted aportó ${mm(r.aportado)} y retiró ${mm(r.retirado)}. Hoy su cartera vale ${mm(r.valor)}: una ganancia de ${mm(gain)}.</p><p style="color:#525252">${rl.l}: ${rl.v} (${esc(rl.n)}). Considerando cuándo hizo cada aporte, su retorno personal fue ${pct(r.xirr, 1)} anual.</p>`);
    case "evolucion": return wrap("Evolución", "Cómo ha evolucionado su patrimonio", evoSVG(c) + `<div style="display:flex;gap:2cqw;flex-wrap:wrap;font-size:1.2cqw">${VEH.filter(k => c.ts.veh[k].some(x => x > 0)).map(k => `<span><i style="display:inline-block;width:1.2cqw;height:1.2cqw;background:#${PAL[k]};margin-right:.5cqw"></i>${VNAME[k]}</span>`).join("")}<span>- - - Aportes netos</span></div>`);
    case "metas": return wrap("Metas", "Sus metas", `<table><thead><tr><th>Meta</th><th>Monto</th><th>Fecha</th><th>Hoy</th><th>Probabilidad</th></tr></thead><tbody>${c.metas.map(g => `<tr><td>${esc(g.nombre)}</td><td>${mm(g.objetivo)}</td><td>${g.fecha ? fdate(g.fecha) : "siempre disponible"}</td><td>${g.estado === "cumplida" ? "cumplida" : mm(g.valor)}</td><td>${g.estado === "cumplida" ? "—" : g.prob == null ? (g.cobertura == null ? "—" : "cubierta " + pct(g.cobertura, 0)) : pct(g.prob, 0)}</td></tr>`).join("")}</tbody></table><div style="display:grid;gap:.8cqw">${c.metas.map(g => `<p><b>${esc(g.nombre)}.</b> ${goalSentence(g)}</p>`).join("")}</div>`);
    case "cartera": return wrap("Cartera", "Cómo está invertido", `<div class="row2"><div>${allocSVG(r.pesos, r.politica)}</div><div style="display:grid;gap:1cqw">${Object.entries(c.sleeves).map(([g, s]) => { const goal = c.metas.find(x => x.key === g); return `<p><b>${esc(goal ? goal.nombre : g)}:</b> ${Object.entries(s.pesos).sort((a, b) => b[1] - a[1]).map(([k, w]) => `${VNAME[k].toLowerCase()} ${pct(w, 0)}`).join(", ")}.</p>`; }).join("")}<p style="color:#525252">Cada meta tiene su propia cartera según su plazo: lo que se necesita pronto va en instrumentos estables; lo de largo plazo puede asumir más variación.</p></div></div>`);
    case "rentabilidad": { const b = c.rel; if (!b) return wrap("Rentabilidad", "Rentabilidad frente a su referencia", "<p>Aún no hay datos suficientes.</p>"); return wrap("Rentabilidad", "Rentabilidad frente a su referencia", tiles([["Su cartera (anual)", pct(b.retorno_portafolio_anual, 1)], ["Su referencia (anual)", pct(b.retorno_benchmark_anual, 1)], ["Diferencia", spct(b.exceso_anual, 1)]]) + `<p>La referencia combina índices con la misma distribución objetivo que su cartera. Entre ${fmonth(b.desde.slice(0, 7))} y ${fmonth(b.hasta.slice(0, 7))} su cartera la superó en ${pct(b.hit_ratio, 0)} de los meses.</p><p style="color:#525252">Todavía no hay 36 meses de historia para medir cuánto se aparta de forma estable de su referencia.</p>${r.meses < 12 ? `<p style="color:#8e6a00">Con menos de 12 meses, las cifras anuales son una extrapolación; la rentabilidad acumulada es ${pct(r.twr, 1)}.</p>` : ""}`); }
    case "riesgo": { const pick = ["adverso", "stress", "covid", "estallido"].filter(k => c.stress[k]).map(k => c.stress[k]); return wrap("Riesgo", "Qué pasaría en un mal escenario", `<div class="row2"><div>${stressSVG(pick)}</div><div style="display:grid;gap:1cqw">${pick.map(s => `<p><b>${esc(s.nombre)}:</b> su cartera ${s.retorno < 0 ? "bajaría" : "subiría"} ${pct(Math.abs(s.retorno), 1)} (${mm(Math.abs(s.pnl_clp))}).</p>`).join("")}<p style="color:#525252">Adverso y Stress son supuestos a 12 meses; los otros repiten lo que ocurrió en esos episodios con su cartera actual.</p></div></div>`); }
    case "crisis": { const e = c.crisis; if (!e) return wrap("Crisis", "Si se repitiera una crisis", "<p>No hay episodios con datos.</p>"); const t = e.trayectoria;
      return wrap("Crisis", `Si se repitiera: ${esc(e.nombre)}`, `<div class="row2"><div>${crisisSVG(c)}</div><div style="display:grid;gap:1cqw"><p>Si su cartera de hoy hubiera vivido ${esc(e.nombre)} (${fdate(e.desde)} a ${fdate(e.hasta)}), habría bajado hasta ${pct(-t.caida_maxima, 1)} (${mm(-t.caida_maxima * t.valor_inicial)}) en ${t.dias_hasta_fondo} días.</p><p>${t.fecha_recuperacion ? `Habría recuperado su valor ${t.dias_recuperacion} días después del punto más bajo, sin vender.` : "No habría recuperado su valor dentro del año siguiente."}</p>${c.ddIPS != null ? `<p style="color:#525252">La caída máxima que usted acordó tolerar es ${nf(c.ddIPS)}%: esta crisis ${-t.caida_maxima * 100 > c.ddIPS ? "la superaría" : "quedaría dentro"}.</p>` : ""}<p style="color:#525252">Es la peor de las crisis recientes para esta cartera; no predice la próxima.</p></div></div>`); }
    case "movimientos": return wrap("Flujos", "Sus aportes y retiros", tiles([["Aportes", mm(c.flujos.aportes_externos)], ["Retiros", mm(c.flujos.retiros_externos)], ["Ganancia neta", mm(c.flujos.ganancia_neta)]]) + `<p>La rentabilidad de la cartera (${r.meses >= 12 ? pct(r.twr_anual, 1) + " anual" : pct(r.twr, 1) + " acumulada"}) mide cómo se gestionó el dinero. Su retorno personal (${pct(r.xirr, 1)} anual) incluye además el momento en que usted aportó o retiró.</p>`);
    case "decisiones": { const ns = c.noticias.filter(n => !n.quiet && n.categoria !== "Cierre"); return wrap("Gestión", "Lo que hicimos en el período", `<table><thead><tr><th>Fecha</th><th>Qué</th><th style="text-align:left">Detalle</th></tr></thead><tbody>${ns.slice(-7).map(n => `<tr><td>${fdate(n.fecha)}</td><td>${esc(n.categoria)}</td><td style="text-align:left">${esc(n.titulo)}</td></tr>`).join("")}</tbody></table><p style="color:#525252">Revisamos su cartera ${c.noticias.filter(n => n.categoria === "Rebalanceo" || n.categoria === "Sin operar").length} veces; en ${c.noticias.filter(n => n.categoria === "Rebalanceo").length} se ajustó la distribución porque se había alejado de su objetivo.</p>`); }
    case "proximos": return wrap("Próximos pasos", "Próximos pasos", `<textarea data-notes aria-label="Próximos pasos">${esc(pres.notes || "")}</textarea>`);
    case "aviso": return wrap("Aviso", "Supuestos, riesgos y aviso", `<div style="display:grid;gap:.9cqw;font-size:1.3cqw"><p>Cifras al ${fdate(L.as_of)}, calculadas con los valores cuota de cada fondo (dividendos reinvertidos). La rentabilidad de la cartera no considera el momento de sus aportes; el retorno personal sí.</p><p>Las probabilidades de las metas vienen de 5.000 escenarios simulados con supuestos de mercado; no son una promesa. Los escenarios adversos son hipotéticos o repiten episodios pasados.</p><p>Rentabilidades pasadas no garantizan rentabilidades futuras. Las inversiones pueden perder valor.</p><p>Faltan datos que limitan algunos análisis: ${esc(c.faltantes.slice(0, 3).join("; ") || "ninguno crítico")}.</p><p>Este documento lo revisa y presenta su asesor; no es una recomendación automática. <b>Cliente y supuestos ficticios: material de simulación.</b></p></div>`);
  }
  return "";
}
function evoSVG(c) {
  const idx = monthIdx(c.ts), W = 1000, H = 330, m = { l: 70, r: 20, t: 10, b: 30 };
  const tot = idx.map(i => VEH.reduce((a, k) => a + c.ts.veh[k][i], 0)), ymax = Math.max(...tot, ...idx.map(i => c.ts.neto[i])) * 1.08;
  const x = j => m.l + j / Math.max(1, idx.length - 1) * (W - m.l - m.r), y = v => m.t + (1 - v / ymax) * (H - m.t - m.b);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Patrimonio por fondo mes a mes">`;
  for (let t = 0; t <= 4; t++) { const v = ymax * t / 4; s += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="#e0e0e0"/><text x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end" font-size="13">${nf(v / 1e6, 0)}M</text>`; }
  const cum = idx.map(() => 0);
  VEH.forEach(k => { const lo = cum.slice(); idx.forEach((i, j) => cum[j] += c.ts.veh[k][i]); if (!c.ts.veh[k].some(v => v > 0)) return;
    s += `<path d="${idx.map((i, j) => `${j ? "L" : "M"}${x(j)},${y(cum[j])}`).join("")}${idx.map((i, j) => `L${x(idx.length - 1 - j)},${y(lo[idx.length - 1 - j])}`).join("")}Z" fill="#${PAL[k]}"/>`; });
  s += `<path d="${idx.map((i, j) => `${j ? "L" : "M"}${x(j)},${y(c.ts.neto[i])}`).join("")}" fill="none" stroke="#161616" stroke-width="2.5" stroke-dasharray="7 5"/>`;
  const step = Math.max(1, Math.ceil(idx.length / 7)); idx.forEach((i, j) => { if (j % step === 0) s += `<text x="${x(j)}" y="${H - 8}" text-anchor="middle" font-size="13">${fmonth(c.ts.fechas[i].slice(0, 7))}</text>`; });
  return s + "</svg>";
}
function crisisSVG(c) {
  const t = c.crisis.trayectoria, v0 = t.valor_inicial, N = t.total.length, W = 520, H = 300, m = { l: 60, r: 14, t: 14, b: 26 };
  const lo = Math.min(...t.total, c.ddIPS != null ? v0 * (1 - c.ddIPS / 100) : Infinity) * .97, hi = Math.max(...t.total, v0) * 1.02;
  const x = i => m.l + i / (N - 1) * (W - m.l - m.r), y = v => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Valor de la cartera durante la crisis">`;
  [lo, (lo + hi) / 2, hi].forEach(v => { s += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="#e0e0e0"/><text x="${m.l - 6}" y="${y(v) + 4}" text-anchor="end" font-size="12">${nf(v / 1e6, 0)}M</text>`; });
  s += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v0)}" y2="${y(v0)}" stroke="#525252" stroke-dasharray="6 4"/>`;
  if (c.ddIPS != null) { const yl = y(v0 * (1 - c.ddIPS / 100)); s += `<line x1="${m.l}" x2="${W - m.r}" y1="${yl}" y2="${yl}" stroke="#da1e28" stroke-dasharray="6 4"/><text x="${W - m.r}" y="${yl - 5}" text-anchor="end" font-size="12" fill="#da1e28">caída tolerada</text>`; }
  const line = t.total.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join("");
  s += `<path d="${line}L${x(N - 1)},${y(lo)}L${x(0)},${y(lo)}Z" fill="#0f62fe" fill-opacity=".12"/><path d="${line}" fill="none" stroke="#0f62fe" stroke-width="2.5"/>`;
  const iT = t.total.indexOf(Math.min(...t.total));
  s += `<circle cx="${x(iT)}" cy="${y(t.total[iT])}" r="5" fill="#da1e28"/><text x="${x(iT)}" y="${y(t.total[iT]) + 20}" text-anchor="middle" font-size="13" fill="#161616">${spct(t.caida_maxima, 1)}</text>`;
  s += `<text x="${m.l}" y="${H - 6}" font-size="12">${fdate(t.fechas[0])}</text><text x="${W - m.r}" y="${H - 6}" text-anchor="end" font-size="12">${fdate(t.fechas[N - 1])}</text>`;
  return s + "</svg>";
}
function allocSVG(w, p) {
  const ks = VEH.filter(k => (w[k] || 0) > 0 || (p[k] || 0) > 0), W = 520, rh = 46, H = ks.length * rh + 30, l = 170;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribución actual y objetivo">`;
  ks.forEach((k, i) => { const cy = i * rh + 20; s += `<text x="0" y="${cy + 5}" font-size="15">${VNAME[k]}</text><rect x="${l}" y="${cy - 9}" width="${(W - l - 60) * (w[k] || 0)}" height="18" fill="#${PAL[k]}"/><line x1="${l + (W - l - 60) * (p[k] || 0)}" x2="${l + (W - l - 60) * (p[k] || 0)}" y1="${cy - 14}" y2="${cy + 14}" stroke="#161616" stroke-width="2.5"/><text x="${W - 50}" y="${cy + 5}" font-size="15">${pct(w[k] || 0, 0)}</text>`; });
  return s + `<text x="${l}" y="${H - 4}" font-size="12">Barra: hoy · línea: objetivo</text></svg>`;
}
function stressSVG(list) {
  const W = 520, rh = 54, H = list.length * rh + 10, mid = 260, ext = Math.max(...list.map(s => Math.abs(s.retorno))) || 1;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Variación de la cartera por escenario"><line x1="${mid}" x2="${mid}" y1="0" y2="${H}" stroke="#8d8d8d"/>`;
  list.forEach((sc, i) => { const cy = i * rh + 28, w = Math.abs(sc.retorno) / ext * 200, x0 = sc.retorno < 0 ? mid - w : mid;
    s += `<text x="${sc.retorno < 0 ? mid + 10 : mid - 10}" y="${cy - 14}" text-anchor="${sc.retorno < 0 ? "start" : "end"}" font-size="14">${esc(sc.nombre)}</text><rect x="${x0}" y="${cy - 6}" width="${w}" height="20" fill="${sc.retorno < 0 ? "#da1e28" : "#0f62fe"}"/><text x="${sc.retorno < 0 ? x0 - 8 : x0 + w + 8}" y="${cy + 9}" text-anchor="${sc.retorno < 0 ? "end" : "start"}" font-size="15" fill="#161616">${spct(sc.retorno, 1)}</text>`; });
  return s + "</svg>";
}

RENDER.pres = async function () {
  const host = $("v-pres");
  if (!pres.client) pres.client = app.client;
  host.innerHTML = `<div class="pagehead"><span class="lbl">Presentaciones para clientes</span><div class="row"><h1>Arma la presentación</h1>
      <div style="display:flex;gap:8px;align-items:center"><label class="lbl" for="p-client">Cliente</label><select id="p-client" class="sel">${L.monitoreo.map(a => `<option value="${a.id}" ${a.id === pres.client ? "selected" : ""}>${esc(L.clientes[a.id].nombre)} (${a.id})</option>`).join("")}</select></div></div></div>
    <div class="builder"><div style="display:grid;gap:16px">
      <div class="tile"><h3>Láminas</h3><p class="helper">Marca lo que quieres mostrar y ordénalo. La portada y la lámina de supuestos y riesgos van siempre.</p><div class="catalog" id="catalog"></div></div>
      <div class="tile"><h3>Revisión y liberación</h3><p class="helper">El sistema no se comunica con el cliente. Quien presenta revisa y libera; queda registrado con fecha, láminas y datos usados.</p>
        <label style="display:flex;gap:8px;align-items:flex-start"><input type="checkbox" id="p-ack"> Revisé las cifras y el lenguaje, y comunicaré esta presentación yo mismo al cliente.</label>
        <label for="p-note" class="lbl">Nota para el registro (opcional)</label><textarea id="p-note" rows="2" style="border:0;border-bottom:1px solid var(--border-strong);background:var(--layer-2);padding:8px"></textarea>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="p-release">Liberar y descargar PPTX</button><button class="btn" id="p-present">Presentar en pantalla</button></div>
        <div id="p-msg" class="notif" hidden></div><h4>Liberaciones registradas</h4><div class="log" id="p-log"><div class="helper">Conectando con el registro compartido…</div></div></div>
    </div><div class="deck" id="deck"><div class="loading">Cargando cliente…</div></div></div>`;
  $("p-client").addEventListener("change", e => { pres.client = e.target.value; RENDER.pres(); });
  $("p-ack").addEventListener("change", e => { if (e.target.checked) $("p-msg").hidden = true; });
  $("p-present").addEventListener("click", () => { $("present").hidden = false; showPresent(0); const p = $("present"); if (p.requestFullscreen) p.requestFullscreen().catch(() => {}); });
  $("p-release").addEventListener("click", release);
  try { pres.C = deckModel(await loadClient(pres.client)); } catch (e) { $("deck").innerHTML = `<div class="notif err"><span>${si("alerta", "Error")}</span><span>${esc(e.message)}</span></div>`; return; }
  loadSel(); renderCatalog(); renderDeck(); renderLog();
};
function renderCatalog() {
  $("catalog").innerHTML = pres.order.map((id, i) => { const s = SLIDES.find(x => x.id === id), on = pres.on.has(id);
    // Láminas obligatorias: candado en vez de una casilla inactiva. Flechas solo donde se puede mover.
    const first = i <= 1, last = i >= pres.order.length - 2;
    return `<div class="sitem${on ? "" : " off"}">${s.fixed ? '<span aria-hidden="true" title="Lámina obligatoria" style="width:16px;text-align:center">🔒</span>' : `<input type="checkbox" id="chk-${id}" data-id="${id}" ${on ? "checked" : ""}>`}<label ${s.fixed ? "" : `for="chk-${id}"`}>${esc(s.t)}<small>${esc(s.d)}</small></label>${s.fixed ? '<span class="lock">obligatoria</span>' : `<span class="mv">${first ? '<span style="width:28px"></span>' : `<button data-up="${id}" aria-label="Subir ${esc(s.t)}">▲</button>`}${last ? '<span style="width:28px"></span>' : `<button data-down="${id}" aria-label="Bajar ${esc(s.t)}">▼</button>`}</span>`}</div>`; }).join("");
  document.querySelectorAll("#catalog input").forEach(cb => cb.addEventListener("change", () => { cb.checked ? pres.on.add(cb.dataset.id) : pres.on.delete(cb.dataset.id); saveSel(); renderCatalog(); renderDeck(); }));
  const mv = (id, d) => { const i = pres.order.indexOf(id), j = i + d; if (j < 1 || j > pres.order.length - 2) return; [pres.order[i], pres.order[j]] = [pres.order[j], pres.order[i]]; saveSel(); renderCatalog(); renderDeck(); };
  document.querySelectorAll("#catalog [data-up]").forEach(b => b.addEventListener("click", () => mv(b.dataset.up, -1)));
  document.querySelectorAll("#catalog [data-down]").forEach(b => b.addEventListener("click", () => mv(b.dataset.down, 1)));
}
function renderDeck() { const ids = chosen(); $("deck").innerHTML = ids.map((id, i) => slideHTML(id, pres.C, i + 1, ids.length)).join("");
  document.querySelectorAll("[data-notes]").forEach(t => t.addEventListener("input", () => { pres.notes = t.value; store.set("notes-" + pres.client, t.value); })); }
function showPresent(i) { const ids = chosen(); pres.idx = Math.max(0, Math.min(ids.length - 1, i)); $("present-slide").innerHTML = slideHTML(ids[pres.idx], pres.C, pres.idx + 1, ids.length); $("pn").textContent = `${pres.idx + 1} / ${ids.length}`; }
const closePresent = () => { $("present").hidden = true; if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); };
$("px").addEventListener("click", closePresent); $("pp").addEventListener("click", () => showPresent(pres.idx - 1)); $("pnx").addEventListener("click", () => showPresent(pres.idx + 1));
addEventListener("keydown", e => { if ($("present").hidden) return; if (e.key === "ArrowRight" || e.key === " ") showPresent(pres.idx + 1); if (e.key === "ArrowLeft") showPresent(pres.idx - 1); if (e.key === "Escape") closePresent(); });

/* Registro compartido (db) y descarga (downloads) */
let db = null, user = null, downloads = null, capsReady = false, logUnsub = null;
(async () => {
  try { db = await window.claude?.use?.("db"); } catch (e) {}
  try { user = await window.claude?.use?.("user"); } catch (e) {}
  try { downloads = await window.claude?.use?.("downloads"); } catch (e) {}
  capsReady = true; if (app.view === "pres" && $("p-log")) renderLog();
})();
const msg = (t, kind = "") => { const m = $("p-msg"); m.hidden = false; m.className = "notif " + kind; m.innerHTML = `<span>${si(kind === "err" ? "alerta" : kind === "ok" ? "ok" : "info", kind === "err" ? "Atención" : "Listo")}</span><span>${esc(t)}</span>`; };
function renderLog() {
  const box = $("p-log"); if (!box) return;
  if (!capsReady) return;
  if (!db) { box.innerHTML = '<div class="helper">El registro compartido no está disponible en esta vista.</div>'; return; }
  if (logUnsub) { logUnsub(); logUnsub = null; }
  logUnsub = db.collection("liberaciones").orderBy("fecha", "desc").limit(50).onSnapshot(async snap => {
    const rows = snap.docs.map(d => d.data()); let names = {};
    try { if (user) names = await user.profiles([...new Set(rows.map(r => r.por).filter(Boolean))]); } catch (e) {}
    const b = $("p-log"); if (!b) return;
    b.innerHTML = rows.length ? rows.map(r => `<div><b>${esc(r.cliente)}</b> · ${esc(new Date(r.fecha).toLocaleString("es-CL"))}<br><span class="helper">${esc((names[r.por] && names[r.por].name) || "Un asesor")} · ${r.laminas.length} láminas · datos al ${fdate(r.datos_al)}${r.nota ? " · " + esc(r.nota) : ""}</span></div>`).join("") : '<div class="helper">Todavía no hay presentaciones liberadas. La primera aparecerá aquí con quién la liberó y qué incluía.</div>';
  }, () => { const b = $("p-log"); if (b) b.innerHTML = '<div class="helper">No se pudo leer el registro compartido.</div>'; });
}
async function buildPptx(c, ids) {
  const P = new PptxGenJS(); P.layout = "LAYOUT_WIDE"; P.title = `Revisión de patrimonio · ${c.nombre}`;
  const FONT = "IBM Plex Sans", INK = "161616", MUT = "6F6F6F", ACC = "0F62FE";
  const r = c.r, rl = retLabel(r), gain = r.valor - r.aportado + r.retirado;
  ids.forEach((id, n) => {
    const s = P.addSlide();
    const head = (k, t) => { s.addText(k.toUpperCase(), { x: .6, y: .35, w: 12, h: .3, fontFace: FONT, fontSize: 11, color: ACC, charSpacing: 2 }); s.addText(t, { x: .6, y: .65, w: 12, h: .7, fontFace: FONT, fontSize: 28, color: INK }); };
    s.addText(`${c.nombre} · datos al ${fdate(L.as_of)}    ·    Cliente ficticio · simulación    ·    ${n + 1} / ${ids.length}`, { x: .6, y: 7, w: 12.1, h: .3, fontFace: FONT, fontSize: 9, color: MUT });
    const tiles = (arr, y = 1.6) => arr.forEach(([l, v], i) => { const w = 12.1 / arr.length - .2; s.addShape(P.ShapeType.rect, { x: .6 + i * (w + .2), y, w, h: 1.4, fill: { color: "F4F4F4" }, line: { color: "F4F4F4" } }); s.addText([{ text: l + "\n", options: { fontSize: 12, color: "525252" } }, { text: v, options: { fontSize: 26, color: INK } }], { x: .75 + i * (w + .2), y: y + .1, w: w - .3, h: 1.2, fontFace: FONT, valign: "middle" }); });
    const para = (t, y, h = .6, o = {}) => s.addText(t, Object.assign({ x: .6, y, w: 12.1, h, fontFace: FONT, fontSize: 15, color: "393939", valign: "top" }, o));
    if (id === "portada") { s.background = { color: "161616" }; s.addText("REVISIÓN DE SU PATRIMONIO", { x: .8, y: 2.4, w: 11, h: .4, fontFace: FONT, fontSize: 14, color: "78A9FF", charSpacing: 3 }); s.addText(c.nombre, { x: .8, y: 2.9, w: 11.5, h: 1.2, fontFace: FONT, fontSize: 44, color: "FFFFFF" }); s.addText(`Datos al ${fdate(L.as_of)} · ${c.asesor}`, { x: .8, y: 4.1, w: 11, h: .5, fontFace: FONT, fontSize: 18, color: "C6C6C6" }); return; }
    if (id === "resumen") { head("Resumen", "Su patrimonio hoy"); tiles([["Valor actual", mm(r.valor)], ["Aportado (neto)", mm(r.aportado - r.retirado)], ["Ganancia", mm(gain)], [rl.l, rl.v]]); para(`Desde ${fmonth(c.onboarding.slice(0, 7))} usted aportó ${mm(r.aportado)} y retiró ${mm(r.retirado)}. Hoy su cartera vale ${mm(r.valor)}: una ganancia de ${mm(gain)}.`, 3.4); para(`${rl.l}: ${rl.v} (${rl.n}). Considerando cuándo hizo cada aporte, su retorno personal fue ${pct(r.xirr, 1)} anual.`, 4.2, .6, { color: "525252" }); }
    if (id === "evolucion") { head("Evolución", "Cómo ha evolucionado su patrimonio"); const idx = monthIdx(c.ts), labels = idx.map(i => fmonth(c.ts.fechas[i].slice(0, 7))), ks = VEH.filter(k => c.ts.veh[k].some(v => v > 0));
      s.addChart(P.ChartType.area, ks.map(k => ({ name: VNAME[k], labels, values: idx.map(i => Math.round(c.ts.veh[k][i] / 1e5) / 10) })), { x: .6, y: 1.5, w: 12.1, h: 5.2, barGrouping: "stacked", chartColors: ks.map(k => PAL[k]), showLegend: true, legendPos: "b", legendFontSize: 11, catAxisLabelFontSize: 10, valAxisLabelFontSize: 10, valAxisLabelFormatCode: '#,##0"M"', catAxisLabelFrequency: Math.max(1, Math.ceil(idx.length / 8)) }); }
    if (id === "metas") { head("Metas", "Sus metas"); s.addTable([["Meta", "Monto", "Fecha", "Probabilidad"].map(t => ({ text: t, options: { bold: true, fill: { color: "F4F4F4" } } })), ...c.metas.map(g => [g.nombre, mm(g.objetivo), g.fecha ? fdate(g.fecha) : "siempre disponible", g.estado === "cumplida" ? "cumplida" : g.prob == null ? (g.cobertura == null ? "—" : "cubierta " + pct(g.cobertura, 0)) : pct(g.prob, 0)])], { x: .6, y: 1.5, w: 12.1, fontFace: FONT, fontSize: 13, color: INK, border: { type: "solid", color: "E0E0E0", pt: .75 } }); para(c.metas.map(g => `${g.nombre}. ${goalSentence(g)}`).join("\n"), 1.6 + .45 * (c.metas.length + 1) + .3, 2.5, { fontSize: 14 }); }
    if (id === "cartera") { head("Cartera", "Cómo está invertido"); const ks = VEH.filter(k => (r.pesos[k] || 0) > 0 || (r.politica[k] || 0) > 0);
      s.addChart(P.ChartType.bar, [{ name: "Hoy", labels: ks.map(k => VNAME[k]), values: ks.map(k => Math.round((r.pesos[k] || 0) * 1000) / 10) }, { name: "Objetivo", labels: ks.map(k => VNAME[k]), values: ks.map(k => Math.round((r.politica[k] || 0) * 1000) / 10) }], { x: .6, y: 1.5, w: 6.4, h: 5.2, barDir: "bar", chartColors: [ACC, "C6C6C6"], showLegend: true, legendPos: "b", valAxisLabelFormatCode: '0"%"', showValue: true, dataLabelFormatCode: '0"%"', dataLabelFontSize: 9 });
      s.addText(Object.entries(c.sleeves).map(([g, sl]) => { const goal = c.metas.find(x => x.key === g); return `${goal ? goal.nombre : g}: ${Object.entries(sl.pesos).sort((a, b) => b[1] - a[1]).map(([k, w]) => `${VNAME[k].toLowerCase()} ${pct(w, 0)}`).join(", ")}.`; }).join("\n\n") + "\n\nCada meta tiene su propia cartera según su plazo.", { x: 7.3, y: 1.6, w: 5.4, h: 5, fontFace: FONT, fontSize: 13, color: "393939", valign: "top" }); }
    if (id === "rentabilidad" && c.rel) { const b = c.rel; head("Rentabilidad", "Rentabilidad frente a su referencia"); tiles([["Su cartera (anual)", pct(b.retorno_portafolio_anual, 1)], ["Su referencia (anual)", pct(b.retorno_benchmark_anual, 1)], ["Diferencia", spct(b.exceso_anual, 1)]]); para(`La referencia combina índices con la misma distribución objetivo que su cartera. Entre ${fmonth(b.desde.slice(0, 7))} y ${fmonth(b.hasta.slice(0, 7))} su cartera la superó en ${pct(b.hit_ratio, 0)} de los meses.`, 3.4); para("Todavía no hay 36 meses de historia para medir cuánto se aparta de forma estable de su referencia." + (r.meses < 12 ? ` Con menos de 12 meses, las cifras anuales son una extrapolación; la acumulada es ${pct(r.twr, 1)}.` : ""), 4.3, .8, { color: "525252" }); }
    if (id === "riesgo") { head("Riesgo", "Qué pasaría en un mal escenario"); const pick = ["adverso", "stress", "covid", "estallido"].filter(k => c.stress[k]).map(k => c.stress[k]);
      s.addChart(P.ChartType.bar, [{ name: "Variación", labels: pick.map(x => x.nombre), values: pick.map(x => Math.round(x.retorno * 1000) / 10) }], { x: .6, y: 1.5, w: 6.4, h: 5.2, barDir: "bar", chartColors: ["DA1E28"], valAxisLabelFormatCode: '0"%"', showValue: true, dataLabelFormatCode: '0.0"%"', showLegend: false });
      s.addText(pick.map(x => `${x.nombre}: su cartera ${x.retorno < 0 ? "bajaría" : "subiría"} ${pct(Math.abs(x.retorno), 1)} (${mm(Math.abs(x.pnl_clp))}).`).join("\n\n") + "\n\nAdverso y Stress son supuestos a 12 meses; los otros repiten episodios reales con su cartera actual.", { x: 7.3, y: 1.6, w: 5.4, h: 5, fontFace: FONT, fontSize: 13, color: "393939", valign: "top" }); }
    if (id === "crisis" && c.crisis) { const e = c.crisis, t = e.trayectoria; head("Crisis", `Si se repitiera: ${e.nombre}`);
      const step = Math.max(1, Math.ceil(t.fechas.length / 60)), idx = t.fechas.map((_, i) => i).filter(i => i % step === 0 || i === t.fechas.length - 1);
      const labels = idx.map(i => fdate(t.fechas[i]));
      const ser = [{ name: "Su cartera", labels, values: idx.map(i => Math.round(t.total[i] / 1e5) / 10) }, { name: "Valor inicial", labels, values: idx.map(() => Math.round(t.valor_inicial / 1e5) / 10) }];
      if (c.ddIPS != null) ser.push({ name: "Caída tolerada", labels, values: idx.map(() => Math.round(t.valor_inicial * (1 - c.ddIPS / 100) / 1e5) / 10) });
      s.addChart(P.ChartType.line, ser, { x: .6, y: 1.5, w: 6.6, h: 5.2, chartColors: ["0F62FE", "525252", "DA1E28"], lineSize: 2, lineDataSymbol: "none", showLegend: true, legendPos: "b", valAxisLabelFormatCode: '#,##0"M"', catAxisLabelFrequency: Math.max(1, Math.ceil(idx.length / 6)), catAxisLabelFontSize: 9 });
      s.addText([`Si su cartera de hoy hubiera vivido ${e.nombre} (${fdate(e.desde)} a ${fdate(e.hasta)}), habría bajado hasta ${pct(-t.caida_maxima, 1)} (${mm(-t.caida_maxima * t.valor_inicial)}) en ${t.dias_hasta_fondo} días.`, t.fecha_recuperacion ? `Habría recuperado su valor ${t.dias_recuperacion} días después del punto más bajo, sin vender.` : "No habría recuperado su valor dentro del año siguiente.", c.ddIPS != null ? `La caída máxima que usted acordó tolerar es ${nf(c.ddIPS)}%: esta crisis ${-t.caida_maxima * 100 > c.ddIPS ? "la superaría" : "quedaría dentro"}.` : "", "Es la peor de las crisis recientes para esta cartera; no predice la próxima."].filter(Boolean).join("\n\n"), { x: 7.5, y: 1.6, w: 5.2, h: 5, fontFace: FONT, fontSize: 13, color: "393939", valign: "top" }); }
    if (id === "movimientos") { head("Flujos", "Sus aportes y retiros"); tiles([["Aportes", mm(c.flujos.aportes_externos)], ["Retiros", mm(c.flujos.retiros_externos)], ["Ganancia neta", mm(c.flujos.ganancia_neta)]]); para(`La rentabilidad de la cartera mide cómo se gestionó el dinero. Su retorno personal (${pct(r.xirr, 1)} anual) incluye además el momento en que usted aportó o retiró.`, 3.4); }
    if (id === "decisiones") { head("Gestión", "Lo que hicimos en el período"); const ns = c.noticias.filter(x => !x.quiet && x.categoria !== "Cierre").slice(-7); s.addTable([["Fecha", "Qué", "Detalle"].map(t => ({ text: t, options: { bold: true, fill: { color: "F4F4F4" } } })), ...ns.map(x => [fdate(x.fecha), x.categoria, x.titulo])], { x: .6, y: 1.5, w: 12.1, colW: [1.8, 2.4, 7.9], fontFace: FONT, fontSize: 12, color: INK, border: { type: "solid", color: "E0E0E0", pt: .75 } }); }
    if (id === "proximos") { head("Próximos pasos", "Próximos pasos"); para(pres.notes || "(sin texto)", 1.6, 5, { fontSize: 16 }); }
    if (id === "aviso") { head("Aviso", "Supuestos, riesgos y aviso"); para([`Cifras al ${fdate(L.as_of)}, calculadas con los valores cuota de cada fondo (dividendos reinvertidos).`, "Las probabilidades de las metas vienen de 5.000 escenarios simulados con supuestos de mercado; no son una promesa. Los escenarios adversos son hipotéticos o repiten episodios pasados.", "Rentabilidades pasadas no garantizan rentabilidades futuras. Las inversiones pueden perder valor.", `Faltan datos que limitan algunos análisis: ${c.faltantes.slice(0, 3).join("; ") || "ninguno crítico"}.`, "Este documento lo revisa y presenta su asesor; no es una recomendación automática. Cliente y supuestos ficticios: material de simulación."].join("\n\n"), 1.6, 5, { fontSize: 14 }); }
  });
  return P.write({ outputType: "blob" });
}
async function release() {
  if (!$("p-ack").checked) { msg("Antes de liberar, marca la casilla de revisión: confirma que revisaste las cifras y que tú comunicarás la presentación al cliente (QM XX).", "err"); $("p-ack").focus(); return; }
  const c = pres.C, ids = chosen(); $("p-release").disabled = true;
  try {
    if (db) { let por = null; try { por = user ? await user.id() : null; } catch (e) {}
      await db.collection("liberaciones").add({ cliente: c.id, laminas: ids, datos_al: L.as_of, fecha: new Date().toISOString(), por, nota: $("p-note").value.slice(0, 300) }); }
    if (typeof PptxGenJS === "undefined") { msg("Liberación registrada. No se pudo cargar el generador de PPTX; usa Presentar en pantalla.", "err"); return; }
    if (!downloads) { msg("Liberación registrada. Esta vista no permite descargar archivos; usa Presentar en pantalla.", "err"); return; }
    await downloads.save({ filename: `Revision-${c.id}-${L.as_of}.pptx`, data: await buildPptx(c, ids) });
    msg(`Liberada y descargada: ${ids.length} láminas para ${c.nombre}.`, "ok");
  } catch (e) {
    const code = e && e.code;
    msg(code === "declined" ? "Descarga cancelada. La liberación quedó registrada." : code === "invalid_argument" ? "Tu nivel de acceso no permite registrar liberaciones." : "No se pudo completar: " + (e && e.message || e), code === "declined" ? "" : "err");
  } finally { $("p-release").disabled = false; }
}
