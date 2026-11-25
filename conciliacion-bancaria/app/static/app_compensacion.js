/* Fase 4 — Compensación analítica de partidas: dashboard, partidas abiertas, compensación manual (doble panel),
   propuestas y aprobaciones, coincidencias ambiguas, anticipos, tributos, conciliación, configuración y reportes.
   La compensación es analítica: nunca modifica los asientos originales. Reutiliza utilitarios de app.js,
   app_contable.js (barraProgreso, esperarTrabajo) y app_analisis.js (gráficos, num, SERIES). */
"use strict";

const ctxC = { corte: null, rol: null };
const CONF = { MUY_ALTA: ["Muy alta", "#00b894"], ALTA: ["Alta", "#257de0"], MEDIA: ["Media", "#fbb315"], BAJA: ["Baja", "#dc3c3d"] };
const CANC = { TOTAL: ["Cancelada", "b-ok"], PARCIAL: ["Parcial", "b-info"], PENDIENTE: ["Pendiente", "b-warn"],
  ANTICIPO_PENDIENTE: ["Anticipo por aplicar", "b-info"], PENDIENTE_APLICAR: ["Por aplicar", "b-warn"] };
const VENC = { VENCIDO: ["Vencido", "b-err"], NO_VENCIDO: ["No vencido", "b-ok"], SIN_VENCIMIENTO: ["Sin fecha de vencimiento", ""], NO_APLICA: ["—", ""] };
const EST_G = { PROPUESTA: ["Propuesta", "b-warn"], APROBADA: ["Aprobada", "b-ok"], RECHAZADA: ["Rechazada", ""], REVERTIDA: ["Revertida", "b-err"] };
const MODAL = { UNO_A_UNO: "1:1", UNO_A_VARIOS: "1:N", VARIOS_A_UNO: "N:1", VARIOS_A_VARIOS: "N:N" };
const ROLES_C = { ADMINISTRADOR: "Administrador", CONTADOR: "Contador", ANALISTA: "Analista", AUDITOR: "Auditor", SUPERVISOR: "Supervisor", CONSULTA: "Consulta" };

const hoyISO = () => new Date().toISOString().slice(0, 10);
const qC = (extra = {}) => ({ empresa_id: estado.empresaId, fecha_corte: ctxC.corte, ...extra });
const chipB = (map, k) => { const [t, c] = map[k] || [k || "—", ""]; return `<span class="badge ${c}">${esc(t)}</span>`; };
const chipConf = (c, p) => (c ? `<span class="badge riesgo" style="--c:${CONF[c][1]}" title="Calidad de la coincidencia (no es una probabilidad)">${p ?? ""} ${CONF[c][0]}</span>` : "");
const modalidadTxt = (m) => { const [b, parc] = [m.replace("_PARCIAL", ""), m.endsWith("_PARCIAL")]; return `${MODAL[b] || b}${parc ? " parcial" : ""}`; };
const doc = (p) => esc(p.documento || (p.serie ? `${p.serie}-${p.numero}` : p.numero) || "s/doc.");
const puede = (accion) => ctxC.rol?.modo_abierto || (ctxC.rol?.permisos || []).includes(accion);
const exportC = (rep, fmt, extra = {}) => `/api/compensacion/exportar/${rep}.${fmt}?` + new URLSearchParams(
  Object.entries(qC(extra)).filter(([, v]) => v !== null && v !== undefined && v !== "")).toString();
const botonesC = (rep, extra = {}) => `<span class="exp"><a class="btn btn-sm" href="${exportC(rep, "xlsx", extra)}">Excel</a><a class="btn btn-sm" href="${exportC(rep, "pdf", extra)}">PDF</a></span>`;

async function inicioComp() {
  if (!requiereEmpresa()) return false;
  ctxC.corte = almacen.leer(`cp_corte_${estado.empresaId}`, "") || hoyISO();
  ctxC.rol = await vigente(api("/compensacion/mi-rol", { params: { empresa_id: estado.empresaId } }));
  return true;
}
function barraCorte(extra = "") {
  const r = ctxC.rol;
  return `<div class="ctx-bar"><label>Fecha de corte <input type="date" id="cp-corte" value="${ctxC.corte}" max="9999-12-31"></label>
    <span class="sub">Rol: <b>${r.modo_abierto ? "modo abierto (sin roles asignados)" : esc(ROLES_C[r.rol] || "sin rol")}</b></span>${extra}</div>`;
}
function enlazarCorte(alCambiar = navegar) {
  $("#cp-corte")?.addEventListener("change", (e) => {
    if (!e.target.value) return;
    ctxC.corte = e.target.value; almacen.guardar(`cp_corte_${estado.empresaId}`, ctxC.corte); alCambiar();
  });
}
function paginador(total, pagina, porPagina, ir) {
  const n = Math.max(1, Math.ceil(total / porPagina));
  const id = `pg${Math.random().toString(36).slice(2, 8)}`;
  setTimeout(() => {
    $(`#${id}-a`)?.addEventListener("click", () => ir(pagina - 1));
    $(`#${id}-s`)?.addEventListener("click", () => ir(pagina + 1));
  });
  return `<div class="paginacion"><span>${total} registros · página ${pagina} de ${n}</span>
    <button class="btn btn-sm" id="${id}-a" ${pagina <= 1 ? "disabled" : ""}>Anterior</button>
    <button class="btn btn-sm" id="${id}-s" ${pagina >= n ? "disabled" : ""}>Siguiente</button></div>`;
}

// ------------------------------------------------------------------ ejecución del motor
async function lanzarCompensacion(forzar = false) {
  const caja = $("#cp-prog");
  try {
    const r = await api("/compensacion/ejecuciones", { method: "POST", params: { empresa_id: estado.empresaId }, body: { fecha_corte: ctxC.corte, forzar } });
    if (r.reutilizado) { toast(`Sin cambios en datos ni reglas: se reutiliza la ejecución #${r.run_id}`, "ok"); return navegar(); }
    caja.innerHTML = `<div class="card">${barraProgreso(0, "En cola")}<div class="acciones"><button class="btn btn-sm btn-peligro" id="cp-cancel">Cancelar</button></div></div>`;
    $("#cp-cancel").onclick = async () => { try { await api(`/compensacion/ejecuciones/${r.run_id}/cancelar`, { method: "POST", params: { empresa_id: estado.empresaId } }); } catch (e) { toast(e.message, "err"); } };
    await esperarTrabajo(r.trabajo, (t) => {
      const b = $("#cp-prog .progreso"); if (!b) return;
      b.querySelector(".progreso-barra").style.width = `${Math.max(2, t.progreso)}%`;
      $("#cp-prog .progreso-txt").innerHTML = `<span>${esc(t.etapa)}</span><b>${t.progreso}%</b>`;
    });
    toast(`Ejecución #${r.run_id} completada`, "ok");
  } catch (e) { toast(e.message, "err"); }
  navegar();
}

// ------------------------------------------------------------------ dashboard
rutas["comp"] = async () => {
  if (!(await inicioComp())) return;
  const d = await vigente(api("/compensacion/dashboard", { params: qC() }));
  const conc = await vigente(api("/compensacion/conciliacion", { params: qC() }));
  const g = d.graficos, u = d.ultima_ejecucion;
  const tile = (l, v, sub = "", cls = "") => `<div class="kpi ${cls}"><div class="l">${l}</div><div class="v">${v}</div>${sub ? `<div class="l">${sub}</div>` : ""}</div>`;
  const cartera = (c, titulo) => {
    const k = d.kpi[c] || {};
    return `<div class="card"><h2>${titulo}</h2><div class="grid grid-4">
      ${tile("Partidas", k.partidas || 0)}${tile("Compensadas", k.compensadas || 0)}${tile("Parciales", k.parciales || 0)}${tile("Pendientes", k.pendientes || 0)}
      ${tile("Importe pendiente (MN)", num(k.importe_pendiente || 0))}${tile("Importe aplicado (MN)", num(k.importe_aplicado || 0))}
      ${tile("Vencidas", k.vencidos || 0)}${tile("Anticipos por aplicar", k.anticipos_pendientes || 0)}</div></div>`;
  };
  const mes = (f) => `${f.slice(5, 7)}/${f.slice(2, 4)}`;
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Compensación de partidas</h1><p class="sub">Compensación analítica: identifica qué documentos cancelan a cuáles sin modificar los asientos originales. La puntuación mide la calidad de la coincidencia, no una probabilidad.</p></div>
      <div class="acciones" style="margin:0">${puede("ejecutar") ? `<button class="btn btn-primario" id="cp-run">Ejecutar motor</button><button class="btn" id="cp-run-f" title="Recalcula aunque no haya cambios">Forzar</button>` : ""}</div></div>
    ${barraCorte()}
    <div id="cp-prog"></div>
    ${u ? `<div class="alerta ${u.estado === "COMPLETADO" ? "alerta-ok" : u.estado === "ERROR" ? "alerta-err" : "alerta-warn"}">Última ejecución #${u.id} · corte ${fecha(u.fecha_corte)} · ${esc(u.estado)} · ${u.duracion_ms ?? "—"} ms · ${esc(u.usuario)}
      ${u.resumen ? ` · ${u.resumen.propuestas || 0} propuestas, ${u.resumen.autoaprobadas || 0} aprobadas por política, ${u.resumen.ambiguas || 0} ambiguas` : ""}${u.error ? ` · ${esc(u.error)}` : ""}</div>`
      : `<div class="alerta alerta-info">Aún no se ejecutó el motor. Las partidas se construyen desde el libro diario importado.</div>`}
    <div class="alerta ${conc.conciliado ? "alerta-ok" : "alerta-err"}">${conc.conciliado ? "Las partidas abiertas concilian con el saldo contable ✓" : `<b>Diferencia con el saldo contable: ${num(conc.totales.diferencia)}</b> — revise la conciliación (no se generan ajustes).`}
      <a href="#/comp-conciliacion">Ver conciliación</a></div>
    <div class="grid grid-5">
      ${tile("Aprobadas por política", d.grupos.autoaprobadas)}${tile("Aprobadas manualmente", d.grupos.manuales_aprobadas)}
      ${tile("Propuestas por revisar", `<a href="#/comp-propuestas">${d.grupos.propuestas_pendientes}</a>`)}${tile("Revertidas", d.grupos.revertidas)}
      ${tile("Diferencias de cambio", num(d.diferencias_cambio), "identificadas, sin asiento")}${tile("Observaciones abiertas", `<a href="#/comp-conciliacion">${d.observaciones_abiertas}</a>`)}
    </div>
    <div class="grid grid-2" style="margin-top:16px">${cartera("CXC", "Cuentas por cobrar")}${cartera("CXP", "Cuentas por pagar")}</div>
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card"><h2>Antigüedad del saldo por pagar</h2>${graficoBarras(g.antiguedad.tramos.map((t, i) => ({ etiqueta: t, valor: Number(g.antiguedad.CXP[i]) })), { max: 20, color: SERIES[1] })}</div>
      <div class="card"><h2>Antigüedad del saldo por cobrar</h2>${graficoBarras(g.antiguedad.tramos.map((t, i) => ({ etiqueta: t, valor: Number(g.antiguedad.CXC[i]) })), { max: 20 })}</div>
      <div class="card"><h2>Evolución del saldo pendiente (fin de mes)</h2>${graficoLineas([{ nombre: "Por cobrar", valores: g.evolucion.map((e) => Number(e.CXC)) }, { nombre: "Por pagar", valores: g.evolucion.map((e) => Number(e.CXP)) }], g.evolucion.map((e) => mes(e.fecha)))}</div>
      <div class="card"><h2>Concentración de saldos por pagar</h2>${graficoBarras((g.concentracion.CXP || []).map((x) => ({ etiqueta: x.razon_social || x.tercero, detalle: x.tercero, valor: Number(x.importe) })), { max: 10 })}</div>
      <div class="card"><h2>Concentración de saldos por cobrar</h2>${graficoBarras((g.concentracion.CXC || []).map((x) => ({ etiqueta: x.razon_social || x.tercero, detalle: x.tercero, valor: Number(x.importe) })), { max: 10, color: SERIES[1] })}</div>
      <div class="card"><h2>Compensaciones por nivel de confianza</h2>${graficoBarras(Object.keys(CONF).map((c) => ({ etiqueta: CONF[c][0], valor: g.confianza[c] || 0 })), { colores: Object.values(CONF).map((x) => x[1]), etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Compensaciones aprobadas por periodo</h2>${graficoAgrupado(g.por_periodo.map((x) => ({ etiqueta: x.periodo, valores: [Number(x.automatica), Number(x.manual)] })), ["Automáticas", "Manuales"])}</div>
      <div class="card"><h2>Saldo pendiente por moneda (en su moneda)</h2>${graficoBarras(g.por_moneda.map((x) => ({ etiqueta: `${x.cartera === "CXC" ? "Por cobrar" : "Por pagar"} · ${x.moneda}`, valor: Number(x.importe) })))}</div>
    </div>`;
  enlazarCorte();
  $("#cp-run")?.addEventListener("click", () => lanzarCompensacion(false));
  $("#cp-run-f")?.addEventListener("click", () => lanzarCompensacion(true));
};

// ------------------------------------------------------------------ partidas abiertas
const fp = { pagina: 1, cuenta: "", tercero: "", rol: "", clase: "", moneda: "", estado_cancelacion: "", estado_vencimiento: "", texto: "", solo_pendientes: true };
rutas["comp-partidas"] = async () => {
  if (!(await inicioComp())) return;
  const sel = (id, ops, v) => `<select id="${id}"><option value="">Todos</option>${ops.map(([k, t]) => `<option value="${k}" ${k === v ? "selected" : ""}>${esc(t)}</option>`).join("")}</select>`;
  const r = await vigente(api("/compensacion/partidas", { params: qC({ ...fp, por_pagina: 100 }) }));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Partidas abiertas</h1><p class="sub">Composición del saldo a la fecha de corte. El estado de cancelación, el de vencimiento y el de revisión se muestran por separado.</p></div>${botonesC("partidas_abiertas")}</div>
    ${barraCorte()}
    <div class="filtros card">
      <label>Cuenta <input id="f-cuenta" value="${esc(fp.cuenta)}" size="8" placeholder="42"></label>
      <label>Tercero (RUC) <input id="f-tercero" value="${esc(fp.tercero)}" size="12"></label>
      <label>Buscar <input id="f-texto" value="${esc(fp.texto)}" placeholder="documento, glosa, razón social"></label>
      <label>Rol ${sel("f-rol", [["ORIGEN", "Documento (origen)"], ["APLICACION", "Cancelación (aplicación)"]], fp.rol)}</label>
      <label>Moneda ${sel("f-moneda", [["PEN", "PEN"], ["USD", "USD"], ["EUR", "EUR"]], fp.moneda)}</label>
      <label>Cancelación ${sel("f-canc", Object.entries(CANC).map(([k, v]) => [k, v[0]]), fp.estado_cancelacion)}</label>
      <label>Vencimiento ${sel("f-venc", Object.entries(VENC).map(([k, v]) => [k, v[0]]), fp.estado_vencimiento)}</label>
      <label class="check"><input type="checkbox" id="f-pend" ${fp.solo_pendientes ? "checked" : ""}> Solo con saldo pendiente</label>
      <button class="btn btn-sm btn-primario" id="f-ir">Filtrar</button></div>
    <div class="alerta alerta-info">Total: ${r.total} partidas · importe ${num(r.totales.importe_mn)} · pendiente con signo contable ${num(r.totales.pendiente_mn)} (MN)</div>
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Fecha</th><th>Cuenta</th><th>Tercero</th><th>Documento</th><th>Clase</th><th>Rol</th><th>Mon.</th>
      <th class="num">Importe</th><th class="num">Aplicado</th><th class="num">Propuesto</th><th class="num">Pendiente</th><th>Cancelación</th><th>Vencimiento</th><th>Revisión</th></tr></thead>
      <tbody>${r.items.map((p) => `<tr class="fila-click" data-id="${p.id}">
        <td class="nowrap">${fecha(p.fecha_contable)}</td><td>${esc(p.cuenta)}</td><td title="${esc(p.tercero || "")}">${esc(p.razon_social || p.tercero || "—")}</td>
        <td>${doc(p)}${p.origen_datos === "APERTURA_CONSOLIDADA" ? ' <span class="badge b-warn" title="Saldo inicial consolidado sin detalle documental">Pendiente de desagregación</span>' : ""}</td>
        <td>${esc(p.clase)}${p.clasificacion_pendiente ? ' <span class="badge b-warn" title="' + esc(p.clase_motivo || "") + '">Por revisar</span>' : ""}</td>
        <td>${p.rol === "ORIGEN" ? "Documento" : "Cancelación"}</td><td>${esc(p.moneda)}</td>
        <td class="num">${num(p.importe)}</td><td class="num">${num(p.aplicado)}</td><td class="num">${Number(p.propuesto) ? num(p.propuesto) : "—"}</td><td class="num"><b>${num(p.pendiente)}</b></td>
        <td>${chipB(CANC, p.estado_cancelacion)}</td><td>${chipB(VENC, p.estado_vencimiento)}${p.dias_vencido > 0 ? ` <span class="sub">${p.dias_vencido} d</span>` : ""}</td>
        <td>${p.estado_revision === "NINGUNA" ? "—" : esc(p.estado_revision)}</td></tr>`).join("") || `<tr><td colspan="14" class="vacio">Sin partidas para los filtros (¿ejecutó el motor?)</td></tr>`}</tbody></table></div>
    ${paginador(r.total, fp.pagina, 100, (p) => { fp.pagina = p; navegar(); })}`;
  enlazarCorte();
  $("#f-ir").onclick = () => {
    Object.assign(fp, { pagina: 1, cuenta: $("#f-cuenta").value.trim(), tercero: $("#f-tercero").value.trim(), texto: $("#f-texto").value.trim(), rol: $("#f-rol").value,
      moneda: $("#f-moneda").value, estado_cancelacion: $("#f-canc").value, estado_vencimiento: $("#f-venc").value, solo_pendientes: $("#f-pend").checked });
    navegar();
  };
  $$(".fila-click").forEach((tr) => tr.addEventListener("click", () => detallePartida(Number(tr.dataset.id))));
};

async function detallePartida(id) {
  try {
    const d = await api(`/compensacion/partidas/${id}`, { params: qC() });
    const p = d.partida;
    abrirModal(`Partida ${p.documento || id} · ${p.cuenta}`, `
      ${d.posterior_al_corte ? '<div class="alerta alerta-warn">La partida es posterior a la fecha de corte.</div>' : ""}
      <div class="grid grid-4">
        <div><div class="sub">Tercero</div>${esc(p.razon_social || "")} ${esc(p.tercero || "")}</div><div><div class="sub">Clase</div>${esc(p.clase)} (${p.clase_confianza ?? "—"}) <div class="sub">${esc(p.clase_motivo || "")}</div></div>
        <div><div class="sub">Origen de datos</div>${esc(p.origen_datos)} · lote ${p.lote_id ?? "—"} · asiento ${esc(p.subdiario || "")}-${esc(p.numero_asiento || "")}</div>
        <div><div class="sub">Fechas</div>doc. ${fecha(p.fecha_documento)} · cont. ${fecha(p.fecha_contable)} · venc. ${fecha(p.fecha_vencimiento)}</div>
        <div><div class="sub">Saldo original</div><b>${num(p.importe)} ${esc(p.moneda)}</b> (MN ${num(p.importe_mn)})</div><div><div class="sub">Aplicado</div>${num(p.aplicado)}</div>
        <div><div class="sub">Pendiente</div><b>${num(p.pendiente)}</b></div><div><div class="sub">Referencia</div>${esc(p.documento_referencia || "—")}</div></div>
      <h3>Aplicaciones (trazabilidad)</h3>
      <table class="tabla"><thead><tr><th>Grupo</th><th>Contraparte</th><th>Clase</th><th>Fecha efectiva</th><th class="num">Importe</th><th class="num">Dif. cambio</th><th>Regla</th><th>Punt.</th><th>Usuario</th><th>Estado</th></tr></thead>
      <tbody>${d.aplicaciones.map((a) => `<tr><td><a href="#" data-grupo="${a.grupo_id}">#${a.grupo_id}</a></td><td>${esc(a.contraparte.documento || "s/doc.")} (${esc(a.contraparte.cuenta)})</td><td>${esc(a.contraparte.clase)}</td>
        <td>${fecha(a.fecha_efectiva)}</td><td class="num">${num(a.importe)}</td><td class="num">${Number(a.diferencia_cambio) ? num(a.diferencia_cambio) : "—"}</td><td>${esc(a.regla || "")}</td><td>${a.puntuacion ?? "—"}</td><td>${esc(a.usuario)}</td><td>${chipB(EST_G, a.estado)}</td></tr>`).join("") || '<tr><td colspan="10" class="vacio">Sin aplicaciones</td></tr>'}</tbody></table>
      <h3>Líneas del libro que la originan</h3>
      <table class="tabla"><thead><tr><th>Tipo de fuente</th><th>Identificador</th><th class="num">Importe MN</th><th class="num">Importe ME</th></tr></thead>
      <tbody>${d.fuentes.map((f) => `<tr><td>${esc(f.tipo_fuente)}</td><td>${f.fuente_id ?? "—"}</td><td class="num">${num(f.importe_mn)}</td><td class="num">${Number(f.importe_me) ? num(f.importe_me) : "—"}</td></tr>`).join("") || '<tr><td colspan="4" class="vacio">Saldo inicial sin líneas de detalle</td></tr>'}</tbody></table>
      ${d.observaciones.length ? `<h3>Observaciones</h3>${d.observaciones.map((o) => `<div class="alerta alerta-warn"><b>${esc(o.codigo)}</b> ${esc(o.titulo)} · ${esc(o.estado)}</div>`).join("")}` : ""}`);
    $$("[data-grupo]", $("#modal-cuerpo")).forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); detalleGrupo(Number(a.dataset.grupo)); }));
  } catch (e) { toast(e.message, "err"); }
}

// ------------------------------------------------------------------ compensación manual (doble panel)
const man = { izq: new Map(), der: new Map(), filtros: { izq: { rol: "ORIGEN", texto: "", tercero: "", cuenta: "" }, der: { rol: "APLICACION", texto: "", tercero: "", cuenta: "" } }, datos: { izq: [], der: [] } };
rutas["comp-manual"] = async () => {
  if (!(await inicioComp())) return;
  if (!puede("proponer")) { vista().innerHTML = `<div class="alerta alerta-warn">Su rol no permite proponer compensaciones.</div>`; return; }
  const panel = (lado, titulo) => {
    const f = man.filtros[lado];
    return `<div class="card"><h2>${titulo}</h2>
      <div class="filtros"><label>Cuenta <input data-f="cuenta" data-lado="${lado}" value="${esc(f.cuenta)}" size="6"></label>
        <label>Tercero <input data-f="tercero" data-lado="${lado}" value="${esc(f.tercero)}" size="11"></label>
        <label>Buscar <input data-f="texto" data-lado="${lado}" value="${esc(f.texto)}" size="14"></label>
        <label>Rol <select data-f="rol" data-lado="${lado}"><option value="">Todos</option><option value="ORIGEN" ${f.rol === "ORIGEN" ? "selected" : ""}>Documentos</option><option value="APLICACION" ${f.rol === "APLICACION" ? "selected" : ""}>Cancelaciones</option></select></label>
        <button class="btn btn-sm" data-buscar="${lado}">Buscar</button></div>
      <div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th></th><th>Fecha</th><th>Cuenta</th><th>Tercero</th><th>Documento</th><th>Mon.</th><th class="num">Disponible</th><th class="num">Aplicar</th></tr></thead>
      <tbody id="tb-${lado}"></tbody></table></div></div>`;
  };
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Compensación manual</h1><p class="sub">Seleccione a la izquierda los documentos y a la derecha lo que los cancela. Puede aplicar importes parciales. La propuesta queda pendiente de aprobación.</p></div></div>
    ${barraCorte()}
    <div class="grid grid-2">${panel("izq", "Documentos a cancelar")}${panel("der", "Pagos, notas de crédito, anticipos…")}</div>
    <div class="card" style="margin-top:16px"><h2>Vista previa</h2><div id="mn-prev" class="sub">Seleccione partidas en ambos paneles.</div>
      <div class="form-grid" style="margin-top:12px">
        <label class="campo" style="grid-column:1/-1">Justificación / comentario<textarea id="mn-just" rows="2" maxlength="4000" placeholder="Obligatoria para compensaciones entre terceros, entre monedas o con partidas por clasificar"></textarea></label>
        <label class="campo">Tipo de cambio (solo entre monedas) <input id="mn-tc" type="number" step="0.000001" min="0"></label>
        <label class="check"><input type="checkbox" id="mn-ter"> Autorizo compensar entre terceros distintos (requiere rol autorizado y sustento)</label></div>
      <div class="acciones"><button class="btn" id="mn-ver">Ver antes / después</button><button class="btn btn-primario" id="mn-ok">Proponer compensación</button><button class="btn" id="mn-limpiar">Limpiar selección</button></div></div>`;
  enlazarCorte();
  const pintar = (lado) => {
    const sel = man[lado];
    $(`#tb-${lado}`).innerHTML = man.datos[lado].map((p) => {
      const s = sel.get(p.id);
      return `<tr><td><input type="checkbox" data-sel="${lado}" data-id="${p.id}" ${s ? "checked" : ""}></td><td class="nowrap">${fecha(p.fecha_contable)}</td><td>${esc(p.cuenta)}</td>
        <td title="${esc(p.tercero || "")}">${esc(p.razon_social || p.tercero || "—")}</td><td>${doc(p)}<div class="sub">${esc(p.clase)}</div></td><td>${esc(p.moneda)}</td><td class="num">${num(p.disponible)}</td>
        <td class="num"><input class="inp-imp" type="number" step="0.01" min="0.01" max="${p.disponible}" data-imp="${lado}" data-id="${p.id}" value="${s ? s.importe : ""}" ${s ? "" : "disabled"} style="width:88px"></td></tr>`;
    }).join("") || `<tr><td colspan="8" class="vacio">Sin partidas disponibles</td></tr>`;
    $$(`[data-sel="${lado}"]`).forEach((c) => c.addEventListener("change", () => {
      const p = man.datos[lado].find((x) => x.id === Number(c.dataset.id));
      if (c.checked) sel.set(p.id, { item_id: p.id, importe: p.disponible }); else sel.delete(p.id);
      pintar(lado); resumen();
    }));
    $$(`[data-imp="${lado}"]`).forEach((i) => i.addEventListener("input", () => { const s = sel.get(Number(i.dataset.id)); if (s) s.importe = i.value; resumen(); }));
  };
  const resumen = () => {
    const t = (m) => [...m.values()].reduce((a, s) => a + Number(s.importe || 0), 0);
    const a = t(man.izq), b = t(man.der);
    $("#mn-prev").innerHTML = `Izquierda: <b>${num(a)}</b> (${man.izq.size}) · Derecha: <b>${num(b)}</b> (${man.der.size}) · ${Math.abs(a - b) < 0.005 && a > 0 ? '<span class="badge b-ok">Cuadra</span>' : '<span class="badge b-warn">Los totales deben coincidir</span>'}`;
  };
  const cargar = async (lado) => {
    const f = man.filtros[lado];
    const r = await api("/compensacion/partidas", { params: qC({ ...f, solo_disponibles: true, por_pagina: 300 }) });
    man.datos[lado] = r.items; pintar(lado);
  };
  $$("[data-buscar]").forEach((b) => b.addEventListener("click", () => {
    const lado = b.dataset.buscar;
    $$(`[data-lado="${lado}"]`).forEach((i) => { man.filtros[lado][i.dataset.f] = i.value.trim(); });
    cargar(lado).catch((e) => toast(e.message, "err"));
  }));
  const cuerpo = () => ({ izquierda: [...man.izq.values()], derecha: [...man.der.values()], justificacion: $("#mn-just").value.trim(),
    autorizar_terceros: $("#mn-ter").checked, tipo_cambio: $("#mn-tc").value || null, fecha_corte: ctxC.corte });
  $("#mn-ver").onclick = async () => {
    try {
      const v = await api("/compensacion/vista-previa", { method: "POST", params: { empresa_id: estado.empresaId }, body: cuerpo() });
      $("#mn-prev").innerHTML = `<table class="tabla"><thead><tr><th>Panel</th><th>Documento</th><th class="num">Disponible antes</th><th class="num">Aplicar</th><th class="num">Disponible después</th><th>Estado resultante</th></tr></thead>
        <tbody>${v.vista.map((x) => `<tr><td>${x.panel === "izquierda" ? "Izquierda" : "Derecha"}</td><td>${esc(x.documento || "s/doc.")}</td><td class="num">${num(x.disponible_antes)}</td><td class="num">${num(x.aplicar)}</td><td class="num">${num(x.disponible_despues)}</td><td>${chipB(CANC, x.estado_despues)}</td></tr>`).join("")}</tbody></table>
        <div class="sub">Total ${num(v.total)} ${esc(v.moneda)}${v.entre_terceros ? " · entre terceros" : ""}${v.entre_cuentas ? " · entre cuentas (regla autorizada)" : ""}</div>`;
    } catch (e) { $("#mn-prev").innerHTML = `<div class="alerta alerta-err">${esc(e.message)}</div>`; }
  };
  $("#mn-ok").onclick = async () => {
    try {
      const g = await api("/compensacion/grupos", { method: "POST", params: { empresa_id: estado.empresaId }, body: cuerpo() });
      toast(`Propuesta #${g.id} registrada; queda pendiente de aprobación`, "ok");
      man.izq.clear(); man.der.clear(); await Promise.all([cargar("izq"), cargar("der")]); resumen();
    } catch (e) { toast(e.message, "err"); }
  };
  $("#mn-limpiar").onclick = () => { man.izq.clear(); man.der.clear(); pintar("izq"); pintar("der"); resumen(); };
  await Promise.all([cargar("izq"), cargar("der")]);
  resumen();
};

// ------------------------------------------------------------------ propuestas, aprobaciones y ambiguas
const fg = { pestana: "PROPUESTA", pagina: 1, confianza: "", origen: "", tercero: "" };
rutas["comp-propuestas"] = async () => {
  if (!(await inicioComp())) return;
  const pest = [["PROPUESTA", "Por aprobar"], ["AMBIGUAS", "Ambiguas (requieren decisión)"], ["APROBADA", "Aprobadas"], ["REVERTIDA", "Revertidas"], ["RECHAZADA", "Rechazadas"]];
  const cab = `<div class="cab-vista"><div><h1>Propuestas y aprobaciones</h1><p class="sub">Las coincidencias ambiguas nunca se aprueban solas. Quien propone no puede aprobar su propia propuesta cuando la separación de funciones está activa.</p></div>
    ${fg.pestana === "APROBADA" ? botonesC("compensaciones_aprobadas") : fg.pestana === "REVERTIDA" ? botonesC("compensaciones_revertidas") : botonesC("compensaciones_propuestas")}</div>
    <div class="pestanas">${pest.map(([k, t]) => `<button class="btn ${fg.pestana === k ? "btn-primario" : ""}" data-pest="${k}">${t}</button>`).join("")}</div>`;
  if (fg.pestana === "AMBIGUAS") {
    const r = await vigente(api("/compensacion/candidatos", { params: { empresa_id: estado.empresaId, por_pagina: 200 } }));
    vista().innerHTML = cab + `<div class="alerta alerta-info">${r.total} casos con más de una alternativa válida. Elija la alternativa sustentada (p. ej., según el voucher) e indique la justificación.</div>
      ${r.items.map((c) => {
        const alts = (c.componentes.alternativas || []);
        const apl = c.aplicaciones.map((a) => `${esc(c.partidas[a.item_id]?.documento || "s/doc.")} ${esc(c.partidas[a.item_id]?.clase || "")} ${num(a.importe)}`).join(", ");
        return `<div class="card" style="margin-bottom:12px"><h3>Caso #${c.id} · ${esc(c.cuenta)} · ${esc(c.tercero || "")} · ${num(c.importe)} ${esc(c.moneda)}</h3>
          <p>Cancelación: <b>${apl}</b>. ${esc((c.componentes.bloqueos || []).join(" · "))}</p>
          <table class="tabla"><thead><tr><th>Opción</th><th>Documentos</th><th></th></tr></thead><tbody>
          ${alts.map((a, i) => `<tr><td>${i + 1}</td><td>${a.origenes.map((id) => `${esc(c.partidas[id]?.documento || id)} (${fecha(c.partidas[id]?.fecha)} · ${num(c.partidas[id]?.importe)})`).join(" + ")}</td>
            <td>${puede("proponer") ? `<button class="btn btn-sm" data-resolver="${c.id}" data-op="${i}">Elegir</button>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
      }).join("") || '<div class="vacio">No hay coincidencias ambiguas pendientes.</div>'}`;
    $$("[data-resolver]").forEach((b) => b.addEventListener("click", async () => {
      const j = prompt("Justificación de la elección (obligatoria):");
      if (!j || j.trim().length < 5) return toast("Indique una justificación", "err");
      try { const g = await api(`/compensacion/candidatos/${b.dataset.resolver}/resolver`, { method: "POST", params: { empresa_id: estado.empresaId }, body: { opcion: Number(b.dataset.op), justificacion: j.trim() } }); toast(`Propuesta #${g.id} creada`, "ok"); navegar(); } catch (e) { toast(e.message, "err"); }
    }));
  } else {
    const r = await vigente(api("/compensacion/grupos", { params: { empresa_id: estado.empresaId, estado: fg.pestana, confianza: fg.confianza, origen: fg.origen, tercero: fg.tercero, pagina: fg.pagina, por_pagina: 100 } }));
    const lote = fg.pestana === "PROPUESTA" && puede("aprobar");
    vista().innerHTML = cab + `
      <div class="filtros card"><label>Confianza <select id="g-conf"><option value="">Todas</option>${Object.entries(CONF).map(([k, v]) => `<option value="${k}" ${fg.confianza === k ? "selected" : ""}>${v[0]}</option>`).join("")}</select></label>
        <label>Origen <select id="g-orig"><option value="">Todos</option><option value="AUTOMATICA" ${fg.origen === "AUTOMATICA" ? "selected" : ""}>Motor</option><option value="MANUAL" ${fg.origen === "MANUAL" ? "selected" : ""}>Manual</option></select></label>
        <label>Tercero <input id="g-ter" value="${esc(fg.tercero)}" size="12"></label><button class="btn btn-sm btn-primario" id="g-ir">Filtrar</button>
        ${lote ? '<button class="btn btn-sm" id="g-lote">Aprobar seleccionadas</button>' : ""}</div>
      <div class="tabla-wrap"><table class="tabla"><thead><tr>${lote ? '<th><input type="checkbox" id="g-todas"></th>' : ""}<th>#</th><th>Modalidad</th><th>Cuenta</th><th>Tercero</th><th class="num">Importe</th><th>Mon.</th><th>Fecha efectiva</th><th>Nivel</th><th>Confianza</th><th>Regla</th><th>Propuesto por</th><th>Estado</th></tr></thead>
      <tbody>${r.items.map((g) => `<tr class="fila-click" data-g="${g.id}">${lote ? `<td><input type="checkbox" class="g-sel" value="${g.id}" ${g.ambiguo || (g.componentes?.bloqueos || []).length ? "" : ""}></td>` : ""}
        <td>${g.id}</td><td>${modalidadTxt(g.modalidad)}${g.entre_cuentas ? ' <span class="badge b-info">entre cuentas</span>' : ""}${g.entre_terceros ? ' <span class="badge b-warn">entre terceros</span>' : ""}</td>
        <td>${esc(g.cuenta)}</td><td>${esc(g.tercero)}</td><td class="num">${num(g.importe)}</td><td>${esc(g.moneda)}</td><td>${fecha(g.fecha_efectiva)}</td><td>N${g.nivel}</td>
        <td>${chipConf(g.confianza, g.puntuacion)}${(g.componentes?.bloqueos || []).length ? ' <span class="badge b-err" title="' + esc(g.componentes.bloqueos.join(" · ")) + '">Requiere sustento</span>' : ""}</td>
        <td>${esc(g.regla || "")}</td><td>${esc(g.propuesto_por)}</td><td>${chipB(EST_G, g.estado)}</td></tr>`).join("") || `<tr><td colspan="13" class="vacio">Sin compensaciones</td></tr>`}</tbody></table></div>
      ${paginador(r.total, fg.pagina, 100, (p) => { fg.pagina = p; navegar(); })}`;
    $("#g-ir").onclick = () => { Object.assign(fg, { pagina: 1, confianza: $("#g-conf").value, origen: $("#g-orig").value, tercero: $("#g-ter").value.trim() }); navegar(); };
    $("#g-todas")?.addEventListener("change", (e) => $$(".g-sel").forEach((c) => { c.checked = e.target.checked; }));
    $$(".g-sel").forEach((c) => c.addEventListener("click", (e) => e.stopPropagation()));
    $("#g-lote")?.addEventListener("click", async () => {
      const ids = $$(".g-sel").filter((c) => c.checked).map((c) => Number(c.value));
      if (!ids.length) return toast("Seleccione compensaciones", "err");
      try {
        const r2 = await api("/compensacion/grupos/aprobar-lote", { method: "POST", params: { empresa_id: estado.empresaId }, body: { grupos: ids, comentario: "Aprobación en lote" } });
        toast(`${r2.aprobadas.length} aprobadas${r2.errores.length ? ` · ${r2.errores.length} con error: ${r2.errores.map((x) => `#${x.grupo} ${x.error}`).join("; ")}` : ""}`, r2.errores.length ? "err" : "ok");
        navegar();
      } catch (e) { toast(e.message, "err"); }
    });
    $$(".fila-click").forEach((tr) => tr.addEventListener("click", () => detalleGrupo(Number(tr.dataset.g))));
  }
  $$("[data-pest]").forEach((b) => b.addEventListener("click", () => { fg.pestana = b.dataset.pest; fg.pagina = 1; navegar(); }));
};

async function detalleGrupo(id) {
  try {
    const g = await api(`/compensacion/grupos/${id}`, { params: { empresa_id: estado.empresaId } });
    const comp = g.componentes || {};
    const pts = Object.entries(comp).filter(([k, v]) => typeof v === "number").map(([k, v]) => `${esc(k)} ${v > 0 ? "+" : ""}${v}`).join(" · ");
    const cuerpo = abrirModal(`Compensación #${g.id} · ${modalidadTxt(g.modalidad)}`, `
      <div class="grid grid-4"><div><div class="sub">Estado</div>${chipB(EST_G, g.estado)}</div><div><div class="sub">Confianza</div>${chipConf(g.confianza, g.puntuacion)}<div class="sub">${pts}</div></div>
        <div><div class="sub">Regla</div>${esc(g.regla || "")} v${g.regla_version ?? "—"} · N${g.nivel}</div><div><div class="sub">Importe</div><b>${num(g.importe)} ${esc(g.moneda)}</b> · efectiva ${fecha(g.fecha_efectiva)}</div></div>
      ${(comp.bloqueos || []).length ? `<div class="alerta alerta-err">Requiere sustento antes de aprobar: ${comp.bloqueos.map(esc).join(" · ")}</div>` : ""}
      ${g.justificacion ? `<div class="alerta alerta-info">Justificación: ${esc(g.justificacion)}</div>` : ""}
      <table class="tabla"><thead><tr><th>Documento (origen)</th><th>Cancelación (aplicación)</th><th class="num">Importe</th><th>Mon.</th><th>T.C.</th><th class="num">MN origen</th><th class="num">MN aplicación</th><th class="num">Dif. cambio</th><th>Estado</th></tr></thead>
      <tbody>${g.aplicaciones.map((a) => `<tr><td>${esc(a.origen.documento || "s/doc.")} · ${esc(a.origen.clase)} · ${fecha(a.origen.fecha)}<div class="sub">${esc(a.origen.cuenta)} · línea ${a.origen.linea_id ?? "—"}</div></td>
        <td>${esc(a.aplicacion.documento || "s/doc.")} · ${esc(a.aplicacion.clase)} · ${fecha(a.aplicacion.fecha)}<div class="sub">${esc(a.aplicacion.cuenta)} · línea ${a.aplicacion.linea_id ?? "—"}</div></td>
        <td class="num">${num(a.importe)}</td><td>${esc(a.moneda)}</td><td>${a.tipo_cambio ?? "—"}</td><td class="num">${num(a.importe_mn_origen)}</td><td class="num">${num(a.importe_mn_aplicacion)}</td><td class="num">${Number(a.diferencia_cambio) ? num(a.diferencia_cambio) : "—"}</td><td>${chipB(EST_G, a.estado)}</td></tr>`).join("")}</tbody></table>
      <h3>Historial</h3><ul>${[`Propuesta por ${esc(g.propuesto_por)} (${g.origen_propuesta === "AUTOMATICA" ? "motor" : "manual"}) el ${fechaHora(g.creado_en)}`,
        ...g.aprobaciones.map((x) => `${esc(x.accion)} por ${esc(x.usuario)} el ${fechaHora(x.creado_en)}${x.comentario ? ` — ${esc(x.comentario)}` : ""}`),
        ...g.reversiones.map((x) => `REVERSIÓN por ${esc(x.usuario)} el ${fechaHora(x.creado_en)} — ${esc(x.motivo)}`)].map((t) => `<li>${t}</li>`).join("")}</ul>
      <h3>Comentarios</h3>${g.comentarios.map((c) => `<div class="obs-mini"><b>${esc(c.usuario)}</b> · ${fechaHora(c.creado_en)}<br>${esc(c.texto)}</div>`).join("") || '<div class="sub">Sin comentarios</div>'}
      <div class="acciones"><input id="gd-com" placeholder="Agregar comentario" style="flex:1"><button class="btn btn-sm" id="gd-com-ok">Comentar</button></div>
      <h3>Sustentos adjuntos</h3>${g.adjuntos.map((a) => `<div><a href="/api/compensacion/grupos/${g.id}/adjuntos/${a.id}?empresa_id=${estado.empresaId}">${esc(a.nombre)}</a> · ${esc(a.usuario)} · ${fechaHora(a.creado_en)}</div>`).join("") || '<div class="sub">Sin adjuntos</div>'}
      <div class="acciones"><input type="file" id="gd-adj"><button class="btn btn-sm" id="gd-adj-ok">Adjuntar</button></div>
      <label class="campo" style="display:block;margin-top:14px">Comentario de la decisión (obligatorio para revertir)<textarea id="gd-dec" rows="2" style="width:100%;display:block;margin-top:4px"></textarea></label>
      <div class="acciones">
        ${g.estado === "PROPUESTA" && puede("aprobar") ? '<button class="btn btn-primario" id="gd-apr">Aprobar</button><button class="btn" id="gd-rech">Rechazar</button>' : ""}
        ${g.estado === "APROBADA" && puede("revertir") ? '<button class="btn btn-peligro" id="gd-rev">Revertir</button>' : ""}</div>`);
    const accion = async (ruta, cuerpoReq) => {
      try { await api(`/compensacion/grupos/${g.id}/${ruta}`, { method: "POST", params: { empresa_id: estado.empresaId }, body: cuerpoReq }); toast("Registrado", "ok"); cerrarModal(); navegar(); } catch (e) { toast(e.message, "err"); }
    };
    $("#gd-apr", cuerpo)?.addEventListener("click", () => accion("aprobar", { comentario: $("#gd-dec").value.trim() || null }));
    $("#gd-rech", cuerpo)?.addEventListener("click", () => accion("rechazar", { comentario: $("#gd-dec").value.trim() || null }));
    $("#gd-rev", cuerpo)?.addEventListener("click", () => { if (confirm("La reversión deja la compensación en el historial y libera los saldos. ¿Continuar?")) accion("revertir", { comentario: $("#gd-dec").value.trim() }); });
    $("#gd-com-ok", cuerpo).onclick = async () => {
      const t = $("#gd-com").value.trim(); if (!t) return;
      try { await api(`/compensacion/grupos/${g.id}/comentarios`, { method: "POST", params: { empresa_id: estado.empresaId }, body: { texto: t } }); detalleGrupo(g.id); } catch (e) { toast(e.message, "err"); }
    };
    $("#gd-adj-ok", cuerpo).onclick = async () => {
      const f = $("#gd-adj").files[0]; if (!f) return;
      const fd = new FormData(); fd.append("archivo", f);
      try { await api(`/compensacion/grupos/${g.id}/adjuntos`, { method: "POST", params: { empresa_id: estado.empresaId }, form: fd }); detalleGrupo(g.id); } catch (e) { toast(e.message, "err"); }
    };
  } catch (e) { toast(e.message, "err"); }
}

// ------------------------------------------------------------------ anticipos y tributos
rutas["comp-anticipos"] = async () => {
  if (!(await inicioComp())) return;
  const l = await vigente(api("/compensacion/anticipos", { params: qC() }));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Anticipos y fondos por aplicar</h1><p class="sub">Anticipos de clientes, a proveedores, entregas a rendir y pagos aún no aplicados a un documento.</p></div>${botonesC("anticipos")}</div>
    ${barraCorte()}
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Tipo</th><th>Fecha</th><th>Cuenta</th><th>Tercero</th><th>Documento</th><th>Mon.</th><th class="num">Importe</th><th class="num">Aplicado</th><th class="num">Pendiente</th><th class="num">Días</th><th>Documentos relacionados</th><th>Ej. anterior</th></tr></thead>
    <tbody>${l.map((a) => `<tr class="fila-click" data-id="${a.id}"><td>${esc(a.tipo_anticipo)}</td><td>${fecha(a.fecha_contable)}</td><td>${esc(a.cuenta)}</td><td>${esc(a.razon_social || a.tercero || "—")}</td><td>${doc(a)}</td><td>${esc(a.moneda)}</td>
      <td class="num">${num(a.importe)}</td><td class="num">${num(a.aplicado)}</td><td class="num"><b>${num(a.pendiente)}</b></td><td class="num">${a.antiguedad_dias}</td><td>${a.relacionados.length ? a.relacionados.map((r) => `#${r.grupo_id} ${num(r.importe)} (${esc(r.estado)})`).join(", ") : "—"}</td><td>${a.ejercicio_anterior ? "Sí" : ""}</td></tr>`).join("") || '<tr><td colspan="12" class="vacio">Sin anticipos pendientes</td></tr>'}</tbody></table></div>`;
  enlazarCorte();
  $$(".fila-click").forEach((tr) => tr.addEventListener("click", () => detallePartida(Number(tr.dataset.id))));
};

rutas["comp-tributos"] = async () => {
  if (!(await inicioComp())) return;
  const t = await vigente(api("/compensacion/tributos", { params: qC() }));
  const tabla = (lista) => `<div class="tabla-wrap"><table class="tabla"><thead><tr><th>Fecha</th><th>Lado</th><th>Tercero</th><th>Comprobante / constancia</th><th>Código</th><th>Documentos relacionados</th><th class="num">Importe doc.</th><th class="num">Importe</th><th class="num">Pendiente</th><th>Revisión</th></tr></thead>
    <tbody>${lista.map((x) => `<tr class="fila-click" data-id="${x.id}"><td>${fecha(x.fecha_contable)}</td><td>${esc(x.lado_tributario)}</td><td>${esc(x.razon_social || x.tercero || "—")}</td><td>${doc(x)} ${esc(x.constancia_detraccion || "")}</td><td>${esc(x.codigo_detraccion || "—")}</td>
      <td>${x.documentos_relacionados.map(esc).join(", ") || "—"}</td><td class="num">${x.importe_documento ? num(x.importe_documento) : "—"}</td><td class="num">${num(x.importe)}</td><td class="num">${num(x.pendiente)}</td>
      <td>${x.pendiente_revision ? `<span class="badge b-warn" title="${esc(x.observaciones.map((o) => o.titulo).join(" · "))}">Pendiente de sustento</span>` : '<span class="badge b-ok">Sustentado</span>'}</td></tr>`).join("") || '<tr><td colspan="10" class="vacio">Sin registros</td></tr>'}</tbody></table></div>`;
  vista().innerHTML = `<div class="cab-vista"><div><h1>Detracciones, retenciones y percepciones</h1><p class="sub">No se asume una tasa universal: las tasas y vigencias se configuran por código. Sin constancia o comprobante, el tributo no se trata como cancelación sustentada.</p></div>
      <span>${botonesC("detracciones")} ${botonesC("retenciones")}</span></div>
    ${barraCorte()}
    <div class="card"><h2>Detracciones (${t.DETRACCION.length})</h2>${tabla(t.DETRACCION)}</div>
    <div class="card"><h2>Retenciones (${t.RETENCION.length})</h2>${tabla(t.RETENCION)}</div>
    <div class="card"><h2>Percepciones (${t.PERCEPCION.length})</h2>${tabla(t.PERCEPCION)}</div>`;
  enlazarCorte();
  $$(".fila-click").forEach((tr) => tr.addEventListener("click", () => detallePartida(Number(tr.dataset.id))));
};

// ------------------------------------------------------------------ conciliación y observaciones
rutas["comp-conciliacion"] = async () => {
  if (!(await inicioComp())) return;
  const [c, o] = await vigente(Promise.all([api("/compensacion/conciliacion", { params: qC() }),
    api("/compensacion/observaciones", { params: { empresa_id: estado.empresaId, por_pagina: 300 } })]));
  const cols = [["saldo_contable", "Saldo contable"], ["origen", "Documentos pendientes"], ["aplicacion", "Cancelaciones por aplicar"], ["sin_detalle", "Saldo inicial sin detalle"],
    ["no_clasificado", "Partidas por clasificar"], ["diferencia_cambio_aplicaciones", "Dif. de cambio identificada"], ["partidas_netas", "Total explicado"], ["diferencia", "Diferencia"]];
  vista().innerHTML = `<div class="cab-vista"><div><h1>Conciliación con el saldo contable</h1><p class="sub">${esc(c.nota)}</p></div>${botonesC("conciliacion")}</div>
    ${barraCorte()}
    <div class="alerta ${c.conciliado ? "alerta-ok" : "alerta-err"}">${c.conciliado ? "Todas las cuentas concilian ✓" : `Diferencia total: <b>${num(c.totales.diferencia)}</b>. Se muestra sin ajustes para su análisis.`}</div>
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Cuenta</th>${cols.map(([, t]) => `<th class="num">${t}</th>`).join("")}<th></th></tr></thead>
    <tbody>${c.cuentas.map((f) => `<tr><td>${esc(f.cuenta)}</td>${cols.map(([k]) => `<td class="num ${k === "diferencia" && Number(f[k]) ? "neg" : ""}">${num(f[k])}</td>`).join("")}<td>${f.conciliado ? '<span class="badge b-ok">OK</span>' : '<span class="badge b-err">Diferencia</span>'}</td></tr>`).join("")}
      <tr><th>Total</th>${cols.map(([k]) => `<th class="num">${num(c.totales[k])}</th>`).join("")}<th></th></tr></tbody></table></div>
    <div class="card" style="margin-top:16px"><h2>Observaciones del motor (${o.total})</h2>
      <div class="chips">${Object.entries(o.por_codigo).map(([k, n]) => `<span class="chip"><b>${n}</b> ${esc(k)}</span>`).join("")}</div>
      <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Código</th><th>Observación</th><th class="num">Importe</th><th>Estado</th><th>Responsable</th><th></th></tr></thead>
      <tbody>${o.items.map((x) => `<tr><td>${esc(x.codigo)}</td><td>${esc(x.titulo)}${x.item_id ? ` <a href="#" data-item="${x.item_id}">ver partida</a>` : ""}</td><td class="num">${num(x.importe)}</td><td>${esc(x.estado)}</td><td>${esc(x.responsable || "—")}</td>
        <td>${puede("revisar") ? `<select data-obs="${x.id}"><option value="">Cambiar…</option><option value="EN_REVISION">En revisión</option><option value="RESUELTA">Resuelta</option><option value="DESCARTADA">Descartada</option><option value="ABIERTA">Reabrir</option></select>` : ""}</td></tr>`).join("") || '<tr><td colspan="6" class="vacio">Sin observaciones</td></tr>'}</tbody></table></div></div>`;
  enlazarCorte();
  $$("[data-item]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); detallePartida(Number(a.dataset.item)); }));
  $$("[data-obs]").forEach((s) => s.addEventListener("change", async () => {
    if (!s.value) return;
    const com = prompt("Comentario de la revisión:") || null;
    try { await api(`/compensacion/observaciones/${s.dataset.obs}`, { method: "PATCH", params: { empresa_id: estado.empresaId }, body: { estado: s.value, responsable: usuario(), comentario: com } }); toast("Observación actualizada", "ok"); navegar(); } catch (e) { toast(e.message, "err"); }
  }));
};

// ------------------------------------------------------------------ antigüedad real y reportes
const fa = { base: "VENCIMIENTO", agrupar: "tercero", cuenta: "" };
rutas["comp-reportes"] = async () => {
  if (!(await inicioComp())) return;
  const a = await vigente(api("/compensacion/antiguedad", { params: qC(fa) }));
  const nombres = { partidas_abiertas: "Partidas abiertas", partidas_compensadas: "Partidas compensadas", aplicaciones_parciales: "Aplicaciones parciales",
    pendientes_tercero: "Saldos pendientes por tercero", antiguedad: "Antigüedad de saldos", compensaciones_propuestas: "Compensaciones propuestas",
    compensaciones_aprobadas: "Compensaciones aprobadas", compensaciones_revertidas: "Compensaciones revertidas", anticipos: "Anticipos pendientes",
    detracciones: "Detracciones", retenciones: "Retenciones", diferencias_cambio: "Diferencias de cambio", saldos_historicos: "Saldos históricos a la fecha de corte",
    conciliacion: "Conciliación con el saldo contable" };
  vista().innerHTML = `<div class="cab-vista"><div><h1>Antigüedad real y reportes</h1><p class="sub">La antigüedad se calcula sobre el saldo realmente pendiente después de las compensaciones aprobadas a la fecha de corte.</p></div></div>
    ${barraCorte(`<label>Base <select id="a-base"><option value="VENCIMIENTO" ${fa.base === "VENCIMIENTO" ? "selected" : ""}>Vencimiento</option><option value="EMISION" ${fa.base === "EMISION" ? "selected" : ""}>Emisión</option></select></label>
      <label>Agrupar <select id="a-agr">${["tercero", "cuenta", "documento", "moneda", "proyecto", "centro_costo"].map((k) => `<option ${fa.agrupar === k ? "selected" : ""}>${k}</option>`).join("")}</select></label>
      <label>Cuenta <input id="a-cta" value="${esc(fa.cuenta)}" size="6"></label><button class="btn btn-sm" id="a-ir">Aplicar</button>`)}
    <div class="card"><h2>Antigüedad del saldo pendiente</h2>${graficoBarras(a.tramos.map((t, i) => ({ etiqueta: t, valor: Number(a.totales[i]) })), { max: 20 })}
      <div class="tabla-wrap"><table class="tabla"><thead><tr><th>${esc(fa.agrupar)}</th>${a.tramos.map((t) => `<th class="num">${esc(t)}</th>`).join("")}<th class="num">Total</th></tr></thead>
      <tbody>${a.grupos.slice(0, 200).map((g) => `<tr><td>${esc(g.razon_social ? `${g.razon_social} · ${g.clave}` : g.clave)}</td>${g.tramos.map((v) => `<td class="num">${Number(v) ? num(v) : ""}</td>`).join("")}<td class="num"><b>${num(g.total)}</b></td></tr>`).join("") || `<tr><td colspan="${a.tramos.length + 2}" class="vacio">Sin saldos pendientes</td></tr>`}</tbody></table></div>
      ${Object.keys(a.saldos_a_favor_sin_aplicar || {}).length ? `<div class="alerta alerta-info">Saldos a favor (cancelaciones aún sin aplicar), presentados aparte: ${Object.entries(a.saldos_a_favor_sin_aplicar).map(([k, v]) => `${esc(k)} ${num(v)}`).join(" · ")}</div>` : ""}</div>
    <div class="card" style="margin-top:16px"><h2>Reportes (Excel / PDF)</h2><p class="sub">Cada reporte indica empresa, periodo, fecha de corte, moneda, filtros aplicados y fecha de generación.</p>
      <table class="tabla"><tbody>${Object.entries(nombres).map(([k, t]) => `<tr><td>${t}</td><td>${botonesC(k, k === "antiguedad" ? { base: fa.base, agrupar: fa.agrupar, cuenta: fa.cuenta } : { cuenta: fa.cuenta })}</td></tr>`).join("")}</tbody></table></div>`;
  enlazarCorte();
  $("#a-ir").onclick = () => { Object.assign(fa, { base: $("#a-base").value, agrupar: $("#a-agr").value, cuenta: $("#a-cta").value.trim() }); navegar(); };
};

// ------------------------------------------------------------------ configuración: reglas, roles, ejecuciones y auditoría
const TIPOS_R = { CUENTA: "Por cuenta", GENERAL: "General", ENTRE_CUENTAS: "Entre cuentas (autorizada)", CONVERSION_MONEDA: "Conversión de moneda", DETRACCION: "Detracción", RETENCION: "Retención", PERCEPCION: "Percepción" };
rutas["comp-config"] = async () => {
  if (!(await inicioComp())) return;
  const [reglas, roles, runs, aud] = await vigente(Promise.all([api("/compensacion/reglas", { params: { empresa_id: estado.empresaId } }),
    api("/compensacion/roles", { params: { empresa_id: estado.empresaId } }), api("/compensacion/ejecuciones", { params: { empresa_id: estado.empresaId } }),
    api("/compensacion/auditoria", { params: { empresa_id: estado.empresaId, limite: 100 } })]));
  const editable = puede("configurar");
  vista().innerHTML = `<div class="cab-vista"><div><h1>Configuración de compensación</h1><p class="sub">Cada cuenta compensable tiene sus propias reglas. La aprobación automática solo procede con política autorizada, puntuación ≥ umbral (mínimo 95), sin ambigüedad y sin bloqueos.</p></div>
      ${editable ? '<button class="btn btn-primario" id="rg-nueva">Nueva regla</button>' : ""}</div>
    <div class="card"><h2>Reglas</h2><div class="tabla-wrap"><table class="tabla"><thead><tr><th>Tipo</th><th>Código</th><th>Nombre</th><th>Parámetros principales</th><th>Vigencia</th><th>Versión</th><th>Activa</th><th></th></tr></thead>
      <tbody>${reglas.map((r) => {
        const p = r.parametros;
        const res = r.tipo === "CUENTA" ? `ventana ${p.ventana_dias} d · máx. comb. ${p.max_combinacion} · FIFO ${p.fifo ? "sí" : "no"} · auto ${p.autoaprobar ? `sí (≥${p.umbral_auto})` : "no"}`
          : r.tipo === "ENTRE_CUENTAS" ? `cuentas ${(p.cuentas || []).join(" ↔ ")}` : ["DETRACCION", "RETENCION", "PERCEPCION"].includes(r.tipo) ? `tasa ${p.tasa ?? "—"} %` : Object.keys(p).slice(0, 4).join(", ");
        return `<tr><td>${esc(TIPOS_R[r.tipo] || r.tipo)}</td><td>${esc(r.codigo)}</td><td>${esc(r.nombre)}</td><td class="sub">${esc(res)}</td><td>${r.vigente_desde ? fecha(r.vigente_desde) : "—"} → ${r.vigente_hasta ? fecha(r.vigente_hasta) : "—"}</td>
          <td>v${r.version}</td><td>${r.activa ? "Sí" : "No"}</td><td>${editable ? `<button class="btn btn-sm" data-regla="${r.id}">Editar</button>` : ""}</td></tr>`;
      }).join("")}</tbody></table></div></div>
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card"><h2>Roles</h2>${ctxC.rol.modo_abierto ? '<div class="alerta alerta-warn">Modo abierto: no hay roles asignados y cualquier usuario puede operar. Al asignar el primer rol, quien lo asigna queda como Administrador.</div>' : ""}
        <table class="tabla"><thead><tr><th>Usuario</th><th>Rol</th><th>Asignado por</th><th></th></tr></thead><tbody>${roles.map((r) => `<tr><td>${esc(r.usuario)}</td><td>${esc(ROLES_C[r.rol])}</td><td>${esc(r.asignado_por || "")}</td><td>${puede("roles") ? `<button class="btn btn-sm" data-quitar="${r.id}">Quitar</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="4" class="vacio">Sin roles</td></tr>'}</tbody></table>
        ${puede("roles") ? `<div class="acciones"><input id="rl-u" placeholder="usuario"><select id="rl-r">${Object.entries(ROLES_C).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select><button class="btn btn-sm btn-primario" id="rl-ok">Asignar</button></div>` : ""}</div>
      <div class="card"><h2>Ejecuciones</h2><table class="tabla"><thead><tr><th>#</th><th>Corte</th><th>Estado</th><th>Usuario</th><th class="num">ms</th><th>Resultado</th></tr></thead>
        <tbody>${runs.map((r) => `<tr><td>${r.id}</td><td>${fecha(r.fecha_corte)}</td><td>${esc(r.estado)}</td><td>${esc(r.usuario)}</td><td class="num">${r.duracion_ms ?? "—"}</td><td class="sub">${r.resumen ? `${r.resumen.propuestas || 0} prop. · ${r.resumen.autoaprobadas || 0} auto · ${r.resumen.ambiguas || 0} amb.` : esc(r.error || "")}</td></tr>`).join("") || '<tr><td colspan="6" class="vacio">Sin ejecuciones</td></tr>'}</tbody></table></div></div>
    <div class="card" style="margin-top:16px"><h2>Auditoría (últimos 100 eventos)</h2><div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th>Fecha</th><th>Usuario</th><th>Rol</th><th>Acción</th><th>Entidad</th><th>Detalle</th></tr></thead>
      <tbody>${aud.map((x) => `<tr><td class="nowrap">${fechaHora(x.fecha)}</td><td>${esc(x.usuario)}</td><td>${esc(x.rol || "")}</td><td>${esc(x.accion)}</td><td>${esc(x.entidad || "")} ${x.entidad_id ?? ""}</td><td class="sub">${esc((x.detalle || "").slice(0, 160))}</td></tr>`).join("")}</tbody></table></div></div>`;
  $$("[data-regla]").forEach((b) => b.addEventListener("click", () => editarRegla(reglas.find((r) => r.id === Number(b.dataset.regla)))));
  $("#rg-nueva")?.addEventListener("click", () => editarRegla(null));
  $("#rl-ok")?.addEventListener("click", async () => {
    try { await api("/compensacion/roles", { method: "POST", params: { empresa_id: estado.empresaId }, body: { usuario: $("#rl-u").value.trim(), rol: $("#rl-r").value } }); toast("Rol asignado", "ok"); navegar(); } catch (e) { toast(e.message, "err"); }
  });
  $$("[data-quitar]").forEach((b) => b.addEventListener("click", async () => {
    try { await api(`/compensacion/roles/${b.dataset.quitar}`, { method: "DELETE", params: { empresa_id: estado.empresaId } }); navegar(); } catch (e) { toast(e.message, "err"); }
  }));
};

function editarRegla(r) {
  const nueva = !r;
  r = r || { tipo: "ENTRE_CUENTAS", codigo: "", nombre: "", parametros: { cuentas: [] }, sustento: "", activa: true };
  const cuerpo = abrirModal(nueva ? "Nueva regla" : `Regla ${r.codigo} (v${r.version})`, `
    <form id="rg-form" class="form-grid">
      <label class="campo">Tipo <select name="tipo" ${nueva ? "" : "disabled"}>${Object.entries(TIPOS_R).map(([k, v]) => `<option value="${k}" ${r.tipo === k ? "selected" : ""}>${v}</option>`).join("")}</select></label>
      <label class="campo">Código <input name="codigo" value="${esc(r.codigo)}" required ${nueva ? "" : "readonly"} placeholder="p. ej. 037 o ANT-PROV"></label>
      <label class="campo" style="grid-column:1/-1">Nombre <input name="nombre" value="${esc(r.nombre)}" required minlength="3"></label>
      <label class="campo" style="grid-column:1/-1">Parámetros (JSON)<textarea name="parametros" rows="10" style="font-family:monospace">${esc(JSON.stringify(r.parametros, null, 2))}</textarea>
        <span class="sub">Cuenta: ventana_dias, max_combinacion, max_candidatos, max_nodos, tolerancia, fifo, autoaprobar, umbral_auto (≥95), pesos… · Entre cuentas: {"cuentas": ["4212","4221"]} · Tributos: {"tasa": "12", "tolerancia": "1"}</span></label>
      <label class="campo" style="grid-column:1/-1">Sustento / autorización<textarea name="sustento" rows="2">${esc(r.sustento || "")}</textarea></label>
      <label class="campo">Vigente desde <input type="date" name="vigente_desde" value="${r.vigente_desde || ""}"></label>
      <label class="campo">Vigente hasta <input type="date" name="vigente_hasta" value="${r.vigente_hasta || ""}"></label>
      <label class="check"><input type="checkbox" name="activa" ${r.activa ? "checked" : ""}> Activa</label>
      <div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Guardar (crea una nueva versión)</button></div></form>`);
  $("#rg-form", cuerpo).addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    let parametros;
    try { parametros = JSON.parse(f.parametros.value || "{}"); } catch { return toast("Los parámetros no son un JSON válido", "err"); }
    const body = { tipo: f.tipo.value, codigo: f.codigo.value.trim(), nombre: f.nombre.value.trim(), parametros, sustento: f.sustento.value.trim() || null,
      vigente_desde: f.vigente_desde.value || null, vigente_hasta: f.vigente_hasta.value || null, activa: f.activa.checked };
    try {
      await api(nueva ? "/compensacion/reglas" : `/compensacion/reglas/${r.id}`, { method: nueva ? "POST" : "PUT", params: { empresa_id: estado.empresaId }, body });
      toast("Regla guardada", "ok"); cerrarModal(); navegar();
    } catch (err) { toast(err.message, "err"); }
  });
}
