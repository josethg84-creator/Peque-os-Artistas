/* Fase 7 — Auditor contable inteligente 360: dashboard ejecutivo, centro de ejecución, biblioteca de reglas, diseñador de
   controles, explorador de hallazgos (evidencias, acciones correctivas, navegación al asiento original), matriz de riesgos
   interactiva, papeles de trabajo, generador de informes, historial y configuración (materialidad, ERP).
   Herramienta de apoyo: no emite dictámenes ni modifica asientos. Reutiliza app.js, app_contable.js, app_analisis.js
   (gráficos, verAsiento), app_compensacion.js (paginador) y app_anexos.js (bajar). */
"use strict";

const au = { cat: null, encargo: null, f: { pagina: 1 } };
const RIESGO_AU = { CRITICO: "#b42318", ALTO: "#dc3c3d", MEDIO: "#f18a59", BAJO: "#fbb315", INFORMATIVO: "#8a94a6" };
const EST_AU = { DETECTADO: "b-err", PENDIENTE_REVISION: "b-warn", EN_ANALISIS: "b-warn", CONFIRMADO: "b-err", JUSTIFICADO: "b-info",
  PENDIENTE_REGULARIZACION: "b-warn", EN_SUBSANACION: "b-info", SUBSANADO: "b-ok", VERIFICADO: "b-ok", CERRADO: "b-ok", REABIERTO: "b-err" };
const SIG_AU = { DETECTADO: ["PENDIENTE_REVISION", "EN_ANALISIS", "CONFIRMADO", "JUSTIFICADO", "FALSO_POSITIVO"],
  PENDIENTE_REVISION: ["EN_ANALISIS", "CONFIRMADO", "JUSTIFICADO", "FALSO_POSITIVO"], EN_ANALISIS: ["CONFIRMADO", "JUSTIFICADO", "FALSO_POSITIVO"],
  REABIERTO: ["PENDIENTE_REVISION", "EN_ANALISIS", "CONFIRMADO", "JUSTIFICADO", "FALSO_POSITIVO"], CONFIRMADO: ["PENDIENTE_REGULARIZACION", "EN_SUBSANACION", "SUBSANADO", "JUSTIFICADO"],
  PENDIENTE_REGULARIZACION: ["EN_SUBSANACION", "SUBSANADO"], EN_SUBSANACION: ["SUBSANADO"], SUBSANADO: ["VERIFICADO", "REABIERTO"],
  VERIFICADO: ["CERRADO", "REABIERTO"], JUSTIFICADO: ["CERRADO", "REABIERTO"], CERRADO: ["REABIERTO"] };
const riesgoAU = (r) => `<span class="badge riesgo" style="--c:${RIESGO_AU[r] || "#8a94a6"}">${esc(r || "—")}</span>`;
const estAU = (e, t) => `<span class="badge ${EST_AU[e] || ""}">${esc(e)}</span>${t && t !== "POTENCIAL" ? ` <small class="sub">${esc(t)}</small>` : ""}`;
const pAU = (x = {}) => ({ empresa_id: estado.empresaId, ...x });
const puedeAU = (a) => !!au.cat?.permisos?.[a];

async function inicioAU() {
  if (!requiereEmpresa()) return false;
  au.cat = await vigente(api("/auditoria360/catalogo", { params: pAU() }));
  const g = Number(almacen.leer(`au_enc_${estado.empresaId}`, "0")) || null;
  au.encargo = g;
  return true;
}
function avisoAU() { return `<div class="alerta alerta-warn" style="margin-bottom:10px">${esc(au.cat.aviso)}</div>`; }
async function selectorEncargoAU(extra = "") {
  const l = await api("/auditoria360/encargos", { params: pAU({ por_pagina: 100 }) });
  if (!au.encargo && l.items.length) au.encargo = l.items[0].id;
  setTimeout(() => $("#au-enc")?.addEventListener("change", (e) => { au.encargo = Number(e.target.value) || null; almacen.guardar(`au_enc_${estado.empresaId}`, String(au.encargo || "")); au.f.pagina = 1; navegar(); }));
  return `<div class="ctx-bar"><label>Encargo <select id="au-enc"><option value="">Todos</option>${l.items.map((e) => `<option value="${e.id}" ${e.id === au.encargo ? "selected" : ""}>${esc(e.codigo)} · ${esc(e.nombre)}</option>`).join("")}</select></label>
    <span class="sub">Rol: <b>${esc(au.cat.rol || "—")}</b></span>${extra}</div>`;
}
async function esperarAU(r, caja) {
  if (caja) caja.innerHTML = `<div class="card">${barraProgreso(0, "En cola")}<div class="acciones"><button class="btn btn-sm btn-peligro" data-cancel>Cancelar</button></div></div>`;
  caja?.querySelector("[data-cancel]")?.addEventListener("click", () => api(`/auditoria360/ejecuciones/${r.run_id}/cancelar`, { method: "POST", params: pAU() }).catch((e) => toast(e.message, "err")));
  await esperarTrabajo(r.trabajo, (t) => {
    const b = caja?.querySelector(".progreso"); if (!b) return;
    b.querySelector(".progreso-barra").style.width = `${Math.max(2, t.progreso)}%`;
    caja.querySelector(".progreso-txt").innerHTML = `<span>${esc(t.etapa)}</span><b>${t.progreso}%</b>`;
  });
  if (caja) caja.innerHTML = "";
}

// ------------------------------------------------------------------ dashboard ejecutivo
rutas["aud"] = async () => {
  if (!(await inicioAU())) return;
  const sel = await selectorEncargoAU();
  const d = await vigente(api("/auditoria360/tablero", { params: pAU({ engagement_id: au.encargo }) }));
  const k = d.kpi;
  const tile = (l, v, s = "", href = "") => `<div class="kpi"><div class="l">${l}</div><div class="v">${href ? `<a href="${href}">${v}</a>` : v}</div>${s ? `<div class="l">${s}</div>` : ""}</div>`;
  vista().innerHTML = `<div class="cab-vista"><div><h1>Auditor contable inteligente 360</h1><p class="sub">Integridad, consistencia, razonabilidad y trazabilidad de la información contable.</p></div>
    <div class="acciones" style="margin:0"><a class="btn btn-primario" href="#/aud-centro">Centro de ejecución</a><a class="btn" href="#/aud-hallazgos">Hallazgos</a></div></div>
    ${avisoAU()}${sel}
    <div class="grid grid-5">${tile("Cuentas auditadas", k.cuentas_auditadas.toLocaleString("es-PE"))}${tile("Movimientos evaluados", k.movimientos_evaluados.toLocaleString("es-PE"))}
      ${tile("Reglas ejecutadas", k.reglas_ejecutadas, `${k.reglas_no_ejecutadas} no ejecutadas (sin datos, sin validar o fuera de vigencia)`)}
      ${tile("Hallazgos", k.hallazgos, `${k.falsos_positivos} falsos positivos`, "#/aud-hallazgos")}${tile("Confirmados", k.confirmados)}
      ${tile("Críticos", `<span style="color:${RIESGO_AU.CRITICO}">${k.criticos}</span>`)}${tile("Riesgo alto", k.altos)}${tile("Pendientes", k.pendientes)}${tile("Subsanados", k.subsanados)}
      ${tile("Exposición potencial", num(k.exposicion_potencial), `bruta ${num(k.exposicion_bruta)}`)}${tile("Exposición confirmada", num(k.exposicion_confirmada))}
      ${tile("Acciones vencidas", k.acciones_vencidas, "", "#/aud-acciones")}${tile("Avance de revisión", k.avance_revision === null ? "—" : `${k.avance_revision} %`)}</div>
    <p class="sub">${esc(d.nota)}</p>
    <div class="grid grid-2" style="margin-top:12px">
      <div class="card"><h2>Hallazgos por módulo</h2>${graficoBarras(Object.entries(d.por_modulo).map(([m, n]) => ({ etiqueta: m, valor: n })), { etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Por nivel de riesgo</h2>${graficoBarras(Object.entries(d.por_riesgo).map(([m, n]) => ({ etiqueta: m, valor: n })), { colores: Object.keys(d.por_riesgo).map((r) => RIESGO_AU[r]), etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Por cuenta</h2>${graficoBarras(Object.entries(d.por_cuenta).map(([m, n]) => ({ etiqueta: m, valor: n })), { etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Por centro de costo</h2>${graficoBarras(Object.entries(d.por_centro_costo).map(([m, n]) => ({ etiqueta: m, valor: n })), { etiquetaValor: (v) => String(v), color: SERIES[2] })}</div>
      <div class="card"><h2>Exposición monetaria por módulo (sin superposición)</h2>${graficoBarras(Object.entries(d.exposicion_por_modulo).map(([m, n]) => ({ etiqueta: m, valor: Number(n) })), { color: "#dc3c3d" })}</div>
      <div class="card"><h2>Evolución mensual</h2>${graficoBarras(Object.entries(d.mensual).map(([m, n]) => ({ etiqueta: m, valor: n })), { etiquetaValor: (v) => String(v), color: SERIES[1] })}</div>
      <div class="card"><h2>Avance por responsable</h2><table class="tabla"><thead><tr><th>Responsable</th><th class="num">Asignados</th><th class="num">Cerrados</th><th class="num">Vencidos</th></tr></thead>
        <tbody>${Object.entries(d.por_responsable).map(([r, x]) => `<tr><td>${esc(r)}</td><td class="num">${x.asignados}</td><td class="num">${x.cerrados}</td><td class="num">${x.vencidos}</td></tr>`).join("") || '<tr><td colspan="4" class="vacio">—</td></tr>'}</tbody></table></div>
      <div class="card"><h2>Hallazgos recurrentes</h2>${tablaHAU(d.recurrentes, false)}</div></div>`;
};

function tablaHAU(items, clic = true) {
  if (!items.length) return '<div class="vacio">Sin hallazgos</div>';
  return `<div class="tabla-scroll"><table class="tabla"><thead><tr><th>Código</th><th>Riesgo</th><th>Módulo</th><th>Título</th><th>Cuenta</th><th>Documento</th><th class="num">Importe</th><th>Estado</th><th>Responsable</th></tr></thead>
    <tbody>${items.map((h) => `<tr class="${clic ? "clic" : ""}" data-h="${h.id}"><td><small>${esc(h.codigo)}</small>${h.reincidencias ? ' <span class="badge b-err" title="Reincidencia">↺</span>' : ""}${h.vigente === false ? ' <span class="badge" title="No se reproduce en la última ejecución">no reproducido</span>' : ""}</td>
      <td>${riesgoAU(h.riesgo)}</td><td><small>${esc(h.modulo)}</small></td><td>${esc(h.titulo)}</td><td>${esc(h.cuenta || "")}</td><td><small>${esc(h.documento || h.asiento || "")}</small></td>
      <td class="num">${num(h.importe)}</td><td>${estAU(h.estado, h.tipo)}</td><td><small>${esc(h.responsable || "")}</small></td></tr>`).join("")}</tbody></table></div>`;
}

// ------------------------------------------------------------------ centro de ejecución
rutas["aud-centro"] = async () => {
  if (!(await inicioAU())) return;
  const l = await vigente(api("/auditoria360/encargos", { params: pAU({ por_pagina: 50 }) }));
  const e = au.encargo ? await api(`/auditoria360/encargos/${au.encargo}`, { params: pAU() }).catch(() => null) : null;
  vista().innerHTML = `<div class="cab-vista"><div><h1>Centro de ejecución de auditorías</h1><p class="sub">Cree encargos, defina el alcance y ejecute la auditoría completa, por módulo, por cuenta o reglas individuales.</p></div>
    <div class="acciones" style="margin:0">${puedeAU("crear_encargo") ? '<button class="btn btn-primario" id="au-nuevo">Nuevo encargo</button>' : ""}</div></div>
    ${avisoAU()}
    <div class="grid grid-2"><div class="card"><h2>Encargos</h2><table class="tabla"><thead><tr><th>Código</th><th>Nombre</th><th>Tipo</th><th>Corte</th><th>Estado</th></tr></thead>
      <tbody>${l.items.map((x) => `<tr class="clic" data-enc="${x.id}" style="${x.id === au.encargo ? "background:#eef2f8" : ""}"><td>${esc(x.codigo)}</td><td>${esc(x.nombre)}</td><td><small>${esc(x.tipo)}</small></td><td>${fecha(x.fecha_corte)}</td><td>${esc(x.estado)}</td></tr>`).join("") || '<tr><td colspan="5" class="vacio">Sin encargos</td></tr>'}</tbody></table></div>
    <div class="card" id="au-det">${e ? detalleEncargoAU(e) : '<div class="vacio">Seleccione un encargo</div>'}</div></div><div id="au-prog"></div>`;
  $$("[data-enc]").forEach((tr) => tr.addEventListener("click", () => { au.encargo = Number(tr.dataset.enc); almacen.guardar(`au_enc_${estado.empresaId}`, String(au.encargo)); navegar(); }));
  $("#au-nuevo")?.addEventListener("click", formEncargoAU);
  if (e) enlazarEncargoAU(e);
};

function detalleEncargoAU(e) {
  const r = e.resumen.totales;
  return `<h2>${esc(e.codigo)} · ${esc(e.nombre)}</h2><p class="sub">${esc(e.tipo)} · corte ${fecha(e.fecha_corte)} · ${esc(e.estado)} · responsable ${esc(e.responsable || "—")}${e.recurrencia ? ` · recurrente ${esc(e.recurrencia.toLowerCase())}` : ""}</p>
    <p class="sub">Alcance: ${esc(Object.entries(e.alcance).map(([k, v]) => `${k}: ${v.join(", ")}`).join(" · ") || "todo el balance")}</p>
    <p>${r.hallazgos} hallazgos · exposición potencial ${num(r.exposicion_potencial)} · confirmada ${num(r.exposicion_confirmada)}</p>
    <div class="filtros"><button class="btn btn-primario" data-run="COMPLETA">Auditoría completa</button>
      <select id="au-mod"><option value="">Módulo…</option>${au.cat.categorias.map((c) => `<option value="${c.codigo}">${esc(c.nombre)}</option>`).join("")}</select><button class="btn" data-run="MODULO">Ejecutar módulo</button>
      <input id="au-cta" placeholder="Cuenta (p. ej. 42)" style="width:130px;min-width:0"><button class="btn" data-run="CUENTA">Ejecutar cuenta</button>
      <input id="au-rg" placeholder="Reglas (INT-01, DUP-01)" style="width:180px;min-width:0"><button class="btn" data-run="REGLAS">Ejecutar reglas</button>
      <label class="sub"><input type="checkbox" id="au-forzar"> recalcular todo</label></div>
    <div class="filtros">${e.estado === "EN_EJECUCION" ? '<button class="btn btn-sm" data-est="EN_REVISION">Enviar a revisión</button>' : ""}${e.estado === "EN_REVISION" && puedeAU("aprobar") ? '<button class="btn btn-sm" data-est="CONCLUIDO">Aprobar conclusión</button>' : ""}
      ${e.estado === "CONCLUIDO" && puedeAU("aprobar") ? '<button class="btn btn-sm" data-est="CERRADO">Cerrar encargo</button>' : ""}${e.recurrencia ? '<button class="btn btn-sm" id="au-sig">Programar siguiente periodo</button>' : ""}
      <a class="btn btn-sm" href="#/aud-papeles">Papeles de trabajo</a><a class="btn btn-sm" href="#/aud-informes">Informes</a></div>
    ${e.conclusion ? `<div class="alerta alerta-ok">Conclusión preliminar (aprobada por ${esc(e.conclusion_aprobada_por)}): ${esc(e.conclusion)}</div>` : ""}
    <h3>Ejecuciones</h3><table class="tabla"><thead><tr><th>#</th><th>Tipo</th><th>Estado</th><th class="num">ms</th><th>Usuario</th><th></th></tr></thead><tbody>
    ${e.ejecuciones.map((x) => `<tr><td>${x.numero}</td><td>${esc(x.tipo)}</td><td>${esc(x.estado_proceso)}</td><td class="num">${x.duracion_ms ?? ""}</td><td>${esc(x.usuario)}</td><td><button class="btn btn-sm" data-ver-run="${x.id}">Reglas</button></td></tr>`).join("") || '<tr><td colspan="6" class="vacio">Sin ejecuciones</td></tr>'}</tbody></table>`;
}

function enlazarEncargoAU(e) {
  $$("[data-run]").forEach((b) => b.addEventListener("click", async () => {
    const tipo = b.dataset.run;
    const body = { tipo, forzar: $("#au-forzar").checked };
    if (tipo === "MODULO") body.modulos = [$("#au-mod").value].filter(Boolean);
    if (tipo === "CUENTA") body.cuentas = [$("#au-cta").value.trim()].filter(Boolean);
    if (tipo === "REGLAS") body.reglas = $("#au-rg").value.split(",").map((x) => x.trim().toUpperCase()).filter(Boolean);
    try { const r = await api(`/auditoria360/encargos/${e.id}/ejecutar`, { method: "POST", params: pAU(), body }); await esperarAU(r, $("#au-prog")); toast("Auditoría ejecutada", "ok"); navegar(); }
    catch (x) { toast(x.message, "err"); }
  }));
  $$("[data-est]").forEach((b) => b.addEventListener("click", async () => {
    let conclusion = null;
    if (b.dataset.est === "CONCLUIDO") { conclusion = prompt("Conclusión preliminar (mínimo 20 caracteres):"); if (!conclusion) return; }
    try { await api(`/auditoria360/encargos/${e.id}/estado`, { method: "POST", params: pAU(), body: { estado: b.dataset.est, conclusion, lock_version: e.lock_version } }); navegar(); } catch (x) { toast(x.message, "err"); }
  }));
  $("#au-sig")?.addEventListener("click", async () => { try { const n = await api(`/auditoria360/encargos/${e.id}/programar-siguiente`, { method: "POST", params: pAU() }); au.encargo = n.id; navegar(); } catch (x) { toast(x.message, "err"); } });
  $$("[data-ver-run]").forEach((b) => b.addEventListener("click", async () => {
    const r = await api(`/auditoria360/ejecuciones/${b.dataset.verRun}`, { params: pAU() });
    abrirModal(`Ejecución #${r.numero} · ${r.duracion_ms} ms`, `<table class="tabla"><thead><tr><th>Regla</th><th>Módulo</th><th>Estado</th><th class="num">Población</th><th class="num">Excepciones</th><th class="num">ms</th><th>Método / mensaje</th></tr></thead>
      <tbody>${r.resultados.map((x) => `<tr><td>${esc(x.codigo)} v${x.version}</td><td><small>${esc(x.modulo)}</small></td><td><small>${esc(x.estado)}</small></td><td class="num">${x.poblacion}</td><td class="num">${x.excepciones}</td><td class="num">${x.duracion_ms}</td><td><small>${esc(x.mensaje || x.metodo || "")}</small></td></tr>`).join("")}</tbody></table>`);
  }));
}

function formEncargoAU() {
  const hoy = new Date(); const fin = new Date(Date.UTC(hoy.getFullYear(), hoy.getMonth(), 0)).toISOString().slice(0, 10);
  const m = abrirModal("Nuevo encargo de auditoría", `<form id="fe" class="form-grid form-q">
    <label>Tipo <select name="tipo">${au.cat.tipos_auditoria.map((t) => `<option>${t}</option>`).join("")}</select></label><label>Nombre <input name="nombre"></label>
    <label>Fecha de corte <input type="date" name="fecha_corte" value="${fin}" required></label><label>Responsable <input name="responsable"></label>
    <label>Recurrencia <select name="recurrencia"><option value="">No recurrente</option><option>MENSUAL</option><option>TRIMESTRAL</option><option>ANUAL</option></select></label>
    <label style="grid-column:1/-1">Objetivo <textarea name="objetivo" rows="2"></textarea></label>
    <label>Módulos (vacío = todos) <select name="modulos" multiple size="6">${au.cat.categorias.map((c) => `<option value="${c.codigo}">${esc(c.nombre)}</option>`).join("")}</select></label>
    <label>Cuentas (separadas por coma) <input name="cuentas"></label><label>Centros de costo <input name="centros_costo"></label><label>Proyectos <input name="proyectos"></label>
    <label>Unidades de negocio <input name="unidades_negocio"></label><label>Reglas aplicables (códigos) <input name="reglas"></label>
    <div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Crear</button></div></form>`);
  m.querySelector("#fe").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = ev.target; const d = datosForm(f);
    const lista = (v) => (v || "").split(",").map((x) => x.trim()).filter(Boolean);
    const alcance = { modulos: [...f.modulos.selectedOptions].map((o) => o.value), cuentas: lista(d.cuentas), centros_costo: lista(d.centros_costo), proyectos: lista(d.proyectos),
      unidades_negocio: lista(d.unidades_negocio), reglas: lista(d.reglas).map((x) => x.toUpperCase()) };
    try { const e = await api("/auditoria360/encargos", { method: "POST", params: pAU(), body: { tipo: d.tipo, nombre: d.nombre || null, fecha_corte: d.fecha_corte, responsable: d.responsable || null,
      recurrencia: d.recurrencia || null, objetivo: d.objetivo || null, alcance } }); au.encargo = e.id; almacen.guardar(`au_enc_${estado.empresaId}`, String(e.id)); cerrarModal(); navegar(); }
    catch (x) { toast(x.message, "err"); }
  });
}

// ------------------------------------------------------------------ explorador de hallazgos
rutas["aud-hallazgos"] = async () => {
  if (!(await inicioAU())) return;
  Object.assign(au.f, parametrosHash());
  const sel = await selectorEncargoAU();
  const r = await vigente(api("/auditoria360/hallazgos", { params: pAU({ ...au.f, engagement_id: au.encargo, por_pagina: 50 }) }));
  const opt = (k, xs) => `<select data-fa="${k}"><option value="">Todos</option>${xs.map((x) => `<option ${au.f[k] === x ? "selected" : ""}>${x}</option>`).join("")}</select>`;
  vista().innerHTML = `<div class="cab-vista"><div><h1>Explorador de hallazgos</h1><p class="sub">Hallazgos potenciales con evidencia verificable; un hallazgo no es una infracción ni un error confirmado hasta su revisión.</p></div></div>
    ${sel}<div class="card"><div class="filtros"><label>Módulo ${opt("modulo", au.cat.categorias.map((c) => c.codigo))}</label><label>Riesgo ${opt("riesgo", au.cat.riesgos)}</label>
      <label>Estado ${opt("estado", Object.keys(EST_AU))}</label><label>Tipo ${opt("tipo", ["POTENCIAL", "CONFIRMADO", "FALSO_POSITIVO", "JUSTIFICADO", "SUBSANADO"])}</label>
      <label>Cuenta <input data-fa="cuenta" value="${esc(au.f.cuenta || "")}" style="width:90px;min-width:0"></label><label>Buscar <input data-fa="buscar" value="${esc(au.f.buscar || "")}"></label>
      <label>Orden <select data-fa="orden"><option value="">Prioridad</option><option value="importe" ${au.f.orden === "importe" ? "selected" : ""}>Importe</option><option value="fecha" ${au.f.orden === "fecha" ? "selected" : ""}>Fecha</option></select></label>
      <label><input type="checkbox" data-fc="vencidos" ${au.f.vencidos ? "checked" : ""}> Vencidos</label><label><input type="checkbox" data-fc="bandeja" ${au.f.bandeja ? "checked" : ""}> Bandeja de regularización</label></div>
      ${tablaHAU(r.items)}${paginador(r.total, r.pagina, r.por_pagina, (p) => { au.f.pagina = p; navegar(); })}</div>`;
  $$("[data-fa]").forEach((i) => i.addEventListener("change", () => { au.f[i.dataset.fa] = i.value; au.f.pagina = 1; location.hash = "#/aud-hallazgos"; navegar(); }));
  $$("[data-fc]").forEach((i) => i.addEventListener("change", () => { au.f[i.dataset.fc] = i.checked; au.f.pagina = 1; navegar(); }));
  $$("[data-h]").forEach((tr) => tr.addEventListener("click", () => panelHAU(Number(tr.dataset.h))));
};

async function panelHAU(id) {
  const h = await api(`/auditoria360/hallazgos/${id}`, { params: pAU() });
  const fila = (k, v) => `<tr><th style="width:28%">${k}</th><td>${v}</td></tr>`;
  const m = abrirModal(`${h.codigo} · ${h.titulo}`, `<p>${riesgoAU(h.riesgo)} ${estAU(h.estado, h.tipo)} <small class="sub">impacto ${h.impacto} × probabilidad ${h.probabilidad} = ${h.puntuacion} (priorización interna)${h.riesgo_ajustado_por ? ` · ajustado por ${esc(h.riesgo_ajustado_por)}: ${esc(h.justificacion_riesgo)}` : ""}</small></p>
    <table class="tabla">${fila("Condición detectada", esc(h.condicion))}${fila("Criterio", esc(h.criterio || "—"))}${fila("Causa o hipótesis", esc(h.causa || "—"))}${fila("Efecto", esc(h.efecto || "—"))}
      ${fila("Impacto potencial", esc(h.impacto_potencial || "—"))}${fila("Recomendación", esc(h.recomendacion || "—"))}
      ${fila("Cuenta / tercero / documento / asiento", `${esc(h.cuenta || "—")} · ${esc(h.razon_social || h.tercero || "—")} · ${esc(h.documento || "—")} · ${esc(h.asiento || "—")} ${h.linea_id ? `<button class="btn btn-sm" id="hz-asi">Ver asiento original</button>` : ""}`)}
      ${fila("Importe", `${num(h.importe)}${h.importe_confirmado ? ` · confirmado ${num(h.importe_confirmado)}` : ""}${h.grupo ? ` · grupo de exposición (${h.grupo.miembros.join(", ")}): ${num(h.grupo.exposicion)}` : ""}`)}
      ${fila("Materialidad", h.sobre_materialidad ? "Supera la materialidad de ejecución" : h.claramente_insignificante ? "Claramente insignificante (visible por su naturaleza)" : "—")}
      ${fila("Tratamiento tributario", esc(h.tratamiento_tributario || "—"))}${fila("Regularización (fase 8)", `${esc(h.regularizacion || "—")}${h.en_bandeja_regularizacion ? " · en bandeja" : ""}`)}
      ${fila("Detección", `${fecha(h.fecha_deteccion)} · regla ${esc(h.regla)} · límite ${fecha(h.fecha_limite)} · reincidencias ${h.reincidencias}`)}</table>
    <h3>Evidencias</h3><table class="tabla"><tbody>${h.evidencias.map((e) => `<tr><td><small>${esc(e.origen)} · ${esc(e.tipo)}</small></td><td>${esc(e.descripcion)}${e.tabla ? ` <small class="sub">(${esc(e.tabla)} #${e.registro_id ?? ""})</small>` : ""}
      ${e.nombre_archivo ? ` <a href="#" data-ev="${e.id}">${esc(e.nombre_archivo)}</a>` : ""}${e.tabla === "lineas_diario" && e.registro_id ? ` <a href="#" data-lin="${e.registro_id}">asiento</a>` : ""}</td></tr>`).join("")}</tbody></table>
    <form id="hz-adj" class="filtros"><input type="file" name="archivo" required><input name="descripcion" placeholder="Descripción de la evidencia"><label class="sub"><input type="checkbox" name="confidencial"> confidencial</label><button class="btn btn-sm">Adjuntar</button></form>
    <h3>Cambiar estado</h3><form id="hz-est" class="form-grid form-q"><label>Nuevo estado <select name="estado">${(SIG_AU[h.estado] || []).map((s) => `<option>${s}</option>`).join("")}</select></label>
      <label>Regularización <select name="regularizacion"><option value="">—</option>${au.cat.regularizacion.map((x) => `<option ${h.regularizacion === x ? "selected" : ""}>${x}</option>`).join("")}</select></label>
      <label>Importe confirmado <input name="importe_confirmado"></label><label style="grid-column:1/-1">Comentario / justificación <textarea name="comentario" rows="2"></textarea></label>
      <div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Aplicar</button>${h.tipo === "CONFIRMADO" && !h.en_bandeja_regularizacion ? '<button type="button" class="btn" id="hz-reg">Enviar a bandeja de regularización</button>' : ""}</div></form>
    <h3>Responsable, plazo y riesgo</h3><form id="hz-upd" class="form-grid form-q"><label>Responsable <input name="responsable" value="${esc(h.responsable || "")}"></label><label>Fecha límite <input type="date" name="fecha_limite" value="${h.fecha_limite || ""}"></label>
      <label>Riesgo <select name="riesgo"><option value="">(sin cambio)</option>${au.cat.riesgos.map((r) => `<option>${r}</option>`).join("")}</select></label><label>Justificación del ajuste <input name="justificacion_riesgo"></label>
      <label style="grid-column:1/-1">Causa <input name="causa" value="${esc(h.causa || "")}"></label><div class="acciones" style="grid-column:1/-1"><button class="btn">Guardar</button></div></form>
    <h3>Plan de acción</h3>${h.planes.map((p) => `<div><small>${esc(p.descripcion)} · ${esc(p.responsable)} · ${fecha(p.fecha_compromiso)} · ${esc(p.estado)}</small></div>`).join("") || '<p class="sub">Sin planes</p>'}
    <form id="hz-plan" class="filtros"><input name="descripcion" placeholder="Acción correctiva" required><input name="responsable" placeholder="Responsable" required><input type="date" name="fecha_compromiso" required><button class="btn btn-sm">Agregar plan</button></form>
    <h3>Historial</h3><table class="tabla"><tbody>${h.historial.map((x) => `<tr><td><small>${fechaHora(x.creado_en)}</small></td><td>${esc(x.usuario)}</td><td>${esc(x.de_estado || "")} → ${esc(x.a_estado || "")}</td><td><small>${esc(x.comentario || "")}</small></td></tr>`).join("") || '<tr><td class="vacio">Sin cambios</td></tr>'}</tbody></table>`);
  const recargar = () => { panelHAU(id); };
  $("#hz-asi")?.addEventListener("click", () => verAsiento(h.linea_id));
  $$("[data-lin]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); verAsiento(Number(a.dataset.lin)); }));
  $$("[data-ev]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); bajar(`/auditoria360/evidencias/${a.dataset.ev}`, pAU(), "evidencia").catch((x) => toast(x.message, "err")); }));
  m.querySelector("#hz-adj").addEventListener("submit", async (ev) => {
    ev.preventDefault(); const f = new FormData(ev.target); f.set("confidencial", ev.target.confidencial.checked ? "true" : "false");
    try { await api(`/auditoria360/hallazgos/${id}/evidencias`, { method: "POST", params: pAU(), form: f }); toast("Evidencia adjuntada", "ok"); recargar(); } catch (x) { toast(x.message, "err"); }
  });
  m.querySelector("#hz-est").addEventListener("submit", async (ev) => {
    ev.preventDefault(); const d = datosForm(ev.target);
    try { await api(`/auditoria360/hallazgos/${id}/estado`, { method: "POST", params: pAU(), body: { estado: d.estado, comentario: d.comentario || null, lock_version: h.lock_version,
      regularizacion: d.regularizacion || null, importe_confirmado: d.importe_confirmado || null } }); toast("Estado actualizado", "ok"); recargar(); } catch (x) { toast(x.message, "err"); }
  });
  $("#hz-reg")?.addEventListener("click", async () => { try { await api(`/auditoria360/hallazgos/${id}/regularizacion`, { method: "POST", params: pAU() }); toast("Enviado a la bandeja (no se generan asientos)", "ok"); recargar(); } catch (x) { toast(x.message, "err"); } });
  m.querySelector("#hz-upd").addEventListener("submit", async (ev) => {
    ev.preventDefault(); const d = datosForm(ev.target);
    const body = { responsable: d.responsable || null, fecha_limite: d.fecha_limite || null, causa: d.causa || null, lock_version: h.lock_version };
    if (d.riesgo) Object.assign(body, { riesgo: d.riesgo, justificacion_riesgo: d.justificacion_riesgo });
    try { await api(`/auditoria360/hallazgos/${id}`, { method: "PATCH", params: pAU(), body }); recargar(); } catch (x) { toast(x.message, "err"); }
  });
  m.querySelector("#hz-plan").addEventListener("submit", async (ev) => {
    ev.preventDefault(); const d = datosForm(ev.target);
    try { await api(`/auditoria360/hallazgos/${id}/planes`, { method: "POST", params: pAU(), body: d }); recargar(); } catch (x) { toast(x.message, "err"); }
  });
}

// ------------------------------------------------------------------ acciones correctivas
rutas["aud-acciones"] = async () => {
  if (!(await inicioAU())) return;
  const sel = await selectorEncargoAU();
  const r = await vigente(api("/auditoria360/hallazgos", { params: pAU({ engagement_id: au.encargo, estado: "CONFIRMADO,PENDIENTE_REGULARIZACION,EN_SUBSANACION,SUBSANADO,REABIERTO", por_pagina: 200 }) }));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Acciones correctivas</h1><p class="sub">Seguimiento de hallazgos confirmados: planes, plazos, subsanación, verificación y cierre (con separación de funciones).</p></div></div>
    ${sel}<div class="card">${tablaHAU(r.items)}</div><div class="card"><a class="btn" href="#/aud-hallazgos?vencidos=1">Ver vencidos</a>
    <button class="btn" id="au-xp">Exportar planes de acción</button><button class="btn" id="au-xs">Exportar seguimiento</button></div>`;
  $$("[data-h]").forEach((tr) => tr.addEventListener("click", () => panelHAU(Number(tr.dataset.h))));
  $("#au-xp").addEventListener("click", () => au.encargo && bajar(`/auditoria360/encargos/${au.encargo}/exportar/PLANES`, pAU(), "planes.xlsx").catch((x) => toast(x.message, "err")));
  $("#au-xs").addEventListener("click", () => au.encargo && bajar(`/auditoria360/encargos/${au.encargo}/exportar/SEGUIMIENTO`, pAU(), "seguimiento.xlsx").catch((x) => toast(x.message, "err")));
};

// ------------------------------------------------------------------ matriz de riesgos interactiva
rutas["aud-matriz"] = async () => {
  if (!(await inicioAU())) return;
  const sel = await selectorEncargoAU();
  const d = await vigente(api("/auditoria360/tablero", { params: pAU({ engagement_id: au.encargo }) }));
  const mz = au.cat.matriz.matriz;
  vista().innerHTML = `<div class="cab-vista"><div><h1>Matriz de riesgos</h1><p class="sub">Impacto (contra la materialidad aprobada) × probabilidad estimada. La puntuación es una priorización interna, no una probabilidad estadística validada.</p></div></div>
    ${sel}<div class="card"><table class="tabla" style="max-width:720px"><thead><tr><th>Impacto \\ Probabilidad</th>${[1, 2, 3, 4, 5].map((p) => `<th class="num">${p}</th>`).join("")}</tr></thead><tbody>
      ${[5, 4, 3, 2, 1].map((i) => `<tr><th>${i}</th>${[1, 2, 3, 4, 5].map((p) => { const n = d.matriz[`${i}x${p}`] || 0; const nv = mz[i - 1][p - 1];
        return `<td class="num clic" data-celda="${i}x${p}" style="background:${RIESGO_AU[nv]}22;border:1px solid ${RIESGO_AU[nv]}55"><b>${n || ""}</b><br><small>${nv}</small></td>`; }).join("")}</tr>`).join("")}</tbody></table>
      <p class="sub">Matriz versión ${au.cat.matriz.version || "por defecto"}. ${puedeAU("aprobar") ? '<button class="btn btn-sm" id="au-edm">Editar matriz</button>' : ""}</p></div><div class="card" id="au-celda"></div>`;
  $$("[data-celda]").forEach((td) => td.addEventListener("click", async () => {
    const [i, p] = td.dataset.celda.split("x").map(Number);
    const r = await api("/auditoria360/hallazgos", { params: pAU({ engagement_id: au.encargo, solo_vigentes: true, por_pagina: 500 }) });
    $("#au-celda").innerHTML = `<h2>Impacto ${i} × probabilidad ${p}</h2>${tablaHAU(r.items.filter((h) => h.impacto === i && h.probabilidad === p))}`;
    $$("#au-celda [data-h]").forEach((tr) => tr.addEventListener("click", () => panelHAU(Number(tr.dataset.h))));
  }));
  $("#au-edm")?.addEventListener("click", () => {
    const m = abrirModal("Editar matriz de riesgos", `<p class="sub">Nivel por celda (filas: impacto 1→5; columnas: probabilidad 1→5).</p><textarea id="mz" rows="8" style="width:100%;font-family:monospace">${esc(JSON.stringify(mz))}</textarea>
      <div class="acciones"><button class="btn btn-primario" id="mz-ok">Guardar y aprobar</button></div>`);
    m.querySelector("#mz-ok").addEventListener("click", async () => {
      try { await api("/auditoria360/matriz", { method: "POST", params: pAU(), body: { matriz: JSON.parse($("#mz").value) } }); cerrarModal(); navegar(); } catch (x) { toast(x.message, "err"); }
    });
  });
};

// ------------------------------------------------------------------ biblioteca de reglas y diseñador de controles
rutas["aud-reglas"] = async () => {
  if (!(await inicioAU())) return;
  const f = parametrosHash();
  const rs = await vigente(api("/auditoria360/reglas", { params: pAU({ modulo: f.modulo, buscar: f.buscar }) }));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Biblioteca de reglas</h1><p class="sub">${rs.length} reglas. Las normativas no se ejecutan sin validar su norma, fuente oficial, vigencia y condiciones.</p></div>
    <div class="acciones" style="margin:0"><a class="btn btn-primario" href="#/aud-disenador">Diseñar control</a></div></div>
    <div class="card"><div class="filtros"><select id="rf-m"><option value="">Todos los módulos</option>${au.cat.categorias.map((c) => `<option value="${c.codigo}" ${f.modulo === c.codigo ? "selected" : ""}>${esc(c.nombre)}</option>`).join("")}</select>
      <input id="rf-b" value="${esc(f.buscar || "")}" placeholder="Buscar"></div>
    <div class="tabla-scroll"><table class="tabla"><thead><tr><th>Código</th><th>Módulo</th><th>Nombre</th><th>Riesgo</th><th>Estado</th><th>Validación</th><th>Versión</th><th></th></tr></thead><tbody>
      ${rs.map((r) => `<tr><td><b>${esc(r.codigo)}</b>${r.personalizada ? ' <span class="badge b-info">empresa</span>' : ""}</td><td><small>${esc(r.modulo)}</small></td><td>${esc(r.nombre)}<br><small class="sub">${esc(r.descripcion || "")}</small></td>
        <td>${riesgoAU(r.riesgo)}</td><td>${r.activa ? "Activa" : "Inactiva"}</td><td><small>${esc(r.estado_validacion)}${r.validada_por ? ` · ${esc(r.validada_por)}` : ""}</small></td><td>${r.version}</td>
        <td><button class="btn btn-sm" data-rg="${r.id}">Editar</button>${r.personalizada && r.estado_validacion === "PENDIENTE" && puedeAU("validar_reglas") ? ` <button class="btn btn-sm" data-val="${r.id}">Validar</button>` : ""}</td></tr>`).join("")}</tbody></table></div></div>`;
  $("#rf-m").addEventListener("change", (e) => { location.hash = `#/aud-reglas?modulo=${e.target.value}`; });
  $("#rf-b").addEventListener("change", (e) => { location.hash = `#/aud-reglas?buscar=${encodeURIComponent(e.target.value)}${f.modulo ? `&modulo=${f.modulo}` : ""}`; });
  $$("[data-val]").forEach((b) => b.addEventListener("click", async () => { try { await api(`/auditoria360/reglas/${b.dataset.val}/validar`, { method: "POST", params: pAU(), body: { aprobar: true } }); navegar(); } catch (x) { toast(x.message, "err"); } }));
  $$("[data-rg]").forEach((b) => b.addEventListener("click", () => {
    const r = rs.find((x) => x.id === Number(b.dataset.rg));
    const m = abrirModal(`Regla ${r.codigo}`, `<form id="frg" class="form-grid form-q"><label>Nombre <input name="nombre" value="${esc(r.nombre)}"></label><label>Cuentas <input name="cuentas" value="${esc(r.cuentas || "")}"></label>
      <label>Riesgo <select name="riesgo">${au.cat.riesgos.map((x) => `<option ${x === r.riesgo ? "selected" : ""}>${x}</option>`).join("")}</select></label><label>Probabilidad (1–5) <input type="number" min="1" max="5" name="probabilidad" value="${r.probabilidad}"></label>
      <label>Vigente desde <input type="date" name="vigente_desde" value="${r.vigente_desde || ""}"></label><label>Vigente hasta <input type="date" name="vigente_hasta" value="${r.vigente_hasta || ""}"></label>
      <label style="grid-column:1/-1">Parámetros (umbrales, tolerancias) <textarea name="parametros" rows="3" style="font-family:monospace">${esc(JSON.stringify(r.parametros))}</textarea></label>
      <label style="grid-column:1/-1">Excepciones (cuentas, terceros, documentos) <input name="excepciones" value="${esc(r.excepciones || "{}")}"></label>
      ${r.normativa ? `<label>Norma de referencia <input name="norma_referencia" value="${esc(r.norma_referencia || "")}"></label><label>Fuente oficial <input name="fuente_oficial" value="${esc(r.fuente_oficial || "")}"></label>
        <label>Fecha de publicación <input type="date" name="fecha_publicacion" value="${r.fecha_publicacion || ""}"></label><label>Responsable de validación <input name="responsable_validacion" value="${esc(r.responsable_validacion || "")}"></label>
        <label style="grid-column:1/-1">Condiciones de aplicación <textarea name="condiciones_aplicacion" rows="2">${esc(r.condiciones_aplicacion || "")}</textarea></label>
        <label style="grid-column:1/-1">Excepciones normativas <textarea name="excepciones_normativas" rows="2">${esc(r.excepciones_normativas || "")}</textarea></label>` : ""}
      <label style="grid-column:1/-1">Motivo del cambio <input name="motivo"></label><div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Guardar nueva versión</button></div></form>`);
    m.querySelector("#frg").addEventListener("submit", async (ev) => {
      ev.preventDefault(); const d = datosForm(ev.target);
      try { d.parametros = JSON.parse(d.parametros || "{}"); d.excepciones = JSON.parse(d.excepciones || "{}"); } catch { toast("JSON no válido", "err"); return; }
      d.probabilidad = Number(d.probabilidad); Object.keys(d).forEach((k) => { if (d[k] === "") d[k] = null; });
      try { await api(`/auditoria360/reglas/${r.id}`, { method: "PUT", params: pAU(), body: d }); cerrarModal(); toast("Regla guardada (nueva versión)", "ok"); navegar(); } catch (x) { toast(x.message, "err"); }
    });
  }));
};

const dsAU = { condiciones: [{ campo: "cuenta", op: "empieza", valor: "6" }], logica: "y" };
rutas["aud-disenador"] = async () => {
  if (!(await inicioAU())) return;
  const fuentes = au.cat.fuentes_configurables;
  dsAU.fuente = dsAU.fuente || "LINEAS";
  const campos = fuentes[dsAU.fuente];
  vista().innerHTML = `<div class="cab-vista"><div><h1>Diseñador de controles</h1><p class="sub">Defina condiciones con operadores lógicos, revise la vista previa y active la regla. No se admite código ni SQL.</p></div></div>
    <div class="card"><form id="fd" class="form-grid form-q"><label>Código <input name="codigo" placeholder="EMP-01" required></label><label>Nombre <input name="nombre" required></label>
      <label>Fuente <select name="fuente" id="ds-f">${Object.keys(fuentes).map((x) => `<option ${x === dsAU.fuente ? "selected" : ""}>${x}</option>`).join("")}</select></label>
      <label>Combinar con <select id="ds-l"><option value="y" ${dsAU.logica === "y" ? "selected" : ""}>Y (todas)</option><option value="o" ${dsAU.logica === "o" ? "selected" : ""}>O (alguna)</option></select></label>
      <label>Riesgo <select name="riesgo">${au.cat.riesgos.map((x) => `<option ${x === "MEDIO" ? "selected" : ""}>${x}</option>`).join("")}</select></label><label>Título <input name="titulo" placeholder="Texto con {campo}"></label>
      <label style="grid-column:1/-1">Recomendación <input name="recomendacion"></label></form>
      <h3>Condiciones</h3><div id="ds-c">${dsAU.condiciones.map((c, i) => `<div class="filtros"><select data-cc="${i}" data-k="campo">${campos.map((x) => `<option ${x === c.campo ? "selected" : ""}>${x}</option>`).join("")}</select>
        <select data-cc="${i}" data-k="op">${au.cat.operadores.map((x) => `<option ${x === c.op ? "selected" : ""}>${x}</option>`).join("")}</select><input data-cc="${i}" data-k="valor" value="${esc(Array.isArray(c.valor) ? c.valor.join(",") : c.valor ?? "")}">
        <button class="btn btn-sm" data-quitar="${i}">Quitar</button></div>`).join("")}</div>
      <div class="acciones"><button class="btn btn-sm" id="ds-mas">Agregar condición</button><button class="btn" id="ds-prev">Vista previa</button><button class="btn btn-primario" id="ds-ok">Guardar (inactiva)</button></div>
      <div id="ds-res"></div></div>`;
  const leer = () => {
    $$("[data-cc]").forEach((i) => { const c = dsAU.condiciones[Number(i.dataset.cc)]; let v = i.value; if (i.dataset.k === "valor" && ["en", "no_en", "entre"].includes(c.op)) v = v.split(",").map((x) => x.trim()); c[i.dataset.k] = v; });
    dsAU.logica = $("#ds-l").value;
  };
  const defin = () => { leer(); const f = datosForm($("#fd")); return { fuente: dsAU.fuente, condiciones: { [dsAU.logica]: dsAU.condiciones.map((c) => ({ ...c })) }, titulo: f.titulo || null }; };
  $("#ds-f").addEventListener("change", (e) => { dsAU.fuente = e.target.value; dsAU.condiciones = [{ campo: fuentes[dsAU.fuente][0], op: "no_vacio", valor: "" }]; navegar(); });
  $("#ds-mas").addEventListener("click", () => { leer(); dsAU.condiciones.push({ campo: campos[0], op: "=", valor: "" }); navegar(); });
  $$("[data-quitar]").forEach((b) => b.addEventListener("click", () => { leer(); dsAU.condiciones.splice(Number(b.dataset.quitar), 1); navegar(); }));
  $("#ds-prev").addEventListener("click", async () => {
    if (!au.encargo) { toast("Seleccione un encargo en el centro de ejecución", "err"); return; }
    try { const r = await api("/auditoria360/reglas/vista-previa", { method: "POST", params: pAU(), body: { engagement_id: au.encargo, definicion: defin() } });
      $("#ds-res").innerHTML = `<p>${r.coincidencias} coincidencias en ${r.poblacion} registros (máx. ${r.limite}). ${esc(r.nota)}</p><table class="tabla"><tbody>${r.muestra.map((x) => `<tr><td>${esc(x.titulo)}</td><td>${esc(x.cuenta || "")}</td><td class="num">${num(x.importe)}</td></tr>`).join("")}</tbody></table>`; }
    catch (x) { toast(x.message, "err"); }
  });
  $("#ds-ok").addEventListener("click", async () => {
    const f = datosForm($("#fd"));
    try { await api("/auditoria360/reglas", { method: "POST", params: pAU(), body: { codigo: f.codigo, nombre: f.nombre, riesgo: f.riesgo, recomendacion: f.recomendacion || null, definicion: defin() } });
      toast("Regla guardada inactiva: actívela desde la biblioteca", "ok"); location.hash = "#/aud-reglas"; } catch (x) { toast(x.message, "err"); }
  });
};

// ------------------------------------------------------------------ papeles de trabajo y muestras
rutas["aud-papeles"] = async () => {
  if (!(await inicioAU())) return;
  const sel = await selectorEncargoAU();
  if (!au.encargo) { vista().innerHTML = sel + '<div class="vacio">Seleccione un encargo</div>'; return; }
  const ps = await vigente(api(`/auditoria360/encargos/${au.encargo}/papeles`, { params: pAU() }));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Papeles de trabajo</h1><p class="sub">Papeles preliminares por procedimiento (regla), con población, método, excepciones, evidencias y conclusión preliminar.</p></div></div>
    ${sel}<div class="card"><div class="filtros"><input id="pp-r" placeholder="Código de regla (p. ej. DUP-01)"><button class="btn btn-primario" id="pp-g">Generar papel</button></div>
    <table class="tabla"><thead><tr><th>Referencia</th><th>Título</th><th>Estado</th><th>Elaboró</th><th>Revisó</th><th>Conclusión preliminar</th><th></th></tr></thead><tbody>
      ${ps.map((p) => `<tr><td>${esc(p.referencia)}</td><td>${esc(p.titulo)}</td><td>${esc(p.estado)}</td><td>${esc(p.elaborado_por)}</td><td>${esc(p.revisado_por || "")}</td><td><small>${esc(p.conclusion || "")}</small></td>
        <td>${{ PRELIMINAR: "EN_REVISION", EN_REVISION: "REVISADO", REVISADO: "APROBADO" }[p.estado] ? `<button class="btn btn-sm" data-pe="${p.id}" data-a="${{ PRELIMINAR: "EN_REVISION", EN_REVISION: "REVISADO", REVISADO: "APROBADO" }[p.estado]}">${{ PRELIMINAR: "Enviar a revisión", EN_REVISION: "Marcar revisado", REVISADO: "Aprobar" }[p.estado]}</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="7" class="vacio">Sin papeles</td></tr>'}</tbody></table>
    <button class="btn" id="pp-x">Exportar papeles (Excel)</button></div>
    <div class="card"><h2>Muestras</h2><form id="mu" class="form-grid form-q"><label>Población <select name="poblacion"><option>LINEAS</option><option>HALLAZGOS</option></select></label>
      <label>Método <select name="metodo">${au.cat.metodos_muestra.map((x) => `<option>${x}</option>`).join("")}</select></label><label>Tamaño <input type="number" name="tamano" value="25" min="1"></label>
      <label>Semilla (aleatoria) <input type="number" name="semilla"></label><label>Criterios (JSON) <input name="criterios" value="{}" placeholder='{"cuenta":"42"} o {"limites":[1000,10000]}'></label>
      <div class="acciones"><button class="btn btn-primario">Seleccionar muestra</button></div></form><div id="mu-r"></div></div>`;
  $("#pp-g").addEventListener("click", async () => { try { await api(`/auditoria360/encargos/${au.encargo}/papeles`, { method: "POST", params: pAU(), body: { regla: $("#pp-r").value.trim().toUpperCase() } }); navegar(); } catch (x) { toast(x.message, "err"); } });
  $$("[data-pe]").forEach((b) => b.addEventListener("click", async () => { try { await api(`/auditoria360/papeles/${b.dataset.pe}/estado`, { method: "POST", params: pAU(), body: { estado: b.dataset.a } }); navegar(); } catch (x) { toast(x.message, "err"); } }));
  $("#pp-x").addEventListener("click", () => bajar(`/auditoria360/encargos/${au.encargo}/exportar/PAPELES`, pAU(), "papeles.xlsx").catch((x) => toast(x.message, "err")));
  $("#mu").addEventListener("submit", async (ev) => {
    ev.preventDefault(); const d = datosForm(ev.target);
    try { const m = await api(`/auditoria360/encargos/${au.encargo}/muestras`, { method: "POST", params: pAU(), body: { poblacion: d.poblacion, metodo: d.metodo, tamano: Number(d.tamano), semilla: d.semilla ? Number(d.semilla) : null, criterios: JSON.parse(d.criterios || "{}") } });
      $("#mu-r").innerHTML = `<p>${m.tamano} de ${m.poblacion_cantidad} registros · método ${esc(m.metodo)}${m.semilla ? ` · semilla <b>${m.semilla}</b>` : ""} · ${m.estadisticamente_representativa ? "estadísticamente representativa" : esc(m.nota)}</p>
        <table class="tabla"><tbody>${m.items.map((i) => `<tr><td><small>${esc(i.tabla)} #${i.registro_id}</small></td><td>${esc(i.descripcion || "")}</td><td class="num">${num(i.importe)}</td><td>${esc(i.estrato || "")}</td></tr>`).join("")}</tbody></table>`; }
    catch (x) { toast(x.message, "err"); }
  });
};

// ------------------------------------------------------------------ generador de informes
rutas["aud-informes"] = async () => {
  if (!(await inicioAU())) return;
  const sel = await selectorEncargoAU();
  vista().innerHTML = `<div class="cab-vista"><div><h1>Generador de informes</h1><p class="sub">${esc(au.cat.aviso)}</p></div></div>${sel}
    <div class="card"><h2>Informes (16 secciones, versionados)</h2><div class="filtros"><select id="in-t">${Object.entries(au.cat.informes).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("")}</select>
      <input id="in-c" placeholder="Cuenta (solo detalle por cuenta)" style="width:200px;min-width:0"><button class="btn btn-primario" id="in-g">Generar versión</button></div><div id="in-r"></div></div>
    <div class="card"><h2>Exportaciones</h2><table class="tabla"><tbody>${Object.entries(au.cat.exportaciones).map(([k, v]) => `<tr><td>${esc(v)}</td><td><button class="btn btn-sm" data-x="${k}" data-f="xlsx">Excel</button> <button class="btn btn-sm" data-x="${k}" data-f="pdf">PDF</button></td></tr>`).join("")}</tbody></table></div>`;
  $("#in-g").addEventListener("click", async () => {
    if (!au.encargo) { toast("Seleccione un encargo", "err"); return; }
    try { const r = await api(`/auditoria360/encargos/${au.encargo}/informes`, { method: "POST", params: pAU(), body: { tipo: $("#in-t").value, cuenta: $("#in-c").value.trim() || null } });
      const c = r.contenido;
      $("#in-r").innerHTML = `<p><b>${esc(r.titulo)}</b> · versión ${r.version_actual} · hash <code>${esc(r.hash.slice(0, 16))}</code></p>
        <p>${c.resumen_ejecutivo.hallazgos} hallazgos · exposición potencial ${num(c.resumen_ejecutivo.exposicion_potencial)} · confirmada ${num(c.resumen_ejecutivo.exposicion_confirmada)}</p>
        <button class="btn" data-ix="${r.id}" data-f="pdf">PDF</button> <button class="btn" data-ix="${r.id}" data-f="xlsx">Excel</button>`;
      $$("[data-ix]").forEach((b) => b.addEventListener("click", () => bajar(`/auditoria360/informes/${b.dataset.ix}/exportar`, pAU({ formato: b.dataset.f }), `informe.${b.dataset.f}`).catch((x) => toast(x.message, "err")))); }
    catch (x) { toast(x.message, "err"); }
  });
  $$("[data-x]").forEach((b) => b.addEventListener("click", () => au.encargo ? bajar(`/auditoria360/encargos/${au.encargo}/exportar/${b.dataset.x}`, pAU({ formato: b.dataset.f }), `auditoria.${b.dataset.f}`).catch((x) => toast(x.message, "err")) : toast("Seleccione un encargo", "err")));
};

// ------------------------------------------------------------------ historial (bitácora protegida)
rutas["aud-historial"] = async () => {
  if (!(await inicioAU())) return;
  const b = await vigente(api("/auditoria360/bitacora", { params: pAU({ engagement_id: au.encargo, por_pagina: 200 }) }).catch((e) => ({ items: [], error: e.message })));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Historial de auditorías</h1><p class="sub">Bitácora encadenada por hash y protegida contra modificaciones.</p></div></div>
    ${b.error ? `<div class="alerta alerta-warn">${esc(b.error)}</div>` : `<div class="alerta ${b.verificacion.integra ? "alerta-ok" : "alerta-err"}">Integridad de la bitácora: ${b.verificacion.integra ? `verificada (${b.verificacion.eventos} eventos)` : `ALTERADA en el evento ${b.verificacion.primer_evento_alterado}`}</div>`}
    <div class="card"><table class="tabla"><thead><tr><th>Fecha</th><th>Usuario</th><th>Rol</th><th>Acción</th><th>Entidad</th><th>Detalle</th><th>Hash</th></tr></thead><tbody>
      ${b.items.map((x) => `<tr><td><small>${fechaHora(x.fecha)}</small></td><td>${esc(x.usuario)}</td><td>${esc(x.rol || "")}</td><td>${esc(x.accion)}</td><td>${esc(x.entidad)} ${x.entidad_id ?? ""}</td><td><small>${esc((x.detalle || "").slice(0, 160))}</small></td><td><code>${esc(x.hash.slice(0, 10))}</code></td></tr>`).join("") || '<tr><td colspan="7" class="vacio">—</td></tr>'}</tbody></table></div>`;
};

// ------------------------------------------------------------------ configuración: materialidad y parametrización del ERP
rutas["aud-config"] = async () => {
  if (!(await inicioAU())) return;
  const [mats, confs] = await vigente(Promise.all([api("/auditoria360/materialidad", { params: pAU() }), api("/auditoria360/configuraciones", { params: pAU() })]));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Materialidad y configuración</h1><p class="sub">Los porcentajes de materialidad los define y aprueba el responsable de auditoría (no hay porcentajes por defecto).</p></div></div>
    <div class="grid grid-2"><div class="card"><h2>Materialidad</h2><table class="tabla"><thead><tr><th>Ejercicio</th><th>Base</th><th class="num">Global</th><th class="num">Ejecución</th><th class="num">Insignificante</th><th>Estado</th><th></th></tr></thead><tbody>
      ${mats.map((m) => `<tr><td>${m.ejercicio}</td><td>${esc(m.base)}</td><td class="num">${num(m.materialidad_global)}</td><td class="num">${num(m.materialidad_ejecucion)}</td><td class="num">${num(m.umbral_insignificante)}</td><td>${esc(m.estado)}${m.aprobado_por ? ` · ${esc(m.aprobado_por)}` : ""}</td>
        <td>${m.estado === "BORRADOR" && puedeAU("aprobar") ? `<button class="btn btn-sm" data-am="${m.id}">Aprobar</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="7" class="vacio">Sin materialidad definida: el impacto se mide con el riesgo de cada regla</td></tr>'}</tbody></table>
      <form id="fm" class="form-grid form-q"><label>Ejercicio <input type="number" name="ejercicio" value="${new Date().getFullYear()}"></label><label>Base <select name="base">${au.cat.bases_materialidad.map((b) => `<option>${b}</option>`).join("")}</select></label>
        <label>Importe base (opcional) <input name="importe_base"></label><label>% global <input name="porcentaje_global" required></label><label>% ejecución <input name="porcentaje_ejecucion" required></label>
        <label>% claramente insignificante <input name="porcentaje_insignificante" required></label><label style="grid-column:1/-1">Justificación <input name="justificacion" required></label>
        <div class="acciones"><button class="btn btn-primario">Definir</button></div></form></div>
    <div class="card"><h2>Parametrización del ERP importada</h2><table class="tabla"><thead><tr><th>Tipo</th><th>Sistema</th><th>Versión</th><th class="num">Registros</th><th>Sustento</th></tr></thead><tbody>
      ${confs.map((c) => `<tr><td>${esc(c.tipo)}</td><td>${esc(c.sistema)}</td><td>${c.version}</td><td class="num">${c.registros}</td><td><small>${esc(c.sustento || "—")}</small></td></tr>`).join("") || '<tr><td colspan="5" class="vacio">Sin configuraciones: las conclusiones se limitan a los datos importados</td></tr>'}</tbody></table>
      <form id="fc" class="form-grid form-q"><label>Tipo <select name="tipo">${["PLAN_APROBADO", "PLAN_UTILIZADO", "RUBROS_APROBADOS", "RUBROS_UTILIZADOS", "DISTRIBUCION_APROBADA", "DISTRIBUCION_UTILIZADA"].map((t) => `<option>${t}</option>`).join("")}</select></label>
        <label>Sistema <select name="sistema">${au.cat.sistemas_erp.map((s) => `<option>${s}</option>`).join("")}</select></label><label>Archivo homologado <input type="file" name="archivo" required></label>
        <label style="grid-column:1/-1">Sustento del cambio <input name="sustento"></label><div class="acciones"><button class="btn btn-primario">Importar</button></div></form></div></div>`;
  $$("[data-am]").forEach((b) => b.addEventListener("click", async () => { try { await api(`/auditoria360/materialidad/${b.dataset.am}/aprobar`, { method: "POST", params: pAU() }); navegar(); } catch (x) { toast(x.message, "err"); } }));
  $("#fm").addEventListener("submit", async (ev) => {
    ev.preventDefault(); const d = datosForm(ev.target); d.ejercicio = Number(d.ejercicio); if (!d.importe_base) delete d.importe_base;
    try { await api("/auditoria360/materialidad", { method: "POST", params: pAU(), body: d }); navegar(); } catch (x) { toast(x.message, "err"); }
  });
  $("#fc").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try { await api("/auditoria360/configuraciones", { method: "POST", params: pAU(), form: new FormData(ev.target) }); toast("Configuración importada", "ok"); navegar(); } catch (x) { toast(x.message, "err"); }
  });
};
