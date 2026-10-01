/* Mesa Central — pestaña Cartera, en el orden del Diversification Flow (DF v1.1 7.1):
   construcción → posiciones → clase y subclase → moneda y geografía → vintage → correlación y riesgo
   → factores → concentración (look-through) → lectura. */
"use strict";
const DIM_NAMES = { clase: "Clase de activo", subclase: "Subclase (taxonomía AFI)", moneda: "Moneda económica", geografia: "Geografía", liquidez: "Liquidez de rescate", administradora: "Administradora" };
const FLOW = [["c-arq", "Construcción"], ["c-pos", "Posiciones"], ["c-dim", "Clase, moneda y geografía"], ["c-vin", "Vintage"], ["c-rsk", "Correlación y riesgo"], ["c-fac", "Factores"], ["c-con", "Concentración"], ["c-ren", "Rentabilidad"], ["c-lec", "Lectura"]];

CT.cartera = function (h, C) {
  const K = C.cartera, S = C.resumen, Dr = C.drift, dv = C.div_cierre, R = C.rentabilidad, Mx = K.medidas;
  const palette = ["--c1", "--c2", "--c3", "--c4", "--c5", "--g1", "--g2", "--g3"];
  h.innerHTML = `
    <div class="steps" role="navigation" aria-label="Flujo de diversificación">${FLOW.map(([id, n], i) => `<a href="#${id}" class="step" style="--sc:var(--interactive);text-decoration:none;color:inherit"><b>${i + 1}. ${n}</b></a>`).join("")}</div>

    <section class="tile" id="c-arq"><div class="th"><div><span class="lbl">1 · Construcción</span><h3>De las metas a los fondos</h3></div><button class="link" data-goto-tab="construccion">Ver cómo se optimizó</button></div>
      <p class="helper">Cada meta tiene su propia cartera según su plazo y el IPS (construcción vigente: ${esc(K.arquitectura.trigger.split("—")[0].trim())}, ${fdate(K.arquitectura.fecha)}). El ancho de cada cinta es el dinero de esa meta en ese fondo hoy.</p>
      <div class="chart" id="sankey"></div>
      <div class="tw"><table class="dt" id="arq"></table></div></section>

    <section class="tile" id="c-pos"><div class="th"><div><span class="lbl">2 · Posiciones</span><h3>Qué tiene el cliente, por meta y fondo</h3></div><label class="helper" style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="pos-closed"> Mostrar posiciones cerradas</label></div>
      <div class="tw"><table class="dt" id="pos"></table></div>
      <p class="helper">Costo a precio promedio. La ganancia realizada viene de ventas por rebalanceos, cambios de horizonte y metas cumplidas. Posiciones simuladas: el conector no trae posiciones de clientes; en producción vendrían del custodio (ESFS M04).</p></section>

    <section class="tile" id="c-dim"><span class="lbl">3 · Clase, moneda y geografía</span><h3>Cómo se reparte la cartera</h3><div class="g2" id="dims"></div>
      <p class="helper">Moneda económica: el fondo global se compra en pesos pero invierte en ETF listados en EE.UU., así que su valor sigue al dólar (cartera IFRS informada a la CMF, ámbito extranjero 100%).</p></section>

    <section class="tile" id="c-vin"><span class="lbl">4 · Vintage</span><h3>Cuándo entró el dinero y desde cuándo existen los fondos</h3>
      <div class="g2"><div><h4>Vintage del capital</h4><div class="chart" id="vcap"></div><div class="tw"><table class="dt" id="vcap-t"></table></div><p class="helper" id="vcap-n"></p></div>
        <div><h4>Vintage de los fondos</h4><div class="chart" id="vfon"></div><p class="helper">Barra: historia del fondo desde su inicio de operaciones (ficha CMF). Punto: primera compra del cliente. El vintage de private equity (compromisos por año y capital calls) no aplica: no hay vehículos con compromisos en el universo; el fondo de facturas es rescatable.</p></div></div></section>

    <section class="tile" id="c-rsk"><span class="lbl">5 · Correlación y aporte al riesgo</span><h3>Diversificación nominal frente a económica</h3>
      <div class="kpis">${kpi("Fondos en cartera", Mx.n_fondos, "diversificación nominal")}${kpi("Apuestas efectivas", Mx.enb == null ? "—" : nf(Mx.enb, 1), "1 / Σ aporte al riesgo² (ADVANCED)")}${kpi("Ratio de diversificación", Mx.dr == null ? "—" : nf(Mx.dr, 2), "Σ wσ / σ cartera (ADVANCED)")}${kpi("HHI por peso", nf(Mx.hhi_pesos, 2), "concentración nominal")}${kpi("HHI por aporte al riesgo", Mx.hhi_riesgo == null ? "—" : nf(Mx.hhi_riesgo, 2), "concentración real de riesgo")}</div>
      <div class="g2"><div><h4>Peso frente a aporte al riesgo</h4><div class="legend"><span><i style="--c:var(--bar)"></i>Peso</span><span><i style="--c:var(--interactive)"></i>Aporte al riesgo</span></div><div class="chart" id="riskw"></div><p class="helper" id="riskw-n"></p></div>
        <div><h4>Peso actual frente al objetivo</h4><div class="legend"><span><i style="--c:var(--interactive)"></i>Actual</span><span><i style="--c:var(--layer-2);outline:1px solid var(--border-strong)"></i>Banda ±${pct(Dr.banda, 0)}</span><span><i class="line" style="border-top-style:solid;border-color:var(--text)"></i>Objetivo</span></div><div class="chart" id="drift"></div></div></div>
      <p class="helper">"Apuestas efectivas" es una convención propia de AFI pendiente de validar por el Comité (QM XXIII, Pendiente 3). Las correlaciones usadas están en la pestaña Construcción.</p></section>

    <section class="tile" id="c-fac"><span class="lbl">6 · Factores</span><h3>A qué riesgos está expuesto</h3><div class="g2"><div class="bars" id="fac"></div><div id="fac-side"></div></div>
      <p class="helper">Exposición por clasificación de cada fondo. El factor risk por regresión sobre índices es ADVANCED y no se calcula todavía (QM V). Por eso el HHI por factores (${nf(Mx.hhi_factores, 2)}) coincide con el de pesos: cada fondo cae en un solo factor.</p></section>

    <section class="tile" id="c-con"><span class="lbl">7 · Concentración</span><h3>Emisores detrás de los fondos (look-through)</h3>
      <p class="helper">Suma lo que cada fondo informa a la CMF (cartera IFRS jun-2026): un mismo banco puede aparecer como depósito, bono y acción en fondos distintos.</p>
      <div class="legend">${VEH.map(k => `<span><i style="--c:${vc(k)}"></i>${k}</span>`).join("")}</div><div class="bars" id="lt"></div></section>

    <section class="tile" id="c-ren"><span class="lbl">8 · Rentabilidad</span><h3>Retorno mensual y por fondo</h3><div id="heat" style="overflow-x:auto"></div>
      <div class="tw"><table class="dt" id="rent"></table></div>
      <div class="g2"><div><h4>Atribución frente al policy benchmark</h4><div class="tw"><table class="dt" id="brin"></table></div><p class="helper">Brinson-Fachler (ADVANCED). Suma aritmética mensual.</p></div><div id="ref-n"></div></div></section>

    <section class="notif" id="c-lec"></section>`;

  // 1 · Sankey metas → fondos
  const A = K.arquitectura, goals = Object.keys(A.metas).filter(g => Object.values(A.metas[g].valor).some(v => v > 0));
  const flows = []; goals.forEach(g => Object.entries(A.metas[g].valor).forEach(([k, v]) => { if (v > 0) flows.push({ g, k, v }); }));
  const host = $("sankey"), W = Math.max(360, host.clientWidth || 900), Hs = 300, gap = 10, total = flows.reduce((a, f) => a + f.v, 0);
  const svg = el("svg", { viewBox: `0 0 ${W} ${Hs}`, role: "img", "aria-label": "Distribución de cada meta entre fondos" }, host);
  const nodeW = 14, lx = 190, rx = W - 190, usable = Hs - gap * (Math.max(goals.length, VEH.length) - 1) - 10, sc = usable / total;
  const gTot = Object.fromEntries(goals.map(g => [g, flows.filter(f => f.g === g).reduce((a, f) => a + f.v, 0)]));
  const funds = VEH.filter(k => flows.some(f => f.k === k)), fTot = Object.fromEntries(funds.map(k => [k, flows.filter(f => f.k === k).reduce((a, f) => a + f.v, 0)]));
  let yy = 5; const gy = {}; goals.forEach(g => { gy[g] = yy; yy += gTot[g] * sc + gap; });
  yy = 5; const fy = {}; funds.forEach(k => { fy[k] = yy; yy += fTot[k] * sc + gap; });
  const gOff = Object.fromEntries(goals.map(g => [g, 0])), fOff = Object.fromEntries(funds.map(k => [k, 0]));
  flows.sort((a, b) => funds.indexOf(a.k) - funds.indexOf(b.k)).forEach(f => { const t = f.v * sc, y0 = gy[f.g] + gOff[f.g], y1 = fy[f.k] + fOff[f.k]; gOff[f.g] += t; fOff[f.k] += t;
    const p = el("path", { d: `M${lx + nodeW},${y0} C${(lx + rx) / 2},${y0} ${(lx + rx) / 2},${y1} ${rx},${y1} L${rx},${y1 + t} C${(lx + rx) / 2},${y1 + t} ${(lx + rx) / 2},${y0 + t} ${lx + nodeW},${y0 + t}Z`, fill: vc(f.k), "fill-opacity": .45 }, svg);
    const tt = el("title", {}, p); tt.textContent = `${gname[f.g]} → ${f.k}: ${mm(f.v)}`; });
  const maxCh = Math.floor((lx - 12) / 6.6);
  const short = s => s.length > maxCh ? s.slice(0, maxCh - 1).trimEnd() + "…" : s;
  goals.forEach(g => { el("rect", { x: lx, y: gy[g], width: nodeW, height: Math.max(2, gTot[g] * sc), fill: css(gcol[g]) }, svg);
    const cy = gy[g] + gTot[g] * sc / 2;
    const t1 = txt(svg, lx - 8, cy - 2, short(gname[g]), { "text-anchor": "end", style: `fill:${css("--text")}` }); el("title", {}, t1).textContent = gname[g];
    txt(svg, lx - 8, cy + 12, mm(gTot[g]), { "text-anchor": "end", style: `fill:${css("--text-2")}` }); });
  funds.forEach(k => { el("rect", { x: rx, y: fy[k], width: nodeW, height: Math.max(2, fTot[k] * sc), fill: vc(k) }, svg); txt(svg, rx + nodeW + 8, fy[k] + fTot[k] * sc / 2 + 4, `${k} · ${mm(fTot[k])} (${pct(fTot[k] / total, 0)})`, { style: `fill:${css("--text")}` }); });
  $("arq").innerHTML = `<thead><tr><th>Meta</th><th>Horizonte</th><th>Tope de volatilidad</th>${VEH.map(k => `<th>${k}</th>`).join("")}<th>Valor</th></tr></thead><tbody>${Object.entries(A.metas).map(([g, m]) => { const tv = Object.values(m.valor).reduce((a, b) => a + b, 0); return `<tr><td><span class="sw" style="--c:var(${gcol[g]})"></span>${esc(gname[g])}</td><td>${esc(m.horizonte)}</td><td class="n">${pct(m.tope, 1)} <span class="helper">${m.fuente === "IPS" ? "IPS" : "horizonte"}</span></td>${VEH.map(k => { const o = m.objetivo[k] || 0, a = tv ? (m.valor[k] || 0) / tv : 0; return o || a ? `<td class="n">${pct(a, 0)} <span class="helper">/ ${pct(o, 0)}</span></td>` : '<td class="n helper">·</td>'; }).join("")}<td class="n">${tv ? mm(tv) : "cerrada"}</td></tr>`; }).join("")}</tbody>`;

  // 2 · Posiciones
  const drawPos = () => { const all = $("pos-closed").checked; const P = K.posiciones.filter(p => all || p.vigente); const tv = S.valor_final;
    $("pos").innerHTML = `<thead><tr><th>Meta</th><th>Fondo</th><th>Cuotas</th><th>Valor cuota</th><th>Valor</th><th>Peso</th><th>Costo</th><th>Ganancia no realizada</th><th>Realizada</th><th>Primera compra</th><th>Rescate</th></tr></thead><tbody>${P.map(p => `<tr${p.vigente ? "" : ' style="color:var(--text-3)"'}><td>${esc(gname[p.meta] || p.meta)}</td><td><span class="sw" style="--c:${vc(p.vehiculo)}"></span>${p.vehiculo} · ${VNAME[p.vehiculo]}</td><td class="n">${nf(p.unidades, 0)}</td><td class="n">${nf(p.valor_cuota, 2)}</td><td class="n">${mm(p.valor)}</td><td class="n">${pct(p.valor / tv, 1)}</td><td class="n">${mm(p.costo)}</td><td class="n${cls(p.ganancia_no_realizada)}">${smm(p.ganancia_no_realizada)}${p.costo ? ` <span class="helper">${spct(p.ganancia_no_realizada / p.costo, 1)}</span>` : ""}</td><td class="n${cls(p.ganancia_realizada)}">${p.ganancia_realizada ? smm(p.ganancia_realizada) : "—"}</td><td class="n">${fdate(p.primera_compra)}</td><td>${esc(L.universo[p.vehiculo].liquidez)}</td></tr>`).join("")}
      <tr><td colspan="4"><b>Total</b></td><td class="n"><b>${mm(P.reduce((a, p) => a + p.valor, 0))}</b></td><td></td><td class="n">${mm(P.reduce((a, p) => a + p.costo, 0))}</td><td class="n"><b>${smm(P.reduce((a, p) => a + p.ganancia_no_realizada, 0))}</b></td><td class="n">${smm(K.posiciones.reduce((a, p) => a + p.ganancia_realizada, 0))}</td><td colspan="2"></td></tr></tbody>`; };
  $("pos-closed").addEventListener("change", drawPos); drawPos();

  // 3 · Dimensiones (barras 100%)
  $("dims").innerHTML = Object.entries(K.exposiciones).map(([d, parts]) => { const e = Object.entries(parts).sort((a, b) => b[1] - a[1]);
    return `<div style="display:grid;gap:6px"><h4>${DIM_NAMES[d] || d}</h4><div class="stack" style="height:22px">${e.map(([n, v], i) => `<i style="width:${(v * 100).toFixed(1)}%;background:var(${palette[i % palette.length]})" title="${esc(n)} ${pct(v, 1)}"></i>`).join("")}</div><div class="legend">${e.map(([n, v], i) => `<span><i style="--c:var(${palette[i % palette.length]})"></i>${esc(n)} <b class="num">${pct(v, 0)}</b></span>`).join("")}</div></div>`; }).join("");

  // 4 · Vintage del capital (columnas aportado vs valor hoy)
  const V = K.vintage_capital, vh = $("vcap"), Wv = Math.max(320, vh.clientWidth || 600), Hv = 200, mv = { t: 10, r: 10, b: 24, l: 56 };
  const vmax = Math.max(...V.map(c => Math.max(c.aportado, c.valor))) * 1.1, bw = Math.min(80, (Wv - mv.l - mv.r) / V.length / 2.6);
  const sv = el("svg", { viewBox: `0 0 ${Wv} ${Hv}`, role: "img", "aria-label": "Aportado y valor hoy por año de entrada" }, vh);
  const yv = v => mv.t + (1 - v / vmax) * (Hv - mv.t - mv.b);
  [0, vmax / 2, vmax].forEach(v => { el("line", { x1: mv.l, x2: Wv - mv.r, y1: yv(v), y2: yv(v), stroke: css("--border") }, sv); txt(sv, mv.l - 6, yv(v) + 4, nf(v / 1e6, 0) + "M", { "text-anchor": "end" }); });
  V.forEach((c, i) => { const cx = mv.l + (i + 0.5) * (Wv - mv.l - mv.r) / V.length;
    el("rect", { x: cx - bw - 2, y: yv(c.aportado), width: bw, height: yv(0) - yv(c.aportado), fill: css("--bar") }, sv);
    el("rect", { x: cx + 2, y: yv(c.valor), width: bw, height: yv(0) - yv(c.valor), fill: css("--interactive") }, sv);
    txt(sv, cx, Hv - 6, String(c.anio), { "text-anchor": "middle" }); });
  $("vcap-t").innerHTML = `<thead><tr><th>Año de entrada</th><th>Aportado</th><th>Retirado (prorrata)</th><th>Valor hoy</th><th>Ganancia</th><th>Peso hoy</th></tr></thead><tbody>${V.map(c => `<tr><td>${c.anio}</td><td class="n">${mm(c.aportado)}</td><td class="n">${c.retirado ? mm(c.retirado) : "—"}</td><td class="n">${mm(c.valor)}</td><td class="n${cls(c.ganancia)}">${smm(c.ganancia)}</td><td class="n">${pct(c.valor / S.valor_final, 0)}</td></tr>`).join("")}</tbody>`;
  const top = V.slice().sort((a, b) => b.valor - a.valor)[0];
  $("vcap-n").textContent = `Barra gris: aportado; azul: valor hoy. ${V.length === 1 ? `Todo el capital entró en ${top.anio}: no se promedió el precio de entrada.` : `El ${pct(top.valor / S.valor_final, 0)} del valor viene de dinero que entró en ${top.anio}.`} Cada cohorte crece con la rentabilidad de la cartera; los retiros se descuentan a prorrata (QM VIII, vintage analysis, ADVANCED).`;
  // Vintage de los fondos (línea de tiempo)
  const VF = K.vintage_fondos, ks = Object.keys(VF), fh = $("vfon"), Wf = Math.max(320, fh.clientWidth || 600), rh = 30, Hf = ks.length * rh + 30, mf = { l: 70, r: 20 };
  const y0 = Math.min(...ks.map(k => +VF[k].inicio.slice(0, 4))), y1 = +L.as_of.slice(0, 4) + 1, xf = d => mf.l + (+d.slice(0, 4) + (+d.slice(5, 7) - 1) / 12 - y0) / (y1 - y0) * (Wf - mf.l - mf.r);
  const sf = el("svg", { viewBox: `0 0 ${Wf} ${Hf}`, role: "img", "aria-label": "Inicio de cada fondo y primera compra del cliente" }, fh);
  for (let y = y0; y <= y1; y += Math.max(1, Math.round((y1 - y0) / 6))) { el("line", { x1: xf(`${y}-01`), x2: xf(`${y}-01`), y1: 0, y2: Hf - 20, stroke: css("--border") }, sf); txt(sf, xf(`${y}-01`), Hf - 6, String(y), { "text-anchor": "middle" }); }
  ks.forEach((k, i) => { const cy = i * rh + 14; txt(sf, mf.l - 8, cy + 4, k, { "text-anchor": "end", style: `fill:${css("--text-2")}` });
    el("rect", { x: xf(VF[k].inicio), y: cy - 6, width: xf(L.as_of) - xf(VF[k].inicio), height: 12, fill: vc(k), "fill-opacity": .5 }, sf);
    if (VF[k].primera_compra) el("circle", { cx: xf(VF[k].primera_compra), cy, r: 6, fill: css("--text"), stroke: css("--layer"), "stroke-width": 2 }, sf);
    txt(sf, xf(VF[k].inicio) + 4, cy - 9, `desde ${VF[k].inicio.slice(0, 4)}`, { style: "font-size:10px" }); });

  // 5 · Peso vs riesgo y drift
  const kr = VEH.filter(k => dv.pesos[k]), rh2 = $("riskw"), W2 = Math.max(300, rh2.clientWidth || 500), m2 = { t: 6, r: 70, b: 6, l: 70 }, H2 = m2.t + m2.b + 34 * kr.length;
  const tp = Math.max(.6, ...kr.map(k => Math.max(dv.pesos[k], dv.contribucion_riesgo[k]))), x2 = v => m2.l + v * (W2 - m2.l - m2.r) / tp;
  const s2 = el("svg", { viewBox: `0 0 ${W2} ${H2}`, role: "img", "aria-label": "Peso frente a aporte al riesgo" }, rh2);
  kr.forEach((k, i) => { const cy = m2.t + i * 34 + 17; txt(s2, m2.l - 8, cy + 4, k, { "text-anchor": "end", style: `fill:${css("--text-2")}` });
    el("rect", { x: x2(0), y: cy - 12, width: x2(dv.pesos[k]) - x2(0), height: 10, fill: css("--bar") }, s2); el("rect", { x: x2(0), y: cy + 1, width: Math.max(1, x2(Math.max(0, dv.contribucion_riesgo[k])) - x2(0)), height: 10, fill: css("--interactive") }, s2);
    txt(s2, x2(Math.max(dv.pesos[k], dv.contribucion_riesgo[k])) + 6, cy + 4, `${pct(dv.pesos[k], 0)} → ${pct(dv.contribucion_riesgo[k], 0)}`, { style: `fill:${css("--text")}` }); });
  const rv = (dv.contribucion_riesgo.RVL || 0) + (dv.contribucion_riesgo.RVG || 0), rvw = (dv.pesos.RVL || 0) + (dv.pesos.RVG || 0);
  $("riskw-n").textContent = `La renta variable pesa ${pct(rvw, 0)} y explica ${pct(rv, 0)} del riesgo.${dv.pesos.DP ? ` Facturas pesa ${pct(dv.pesos.DP, 0)} y casi no aporta riesgo medido: su valor cuota está suavizado.` : ""}`;
  const kd = VEH.filter(k => (Dr.actual[k] || 0) > 0 || (Dr.objetivo[k] || 0) > 0), dh = $("drift"), Wd = Math.max(300, dh.clientWidth || 500), md = { t: 6, r: 16, b: 22, l: 50 }, Hd = md.t + md.b + 30 * kd.length, xd = v => md.l + v * (Wd - md.l - md.r);
  const sd = el("svg", { viewBox: `0 0 ${Wd} ${Hd}`, role: "img", "aria-label": "Peso actual frente al objetivo" }, dh);
  [0, .5, 1].forEach(v => { el("line", { x1: xd(v), x2: xd(v), y1: md.t, y2: Hd - md.b, stroke: css("--border") }, sd); txt(sd, xd(v), Hd - 6, pct(v, 0), { "text-anchor": "middle" }); });
  kd.forEach((k, i) => { const cy = md.t + i * 30 + 15, a = Dr.actual[k] || 0, o = Dr.objetivo[k] || 0, out = Math.abs(a - o) > Dr.banda;
    txt(sd, md.l - 8, cy + 4, k, { "text-anchor": "end", style: `fill:${css("--text-2")}` });
    el("rect", { x: xd(Math.max(0, o - Dr.banda)), y: cy - 7, width: xd(Math.min(1, o + Dr.banda)) - xd(Math.max(0, o - Dr.banda)), height: 14, fill: css("--layer-2"), stroke: css("--border-strong") }, sd);
    el("line", { x1: xd(o), x2: xd(o), y1: cy - 9, y2: cy + 9, stroke: css("--text"), "stroke-width": 2 }, sd);
    el(out ? "rect" : "circle", out ? { x: xd(a) - 5, y: cy - 5, width: 10, height: 10, fill: css("--err"), transform: `rotate(45 ${xd(a)} ${cy})` } : { cx: xd(a), cy, r: 5.5, fill: css("--interactive") }, sd);
    txt(sd, xd(a) + 10, cy + 4, `${pct(a, 1)} (${spct(a - o, 1)})`, { style: `fill:${css("--text")}` }); });

  // 6 · Factores
  const F = K.factores, fk = Object.keys(F).filter(k => !k.startsWith("Tasa"));
  $("fac").innerHTML = fk.map(k => `<div class="brow"><span>${esc(k)}</span><div class="track"><i style="left:0;width:${(F[k] * 100).toFixed(1)}%;background:var(--interactive)"></i></div><span class="num">${pct(F[k], 0)}</span></div>`).join("");
  const sec = Object.entries(K.sectores).sort((a, b) => b[1] - a[1]), rat = Object.entries(K.rating).sort((a, b) => b[1] - a[1]);
  $("fac-side").innerHTML = `<dl class="kv"><dt>Duración ponderada de la cartera</dt><dd class="num">${nf(F["Tasa (duración ponderada, años)"], 2)} años</dd><dt>Exposición al dólar</dt><dd class="num">${pct(F["Moneda extranjera"], 0)}</dd></dl>
    ${sec.length ? `<h4 style="margin-top:12px">Sectores de las acciones locales (% de la cartera)</h4><div class="bars">${sec.slice(0, 6).map(([s, v]) => `<div class="brow" style="grid-template-columns:170px minmax(0,1fr) 60px"><span>${esc(s)}</span><div class="track"><i style="left:0;width:${(v / sec[0][1] * 100).toFixed(1)}%;background:var(${VCOL.RVL})"></i></div><span class="num">${pct(v, 1)}</span></div>`).join("")}</div>` : ""}
    ${rat.length ? `<h4 style="margin-top:12px">Calidad crediticia de la renta fija (% de la cartera)</h4><div class="legend">${rat.map(([s, v]) => `<span>${esc(s)} <b class="num">${pct(v, 1)}</b></span>`).join("")}</div>` : ""}`;

  // 7 · Look-through
  const LT = K.look_through, mx = Math.max(...LT.map(r => r.peso));
  $("lt").innerHTML = LT.map(r => `<div class="brow" style="grid-template-columns:240px minmax(0,1fr) 70px"><span title="${esc(r.tipo)}">${esc(r.emisor)} <span class="helper">${esc(r.tipo)}</span></span><div class="track">${Object.entries(r.por_fondo).map(([k, v], i, arr) => { const left = arr.slice(0, i).reduce((a, [, x]) => a + x, 0); return `<i style="left:${(left / mx * 100).toFixed(2)}%;width:${(v / mx * 100).toFixed(2)}%;background:${vc(k)}" title="${k} ${pct(v, 2)}"></i>`; }).join("")}</div><span class="num">${pct(r.peso, 1)}</span></div>`).join("") + (K.look_through_resto > 0.001 ? `<p class="helper">Otros emisores: ${pct(K.look_through_resto, 1)} en total.</p>` : "");

  // 8 · Rentabilidad
  const rets = Object.fromEntries(C.retornos_mensuales.map(r => [r.mes, r.r])), years = [...new Set(C.retornos_mensuales.map(r => r.mes.slice(0, 4)))];
  const col = v => { const a = Math.min(1, Math.abs(v) / 0.04); return `background:color-mix(in srgb, var(${v >= 0 ? "--div-pos" : "--div-neg"}) ${Math.round(a * 85)}%, var(--div-0));color:${a > .6 ? "#fff" : "var(--text)"}`; };
  $("heat").innerHTML = `<div class="heat" style="min-width:640px"><div class="h"></div>${MON.map(x => `<div class="h">${x}</div>`).join("")}${years.map(y => `<div class="h" style="text-align:left">${y}</div>` + MON.map((_, i) => { const k = `${y}-${String(i + 1).padStart(2, "0")}`, v = rets[k]; return v == null ? "<div></div>" : `<div style="${col(v)}" title="${fmonth(k)}: ${spct(v, 2)}">${spct(v, 1)}</div>`; }).join("")).join("")}</div>`;
  const rrow = (name, r) => `<tr><td class="tx">${name}</td>${["1m", "3m", "ytd", "1a", "3a", "5a", "desde_inicio_anual"].map(k => `<td class="n${cls(r[k])}">${pct(r[k], 1)}</td>`).join("")}<td class="n">${pct(r.volatilidad_3a, 1)}</td><td class="n neg">${pct(r.max_drawdown_3a, 1)}</td></tr>`;
  $("rent").innerHTML = `<thead><tr><th>Fondo</th><th>1 mes</th><th>3 meses</th><th>YTD</th><th>1 año</th><th>3 años</th><th>5 años</th><th>Inicio</th><th>Vol 3a</th><th>Caída 3a</th></tr></thead><tbody>${VEH.map(k => rrow(`<span class="sw" style="--c:${vc(k)}"></span>${k} · ${esc(R[k].nombre)}`, R[k])).join("")}<tr class="grp"><td colspan="10">Referencias (no elegibles como benchmark)</td></tr>${rrow(esc(L.referencias.IPSA.nombre), L.referencias.IPSA)}${rrow(esc(L.referencias.AFP_C.nombre), L.referencias.AFP_C)}</tbody>`;
  const B = (C.relativo.realizado || {}).atribucion;
  $("brin").innerHTML = B ? `<thead><tr><th>Fondo</th><th>Asignación</th><th>Selección</th><th>Interacción</th></tr></thead><tbody>${VEH.map(k => { const b = B.por_vehiculo[k]; return `<tr><td>${k}</td><td class="n${cls(b.asignacion)}">${spct(b.asignacion, 2)}</td><td class="n${cls(b.seleccion)}">${spct(b.seleccion, 2)}</td><td class="n${cls(b.interaccion)}">${spct(b.interaccion, 2)}</td></tr>`; }).join("")}<tr><td><b>Total</b></td><td class="n">${spct(B.total.asignacion, 2)}</td><td class="n"><b>${spct(B.total.seleccion, 2)}</b></td><td class="n">${spct(B.total.interaccion, 2)}</td></tr></tbody>` : "<tbody><tr><td class='muted'>Sin atribución.</td></tr></tbody>";
  const mg = Math.max(...VEH.map(k => Math.abs(R[k].ciclo.ganancia_clp))) || 1;
  $("ref-n").innerHTML = `<h4>Qué aportó cada fondo</h4><div class="tw"><table class="dt"><thead><tr><th>Fondo</th><th>Invertido neto</th><th>Valor final</th><th>Ganancia</th></tr></thead><tbody>${VEH.map(k => { const c = R[k].ciclo; return `<tr><td>${k}</td><td class="n">${mm(c.invertido_neto)}</td><td class="n">${mm(c.valor_final)}</td><td class="n w" style="--pct:${(Math.abs(c.ganancia_clp) / mg * 100).toFixed(0)}%">${mm(c.ganancia_clp)}</td></tr>`; }).join("")}</tbody></table></div>`;

  // 9 · Lectura (reglas fijas)
  const usd = F["Moneda extranjera"], topLT = LT.filter(r => r.tipo !== "resto")[0], banks = LT.filter(r => r.tipo === "banco").reduce((a, r) => a + r.peso, 0), multi = LT.filter(r => Object.keys(r.por_fondo).length > 1);
  const bullets = [
    `Tiene ${Mx.n_fondos} fondos, pero en riesgo se comporta como ${nf(Mx.enb, 1)} apuestas independientes: ${pct(rv, 0)} del riesgo viene de la renta variable.`,
    `${pct(usd, 0)} del patrimonio sigue al dólar a través del fondo global, aunque todo se compró en pesos.`,
    topLT ? `La mayor exposición por emisor es ${topLT.emisor} (${pct(topLT.peso, 1)})${topLT.tipo === "fondo privado" ? ", un fondo privado sin cartera informada: la concentración real depende de sus facturas" : topLT.tipo === "ETF" ? ", un ETF diversificado: no es concentración de emisor" : ""}.` : "",
    banks > 0.05 ? `La banca chilena suma ${pct(banks, 1)} entre depósitos, bonos y acciones${multi.length ? `; ${multi.filter(r => r.tipo === "banco").map(r => r.emisor).slice(0, 3).join(", ")} aparecen en más de un fondo` : ""}.` : "",
    K.vintage_capital.length === 1 ? `Todo el capital entró en ${K.vintage_capital[0].anio}: sin promedio de precio de entrada.` : "",
  ].filter(Boolean);
  $("c-lec").innerHTML = `<span>${si("info", "9 · Lectura")}</span><span><ul class="plain">${bullets.map(b => `<li>${esc(b)}</li>`).join("")}</ul></span>`;
};
