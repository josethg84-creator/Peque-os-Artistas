/* Conciliación Bancaria — interfaz web (SPA sin dependencias). */
"use strict";

// ---------------------------------------------------------------- utilidades
const $ = (s, raiz = document) => raiz.querySelector(s);
const $$ = (s, raiz = document) => [...raiz.querySelectorAll(s)];
const vista = () => $("#vista");

// Si el usuario navega mientras una vista aún carga datos, el resultado de la
// navegación anterior se descarta (la promesa nunca se resuelve) y no pisa la vista actual.
let navSeq = 0;
function vigente(promesa) {
  const s = navSeq;
  return promesa.then((v) => (s === navSeq ? v : new Promise(() => {})));
}

const almacen = {
  leer(k, def = null) { try { return localStorage.getItem(k) ?? def; } catch { return def; } },
  guardar(k, v) { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento */ } },
};

const estado = { empresas: [], empresaId: null, bancos: [], monedas: [], cuentas: [] };

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const fmtNum = new Intl.NumberFormat("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
function dinero(v, moneda) {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  const simb = { PEN: "S/", USD: "US$", EUR: "€" }[moneda] || "";
  return `${simb ? simb + " " : ""}${fmtNum.format(n)}`;
}
function celdaImporte(v, moneda) {
  const n = Number(v);
  return `<td class="num ${n < 0 ? "neg" : "pos"}">${esc(dinero(v, moneda))}</td>`;
}
function fecha(iso) {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}
function fechaHora(iso) {
  if (!iso) return "—";
  return `${fecha(iso)} ${iso.slice(11, 16)}`;
}
function parametrosHash() {
  const q = location.hash.split("?")[1] || "";
  return Object.fromEntries(new URLSearchParams(q));
}
function badgeEstado(e) {
  const cls = { PENDIENTE: "b-warn", CONCILIADO: "b-ok", PROPUESTO: "b-info", EXCLUIDO: "", ACTIVA: "b-ok", ANULADA: "b-err" }[e] || "";
  return `<span class="badge ${cls}">${esc(e)}</span>`;
}
const usuario = () => almacen.leer("cb_usuario", "") || "sistema";

async function api(ruta, { method = "GET", body, form, params } = {}) {
  let url = "/api" + ruta;
  if (params) {
    const p = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "" && v !== false) p.append(k, v); });
    if ([...p].length) url += "?" + p;
  }
  const opciones = { method, headers: { "X-Usuario": encodeURIComponent(usuario()) } };
  if (form) opciones.body = form;
  else if (body !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(body);
  }
  const resp = await fetch(url, opciones);
  const datos = resp.headers.get("content-type")?.includes("json") ? await resp.json() : null;
  if (!resp.ok) {
    let msg = datos?.detail ?? `Error ${resp.status}`;
    if (Array.isArray(msg)) msg = msg.map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`).join(" · ");
    const err = new Error(msg);
    err.status = resp.status;
    throw err;
  }
  return datos;
}

function toast(msg, tipo = "") {
  const t = document.createElement("div");
  t.className = `toast ${tipo}`;
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), tipo === "err" ? 7000 : 3500);
}

function abrirModal(titulo, html) {
  $("#modal-titulo").textContent = titulo;
  $("#modal-cuerpo").innerHTML = html;
  $("#modal").hidden = false;
  return $("#modal-cuerpo");
}
function cerrarModal() { $("#modal").hidden = true; $("#modal-cuerpo").innerHTML = ""; }

function datosForm(form) {
  const d = {};
  new FormData(form).forEach((v, k) => { d[k] = typeof v === "string" ? v.trim() : v; });
  $$("input[type=checkbox]", form).forEach((c) => { d[c.name] = c.checked; });
  return d;
}

function cuentaPorId(id) { return estado.cuentas.find((c) => c.id === Number(id)); }
function nombreCuenta(c) { return c ? `${c.cuenta_contable} · ${c.banco.codigo} ${c.moneda} ${c.numero_cuenta}` : "—"; }
function opcionesCuentas(sel) {
  return estado.cuentas.map((c) => `<option value="${c.id}" ${Number(sel) === c.id ? "selected" : ""}>${esc(nombreCuenta(c))}</option>`).join("");
}

// ------------------------------------------------------------------ carga
async function cargarMaestros() {
  [estado.empresas, estado.bancos, estado.monedas] = await Promise.all([
    api("/empresas"), api("/bancos"), api("/monedas"),
  ]);
  const guardada = Number(almacen.leer("cb_empresa"));
  estado.empresaId = estado.empresas.some((e) => e.id === guardada) ? guardada : estado.empresas[0]?.id ?? null;
  pintarSelectorEmpresa();
  await cargarCuentas();
}
async function cargarCuentas() {
  estado.cuentas = estado.empresaId ? await api("/cuentas", { params: { empresa_id: estado.empresaId } }) : [];
}
function pintarSelectorEmpresa() {
  const sel = $("#sel-empresa");
  sel.innerHTML = estado.empresas.length
    ? estado.empresas.map((e) => `<option value="${e.id}" ${e.id === estado.empresaId ? "selected" : ""}>${esc(e.razon_social)} — RUC ${esc(e.ruc)}</option>`).join("")
    : `<option value="">(registre una empresa)</option>`;
}

// ------------------------------------------------------------------ router
const rutas = {};
async function navegar() {
  const ruta = (location.hash.replace(/^#\//, "").split("?")[0]) || "panel";
  $$("#nav a[data-ruta]").forEach((a) => a.classList.toggle("activo", a.dataset.ruta === ruta));
  const fn = rutas[ruta] || rutas.panel;
  navSeq++;
  vista().innerHTML = `<div class="vacio">Cargando…</div>`;
  try { await fn(); } catch (e) {
    vista().innerHTML = `<div class="alerta alerta-err">${esc(e.message)}</div>`;
  }
}
function requiereEmpresa() {
  if (estado.empresaId) return true;
  vista().innerHTML = `
    <div class="card" style="max-width:640px">
      <h2>Bienvenido</h2>
      <p>Para comenzar registre una empresa (RUC) y luego sus cuentas bancarias vinculadas a las subcuentas de la cuenta 10.</p>
      <a class="btn btn-primario" href="#/empresas">Registrar empresa</a>
    </div>`;
  return false;
}

// ------------------------------------------------------------------ panel
rutas.panel = async () => {
  if (!requiereEmpresa()) return;
  const { cuentas } = await vigente(api("/panel", { params: { empresa_id: estado.empresaId } }));
  const emp = estado.empresas.find((e) => e.id === estado.empresaId);
  const tot = cuentas.reduce((a, c) => {
    a.bp += c.banco_resumen.pendientes; a.lp += c.libro_resumen.pendientes;
    a.dup += c.banco_resumen.posibles_duplicados + c.libro_resumen.posibles_duplicados;
    a.mov += c.banco_resumen.movimientos + c.libro_resumen.movimientos;
    return a;
  }, { bp: 0, lp: 0, dup: 0, mov: 0 });

  vista().innerHTML = `
    <div class="cab-vista">
      <div><h1>Panel de tesorería</h1><p class="sub">${esc(emp?.razon_social)} · ${cuentas.length} cuenta(s) bancaria(s)</p></div>
      <a class="btn btn-primario" href="#/importar">Importar archivos</a>
    </div>
    <div class="grid grid-4" style="margin-bottom:16px">
      <div class="kpi"><div class="l">Movimientos cargados</div><div class="v">${tot.mov}</div></div>
      <div class="kpi"><div class="l">Pendientes en banco</div><div class="v">${tot.bp}</div></div>
      <div class="kpi"><div class="l">Pendientes en libros</div><div class="v">${tot.lp}</div></div>
      <div class="kpi"><div class="l">Posibles duplicados</div><div class="v" style="color:${tot.dup ? "var(--warn)" : "inherit"}">${tot.dup}</div></div>
    </div>
    ${cuentas.length ? "" : `<div class="card vacio">No hay cuentas bancarias. <a href="#/cuentas">Registrar una cuenta</a></div>`}
    <div class="grid grid-2">
      ${cuentas.map((c) => `
        <div class="card cuenta-card">
          <h3>${esc(c.banco)} <span class="badge b-info">${esc(c.moneda)}</span></h3>
          <div class="cuenta-meta">Cta. ${esc(c.numero_cuenta)} · Subcuenta ${esc(c.cuenta_contable)}${c.descripcion ? " · " + esc(c.descripcion) : ""}</div>
          <table class="mini-tabla">
            <tr><td>Último corte del estado de cuenta</td><td>${fecha(c.ultimo_corte_banco)}</td></tr>
            <tr><td>Saldo según banco al corte</td><td>${dinero(c.ultimo_saldo_banco, c.moneda)}</td></tr>
            <tr><td>Movimientos banco (pendientes)</td><td>${c.banco_resumen.movimientos} (${c.banco_resumen.pendientes})</td></tr>
            <tr><td>Movimientos libro (pendientes)</td><td>${c.libro_resumen.movimientos} (${c.libro_resumen.pendientes})</td></tr>
            <tr><td>Posibles duplicados</td><td>${c.banco_resumen.posibles_duplicados + c.libro_resumen.posibles_duplicados}</td></tr>
            <tr><td>Período cargado (banco)</td><td>${fecha(c.banco_resumen.desde)} – ${fecha(c.banco_resumen.hasta)}</td></tr>
          </table>
          <div class="acciones">
            <a class="btn btn-sm" href="#/movimientos?cuenta=${c.id}">Ver movimientos</a>
            <a class="btn btn-sm btn-primario" href="#/importar?cuenta=${c.id}">Importar</a>
          </div>
        </div>`).join("")}
    </div>`;
};

// ---------------------------------------------------------------- empresas
rutas.empresas = async () => {
  const lista = await vigente(api("/empresas", { params: { incluir_inactivas: true } }));
  vista().innerHTML = `
    <div class="cab-vista">
      <div><h1>Empresas</h1><p class="sub">Administración multiempresa. El RUC se valida con su dígito verificador.</p></div>
      <button class="btn btn-primario" id="nueva">Nueva empresa</button>
    </div>
    <div class="tabla-wrap"><table class="tabla">
      <thead><tr><th>RUC</th><th>Razón social</th><th>Nombre comercial</th><th>Estado</th><th></th></tr></thead>
      <tbody>${lista.map((e) => `
        <tr><td>${esc(e.ruc)}</td><td>${esc(e.razon_social)}</td><td>${esc(e.nombre_comercial || "")}</td>
        <td>${e.activo ? '<span class="badge b-ok">Activa</span>' : '<span class="badge">Inactiva</span>'}</td>
        <td class="num"><button class="btn btn-sm" data-editar="${e.id}">Editar</button></td></tr>`).join("")
        || `<tr><td colspan="5" class="vacio">Sin empresas registradas</td></tr>`}</tbody>
    </table></div>`;
  $("#nueva").onclick = () => formEmpresa();
  $$("[data-editar]").forEach((b) => { b.onclick = () => formEmpresa(lista.find((e) => e.id === Number(b.dataset.editar))); });
};

function formEmpresa(e) {
  const cuerpo = abrirModal(e ? "Editar empresa" : "Nueva empresa", `
    <form id="f-emp">
      <div class="form-grid">
        <div class="campo"><label>RUC</label><input name="ruc" required maxlength="11" pattern="\\d{11}" value="${esc(e?.ruc)}"></div>
        <div class="campo" style="grid-column:span 2"><label>Razón social</label><input name="razon_social" required value="${esc(e?.razon_social)}"></div>
        <div class="campo" style="grid-column:span 2"><label>Nombre comercial</label><input name="nombre_comercial" value="${esc(e?.nombre_comercial)}"></div>
        <label class="check"><input type="checkbox" name="activo" ${!e || e.activo ? "checked" : ""}> Activa</label>
      </div>
      <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-primario">Guardar</button></div>
    </form>`);
  $("#f-emp", cuerpo).onsubmit = async (ev) => {
    ev.preventDefault();
    const d = datosForm(ev.target);
    d.nombre_comercial = d.nombre_comercial || null;
    try {
      const r = e ? await api(`/empresas/${e.id}`, { method: "PUT", body: d }) : await api("/empresas", { method: "POST", body: d });
      cerrarModal();
      toast("Empresa guardada", "ok");
      if (!estado.empresaId) almacen.guardar("cb_empresa", r.id);
      await cargarMaestros();
      navegar();
    } catch (err) { toast(err.message, "err"); }
  };
}

// ----------------------------------------------------------------- cuentas
rutas.cuentas = async () => {
  if (!requiereEmpresa()) return;
  const lista = await vigente(api("/cuentas", { params: { empresa_id: estado.empresaId, incluir_inactivas: true } }));
  vista().innerHTML = `
    <div class="cab-vista">
      <div><h1>Cuentas bancarias</h1><p class="sub">Cada cuenta se vincula a su subcuenta contable de la cuenta 10 (p. ej. 104101) y tiene sus propias tolerancias.</p></div>
      <button class="btn btn-primario" id="nueva">Nueva cuenta</button>
    </div>
    <div class="tabla-wrap"><table class="tabla">
      <thead><tr><th>Subcuenta</th><th>Banco</th><th>Moneda</th><th>N.º de cuenta</th><th>CCI</th><th>Descripción</th><th>Estado</th><th></th></tr></thead>
      <tbody>${lista.map((c) => `
        <tr><td><b>${esc(c.cuenta_contable)}</b></td><td>${esc(c.banco.nombre)}</td><td>${esc(c.moneda)}</td>
        <td>${esc(c.numero_cuenta)}</td><td>${esc(c.cci || "")}</td><td>${esc(c.descripcion || "")}</td>
        <td>${c.activo ? '<span class="badge b-ok">Activa</span>' : '<span class="badge">Inactiva</span>'}</td>
        <td class="num"><button class="btn btn-sm" data-tol="${c.id}">Tolerancias</button> <button class="btn btn-sm" data-editar="${c.id}">Editar</button></td></tr>`).join("")
        || `<tr><td colspan="8" class="vacio">Sin cuentas registradas</td></tr>`}</tbody>
    </table></div>`;
  $("#nueva").onclick = () => formCuenta();
  $$("[data-editar]").forEach((b) => { b.onclick = () => formCuenta(lista.find((c) => c.id === Number(b.dataset.editar))); });
  $$("[data-tol]").forEach((b) => { b.onclick = () => formTolerancias(lista.find((c) => c.id === Number(b.dataset.tol))); });
};

function formCuenta(c) {
  const cuerpo = abrirModal(c ? "Editar cuenta bancaria" : "Nueva cuenta bancaria", `
    <form id="f-cta">
      <div class="form-grid">
        <div class="campo"><label>Banco</label><select name="banco_id" required>${estado.bancos.map((b) => `<option value="${b.id}" ${c?.banco_id === b.id ? "selected" : ""}>${esc(b.nombre)}</option>`).join("")}</select></div>
        <div class="campo"><label>Moneda</label><select name="moneda">${estado.monedas.map((m) => `<option value="${m.codigo}" ${c?.moneda === m.codigo ? "selected" : ""}>${m.codigo} — ${esc(m.nombre)}</option>`).join("")}</select></div>
        <div class="campo"><label>N.º de cuenta</label><input name="numero_cuenta" required minlength="5" value="${esc(c?.numero_cuenta)}"></div>
        <div class="campo"><label>CCI (20 dígitos)</label><input name="cci" maxlength="24" value="${esc(c?.cci)}"></div>
        <div class="campo"><label>Subcuenta contable</label><input name="cuenta_contable" required pattern="10\\d+" placeholder="104101" value="${esc(c?.cuenta_contable)}"><small>Debe iniciar con 10 (PCGE).</small></div>
        <div class="campo"><label>Descripción</label><input name="descripcion" value="${esc(c?.descripcion)}"></div>
        <label class="check"><input type="checkbox" name="activo" ${!c || c.activo ? "checked" : ""}> Activa</label>
      </div>
      <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-primario">Guardar</button></div>
    </form>`);
  $("#f-cta", cuerpo).onsubmit = async (ev) => {
    ev.preventDefault();
    const d = datosForm(ev.target);
    Object.assign(d, { empresa_id: estado.empresaId, banco_id: Number(d.banco_id), cci: d.cci || null, descripcion: d.descripcion || null });
    try {
      if (c) await api(`/cuentas/${c.id}`, { method: "PUT", body: d });
      else await api("/cuentas", { method: "POST", body: d });
      cerrarModal(); toast("Cuenta guardada", "ok");
      await cargarCuentas(); navegar();
    } catch (err) { toast(err.message, "err"); }
  };
}

async function formTolerancias(c) {
  const cfg = await api(`/cuentas/${c.id}/configuracion`);
  const cuerpo = abrirModal(`Tolerancias · ${nombreCuenta(c)}`, `
    <div class="alerta alerta-info">Estos parámetros los usará el motor de conciliación (fase 2). Una coincidencia ambigua nunca se confirma automáticamente, aunque supere el umbral.</div>
    <form id="f-tol">
      <div class="form-grid">
        <div class="campo"><label>Tolerancia de fechas (días)</label><input type="number" name="tolerancia_dias" min="0" max="60" value="${cfg.tolerancia_dias}"></div>
        <div class="campo"><label>Tolerancia de importe (${esc(c.moneda)})</label><input type="number" step="0.01" min="0" name="tolerancia_importe" value="${cfg.tolerancia_importe}"></div>
        <div class="campo"><label>Umbral de auto-confirmación (0–100)</label><input type="number" min="50" max="100" name="umbral_auto_confirmacion" value="${cfg.umbral_auto_confirmacion}"></div>
        <div class="campo"><label>Umbral mínimo de sugerencia</label><input type="number" min="10" max="100" name="umbral_sugerencia" value="${cfg.umbral_sugerencia}"></div>
        <div class="campo"><label>Máx. movimientos por combinación (1 a N)</label><input type="number" min="1" max="8" name="max_elementos_combinacion" value="${cfg.max_elementos_combinacion}"></div>
        <label class="check"><input type="checkbox" name="usar_numero_operacion" ${cfg.usar_numero_operacion ? "checked" : ""}> Usar n.º de operación como criterio</label>
      </div>
      <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-primario">Guardar</button></div>
    </form>`);
  $("#f-tol", cuerpo).onsubmit = async (ev) => {
    ev.preventDefault();
    const d = datosForm(ev.target);
    ["tolerancia_dias", "umbral_auto_confirmacion", "umbral_sugerencia", "max_elementos_combinacion"].forEach((k) => { d[k] = Number(d[k]); });
    try { await api(`/cuentas/${c.id}/configuracion`, { method: "PUT", body: d }); cerrarModal(); toast("Tolerancias actualizadas", "ok"); }
    catch (err) { toast(err.message, "err"); }
  };
}

// ---------------------------------------------------------------- importar
const imp = { paso: 1, cuentaId: null, tipo: "BANCO", archivo: null, anio: "", invertir: false, mapeo: null, previa: null };

rutas.importar = async () => {
  if (!requiereEmpresa()) return;
  if (!estado.cuentas.length) {
    vista().innerHTML = `<div class="card vacio">Primero registre una cuenta bancaria. <a href="#/cuentas">Ir a cuentas</a></div>`;
    return;
  }
  const p = parametrosHash();
  if (imp.paso === 3) Object.assign(imp, { paso: 1, archivo: null, previa: null, mapeo: null });
  if (p.cuenta) { imp.cuentaId = Number(p.cuenta); imp.paso = 1; imp.previa = null; }
  if (!cuentaPorId(imp.cuentaId)) imp.cuentaId = estado.cuentas[0].id;
  pintarImportar();
};

function pintarImportar() {
  const pasos = ["Archivo", "Revisión y mapeo", "Resultado"];
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Importar archivos</h1>
      <p class="sub">Estados de cuenta (CSV, Excel .xlsx, PDF) y libro mayor de la cuenta 10 (CSV, Excel).</p></div></div>
    <div class="pasos">${pasos.map((t, i) => `<div class="paso ${imp.paso === i + 1 ? "activo" : ""} ${imp.paso > i + 1 ? "hecho" : ""}"><b>${i + 1}. ${t}</b></div>`).join("")}</div>
    <div id="paso-cuerpo"></div>`;
  ({ 1: pasoArchivo, 2: pasoRevision, 3: pasoResultado })[imp.paso]();
}

function pasoArchivo() {
  $("#paso-cuerpo").innerHTML = `
    <div class="card">
      <div class="form-grid">
        <div class="campo"><label>Cuenta bancaria</label><select id="i-cuenta">${opcionesCuentas(imp.cuentaId)}</select></div>
        <div class="campo"><label>Tipo de archivo</label>
          <select id="i-tipo">
            <option value="BANCO" ${imp.tipo === "BANCO" ? "selected" : ""}>Estado de cuenta bancario</option>
            <option value="LIBRO" ${imp.tipo === "LIBRO" ? "selected" : ""}>Libro mayor — cuenta 10</option>
          </select></div>
        <div class="campo"><label>Año (si el archivo no lo indica)</label><input id="i-anio" type="number" min="2000" max="2100" placeholder="${new Date().getFullYear()}" value="${esc(imp.anio)}"></div>
        <label class="check"><input type="checkbox" id="i-inv" ${imp.invertir ? "checked" : ""}> Invertir signo de los importes</label>
      </div>
      <div style="margin-top:16px" id="drop" class="dropzone">
        <input type="file" id="i-archivo" accept=".csv,.txt,.xlsx,.xlsm,.pdf" hidden>
        <div id="drop-txt">${imp.archivo ? `<strong>${esc(imp.archivo.name)}</strong> · ${(imp.archivo.size / 1024).toFixed(1)} KB` : "<strong>Arrastre el archivo aquí</strong> o haga clic para seleccionarlo"}</div>
        <small>CSV · XLSX · PDF (con texto seleccionable)</small>
      </div>
      <div id="i-nota" class="alerta alerta-info" style="margin-top:12px"></div>
      <div class="acciones"><button class="btn btn-primario" id="i-analizar" ${imp.archivo ? "" : "disabled"}>Analizar archivo</button></div>
    </div>`;
  const nota = () => {
    const c = cuentaPorId($("#i-cuenta").value);
    $("#i-nota").innerHTML = $("#i-tipo").value === "LIBRO"
      ? `Se importarán solo las filas de la subcuenta <b>${esc(c.cuenta_contable)}</b> (si el archivo tiene columna de cuenta). Debe = ingreso, Haber = salida.`
      : `Moneda esperada: <b>${esc(c.moneda)}</b>. Se valida la continuidad de saldos y se detectan duplicados contra lo ya importado.`;
  };
  nota();
  $("#i-cuenta").onchange = (e) => { imp.cuentaId = Number(e.target.value); nota(); };
  $("#i-tipo").onchange = (e) => { imp.tipo = e.target.value; nota(); };
  const drop = $("#drop"), input = $("#i-archivo");
  const elegir = (f) => { if (f) { imp.archivo = f; imp.mapeo = null; pasoArchivo(); } };
  drop.onclick = () => input.click();
  input.onchange = () => elegir(input.files[0]);
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("sobre"); };
  drop.ondragleave = () => drop.classList.remove("sobre");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("sobre"); elegir(e.dataTransfer.files[0]); };
  $("#i-analizar").onclick = async () => {
    imp.anio = $("#i-anio").value; imp.invertir = $("#i-inv").checked;
    imp.cuentaId = Number($("#i-cuenta").value); imp.tipo = $("#i-tipo").value;
    await analizar();
  };
}

function formImportacion(extra = {}) {
  const f = new FormData();
  f.append("archivo", imp.archivo);
  f.append("cuenta_id", imp.cuentaId);
  f.append("tipo", imp.tipo);
  if (imp.anio) f.append("anio", imp.anio);
  f.append("invertir_signo", imp.invertir);
  if (imp.mapeo) f.append("mapeo", JSON.stringify(imp.mapeo));
  Object.entries(extra).forEach(([k, v]) => f.append(k, v));
  return f;
}

async function analizar() {
  const btn = $("#i-analizar") || $("#r-reaplicar");
  if (btn) { btn.disabled = true; btn.textContent = "Analizando…"; }
  try {
    const s = navSeq;
    const previa = await api("/importaciones/vista-previa", { method: "POST", form: formImportacion() });
    if (s !== navSeq) return;  // el usuario ya se fue a otra vista
    imp.previa = previa;
    imp.paso = 2;
    pintarImportar();
  } catch (err) {
    toast(err.message, "err");
    if (err.status === 422 && /mapeo manual|columnas/i.test(err.message) && imp.paso === 1) {
      $("#i-nota").className = "alerta alerta-err";
      $("#i-nota").innerHTML = `${esc(err.message)}<br>Revise que el archivo tenga encabezados de fecha e importe (o cargo/abono, debe/haber).`;
    }
    if (btn) { btn.disabled = false; btn.textContent = btn.id === "i-analizar" ? "Analizar archivo" : "Reaplicar mapeo"; }
  }
}

function pasoRevision() {
  const p = imp.previa, r = p.resumen, c = cuentaPorId(imp.cuentaId), m = c.moneda;
  const esBanco = imp.tipo === "BANCO";
  const opcionesCampo = (sel) => `<option value="">— ignorar —</option>` + p.campos.map((x) => `<option value="${x.campo}" ${sel === x.campo ? "selected" : ""}>${esc(x.etiqueta)}</option>`).join("");
  const dupTotal = r.duplicados_archivo + r.duplicados_base;
  $("#paso-cuerpo").innerHTML = `
    <div class="grid grid-4" style="margin-bottom:16px">
      <div class="kpi"><div class="l">Movimientos válidos</div><div class="v">${r.registros}</div></div>
      <div class="kpi"><div class="l">Ingresos</div><div class="v pos">${dinero(r.ingresos, m)}</div></div>
      <div class="kpi"><div class="l">Egresos</div><div class="v neg">${dinero(r.egresos, m)}</div></div>
      <div class="kpi"><div class="l">Período</div><div class="v" style="font-size:16px">${fecha(r.fecha_desde)} – ${fecha(r.fecha_hasta)}</div></div>
      <div class="kpi"><div class="l">Saldo inicial</div><div class="v" style="font-size:17px">${dinero(r.saldo_inicial, m)}</div></div>
      <div class="kpi"><div class="l">Saldo final</div><div class="v" style="font-size:17px">${dinero(r.saldo_final, m)}</div></div>
      <div class="kpi"><div class="l">Posibles duplicados</div><div class="v" style="color:${dupTotal ? "var(--warn)" : "inherit"}">${dupTotal}</div></div>
      <div class="kpi"><div class="l">Filas descartadas</div><div class="v" style="color:${r.errores ? "var(--err)" : "inherit"}">${r.errores}</div></div>
    </div>
    <div class="card">
      <h2>${esc(imp.archivo.name)} <span class="badge b-info">${esc(p.formato)}</span> ${p.metodo === "TEXTO_PDF" ? '<span class="badge b-warn">PDF leído como texto</span>' : ""}</h2>
      ${p.archivo_ya_importado ? `<div class="alerta alerta-err">Este archivo ya fue importado (importación #${p.archivo_ya_importado.id} del ${fechaHora(p.archivo_ya_importado.fecha)}). Para volver a cargarlo marque «Reimportar de todas formas».</div>` : ""}
      ${esBanco && r.saldos_consistentes === true ? `<div class="alerta alerta-ok">Continuidad de saldos verificada: saldo anterior + movimiento = saldo en todas las filas.</div>` : ""}
      ${p.advertencias.length ? `<div class="alerta alerta-warn"><b>Advertencias</b><ul>${p.advertencias.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>` : ""}
      ${p.errores.length ? `<details class="alerta alerta-err"><summary><b>${p.errores.length} fila(s) descartadas</b> — ver detalle</summary><ul>${p.errores.map((e) => `<li>Fila ${e.fila}: ${esc(e.mensaje)}</li>`).join("")}</ul></details>` : ""}
      ${p.descuadres_saldo.length ? `<details class="alerta alerta-warn"><summary><b>Descuadres de saldo</b></summary><ul>${p.descuadres_saldo.map((d) => `<li>Fila ${d.fila}: esperado ${dinero(d.esperado, m)}, informado ${dinero(d.saldo, m)} (dif. ${dinero(d.diferencia, m)})</li>`).join("")}</ul></details>` : ""}
    </div>
    ${p.metodo === "TABLA" ? `
    <div class="card">
      <h2>Mapeo de columnas</h2>
      <p class="sub" style="margin-bottom:12px">Detectado automáticamente en la fila ${p.fila_encabezado + 1}. Corrija si es necesario y pulse «Reaplicar mapeo».</p>
      <div class="mapeo-grid">${p.encabezados.map((h, i) => `
        <div class="mapeo-item ${p.mapeo[i] ? "asignado" : ""}"><div class="col" title="${esc(h)}">${esc(h || `(columna ${i + 1})`)}</div>
          <select data-col="${i}">${opcionesCampo(p.mapeo[i])}</select></div>`).join("")}</div>
      <div class="acciones"><button class="btn" id="r-reaplicar">Reaplicar mapeo</button></div>
    </div>` : ""}
    <div class="card">
      <h2>Vista previa ${p.registros.length < r.registros ? `<small class="sub">(primeros ${p.registros.length})</small>` : ""}</h2>
      <div class="tabla-wrap" style="max-height:460px">${tablaPrevia(p.registros, esBanco, m)}</div>
    </div>
    <div class="card">
      <div class="form-grid">
        <div class="campo"><label>Duplicados contra movimientos ya importados (${r.duplicados_base})</label>
          <select id="r-dup"><option value="marcar">Importarlos marcados para revisión</option><option value="omitir">Omitirlos (no importar)</option></select>
          <small>Los repetidos dentro del mismo archivo siempre se importan marcados para que usted decida.</small></div>
        ${p.archivo_ya_importado ? `<label class="check"><input type="checkbox" id="r-forzar"> Reimportar de todas formas</label>` : ""}
      </div>
      <div class="acciones">
        <button class="btn" id="r-volver">Volver</button>
        <button class="btn btn-primario" id="r-confirmar" ${r.registros ? "" : "disabled"}>Confirmar importación de ${r.registros} movimientos</button>
      </div>
    </div>`;

  $("#r-volver").onclick = () => { imp.paso = 1; pintarImportar(); };
  const reap = $("#r-reaplicar");
  if (reap) reap.onclick = async () => {
    imp.mapeo = {};
    $$("[data-col]").forEach((s) => { if (s.value) imp.mapeo[s.dataset.col] = s.value; });
    await analizar();
  };
  $("#r-confirmar").onclick = async (ev) => {
    ev.target.disabled = true; ev.target.textContent = "Importando…";
    try {
      const extra = { accion_duplicados: $("#r-dup").value };
      if ($("#r-forzar")?.checked) extra.forzar = "true";
      const s = navSeq;
      const r = await api("/importaciones", { method: "POST", form: formImportacion(extra) });
      toast(`Importación #${r.id} registrada (${r.total_registros} movimientos)`, "ok");
      if (s !== navSeq) { Object.assign(imp, { paso: 1, archivo: null, previa: null, mapeo: null }); return; }
      imp.resultado = r;
      imp.paso = 3; pintarImportar();
    } catch (err) {
      toast(err.message, "err");
      ev.target.disabled = false; ev.target.textContent = "Confirmar importación";
    }
  };
}

function tablaPrevia(regs, esBanco, m) {
  if (!regs.length) return `<div class="vacio">Sin movimientos</div>`;
  const dup = (x) => x.duplicado ? `<span class="badge b-warn" title="${esc(x.duplicado.motivo)}">Duplicado ${x.duplicado.origen === "BASE" ? "(ya existe)" : "(archivo)"}</span>` : "";
  if (esBanco) return `<table class="tabla"><thead><tr><th>Fila</th><th>Fecha</th><th>Descripción</th><th>N.º operación</th><th>Categoría</th><th class="num">Importe</th><th class="num">Saldo</th><th></th></tr></thead><tbody>
    ${regs.map((x) => `<tr class="${x.duplicado ? "fila-dup" : ""}"><td>${x.fila}</td><td>${fecha(x.fecha)}</td><td>${esc(x.descripcion)}</td><td>${esc(x.numero_operacion || "")}</td>
      <td><span class="badge cat-${esc(x.categoria)}">${esc(x.categoria)}</span></td>${celdaImporte(x.importe, m)}<td class="num">${dinero(x.saldo, m)}</td><td>${dup(x)}</td></tr>`).join("")}</tbody></table>`;
  return `<table class="tabla"><thead><tr><th>Fila</th><th>Fecha</th><th>Voucher</th><th>Glosa</th><th>N.º doc./op.</th><th>Tercero</th><th class="num">Debe</th><th class="num">Haber</th><th></th></tr></thead><tbody>
    ${regs.map((x) => `<tr class="${x.duplicado ? "fila-dup" : ""}"><td>${x.fila}</td><td>${fecha(x.fecha)}</td><td>${esc(x.voucher || "")}</td><td>${esc(x.glosa)}</td><td>${esc(x.numero_operacion || "")}</td><td>${esc(x.tercero || "")}</td>
      <td class="num">${Number(x.debe) ? dinero(x.debe, m) : ""}</td><td class="num">${Number(x.haber) ? dinero(x.haber, m) : ""}</td><td>${dup(x)}</td></tr>`).join("")}</tbody></table>`;
}

function pasoResultado() {
  const r = imp.resultado, m = cuentaPorId(imp.cuentaId)?.moneda;
  $("#paso-cuerpo").innerHTML = `
    <div class="card">
      <div class="alerta alerta-ok"><b>Importación #${r.id} registrada.</b> ${r.total_registros} movimientos de ${esc(r.nombre_archivo)}.</div>
      <table class="mini-tabla" style="max-width:520px">
        <tr><td>Período</td><td>${fecha(r.fecha_desde)} – ${fecha(r.fecha_hasta)}</td></tr>
        <tr><td>Ingresos / egresos</td><td>${dinero(r.total_ingresos, m)} / ${dinero(r.total_egresos, m)}</td></tr>
        <tr><td>Saldo inicial / final</td><td>${dinero(r.saldo_inicial, m)} / ${dinero(r.saldo_final, m)}</td></tr>
        <tr><td>Marcados como posible duplicado</td><td>${r.total_duplicados}</td></tr>
        <tr><td>Omitidos por duplicado</td><td>${r.total_omitidos}</td></tr>
      </table>
      <div class="acciones">
        <button class="btn" id="otra">Importar otro archivo</button>
        <a class="btn btn-primario" href="#/movimientos?tipo=${r.tipo}&importacion=${r.id}&cuenta=${r.cuenta_bancaria_id}">Ver movimientos importados</a>
      </div>
    </div>`;
  $("#otra").onclick = () => { Object.assign(imp, { paso: 1, archivo: null, previa: null, mapeo: null }); pintarImportar(); };
}

// ------------------------------------------------------------- movimientos
const filtrosMov = { tipo: "BANCO", cuenta_id: "", desde: "", hasta: "", estado: "", categoria: "", texto: "", solo_duplicados: false, importacion_id: "", pagina: 1 };

rutas.movimientos = async () => {
  if (!requiereEmpresa()) return;
  const p = parametrosHash();
  if (p.tipo) filtrosMov.tipo = p.tipo;
  if (p.cuenta) filtrosMov.cuenta_id = p.cuenta;
  filtrosMov.importacion_id = p.importacion || "";
  if (Object.keys(p).length) filtrosMov.pagina = 1;
  if (filtrosMov.cuenta_id && !cuentaPorId(filtrosMov.cuenta_id)) filtrosMov.cuenta_id = "";
  await pintarMovimientos();
};

async function pintarMovimientos() {
  const f = filtrosMov, esBanco = f.tipo === "BANCO";
  const params = { ...f, empresa_id: estado.empresaId, por_pagina: 100 };
  delete params.tipo;
  if (!esBanco) delete params.categoria;
  const datos = await vigente(api(`/movimientos/${esBanco ? "banco" : "libro"}`, { params }));
  const categorias = ["ITF", "COMISION", "INTERES", "RETENCION", "TRANSFERENCIA", "DEPOSITO", "CHEQUE", "PAGO", "RETIRO", "OTRO"];
  const monedaUnica = f.cuenta_id ? cuentaPorId(f.cuenta_id)?.moneda : null;
  const paginas = Math.max(1, Math.ceil(datos.total / datos.por_pagina));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Movimientos</h1><p class="sub">Consulta de movimientos importados y revisión de duplicados.</p></div>
      <div class="pasos" style="margin:0">
        <button class="btn ${esBanco ? "btn-primario" : ""}" data-tipo="BANCO">Banco</button>
        <button class="btn ${!esBanco ? "btn-primario" : ""}" data-tipo="LIBRO">Libro (cuenta 10)</button>
      </div></div>
    <div class="card">
      <form class="filtros" id="f-mov">
        <div class="campo"><label>Cuenta</label><select name="cuenta_id"><option value="">Todas</option>${opcionesCuentas(f.cuenta_id)}</select></div>
        <div class="campo"><label>Desde</label><input type="date" name="desde" value="${esc(f.desde)}"></div>
        <div class="campo"><label>Hasta</label><input type="date" name="hasta" value="${esc(f.hasta)}"></div>
        <div class="campo"><label>Estado</label><select name="estado"><option value="">Todos</option>${["PENDIENTE", "PROPUESTO", "CONCILIADO", "EXCLUIDO"].map((e) => `<option ${f.estado === e ? "selected" : ""}>${e}</option>`).join("")}</select></div>
        ${esBanco ? `<div class="campo"><label>Categoría</label><select name="categoria"><option value="">Todas</option>${categorias.map((c) => `<option ${f.categoria === c ? "selected" : ""}>${c}</option>`).join("")}</select></div>` : ""}
        <div class="campo" style="flex:1"><label>Buscar</label><input name="texto" placeholder="descripción, n.º operación, voucher…" value="${esc(f.texto)}"></div>
        <label class="check"><input type="checkbox" name="solo_duplicados" ${f.solo_duplicados ? "checked" : ""}> Solo posibles duplicados</label>
        <button class="btn btn-primario">Filtrar</button>
      </form>
      ${f.importacion_id ? `<div class="alerta alerta-info">Filtrando por importación #${esc(f.importacion_id)} · <a href="#/movimientos" id="quitar-imp">quitar filtro</a></div>` : ""}
    </div>
    <div class="tabla-wrap">${esBanco ? tablaBanco(datos.items) : tablaLibro(datos.items)}</div>
    <div class="paginacion">
      <span>${datos.total} movimiento(s) · Neto (sin excluidos): <b>${monedaUnica ? dinero(datos.suma_importes, monedaUnica) : fmtNum.format(datos.suma_importes)}</b>${monedaUnica ? "" : " (seleccione una cuenta para ver la moneda)"}</span>
      <span><button class="btn btn-sm" id="pg-ant" ${f.pagina <= 1 ? "disabled" : ""}>‹ Anterior</button> Página ${f.pagina} de ${paginas} <button class="btn btn-sm" id="pg-sig" ${f.pagina >= paginas ? "disabled" : ""}>Siguiente ›</button></span>
    </div>`;

  $$("[data-tipo]").forEach((b) => { b.onclick = () => { f.tipo = b.dataset.tipo; f.pagina = 1; f.importacion_id = ""; pintarMovimientos(); }; });
  $("#f-mov").onsubmit = (ev) => { ev.preventDefault(); Object.assign(f, datosForm(ev.target), { pagina: 1 }); pintarMovimientos(); };
  $("#pg-ant").onclick = () => { f.pagina--; pintarMovimientos(); };
  $("#pg-sig").onclick = () => { f.pagina++; pintarMovimientos(); };
  $$("[data-dup]").forEach((b) => { b.onclick = () => decidirDuplicado(f.tipo, b.dataset.id, b.dataset.dup); });
}

function accionesDup(x) {
  if (x.estado_conciliacion === "EXCLUIDO" && x.posible_duplicado)
    return `<button class="btn btn-sm" data-dup="RESTAURAR" data-id="${x.id}">Restaurar</button>`;
  if (!x.posible_duplicado || x.estado_conciliacion !== "PENDIENTE") return "";
  return `<button class="btn btn-sm btn-peligro" data-dup="EXCLUIR" data-id="${x.id}" title="Es un duplicado: excluirlo">Excluir</button>
          <button class="btn btn-sm" data-dup="MANTENER" data-id="${x.id}" title="Es un movimiento legítimo">Mantener</button>`;
}
function claseFila(x) { return x.estado_conciliacion === "EXCLUIDO" ? "fila-excl" : x.posible_duplicado ? "fila-dup" : ""; }
function dupInfo(x) { return x.posible_duplicado ? `<br><span class="badge b-warn" title="${esc(x.motivo_duplicado)}">Posible duplicado</span>` : ""; }

function tablaBanco(items) {
  if (!items.length) return `<div class="vacio">No hay movimientos con estos filtros</div>`;
  return `<table class="tabla"><thead><tr><th>Fecha</th><th>Cuenta</th><th>Descripción</th><th>N.º operación</th><th>Categoría</th><th class="num">Importe</th><th class="num">Saldo</th><th>Estado</th><th></th></tr></thead><tbody>
    ${items.map((x) => { const c = cuentaPorId(x.cuenta_bancaria_id); return `<tr class="${claseFila(x)}">
      <td>${fecha(x.fecha)}</td><td>${esc(c?.cuenta_contable || "")}</td><td>${esc(x.descripcion)}${dupInfo(x)}</td><td>${esc(x.numero_operacion || "")}</td>
      <td><span class="badge cat-${esc(x.categoria)}">${esc(x.categoria)}</span></td>${celdaImporte(x.importe, x.moneda)}<td class="num">${dinero(x.saldo, x.moneda)}</td>
      <td>${badgeEstado(x.estado_conciliacion)}</td><td class="num">${accionesDup(x)}</td></tr>`; }).join("")}</tbody></table>`;
}
function tablaLibro(items) {
  if (!items.length) return `<div class="vacio">No hay movimientos con estos filtros</div>`;
  return `<table class="tabla"><thead><tr><th>Fecha</th><th>Subcuenta</th><th>Voucher</th><th>Glosa</th><th>N.º doc./op.</th><th>Tercero</th><th class="num">Debe</th><th class="num">Haber</th><th>Estado</th><th></th></tr></thead><tbody>
    ${items.map((x) => `<tr class="${claseFila(x)}">
      <td>${fecha(x.fecha)}</td><td>${esc(x.cuenta_contable || "")}</td><td>${esc(x.voucher || "")}</td><td>${esc(x.glosa)}${dupInfo(x)}</td><td>${esc(x.numero_operacion || "")}</td><td>${esc(x.tercero || "")}</td>
      <td class="num">${Number(x.debe) ? dinero(x.debe, x.moneda) : ""}</td><td class="num">${Number(x.haber) ? dinero(x.haber, x.moneda) : ""}</td>
      <td>${badgeEstado(x.estado_conciliacion)}</td><td class="num">${accionesDup(x)}</td></tr>`).join("")}</tbody></table>`;
}

function decidirDuplicado(tipo, id, decision) {
  const textos = { EXCLUIR: "Confirmar que es un duplicado y excluirlo", MANTENER: "Confirmar que es un movimiento legítimo", RESTAURAR: "Restaurar el movimiento a pendiente" };
  const cuerpo = abrirModal(textos[decision], `
    <form id="f-dup"><div class="campo"><label>Comentario (queda en la auditoría)</label><input name="comentario" maxlength="200"></div>
    <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-primario">Confirmar</button></div></form>`);
  $("#f-dup", cuerpo).onsubmit = async (ev) => {
    ev.preventDefault();
    try {
      await api(`/movimientos/${tipo.toLowerCase()}/${id}/duplicado`, { method: "POST", body: { decision, comentario: datosForm(ev.target).comentario || null } });
      cerrarModal(); toast("Decisión registrada", "ok"); pintarMovimientos();
    } catch (err) { toast(err.message, "err"); }
  };
}

// ----------------------------------------------------------- importaciones
rutas.importaciones = async () => {
  if (!requiereEmpresa()) return;
  const lista = await vigente(api("/importaciones", { params: { empresa_id: estado.empresaId } }));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Historial de importaciones</h1><p class="sub">Cada carga queda registrada con su usuario, archivo, huella e incidencias. Anular excluye sus movimientos sin borrarlos.</p></div>
      <a class="btn btn-primario" href="#/importar">Nueva importación</a></div>
    <div class="tabla-wrap"><table class="tabla">
      <thead><tr><th>#</th><th>Fecha de carga</th><th>Cuenta</th><th>Tipo</th><th>Archivo</th><th>Período</th><th class="num">Movs.</th><th class="num">Dup.</th><th class="num">Ingresos</th><th class="num">Egresos</th><th>Estado</th><th></th></tr></thead>
      <tbody>${lista.map((i) => { const c = cuentaPorId(i.cuenta_bancaria_id); const m = c?.moneda; return `<tr class="${i.estado === "ANULADA" ? "fila-excl" : ""}">
        <td>${i.id}</td><td class="nowrap">${fechaHora(i.creado_en)}<br><small class="sub">${esc(i.usuario)}</small></td><td>${esc(c?.cuenta_contable || i.cuenta_bancaria_id)}</td><td><span class="badge ${i.tipo === "BANCO" ? "b-info" : ""}">${i.tipo === "BANCO" ? "Banco" : "Libro"}</span></td>
        <td>${esc(i.nombre_archivo)} <span class="badge">${esc(i.formato)}</span></td><td class="nowrap">${fecha(i.fecha_desde)}<br>${fecha(i.fecha_hasta)}</td>
        <td class="num">${i.total_registros}</td><td class="num">${i.total_duplicados}</td><td class="num">${dinero(i.total_ingresos, m)}</td><td class="num">${dinero(i.total_egresos, m)}</td>
        <td>${badgeEstado(i.estado)}</td>
        <td><div class="acc-col"><button class="btn btn-sm" data-ver="${i.id}">Detalle</button>
          <a class="btn btn-sm" href="#/movimientos?tipo=${i.tipo}&importacion=${i.id}&cuenta=${i.cuenta_bancaria_id}">Movs.</a>
          ${i.estado === "ACTIVA" ? `<button class="btn btn-sm btn-peligro" data-anular="${i.id}">Anular</button>` : ""}</div></td></tr>`; }).join("")
        || `<tr><td colspan="12" class="vacio">Sin importaciones</td></tr>`}</tbody>
    </table></div>`;
  $$("[data-ver]").forEach((b) => { b.onclick = () => detalleImportacion(b.dataset.ver); });
  $$("[data-anular]").forEach((b) => { b.onclick = () => anularImportacion(b.dataset.anular); });
};

async function detalleImportacion(id) {
  const d = await api(`/importaciones/${id}`);
  const inc = d.incidencias || {};
  abrirModal(`Importación #${d.id}`, `
    <table class="mini-tabla">
      <tr><td>Archivo</td><td>${esc(d.nombre_archivo)} (${esc(d.formato)})</td></tr>
      <tr><td>Método de lectura</td><td>${esc(d.mapeo?.metodo || "")}</td></tr>
      <tr><td>Usuario / fecha</td><td>${esc(d.usuario)} · ${fechaHora(d.creado_en)}</td></tr>
      <tr><td>Estado</td><td>${badgeEstado(d.estado)}${d.motivo_anulacion ? " · " + esc(d.motivo_anulacion) : ""}</td></tr>
    </table>
    <h3 style="margin:14px 0 6px">Mapeo de columnas</h3>
    <pre class="json">${esc(JSON.stringify(d.mapeo?.columnas || {}, null, 2))}</pre>
    ${(inc.advertencias || []).length ? `<div class="alerta alerta-warn"><ul>${inc.advertencias.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>` : ""}
    ${(inc.errores || []).length ? `<div class="alerta alerta-err"><b>Filas descartadas</b><ul>${inc.errores.map((e) => `<li>Fila ${e.fila}: ${esc(e.mensaje)}</li>`).join("")}</ul></div>` : ""}`);
}

function anularImportacion(id) {
  const cuerpo = abrirModal(`Anular importación #${id}`, `
    <div class="alerta alerta-warn">Los movimientos de esta importación pasarán a estado EXCLUIDO. No se puede anular si alguno ya está conciliado.</div>
    <form id="f-anu"><div class="campo"><label>Motivo (obligatorio)</label><input name="motivo" required minlength="5" maxlength="255"></div>
    <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-peligro">Anular</button></div></form>`);
  $("#f-anu", cuerpo).onsubmit = async (ev) => {
    ev.preventDefault();
    try { await api(`/importaciones/${id}/anular`, { method: "POST", body: datosForm(ev.target) }); cerrarModal(); toast("Importación anulada", "ok"); navegar(); }
    catch (err) { toast(err.message, "err"); }
  };
}

// --------------------------------------------------------------- auditoría
rutas.auditoria = async () => {
  const lista = await vigente(api("/auditoria", { params: { empresa_id: estado.empresaId } }));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Auditoría</h1><p class="sub">Bitácora inmutable de altas, cambios, importaciones, anulaciones y decisiones.</p></div></div>
    <div class="tabla-wrap"><table class="tabla">
      <thead><tr><th>Fecha</th><th>Usuario</th><th>Entidad</th><th>Acción</th><th>Detalle</th><th></th></tr></thead>
      <tbody>${lista.map((a) => `<tr><td>${fechaHora(a.fecha)}</td><td>${esc(a.usuario)}</td><td>${esc(a.entidad)} #${esc(a.entidad_id ?? "")}</td>
        <td><span class="badge b-info">${esc(a.accion)}</span></td><td>${esc(a.detalle || "")}</td>
        <td class="num">${a.datos ? `<button class="btn btn-sm" data-datos="${a.id}">Cambios</button>` : ""}</td></tr>`).join("")
        || `<tr><td colspan="6" class="vacio">Sin registros</td></tr>`}</tbody>
    </table></div>`;
  $$("[data-datos]").forEach((b) => {
    b.onclick = () => {
      const a = lista.find((x) => x.id === Number(b.dataset.datos));
      const d = JSON.parse(a.datos);
      const cuerpo = d.cambios && Object.keys(d.cambios).length
        ? `<table class="tabla"><thead><tr><th>Campo</th><th>Antes</th><th>Después</th></tr></thead><tbody>${Object.entries(d.cambios).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v.antes)}</td><td>${esc(v.despues)}</td></tr>`).join("")}</tbody></table>`
        : `<pre class="json">${esc(JSON.stringify(d.despues || d, null, 2))}</pre>`;
      abrirModal(`${a.accion} · ${a.entidad} #${a.entidad_id ?? ""}`, cuerpo);
    };
  });
};

// ----------------------------------------------------------------- inicio
document.addEventListener("click", (e) => { if (e.target.closest("[data-cerrar]")) cerrarModal(); });
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") cerrarModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarModal(); });

(async function iniciar() {
  const inpUsuario = $("#inp-usuario");
  inpUsuario.value = almacen.leer("cb_usuario", "");
  inpUsuario.onchange = () => { almacen.guardar("cb_usuario", inpUsuario.value.trim()); toast(`Operando como ${usuario()}`); };
  $("#sel-empresa").onchange = async (e) => {
    estado.empresaId = Number(e.target.value) || null;
    almacen.guardar("cb_empresa", estado.empresaId ?? "");
    Object.assign(filtrosMov, { cuenta_id: "", importacion_id: "", pagina: 1 });
    imp.cuentaId = null;
    await cargarCuentas();
    navegar();
  };
  try {
    const s = await api("/salud");
    $("#version").textContent = s.version;
    await cargarMaestros();
  } catch (e) { toast(e.message, "err"); }
  window.addEventListener("hashchange", navegar);
  navegar();
})();
