/* Mesa Central — acciones de la plataforma local (apps/mesa_central/plataforma.py).
   Solo se activa si el servidor responde en api/estado: en la página publicada no hace nada.
   Agrega: validar la propuesta con el motor Python, ingresar el cliente al libro con su IPS
   firmado, registrar aportes y retiros extraordinarios, archivar una cuenta y seguir los cálculos. */
"use strict";
const PLAT = { on: false, est: null, version: null, timer: null, pending: null };

async function platApi(path, body) {
  const res = await fetch(path, body === undefined ? { cache: "no-store" } : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  let data = null; try { data = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error((data && data.detail) || `Error ${res.status}`);
  return data;
}

(async function platBoot() {
  try { PLAT.est = await platApi("api/estado"); } catch (e) { return; }
  if (!PLAT.est || PLAT.est.modo !== "plataforma") return;
  PLAT.on = true; PLAT.version = PLAT.est.trabajo.version;
  const tag = document.createElement("span"); tag.className = "tag-sim"; tag.style.background = "#42be65";
  tag.textContent = "Plataforma local · motor Python"; document.querySelector(".hdr .tag-sim").before(tag);
  const bar = document.createElement("div"); bar.id = "plat-bar"; bar.className = "notif"; bar.hidden = true;
  bar.style.cssText = "position:fixed;left:16px;right:16px;bottom:16px;z-index:40;max-width:720px;margin:0 auto;box-shadow:0 2px 6px rgba(0,0,0,.3)";
  document.body.appendChild(bar);
  platWatch(PLAT.est);
  if (PLAT.est.trabajo.estado === "calculando") platPoll();
  if (app.view === "alta" || app.view === "cliente") setTimeout(() => RENDER[app.view]({}), 0);
})();

function platWatch(est) {
  const bar = $("plat-bar"), t = est.trabajo;
  if (t.estado === "calculando") { bar.hidden = false; bar.className = "notif"; bar.innerHTML = `<span>${si("info", "Calculando")}</span><span>${esc(t.tarea)} · el motor Python está trabajando; puedes seguir usando la Mesa Central.</span>`; }
  else if (t.error) { bar.hidden = false; bar.className = "notif err"; bar.innerHTML = `<span>${si("alerta", "Error")}</span><span>${esc(t.error)} <button class="link" id="plat-x">Cerrar</button></span>`; $("plat-x").onclick = () => { bar.hidden = true; }; }
  else bar.hidden = true;
}

function platPoll() {
  clearTimeout(PLAT.timer);
  PLAT.timer = setTimeout(async () => {
    let est; try { est = await platApi("api/estado"); } catch (e) { platPoll(); return; }
    PLAT.est = est; platWatch(est);
    if (est.trabajo.version !== PLAT.version) {
      PLAT.version = est.trabajo.version;
      try { await reloadLibro(); } catch (e) {}
      if (PLAT.pending && L.clientes[PLAT.pending.id]) { const id = PLAT.pending.id, tab = PLAT.pending.tab; PLAT.pending = null; openClient(id, tab); }
      else RENDER[app.view]({});
    }
    if (est.trabajo.estado === "calculando") platPoll();
  }, 2500);
}

/* ---------- Alta: validar con el motor real e ingresar al libro ---------- */
(function hookPropuesta() {
  if (typeof OBS === "undefined") return;
  const orig = OBS.propuesta;
  OBS.propuesta = function (h) {
    orig(h);
    if (!PLAT.on || !ob.res || ob.res.gate.length) return;
    const ins = PLAT.est.inicios, done = ob.d.ingresado && L.clientes[ob.d.ingresado];
    const tile = document.createElement("div"); tile.className = "tile";
    tile.innerHTML = `<div class="th"><div><span class="lbl">Plataforma local · motor Python</span><h3>Firmar e ingresar al libro</h3></div></div>
      ${done ? `<div class="notif ok"><span>${si("ok", "En el libro")}</span><span>${esc(ob.d.cliente.nombre || ob.d.id)} ya es cliente (${esc(ob.d.ingresado)}). <button class="link" data-open-client="${esc(ob.d.ingresado)}">Abrir la cuenta</button></span></div>` : `
      <div class="form f4">
        <label class="fld"><span class="lbl">Inicio de la cartera (cierre de mes)</span><select class="sel" id="pl-ini">${ins.slice().reverse().map((d, i) => `<option value="${d}" ${i === 0 ? "selected" : ""}>${fdate(d)}${i === 0 ? " · último cierre" : ""}</option>`).join("")}</select>
          <span class="helper">El motor valoriza en cierres mensuales. Una fecha anterior reconstruye una cuenta que ya existía.</span></label>
        <label class="fld"><span class="lbl">Asesor responsable</span><input id="pl-as" value="${esc(ob.d.cliente.asesor || "")}" maxlength="60"></label>
        <label class="fld chkf"><input type="checkbox" id="pl-ips"><span>El cliente firmó el IPS</span></label></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn" id="pl-val">Validar con el motor Python</button><button class="btn primary" id="pl-go">Ingresar al libro</button></div>`}
      <div id="pl-msg"></div>
      <p class="helper">Al ingresar, el motor corre el ciclo de vida desde el inicio hasta el último dato (${fdate(PLAT.est.datos_al)}): aportes mensuales, revisiones trimestrales, rebalanceos, glide path y metas que vencen. La cuenta aparece en el libro con su monitoreo. El sistema no ejecuta órdenes ni contacta al cliente.</p>`;
    h.appendChild(tile);
    const msg = (kind, label, text) => { $("pl-msg").innerHTML = `<div class="notif ${kind}"><span>${si(kind === "err" ? "alerta" : kind === "ok" ? "ok" : "info", label)}</span><span>${text}</span></div>`; };
    if (done) return;
    $("pl-val").onclick = async () => {
      msg("", "Validando", "El motor Python está construyendo la propuesta…");
      try { const r = await platApi("api/proponer", { ficha: prospectFile() });
        if (!r.ok) return msg("err", "Sin construcción", esc(r.motivo));
        msg(r.diferencias.length ? "warn" : "ok", r.diferencias.length ? "Difiere" : "Idéntica", r.diferencias.length ? `El motor Python no coincide con el navegador en: ${esc(r.diferencias.join(", "))}. Manda el resultado del motor.` : "El motor Python calcula exactamente la misma propuesta: pesos, probabilidades y niveles.");
      } catch (e) { msg("err", "Error", esc(e.message)); }
    };
    $("pl-go").onclick = async () => {
      if (!$("pl-ips").checked) return msg("err", "Falta la firma", "Marca que el cliente firmó el IPS: sin IPS firmado la cuenta no se ingresa (ESFS 9.1).");
      $("pl-go").disabled = true;
      try { const r = await platApi("api/clientes", { ficha: prospectFile(), inicio: $("pl-ini").value, asesor: $("pl-as").value });
        ob.d.ingresado = r.id; obSave(); PLAT.pending = { id: r.id, tab: "resumen" };
        msg("", "Ingresando", `${esc(r.id)} quedó registrado. El motor está corriendo su ciclo de vida (toma alrededor de medio minuto); la cuenta se abre sola al terminar.`);
        platPoll();
      } catch (e) { $("pl-go").disabled = false; msg("err", "No se ingresó", esc(e.message)); }
    };
  };
})();

/* ---------- Cuenta: flujos extraordinarios y archivo ---------- */
(function hookResumen() {
  if (typeof CT === "undefined") return;
  const orig = CT.resumen;
  CT.resumen = function (h, C) {
    orig(h, C);
    if (!PLAT.on || C.origen !== "plataforma" || !$("ciclo-acc")) return;
    $("ciclo-acc").innerHTML = `<button class="btn sm primary" id="pl-fl">Registrar aporte o retiro</button><button class="btn sm" id="pl-ar">Archivar cuenta</button>`;
    $("pl-fl").onclick = () => flowForm(C);
    $("pl-ar").onclick = async () => {
      if (!confirm(`¿Sacar a ${C.cliente.nombre} del libro? Su ficha queda guardada en la plataforma.`)) return;
      try { await platApi(`api/clientes/${C.id}/archivar`, {}); PLAT.pending = null; app.client = null; go("libro"); platPoll(); } catch (e) { alert(e.message); }
    };
  };
})();

function flowForm(C) {
  const open = C.cliente.metas.filter(g => !g.cerrada), last = PLAT.est.datos_al;
  const box = $("ciclo-form");
  box.innerHTML = `<div class="goal"><b>Flujo extraordinario del cliente</b>
    <div class="form f4">
      <label class="fld"><span class="lbl">Tipo</span><select class="sel" id="fl-t"><option value="aporte">Aporte</option><option value="retiro">Retiro</option></select></label>
      <label class="fld"><span class="lbl">Meta</span><select class="sel" id="fl-m">${open.map(g => `<option value="${esc(g.key)}">${esc(g.nombre)}</option>`).join("")}</select></label>
      <label class="fld"><span class="lbl">Monto (CLP)</span><input id="fl-a" type="number" min="1" step="1000000"></label>
      <label class="fld"><span class="lbl">Fecha</span><input id="fl-d" type="date" max="${last}" value="${last}"></label>
      <label class="fld" style="grid-column:1/-1"><span class="lbl">Motivo</span><input id="fl-r" maxlength="120" placeholder="p. ej. bono anual, compra de auto"></label></div>
    <div style="display:flex;gap:8px"><button class="btn primary sm" id="fl-go">Registrar y recalcular</button><button class="btn sm" id="fl-x">Cancelar</button></div>
    <p class="helper">Se aplica en el cierre de su mes: un aporte se invierte según los pesos objetivo de la meta; un retiro vende a prorrata dentro de la meta. Toda la cuenta se vuelve a calcular con el motor.</p><div id="fl-msg"></div></div>`;
  $("fl-x").onclick = () => { box.innerHTML = ""; };
  $("fl-go").onclick = async () => {
    const body = { tipo: $("fl-t").value, meta: $("fl-m").value, monto: +$("fl-a").value, fecha: $("fl-d").value, motivo: $("fl-r").value };
    try { await platApi(`api/clientes/${C.id}/flujos`, body); PLAT.pending = { id: C.id, tab: "resumen" };
      $("fl-msg").innerHTML = `<div class="notif"><span>${si("info", "Recalculando")}</span><span>Flujo registrado. La cuenta se actualiza al terminar el cálculo.</span></div>`; platPoll(); }
    catch (e) { $("fl-msg").innerHTML = `<div class="notif err"><span>${si("alerta", "No se registró")}</span><span>${esc(e.message)}</span></div>`; }
  };
}
