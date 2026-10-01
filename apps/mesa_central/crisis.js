/* Mesa Central — Simulación de crisis: la cartera ACTUAL del cliente reviviendo episodios reales, día a día.
   Comprar y mantener desde el inicio del episodio, sin rebalancear, en CLP (Historical Simulation, QM XI). */
"use strict";
const cr = { ep: null, i: 0, playing: false, speed: 1, timer: null, N: 0, draw: null };
function crStop() { if (cr.timer) { clearInterval(cr.timer); cr.timer = null; } cr.playing = false; const b = document.getElementById("cr-play"); if (b) b.textContent = "▶ Reproducir"; }
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

CT.crisis = function (h, C) {
  const H = C.stress.historicos;
  const eps = Object.entries(H).filter(([, e]) => e.trayectoria && e.trayectoria.fechas.length > 1).sort((a, b) => a[1].desde < b[1].desde ? -1 : 1);
  if (!eps.length) { h.innerHTML = `<div class="notif"><span>${si("sin_datos", "Sin episodios")}</span><span>No hay episodios con datos para esta cartera.</span></div>`; return; }
  if (!cr.ep || !H[cr.ep]) cr.ep = eps.slice().sort((a, b) => a[1].trayectoria.caida_maxima - b[1].trayectoria.caida_maxima)[0][0];
  const dd = C.ips.limites.dd, lim = dd == null ? null : -dd / 100, val0 = C.resumen.valor_final;
  // escala común para la galería (Carbon: misma medida en todos los gráficos)
  const rel = e => e.trayectoria.total.map(v => v / e.trayectoria.valor_inicial - 1);
  const gLo = Math.min(lim ?? 0, ...eps.map(([, e]) => Math.min(...rel(e)))) * 1.1, gHi = Math.max(0.03, ...eps.map(([, e]) => Math.max(...rel(e)))) * 1.1;
  const base = Object.fromEntries(GOALS.filter(g => C.metas_cierre[g] && C.metas_cierre[g].prob_exito != null).map(g => [g, C.metas_cierre[g].prob_exito]));
  h.innerHTML = `
    <div class="pagehead"><h2>Si su cartera de hoy hubiera vivido estas crisis</h2>
      <p class="muted" style="max-width:100ch">Cada crisis aplica los movimientos reales de cada fondo a la cartera actual (${mm(val0)}), comprada al inicio y mantenida sin rebalancear, hasta recuperar su valor o un año después del fin del episodio. Es la Simulación Histórica de la QM (Parte XI) mirada día a día; no predice la próxima crisis.</p></div>
    <div class="g3" id="cr-gal" role="list"></div>
    <div class="tile">
      <div class="th"><div><span class="lbl" id="cr-dates"></span><h2 id="cr-title"></h2></div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><button class="btn primary sm" id="cr-play">▶ Reproducir</button><button class="btn sm" id="cr-reset">Reiniciar</button>
          <div class="seg" id="cr-speed"><button data-v="1" aria-pressed="true">1×</button><button data-v="2" aria-pressed="false">2×</button><button data-v="4" aria-pressed="false">4×</button></div></div></div>
      <div class="kpis" id="cr-kpis"></div>
      <div style="display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px" class="cr-main">
        <div style="min-width:0"><div class="chart" id="cr-chart"></div><div class="chart" id="cr-under"></div>
          <input type="range" id="cr-slider" min="0" value="0" style="width:100%" aria-label="Día de la crisis">
          <div class="legend" id="cr-legend"></div></div>
        <div style="display:grid;gap:8px;align-content:start"><h4>Cada fondo hasta este día</h4><div class="bars" id="cr-bars"></div><p class="helper" id="cr-src"></p></div>
      </div>
      <div class="notif" id="cr-story"></div>
    </div>
    <div class="g2">
      <div class="tile"><h3>Comparación de crisis</h3><div class="tw"><table class="dt" id="cr-table"></table></div></div>
      <div class="tile"><h3>Efecto en las metas al terminar cada crisis</h3><div class="tw"><table class="dt" id="cr-goals"></table></div><p class="helper">Probabilidad de lograr cada meta si la cartera partiera desde el valor al fin del episodio (5.000 trayectorias).</p></div>
    </div>`;
  // Galería de crisis (small multiples con escala común)
  $("cr-gal").innerHTML = eps.map(([k, e]) => { const t = e.trayectoria, r = rel(e), W = 260, Hh = 70;
    const x = i => i / (r.length - 1) * W, y = v => (1 - (v - gLo) / (gHi - gLo)) * Hh, iT = t.total.indexOf(Math.min(...t.total));
    const breach = lim != null && t.caida_maxima < lim;
    return `<button class="tile" role="listitem" data-ep="${k}" aria-pressed="${k === cr.ep}" style="all:unset;box-sizing:border-box;cursor:pointer;background:var(--layer);padding:16px;display:grid;gap:8px;border-top:3px solid ${k === cr.ep ? "var(--interactive)" : "transparent"}">
      <span class="lbl">${fdate(e.desde)} – ${fdate(e.hasta)}</span><b>${esc(e.nombre)}</b>
      <svg viewBox="0 0 ${W} ${Hh}" preserveAspectRatio="none" style="width:100%;height:70px" aria-hidden="true"><line x1="0" x2="${W}" y1="${y(0)}" y2="${y(0)}" stroke="${css("--border-strong")}" stroke-dasharray="3 3"/>${lim != null ? `<line x1="0" x2="${W}" y1="${y(lim)}" y2="${y(lim)}" stroke="${css("--err")}" stroke-dasharray="4 3"/>` : ""}<path d="${r.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("")}" fill="none" stroke="${t.caida_maxima < -0.05 ? css("--err") : css("--interactive")}" stroke-width="2"/><circle cx="${x(iT)}" cy="${y(r[iT])}" r="3.5" fill="${css("--text")}"/></svg>
      <span style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><span class="num" style="font-size:20px">${spct(t.caida_maxima, 1)}</span>${breach ? si("alerta", "supera el IPS") : t.caida_maxima < -0.05 ? si("atencion", "caída relevante") : si("ok", "acotada")}</span>
      <span class="helper">${smm(t.caida_maxima * t.valor_inicial)} · fondo en ${t.dias_hasta_fondo} días · ${t.fecha_recuperacion ? `recupera en ${t.dias_recuperacion} días` : "no recupera dentro del horizonte"}</span></button>`; }).join("");
  document.querySelectorAll("#cr-gal [data-ep]").forEach(b => b.addEventListener("click", () => { crStop(); cr.ep = b.dataset.ep; CT.crisis(h, C); }));
  // Comparación y metas
  $("cr-table").innerHTML = `<thead><tr><th>Crisis</th><th>Caída máxima</th><th>En CLP</th><th>Días al fondo</th><th>Recuperación</th><th>Al fin del episodio</th><th>Peor fondo</th></tr></thead><tbody>${eps.map(([k, e]) => { const t = e.trayectoria; return `<tr class="${k === cr.ep ? "hl" : ""}"><td>${esc(e.nombre)}</td><td class="n neg">${spct(t.caida_maxima, 1)}</td><td class="n">${smm(t.caida_maxima * t.valor_inicial)}</td><td class="n">${t.dias_hasta_fondo}</td><td class="n">${t.fecha_recuperacion ? t.dias_recuperacion + " días" : "más de 1 año"}</td><td class="n${cls(t.retorno_al_fin)}">${spct(t.retorno_al_fin, 1)}</td><td>${esc(e.mayor_perdida_vehiculo || "—")}</td></tr>`; }).join("")}</tbody>`;
  const gk = Object.keys(base);
  $("cr-goals").innerHTML = `<thead><tr><th>Escenario</th>${gk.map(g => `<th>${esc(gname[g])}</th>`).join("")}</tr></thead><tbody><tr class="grp"><td colspan="${gk.length + 1}">Hoy</td></tr><tr><td>Sin crisis</td>${gk.map(g => `<td class="n">${pct(base[g], 0)}</td>`).join("")}</tr><tr class="grp"><td colspan="${gk.length + 1}">Después de cada crisis</td></tr>${eps.map(([k, e]) => `<tr class="${k === cr.ep ? "hl" : ""}"><td>${esc(e.nombre)}</td>${gk.map(g => { const p = ((e.metas || {})[g] || {}).prob_exito; const d = p == null ? null : p - base[g]; return `<td class="n${d != null && d < -0.005 ? " neg" : ""}">${pct(p, 0)}${d != null && Math.abs(d) >= 0.005 ? ` <span class="helper">(${spct(d, 0)})</span>` : ""}</td>`; }).join("")}</tr>`).join("")}</tbody>`;
  buildReplay(C, H[cr.ep], lim);
};

function buildReplay(C, e, lim) {
  crStop();
  const t = e.trayectoria, N = t.fechas.length, v0 = t.valor_inicial, ks = Object.keys(t.veh);
  cr.N = N; cr.i = N - 1;
  $("cr-title").textContent = e.nombre;
  $("cr-dates").textContent = `Episodio ${fdate(e.desde)} – ${fdate(e.hasta)} · recorrido hasta ${fdate(t.fechas[N - 1])}`;
  $("cr-legend").innerHTML = `<span><i style="--c:var(--err);opacity:.45"></i>Bajo el valor inicial</span><span><i style="--c:var(--ok);opacity:.45"></i>Sobre el valor inicial</span><span><i class="line"></i>Valor inicial</span>${lim != null ? `<span><i class="line" style="border-color:var(--err)"></i>Caída tolerada IPS (${pct(-lim, 0)})</span>` : ""}<span><i style="--c:var(--layer-2);outline:1px solid var(--border-strong)"></i>Duración del episodio</span>`;
  const srcs = Object.entries(t.fuentes).filter(([, s]) => s !== "observado");
  $("cr-src").textContent = srcs.length ? "Sin historia en el episodio: " + srcs.map(([k, s]) => `${k} ${s}`).join("; ") + "." : "Todos los fondos con datos observados en el episodio.";
  // Gráfico principal
  const host = $("cr-chart"); host.innerHTML = "";
  const W = Math.max(360, host.clientWidth || 900), Hm = 320, m = { t: 14, r: 70, b: 26, l: 64 };
  const tot = t.total, lo = Math.min(...tot, lim != null ? v0 * (1 + lim) : Infinity) * 0.97, hi = Math.max(...tot, v0) * 1.02;
  const x = i => m.l + i / (N - 1) * (W - m.l - m.r), y = v => m.t + (1 - (v - lo) / (hi - lo)) * (Hm - m.t - m.b);
  const svg = el("svg", { viewBox: `0 0 ${W} ${Hm}`, role: "img", "aria-label": `Valor de la cartera durante ${e.nombre}` }, host);
  const after = t.fechas.findIndex(d => d > e.hasta), iEndEp = after === -1 ? N - 1 : Math.max(0, after - 1);
  el("rect", { x: x(0), y: m.t, width: x(iEndEp) - x(0), height: Hm - m.t - m.b, fill: css("--layer-2") }, svg);
  for (let s = 0; s <= 4; s++) { const v = lo + (hi - lo) * s / 4; el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: css("--border") }, svg); txt(svg, m.l - 6, y(v) + 4, nf(v / 1e6, 0) + "M", { "text-anchor": "end" }); }
  const ticks = Math.max(2, Math.min(5, Math.floor((W - m.l - m.r) / 110))); for (let s = 0; s <= ticks; s++) { const i = Math.round((N - 1) * s / ticks); txt(svg, x(i), Hm - 6, fdate(t.fechas[i]), { "text-anchor": s === 0 ? "start" : s === ticks ? "end" : "middle" }); }
  // fantasma (todo el recorrido, tenue) y capa revelada (recortada hasta el cursor)
  el("path", { d: tot.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(""), fill: "none", stroke: css("--border-strong"), "stroke-width": 1.5, "stroke-dasharray": "2 3" }, svg);
  const clipId = "crclip" + Math.random().toString(36).slice(2, 7);
  const cp = el("clipPath", { id: clipId }, el("defs", {}, svg)); const clipR = el("rect", { x: 0, y: 0, width: W, height: Hm }, cp);
  const g = el("g", { "clip-path": `url(#${clipId})` }, svg);
  // Relleno entre la cartera y su valor inicial: rojo debajo, verde encima (eje truncado solo para líneas)
  const defs = svg.querySelector("defs");
  const below = el("clipPath", { id: clipId + "b" }, defs); el("rect", { x: 0, y: y(v0), width: W, height: Hm }, below);
  const above = el("clipPath", { id: clipId + "a" }, defs); el("rect", { x: 0, y: 0, width: W, height: y(v0) }, above);
  const band = tot.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join("") + `L${x(N - 1)},${y(v0)}L${x(0)},${y(v0)}Z`;
  el("path", { d: band, fill: css("--err"), "fill-opacity": .32, "clip-path": `url(#${clipId}b)` }, g);
  el("path", { d: band, fill: css("--ok"), "fill-opacity": .32, "clip-path": `url(#${clipId}a)` }, g);
  el("path", { d: tot.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(""), fill: "none", stroke: css("--text"), "stroke-width": 2 }, g);
  el("line", { x1: m.l, x2: W - m.r, y1: y(v0), y2: y(v0), stroke: css("--text-2"), "stroke-dasharray": "6 4", "stroke-width": 1.5 }, svg);
  txt(svg, W - m.r + 4, y(v0) + 4, mm(v0), { style: `fill:${css("--text-2")}` });
  if (lim != null) { const yl = y(v0 * (1 + lim)); el("line", { x1: m.l, x2: W - m.r, y1: yl, y2: yl, stroke: css("--err"), "stroke-dasharray": "6 4", "stroke-width": 1.5 }, svg); txt(svg, W - m.r + 4, yl + 4, "límite IPS", { style: `fill:${css("--err")}` }); }
  const iT = tot.indexOf(Math.min(...tot)), iR = t.fecha_recuperacion ? t.fechas.indexOf(t.fecha_recuperacion) : -1;
  // Etiquetas escalonadas: el fondo puede coincidir con el fin del episodio (COVID)
  const placed = [];
  const mark = (i, label, col) => { const mk = el("g", { opacity: 0 }, svg); const row = placed.filter(p => Math.abs(p - x(i)) < 120).length; placed.push(x(i));
    const right = x(i) > W - m.r - 130; el("line", { x1: x(i), x2: x(i), y1: m.t, y2: Hm - m.b, stroke: col, "stroke-width": 1 }, mk);
    txt(mk, right ? x(i) - 4 : x(i) + 4, m.t + 10 + row * 14, label, { "text-anchor": right ? "end" : "start", style: `fill:${col};font-weight:600` }); return { i, mk }; };
  const marks = [mark(iT, `Fondo ${spct(t.caida_maxima, 1)}`, css("--err")), ...(iEndEp < N - 1 && iEndEp !== iT ? [mark(iEndEp, "Fin del episodio", css("--text-2"))] : []), ...(iR >= 0 ? [mark(iR, "Recuperado", css("--ok"))] : [])];
  const cur = el("line", { y1: m.t, y2: Hm - m.b, stroke: css("--interactive"), "stroke-width": 2 }, svg), dot = el("circle", { r: 5, fill: css("--interactive"), stroke: css("--layer"), "stroke-width": 2 }, svg);
  // Bajo el agua: caída desde el valor inicial
  const uh = $("cr-under"); uh.innerHTML = ""; const Hu = 90, mu = { t: 6, r: 70, b: 6, l: 64 };
  const dds = tot.map(v => Math.min(0, v / v0 - 1)), dlo = Math.min(...dds, lim ?? 0) * 1.1 || -0.01;
  const yu = v => mu.t + (v / dlo) * (Hu - mu.t - mu.b);
  const su = el("svg", { viewBox: `0 0 ${W} ${Hu}`, role: "img", "aria-label": "Caída desde el valor inicial" }, uh);
  txt(su, mu.l - 6, yu(0) + 10, "0%", { "text-anchor": "end" }); txt(su, mu.l - 6, yu(dlo) - 2, pct(dlo, 0), { "text-anchor": "end" });
  const cpu = el("clipPath", { id: clipId + "u" }, el("defs", {}, su)); const clipU = el("rect", { x: 0, y: 0, width: W, height: Hu }, cpu);
  el("path", { d: `M${x(0)},${yu(0)}` + dds.map((v, i) => `L${x(i)},${yu(v)}`).join("") + `L${x(N - 1)},${yu(0)}Z`, fill: css("--err"), "fill-opacity": .35, stroke: css("--err"), "clip-path": `url(#${clipId}u)` }, su);
  if (lim != null) el("line", { x1: mu.l, x2: W - mu.r, y1: yu(lim), y2: yu(lim), stroke: css("--err"), "stroke-dasharray": "6 4" }, su);
  txt(su, W - mu.r + 4, Hu / 2, "caída", { style: `fill:${css("--text-3")}` });
  const curU = el("line", { y1: mu.t, y2: Hu - mu.b, stroke: css("--interactive"), "stroke-width": 2 }, su);
  // Slider y lectura en vivo
  const sl = $("cr-slider"); sl.max = N - 1; sl.value = N - 1;
  sl.oninput = () => { crStop(); cr.draw(+sl.value); };
  const maxAbs = Math.max(1, ...ks.map(k => Math.max(...t.veh[k].map((v, i) => Math.abs(v - t.veh[k][0])))));
  cr.draw = i => {
    cr.i = i; const xx = x(i);
    clipR.setAttribute("width", xx); clipU.setAttribute("width", xx);
    cur.setAttribute("x1", xx); cur.setAttribute("x2", xx); curU.setAttribute("x1", xx); curU.setAttribute("x2", xx);
    dot.setAttribute("cx", xx); dot.setAttribute("cy", y(tot[i]));
    marks.forEach(mk => mk.mk.setAttribute("opacity", i >= mk.i ? 1 : 0));
    sl.value = i;
    const chg = tot[i] / v0 - 1, minSoFar = Math.min(...tot.slice(0, i + 1)) / v0 - 1;
    const deltas = ks.map(k => [k, t.veh[k][i] - t.veh[k][0], t.veh[k][0] ? t.veh[k][i] / t.veh[k][0] - 1 : 0]);
    const worst = deltas.slice().sort((a, b) => a[1] - b[1])[0];
    $("cr-kpis").innerHTML = [["Fecha", fdate(t.fechas[i]), `día ${i + 1} de ${N}`], ["Valor de la cartera", mm(tot[i]), `parte en ${mm(v0)}`], ["Variación desde el inicio", spct(chg, 1), smm(tot[i] - v0)], ["Peor punto hasta aquí", spct(minSoFar, 1), lim != null ? (minSoFar < lim ? "supera la caída tolerada del IPS" : `límite IPS ${pct(-lim, 0)}`) : "el IPS no define caída tolerada"], ["Fondo que más pesa", worst[1] < 0 ? `${worst[0]} ${spct(worst[2], 0)}` : "ninguno pierde", worst[1] < 0 ? smm(worst[1]) : ""]]
      .map(([l, v, n]) => `<div class="kpi"><span class="lbl">${l}</span><span class="v sm${l.startsWith("Variación") ? (chg < 0 ? " neg" : " pos") : ""}">${v}</span><span class="helper">${esc(n)}</span></div>`).join("");
    $("cr-bars").innerHTML = deltas.map(([k, d, p]) => `<div class="brow" style="grid-template-columns:70px minmax(0,1fr) 92px"><span><span class="sw" style="--c:${vc(k)}"></span>${k}</span><div class="track"><i style="left:50%;width:${(Math.abs(d) / maxAbs * 50).toFixed(1)}%;${d < 0 ? "transform:translateX(-100%);" : ""}background:${d < 0 ? css("--err") : css("--ok")}"></i><i style="left:50%;width:1px;background:var(--border-strong)"></i></div><span class="num" style="font-size:12px">${smm(d)} <span class="helper">${spct(p, 0)}</span></span></div>`).join("");
  };
  cr.draw(N - 1);
  // Relato determinístico (QM XIX: mismas cifras, plantilla fija)
  const st = $("cr-story"); const breach = lim != null && t.caida_maxima < lim;
  st.className = "notif " + (breach ? "err" : t.caida_maxima < -0.05 ? "warn" : "");
  st.innerHTML = `<span>${si(breach ? "alerta" : t.caida_maxima < -0.05 ? "atencion" : "ok", "Lectura")}</span><span>Con la cartera de hoy, ${esc(e.nombre.toLowerCase().startsWith("el ") ? e.nombre : "el episodio " + e.nombre)} habría llevado su patrimonio de ${mm(v0)} a ${mm(Math.min(...tot))} (${spct(t.caida_maxima, 1)}) en ${t.dias_hasta_fondo} días corridos, tocando fondo el ${fdate(t.fecha_fondo)}. ${t.fecha_recuperacion ? `Habría vuelto a su valor inicial el ${fdate(t.fecha_recuperacion)}, ${t.dias_recuperacion} días después del fondo.` : `No habría recuperado su valor dentro del horizonte medido (hasta ${fdate(t.datos_hasta)}).`} ${lim == null ? "El IPS no define una caída tolerada para comparar." : breach ? `Supera la caída máxima que tolera el IPS (${pct(-lim, 0)}): es una alerta para conversar con el cliente, no un ajuste automático.` : `Queda dentro de la caída que tolera el IPS (${pct(-lim, 0)}).`}</span>`;
  // Controles
  const play = $("cr-play");
  play.onclick = () => { if (cr.playing) { crStop(); return; } if (cr.i >= N - 1) cr.draw(0); cr.playing = true; play.textContent = "⏸ Pausa";
    const stepPer = Math.max(1, Math.round(N / 160));
    if (reduceMotion()) { cr.draw(N - 1); crStop(); return; }
    cr.timer = setInterval(() => { const nx = Math.min(N - 1, cr.i + stepPer * cr.speed); cr.draw(nx); if (nx >= N - 1) crStop(); }, 45); };
  $("cr-reset").onclick = () => { crStop(); cr.draw(0); };
  document.querySelectorAll("#cr-speed button").forEach(b => { b.setAttribute("aria-pressed", String(+b.dataset.v === cr.speed)); b.onclick = () => { cr.speed = +b.dataset.v; document.querySelectorAll("#cr-speed button").forEach(x => x.setAttribute("aria-pressed", String(x === b))); }; });
}
