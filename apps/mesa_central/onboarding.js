/* Mesa Central — Nuevo cliente: onboarding y construcción de la cartera desde cero.
   El motor de construcción está portado desde Python con las MISMAS reglas (grilla de 5 pp,
   MVO robusto con tope de volatilidad, alternativas MinVol y ERC, Trade-off Detection,
   Recommendation Layer y Monte Carlo con bootstrap por bloques con el mismo generador
   aleatorio que Python). Los supuestos de mercado vienen de data/motor.json, que exporta el
   motor Python; al cargar se verifica la paridad contra un caso calculado por el motor real. */
"use strict";
let MO = null;                       // motor.json
async function loadMotor() {
  if (MO) return MO;
  const res = await fetch("data/motor.json");
  if (!res.ok) throw new Error("motor.json " + res.status);
  MO = await res.json();
  MO.ix = Object.fromEntries(MO.vehiculos.map((k, i) => [k, i]));
  MO.ret = Object.fromEntries(MO.vehiculos.map((k, i) => [k, MO.historia.retornos[i]]));
  return MO;
}

/* ---------- Generador aleatorio de Python (MT19937 + random.seed(int) + randrange) ---------- */
class PyRandom {
  constructor(seed) { this.mt = new Uint32Array(624); this.idx = 624; this.initByArray([seed >>> 0]); }
  initGenrand(s) { const mt = this.mt; mt[0] = s >>> 0; for (let i = 1; i < 624; i++) mt[i] = (Math.imul(1812433253, mt[i - 1] ^ (mt[i - 1] >>> 30)) + i) >>> 0; }
  initByArray(key) {
    const mt = this.mt; this.initGenrand(19650218);
    let i = 1, j = 0;
    for (let k = Math.max(624, key.length); k; k--) {
      mt[i] = ((mt[i] ^ Math.imul(mt[i - 1] ^ (mt[i - 1] >>> 30), 1664525)) + key[j] + j) >>> 0;
      i++; j++; if (i >= 624) { mt[0] = mt[623]; i = 1; } if (j >= key.length) j = 0;
    }
    for (let k = 623; k; k--) {
      mt[i] = ((mt[i] ^ Math.imul(mt[i - 1] ^ (mt[i - 1] >>> 30), 1566083941)) - i) >>> 0;
      i++; if (i >= 624) { mt[0] = mt[623]; i = 1; }
    }
    mt[0] = 0x80000000; this.idx = 624;
  }
  uint32() {
    const mt = this.mt;
    if (this.idx >= 624) {
      for (let k = 0; k < 624; k++) {
        const y = (mt[k] & 0x80000000) | (mt[(k + 1) % 624] & 0x7fffffff);
        mt[k] = mt[(k + 397) % 624] ^ (y >>> 1) ^ (y & 1 ? 0x9908b0df : 0);
      }
      this.idx = 0;
    }
    let y = mt[this.idx++];
    y ^= y >>> 11; y ^= (y << 7) & 0x9d2c5680; y ^= (y << 15) & 0xefc60000; y ^= y >>> 18;
    return y >>> 0;
  }
  randrange(n) { const k = 32 - Math.clz32(n); let r = this.uint32() >>> (32 - k); while (r >= n) r = this.uint32() >>> (32 - k); return r; }
}

/* ---------- Motor (mismas reglas y mismo orden de operaciones que Python) ---------- */
const E = {
  cov: (i, j) => MO.cma.cov[MO.ix[i]][MO.ix[j]],
  pvar(w) { let s = 0; for (const i in w) for (const j in w) s += w[i] * w[j] * E.cov(i, j); return s; },
  pret(w) { let s = 0; for (const k in w) s += w[k] * MO.cma.mu[MO.ix[k]]; return s; },
  vol: k => Math.sqrt(E.cov(k, k)),
  hhi(w) { let s = 0; for (const k in w) s += w[k] * w[k]; return s; },
  rc(w) { const m = {}; for (const i in w) { let s = 0; for (const j in w) s += E.cov(i, j) * w[j]; m[i] = s; }
    let v = 0; for (const i in w) v += w[i] * m[i]; const o = {}; for (const i in w) o[i] = w[i] * m[i] / v; return o; },
  grid(keys, caps, step = MO.paso_grilla) {           // engines/construction.py grid_portfolios
    const units = Math.round(1 / step), cp = keys.map(k => Math.min(units, Math.floor(caps[k] / step + 1e-9))), alloc = keys.map(() => 0), out = [];
    const rec = (i, rem) => {
      if (i === keys.length - 1) { if (rem <= cp[i]) { alloc[i] = rem; const w = {}; keys.forEach((k, j) => { if (alloc[j]) w[k] = alloc[j] / units; }); out.push(w); } return; }
      for (let u = 0; u <= Math.min(rem, cp[i]); u++) { alloc[i] = u; rec(i + 1, rem - u); }
      alloc[i] = 0;
    };
    rec(0, units); return out;
  },
  erc(keys, it = 500) {                                // flows/construction.py equal_risk_contribution
    let w = {}; keys.forEach(k => { w[k] = 1 / E.vol(k); }); let s = 0; for (const k in w) s += w[k]; for (const k in w) w[k] /= s;
    for (let n = 0; n < it; n++) { const rc = E.rc(w); const x = {}; keys.forEach(k => { x[k] = w[k] * Math.pow(1 / keys.length / rc[k], 0.5); }); s = 0; for (const k in x) s += x[k]; for (const k in x) x[k] /= s; w = x; }
    return w;
  },
  boot(w, months, value0, contrib, checkpoints) {      // engines/goals.py bootstrap_paths
    const R = MO.ret, n = MO.historia.meses.length, block = +MO.params.mc_block_months, sims = +MO.params.mc_simulations;
    const port = []; for (let t = 0; t < n; t++) { let s = 0; for (const k in w) s += w[k] * R[k][t]; port.push(s); }
    const rng = new PyRandom(MO.semilla), finals = new Float64Array(sims);
    for (let s = 0; s < sims; s++) {
      let v = value0, m = 0;
      while (m < months) { const st = rng.randrange(n); for (let j = 0; j < block; j++) { if (m >= months) break; v = v * (1 + port[(st + j) % n]) + contrib; m++; if (checkpoints && checkpoints[m]) checkpoints[m].push(v); } }
      finals[s] = v;
    }
    return Array.from(finals);
  },
};
const pyRound = x => { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : (f % 2 === 0 ? f : f + 1); };
const pctl = (sorted, q) => sorted[Math.min(sorted.length - 1, Math.max(0, pyRound(q * (sorted.length - 1))))];
const monthsBetween = (a, b) => { const [ya, ma] = a.split("-").map(Number), [yb, mb] = b.split("-").map(Number); return (yb - ya) * 12 + (mb - ma); };
function horizonOf(g) {
  if (!g.fecha) return "corto";
  const m = monthsBetween(MO.as_of, g.fecha), P = MO.params;
  return m <= P.risk_horizon_short_max_months ? "corto" : m <= P.risk_horizon_medium_max_months ? "medio" : "largo";
}
const CAPP = { corto: "vol_cap_short_pct", medio: "vol_cap_medium_pct", largo: "vol_cap_long_pct" };
function keysCaps(h) {
  const P = MO.params;
  if (h === "corto") { const ks = MO.vehiculos.filter(k => MO.subclase[k] === P.short_horizon_eligible_subclass); return [ks, Object.fromEntries(ks.map(k => [k, 1]))]; }
  return [MO.vehiculos.slice(), Object.fromEntries(MO.vehiculos.map(k => [k, P.max_weight_per_vehicle_pct / 100]))];
}
const ADV = () => MO.escenarios.adverso.shocks;
const CDIMS = [["retorno_esperado", "Retorno esperado", "Construction", "mayor", "pct"], ["volatilidad_ex_ante", "Volatilidad ex-ante", "Risk", "menor", "pct"],
  ["retorno_escenario_adverso", "Retorno en escenario adverso", "Scenario", "mayor", "pct"], ["prob_exito", "Probabilidad de lograr la meta", "ClientGoal", "mayor", "pct"],
  ["hhi", "Concentración (HHI)", "Diversification", "menor", "num"], ["max_contribucion_riesgo", "Mayor aporte al riesgo de un fondo", "Diversification", "menor", "pct"]];
function tradeoffs(alts, ref) {                       // decision/tradeoff.py detect_tradeoffs (sin umbral: OQ4 abierta)
  const r = alts[ref], out = [];
  for (const [key, a] of Object.entries(alts)) {
    if (key === ref) continue;
    const eff = [];
    for (const [k, nombre, , mejor, fmt] of CDIMS) { const x = r[k], y = a[k]; if (x == null || y == null) continue; const d = y - x; if (Math.abs(d) <= 1e-4) continue;
      const fx = v => fmt === "num" ? nf(v, 3) : pct(v, 2); eff.push({ nombre, mejora: mejor === "menor" ? d < 0 : d > 0, texto: `${nombre}: ${fx(x)} → ${fx(y)}` }); }
    const mej = eff.filter(e => e.mejora), emp = eff.filter(e => !e.mejora);
    if (mej.length && emp.length) out.push({ alternativa: key, conflicto: `${a.nombre} frente a ${r.nombre}: mejora ${mej.map(e => e.nombre.toLowerCase()).join(", ")} a cambio de ${emp.map(e => e.nombre.toLowerCase()).join(", ")}.`, mejora: mej.map(e => e.texto), empeora: emp.map(e => e.texto) });
  }
  return out;
}
const ALT_NAMES = { MVO: "MVO robusto (CORE)", MINVOL: "Mínima volatilidad (CORE)", ERC: "Paridad de riesgo ERC (ADVANCED, referencia)" };
const NO_ALTS = "No existen alternativas cuantitativamente evaluables con la información disponible.";

/* Construcción completa de un prospecto: ConstructionEngine + ClientGoalEngine + construction_alternatives */
function runEngine(d, blocking = []) {
  const P = MO.params, delta = +P.risk_aversion_delta, ipsVol = d.riesgo.vol == null || d.riesgo.vol === "" ? null : +d.riesgo.vol / 100;
  const goals = d.metas.filter(goalReady);
  const sleeves = {}, blocked = {}, frontier = {}, alts = {}, goalRes = {};
  for (const g of goals) {
    const h = horizonOf(g); let cap = P[CAPP[h]] / 100, fuente = "horizonte";
    if (ipsVol != null && ipsVol < cap) { cap = ipsVol; fuente = "IPS"; }
    const [ks, caps] = keysCaps(h), grid = E.grid(ks, caps);
    let best = null, bu = -Infinity; const pts = [];
    for (const w of grid) { const v = E.pvar(w); pts.push([Math.sqrt(v), E.pret(w)]); if (Math.sqrt(v) > cap + 1e-12) continue; const u = E.pret(w) - delta / 2 * v; if (u > bu + 1e-15) { best = w; bu = u; } }
    frontier[g.key] = { pts, grid: grid.length, feasible: pts.filter(p => p[0] <= cap + 1e-12).length, ks };
    if (!best) { blocked[g.key] = `Ninguna cartera de la grilla cumple volatilidad ≤ ${pct(cap, 1)} con los vehículos elegibles.`; continue; }
    sleeves[g.key] = { horizonte: h, tope: cap, fuente, pesos: best, ret: E.pret(best), vol: Math.sqrt(E.pvar(best)), ks, caps, grid };
  }
  let tc = 0; for (const g of goals) if (sleeves[g.key]) tc += +g.capital;
  const total = {}; if (tc > 0) for (const g of goals) { const s = sleeves[g.key]; if (!s) continue; const sh = +g.capital / tc; for (const k in s.pesos) total[k] = (total[k] || 0) + sh * s.pesos[k]; }
  // ClientGoal: probabilidad y abanico con la cartera MVO de cada meta
  for (const g of goals) {
    const s = sleeves[g.key]; if (!s) continue;
    if (!g.fecha) { goalRes[g.key] = { tipo: "reserva", cobertura: +g.capital / +g.objetivo }; continue; }
    const months = monthsBetween(MO.as_of, g.fecha); if (months <= 0) continue;
    const marks = {}; for (let m = 12; m < months; m += 12) marks[m] = []; marks[months] = [];
    const fin = E.boot(s.pesos, months, +g.capital, +g.aporte || 0, marks).sort((a, b) => a - b);
    const path = [{ mes: 0, p10: +g.capital, p25: +g.capital, p50: +g.capital, p75: +g.capital, p90: +g.capital }];
    Object.keys(marks).map(Number).sort((a, b) => a - b).forEach(m => { const v = marks[m].sort((a, b) => a - b); path.push({ mes: m, p10: pctl(v, .1), p25: pctl(v, .25), p50: pctl(v, .5), p75: pctl(v, .75), p90: pctl(v, .9) }); });
    goalRes[g.key] = { tipo: "meta", meses: months, prob_exito: fin.filter(v => v >= +g.objetivo).length / fin.length, p10: pctl(fin, .1), p50: pctl(fin, .5), p90: pctl(fin, .9), trayectoria: path };
  }
  // Carteras alternativas por meta (DF v1.1 caso 3)
  for (const g of goals) {
    const s = sleeves[g.key]; if (!s) continue;
    const out = { alternativas: {} };
    if (s.ks.length < 2) { alts[g.key] = { ...out, nivel: 1, recomendada: null, motivo_nivel: "Un solo vehículo elegible para el horizonte: no hay carteras alternativas que comparar." }; continue; }
    let mv = null, mvv = Infinity; for (const w of s.grid) { const v = E.pvar(w); if (v < mvv) { mv = w; mvv = v; } }
    const W = { MVO: { ...s.pesos }, MINVOL: mv, ERC: E.erc(s.ks) };
    const months = g.fecha ? monthsBetween(MO.as_of, g.fecha) : null;
    for (const [key, w0] of Object.entries(W)) {
      const w = {}; for (const k in w0) if (w0[k] > 1e-9) w[k] = w0[k];
      const vol = Math.sqrt(E.pvar(w)), rc = E.rc(w), reasons = [];
      const over = Object.keys(w).filter(k => w[k] > s.caps[k] + 1e-9).sort();
      if (over.length) reasons.push(`supera el tope por fondo en ${over.join(", ")}`);
      if (vol > s.tope + 1e-12) reasons.push(`volatilidad ${pct(vol, 1)} sobre el tope del horizonte (${pct(s.tope, 1)})`);
      let adv = 0; for (const k in w) adv += w[k] * ADV()[k];
      const a = { nombre: ALT_NAMES[key], pesos: w, retorno_esperado: E.pret(w), volatilidad_ex_ante: vol, utilidad: E.pret(w) - delta / 2 * vol * vol,
        retorno_escenario_adverso: adv, hhi: E.hhi(w), contribucion_riesgo: rc, max_contribucion_riesgo: Math.max(...Object.values(rc)), admisible: !reasons.length, motivo_inadmisible: reasons.join("; ") || null, prob_exito: null };
      if (months) { const f = E.boot(w, months, +g.capital, +g.aporte || 0); a.prob_exito = f.filter(v => v >= +g.objetivo).length / f.length; }
      out.alternativas[key] = a;
    }
    if (s.ks.every(k => Math.abs((W.MINVOL[k] || 0) - (W.MVO[k] || 0)) < 1e-9)) { delete out.alternativas.MINVOL; out.descartadas = { MINVOL: "coincide con la cartera MVO" }; }
    const A = out.alternativas; out.tradeoffs = tradeoffs(A, "MVO");
    const crit = `mayor utilidad μ − ${delta}/2·σ² entre las carteras admisibles (MVO robusto, QM VII)`, cands = Object.keys(A).filter(k => A[k].admisible);
    Object.assign(out, { criterio: crit, sensibilidad: { admisibles: frontier[g.key].feasible, grilla: frontier[g.key].grid } });
    if (blocking.length) Object.assign(out, { nivel: 2, recomendada: null, motivo_nivel: `Nivel 2: se muestran las alternativas, pero faltan datos que bloquean una recomendación: ${blocking.join(", ")}.` });
    else if (!cands.length) Object.assign(out, { nivel: 2, recomendada: null, motivo_nivel: `Nivel 2: ninguna alternativa cumple el criterio (${crit}); el WM decide entre las alternativas mostradas sin recomendación analítica.` });
    else { const ch = cands.reduce((b, k) => A[k].utilidad > A[b].utilidad ? k : b, cands[0]);
      Object.assign(out, { nivel: 3, recomendada: ch, motivo_nivel: "Nivel 3 es el techo: el sistema no ejecuta (Nivel 4 no existe) ni asigna quién decide.",
        recomendacion: `Bajo el criterio de ${crit} y los supuestos declarados, la alternativa ${ch} (${A[ch].nombre}) presenta el resultado más consistente con los objetivos analizados.` }); }
    alts[g.key] = out;
  }
  return { goals, sleeves, blocked, frontier, total, goalRes, alts, capital: tc };
}

/* Simulación histórica: cartera comprada al inicio del episodio y mantenida (engines/scenario.py episode_path) */
function episodeRun(values, e) {
  const t0 = Object.values(values).reduce((a, b) => a + b, 0), path = [];
  for (let i = 0; i < e.fechas.length; i++) { let s = 0; for (const k in values) s += values[k] * e.rel[k][i]; path.push({ f: e.fechas[i], t: s }); if (e.fechas[i] > e.hasta && s >= t0) break; }
  let tr = path[0]; path.forEach(p => { if (p.t < tr.t) tr = p; });
  const rec = path.find(p => p.f > tr.f && p.t >= t0), end = [...path].reverse().find(p => p.f <= e.hasta) || path[path.length - 1];
  const days = (a, b) => Math.round((new Date(b) - new Date(a)) / 864e5);
  return { path, t0, caida: tr.t / t0 - 1, fondo: tr.f, dias_fondo: days(e.desde, tr.f), recupera: rec ? rec.f : null, dias_rec: rec ? days(tr.f, rec.f) : null, al_fin: end.t / t0 - 1 };
}

/* Paridad con el motor Python: el caso de control lo calculó LifecycleSimulation.construct */
function parityCheck() {
  const C = MO.control, d = { riesgo: { vol: C.vol_ips_pct }, metas: C.metas.map(m => ({ ...m, reserva: !m.fecha })) };
  const r = runEngine(d), X = C.esperado, diffs = [];
  const near = (a, b, tol) => a == null && b == null || (a != null && b != null && Math.abs(a - b) <= tol);
  for (const [g, s] of Object.entries(X.sleeves)) { const j = r.sleeves[g]; if (!j) { diffs.push(`${g}: sin cartera`); continue; }
    for (const k of new Set([...Object.keys(s.pesos), ...Object.keys(j.pesos)])) if (!near(s.pesos[k] || 0, j.pesos[k] || 0, 1e-12)) diffs.push(`${g}.${k}`); }
  for (const [g, m] of Object.entries(X.metas)) { const j = r.goalRes[g] || {}; ["prob_exito", "p10", "p50", "p90"].forEach(q => { if (m[q] != null && !near(m[q], j[q], Math.abs(m[q]) * 1e-9)) diffs.push(`${g}.${q}`); }); }
  for (const [g, a] of Object.entries(X.alternativas)) { const j = r.alts[g] || {}; if (a.nivel !== j.nivel || a.recomendada !== j.recomendada) diffs.push(`${g}.nivel`);
    for (const [k, x] of Object.entries(a.alts)) { const y = (j.alternativas || {})[k]; if (!y) { diffs.push(`${g}.${k}`); continue; } if (!near(x.prob_exito, y.prob_exito, 2e-4)) diffs.push(`${g}.${k}.prob`); if (!near(x.volatilidad_ex_ante, y.volatilidad_ex_ante, 1e-9)) diffs.push(`${g}.${k}.vol`); } }
  return { ok: !diffs.length, diffs, metas: Object.keys(X.sleeves).length };
}

/* ---------- Estado del asistente (borrador por asesor en este navegador) ---------- */
const OB_STEPS = [["cliente", "Cliente"], ["riesgo", "Perfil de riesgo"], ["patrimonio", "Patrimonio y restricciones"], ["metas", "Metas"],
  ["datos", "Completitud"], ["construccion", "Construcción"], ["proyeccion", "Proyección y stress"], ["propuesta", "Propuesta"]];
const blankDraft = () => ({ step: 0, id: "PRO-" + Math.random().toString(36).slice(2, 7).toUpperCase(),
  cliente: { nombre: "", nacimiento: "", pais: "Chile", segmento: "Wealth, persona natural", asesor: "", moneda: "CLP" },
  riesgo: { perfil: "", puntaje: "", capacidad: "", capacidad_motivo: "", vol: "", var: "", es: "", dd: "" },
  patrimonio: { total: "", fuera: "", capital_humano: "", activos_nf: "", pasivos: "", compromisos: "", esg: "", regulatorias: "", familiares: "", admin: "" },
  metas: [] });
const ob = { d: store.get("onb", null) || blankDraft(), res: null, parity: null, saved: [] };
const obSave = () => store.set("onb", ob.d);
const has = v => v !== "" && v != null;
const goalReady = g => has(g.objetivo) && +g.objetivo > 0 && has(g.capital) && +g.capital >= 0 && (!g.fecha || monthsBetween(MO.as_of, g.fecha) > 0) && (g.fecha || g.reserva);
const newGoal = (n) => ({ key: "m" + Date.now().toString(36) + n, nombre: "", prioridad: "importante", objetivo: "", fecha: "", reserva: false, capital: "", aporte: 0, prob_deseada: "", liquidez: "" });
const GOAL_TEMPLATES = [["Fondo de emergencia", { prioridad: "esencial", reserva: true, liquidez: "disponible en 3 días hábiles" }],
  ["Pie de vivienda", { prioridad: "importante", anios: 3, prob_deseada: 80, liquidez: "efectivo en la fecha" }],
  ["Educación de los hijos", { prioridad: "importante", anios: 8, prob_deseada: 80, liquidez: "pagos anuales desde la fecha" }],
  ["Capital de retiro", { prioridad: "esencial", anios: 20, prob_deseada: 75, liquidez: "retiros programados" }]];

/* Catálogo de información (ESFS 9.1 / DF 5.2): estado de lo que declara el cliente */
function clientCatalogValue(v) {
  const d = ob.d, r = d.riesgo, p = d.patrimonio, G = d.metas, dated = G.filter(g => g.fecha);
  const all = a => a.length && a.every(has) ? "ok" : null;
  switch (v) {
    case "IPS vigente y firmado": return "borrador";
    case "Moneda base": return "CLP";
    case "País de residencia y segmento": return has(d.cliente.pais) && has(d.cliente.segmento) ? "ok" : null;
    case "Perfil y tolerancia al riesgo declarada": return has(r.perfil) ? "ok" : null;
    case "Capacidad de riesgo (objetiva)": return has(r.capacidad) ? "ok" : null;
    case "Límites de riesgo por perfil (vol / VaR / ES)": return all([r.vol, r.var, r.es]);
    case "Drawdown tolerado": return has(r.dd) ? "ok" : null;
    case "Patrimonio total (incluye fuera de AFI)": return has(p.total) ? "ok" : null;
    case "Inversiones existentes fuera de AFI": return has(p.fuera) ? "ok" : null;
    case "Life balance sheet (capital humano, activos, pasivos, compromisos)": return all([p.capital_humano, p.activos_nf, p.pasivos, p.compromisos]);
    case "Restricciones ESG / regulatorias / familiares": return all([p.esg, p.regulatorias, p.familiares]);
    case "Límites de concentración (emisor / gestor / país)": return has(p.admin) ? "ok" : null;
    case "Monto y fecha de cada meta": return G.length && G.every(goalReady) ? "ok" : null;
    case "Horizonte de cada meta (corto / medio / largo)": return G.length && G.every(goalReady) ? "derivado" : null;
    case "Moneda de cada meta": return G.length ? "CLP" : null;
    case "Probabilidad deseada de cada meta": return dated.length ? all(dated.map(g => g.prob_deseada)) : G.length ? "ok" : null;
    case "Prioridad relativa de cada meta": return G.length ? all(G.map(g => g.prioridad)) : null;
    case "Liquidez requerida en la fecha de cada meta": return G.length ? all(G.map(g => g.liquidez)) : null;
    case "Calendario de flujos esperados (aportes, retiros, impuestos, gastos)": return G.length && G.every(goalReady) ? "derivado" : null;
  }
  return null;
}
function evaluateCatalog() {
  return MO.catalogo.map(c => {
    if (c.origen === "post") return { ...c, estado: "post", comportamiento: "—" };
    if (c.origen === "plataforma") return c;
    const v = clientCatalogValue(c.variable);
    if (v === "borrador") return { ...c, estado: "degraded", comportamiento: "ADVERTENCIA", nota: "se redacta con esta propuesta y se firma antes de ejecutar" };
    if (v === "derivado") return { ...c, estado: "available", comportamiento: "—", nota: "derivado de las metas" };
    if (v != null) return { ...c, estado: "available", comportamiento: "—" };
    return { ...c, estado: c.criticidad === "CRITICAL" ? "missing_critical" : "missing_non_critical", comportamiento: c.criticidad === "CRITICAL" ? "BLOQUEO" : "ADVERTENCIA" };
  });
}
const blockingMissing = cat => cat.filter(c => c.origen === "cliente" && c.estado === "missing_critical").map(c => c.variable);
function engineGate() {                              // datos CRITICAL del ConstructionEngine (required_critical_data)
  const miss = [];
  if (!has(ob.d.riesgo.perfil)) miss.push("perfil de riesgo del cliente");
  if (!ob.d.metas.length) miss.push("al menos una meta");
  ob.d.metas.forEach((g, i) => { if (!goalReady(g)) miss.push(`meta ${i + 1} (${g.nombre || "sin nombre"}): monto, capital y fecha futura o reserva`); });
  return miss;
}
function compute() {
  const cat = evaluateCatalog(), gate = engineGate();
  ob.res = gate.length ? { gate, cat } : { ...runEngine(ob.d, blockingMissing(cat)), gate, cat };
  return ob.res;
}

/* ---------- Vista ---------- */
const fld = (k, label, type = "text", attrs = "", help = "") => { const v = k.split(".").reduce((o, x) => o?.[x], ob.d);
  return `<label class="fld"><span class="lbl">${label}</span><input data-k="${k}" type="${type}" value="${esc(v ?? "")}" ${attrs}>${help ? `<span class="helper">${help}</span>` : ""}</label>`; };
const money = (k, label, help = "") => fld(k, label, "number", 'min="0" step="1000000" inputmode="numeric"', help || (() => { const v = k.split(".").reduce((o, x) => o?.[x], ob.d); return has(v) ? mm(+v) : "CLP"; })());
const hname = { corto: "Corto", medio: "Medio", largo: "Largo" };
const stepState = i => {
  const d = ob.d, r = d.riesgo, p = d.patrimonio;
  switch (OB_STEPS[i][0]) {
    case "cliente": return has(d.cliente.nombre) && has(d.cliente.nacimiento) ? "ok" : "pend";
    case "riesgo": return has(r.perfil) && [r.vol, r.var, r.es, r.dd, r.capacidad].every(has) ? "ok" : has(r.perfil) ? "parcial" : "pend";
    case "patrimonio": return [p.total, p.fuera, p.capital_humano, p.activos_nf, p.pasivos, p.compromisos, p.admin].every(has) ? "ok" : [p.total, p.fuera].some(has) ? "parcial" : "pend";
    case "metas": return d.metas.length && d.metas.every(goalReady) ? "ok" : d.metas.length ? "parcial" : "pend";
    case "datos": { const c = evaluateCatalog(); return blockingMissing(c).length ? "parcial" : "ok"; }
    default: return engineGate().length ? "pend" : "ok";
  }
};
RENDER.alta = async function () {
  const host = $("v-alta");
  if (!MO) { host.innerHTML = '<div class="loading">Cargando el motor de construcción…</div>';
    try { await loadMotor(); ob.parity = parityCheck(); } catch (e) { host.innerHTML = `<div class="notif err"><span>${si("alerta", "Error")}</span><span>No se pudo cargar el motor: ${esc(e.message)}</span></div>`; return; } }
  const d = ob.d, i = Math.min(d.step, OB_STEPS.length - 1);
  host.innerHTML = `
    <div class="pagehead"><span class="lbl">Nuevo cliente · prospecto ${esc(d.id)} · supuestos de mercado al ${fdate(MO.as_of)}</span>
      <div class="row"><h1>${esc(d.cliente.nombre || "Construcción de cartera desde cero")}</h1>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" id="ob-ex">Cargar caso de ejemplo</button><button class="btn sm" id="ob-new">Empezar en blanco</button></div></div>
      <p class="muted" style="max-width:100ch">El asistente recoge lo que pide el catálogo de información (DF 5.2, ESFS 9.1), declara qué falta y construye la cartera por meta con el mismo motor del libro. El borrador queda en este navegador hasta que lo guardes; el cliente entra al libro solo cuando el IPS está firmado y el motor Python lo procesa.</p></div>
    <nav class="steps obsteps" aria-label="Etapas">${OB_STEPS.map(([id, t], n) => { const st = stepState(n);
      return `<button class="step" data-step="${n}" aria-current="${n === i ? "step" : "false"}" style="--sc:${n === i ? "var(--interactive)" : st === "ok" ? "var(--ok)" : st === "parcial" ? "var(--warn)" : "var(--border-strong)"}"><b>${n + 1}. ${t}</b><span>${st === "ok" ? "completo" : st === "parcial" ? "incompleto" : "pendiente"}</span></button>`; }).join("")}</nav>
    <div id="ob-body" style="display:grid;gap:16px"></div>
    <div class="obnav"><button class="btn" id="ob-prev" ${i === 0 ? "disabled" : ""}>Anterior</button><span class="helper">${i + 1} de ${OB_STEPS.length}</span><button class="btn primary" id="ob-next" ${i === OB_STEPS.length - 1 ? "disabled" : ""}>Siguiente: ${OB_STEPS[i + 1] ? OB_STEPS[i + 1][1] : ""}</button></div>`;
  host.querySelectorAll("[data-step]").forEach(b => b.addEventListener("click", () => obGo(+b.dataset.step)));
  $("ob-prev").addEventListener("click", () => obGo(i - 1)); $("ob-next").addEventListener("click", () => obGo(i + 1));
  $("ob-ex").addEventListener("click", loadExample);
  $("ob-new").addEventListener("click", () => { if (d.metas.length && !confirm("¿Descartar el borrador actual?")) return; ob.d = blankDraft(); obSave(); RENDER.alta(); });
  const body = $("ob-body");
  try { OBS[OB_STEPS[i][0]](body); } catch (e) { console.error(e); body.innerHTML = `<div class="notif err"><span>${si("alerta", "Error")}</span><span>${esc(e.message)}</span></div>`; }
  bindFields(body);
};
function obGo(n) { ob.d.step = Math.max(0, Math.min(OB_STEPS.length - 1, n)); obSave(); RENDER.alta(); window.scrollTo({ top: 0 }); }
function bindFields(root) {
  root.querySelectorAll("[data-k]").forEach(inp => inp.addEventListener("change", () => {
    const path = inp.dataset.k.split("."), last = path.pop(); let o = ob.d; for (const x of path) o = o[x];
    o[last] = inp.type === "checkbox" ? inp.checked : inp.value; obSave();
    setTimeout(() => { const f = document.activeElement?.dataset?.k; RENDER.alta(); if (f) { const n = document.querySelector(`#v-alta [data-k="${f}"]`); if (n) n.focus(); } }, 0);
  }));
}
function loadExample() {
  const C = MO.control, P = MO.perfiles.Moderado;
  ob.d = { ...blankDraft(), step: ob.d.step,
    cliente: { nombre: "Prospecto de ejemplo", nacimiento: "1985-06-01", pais: "Chile", segmento: "Wealth, persona natural", asesor: "Asesor A", moneda: "CLP" },
    riesgo: { perfil: "Moderado", puntaje: 55, capacidad: "Media", capacidad_motivo: "ingresos estables, 20 años al retiro, compromisos de vivienda en 30 meses", vol: P.vol, var: P.var, es: P.es, dd: P.dd },
    patrimonio: { total: 450000000, fuera: 238000000, capital_humano: 900000000, activos_nf: 180000000, pasivos: 60000000, compromisos: 90000000, esg: "sin exclusiones declaradas", regulatorias: "persona natural, sin restricciones", familiares: "ninguna declarada", admin: 60 },
    metas: C.metas.map(m => ({ key: m.key, nombre: m.nombre, prioridad: m.prioridad, objetivo: m.objetivo, fecha: m.fecha || "", reserva: !m.fecha, capital: m.capital, aporte: m.aporte, prob_deseada: m.prob_deseada == null ? "" : m.prob_deseada * 100, liquidez: m.liquidez || "" })) };
  obSave(); RENDER.alta();
}

const OBS = {};
OBS.cliente = function (h) {
  h.innerHTML = `<div class="g2"><div class="tile"><h3>Identificación</h3><div class="form">
      ${fld("cliente.nombre", "Nombre o seudónimo del prospecto", "text", 'maxlength="80" autocomplete="off"', "Para pruebas usa un seudónimo: el registro compartido lo ve todo el equipo.")}
      ${fld("cliente.nacimiento", "Fecha de nacimiento", "date")}
      ${fld("cliente.pais", "País de residencia")}${fld("cliente.segmento", "Segmento")}${fld("cliente.asesor", "Asesor responsable")}
      <label class="fld"><span class="lbl">Moneda base</span><input value="CLP" disabled><span class="helper">El universo de construcción está en CLP; otra moneda exige serie FX (ESFS 9.4).</span></label></div></div>
    <div class="tile"><h3>Qué se hace en este proceso</h3><ol class="obflow">
      ${["Perfil de riesgo: tolerancia declarada, capacidad objetiva y límites del IPS", "Patrimonio, balance de vida y restricciones", "Metas: monto, fecha, prioridad, liquidez y probabilidad deseada", "Completitud: qué falta y qué bloquea (Data Completeness Gate)", "Construcción: CMA → horizontes → topes → optimización en grilla → alternativas", "Proyección de cada meta (Monte Carlo) y stress con escenarios e historia", "Propuesta: borrador de IPS, cartera, nivel de recomendación y pendientes"].map(s => `<li>${esc(s)}</li>`).join("")}</ol>
      <p class="helper">El sistema no contacta al cliente ni ejecuta: entrega la propuesta al asesor (QM XX).</p></div></div>`;
};
OBS.riesgo = function (h) {
  const r = ob.d.riesgo, age = ob.d.cliente.nacimiento ? monthsBetween(ob.d.cliente.nacimiento, MO.as_of) / 12 : null;
  const longest = Math.max(0, ...ob.d.metas.filter(g => g.fecha).map(g => monthsBetween(MO.as_of, g.fecha)));
  const p = ob.d.patrimonio, compRatio = has(p.total) && has(p.compromisos) && +p.total > 0 ? +p.compromisos / +p.total : null;
  // Qué habría vivido la cartera de largo plazo de cada perfil en el peor episodio histórico
  const prof = Object.entries(MO.perfiles).map(([n, L0]) => profileImpact(n, L0.vol, L0.dd));
  const ref0 = MO.perfiles[r.perfil];
  if (has(r.vol) && (!ref0 || +r.vol !== ref0.vol || (has(r.dd) ? +r.dd : null) !== ref0.dd)) prof.push(profileImpact("Lo declarado", +r.vol, has(r.dd) ? +r.dd : null));
  h.innerHTML = `<div class="g2">
    <div class="tile"><h3>Tolerancia declarada</h3>
      <div class="seg" role="group" aria-label="Perfil">${Object.keys(MO.perfiles).map(n => `<button data-perfil="${n}" aria-pressed="${r.perfil === n}">${n}</button>`).join("")}</div>
      <div class="form">${fld("riesgo.puntaje", "Puntaje del cuestionario (0–100)", "number", 'min="0" max="100"', "Se registra el resultado; el cuestionario de AFI no está definido en el DF.")}</div>
      <h4>Límites de riesgo del IPS</h4>
      <div class="form f4">${fld("riesgo.vol", "Volatilidad máx. %", "number", 'step="0.5" min="0"')}${fld("riesgo.var", "VaR 95% 1m máx. %", "number", 'step="0.5" min="0"')}${fld("riesgo.es", "ES 95% 1m máx. %", "number", 'step="0.5" min="0"')}${fld("riesgo.dd", "Caída tolerada %", "number", 'step="1" min="0"')}</div>
      ${has(r.perfil) ? `<button class="btn sm" id="ob-ref">Usar los límites de referencia de ${esc(r.perfil)}</button>` : ""}
      <p class="helper">Referencia: límites de los clientes sintéticos del libro, no aprobados por el Comité. La volatilidad máxima del IPS también limita la construcción de cada meta (ESFS 9.1, M03).</p></div>
    <div class="tile"><h3>Capacidad de riesgo (objetiva)</h3>
      <dl class="kv"><dt>Edad</dt><dd class="num">${age == null ? "—" : nf(Math.floor(age))} años</dd><dt>Meta más lejana</dt><dd class="num">${longest ? nf(longest / 12, 1) + " años" : "—"}</dd>
        <dt>Compromisos futuros / patrimonio</dt><dd class="num">${compRatio == null ? "—" : pct(compRatio, 0)}</dd><dt>Capital humano</dt><dd class="num">${has(p.capital_humano) ? mm(+p.capital_humano) : "—"}</dd></dl>
      <div class="form">${fld("riesgo.capacidad", "Capacidad (la clasifica el asesor)", "text", 'list="ob-cap"')}${fld("riesgo.capacidad_motivo", "Fundamento")}</div>
      <datalist id="ob-cap"><option>Baja</option><option>Media</option><option>Alta</option></datalist>
      <p class="helper">El DF pide contrastar la tolerancia declarada con la capacidad objetiva (balance, horizonte, estabilidad de ingresos); no fija una regla de puntaje, así que el sistema muestra la evidencia y no clasifica.</p></div></div>
    <div class="tile"><div class="th"><h3>Antes de elegir: qué habría vivido la cartera de largo plazo de cada perfil</h3><span class="helper">peor episodio de la biblioteca ${esc(MO.biblioteca.version)}</span></div>
      <div class="tw"><table class="dt"><thead><tr><th>Perfil</th><th>Tope de volatilidad</th><th>Cartera de largo plazo</th><th>Retorno esperado</th><th>Peor caída histórica</th><th>Episodio</th><th>Caída tolerada</th></tr></thead><tbody>
      ${prof.map(x => `<tr class="${x.n === r.perfil ? "hl" : ""}"><td>${esc(x.n)}</td><td class="n">${pct(x.cap, 1)}</td><td>${x.w ? wbar(x.w) : "—"}</td><td class="n">${pct(x.ret, 1)}</td><td class="n neg">${pct(x.dd, 1)}</td><td>${esc(x.ep || "—")}</td><td class="n">${x.tol == null ? "—" : pct(-x.tol / 100, 0)} ${x.tol != null && x.dd < -x.tol / 100 ? si("alerta", "la supera") : x.tol != null ? si("ok", "dentro") : ""}</td></tr>`).join("")}</tbody></table></div>
      <p class="helper">Calibrar la tolerancia real a pérdidas con la máxima caída observada, más allá del cuestionario (QM V). Cartera de una meta de más de ${MO.params.risk_horizon_medium_max_months / 12} años construida con el motor (el tope de volatilidad de largo plazo, ${nf(MO.params.vol_cap_long_pct, 0)}%, también limita a los perfiles con un límite mayor); compra al inicio del episodio y mantiene.</p></div>`;
  h.querySelectorAll("[data-perfil]").forEach(b => b.addEventListener("click", () => { r.perfil = b.dataset.perfil; if (!has(r.vol)) Object.assign(r, MO.perfiles[r.perfil]); obSave(); RENDER.alta(); }));
  const ref = $("ob-ref"); if (ref) ref.addEventListener("click", () => { Object.assign(r, MO.perfiles[r.perfil]); obSave(); RENDER.alta(); });
};
function profileImpact(n, volPct, dd) {
  const cap = Math.min(MO.params.vol_cap_long_pct, volPct) / 100, [ks, caps] = keysCaps("largo");
  let best = null, bu = -Infinity; for (const w of E.grid(ks, caps)) { const v = E.pvar(w); if (Math.sqrt(v) > cap + 1e-12) continue; const u = E.pret(w) - MO.params.risk_aversion_delta / 2 * v; if (u > bu + 1e-15) { best = w; bu = u; } }
  if (!best) return { n, cap, tol: dd };
  let worst = null; for (const e of Object.values(MO.episodios)) { const x = episodeRun(best, e); if (!worst || x.caida < worst.caida) worst = { ...x, nombre: e.nombre }; }
  return { n, cap, w: best, ret: E.pret(best), dd: worst.caida, ep: worst.nombre, tol: dd };
}
const wbar = w => `<div class="stack" style="min-width:140px" title="${esc(Object.entries(w).map(([k, x]) => `${k} ${pct(x, 0)}`).join(" · "))}">${Object.entries(w).map(([k, x]) => `<i style="width:${x * 100}%;background:${vc(k)}"></i>`).join("")}</div>`;
OBS.patrimonio = function (h) {
  h.innerHTML = `<div class="g2">
    <div class="tile"><h3>Patrimonio</h3><div class="form">${money("patrimonio.total", "Patrimonio financiero total (incluye fuera de AFI)")}${money("patrimonio.fuera", "Inversiones fuera de AFI")}</div>
      <h4>Balance de vida (life balance sheet)</h4><div class="form">${money("patrimonio.capital_humano", "Capital humano (VP de ingresos futuros)")}${money("patrimonio.activos_nf", "Activos no financieros")}${money("patrimonio.pasivos", "Pasivos")}${money("patrimonio.compromisos", "Compromisos futuros")}</div>
      <p class="helper">Crítico para el límite de ilíquidos (QM IX). Sin él, la cartera se construye pero la recomendación baja a Nivel 2.</p></div>
    <div class="tile"><h3>Restricciones</h3><div class="form">${fld("patrimonio.esg", "ESG", "text", "", "Escribe «ninguna» si el cliente no declara.")}${fld("patrimonio.regulatorias", "Regulatorias")}${fld("patrimonio.familiares", "Familiares")}
      ${fld("patrimonio.admin", "Máximo por administradora (%)", "number", 'min="0" max="100" step="5"')}</div>
      <p class="helper">Las restricciones declaradas como vinculantes en el IPS pasan a ser restricciones de la optimización (QM XXIII P6). El motor actual solo aplica el tope por fondo y el de volatilidad; otras quedan declaradas para el Comité.</p></div></div>`;
};
OBS.metas = function (h) {
  const G = ob.d.metas, P = MO.params;
  const rows = G.map((g, n) => { const ok = goalReady(g), hz = ok ? horizonOf(g) : null, m = g.fecha ? monthsBetween(MO.as_of, g.fecha) : null;
    return `<div class="goal"><div class="gh"><b>${n + 1}. ${esc(g.nombre || "Meta sin nombre")}</b>${hz ? `<span class="tag ${hz === "largo" ? "info" : ""}">Horizonte ${hname[hz].toLowerCase()} · tope de volatilidad ${pct(Math.min(P[CAPP[hz]] / 100, has(ob.d.riesgo.vol) ? +ob.d.riesgo.vol / 100 : 1), 1)}</span>` : si("atencion", "incompleta")}<button class="btn sm" data-del="${n}" aria-label="Eliminar meta">Eliminar</button></div>
      <div class="form f4">${fld(`metas.${n}.nombre`, "Nombre")}
        <label class="fld"><span class="lbl">Prioridad</span><select data-k="metas.${n}.prioridad" class="sel">${["esencial", "importante", "aspiracional"].map(p => `<option ${g.prioridad === p ? "selected" : ""}>${p}</option>`).join("")}</select></label>
        ${money(`metas.${n}.objetivo`, "Monto objetivo")}
        ${g.reserva ? `<label class="fld"><span class="lbl">Fecha</span><input value="Reserva permanente" disabled></label>` : fld(`metas.${n}.fecha`, "Fecha", "date", `min="${MO.as_of}"`, m != null ? (m > 0 ? `${m} meses desde ${fdate(MO.as_of)}` : "debe ser posterior a la fecha de los datos") : "")}
        <label class="fld chkf"><input type="checkbox" data-k="metas.${n}.reserva" ${g.reserva ? "checked" : ""}><span>Sin fecha: reserva de liquidez</span></label>
        ${money(`metas.${n}.capital`, "Capital inicial asignado")}${money(`metas.${n}.aporte`, "Aporte mensual")}
        ${g.reserva ? "" : fld(`metas.${n}.prob_deseada`, "Probabilidad deseada %", "number", 'min="1" max="99"')}${fld(`metas.${n}.liquidez`, "Liquidez requerida")}</div></div>`; }).join("");
  const cap = G.reduce((a, g) => a + (+g.capital || 0), 0), pt = +ob.d.patrimonio.total || 0;
  h.innerHTML = `<div class="tile"><div class="th"><div><h3>Metas del cliente</h3><span class="helper">Cada meta tiene su propia cartera según su horizonte: corto ≤ ${P.risk_horizon_short_max_months} meses (solo ${esc(P.short_horizon_eligible_subclass)}), medio ≤ ${P.risk_horizon_medium_max_months}, largo después.</span></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${GOAL_TEMPLATES.map(([n], i) => `<button class="btn sm" data-tpl="${i}">+ ${esc(n)}</button>`).join("")}<button class="btn sm primary" id="ob-add">+ Meta</button></div></div>
      ${rows || '<div class="notif"><span>' + si("info", "Sin metas") + '</span><span>Agrega las metas del cliente. Sin metas no hay construcción: el motor arma una cartera por meta.</span></div>'}
      ${G.length ? `<div class="kpis">${kpiS("Capital inicial total", mm(cap), pt ? `${pct(cap / pt, 0)} del patrimonio financiero declarado` : "patrimonio no declarado")}${kpiS("Aportes mensuales", mm(G.reduce((a, g) => a + (+g.aporte || 0), 0)), "suma de todas las metas")}${kpiS("Metas completas", `${G.filter(goalReady).length} de ${G.length}`, "con monto, capital y fecha o reserva")}</div>` : ""}</div>`;
  h.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", () => { G.splice(+b.dataset.del, 1); obSave(); RENDER.alta(); }));
  $("ob-add").addEventListener("click", () => { G.push(newGoal(G.length)); obSave(); RENDER.alta(); });
  h.querySelectorAll("[data-tpl]").forEach(b => b.addEventListener("click", () => { const [n, t] = GOAL_TEMPLATES[+b.dataset.tpl], g = newGoal(G.length);
    Object.assign(g, { nombre: n, prioridad: t.prioridad, reserva: !!t.reserva, liquidez: t.liquidez, prob_deseada: t.prob_deseada ?? "" });
    if (t.anios) { const [y, m] = MO.as_of.split("-").map(Number); g.fecha = `${y + t.anios}-${String(m).padStart(2, "0")}-28`; } G.push(g); obSave(); RENDER.alta(); }));
};
const kpiS = (l, v, n) => `<div class="kpi"><span class="lbl">${l}</span><span class="v sm">${v}</span><span class="helper">${esc(n)}</span></div>`;
const ESTADO = { available: ["ok", "Disponible"], degraded: ["atencion", "Degradado"], missing_critical: ["alerta", "Falta · crítico"], missing_non_critical: ["atencion", "Falta"], post: ["sin_datos", "Tras ejecutar"] };
OBS.datos = function (h) {
  const cat = evaluateCatalog(), block = blockingMissing(cat), gate = engineGate(), groups = [...new Set(cat.map(c => c.grupo))];
  const cnt = s => cat.filter(c => c.estado === s).length;
  h.innerHTML = `<div class="kpis">${kpiS("Disponibles", cnt("available"), "del catálogo de " + cat.length + " variables")}${kpiS("Faltan críticas del cliente", block.length, block.length ? "la recomendación baja a Nivel 2" : "ninguna")}${kpiS("Faltan críticas de la plataforma", cat.filter(c => c.origen === "plataforma" && c.estado === "missing_critical").length, "se declaran como limitación")}${kpiS("Degradadas", cnt("degraded"), "se usan con advertencia")}</div>
    <div class="notif ${gate.length ? "err" : block.length ? "warn" : "ok"}"><span>${gate.length ? si("alerta", "No se puede construir") : block.length ? si("atencion", "Se construye con Nivel 2") : si("ok", "Lista para construir")}</span><span>${gate.length ? "El Construction Engine necesita: " + esc(gate.join("; ")) + "." : block.length ? "La cartera se calcula y se muestran las alternativas, pero sin recomendación analítica hasta completar: " + esc(block.join("; ")) + " (DF 4.1: dato crítico ausente = bloqueo de la recomendación)." : "Todos los datos críticos del cliente están. Lo que falta de la plataforma queda declarado como limitación, igual que en el libro."}</span></div>
    <div class="tile"><h3>Catálogo de información (DF 5.2, ESFS 9.1)</h3><div class="tw"><table class="dt"><thead><tr><th>Variable</th><th>Criticidad</th><th>Origen</th><th>Estado</th><th>Si falta</th><th>Qué habilita</th></tr></thead><tbody>
      ${groups.map(g => `<tr class="grp"><td colspan="6">${esc(g)}</td></tr>` + cat.filter(c => c.grupo === g).map(c => { const [s, l] = ESTADO[c.estado] || ["sin_datos", c.estado];
        return `<tr><td>${esc(c.variable)}${c.nota ? `<br><span class="helper">${esc(c.nota)}</span>` : ""}</td><td>${c.criticidad === "CRITICAL" ? "Crítica" : c.criticidad === "NON-CRITICAL" ? "No crítica" : "Complementaria"}</td><td>${c.origen === "cliente" ? "Cliente" : c.origen === "post" ? "Operación" : "Plataforma"}</td><td>${si(s, l)}</td><td>${esc(c.comportamiento)}</td><td class="helper" style="text-align:left">${esc(c.habilita)} · ${esc(c.fuente_doc)}</td></tr>`; }).join("")).join("")}
    </tbody></table></div><p class="helper">Lo de la plataforma (CMAs institucionales, curvas, Approved List, costos) tiene el mismo estado para todo cliente: se toma de la última corrida del libro.</p></div>`;
};
function gateNotice(h, r) { h.innerHTML = `<div class="notif err"><span>${si("alerta", "Sin construcción")}</span><span>El Construction Engine necesita: ${esc(r.gate.join("; "))}. Complétalo en las etapas anteriores.</span></div>`; }
OBS.construccion = function (h) {
  const r = compute(); if (r.gate.length) return gateNotice(h, r);
  const V = MO.vehiculos, P = MO.params, c = MO.cma;
  const flow = ["Objetivos", "Horizontes", "Riesgo", "Liquidez", "Restricciones", "Retornos esperados", "Modelo de riesgo", "Correlaciones", "Optimización", "Escenarios", "Alternativas"];
  const corr = (i, j) => c.cov[i][j] / Math.sqrt(c.cov[i][i] * c.cov[j][j]);
  h.innerHTML = `<div class="tile"><span class="lbl">Portfolio Construction Decision Flow (DF v1.1 7.1)</span><div class="pflow">${flow.map((s, n) => `<span>${n + 1}. ${s}</span>`).join("")}</div></div>
    <div class="notif ${ob.parity.ok ? "ok" : "err"}"><span>${si(ob.parity.ok ? "ok" : "alerta", ob.parity.ok ? "Motor verificado" : "Diferencia con Python")}</span><span>${ob.parity.ok ? `Este cálculo corre en el navegador con las reglas del motor Python. Al cargar se reprodujo el caso de control (${ob.parity.metas} metas) que calculó el motor real: mismos pesos, probabilidades, alternativas y nivel.` : "El caso de control no coincide con el motor Python en: " + esc(ob.parity.diffs.join(", ")) + ". No uses esta propuesta."}</span></div>
    <div class="g2"><div class="tile"><h3>Supuestos de mercado (CMA)</h3><div class="tw"><table class="dt"><thead><tr><th>Fondo</th><th>Retorno esperado</th><th>Volatilidad</th><th>Liquidez</th></tr></thead><tbody>${V.map((k, i) => `<tr><td><span class="sw" style="--c:${vc(k)}"></span>${k} · ${esc(VNAME[k] || k)}</td><td class="n">${pct(c.mu[i], 1)}</td><td class="n">${pct(Math.sqrt(c.cov[i][i]), 1)}</td><td>${esc(MO.liquidez[k] || "—")}</td></tr>`).join("")}</tbody></table></div>
      <p class="helper">μ y σ de simulación del Parameter Registry (no institucionales). Correlaciones de ${c.n_obs} meses (${fmonth(c.desde.slice(0, 7))} a ${fmonth(c.hasta.slice(0, 7))}) con shrinkage ${esc(c.metodo)}, intensidad ${nf(c.intensidad, 2)} hacia la correlación promedio ${nf(c.rbar, 2)}.</p></div>
      <div class="tile"><h3>Correlaciones usadas</h3><div class="corr" style="grid-template-columns:44px repeat(${V.length},minmax(0,1fr))"><div class="h"></div>${V.map(k => `<div class="h">${k}</div>`).join("")}${V.map((a, i) => `<div class="h">${a}</div>` + V.map((b, j) => { const x = corr(i, j); return `<div style="background:${alpha(css(x >= 0 ? "--div-pos" : "--div-neg"), Math.min(.85, Math.abs(x)))};color:${Math.abs(x) > .5 ? "#fff" : "inherit"}">${nf(x, 2)}</div>`; }).join("")).join("")}</div></div></div>
    ${r.goals.map(g => sleeveTile(g, r)).join("")}
    <div class="tile"><h3>Cartera total propuesta</h3><div class="kpis">${kpiS("Capital inicial", mm(r.capital), `${Object.keys(r.sleeves).length} metas con cartera`)}${kpiS("Retorno esperado", pct(E.pret(r.total), 1), "promedio ponderado por capital de cada meta")}${kpiS("Volatilidad ex-ante", pct(Math.sqrt(E.pvar(r.total)), 1), has(ob.d.riesgo.vol) ? `límite del IPS ${nf(+ob.d.riesgo.vol, 1)}%` : "sin límite en el IPS")}${kpiS("Concentración (HHI)", nf(E.hhi(r.total), 3), "1 = un solo fondo")}</div>
      <div class="bars">${V.filter(k => r.total[k]).map(k => `<div class="brow"><span><span class="sw" style="--c:${vc(k)}"></span>${k} · ${esc(VNAME[k] || k)}</span><div class="track"><i style="left:0;width:${r.total[k] * 100}%;background:${vc(k)}"></i></div><span class="num">${pct(r.total[k], 1)} · ${mm(r.total[k] * r.capital)}</span></div>`).join("")}</div>
      <p class="helper">La asignación total es la suma de las carteras por meta ponderada por su capital (goal-based). La cartera de cada meta se rebalancea a sus pesos; el aporte mensual va a su meta.</p></div>`;
  h.querySelectorAll("[data-front]").forEach(n => drawFrontier(n, r, n.dataset.front));
};
function sleeveTile(g, r) {
  const s = r.sleeves[g.key], a = r.alts[g.key], f = r.frontier[g.key];
  if (!s) return `<div class="tile"><h3>${esc(g.nombre)}</h3><div class="notif err"><span>${si("alerta", "Sin cartera")}</span><span>${esc(r.blocked[g.key] || "Sin construcción")}</span></div></div>`;
  const A = a.alternativas || {}, lv = a.nivel;
  return `<div class="tile"><div class="th"><div><span class="lbl">Meta · ${esc(g.prioridad)} · horizonte ${s.horizonte} · tope ${pct(s.tope, 1)} (${s.fuente === "IPS" ? "límite del IPS" : "por horizonte"})</span><h3>${esc(g.nombre)}</h3></div>${si(lv === 3 ? "ok" : lv === 2 ? "atencion" : "sin_datos", `Nivel ${lv}`)}</div>
    <div class="g2" style="gap:16px"><div style="min-width:0"><div class="chart" data-front="${g.key}"></div><p class="helper">${nf(f.grid)} carteras de la grilla de 5 pp con ${f.ks.join(", ")}; ${nf(f.feasible)} cumplen el tope. El motor elige la de mayor μ − ${MO.params.risk_aversion_delta}/2·σ² entre las admisibles.</p></div>
      <div style="display:grid;gap:12px;align-content:start">${Object.keys(A).length ? `<div class="tw"><table class="dt"><thead><tr><th>Alternativa</th><th>Pesos</th><th>Retorno</th><th>Volatilidad</th><th>Adverso</th><th>Prob. meta</th></tr></thead><tbody>${Object.entries(A).map(([k, x]) => `<tr class="${k === a.recomendada ? "hl" : ""}"><td>${esc(x.nombre)}${x.admisible ? "" : `<br><span class="helper neg">${esc(x.motivo_inadmisible)}</span>`}</td><td>${wbar(x.pesos)}</td><td class="n">${pct(x.retorno_esperado, 1)}</td><td class="n">${pct(x.volatilidad_ex_ante, 1)}</td><td class="n${cls(x.retorno_escenario_adverso)}">${spct(x.retorno_escenario_adverso, 1)}</td><td class="n">${x.prob_exito == null ? "—" : pct(x.prob_exito, 0)}</td></tr>`).join("")}</tbody></table></div>` : `<dl class="kv">${Object.entries(s.pesos).map(([k, x]) => `<dt>${k} · ${esc(VNAME[k] || k)}</dt><dd class="num">${pct(x, 0)}</dd>`).join("")}<dt>Retorno esperado</dt><dd class="num">${pct(s.ret, 1)}</dd><dt>Volatilidad</dt><dd class="num">${pct(s.vol, 1)}</dd></dl>`}
        ${(a.tradeoffs || []).map(t => `<div class="to"><b>${esc(t.conflicto)}</b><div class="cols"><span class="pos">Mejora: ${esc(t.mejora.join(" · "))}</span><span class="neg">Empeora: ${esc(t.empeora.join(" · "))}</span></div></div>`).join("")}
        <div class="notif ${lv === 3 ? "ok" : "warn"}"><span>${si(lv === 3 ? "ok" : lv === 2 ? "atencion" : "sin_datos", `Nivel ${lv}`)}</span><span>${esc(a.recomendacion || a.motivo_nivel || NO_ALTS)}</span></div>
        ${a.descartadas ? `<p class="helper">Mínima volatilidad no se muestra: ${esc(a.descartadas.MINVOL)}.</p>` : ""}</div></div></div>`;
}
function drawFrontier(host, r, key) {
  const f = r.frontier[key], s = r.sleeves[key], W = Math.max(320, host.clientWidth || 520), H = 240, m = { l: 44, r: 12, t: 12, b: 32 };
  const xs = f.pts.map(p => p[0]), ys = f.pts.map(p => p[1]), x0 = 0, x1 = Math.max(...xs, s.tope) * 1.05, y0 = Math.min(...ys) * .95, y1 = Math.max(...ys) * 1.02;
  const X = v => m.l + (v - x0) / (x1 - x0) * (W - m.l - m.r), Y = v => m.t + (1 - (v - y0) / (y1 - y0 || 1)) * (H - m.t - m.b);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Carteras de la grilla: volatilidad contra retorno esperado" }, host);
  for (let i = 0; i <= 4; i++) { const v = y0 + (y1 - y0) * i / 4; el("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), stroke: css("--border") }, svg); txt(svg, m.l - 6, Y(v) + 4, pct(v, 1), { "text-anchor": "end" }); }
  for (let i = 0; i <= 4; i++) { const v = x1 * i / 4; txt(svg, X(v), H - 14, pct(v, 1), { "text-anchor": "middle" }); }
  txt(svg, W - m.r, H - 2, "volatilidad ex-ante", { "text-anchor": "end" });
  el("rect", { x: X(s.tope), y: m.t, width: Math.max(0, W - m.r - X(s.tope)), height: H - m.t - m.b, fill: alpha(css("--err"), .06) }, svg);
  el("line", { x1: X(s.tope), x2: X(s.tope), y1: m.t, y2: H - m.b, stroke: css("--err"), "stroke-dasharray": "4 3" }, svg);
  txt(svg, X(s.tope) + 4, m.t + 12, `tope ${pct(s.tope, 1)}`, { fill: css("--err-text") });
  const step = Math.max(1, Math.floor(f.pts.length / 1500));
  for (let i = 0; i < f.pts.length; i += step) { const p = f.pts[i]; el("circle", { cx: X(p[0]), cy: Y(p[1]), r: 1.6, fill: p[0] <= s.tope + 1e-12 ? css("--bar") : alpha(css("--bar"), .35) }, svg); }
  const A = (r.alts[key] || {}).alternativas || {};
  Object.entries(A).forEach(([k, a]) => { if (k === "MVO") return; el("circle", { cx: X(a.volatilidad_ex_ante), cy: Y(a.retorno_esperado), r: 5, fill: "none", stroke: css("--text-2"), "stroke-width": 2 }, svg); txt(svg, X(a.volatilidad_ex_ante) + 7, Y(a.retorno_esperado) + 4, k); });
  el("circle", { cx: X(s.vol), cy: Y(s.ret), r: 6, fill: css("--interactive"), stroke: css("--layer"), "stroke-width": 2 }, svg);
  txt(svg, X(s.vol) - 8, Y(s.ret) - 9, "MVO elegida", { "text-anchor": "end", fill: css("--text") });
}
OBS.proyeccion = function (h) {
  const r = ob.res && !ob.res.gate.length ? ob.res : compute(); if (r.gate.length) return gateNotice(h, r);
  const tot = r.capital, vals = Object.fromEntries(Object.entries(r.total).map(([k, w]) => [k, w * tot]));
  const eps = Object.entries(MO.episodios).map(([k, e]) => ({ k, e, x: episodeRun(vals, e) })).sort((a, b) => a.x.caida - b.x.caida);
  const dd = has(ob.d.riesgo.dd) ? -ob.d.riesgo.dd / 100 : null;
  h.innerHTML = `<div class="tile"><h3>Probabilidad de lograr cada meta</h3><div class="tw"><table class="dt"><thead><tr><th>Meta</th><th>Horizonte</th><th>Objetivo</th><th>Probabilidad</th><th>Deseada</th><th>Pesimista (p10)</th><th>Central (p50)</th><th>Optimista (p90)</th></tr></thead><tbody>
      ${r.goals.map(g => { const x = r.goalRes[g.key]; if (!x) return ""; if (x.tipo === "reserva") return `<tr><td>${esc(g.nombre)}</td><td>reserva</td><td class="n">${mm(+g.objetivo)}</td><td class="n" colspan="5">cobertura ${pct(x.cobertura, 0)} del objetivo con el capital inicial</td></tr>`;
        const des = has(g.prob_deseada) ? +g.prob_deseada / 100 : null, low = des != null && x.prob_exito < des;
        return `<tr><td>${esc(g.nombre)}</td><td>${nf(x.meses / 12, 1)} años</td><td class="n">${mm(+g.objetivo)}</td><td class="n">${pct(x.prob_exito, 0)} ${low ? si("atencion", "bajo lo deseado") : des != null ? si("ok", "cumple") : ""}</td><td class="n">${des == null ? "—" : pct(des, 0)}</td><td class="n">${mm(x.p10)}</td><td class="n">${mm(x.p50)}</td><td class="n">${mm(x.p90)}</td></tr>`; }).join("")}</tbody></table></div>
      <div class="g3" id="ob-fans"></div>
      <p class="helper">${nf(MO.params.mc_simulations)} trayectorias por meta con bloques de ${MO.params.mc_block_months} meses de la historia real (${fmonth(MO.historia.meses[0].slice(0, 7))} a ${fmonth(MO.historia.meses[MO.historia.meses.length - 1].slice(0, 7))}) re-centrada en la CMA; semilla fija, el resultado es reproducible. Montos nominales en CLP.</p></div>
    <div class="g2"><div class="tile"><h3>Escenarios del Comité</h3><div class="tw"><table class="dt"><thead><tr><th>Escenario</th><th>Retorno de la cartera</th><th>En CLP</th><th>Rescates suspendidos</th></tr></thead><tbody>
      ${Object.values(MO.escenarios).map(s => { let x = 0; for (const k in r.total) x += r.total[k] * s.shocks[k]; const sus = s.suspendidos.filter(k => r.total[k]);
        return `<tr><td>${esc(s.nombre)}</td><td class="n${cls(x)}">${spct(x, 1)}</td><td class="n">${smm(x * tot)}</td><td>${sus.length ? esc(sus.map(k => `${k} (${pct(r.total[k], 0)})`).join(", ")) : "—"}</td></tr>`; }).join("")}</tbody></table></div>
      <p class="helper">Biblioteca ${esc(MO.biblioteca.version)} · ${esc(MO.biblioteca.autor)}.</p></div>
      <div class="tile"><h3>Si la cartera propuesta hubiera vivido estas crisis</h3><div class="tw"><table class="dt"><thead><tr><th>Episodio</th><th>Caída máxima</th><th>En CLP</th><th>Recuperación</th></tr></thead><tbody>
      ${eps.map(({ e, x }) => `<tr><td>${esc(e.nombre)}<br><span class="helper">${fdate(e.desde)} – ${fdate(e.hasta)}</span></td><td class="n neg">${pct(x.caida, 1)} ${dd != null && x.caida < dd ? si("alerta", "supera la caída tolerada") : ""}</td><td class="n">${smm(x.caida * x.t0)}</td><td class="n">${x.recupera ? x.dias_rec + " días" : "más de 1 año"}</td></tr>`).join("")}</tbody></table></div>
      <div class="chart" id="ob-crisis"></div><p class="helper">Peor episodio día a día, comprando la cartera total al inicio y manteniéndola (Simulación Histórica, QM XI). ${dd != null ? `Línea roja: caída tolerada del IPS (${pct(dd, 0)}).` : ""}</p></div></div>`;
  const fans = $("ob-fans"); r.goals.forEach(g => { const x = r.goalRes[g.key]; if (x && x.tipo === "meta") drawFan(fans, g, x); });
  if (eps.length) drawCrisis($("ob-crisis"), eps[0], dd);
};
function drawFan(parent, g, x) {
  const box = document.createElement("div"); box.className = "chart"; box.innerHTML = `<b style="font-size:14px">${esc(g.nombre)}</b>`; parent.appendChild(box);
  const t = x.trayectoria, W = 300, H = 150, m = { l: 48, r: 8, t: 8, b: 20 }, hi = Math.max(...t.map(p => p.p90), +g.objetivo) * 1.05;
  const X = mo => m.l + mo / t[t.length - 1].mes * (W - m.l - m.r), Y = v => m.t + (1 - v / hi) * (H - m.t - m.b);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Abanico de ${g.nombre}` }, box);
  const area = (a, b) => t.map((p, i) => `${i ? "L" : "M"}${X(p.mes)},${Y(p[a])}`).join("") + [...t].reverse().map(p => `L${X(p.mes)},${Y(p[b])}`).join("") + "Z";
  el("path", { d: area("p90", "p10"), fill: alpha(css("--interactive"), .15) }, svg); el("path", { d: area("p75", "p25"), fill: alpha(css("--interactive"), .3) }, svg);
  el("path", { d: t.map((p, i) => `${i ? "L" : "M"}${X(p.mes)},${Y(p.p50)}`).join(""), fill: "none", stroke: css("--interactive"), "stroke-width": 2 }, svg);
  el("line", { x1: m.l, x2: W - m.r, y1: Y(+g.objetivo), y2: Y(+g.objetivo), stroke: css("--err"), "stroke-dasharray": "4 3" }, svg);
  txt(svg, m.l - 4, Y(+g.objetivo) + 4, mm(+g.objetivo), { "text-anchor": "end" }); txt(svg, m.l - 4, Y(0), "0", { "text-anchor": "end" });
  txt(svg, m.l, H - 4, "hoy"); txt(svg, W - m.r, H - 4, `${nf(t[t.length - 1].mes / 12, 1)} años`, { "text-anchor": "end" });
  const p = document.createElement("span"); p.className = "helper"; p.textContent = `Probabilidad ${pct(x.prob_exito, 0)} · banda p10–p90 y p25–p75`; box.appendChild(p);
}
function drawCrisis(host, ep, dd) {
  const { x, e } = ep, P = x.path, W = Math.max(320, host.clientWidth || 520), H = 180, m = { l: 44, r: 8, t: 20, b: 20 };
  const rel = P.map(p => p.t / x.t0 - 1), lo = Math.min(...rel, dd ?? 0) * 1.1, hi = Math.max(0.01, ...rel) * 1.1;
  const X = i => m.l + i / Math.max(1, P.length - 1) * (W - m.l - m.r), Y = v => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Trayectoria en ${e.nombre}` }, host);
  txt(svg, m.l, 12, e.nombre, { fill: css("--text") });
  el("line", { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), stroke: css("--border-strong"), "stroke-dasharray": "3 3" }, svg); txt(svg, m.l - 4, Y(0) + 4, "0%", { "text-anchor": "end" });
  if (dd != null) { el("line", { x1: m.l, x2: W - m.r, y1: Y(dd), y2: Y(dd), stroke: css("--err"), "stroke-dasharray": "4 3" }, svg); txt(svg, m.l - 4, Y(dd) + 4, pct(dd, 0), { "text-anchor": "end" }); }
  el("path", { d: rel.map((v, i) => `${i ? "L" : "M"}${X(i)},${Y(v)}`).join("") + `L${X(rel.length - 1)},${Y(0)}L${X(0)},${Y(0)}Z`, fill: alpha(css("--err"), .12) }, svg);
  el("path", { d: rel.map((v, i) => `${i ? "L" : "M"}${X(i)},${Y(v)}`).join(""), fill: "none", stroke: css("--err"), "stroke-width": 2 }, svg);
  const it = rel.indexOf(Math.min(...rel)); el("circle", { cx: X(it), cy: Y(rel[it]), r: 4, fill: css("--text") }, svg); txt(svg, X(it) + 6, Y(rel[it]) + 14, `${pct(rel[it], 1)} el ${fdate(P[it].f)}`);
  txt(svg, m.l, H - 4, fdate(P[0].f)); txt(svg, W - m.r, H - 4, fdate(P[P.length - 1].f), { "text-anchor": "end" });
}
OBS.propuesta = function (h) {
  const r = ob.res && !ob.res.gate.length ? ob.res : compute(); if (r.gate.length) return gateNotice(h, r);
  const d = ob.d, R = d.riesgo, cat = r.cat, block = blockingMissing(cat), levels = Object.values(r.alts).map(a => a.nivel);
  const multi = levels.filter(x => x > 1), lvl = !levels.length ? null : multi.length ? Math.min(...multi) : 1;
  const plat = cat.filter(c => c.origen === "plataforma" && c.estado !== "available").map(c => `${c.variable} (${ESTADO[c.estado]?.[1] || c.estado})`);
  h.innerHTML = `<div class="g2"><div class="tile"><h3>Borrador de IPS</h3><dl class="kv">${[["Cliente", `${esc(d.cliente.nombre || d.id)} · ${esc(d.id)}`], ["Vigencia", `desde la firma, revisión antes de 3 años o ante evento de vida (QM XVI)`], ["Moneda base", "CLP"], ["Perfil y tolerancia", `${esc(R.perfil)}${has(R.puntaje) ? ` (cuestionario ${nf(+R.puntaje)}/100)` : ""}`], ["Capacidad", esc(R.capacidad || "sin clasificar")],
      ["Límites", `vol ${has(R.vol) ? nf(+R.vol, 1) + "%" : "—"} · VaR ${has(R.var) ? nf(+R.var, 1) + "%" : "—"} · ES ${has(R.es) ? nf(+R.es, 1) + "%" : "—"} · caída ${has(R.dd) ? nf(+R.dd, 0) + "%" : "—"}`], ["Máximo por administradora", has(d.patrimonio.admin) ? nf(+d.patrimonio.admin) + "%" : "—"], ["Metas", r.goals.map(g => esc(g.nombre)).join(" · ")]].map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("")}</dl>
      <div class="notif warn"><span>${si("atencion", "Sin firma")}</span><span>El IPS se firma con el cliente antes de ejecutar. La violación de un límite genera alerta, nunca ajuste automático.</span></div></div>
    <div class="tile"><h3>Estado de la recomendación</h3><div class="kpis">${kpiS("Nivel más bajo entre metas", lvl == null ? "—" : "Nivel " + lvl, "Nivel 3 es el techo")}${kpiS("Pendientes del cliente", block.length, "datos críticos")}</div>
      ${block.length ? `<div class="notif warn"><span>${si("atencion", "Nivel 2")}</span><span>Falta para una recomendación analítica: ${esc(block.join("; "))}.</span></div>` : ""}
      <h4>Limitaciones declaradas</h4><ul class="helper" style="margin:0;padding-left:16px">${["CMAs de simulación, no institucionales del Comité", "ERC se muestra como referencia y no se optimiza en la grilla", ...plat].map(x => `<li>${esc(x)}</li>`).join("")}</ul></div></div>
    <div class="tile"><h3>Cartera por meta</h3><div class="tw"><table class="dt"><thead><tr><th>Meta</th><th>Capital</th><th>Aporte mensual</th>${MO.vehiculos.map(k => `<th>${k}</th>`).join("")}<th>Probabilidad</th><th>Nivel</th></tr></thead><tbody>
      ${r.goals.map(g => { const s = r.sleeves[g.key], x = r.goalRes[g.key] || {}, a = r.alts[g.key] || {}; return `<tr><td>${esc(g.nombre)}</td><td class="n">${mm(+g.capital)}</td><td class="n">${mm(+g.aporte || 0)}</td>${MO.vehiculos.map(k => `<td class="n">${s && s.pesos[k] ? pct(s.pesos[k], 0) : "·"}</td>`).join("")}<td class="n">${x.tipo === "reserva" ? "reserva" : pct(x.prob_exito, 0)}</td><td>${a.nivel ? "Nivel " + a.nivel : "—"}</td></tr>`; }).join("")}
      <tr class="grp"><td>Total</td><td class="n">${mm(r.capital)}</td><td></td>${MO.vehiculos.map(k => `<td class="n">${r.total[k] ? pct(r.total[k], 0) : "·"}</td>`).join("")}<td></td><td></td></tr></tbody></table></div></div>
    <div class="tile"><div class="th"><h3>Guardar y siguientes pasos</h3><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="ob-save">Guardar prospecto</button><button class="btn" id="ob-dl">Descargar ficha para el motor (JSON)</button></div></div>
      <div id="ob-msg" class="notif" hidden></div>
      <ol class="helper" style="margin:0;padding-left:16px"><li>Revisar la propuesta con el cliente en una reunión: el sistema no le envía nada (QM XX).</li><li>Firmar el IPS y completar lo que falta del catálogo.</li><li>Procesar la ficha con el motor Python (<code>python -m afi_quant.book.prospect ficha.json</code>): recalcula todo con los datos del día y lo deja listo para entrar al libro.</li></ol>
      <h4>Prospectos guardados</h4><div class="log" id="ob-list"><div class="helper">Cargando…</div></div></div>`;
  $("ob-save").addEventListener("click", saveProspect); $("ob-dl").addEventListener("click", downloadProspect);
  listProspects();
};
function prospectFile() {
  const r = ob.res; return { formato: "afi-prospecto-v1", generado: new Date().toISOString(), datos_al: MO.as_of, prospecto: ob.d,
    propuesta_navegador: r && !r.gate.length ? { total: r.total, sleeves: Object.fromEntries(Object.entries(r.sleeves).map(([k, s]) => [k, { horizonte: s.horizonte, tope: s.tope, pesos: s.pesos }])),
      probabilidades: Object.fromEntries(Object.entries(r.goalRes).map(([k, x]) => [k, x.prob_exito ?? null])), niveles: Object.fromEntries(Object.entries(r.alts).map(([k, a]) => [k, a.nivel])) } : null };
}
const obMsg = (t, kind) => { const m = $("ob-msg"); if (!m) return; m.hidden = false; m.className = "notif " + kind; m.innerHTML = `<span>${si(kind === "err" ? "alerta" : "ok", kind === "err" ? "Atención" : "Listo")}</span><span>${esc(t)}</span>`; };
async function saveProspect() {
  if (!db) { obMsg("El registro compartido no está disponible en esta vista. Descarga la ficha para conservarla.", "err"); return; }
  let por = null; try { por = user ? await user.id() : null; } catch (e) {}
  try { const f = prospectFile(); await db.collection("prospectos").doc(ob.d.id).set({ nombre: ob.d.cliente.nombre || ob.d.id, perfil: ob.d.riesgo.perfil || null, metas: ob.d.metas.length, actualizado: f.generado, por, datos_al: MO.as_of, ficha: JSON.stringify(f) });
    obMsg(`Prospecto ${ob.d.id} guardado en el registro compartido.`, "ok"); listProspects(); }
  catch (e) { obMsg(`No se pudo guardar (${e.code || e.message}). Descarga la ficha para conservarla.`, "err"); }
}
async function downloadProspect() {
  const data = JSON.stringify(prospectFile(), null, 2), name = `prospecto-${ob.d.id}.json`;
  if (!downloads) { obMsg("Esta vista no permite descargar archivos.", "err"); return; }
  try { await downloads.save({ filename: name, data }); obMsg(`Ficha ${name} descargada.`, "ok"); }
  catch (e) { if (e && e.code !== "declined") obMsg("No se pudo descargar: " + (e && (e.code || e.message)), "err"); }
}
async function listProspects() {
  const box = $("ob-list"); if (!box) return;
  if (!db) { box.innerHTML = '<div class="helper">El registro compartido no está disponible en esta vista.</div>'; return; }
  try { const snap = await db.collection("prospectos").orderBy("actualizado", "desc").limit(20).get();
    box.innerHTML = snap.docs.length ? snap.docs.map(s => { const x = s.data() || {}; return `<div style="display:flex;justify-content:space-between;gap:12px;align-items:center"><span><b>${esc(x.nombre)}</b> <span class="helper">${esc(s.id)} · ${esc(x.perfil || "sin perfil")} · ${x.metas} metas · ${fdate(String(x.actualizado || "").slice(0, 10))}</span></span><button class="btn sm" data-load="${esc(s.id)}">Abrir</button></div>`; }).join("") : '<div class="helper">Aún no hay prospectos guardados.</div>';
    box.querySelectorAll("[data-load]").forEach(b => b.addEventListener("click", async () => { const s = await db.collection("prospectos").doc(b.dataset.load).get(); try { const f = JSON.parse((s.data() || {}).ficha); ob.d = { ...f.prospecto, step: 0 }; obSave(); RENDER.alta(); } catch (e) { obMsg("La ficha guardada no se pudo leer.", "err"); } }));
  } catch (e) { box.innerHTML = `<div class="helper">No se pudo leer el registro (${esc(e.code || e.message)}).</div>`; }
}
