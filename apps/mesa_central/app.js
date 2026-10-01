/* Mesa Central — núcleo: datos, navegación, Libro y Due diligence. */
"use strict";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const nf = (x, d = 0) => (x ?? 0).toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (x, d = 1) => x == null ? "—" : nf(x * 100, d) + "%";
const spct = (x, d = 1) => x == null ? "—" : (x > 0 ? "+" : "") + nf(x * 100, d) + "%";
const mm = x => x == null ? "—" : "$" + nf(x / 1e6, 1) + "M";
const smm = x => x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + "$" + nf(Math.abs(x) / 1e6, 1) + "M";
const fdate = s => { if (!s) return "—"; const [y, m, d] = String(s).slice(0, 10).split("-"); return `${d}-${m}-${y}`; };
const MON = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const fmonth = s => { const [y, m] = String(s).split("-"); return `${MON[+m - 1]} ${y}`; };
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const cls = x => x == null ? "" : x < 0 ? " neg" : "";
const isDark = () => document.documentElement.dataset.theme === "dark" || (document.documentElement.dataset.theme !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
function alpha(hex, a) { const h = hex.replace("#", ""); const f = h.length === 3 ? h.split("").map(c => c + c).join("") : h; const n = parseInt(f, 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`; }
const store = { get(k, d) { try { const v = localStorage.getItem("mesa2-" + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem("mesa2-" + k, JSON.stringify(v)); } catch (e) {} } };
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function txt(parent, x, y, s, attrs = {}) { const t = el("text", { x, y, ...attrs }, parent); t.textContent = s; return t; }
const ST_LABEL = { ok: "OK", atencion: "Atención", alerta: "Alerta", sin_datos: "Sin datos" };
const si = (st, label) => `<span class="si ${st}">${esc(label ?? ST_LABEL[st] ?? st)}</span>`;

/* Paleta: un color fijo por fondo en toda la aplicación (Carbon: consistencia por serie) */
let L = null;                       // libro.json
let VEH = [], VCOL = {}, vname = {};
const VNAME = { MM: "Money market", RF: "Deuda corporativa", DP: "Facturas", RVL: "Acciones Chile", RVG: "Acciones globales" };
const vc = k => css(VCOL[k] || "--c1");
const retLabel = r => (r.meses >= 12)
  ? { v: pct(r.twr_anual, 1), l: "Rentabilidad anual", n: `${r.meses} meses · acumulada ${pct(r.twr, 1)}` }
  : { v: pct(r.twr, 1), l: "Rentabilidad acumulada", n: `${r.meses} meses: con menos de 12 no se anualiza` };

const cache = {};
async function loadClient(id) {
  if (cache[id]) return cache[id];
  const res = await fetch(`data/clientes/${id}.json`);
  if (!res.ok) throw new Error(`No se pudieron cargar los datos de ${id} (${res.status})`);
  cache[id] = await res.json();
  return cache[id];
}

/* ---------- Navegación ---------- */
const VIEWS = ["libro", "cliente", "dd", "pres"];
const app = { view: "libro", client: null, fund: store.get("fund", "DP") };
const RENDER = {};
function go(v, opts = {}) {
  if (!VIEWS.includes(v)) v = "libro";
  app.view = v;
  VIEWS.forEach(x => { $("v-" + x).hidden = x !== v; });
  document.querySelectorAll("#snav [data-view]").forEach(b => b.setAttribute("aria-current", b.dataset.view === v ? "page" : "false"));
  document.querySelectorAll("#snav [data-client]").forEach(b => b.setAttribute("aria-current", v === "cliente" && b.dataset.client === app.client ? "page" : "false"));
  try { history.replaceState(null, "", "#" + v); } catch (e) {}
  store.set("view", v);
  $("snav").classList.remove("open");
  setTimeout(() => RENDER[v](opts), 0);
  window.scrollTo({ top: 0 });
}
function openClient(id, tab) { app.client = id; store.set("client", id); go("cliente", { tab }); }
document.addEventListener("click", e => {
  const c = e.target.closest("[data-open-client]"); if (c) { openClient(c.dataset.openClient, c.dataset.tab); return; }
  const f = e.target.closest("[data-open-fund]"); if (f) { app.fund = f.dataset.openFund; app._ddFromLink = true; store.set("fund", app.fund); go("dd"); }
});
$("menu").addEventListener("click", () => $("snav").classList.toggle("open"));
// Áreas del menú lateral (los clientes del submenú usan data-open-client)
document.querySelectorAll("#snav [data-view]").forEach(b => b.addEventListener("click", () => go(b.dataset.view)));

/* ---------- Libro ---------- */
RENDER.libro = function () {
  const M = L.monitoreo, A = L.agregados;
  const withAlert = M.filter(a => a.conteo.alerta).length;
  const dims = Object.keys(L.dimensiones);
  const maxF = Math.max(...Object.values(A.por_fondo));
  const adm = Object.entries(A.por_administradora).sort((a, b) => b[1] - a[1]);
  $("v-libro").innerHTML = `
    <div class="pagehead"><span class="lbl">Libro de clientes · datos al ${fdate(L.as_of)}</span><div class="row"><h1>¿En qué cuentas actuar hoy?</h1>
      <div class="meta"><span><b>${M.length}</b> cuentas</span><span><b>${Object.keys(A.por_asesor).length}</b> asesores</span><span>Escenarios <b>${esc(L.biblioteca.version)}</b></span></div></div></div>
    <div class="kpis">
      <div class="kpi"><span class="lbl">Patrimonio administrado</span><span class="v">${mm(A.aum)}</span><span class="helper">aportes ${mm(A.aportes)} · retiros ${mm(A.retiros)}</span></div>
      <div class="kpi"><span class="lbl">Cuentas con alerta</span><span class="v">${withAlert} de ${M.length}</span><span class="helper">al menos una dimensión en alerta</span></div>
      <div class="kpi"><span class="lbl">En fondos sin due diligence completo</span><span class="v">${pct(A.aum_en_fondos_sin_dd / A.aum, 0)}</span><span class="helper">${mm(A.aum_en_fondos_sin_dd)}: falta IDD cualitativa y ODD</span></div>
      <div class="kpi"><span class="lbl">En fondos con señales</span><span class="v">${pct(A.aum_en_fondos_con_senales / A.aum, 0)}</span><span class="helper">${mm(A.aum_en_fondos_con_senales)} con al menos una señal temprana</span></div>
    </div>
    <div class="tile"><div class="th"><h3>Monitoreo por cuenta</h3><div class="legend">${["alerta", "atencion", "ok", "sin_datos"].map(s => si(s)).join("")}</div></div>
      <div class="mon"><table><thead><tr><th>Cuenta, en orden de prioridad</th>${dims.map(d => `<th>${esc(L.dimensiones[d])}</th>`).join("")}</tr></thead><tbody>
      ${M.map((a, i) => `<tr><td><div class="who" data-open-client="${a.id}" role="button" tabindex="0"><span class="helper num">${i + 1} · ${a.id}</span><b>${esc(L.clientes[a.id].nombre)}</b><span class="helper">${esc(a.perfil)} · ${esc(a.asesor)} · ${mm(a.valor)}</span></div></td>
        ${dims.map(d => { const x = a.dimensiones[d]; return `<td title="${esc(x.evidencia.join(" · "))}">${si(x.estado)}<span class="res">${esc(x.resumen)}</span></td>`; }).join("")}</tr>`).join("")}
      </tbody></table></div>
      <p class="helper">${esc(L.notas.join(" "))}</p></div>
    <div class="g2">
      <div class="tile"><h3>Patrimonio por fondo</h3><div class="bars">${L.vehiculos.filter(k => A.por_fondo[k]).sort((a, b) => A.por_fondo[b] - A.por_fondo[a]).map(k => { const f = L.fondos[k];
        return `<div class="brow"><button class="link" data-open-fund="${k}" style="font-size:13px"><span class="sw" style="--c:${vc(k)}"></span>${k} · ${VNAME[k]}</button><div class="track"><i style="left:0;width:${(A.por_fondo[k] / maxF * 100).toFixed(1)}%;background:${vc(k)}"></i></div><span class="num">${mm(A.por_fondo[k])}</span></div>
        <div style="margin:-4px 0 4px 182px;display:flex;gap:12px;flex-wrap:wrap">${si(f.senales.length ? "atencion" : "sin_datos", `${f.estado}${f.senales.length ? ` · ${f.senales.length} señal${f.senales.length > 1 ? "es" : ""}` : ""}`)}<span class="helper">${f.tenedores.length} cliente${f.tenedores.length !== 1 ? "s" : ""}</span></div>`; }).join("")}</div></div>
      <div class="tile"><h3>Patrimonio por administradora</h3><div class="bars">${adm.map(([n, v]) => `<div class="brow"><span>${esc(n)}</span><div class="track"><i style="left:0;width:${(v / adm[0][1] * 100).toFixed(1)}%;background:var(--interactive)"></i></div><span class="num">${pct(v / A.aum, 0)}</span></div>`).join("")}</div>
        <p class="helper">El límite por administradora es de cada cliente (IPS); aquí se ve la exposición del libro.</p></div>
    </div>
    <div class="tile"><h3>Exposición por cliente</h3><div class="tw"><table class="dt"><thead><tr><th>Cliente</th><th>Patrimonio</th>${L.vehiculos.map(k => `<th>${k}</th>`).join("")}<th>Límite por administradora</th></tr></thead><tbody>
      ${M.map(a => { const w = L.expo[a.id] || {}; return `<tr><td><button class="link" data-open-client="${a.id}">${a.id}</button> <span class="helper">${esc(a.perfil)}</span></td><td class="n">${mm(a.valor)}</td>${L.vehiculos.map(k => `<td class="n">${w[k] ? pct(w[k], 0) : "·"}</td>`).join("")}<td class="n">${L.limite_adm[a.id] == null ? "—" : nf(L.limite_adm[a.id]) + "%"}</td></tr>`; }).join("")}
    </tbody></table></div></div>`;
  document.querySelectorAll("#v-libro .who").forEach(w => w.addEventListener("keydown", e => { if (e.key === "Enter") openClient(w.dataset.openClient); }));
};

/* ---------- Due diligence ---------- */
/* Dossier completo de un fondo del universo de construcción (lo llama dd.js). */
function renderModelDossier(host) {
  const F = L.fondos, f = F[app.fund], fi = f.ficha, ca = fi.cartera || {}, i = f.idd, A = L.agregados;
  const row = (l, v) => `<dt>${l}</dt><dd>${v}</dd>`;
  const stepCol = v => v.startsWith("completa") ? "var(--ok)" : v.startsWith("parcial") || v.startsWith("señales") ? "var(--warn)" : "var(--border-strong)";
  const rel = f.relativo;
  host.innerHTML = `
    <div class="tile"><div class="th"><div><span class="lbl">${app.fund} · RUN ${esc(fi.rut)}</span><h2>${esc(fi.nombre_completo)}</h2></div><div style="display:flex;gap:12px;flex-wrap:wrap">${si("sin_datos", "Approved List: " + f.estado)}${f.senales.length ? si("atencion", `${f.senales.length} señal${f.senales.length > 1 ? "es" : ""}`) : si("ok", "Sin señales")}</div></div>
      <div class="steps">${Object.entries(f.etapas).map(([s, v]) => `<div class="step" style="--sc:${stepCol(v)}"><b>${esc(s)}</b><span>${esc(v)}</span></div>`).join("")}</div>
      <div class="notif ${f.elegibilidad.elegible ? "ok" : "err"}"><span>${si(f.elegibilidad.elegible ? "ok" : "alerta", f.elegibilidad.elegible ? "Elegible" : "No elegible")}</span><span>${esc(f.elegibilidad.motivo)}. Nivel máximo en decisiones sobre este fondo: ${f.elegibilidad.nivel_maximo_decisiones_de_fondo}. Siguiente paso: ${esc(f.elegibilidad.propuesta)}.</span></div></div>
    <div class="g2">
      <div class="tile"><h3>Ficha CMF</h3><dl class="kv">${[["Administradora", esc(fi.administradora)], ["Tipo", `${esc(fi.tipo)} · ${esc(fi.tipo_fondo)} · ${esc(fi.inversionista)}`], ["Inicio de operaciones", fdate(fi.inicio_operaciones)], ["Reglamento vigente", fdate(fi.fecha_reglamento)], ["Rescate", esc(fi.liquidez_declarada || "sin dato en la ficha")], ["Clase y subclase (taxonomía AFI)", `${esc(f.clase)} · ${esc(f.subclase)}`]].map(([a, b]) => row(a, b)).join("")}</dl></div>
      <div class="tile"><h3>Cartera informada (IFRS ${esc(ca.periodo || "")})</h3><dl class="kv">${[["Tamaño", ca.aum_mm_clp ? "$" + nf(ca.aum_mm_clp) + " millones" : "—"], ["Posiciones", nf(ca.posiciones)], ["Mayor posición", `${esc(ca.mayor_emisor)}: ${nf(ca.mayor_emisor_pct, 1)}%`], ["5 mayores", ca.top5_pct == null ? "—" : nf(ca.top5_pct, 0) + "%"], ["Emisores efectivos", ca.efectivos == null ? "—" : nf(ca.efectivos, 1)], ["Composición", esc(ca.detalle)], ["Rotación del trimestre", `${ca.incorporaciones} entradas, ${ca.liquidaciones} salidas`]].map(([a, b]) => row(a, b)).join("")}</dl>${ca.look_through ? `<p class="helper">${esc(ca.look_through)}</p>` : ""}</div>
    </div>
    <div class="g2">
      <div class="tile"><h3>IDD cuantitativa</h3><dl class="kv">${[["Datos de valor cuota", `${fdate(i.desde_datos)} a ${fdate(i.hasta)} (${nf(i.anios_datos, 1)} años)`], ["Retorno 1 año", pct(i.retorno_1a, 1)], ["Retorno 3 años (anual)", pct(i.retorno_3a, 1)], ["Retorno 5 años (anual)", pct(i.retorno_5a, 1)], ["Volatilidad 3 años", pct(i.volatilidad_3a, 1)], ["Máxima caída 3 años", pct(i.max_drawdown_3a, 1)], ["Sharpe 3 años", i.sharpe_3a == null ? "no se informa" : nf(i.sharpe_3a, 2)], ["Calmar 3 años", i.calmar_3a == null ? "no se informa" : nf(i.calmar_3a, 2)]].map(([a, b]) => row(a, `<span class="num">${b}</span>`)).join("")}</dl>
        ${i.advertencia ? `<div class="notif warn"><span>${si("atencion", "Advertencia")}</span><span>${esc(i.advertencia)}</span></div>` : ""}
        ${rel ? `<h4>Contra su índice pasivo (S&amp;P/CLX IPSA, ${rel.n_obs} meses)</h4><dl class="kv">${[["Exceso anual", spct(rel.exceso_anual, 1)], ["Tracking error", pct(rel.tracking_error, 1)], ["Information ratio", nf(rel.information_ratio, 2)], ["Beta", nf(rel.beta, 2)], ["Meses sobre el índice", pct(rel.hit_ratio, 0)]].map(([a, b]) => row(a, `<span class="num">${b}</span>`)).join("")}</dl>` : '<p class="helper">Sin índice pasivo elegible en el universo: no se calcula retorno relativo.</p>'}
        <div class="chart" id="dd-nav"></div><p class="helper">Valor cuota semanal desde oct-2021 (base 100).</p></div>
      <div class="tile"><h3>Señales tempranas (Checklist 2, Vol. II)</h3>${f.senales.length ? f.senales.map(s => `<div class="sig"><b>${esc(s.tipo)}</b><span>${esc(s.senal)}</span><em>${esc(s.evidencia)}</em></div>`).join("") : '<p class="muted">Sin señales con los umbrales vigentes.</p>'}
        <p class="helper">Una señal no cambia el estado: abre el análisis de causa raíz (cíclico, estructural u operacional) antes del Comité. Una concentración puede ser legítima: un ETF que replica un índice global no equivale a un fondo privado.</p></div>
    </div>
    <div class="g2">
      <div class="tile"><h3>Pilares cualitativos</h3><div class="chk">${Object.entries(f.pilares).map(([p, v]) => `${si("sin_datos", "Pendiente")}<span><b>${p}</b> · ${esc(v.que_falta)}<br><span class="helper">Fuente: ${esc(v.fuente_requerida)}</span></span>`).join("")}</div>
        <p class="helper">No se infieren de la rentabilidad: eso sería performance chasing (Vol. II, principio 4).</p></div>
      <div class="tile"><h3>Revisión operacional (ODD)</h3><div class="chk">${Object.keys(f.odd.items).map(p => `${si("sin_datos", "Pendiente")}<span>${esc(p)}</span>`).join("")}</div>
        <div class="notif err"><span>${si("alerta", "Veto")}</span><span>${esc(f.odd.regla)}</span></div></div>
    </div>
    <div class="tile"><h3>Clientes con este fondo</h3><div class="tw"><table class="dt"><thead><tr><th>Cliente</th><th>Perfil</th><th>Valor en el fondo</th><th>Peso en su cartera</th></tr></thead><tbody>
      ${f.tenedores.slice().sort((a, b) => b.valor - a.valor).map(h => `<tr><td><button class="link" data-open-client="${h.cliente}">${h.cliente} · ${esc(L.clientes[h.cliente].nombre)}</button></td><td>${esc(L.clientes[h.cliente].perfil)}</td><td class="n">${mm(h.valor)}</td><td class="n">${pct(h.valor / L.clientes[h.cliente].valor, 0)}</td></tr>`).join("") || '<tr><td colspan="4" class="muted">Ningún cliente lo tiene.</td></tr>'}
    </tbody></table></div></div>`;
  // mini gráfico de valor cuota (base 100)
  const navHost = $("dd-nav"); const pts = f.nav; if (!pts.length) return;
  const W = Math.max(320, navHost.clientWidth || 600), H = 150, m = { l: 40, r: 8, t: 8, b: 20 }, base = pts[0].v;
  const vals = pts.map(p => p.v / base * 100), lo = Math.min(...vals), hi = Math.max(...vals);
  const x = i => m.l + i / (pts.length - 1) * (W - m.l - m.r), y = v => m.t + (1 - (v - lo) / (hi - lo || 1)) * (H - m.t - m.b);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Valor cuota base 100" }, navHost);
  [lo, (lo + hi) / 2, hi].forEach(v => { el("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v), stroke: css("--border") }, svg); txt(svg, m.l - 6, y(v) + 4, nf(v, 0), { "text-anchor": "end" }); });
  el("path", { d: vals.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(""), fill: "none", stroke: vc(app.fund), "stroke-width": 2 }, svg);
  [0, Math.floor(pts.length / 2), pts.length - 1].forEach(i => txt(svg, x(i), H - 4, fmonth(pts[i].f.slice(0, 7)), { "text-anchor": i === 0 ? "start" : i === pts.length - 1 ? "end" : "middle" }));
};

/* ---------- Arranque ---------- */
(async function boot() {
  try {
    const res = await fetch("data/libro.json");
    if (!res.ok) throw new Error("libro.json " + res.status);
    L = await res.json();
  } catch (e) { $("v-libro").innerHTML = `<div class="notif err"><span>${si("alerta", "Error")}</span><span>No se pudieron cargar los datos: ${esc(e.message)}</span></div>`; return; }
  VEH = L.vehiculos; VEH.forEach((k, i) => { VCOL[k] = `--c${i + 1}`; vname[k] = VNAME[k] || k; });
  // exposición y límites por cliente para la tabla del libro
  L.expo = {}; L.limite_adm = {};
  $("asof").textContent = "Datos al " + fdate(L.as_of);
  $("b-alert").textContent = L.monitoreo.filter(a => a.conteo.alerta).length;
  $("b-cli").textContent = L.monitoreo.length;
  $("b-fund").textContent = VEH.length;
  $("nav-clients").innerHTML = L.monitoreo.map(a => `<button class="cl" data-client="${a.id}" data-open-client="${a.id}">${esc(L.clientes[a.id].nombre)} ${a.conteo.alerta ? `<span class="si alerta" aria-label="con alerta"></span>` : ""}</button>`).join("");
  app.client = store.get("client", L.monitoreo[0].id);
  // pesos de cada cliente: se cargan en segundo plano para la tabla de exposición
  Promise.all(L.monitoreo.map(a => loadClient(a.id).then(c => { L.expo[a.id] = c.resumen.pesos_actuales; L.limite_adm[a.id] = c.ips.admin_max; }).catch(() => {})))
    .then(() => { if (app.view === "libro") RENDER.libro(); });
  let first = location.hash.slice(1); if (!VIEWS.includes(first)) first = store.get("view", "libro");
  go(first);
})();
addEventListener("hashchange", () => { const h = location.hash.slice(1); if (VIEWS.includes(h) && h !== app.view) go(h); });
const retheme = () => RENDER[app.view] && RENDER[app.view]({});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", retheme);
new MutationObserver(retheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
