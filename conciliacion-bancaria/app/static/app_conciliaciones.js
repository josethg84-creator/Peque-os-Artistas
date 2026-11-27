/* Fase 6 — Motor de conciliaciones contables: dashboard, centro de conciliaciones, asistente de importación de fuentes,
   panel dual de conciliación manual, explorador de diferencias, centro de incidencias, diseñador de reglas, historial,
   panel de aprobación y centro de exportación. Todo es analítico: no modifica asientos ni genera ajustes.
   Reutiliza utilitarios de app.js, app_contable.js (barraProgreso, esperarTrabajo), app_analisis.js (gráficos, num),
   app_compensacion.js (paginador) y app_anexos.js (bajar). */
"use strict";

const cq = { cat: null, ejercicio: new Date().getFullYear(), periodo: null };
const EST_Q = { BORRADOR: ["Borrador", ""], EJECUTADA: ["Ejecutada", "b-info"], EN_REVISION: ["En revisión", "b-warn"], OBSERVADA: ["Observada", "b-err"],
  REVISADA: ["Revisada", "b-info"], APROBADA: ["Aprobada", "b-ok"], CERRADA: ["Cerrada", "b-ok"], REABIERTA: ["Reabierta", "b-warn"] };
const EST_DIF = { DETECTADO: ["Detectado", "b-err"], PENDIENTE_REVISION: ["Pendiente de revisión", "b-warn"], EN_ANALISIS: ["En análisis", "b-warn"],
  JUSTIFICADO: ["Justificado", "b-info"], PENDIENTE_REGULARIZACION: ["Pendiente de regularización", "b-warn"], SUBSANADO: ["Subsanado", "b-ok"],
  APROBADO: ["Aprobado", "b-ok"], CERRADO: ["Cerrado", "b-ok"], REABIERTO: ["Reabierto", "b-err"] };
const PRIO_Q = { CRITICO: "#b42318", ALTO: "#dc3c3d", MEDIO: "#f18a59", BAJO: "#fbb315", INFORMATIVO: "#8a94a6" };
const ASIG_Q = { CONCILIADO: "b-ok", PROPUESTO: "b-info", PARCIAL: "b-warn", PENDIENTE: "b-err", AMBIGUO: "b-warn", DUPLICADO: "b-err", EXCLUIDO: "" };
const ACC_Q = { EN_REVISION: "Enviar a revisión", OBSERVADA: "Observar", REVISADA: "Marcar revisada", APROBADA: "Aprobar", CERRADA: "Cerrar" };
const SIG_DIF = { DETECTADO: ["PENDIENTE_REVISION", "EN_ANALISIS", "JUSTIFICADO", "PENDIENTE_REGULARIZACION", "SUBSANADO"],
  PENDIENTE_REVISION: ["EN_ANALISIS", "JUSTIFICADO", "PENDIENTE_REGULARIZACION", "SUBSANADO"], EN_ANALISIS: ["JUSTIFICADO", "PENDIENTE_REGULARIZACION", "SUBSANADO"],
  JUSTIFICADO: ["APROBADO", "CERRADO", "REABIERTO"], PENDIENTE_REGULARIZACION: ["SUBSANADO", "APROBADO"], SUBSANADO: ["APROBADO", "CERRADO", "REABIERTO"],
  APROBADO: ["CERRADO", "REABIERTO"], CERRADO: ["REABIERTO"], REABIERTO: ["EN_ANALISIS", "JUSTIFICADO", "PENDIENTE_REGULARIZACION", "SUBSANADO"] };

const chipQ = (map, k) => { const [t, c] = map[k] || [k || "—", ""]; return `<span class="badge ${c}">${esc(t)}</span>`; };
const prioQ = (p) => `<span class="badge riesgo" style="--c:${PRIO_Q[p] || "#8a94a6"}">${esc(p || "—")}</span>`;
const asigQ = (a) => (a ? `<span class="badge ${ASIG_Q[a.estado] || ""}">${esc(a.estado)}</span>` : "—");
const pQ = (extra = {}) => ({ empresa_id: estado.empresaId, ...extra });
const puedeQ = (a) => !!cq.cat?.permisos?.[a];
const nombreTipoQ = (t) => cq.cat?.tipos.find((x) => x.codigo === t)?.nombre || t;

async function inicioQ() {
  if (!requiereEmpresa()) return false;
  cq.cat = await vigente(api("/conciliaciones/catalogo", { params: pQ() }));
  const g = JSON.parse(almacen.leer(`cq_ctx_${estado.empresaId}`, "null") || "null");
  if (g) Object.assign(cq, g);
  return true;
}
function barraQ() {
  const per = ['<option value="">Todos</option>'].concat(Array.from({ length: 12 }, (_, i) => i + 1)
    .map((p) => `<option value="${p}" ${p === cq.periodo ? "selected" : ""}>${String(p).padStart(2, "0")}</option>`)).join("");
  return `<div class="ctx-bar"><label>Ejercicio <input type="number" id="cq-ej" value="${cq.ejercicio}" style="width:90px;min-width:0"></label>
    <label>Periodo <select id="cq-pe">${per}</select></label>
    <span class="sub">Rol: <b>${esc(cq.cat.rol || "modo abierto")}</b> · Análisis sin modificar asientos ni generar ajustes</span></div>`;
}
function enlazarQ() {
  const g = () => { almacen.guardar(`cq_ctx_${estado.empresaId}`, JSON.stringify({ ejercicio: cq.ejercicio, periodo: cq.periodo })); navegar(); };
  $("#cq-ej")?.addEventListener("change", (e) => { cq.ejercicio = Number(e.target.value) || cq.ejercicio; g(); });
  $("#cq-pe")?.addEventListener("change", (e) => { cq.periodo = Number(e.target.value) || null; g(); });
}

async function ejecutarQ(id, caja, forzar = false) {
  try {
    const r = await api(`/conciliaciones/${id}/ejecutar`, { method: "POST", params: pQ(), body: { forzar } });
    if (caja) caja.innerHTML = `<div class="card">${barraProgreso(0, "En cola")}<div class="acciones"><button class="btn btn-sm btn-peligro" data-cancelar>Cancelar</button></div></div>`;
    caja?.querySelector("[data-cancelar]")?.addEventListener("click", async () => {
      try { await api(`/conciliaciones/${id}/cancelar`, { method: "POST", params: pQ() }); toast("Cancelación solicitada"); } catch (e) { toast(e.message, "err"); }
    });
    await esperarTrabajo(r.trabajo, (t) => {
      const b = caja?.querySelector(".progreso"); if (!b) return;
      b.querySelector(".progreso-barra").style.width = `${Math.max(2, t.progreso)}%`;
      caja.querySelector(".progreso-txt").innerHTML = `<span>${esc(t.etapa)}</span><b>${t.progreso}%</b>`;
    });
    const c = await api(`/conciliaciones/${id}`, { params: pQ() });
    toast(c.estado_proceso === "CANCELADO" ? "Ejecución cancelada" : `Versión ${c.version?.numero ?? "—"}: ${c.resumen?.diferencias ?? 0} diferencias · ${c.etapa || ""}`, "ok");
  } catch (e) { toast(e.message, "err"); }
  if (caja) caja.innerHTML = "";
}

// ------------------------------------------------------------------ dashboard
rutas["conc"] = async () => {
  if (!(await inicioQ())) return;
  const d = await vigente(api("/conciliaciones/tablero", { params: pQ({ ejercicio: cq.ejercicio, periodo: cq.periodo }) }));
  const k = d.kpi;
  const tile = (l, v, sub = "", href = "") => `<div class="kpi"><div class="l">${l}</div><div class="v">${href ? `<a href="${href}">${v}</a>` : v}</div>${sub ? `<div class="l">${sub}</div>` : ""}</div>`;
  const pct = (v) => (v === null || v === undefined ? "—" : `${Number(v).toFixed(2)} %`);
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Conciliaciones contables</h1><p class="sub">Comparación de fuentes independientes: coincidencias, faltantes, duplicados y diferencias. No toda diferencia es un error contable.</p></div>
      <div class="acciones" style="margin:0"><a class="btn btn-primario" href="#/conc-centro">Centro de conciliaciones</a><a class="btn" href="#/conc-incidencias">Incidencias</a></div></div>
    ${barraQ()}
    <div class="grid grid-5">
      ${tile("Programadas", k.programadas)}${tile("Creadas", k.creadas, "", "#/conc-centro")}${tile("Ejecutadas", k.ejecutadas)}
      ${tile("Aprobadas o cerradas", k.aprobadas)}${tile("Pendientes", k.pendientes, `${k.en_revision} en revisión · ${k.observadas} observadas`)}
      ${tile("Registros comparados", k.registros_comparados.toLocaleString("es-PE"))}${tile("Conciliados", k.registros_conciliados.toLocaleString("es-PE"), `${k.registros_parciales} parciales`)}
      ${tile("No conciliados", k.registros_pendientes.toLocaleString("es-PE"), `${k.duplicados} duplicados`)}
      ${tile("% conciliado por cantidad", pct(k.pct_conciliado_cantidad))}${tile("% conciliado por importe", pct(k.pct_conciliado_importe))}
      ${tile("Importe pendiente (neto)", num(k.importe_pendiente_neto), `bruto ${num(k.importe_pendiente_bruto)}`)}
      ${tile("Diferencias críticas", `<span style="color:${k.diferencias_criticas ? "#b42318" : "inherit"}">${k.diferencias_criticas}</span>`, `${k.diferencias_abiertas} abiertas`, "#/conc-diferencias?prioridad=CRITICO")}
      ${tile("Dentro de tolerancia", k.dentro_tolerancia, "visibles y cuantificadas")}${tile("Avance del cierre", pct(k.avance_cierre))}
    </div>
    <p class="sub">${esc(d.nota)}${k.diferencias_duplicadas_entre_conciliaciones ? ` (${k.diferencias_duplicadas_entre_conciliaciones} partidas observadas en más de una conciliación).` : ""}</p>
    <div class="grid grid-2" style="margin-top:12px">
      <div class="card"><h2>Por tipo de conciliación</h2>${graficoBarras(d.por_tipo.map((x) => ({ etiqueta: nombreTipoQ(x.tipo), valor: Number(x.importe_pendiente) })), { color: "#dc3c3d" })}
        <table class="tabla"><thead><tr><th>Tipo</th><th class="num">Conciliaciones</th><th class="num">Registros</th><th class="num">Conciliados</th><th class="num">Diferencias</th></tr></thead>
        <tbody>${d.por_tipo.map((x) => `<tr><td>${esc(nombreTipoQ(x.tipo))}</td><td class="num">${x.conciliaciones}</td><td class="num">${x.registros}</td><td class="num">${x.conciliados}</td><td class="num">${x.diferencias}</td></tr>`).join("") || '<tr><td colspan="5" class="vacio">Sin conciliaciones</td></tr>'}</tbody></table></div>
      <div class="card"><h2>Evolución mensual</h2>${graficoLineas([{ nombre: "Conciliaciones", valores: d.mensual.map((x) => x.conciliaciones) }, { nombre: "Aprobadas", valores: d.mensual.map((x) => x.aprobadas) }, { nombre: "Diferencias", valores: d.mensual.map((x) => x.diferencias) }], d.mensual.map((x) => x.periodo.slice(5)))}</div>
      <div class="card"><h2>Diferencias por cuenta (importe abierto)</h2>${graficoBarras(d.por_cuenta.map((x) => ({ etiqueta: x.cuenta, valor: Number(x.importe) })))}</div>
      <div class="card"><h2>Antigüedad de diferencias abiertas</h2>${graficoBarras(d.antiguedad.map((x) => ({ etiqueta: `${x.tramo} (${x.cantidad})`, valor: Number(x.importe) })), { color: SERIES[1] })}</div>
      <div class="card"><h2>Riesgo (prioridad)</h2>${graficoBarras(Object.entries(d.por_prioridad).map(([p, n]) => ({ etiqueta: p, valor: n })), { colores: Object.keys(d.por_prioridad).map((p) => PRIO_Q[p]), etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Estado de aprobación</h2>${graficoBarras(Object.entries(d.por_estado).map(([e, n]) => ({ etiqueta: EST_Q[e]?.[0] || e, valor: n })), { etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Avance por responsable</h2><table class="tabla"><thead><tr><th>Responsable</th><th class="num">Asignadas</th><th class="num">Aprobadas</th><th class="num">Diferencias abiertas</th></tr></thead>
        <tbody>${d.por_responsable.map((x) => `<tr><td>${esc(x.responsable)}</td><td class="num">${x.asignadas}</td><td class="num">${x.aprobadas}</td><td class="num">${x.diferencias_abiertas}</td></tr>`).join("") || '<tr><td colspan="4" class="vacio">—</td></tr>'}</tbody></table></div>
      <div class="card"><h2>Diferencias recurrentes</h2>${tablaDifQ(d.recurrentes, false)}</div>
    </div>`;
  enlazarQ();
};

// ------------------------------------------------------------------ centro de conciliaciones
const fc = { tipo_codigo: "", estado: "", buscar: "", responsable: "", pagina: 1 };
rutas["conc-centro"] = async () => {
  if (!(await inicioQ())) return;
  const l = await vigente(api("/conciliaciones", { params: pQ({ ...fc, ejercicio: cq.ejercicio, periodo: cq.periodo, por_pagina: 25 }) }));
  const tipos = cq.cat.tipos.map((t) => `<option value="${t.codigo}" ${fc.tipo_codigo === t.codigo ? "selected" : ""}>${esc(t.nombre)}</option>`).join("");
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Centro de conciliaciones</h1><p class="sub">Cree, importe fuentes, ejecute, revise coincidencias, resuelva diferencias y apruebe.</p></div>
      <div class="acciones" style="margin:0">${puedeQ("operar") || cq.cat.tipos.some((t) => t.puede_operar) ? '<button class="btn btn-primario" id="cq-nueva">Nueva conciliación</button>' : ""}</div></div>
    ${barraQ()}
    <div class="card"><div class="filtros">
      <label>Tipo <select id="f-tipo"><option value="">Todos</option>${tipos}</select></label>
      <label>Estado <select id="f-est"><option value="">Todos</option>${Object.entries(EST_Q).map(([k, [t]]) => `<option value="${k}" ${fc.estado === k ? "selected" : ""}>${t}</option>`).join("")}</select></label>
      <label>Responsable <input id="f-resp" value="${esc(fc.responsable)}"></label>
      <label>Buscar <input id="f-bus" value="${esc(fc.buscar)}" placeholder="nombre"></label></div>
      <table class="tabla"><thead><tr><th>#</th><th>Conciliación</th><th>Tipo</th><th>Corte</th><th>Estado</th><th>Proceso</th><th class="num">Versión</th>
        <th class="num">Registros</th><th class="num">Diferencias</th><th>Responsable</th></tr></thead>
      <tbody>${l.items.map((c) => `<tr class="clic" data-id="${c.id}"><td>${c.id}</td><td><a href="#/conc-ver?id=${c.id}">${esc(c.nombre)}</a></td><td><small>${esc(nombreTipoQ(c.tipo_codigo))}</small></td>
        <td>${fecha(c.fecha_corte)}</td><td>${chipQ(EST_Q, c.estado)}</td><td><small>${esc(c.estado_proceso)}</small></td><td class="num">${c.version_actual || "—"}</td>
        <td class="num">${c.resumen ? Object.values(c.resumen.registros || {}).reduce((a, b) => a + b, 0) : "—"}</td><td class="num">${c.resumen?.diferencias ?? "—"}</td><td>${esc(c.responsable || "")}</td></tr>`).join("")
        || '<tr><td colspan="10" class="vacio">Sin conciliaciones para el filtro</td></tr>'}</tbody></table>
      ${paginador(l.total, l.pagina, l.por_pagina, (p) => { fc.pagina = p; navegar(); })}</div>`;
  enlazarQ();
  const re = (k) => (e) => { fc[k] = e.target.value; fc.pagina = 1; navegar(); };
  $("#f-tipo").addEventListener("change", re("tipo_codigo")); $("#f-est").addEventListener("change", re("estado"));
  $("#f-resp").addEventListener("change", re("responsable")); $("#f-bus").addEventListener("change", re("buscar"));
  $$("tr.clic").forEach((tr) => tr.addEventListener("dblclick", () => { location.hash = `#/conc-ver?id=${tr.dataset.id}`; }));
  $("#cq-nueva")?.addEventListener("click", formNuevaQ);
};

async function formNuevaQ() {
  const ops = cq.cat.tipos.filter((t) => t.puede_operar).map((t) => `<option value="${t.codigo}">${esc(t.nombre)}</option>`).join("");
  const plant = cq.cat.plantillas.filter((p) => p.personalizada).map((p) => `<option value="${p.id}" ${p.autorizada ? "" : "disabled"}>${esc(p.nombre)}${p.autorizada ? "" : " (sin autorizar)"}</option>`).join("");
  const hoy = new Date();
  const fin = new Date(Date.UTC(hoy.getFullYear(), hoy.getMonth(), 0)).toISOString().slice(0, 10);
  const m = abrirModal("Nueva conciliación", `<form id="fq" class="form-grid form-q">
    <label>Tipo <select name="tipo" id="fq-tipo">${ops}</select></label>
    <label>Plantilla personalizada <select name="plantilla_id"><option value="">Plantilla del sistema</option>${plant}</select></label>
    <label>Fecha de corte <input type="date" name="fecha_corte" value="${fin}" required></label>
    <label>Responsable <input name="responsable"></label><label>Fecha límite <input type="date" name="fecha_limite"></label>
    <div id="fq-amb" class="form-grid form-q" style="grid-column:1/-1"></div>
    <div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Crear</button></div></form>`);
  const ambito = async () => {
    const t = $("#fq-tipo").value;
    let h = `<label>Cuenta contable <input name="cuenta" placeholder="p. ej. 1212"></label><label>Moneda <select name="moneda"><option value="">Todas</option><option>PEN</option><option>USD</option></select></label>
      <label>Centro de costo <input name="centro_costo"></label><label>Proyecto <input name="proyecto"></label>`;
    if (t === "BANCARIA") h = `<label>Cuenta bancaria <select name="cuenta_bancaria_id" required>${estado.cuentas.filter((c) => c.empresa_id === estado.empresaId).map((c) => `<option value="${c.id}">${esc(nombreCuenta(c))}</option>`).join("")}</select></label>`;
    if (t === "INTERCOMPANIA") h = `<label>Empresa relacionada <select name="empresa_relacionada_id">${estado.empresas.filter((e) => e.id !== estado.empresaId).map((e) => `<option value="${e.id}">${esc(e.razon_social)}</option>`).join("")}</select></label>`;
    $("#fq-amb").innerHTML = h;
  };
  $("#fq-tipo").addEventListener("change", ambito); await ambito();
  m.querySelector("#fq").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const d = datosForm(ev.target);
    const amb = {};
    ["cuenta", "moneda", "centro_costo", "proyecto"].forEach((k) => { if (d[k]) amb[k] = d[k]; });
    ["cuenta_bancaria_id", "empresa_relacionada_id"].forEach((k) => { if (d[k]) amb[k] = Number(d[k]); });
    try {
      const c = await api("/conciliaciones", { method: "POST", params: pQ(), body: { tipo: d.tipo, plantilla_id: d.plantilla_id ? Number(d.plantilla_id) : null,
        fecha_corte: d.fecha_corte, responsable: d.responsable || null, fecha_limite: d.fecha_limite || null, ambito: amb } });
      cerrarModal(); location.hash = `#/conc-ver?id=${c.id}`;
    } catch (e) { toast(e.message, "err"); }
  });
}

// ------------------------------------------------------------------ vista de la conciliación
const vq = { id: null, pest: "resumen", pasada: null, a: { pagina: 1, buscar: "", estado: "PENDIENTE,PARCIAL,AMBIGUO" }, b: { pagina: 1, buscar: "", estado: "PENDIENTE,PARCIAL,AMBIGUO" },
  sel: { a: new Map(), b: new Map() }, grupos: { estado: "", pagina: 1 }, difs: { pagina: 1 } };
rutas["conc-ver"] = async () => {
  if (!(await inicioQ())) return;
  const id = Number(parametrosHash().id);
  if (vq.id !== id) Object.assign(vq, { id, pest: "resumen", pasada: null, sel: { a: new Map(), b: new Map() } });
  const c = await vigente(api(`/conciliaciones/${id}`, { params: pQ() }));
  const pas = c.version?.configuracion?.pasadas || [];
  if (!vq.pasada && pas.length) vq.pasada = `${pas[0].a}-${pas[0].b}`;
  const editable = c.version && !c.version.inmutable && ["EJECUTADA", "OBSERVADA"].includes(c.estado);
  const sig = { EJECUTADA: ["EN_REVISION"], OBSERVADA: ["EN_REVISION"], EN_REVISION: ["REVISADA", "OBSERVADA"], REVISADA: ["APROBADA", "OBSERVADA"], APROBADA: ["CERRADA"] }[c.estado] || [];
  const pest = [["resumen", "Resumen y reporte"], ["fuentes", "Fuentes"], ["panel", "Panel de conciliación"], ["grupos", "Coincidencias"], ["diferencias", "Diferencias"], ["historial", "Historial y aprobación"]];
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>${esc(c.nombre)}</h1><p class="sub">${esc(c.tipo_nombre)} · corte ${fecha(c.fecha_corte)} · ${chipQ(EST_Q, c.estado)} · versión ${c.version?.numero ?? "—"}${c.version?.inmutable ? " (inmutable)" : ""}
      ${c.datos_personales && !c.ve_datos_personales ? ' · <span class="badge b-warn">Datos personales enmascarados</span>' : ""}</p></div>
      <div class="acciones" style="margin:0">
        ${["BORRADOR", "EJECUTADA", "OBSERVADA", "REABIERTA"].includes(c.estado) ? '<button class="btn btn-primario" id="q-ejec">Ejecutar conciliación</button>' : ""}
        ${sig.map((s) => `<button class="btn" data-estado="${s}">${ACC_Q[s]}</button>`).join("")}
        ${["APROBADA", "CERRADA"].includes(c.estado) && puedeQ("revertir") ? '<button class="btn btn-peligro" id="q-rev">Revertir aprobación</button>' : ""}
        ${c.version ? '<button class="btn" id="q-xlsx">Excel</button><button class="btn" id="q-pdf">PDF</button>' : ""}</div></div>
    <div id="q-prog"></div>
    ${c.estado_proceso === "ERROR" ? `<div class="alerta alerta-err">La última ejecución falló: ${esc(c.error)}</div>` : ""}
    ${c.pendientes.ambiguas ? `<div class="alerta alerta-warn">${c.pendientes.ambiguas} coincidencia(s) ambigua(s): no se aprueban automáticamente; resuélvalas en «Coincidencias» o en el panel de conciliación.</div>` : ""}
    <div class="pestanas">${pest.map(([k, t]) => `<button class="btn ${vq.pest === k ? "btn-primario" : ""}" data-pest="${k}">${t}</button>`).join("")}</div>
    <div id="q-cuerpo"></div>`;
  $$("[data-pest]").forEach((b) => b.addEventListener("click", () => { vq.pest = b.dataset.pest; navegar(); }));
  $("#q-ejec")?.addEventListener("click", async () => { await ejecutarQ(id, $("#q-prog"), c.estado === "EJECUTADA"); navegar(); });
  $("#q-xlsx")?.addEventListener("click", () => bajar(`/conciliaciones/${id}/exportar`, pQ({ formato: "xlsx" }), "conciliacion.xlsx").catch((e) => toast(e.message, "err")));
  $("#q-pdf")?.addEventListener("click", () => bajar(`/conciliaciones/${id}/exportar`, pQ({ formato: "pdf" }), "conciliacion.pdf").catch((e) => toast(e.message, "err")));
  $$("[data-estado]").forEach((b) => b.addEventListener("click", () => cambiarEstadoQ(c, b.dataset.estado)));
  $("#q-rev")?.addEventListener("click", () => motivoQ("Revertir la conciliación aprobada", "Se reabrirá con una nueva versión; la versión aprobada se conserva inmutable.", async (m) => {
    await api(`/conciliaciones/${id}/revertir`, { method: "POST", params: pQ(), body: { motivo: m } });
  }));
  const fn = { resumen: pestResumenQ, fuentes: pestFuentesQ, panel: pestPanelQ, grupos: pestGruposQ, diferencias: pestDifQ, historial: pestHistQ }[vq.pest];
  await fn(c, editable, pas);
};

function motivoQ(titulo, texto, fn) {
  const m = abrirModal(titulo, `<p class="sub">${esc(texto)}</p><form id="fm"><label>Motivo / comentario <textarea name="m" rows="3" required minlength="10"></textarea></label>
    <div class="acciones"><button class="btn btn-primario">Confirmar</button></div></form>`);
  m.querySelector("#fm").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try { await fn(ev.target.m.value.trim()); cerrarModal(); toast("Registrado", "ok"); navegar(); } catch (e) { toast(e.message, "err"); }
  });
}
function cambiarEstadoQ(c, est) {
  const hacer = async (comentario) => api(`/conciliaciones/${c.id}/estado`, { method: "POST", params: pQ(), body: { estado: est, comentario, lock_version: c.lock_version } });
  if (est === "OBSERVADA") return motivoQ("Observar la conciliación", "Describa lo que debe corregirse.", hacer);
  hacer(null).then(() => { toast(ACC_Q[est], "ok"); navegar(); }).catch((e) => toast(e.message, "err"));
}

async function pestResumenQ(c) {
  const r = c.resumen || {}, rep = c.version?.reporte || {};
  const fila = (k, v) => `<tr><th style="width:45%">${k}</th><td style="white-space:normal">${v}</td></tr>`;
  let reporte = "";
  if (rep.tipo === "BANCARIA") {
    const lin = (t, v, b) => `<tr${b ? ' class="tot"' : ""}><td>${b ? `<b>${esc(t)}</b>` : esc(t)}</td><td class="num">${b ? `<b>${num(v)}</b>` : num(v)}</td></tr>`;
    reporte = `<div class="card"><h2>Conciliación bancaria</h2><p class="sub">${esc(rep.convencion)}</p><table class="tabla">
      ${lin("Saldo según estado bancario", rep.saldo_banco, true)}${rep.partidas_banco.map((x) => lin(x.concepto, x.importe)).join("")}${lin("Saldo bancario ajustado", rep.saldo_banco_ajustado, true)}
      ${lin("Saldo según libros", rep.saldo_libros, true)}${rep.partidas_libros.map((x) => lin(x.concepto, x.importe)).join("")}${lin("Saldo en libros ajustado", rep.saldo_libros_ajustado, true)}
      ${lin("Diferencia final", rep.diferencia_final, true)}</table>${rep.nota ? `<div class="alerta alerta-warn">${esc(rep.nota)}</div>` : ""}</div>`;
  } else if (rep.tipo) {
    reporte = `<div class="card"><h2>Reporte ${esc(rep.tipo)}</h2>${rep.nota ? `<p class="sub">${esc(rep.nota)}</p>` : ""}<pre class="pre">${esc(JSON.stringify(Object.fromEntries(Object.entries(rep).filter(([k]) => !["tipo", "nota"].includes(k))), null, 2))}</pre></div>`;
  }
  $("#q-cuerpo").innerHTML = !c.version ? `<div class="card"><p>Aún no se ha ejecutado. Importe las fuentes externas (pestaña «Fuentes») y ejecute la conciliación.</p></div>` : `
    <div class="grid grid-2">
      <div class="card"><h2>Resultado</h2><table class="tabla">
        ${Object.entries(r.registros || {}).map(([l, n]) => fila(`Registros fuente ${l}`, n.toLocaleString("es-PE"))).join("")}
        ${Object.entries(r.asignaciones || {}).map(([k, n]) => fila(`${k}`, `${n.toLocaleString("es-PE")} · ${num(r.importes?.[k])} · ${(r.porcentaje_cantidad?.[k] ?? 0).toFixed(2)} % cant. · ${(r.porcentaje_importe?.[k] ?? 0).toFixed(2)} % imp.`)).join("")}
        ${fila("Diferencias", `${r.diferencias} (${r.dentro_tolerancia} dentro de tolerancia)`)}${fila("Importe de diferencias", num(r.importe_diferencias))}
        ${fila("Duplicados / excluidos", `${r.duplicados} / ${r.excluidos}`)}${fila("Decisiones manuales re-aplicadas", `${r.manuales_reaplicadas} (no re-aplicadas: ${r.manuales_no_reaplicadas})`)}
        ${fila("Diferencias trasladadas de periodos anteriores", r.trasladadas)}${fila("Tolerancia aplicada", `absoluta ${num(r.tolerancia?.importe_absoluto)} · ${r.tolerancia?.porcentaje ?? "—"} % · ${r.tolerancia?.dias ?? 0} días`)}
        ${fila("Duración", `${c.duracion_ms ?? "—"} ms`)}</table>
        <p class="sub">Pendientes: ${c.pendientes.propuestas} propuestas · ${c.pendientes.ambiguas} ambiguas · ${c.pendientes.diferencias_abiertas} diferencias abiertas (${c.pendientes.criticas_abiertas} críticas).</p></div>
      <div class="card"><h2>Diferencias por clasificación</h2>${graficoBarras(Object.entries(r.por_clasificacion || {}).map(([k, n]) => ({ etiqueta: k.replaceAll("_", " ").toLowerCase(), valor: n })), { etiquetaValor: (v) => String(v) })}
        <h2>Etapas (ms)</h2>${graficoBarras(Object.entries(c.tiempos || {}).map(([k, n]) => ({ etiqueta: k, valor: n })), { etiquetaValor: (v) => String(v), color: SERIES[2] })}</div>
    </div>${reporte}`;
}

async function pestFuentesQ(c, editable) {
  const cfg = (await api(`/conciliaciones/plantillas/${c.plantilla_id}`, { params: pQ() })).configuracion;
  const vigentes = c.fuentes.filter((f) => f.vigente);
  $("#q-cuerpo").innerHTML = `<div class="grid grid-2">${Object.entries(cfg.fuentes).map(([lado, f]) => {
    const v = vigentes.find((x) => x.lado === lado);
    return `<div class="card"><h2>Fuente ${lado} · ${esc(f.nombre)}</h2><p class="sub">${esc(f.tipo)} · rol ${esc(f.rol)}${f.esquema ? ` · diseño ${esc(f.esquema)}` : ""}</p>
      ${v ? `<table class="tabla">${[["Registros", v.registros], ["Total", num(v.total)], ["Saldo informado", v.saldo !== null ? num(v.saldo) : "—"], ["Archivo", esc(v.nombre_archivo || "Generada desde el sistema")],
        ["Hash de datos", `<code>${esc((v.version_datos || "").slice(0, 16))}</code>`], ["Observaciones", esc(v.observaciones || "—")]].map(([k, x]) => `<tr><th>${k}</th><td>${x}</td></tr>`).join("")}</table>`
        : `<p class="sub">${f.tipo === "ARCHIVO" ? "Pendiente de importar." : "Se arma automáticamente al ejecutar (libro, registros y auxiliares importados)."}</p>`}
      ${f.tipo === "ARCHIVO" && ["BORRADOR", "EJECUTADA", "OBSERVADA", "REABIERTA"].includes(c.estado) ? `<button class="btn btn-primario" data-imp="${lado}">Importar archivo…</button>` : ""}
      ${f.tipo === "BANCO" ? '<p class="sub">El estado de cuenta se importa en <a href="#/importar">Importar estados de cuenta</a> (fase 1, incluye PDF con revisión manual).</p>' : ""}</div>`;
  }).join("")}</div>
  <div class="card"><h2>Historial de fuentes</h2><table class="tabla"><thead><tr><th>Lado</th><th>Fuente</th><th>Archivo</th><th class="num">Registros</th><th class="num">Total</th><th>Vigente</th><th>Usuario</th><th>Fecha</th></tr></thead>
    <tbody>${c.fuentes.map((f) => `<tr><td>${f.lado}</td><td>${esc(f.nombre)}</td><td>${esc(f.nombre_archivo || "—")}</td><td class="num">${f.registros}</td><td class="num">${num(f.total)}</td><td>${f.vigente ? "Sí" : "No (versiones anteriores)"}</td><td>${esc(f.creado_por)}</td><td>${fechaHora(f.creado_en)}</td></tr>`).join("")}</tbody></table></div>`;
  $$("[data-imp]").forEach((b) => b.addEventListener("click", () => asistenteImportQ(c, b.dataset.imp)));
}

function asistenteImportQ(c, lado) {
  const m = abrirModal(`Importar fuente ${lado}`, `<form id="fi"><label>Archivo (Excel, CSV o TXT) <input type="file" name="archivo" required></label>
    <div class="acciones"><button class="btn btn-primario">Vista previa</button></div></form><div id="fi-prev"></div>`);
  let archivo = null;
  const enviar = async (confirmar, extra = {}) => {
    const f = new FormData(); f.append("archivo", archivo); f.append("confirmar", confirmar ? "true" : "false");
    Object.entries(extra).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== "") f.append(k, v); });
    return api(`/conciliaciones/${c.id}/fuentes/${lado}/archivo`, { method: "POST", params: pQ(), form: f });
  };
  m.querySelector("#fi").addEventListener("submit", async (ev) => {
    ev.preventDefault(); archivo = ev.target.archivo.files[0];
    try {
      const v = await enviar(false);
      const pintar = (v) => {
        $("#fi-prev").innerHTML = `<h3>Homologación de columnas</h3><p class="sub">Formato ${esc(v.formato)} · fila de encabezado ${v.fila_encabezado + 1} · ${v.registros} registros · ${v.excluidos} filas excluidas (subtotales: ${v.filas_subtotal})</p>
          <table class="tabla"><thead><tr><th>Campo</th><th>Columna del archivo</th></tr></thead><tbody>${v.campos.map((cp) => `<tr><td>${esc(cp.etiqueta)}${cp.obligatorio ? " *" : ""}</td>
            <td><select data-campo="${cp.clave}"><option value="">— no usar —</option>${v.encabezados.map((h, i) => `<option value="${i}" ${v.mapeo[cp.clave] === i ? "selected" : ""}>${esc(h)}</option>`).join("")}</select></td></tr>`).join("")}</tbody></table>
          ${v.observaciones.length ? `<div class="alerta alerta-warn">${v.observaciones.slice(0, 10).map(esc).join("<br>")}</div>` : ""}
          <h3>Muestra</h3><div class="tabla-scroll"><table class="tabla"><thead><tr><th>Fecha</th><th>Documento</th><th>Tercero</th><th>Concepto</th><th class="num">Importe</th></tr></thead>
          <tbody>${v.muestra.map((x) => `<tr><td>${fecha(x.fecha)}</td><td>${esc([x.serie, x.numero].filter(Boolean).join("-") || x.operacion || "")}</td><td>${esc(x.tercero || "")}</td><td>${esc(x.concepto || "")}</td><td class="num">${num(x.importe)}</td></tr>`).join("")}</tbody></table></div>
          <form id="fi-ok" class="form-grid form-q"><label>Guardar homologación como <input name="g" placeholder="opcional"></label>
          <div class="acciones"><button type="button" class="btn" id="fi-re">Recalcular</button><button class="btn btn-primario">Confirmar importación</button></div></form>`;
        const mapeo = () => JSON.stringify(Object.fromEntries($$("[data-campo]").filter((s) => s.value !== "").map((s) => [s.dataset.campo, Number(s.value)])));
        $("#fi-re").addEventListener("click", async () => { try { pintar(await enviar(false, { mapeo: mapeo(), fila_encabezado: v.fila_encabezado })); } catch (e) { toast(e.message, "err"); } });
        $("#fi-ok").addEventListener("submit", async (e2) => {
          e2.preventDefault();
          try { const r = await enviar(true, { mapeo: mapeo(), fila_encabezado: v.fila_encabezado, guardar_mapeo: e2.target.g.value }); cerrarModal(); toast(`${r.registros} registros importados`, "ok"); navegar(); }
          catch (e) { toast(e.message, "err"); }
        });
      };
      pintar(v);
    } catch (e) { toast(e.message, "err"); }
  });
}

// panel dual: registros pendientes de ambas fuentes, selección múltiple, importes parciales y totales permanentes
async function pestPanelQ(c, editable, pas) {
  if (!c.version) { $("#q-cuerpo").innerHTML = '<div class="vacio">Ejecute la conciliación primero</div>'; return; }
  const [la, lb] = (vq.pasada || "A-B").split("-");
  const carga = (lado, f) => api(`/conciliaciones/${c.id}/registros`, { params: pQ({ lado, pasada: vq.pasada, por_pagina: 50, ...f }) });
  const [ra, rb] = await Promise.all([carga(la, vq.a), carga(lb, vq.b)]);
  const fuentes = c.version.fuentes;
  const panel = (k, lado, r, f) => `<div class="card"><h2>${lado} · ${esc(fuentes[lado]?.nombre || "")}</h2>
    <div class="filtros"><input data-bus="${k}" value="${esc(f.buscar)}" placeholder="documento, operación, tercero, glosa…">
      <select data-est="${k}">${[["PENDIENTE,PARCIAL,AMBIGUO", "No conciliados"], ["", "Todos"], ["CONCILIADO,PROPUESTO", "Conciliados"], ["DUPLICADO,EXCLUIDO", "Duplicados y excluidos"]]
        .map(([v, t]) => `<option value="${v}" ${f.estado === v ? "selected" : ""}>${t}</option>`).join("")}</select></div>
    <div class="tabla-scroll" style="max-height:440px"><table class="tabla"><thead><tr><th></th><th>Fecha</th><th>Documento</th><th>Descripción</th><th class="num">Importe</th><th class="num">Pendiente</th><th>Estado</th></tr></thead>
    <tbody>${r.items.map((x) => `<tr><td>${x.asignacion && Number(x.asignacion.pendiente) > 0 && editable ? `<input type="checkbox" data-sel="${k}" data-id="${x.id}" data-pend="${x.asignacion.pendiente}" ${vq.sel[k].has(x.id) ? "checked" : ""}>` : ""}</td>
      <td>${fecha(x.fecha)}</td><td><small>${esc([x.tipo_documento, [x.serie, x.numero].filter(Boolean).join("-")].filter(Boolean).join(" ") || x.operacion || x.referencia || x.concepto || "")}</small></td>
      <td><small>${esc(x.descripcion || x.razon_social || "")}</small></td><td class="num">${num(x.importe)}</td><td class="num">${x.asignacion ? num(x.asignacion.pendiente) : "—"}</td><td>${asigQ(x.asignacion)}</td></tr>`).join("") || '<tr><td colspan="7" class="vacio">Sin registros</td></tr>'}</tbody></table></div>
    ${paginador(r.total, r.pagina, r.por_pagina, (p) => { f.pagina = p; navegar(); })}
    <p class="sub">Total filtrado ${num(r.totales.importe)} · pendiente ${num(r.totales.pendiente)}</p></div>`;
  $("#q-cuerpo").innerHTML = `
    ${pas.length > 1 ? `<div class="pestanas">${pas.map((p) => `<button class="btn btn-sm ${vq.pasada === `${p.a}-${p.b}` ? "btn-primario" : ""}" data-pas="${p.a}-${p.b}">${p.a} ↔ ${p.b}</button>`).join("")}</div>` : ""}
    <div class="grid grid-2">${panel("a", la, ra, vq.a)}${panel("b", lb, rb, vq.b)}</div>
    <div class="card" id="q-totales" style="position:sticky;bottom:0"></div>`;
  const totales = () => {
    const suma = (k) => [...vq.sel[k].values()].reduce((s, v) => s + Number(v.importe), 0);
    const ta = suma("a"), tb = suma("b"), d = tb - ta;
    $("#q-totales").innerHTML = `<div class="filtros"><b>Seleccionado ${la}: ${num(ta)}</b><b>Seleccionado ${lb}: ${num(tb)}</b><b style="color:${Math.abs(d) < 0.005 ? "#00b894" : "#dc3c3d"}">Diferencia: ${num(d)}</b>
      <span class="badge ${Math.abs(d) < 0.005 && ta ? "b-ok" : "b-warn"}">${!ta && !tb ? "Sin selección" : Math.abs(d) < 0.005 ? "Cuadra" : "Con diferencia"}</span>
      ${editable ? `<input id="q-just" placeholder="Justificación (obligatoria)" style="flex:1;min-width:240px"><label class="sub"><input type="checkbox" id="q-acep"> aceptar diferencia</label>
      <button class="btn" id="q-prev">Vista previa</button><button class="btn btn-primario" id="q-conc">Conciliar</button><button class="btn" id="q-limp">Limpiar</button>` : '<span class="sub">Versión no editable (aprobada o en revisión)</span>'}</div>
      ${[...vq.sel.a.values(), ...vq.sel.b.values()].length ? `<div class="sub">Importes a aplicar (parciales permitidos): ${["a", "b"].map((k) => [...vq.sel[k].entries()].map(([id, v]) => `<label>#${id} <input data-imp-sel="${k}" data-id="${id}" value="${v.importe}" style="width:110px;min-width:0"></label>`).join(" ")).join(" ")}</div>` : ""}`;
    $$("[data-imp-sel]").forEach((i) => i.addEventListener("change", () => { vq.sel[i.dataset.impSel].get(Number(i.dataset.id)).importe = i.value; totales(); }));
    $("#q-limp")?.addEventListener("click", () => { vq.sel = { a: new Map(), b: new Map() }; navegar(); });
    $("#q-prev")?.addEventListener("click", () => abrirModal("Vista previa", `<p>Se conciliarán ${vq.sel.a.size} registro(s) de ${la} por ${num(ta)} con ${vq.sel.b.size} de ${lb} por ${num(tb)}.</p>
      <p>${Math.abs(d) < 0.005 ? "Los importes cuadran." : `Queda una diferencia de ${num(d)} que se registrará como diferencia monetaria si la acepta.`}</p><p class="sub">No se modifican asientos: la decisión se guarda en la versión vigente con su justificación y usuario.</p>`));
    $("#q-conc")?.addEventListener("click", async () => {
      const body = { pasada: vq.pasada, justificacion: $("#q-just").value, aceptar_diferencia: $("#q-acep").checked,
        registros_a: [...vq.sel.a.entries()].map(([id, v]) => ({ id, importe: v.importe })), registros_b: [...vq.sel.b.entries()].map(([id, v]) => ({ id, importe: v.importe })) };
      if (!confirm(`¿Confirmar la conciliación manual (${num(ta)} vs ${num(tb)})?`)) return;
      try { await api(`/conciliaciones/${c.id}/manual`, { method: "POST", params: pQ(), body }); vq.sel = { a: new Map(), b: new Map() }; toast("Conciliación manual registrada", "ok"); navegar(); }
      catch (e) { toast(e.message, "err"); }
    });
  };
  totales();
  $$("[data-pas]").forEach((b) => b.addEventListener("click", () => { vq.pasada = b.dataset.pas; vq.sel = { a: new Map(), b: new Map() }; navegar(); }));
  $$("[data-sel]").forEach((ch) => ch.addEventListener("change", () => {
    const m = vq.sel[ch.dataset.sel], id = Number(ch.dataset.id);
    if (ch.checked) m.set(id, { importe: ch.dataset.pend }); else m.delete(id);
    totales();
  }));
  $$("[data-bus]").forEach((i) => i.addEventListener("change", () => { vq[i.dataset.bus].buscar = i.value; vq[i.dataset.bus].pagina = 1; navegar(); }));
  $$("[data-est]").forEach((i) => i.addEventListener("change", () => { vq[i.dataset.est].estado = i.value; vq[i.dataset.est].pagina = 1; navegar(); }));
}

async function pestGruposQ(c, editable) {
  if (!c.version) { $("#q-cuerpo").innerHTML = '<div class="vacio">Sin versión</div>'; return; }
  const g = await api(`/conciliaciones/${c.id}/grupos`, { params: pQ({ estado: vq.grupos.estado, pagina: vq.grupos.pagina, por_pagina: 30 }) });
  $("#q-cuerpo").innerHTML = `<div class="card"><div class="filtros"><select id="g-est">${[["", "Todas"], ["AMBIGUA", "Ambiguas"], ["PROPUESTA", "Propuestas"], ["CONFIRMADA", "Confirmadas"], ["RECHAZADA,REVERTIDA", "Rechazadas o revertidas"]]
      .map(([v, t]) => `<option value="${v}" ${vq.grupos.estado === v ? "selected" : ""}>${t}</option>`).join("")}</select>
      ${editable ? '<button class="btn btn-sm" id="g-conf-todas">Confirmar propuestas visibles</button>' : ""}</div>
    <table class="tabla"><thead><tr><th>#</th><th>Tipo</th><th>Modalidad</th><th>Regla</th><th>Estado</th><th class="num">Importe A</th><th class="num">Importe B</th><th class="num">Diferencia</th><th>Registros</th><th></th></tr></thead>
    <tbody>${g.items.map((x) => `<tr><td>${x.id}</td><td>${esc(x.tipo)}</td><td>${esc(x.modalidad)}</td><td><small>${esc(x.regla)}</small></td><td><span class="badge ${x.estado === "CONFIRMADA" ? "b-ok" : x.estado === "AMBIGUA" ? "b-warn" : x.estado === "PROPUESTA" ? "b-info" : ""}">${esc(x.estado)}</span></td>
      <td class="num">${num(x.importe_a)}</td><td class="num">${num(x.importe_b)}</td><td class="num">${num(x.diferencia)}</td>
      <td><small>${x.registros.map((r) => `${r.lado}: ${esc(r.documento || "")} ${num(r.importe_aplicado)}`).join("<br>")}${x.detalle.motivo ? `<br><i>${esc(x.detalle.motivo)}</i>` : ""}${x.justificacion ? `<br><i>${esc(x.justificacion)}</i>` : ""}</small></td>
      <td>${editable ? `${x.estado === "PROPUESTA" ? `<button class="btn btn-sm" data-g="confirmar" data-id="${x.id}">Confirmar</button>` : ""}
        ${["PROPUESTA", "AMBIGUA"].includes(x.estado) ? `<button class="btn btn-sm" data-g="rechazar" data-id="${x.id}">Rechazar</button>` : ""}
        ${x.estado === "CONFIRMADA" && puedeQ("revertir") ? `<button class="btn btn-sm btn-peligro" data-g="revertir" data-id="${x.id}">Revertir</button>` : ""}` : ""}</td></tr>`).join("") || '<tr><td colspan="10" class="vacio">Sin coincidencias</td></tr>'}</tbody></table>
    ${paginador(g.total, g.pagina, g.por_pagina, (p) => { vq.grupos.pagina = p; navegar(); })}</div>`;
  $("#g-est").addEventListener("change", (e) => { vq.grupos.estado = e.target.value; vq.grupos.pagina = 1; navegar(); });
  const decidir = (id, acc, motivo) => api(`/conciliaciones/grupos/${id}/${acc}`, { method: "POST", params: pQ(), body: { motivo } });
  $$("[data-g]").forEach((b) => b.addEventListener("click", () => {
    if (b.dataset.g === "confirmar") decidir(b.dataset.id, "confirmar").then(() => navegar()).catch((e) => toast(e.message, "err"));
    else motivoQ(b.dataset.g === "rechazar" ? "Rechazar coincidencia" : "Revertir coincidencia confirmada", "Los registros vuelven a quedar pendientes.", (m) => decidir(b.dataset.id, b.dataset.g, m));
  }));
  $("#g-conf-todas")?.addEventListener("click", async () => {
    for (const x of g.items.filter((y) => y.estado === "PROPUESTA")) { try { await decidir(x.id, "confirmar"); } catch (e) { toast(e.message, "err"); break; } }
    navegar();
  });
}

function tablaDifQ(items, conAcciones = true) {
  if (!items.length) return '<div class="vacio">Sin diferencias</div>';
  return `<div class="tabla-scroll"><table class="tabla"><thead><tr><th>Código</th><th>Prioridad</th><th>Clasificación</th><th>Documento</th><th>Tercero</th><th class="num">Importe</th>
    <th class="num">Pendiente</th><th>Estado</th><th>Responsable</th><th class="num">Días</th><th>Explicación</th></tr></thead>
    <tbody>${items.map((d) => `<tr class="${conAcciones ? "clic" : ""}" data-dif="${d.id}"><td><small>${esc(d.codigo)}</small>${d.anterior_id ? ' <span class="badge b-info" title="Viene de un periodo o versión anterior">↺</span>' : ""}</td><td>${prioQ(d.prioridad)}</td>
      <td><small>${esc(d.clasificacion)}<br><i>${esc(d.subtipo || "")}</i></small></td><td><small>${esc(d.documento || "")}</small></td><td><small>${esc(d.tercero || "")}</small></td>
      <td class="num">${num(d.importe)}${d.dentro_tolerancia ? '<br><span class="badge">en tolerancia</span>' : ""}</td><td class="num">${num(d.importe_pendiente)}</td><td>${chipQ(EST_DIF, d.estado)}${d.vencida ? ' <span class="badge b-err">vencida</span>' : ""}</td>
      <td><small>${esc(d.responsable || "")}</small></td><td class="num">${d.antiguedad_dias ?? ""}</td><td><small>${esc(d.explicacion || "")}</small></td></tr>`).join("")}</tbody></table></div>`;
}

async function pestDifQ(c) {
  const r = await api("/conciliaciones/diferencias", { params: pQ({ run_id: c.id, pagina: vq.difs.pagina, por_pagina: 50 }) });
  $("#q-cuerpo").innerHTML = `<div class="card"><p class="sub">Importe total ${num(r.importe_total)} · las diferencias dentro de tolerancia se muestran y cuantifican; ninguna diferencia se oculta.</p>${tablaDifQ(r.items)}
    ${paginador(r.total, r.pagina, r.por_pagina, (p) => { vq.difs.pagina = p; navegar(); })}</div>`;
  $$("[data-dif]").forEach((tr) => tr.addEventListener("click", () => panelDifQ(Number(tr.dataset.dif))));
}

async function panelDifQ(id) {
  const h = await api(`/conciliaciones/diferencias/${id}`, { params: pQ() });
  const d = h.diferencia;
  const m = abrirModal(`Incidencia ${d.codigo}`, `<p>${prioQ(d.prioridad)} ${chipQ(EST_DIF, d.estado)} <b>${esc(d.clasificacion)}</b> · ${esc(d.subtipo || "")}</p>
    <p>${esc(d.explicacion || "")}</p><p class="sub">${esc(d.recomendacion || "")}</p>
    <table class="tabla">${[["Importe", num(d.importe)], ["Pendiente", num(d.importe_pendiente)], ["Original", num(d.importe_original)], ["Documento", esc(d.documento || "")], ["Tercero", esc(d.tercero || "")],
      ["Cuenta", esc(d.cuenta || "")], ["Regla", esc(d.regla || "")], ["Detectada", `${fecha(d.fecha_deteccion)} · periodo origen ${d.periodo_origen ?? "—"} · ${d.antiguedad_dias} días · ${d.recurrencias} recurrencia(s)`],
      ["Evidencia (registros)", esc((d.evidencia.registros || []).join(", "))]].map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join("")}</table>
    <form id="fdq" class="form-grid form-q"><label>Responsable <input name="responsable" value="${esc(d.responsable || "")}"></label><label>Fecha límite <input type="date" name="fecha_limite" value="${d.fecha_limite || ""}"></label>
      <label style="grid-column:1/-1">Causa <textarea name="causa" rows="2">${esc(d.causa || "")}</textarea></label>
      <label style="grid-column:1/-1">Acción correctiva (se prepara para el módulo de asientos de regularización; no se generan asientos aquí) <textarea name="accion_correctiva" rows="2">${esc(d.accion_correctiva || "")}</textarea></label>
      <label>Nuevo estado <select name="estado"><option value="">(sin cambio)</option>${(SIG_DIF[d.estado] || []).map((s) => `<option value="${s}">${EST_DIF[s][0]}</option>`).join("")}</select></label>
      <label>Comentario <input name="comentario"></label>
      <div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Guardar</button></div></form>
    <form id="fa" class="filtros"><input type="file" name="archivo" required><input name="descripcion" placeholder="descripción del sustento"><button class="btn btn-sm">Adjuntar</button></form>
    <h3>Documentos</h3>${h.adjuntos.map((a) => `<div><a href="#" data-adj="${a.id}">${esc(a.nombre)}</a> <small class="sub">${esc(a.usuario)} · ${fechaHora(a.creado_en)}</small></div>`).join("") || '<p class="sub">Sin documentos</p>'}
    <h3>Historial</h3><table class="tabla"><tbody>${h.revisiones.map((r) => `<tr><td><small>${fechaHora(r.creado_en)}</small></td><td>${esc(r.usuario)}</td><td>${esc(r.de_estado || "")} → ${esc(r.a_estado || "")}</td><td><small>${esc(r.comentario || "")}</small></td></tr>`).join("") || '<tr><td class="vacio">Sin cambios</td></tr>'}</tbody></table>
    ${h.cadena.length > 1 ? `<h3>Continuidad</h3>${h.cadena.map((x) => `<div><small>${esc(x.codigo)} · ${esc(x.conciliacion)} · corte ${fecha(x.fecha_corte)} · ${num(x.importe)} · ${esc(x.estado)}</small></div>`).join("")}` : ""}`);
  m.querySelector("#fdq").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = datosForm(ev.target);
    const body = { responsable: f.responsable || null, fecha_limite: f.fecha_limite || null, causa: f.causa || null, accion_correctiva: f.accion_correctiva || null,
      comentario: f.comentario || null, lock_version: d.lock_version };
    if (f.estado) body.estado = f.estado;
    try { await api(`/conciliaciones/diferencias/${id}`, { method: "PATCH", params: pQ(), body }); toast("Incidencia actualizada", "ok"); cerrarModal(); navegar(); } catch (e) { toast(e.message, "err"); }
  });
  m.querySelector("#fa").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = new FormData(); f.append("archivo", ev.target.archivo.files[0]); f.append("diferencia_id", id); f.append("descripcion", ev.target.descripcion.value);
    try { await api("/conciliaciones/adjuntos", { method: "POST", params: pQ(), form: f }); toast("Documento adjuntado", "ok"); panelDifQ(id); } catch (e) { toast(e.message, "err"); }
  });
  $$("[data-adj]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); bajar(`/conciliaciones/adjuntos/${a.dataset.adj}`, pQ(), "documento").catch((x) => toast(x.message, "err")); }));
}

async function pestHistQ(c) {
  const h = await api(`/conciliaciones/${c.id}/historial`, { params: pQ() }).catch(() => ({ revisiones: [], aprobaciones: [], reversiones: [], auditoria: [] }));
  $("#q-cuerpo").innerHTML = `<div class="grid grid-2">
    <div class="card"><h2>Versiones</h2><table class="tabla"><thead><tr><th>Versión</th><th>Generada</th><th>Por</th><th>Estado</th><th></th></tr></thead><tbody>
      ${c.versiones.map((v) => `<tr><td>${v.numero}</td><td>${fechaHora(v.generado_en)}</td><td>${esc(v.generado_por)}</td><td>${v.inmutable ? `<span class="badge b-ok">Inmutable${v.estado_al_cerrar ? ` · ${esc(v.estado_al_cerrar)}` : ""}</span>` : "Editable"}</td>
        <td><button class="btn btn-sm" data-vx="${v.id}">Excel</button></td></tr>`).join("")}</tbody></table>
      <h3>Estado a una fecha</h3><div class="filtros"><input type="date" id="h-fecha"><button class="btn btn-sm" id="h-ver">Reconstruir</button></div><div id="h-res"></div></div>
    <div class="card"><h2>Elaboración, revisión y aprobación</h2><table class="tabla"><tbody>
      <tr><th>Elaboró</th><td>${esc(c.ejecutado_por || c.creado_por)}</td></tr><tr><th>Revisó</th><td>${esc(c.revisado_por || "—")} ${c.revisado_en ? fechaHora(c.revisado_en) : ""}</td></tr>
      <tr><th>Aprobó</th><td>${esc(c.aprobado_por || "—")} ${c.aprobado_en ? fechaHora(c.aprobado_en) : ""}</td></tr></tbody></table>
      <table class="tabla"><thead><tr><th>Fecha</th><th>Acción</th><th>Usuario</th><th>Comentario</th></tr></thead><tbody>${h.aprobaciones.map((a) => `<tr><td><small>${fechaHora(a.creado_en)}</small></td><td>${esc(a.accion)}</td><td>${esc(a.usuario)}</td><td><small>${esc(a.comentario || "")}</small></td></tr>`).join("")}
      ${h.reversiones.map((r) => `<tr><td><small>${fechaHora(r.creado_en)}</small></td><td>REVERSIÓN ${esc(r.alcance)}</td><td>${esc(r.usuario)}</td><td><small>${esc(r.motivo)}</small></td></tr>`).join("")}</tbody></table></div>
    <div class="card" style="grid-column:1/-1"><h2>Auditoría</h2><div class="tabla-scroll" style="max-height:360px"><table class="tabla"><thead><tr><th>Fecha</th><th>Usuario</th><th>Rol</th><th>Acción</th><th>Entidad</th><th>Versión</th><th>Detalle</th></tr></thead>
      <tbody>${h.auditoria.map((a) => `<tr><td><small>${fechaHora(a.fecha)}</small></td><td>${esc(a.usuario)}</td><td>${esc(a.rol || "")}</td><td>${esc(a.accion)}</td><td>${esc(a.entidad)} ${a.entidad_id ?? ""}</td><td>${a.version ?? ""}</td><td><small>${esc((a.detalle || "").slice(0, 160))}</small></td></tr>`).join("") || '<tr><td colspan="7" class="vacio">Sin acceso o sin registros</td></tr>'}</tbody></table></div></div></div>`;
  $$("[data-vx]").forEach((b) => b.addEventListener("click", () => bajar(`/conciliaciones/${c.id}/exportar`, pQ({ version_id: b.dataset.vx }), "conciliacion.xlsx").catch((e) => toast(e.message, "err"))));
  $("#h-ver").addEventListener("click", async () => {
    const f = $("#h-fecha").value; if (!f) return;
    try {
      const r = await api(`/conciliaciones/${c.id}/a-fecha`, { params: pQ({ fecha: f }) });
      $("#h-res").innerHTML = !r.existia ? `<p class="sub">${esc(r.nota)}</p>` : `<p>Al ${fecha(r.fecha)}: versión ${r.version.numero}, estado ${chipQ(EST_Q, r.estado)} · ${Object.entries(r.estados).map(([k, n]) => `${esc(k)}: ${n}`).join(" · ")}</p>${tablaDifQ(r.diferencias, false)}`;
    } catch (e) { toast(e.message, "err"); }
  });
}

// ------------------------------------------------------------------ explorador de diferencias y centro de incidencias
const fdq = { clasificacion: "", prioridad: "", estado: "", tipo_conciliacion: "", responsable: "", buscar: "", abiertas: false, trasladadas: false, dentro_tolerancia: "", orden: "", pagina: 1 };
async function listaDifQ(titulo, sub, fijos = {}) {
  if (!(await inicioQ())) return;
  Object.assign(fdq, parametrosHash());
  const r = await vigente(api("/conciliaciones/diferencias", { params: pQ({ ...fdq, ...fijos, por_pagina: 50 }) }));
  const sel = (k, opts) => `<select data-f="${k}"><option value="">Todos</option>${opts.map((o) => `<option ${fdq[k] === o ? "selected" : ""}>${o}</option>`).join("")}</select>`;
  vista().innerHTML = `<div class="cab-vista"><div><h1>${titulo}</h1><p class="sub">${sub}</p></div></div>
    <div class="card"><div class="filtros"><label>Clasificación ${sel("clasificacion", cq.cat.clasificaciones)}</label><label>Prioridad ${sel("prioridad", cq.cat.prioridades)}</label>
      <label>Estado ${sel("estado", cq.cat.estados_diferencia)}</label><label>Tipo ${sel("tipo_conciliacion", cq.cat.tipos.map((t) => t.codigo))}</label>
      <label>Responsable <input data-f="responsable" value="${esc(fdq.responsable)}"></label><label>Buscar <input data-f="buscar" value="${esc(fdq.buscar)}"></label>
      <label>Orden <select data-f="orden"><option value="">Código</option><option value="importe" ${fdq.orden === "importe" ? "selected" : ""}>Importe</option><option value="antiguedad" ${fdq.orden === "antiguedad" ? "selected" : ""}>Antigüedad</option></select></label>
      <label><input type="checkbox" data-c="trasladadas" ${fdq.trasladadas ? "checked" : ""}> Trasladadas</label></div>
      <p class="sub">${r.total} diferencias · importe ${num(r.importe_total)}</p>${tablaDifQ(r.items)}${paginador(r.total, r.pagina, r.por_pagina, (p) => { fdq.pagina = p; location.hash = location.hash.split("?")[0]; navegar(); })}</div>`;
  $$("[data-f]").forEach((i) => i.addEventListener("change", () => { fdq[i.dataset.f] = i.value; fdq.pagina = 1; location.hash = location.hash.split("?")[0]; navegar(); }));
  $$("[data-c]").forEach((i) => i.addEventListener("change", () => { fdq[i.dataset.c] = i.checked; fdq.pagina = 1; navegar(); }));
  $$("[data-dif]").forEach((tr) => tr.addEventListener("click", () => panelDifQ(Number(tr.dataset.dif))));
}
rutas["conc-diferencias"] = () => listaDifQ("Explorador de diferencias", "Todas las diferencias de las versiones vigentes, con su evidencia, regla, explicación y recomendación.");
rutas["conc-incidencias"] = () => listaDifQ("Centro de incidencias", "Diferencias abiertas: asigne responsables, plazos, causas y acciones correctivas; marque subsanadas o reabra. Se preparan para auditoría y asientos de regularización (fases posteriores).", { abiertas: true });

// ------------------------------------------------------------------ panel de aprobación
rutas["conc-aprobacion"] = async () => {
  if (!(await inicioQ())) return;
  const [rev, revs] = await vigente(Promise.all(["EN_REVISION", "REVISADA"].map((e) => api("/conciliaciones", { params: pQ({ estado: e, por_pagina: 100 }) }))));
  const fila = (c) => `<tr><td><a href="#/conc-ver?id=${c.id}">${esc(c.nombre)}</a></td><td>${fecha(c.fecha_corte)}</td><td>${chipQ(EST_Q, c.estado)}</td><td>${esc(c.ejecutado_por || c.creado_por)}</td>
    <td class="num">${c.resumen?.diferencias ?? "—"}</td><td>${esc(c.revisado_por || "")}</td></tr>`;
  vista().innerHTML = `<div class="cab-vista"><div><h1>Panel de aprobación</h1><p class="sub">Separación de funciones: quien elabora no revisa ni aprueba; quien revisa no aprueba. Una versión aprobada es inmutable.</p></div></div>
    <div class="card"><h2>Pendientes de revisión</h2><table class="tabla"><thead><tr><th>Conciliación</th><th>Corte</th><th>Estado</th><th>Elaboró</th><th class="num">Diferencias</th><th>Revisó</th></tr></thead><tbody>${rev.items.map(fila).join("") || '<tr><td colspan="6" class="vacio">—</td></tr>'}</tbody></table></div>
    <div class="card"><h2>Pendientes de aprobación</h2><table class="tabla"><thead><tr><th>Conciliación</th><th>Corte</th><th>Estado</th><th>Elaboró</th><th class="num">Diferencias</th><th>Revisó</th></tr></thead><tbody>${revs.items.map(fila).join("") || '<tr><td colspan="6" class="vacio">—</td></tr>'}</tbody></table></div>`;
};

// ------------------------------------------------------------------ diseñador de reglas (asistente de 10 pasos)
const dzq = { paso: 0, def: null, nombre: "", run_id: "", prueba: null };
rutas["conc-disenador"] = async () => {
  if (!(await inicioQ())) return;
  if (!dzq.def) dzq.def = { fuentes: { A: { tipo: "LIBRO", rol: "CONTABLE", nombre: "Libro", parametros: { cuentas: [] } }, B: { tipo: "ARCHIVO", rol: "EXTERNA", nombre: "Fuente externa", esquema: "CONC_GENERICO", parametros: {} } },
    pasadas: [{ a: "A", b: "B", modo: "PARTIDAS", signo: "IGUAL" }], tolerancia: { importe_absoluto: "0", porcentaje: null, dias: 3 }, confirmar_automaticamente: ["EXACTA"], duplicados: {},
    reglas: [{ codigo: "DOCUMENTO", descripcion: "Documento", tipo: "CLAVE", parametros: { campos: ["serie", "numero"] } }, { codigo: "IMPORTE_FECHA", descripcion: "Importe y fecha", tipo: "IMPORTE_FECHA", parametros: {} }] };
  const P = cq.cat.pasos_disenador;
  const d = dzq.def;
  const campos = ["fecha", "periodo", "tipo_documento", "serie", "numero", "tercero", "referencia", "operacion", "descripcion", "cuenta", "centro_costo", "proyecto", "concepto", "moneda", "importe", "importe_me", "cantidad"];
  const cuerpo = [
    () => `<p class="sub">Defina de 2 a 4 fuentes. Las internas se arman desde el libro, registros y auxiliares; las externas se importan como archivo.</p>
      ${Object.entries(d.fuentes).map(([l, f]) => `<div class="form-grid form-q"><b>${l}</b><label>Tipo <select data-ft="${l}">${cq.cat.tipos_fuente.map((t) => `<option ${f.tipo === t ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <label>Rol <select data-fr="${l}">${["CONTABLE", "EXTERNA", "AUXILIAR_INTERNO"].map((r) => `<option ${f.rol === r ? "selected" : ""}>${r}</option>`).join("")}</select></label>
        <label>Nombre <input data-fn="${l}" value="${esc(f.nombre)}"></label><label>Cuentas (si aplica) <input data-fc="${l}" value="${esc((f.parametros.cuentas || []).join(","))}"></label></div>`).join("")}
      <button class="btn btn-sm" id="dzq-masf">Agregar fuente</button>`,
    () => `<p class="sub">Las fuentes de tipo archivo usan la homologación de columnas de la fase 2 (sinónimos, encabezados, subtotales).</p>${Object.entries(d.fuentes).filter(([, f]) => f.tipo === "ARCHIVO").map(([l, f]) => `<label>${l} · diseño <select data-fe="${l}">${["CONC_GENERICO", "CONC_PLANILLA", "CONC_KARDEX", "CONC_COSTOS", "CONC_CONSTANCIAS", "CONC_RETENCIONES", "CONC_DECLARACIONES", "CONC_SALDOS"].map((e) => `<option ${f.esquema === e ? "selected" : ""}>${e}</option>`).join("")}</select></label>`).join("") || "Sin fuentes de archivo."}`,
    () => `<p class="sub">Campos de cruce de la primera regla de clave (identificadores únicos).</p>${campos.map((c) => `<label><input type="checkbox" data-cc="${c}" ${(d.reglas.find((r) => r.tipo === "CLAVE")?.parametros.campos || []).includes(c) ? "checked" : ""}> ${c}</label>`).join(" ")}`,
    () => `<p class="sub">Comparaciones monetarias adicionales (campo A, campo B, nombre, subtipo), una por línea.</p><textarea id="dzq-cmp" rows="4" style="width:100%">${esc((d.reglas.find((r) => r.tipo === "CLAVE")?.parametros.comparar || []).map((x) => x.join(";")).join("\n"))}</textarea>`,
    () => `<div class="form-grid form-q"><label>Tolerancia absoluta <input id="dzq-ta" value="${esc(d.tolerancia.importe_absoluto)}"></label><label>Porcentaje <input id="dzq-tp" value="${d.tolerancia.porcentaje ?? ""}"></label><label>Días <input id="dzq-td" type="number" value="${d.tolerancia.dias}"></label></div>
      <p class="sub">Confirmar automáticamente: ${["EXACTA", "TOLERANCIA"].map((t) => `<label><input type="checkbox" data-auto="${t}" ${d.confirmar_automaticamente.includes(t) ? "checked" : ""}> ${t}</label>`).join(" ")} — las ambiguas nunca se confirman solas.</p>`,
    () => `<p class="sub">Reglas en orden de prioridad. Tipos: CLAVE, IMPORTE_FECHA, COMBINACION, AGREGADO, EXCLUSION (expresión segura), CLASIFICACION. Edite como JSON declarativo (no se admite SQL ni código).</p><textarea id="dzq-reglas" rows="12" style="width:100%;font-family:monospace">${esc(JSON.stringify(d.reglas, null, 2))}</textarea>`,
    () => `<p class="sub">Agrupación de las comparaciones (p. ej. por tercero o cuenta) y modo PARTIDAS o AGREGADO.</p>${d.pasadas.map((p, i) => `<div class="form-grid form-q"><b>${p.a} ↔ ${p.b}</b><label>Modo <select data-pm="${i}">${["PARTIDAS", "AGREGADO"].map((m) => `<option ${p.modo === m ? "selected" : ""}>${m}</option>`).join("")}</select></label>
      <label>Signo <select data-ps="${i}">${["IGUAL", "OPUESTO"].map((m) => `<option ${p.signo === m ? "selected" : ""}>${m}</option>`).join("")}</select></label><label>Agrupar por <input data-pg="${i}" value="${esc((p.agrupar_por || []).join(","))}"></label></div>`).join("")}`,
    () => `<p class="sub">Prueba en memoria sobre las fuentes ya cargadas de una conciliación (no guarda nada).</p><label>Id de conciliación <input id="dzq-run" value="${esc(dzq.run_id)}"></label><button class="btn btn-sm" id="dzq-probar">Probar</button>
      <pre class="pre">${dzq.prueba ? esc(JSON.stringify(dzq.prueba, null, 2)) : ""}</pre>`,
    () => `<pre class="pre">${esc(JSON.stringify(d, null, 2))}</pre><button class="btn btn-sm" id="dzq-validar">Validar</button>`,
    () => `<label>Nombre de la plantilla <input id="dzq-nombre" value="${esc(dzq.nombre)}"></label><p class="sub">La plantilla queda pendiente de autorización por un supervisor o administrador distinto de quien la diseña.</p>
      <button class="btn btn-primario" id="dzq-guardar">Guardar plantilla</button>
      <h3>Plantillas personalizadas</h3><table class="tabla"><tbody>${cq.cat.plantillas.filter((p) => p.personalizada).map((p) => `<tr><td>${esc(p.nombre)}</td><td>v${p.version}</td><td>${p.autorizada ? `<span class="badge b-ok">Autorizada por ${esc(p.autorizada_por)}</span>` : '<span class="badge b-warn">Pendiente</span>'}</td>
        <td>${!p.autorizada && puedeQ("configurar") ? `<button class="btn btn-sm" data-aut="${p.id}">Autorizar</button>` : ""}</td></tr>`).join("") || '<tr><td class="vacio">—</td></tr>'}</tbody></table>`];
  vista().innerHTML = `<div class="cab-vista"><div><h1>Diseñador de conciliaciones</h1><p class="sub">Defina fuentes, homologación, cruces, tolerancias y reglas sin programar.</p></div></div>
    <div class="pasos">${P.map((t, i) => `<button class="btn btn-sm ${i === dzq.paso ? "btn-primario" : ""}" data-paso="${i}">${i + 1}. ${t}</button>`).join(" ")}</div>
    <div class="card" id="dzq-cuerpo">${cuerpo[dzq.paso]()}</div>
    <div class="acciones"><button class="btn" id="dzq-ant" ${dzq.paso === 0 ? "disabled" : ""}>Anterior</button><button class="btn btn-primario" id="dzq-sig" ${dzq.paso === P.length - 1 ? "disabled" : ""}>Siguiente</button></div>`;
  const leer = () => {
    $$("[data-ft]").forEach((s) => { d.fuentes[s.dataset.ft].tipo = s.value; });
    $$("[data-fr]").forEach((s) => { d.fuentes[s.dataset.fr].rol = s.value; });
    $$("[data-fn]").forEach((s) => { d.fuentes[s.dataset.fn].nombre = s.value; });
    $$("[data-fc]").forEach((s) => { d.fuentes[s.dataset.fc].parametros.cuentas = s.value.split(",").map((x) => x.trim()).filter(Boolean); });
    $$("[data-fe]").forEach((s) => { d.fuentes[s.dataset.fe].esquema = s.value; });
    const clave = d.reglas.find((r) => r.tipo === "CLAVE");
    if ($$("[data-cc]").length && clave) clave.parametros.campos = $$("[data-cc]").filter((x) => x.checked).map((x) => x.dataset.cc);
    if ($("#dzq-cmp") && clave) clave.parametros.comparar = $("#dzq-cmp").value.split("\n").map((l) => l.split(";").map((x) => x.trim())).filter((x) => x.length === 4);
    if ($("#dzq-ta")) d.tolerancia = { importe_absoluto: $("#dzq-ta").value || "0", porcentaje: $("#dzq-tp").value || null, dias: Number($("#dzq-td").value || 0) };
    if ($$("[data-auto]").length) d.confirmar_automaticamente = $$("[data-auto]").filter((x) => x.checked).map((x) => x.dataset.auto);
    if ($("#dzq-reglas")) { try { d.reglas = JSON.parse($("#dzq-reglas").value); } catch { toast("Reglas: JSON no válido", "err"); } }
    $$("[data-pm]").forEach((s) => { d.pasadas[s.dataset.pm].modo = s.value; });
    $$("[data-ps]").forEach((s) => { d.pasadas[s.dataset.ps].signo = s.value; });
    $$("[data-pg]").forEach((s) => { const v = s.value.split(",").map((x) => x.trim()).filter(Boolean); if (v.length) d.pasadas[s.dataset.pg].agrupar_por = v; else delete d.pasadas[s.dataset.pg].agrupar_por; });
    if ($("#dzq-run")) dzq.run_id = $("#dzq-run").value;
    if ($("#dzq-nombre")) dzq.nombre = $("#dzq-nombre").value;
  };
  $$("[data-paso]").forEach((b) => b.addEventListener("click", () => { leer(); dzq.paso = Number(b.dataset.paso); navegar(); }));
  $("#dzq-ant").addEventListener("click", () => { leer(); dzq.paso--; navegar(); });
  $("#dzq-sig").addEventListener("click", () => { leer(); dzq.paso++; navegar(); });
  $("#dzq-masf")?.addEventListener("click", () => { leer(); const l = "ABCD"[Object.keys(d.fuentes).length]; if (!l) return; d.fuentes[l] = { tipo: "ARCHIVO", rol: "EXTERNA", nombre: `Fuente ${l}`, esquema: "CONC_GENERICO", parametros: {} }; navegar(); });
  $("#dzq-probar")?.addEventListener("click", async () => { leer(); try { dzq.prueba = await api("/conciliaciones/plantillas/probar", { method: "POST", params: pQ(), body: { run_id: Number(dzq.run_id), configuracion: d } }); navegar(); } catch (e) { toast(e.message, "err"); } });
  $("#dzq-validar")?.addEventListener("click", async () => { try { await api("/conciliaciones/plantillas/validar", { method: "POST", params: pQ(), body: { configuracion: d } }); toast("Definición válida", "ok"); } catch (e) { toast(e.message, "err"); } });
  $("#dzq-guardar")?.addEventListener("click", async () => {
    leer();
    try { await api("/conciliaciones/plantillas", { method: "POST", params: pQ(), body: { nombre: dzq.nombre, configuracion: d } }); toast("Plantilla guardada (pendiente de autorización)", "ok"); dzq.def = null; dzq.paso = 0; navegar(); }
    catch (e) { toast(e.message, "err"); }
  });
  $$("[data-aut]").forEach((b) => b.addEventListener("click", async () => { try { await api(`/conciliaciones/plantillas/${b.dataset.aut}/autorizar`, { method: "POST", params: pQ() }); toast("Plantilla autorizada", "ok"); navegar(); } catch (e) { toast(e.message, "err"); } }));
};

// ------------------------------------------------------------------ historial (auditoría global)
rutas["conc-historial"] = async () => {
  if (!(await inicioQ())) return;
  const a = await vigente(api("/conciliaciones/auditoria", { params: pQ({ por_pagina: 200 }) }).catch((e) => ({ items: [], error: e.message })));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Historial de conciliaciones</h1><p class="sub">Usuario, fecha, fuente, regla, versión, resultado, cambios manuales, aprobaciones y reversiones.</p></div></div>
    ${a.error ? `<div class="alerta alerta-warn">${esc(a.error)}</div>` : ""}
    <div class="card"><table class="tabla"><thead><tr><th>Fecha</th><th>Usuario</th><th>Rol</th><th>Acción</th><th>Entidad</th><th>Conciliación</th><th>Versión</th><th>Detalle</th></tr></thead>
    <tbody>${a.items.map((x) => `<tr><td><small>${fechaHora(x.fecha)}</small></td><td>${esc(x.usuario)}</td><td>${esc(x.rol || "")}</td><td>${esc(x.accion)}</td><td>${esc(x.entidad)} ${x.entidad_id ?? ""}</td>
      <td>${x.run_id ? `<a href="#/conc-ver?id=${x.run_id}">#${x.run_id}</a>` : ""}</td><td>${x.version ?? ""}</td><td><small>${esc((x.detalle || "").slice(0, 200))}</small></td></tr>`).join("") || '<tr><td colspan="8" class="vacio">—</td></tr>'}</tbody></table></div>`;
};

// ------------------------------------------------------------------ centro de exportación
rutas["conc-export"] = async () => {
  if (!(await inicioQ())) return;
  vista().innerHTML = `<div class="cab-vista"><div><h1>Centro de exportación</h1><p class="sub">Reportes en Excel (con fórmulas) y PDF. Los reportes especializados (bancario, compras, ventas, planillas, inventarios, activos, financieras, detracciones, retenciones, origen-destino) se exportan desde cada conciliación.</p></div></div>
    ${barraQ()}
    <div class="card"><table class="tabla"><thead><tr><th>Reporte</th><th>Tipo de conciliación</th><th></th></tr></thead><tbody>
      ${Object.entries(cq.cat.reportes).map(([k, t]) => `<tr><td>${esc(t)}</td><td><select data-tq="${k}"><option value="">Todos</option>${cq.cat.tipos.map((x) => `<option value="${x.codigo}">${esc(x.nombre)}</option>`).join("")}</select></td>
        <td><button class="btn btn-sm" data-rep="${k}" data-fmt="xlsx">Excel</button> <button class="btn btn-sm" data-rep="${k}" data-fmt="pdf">PDF</button></td></tr>`).join("")}</tbody></table></div>`;
  enlazarQ();
  $$("[data-rep]").forEach((b) => b.addEventListener("click", () => bajar(`/conciliaciones/reportes/${b.dataset.rep}`, pQ({ formato: b.dataset.fmt, ejercicio: cq.ejercicio, periodo: cq.periodo, tipo_codigo: $(`[data-tq="${b.dataset.rep}"]`).value }), `reporte.${b.dataset.fmt}`).catch((e) => toast(e.message, "err"))));
};

// ------------------------------------------------------------------ configuración: tolerancias, responsables, grupo económico y tasas
rutas["conc-config"] = async () => {
  if (!(await inicioQ())) return;
  const [tol, asig, reglas] = await vigente(Promise.all([api("/conciliaciones/tolerancias", { params: pQ() }), api("/conciliaciones/asignaciones", { params: pQ() }),
    api("/compensacion/reglas", { params: pQ() }).catch(() => [])]));
  const tasas = reglas.filter((r) => ["DETRACCION", "RETENCION", "PERCEPCION"].includes(r.tipo));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Tolerancias, responsables y tasas</h1><p class="sub">Gana la tolerancia más específica (tipo, cuenta, moneda). Las tasas tributarias requieren vigencia, fuente normativa y aprobación del responsable tributario.</p></div></div>
    <div class="grid grid-2">
      <div class="card"><h2>Tolerancias</h2><table class="tabla"><thead><tr><th>Tipo</th><th>Cuenta</th><th>Moneda</th><th class="num">Absoluta</th><th class="num">%</th><th class="num">Días</th><th></th></tr></thead>
        <tbody>${tol.map((t) => `<tr><td>${esc(t.tipo_codigo || "Todos")}</td><td>${esc(t.cuenta || "")}</td><td>${esc(t.moneda || "")}</td><td class="num">${num(t.importe_absoluto)}</td><td class="num">${t.porcentaje ?? ""}</td><td class="num">${t.dias}</td>
          <td><button class="btn btn-sm" data-dtol="${t.id}">Desactivar</button></td></tr>`).join("") || '<tr><td colspan="7" class="vacio">Se usan las de cada plantilla</td></tr>'}</tbody></table>
        <form id="ft" class="form-grid form-q"><label>Tipo <select name="tipo_codigo"><option value="">Todos</option>${cq.cat.tipos.map((x) => `<option value="${x.codigo}">${esc(x.nombre)}</option>`).join("")}</select></label>
          <label>Cuenta <input name="cuenta"></label><label>Moneda <input name="moneda" maxlength="3"></label><label>Absoluta <input name="importe_absoluto" value="0"></label><label>% <input name="porcentaje"></label><label>Días <input name="dias" type="number" value="0"></label>
          <div class="acciones"><button class="btn btn-primario">Agregar</button></div></form></div>
      <div class="card"><h2>Responsables, programación y grupo económico</h2><table class="tabla"><thead><tr><th>Tipo</th><th>Conciliación</th><th>Usuario / empresa</th><th>Día</th><th></th></tr></thead>
        <tbody>${asig.map((a) => `<tr><td>${esc(a.tipo)}</td><td>${esc(a.tipo_conciliacion || "")}</td><td>${esc(a.usuario || estado.empresas.find((e) => e.id === a.empresa_relacionada_id)?.razon_social || "")}</td><td>${a.dia_programado ?? ""}</td>
          <td><button class="btn btn-sm" data-dasig="${a.id}">Desactivar</button></td></tr>`).join("") || '<tr><td colspan="5" class="vacio">—</td></tr>'}</tbody></table>
        <form id="fa2" class="form-grid form-q"><label>Tipo <select name="tipo">${["ELABORACION", "REVISION", "APROBACION", "PROGRAMADA", "GRUPO_ECONOMICO"].map((t) => `<option>${t}</option>`).join("")}</select></label>
          <label>Conciliación <select name="tipo_conciliacion"><option value="">—</option>${cq.cat.tipos.map((x) => `<option value="${x.codigo}">${esc(x.nombre)}</option>`).join("")}</select></label>
          <label>Usuario <input name="usuario"></label><label>Empresa relacionada <select name="empresa_relacionada_id"><option value="">—</option>${estado.empresas.filter((e) => e.id !== estado.empresaId).map((e) => `<option value="${e.id}">${esc(e.razon_social)}</option>`).join("")}</select></label>
          <label>Día programado <input name="dia_programado" type="number" min="1" max="31"></label><div class="acciones"><button class="btn btn-primario">Agregar</button></div></form></div>
      <div class="card" style="grid-column:1/-1"><h2>Tasas de detracción, retención y percepción</h2><p class="sub">Se configuran en <a href="#/comp-config">Reglas y roles</a> (fase 4) y se aprueban aquí. Sin aprobación no se calcula el importe esperado (no se usan tasas fijas).</p>
        <table class="tabla"><thead><tr><th>Tipo</th><th>Código</th><th class="num">Tasa</th><th>Vigencia</th><th>Fuente normativa</th><th>Aprobada por</th><th></th></tr></thead>
        <tbody>${tasas.map((r) => `<tr><td>${esc(r.tipo)}</td><td>${esc(r.codigo)}</td><td class="num">${esc(r.parametros.tasa ?? "")}</td><td>${fecha(r.vigente_desde)} – ${r.vigente_hasta ? fecha(r.vigente_hasta) : "…"}</td>
          <td><small>${esc(r.sustento || "")}</small></td><td>${esc(r.autorizado_por || "—")}</td><td>${!r.autorizado_por && puedeQ("configurar") ? `<button class="btn btn-sm" data-tasa="${r.id}">Aprobar</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="7" class="vacio">Sin tasas configuradas</td></tr>'}</tbody></table></div>
    </div>`;
  $("#ft").addEventListener("submit", async (ev) => { ev.preventDefault(); const d = datosForm(ev.target);
    try { await api("/conciliaciones/tolerancias", { method: "POST", params: pQ(), body: { ...d, tipo_codigo: d.tipo_codigo || null, cuenta: d.cuenta || null, moneda: d.moneda || null, porcentaje: d.porcentaje || null, dias: Number(d.dias || 0) } }); navegar(); } catch (e) { toast(e.message, "err"); } });
  $("#fa2").addEventListener("submit", async (ev) => { ev.preventDefault(); const d = datosForm(ev.target);
    try { await api("/conciliaciones/asignaciones", { method: "POST", params: pQ(), body: { tipo: d.tipo, tipo_conciliacion: d.tipo_conciliacion || null, usuario: d.usuario || null,
      empresa_relacionada_id: d.empresa_relacionada_id ? Number(d.empresa_relacionada_id) : null, dia_programado: d.dia_programado ? Number(d.dia_programado) : null } }); navegar(); } catch (e) { toast(e.message, "err"); } });
  $$("[data-dtol]").forEach((b) => b.addEventListener("click", () => api(`/conciliaciones/tolerancias/${b.dataset.dtol}`, { method: "DELETE", params: pQ() }).then(navegar).catch((e) => toast(e.message, "err"))));
  $$("[data-dasig]").forEach((b) => b.addEventListener("click", () => api(`/conciliaciones/asignaciones/${b.dataset.dasig}`, { method: "DELETE", params: pQ() }).then(navegar).catch((e) => toast(e.message, "err"))));
  $$("[data-tasa]").forEach((b) => b.addEventListener("click", () => api(`/conciliaciones/tasas/${b.dataset.tasa}/aprobar`, { method: "POST", params: pQ(), body: {} }).then(() => { toast("Tasa aprobada", "ok"); navegar(); }).catch((e) => toast(e.message, "err"))));
};
