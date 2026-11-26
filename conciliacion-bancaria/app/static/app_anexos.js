/* Fase 5 — Generador de anexos contables: dashboard, centro de anexos (explorador jerárquico), generador masivo,
   vista del anexo (detalle, conciliación, observaciones, documentación, revisión y versiones), vista de impresión,
   diseñador de plantillas, documentación, exportaciones, registros auxiliares y responsables.
   Reutiliza utilitarios de app.js, app_contable.js (barraProgreso, esperarTrabajo) y app_analisis.js (gráficos, num). */
"use strict";

const ctxX = { ejercicio: null, periodo: null, corte: null, rol: null, periodos: [] };
const EST_X = { PENDIENTE_GENERACION: ["Pendiente de generación", ""], GENERADO: ["Generado", "b-info"], EN_ELABORACION: ["En elaboración", "b-info"],
  EN_REVISION: ["En revisión", "b-warn"], OBSERVADO: ["Observado", "b-err"], SUBSANADO: ["Subsanado", "b-warn"], REVISADO: ["Revisado", "b-info"],
  APROBADO: ["Aprobado", "b-ok"], CERRADO: ["Cerrado", "b-ok"], REABIERTO: ["Reabierto", "b-warn"] };
const RES_X = { CUADRADO: ["Cuadrado", "#00b894"], CUADRADO_CON_OBSERVACIONES: ["Cuadrado con observaciones", "#257de0"],
  PARCIALMENTE_SUSTENTADO: ["Parcialmente sustentado", "#f2a600"], DESCUADRADO: ["Descuadrado", "#dc3c3d"], INFORMACION_INSUFICIENTE: ["Información insuficiente", "#8a94a6"] };
const SUST_X = { DOCUMENTADO: ["Documentado", "b-ok"], SIN_DOCUMENTO: ["Sin documento", "b-warn"], SIN_DETALLE: ["Sin detalle", "b-err"], POR_CLASIFICAR: ["Por clasificar", "b-warn"] };
const SEV_X = { ALTA: "#dc3c3d", MEDIA: "#f18a59", BAJA: "#fbb315", INFORMATIVA: "#8a94a6" };
const ACCION_X = { EN_ELABORACION: "Iniciar elaboración", EN_REVISION: "Enviar a revisión", OBSERVADO: "Observar", SUBSANADO: "Marcar subsanado",
  REVISADO: "Marcar revisado", APROBADO: "Aprobar", CERRADO: "Cerrar", REABIERTO: "Reabrir" };
const TIPOS_REG = { ACTIVO_FIJO: "Registro de activos fijos", CONTRATO_FINANCIERO: "Contratos financieros", CUOTA_FINANCIERA: "Cronogramas (cuotas)",
  GASTO_ANTICIPADO: "Gastos contratados por anticipado", SERVICIO_PROCESO: "Servicios en proceso (cuenta 23)", INVENTARIO: "Inventario valorizado" };
const ELEMENTOS = { 0: "Cuentas de orden", 1: "Activo disponible y exigible", 2: "Activo realizable", 3: "Activo inmovilizado", 4: "Pasivo",
  5: "Patrimonio", 6: "Gastos por naturaleza", 7: "Ingresos", 8: "Saldos intermediarios", 9: "Contabilidad analítica" };

const chipX = (map, k) => { const [t, c] = map[k] || [k || "—", ""]; return `<span class="badge ${c}">${esc(t)}</span>`; };
const resX = (k) => (k ? `<span class="badge riesgo" style="--c:${RES_X[k][1]}">${esc(RES_X[k][0])}</span>` : "—");
const puedeX = (a) => (ctxX.rol?.permisos || []).includes(a);
const qX = (extra = {}) => ({ empresa_id: estado.empresaId, ejercicio: ctxX.ejercicio, periodo: ctxX.periodo, fecha_corte: ctxX.corte, ...extra });
const finMes = (ej, p) => { const m = Math.min(Math.max(p, 1), 12); return new Date(Date.UTC(ej, m, 0)).toISOString().slice(0, 10); };
const valorX = (v, tipo) => (v === null || v === undefined || v === "" ? "" : tipo === "importe" ? num(v) : tipo === "fecha" ? fecha(v)
  : tipo === "pct" ? `${Number(v).toFixed(2)} %` : tipo === "tasa" ? Number(v).toLocaleString("es-PE", { maximumFractionDigits: 6 }) : esc(v));

async function bajar(ruta, params = {}, nombre = "archivo") {
  const p = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== ""));
  const r = await fetch(`/api${ruta}?${p}`, { headers: { "X-Usuario": encodeURIComponent(usuario()) } });
  if (!r.ok) { let m = `Error ${r.status}`; try { m = (await r.json()).detail || m; } catch { /* binario */ } throw new Error(m); }
  const cd = r.headers.get("content-disposition") || "";
  const n = (cd.match(/filename="([^"]+)"/) || [])[1] || nombre;
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a"); a.href = url; a.download = n; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

async function inicioAnx() {
  if (!requiereEmpresa()) return false;
  ctxX.periodos = await vigente(api(`/analisis/periodos/${estado.empresaId}`));
  ctxX.rol = await vigente(api("/anexos/mi-rol", { params: { empresa_id: estado.empresaId } }));
  const g = JSON.parse(almacen.leer(`ax_ctx_${estado.empresaId}`, "null") || "null");
  if (g && ctxX.periodos.some((x) => x.ejercicio === g.ejercicio)) Object.assign(ctxX, g);
  else if (ctxX.periodos.length) {
    const u = ctxX.periodos[0];
    const ps = u.periodos.map((x) => x.periodo).filter((p) => p >= 1 && p <= 12);
    Object.assign(ctxX, { ejercicio: u.ejercicio, periodo: Math.max(...ps, 1) });
    ctxX.corte = finMes(ctxX.ejercicio, ctxX.periodo);
  }
  if (!ctxX.periodos.length) {
    vista().innerHTML = `<div class="card" style="max-width:680px"><h2>Sin información contable</h2><p>Los anexos se generan a partir del libro diario importado.</p>
      <a class="btn btn-primario" href="#/contable-importar">Importar información contable</a></div>`;
    return false;
  }
  return true;
}
function barraX(extra = "") {
  const ej = ctxX.periodos.map((x) => `<option ${x.ejercicio === ctxX.ejercicio ? "selected" : ""}>${x.ejercicio}</option>`).join("");
  const per = Array.from({ length: 13 }, (_, i) => i + 1).map((p) => `<option value="${p}" ${p === ctxX.periodo ? "selected" : ""}>${String(p).padStart(2, "0")}${p === 13 ? " Cierre" : ""}</option>`).join("");
  const r = ctxX.rol;
  return `<div class="ctx-bar"><label>Ejercicio <select id="ax-ej">${ej}</select></label><label>Periodo <select id="ax-pe">${per}</select></label>
    <label>Fecha de corte <input type="date" id="ax-co" value="${ctxX.corte}"></label>
    <span class="sub">Rol: <b>${r.modo_abierto ? "modo abierto" : esc(r.rol || "sin rol")}</b>${r.cuentas_permitidas ? ` · cuentas: ${esc(r.cuentas_permitidas.join(", "))}` : ""}</span>${extra}</div>`;
}
function enlazarX(alCambiar = navegar) {
  const guardar = () => { almacen.guardar(`ax_ctx_${estado.empresaId}`, JSON.stringify({ ejercicio: ctxX.ejercicio, periodo: ctxX.periodo, corte: ctxX.corte })); alCambiar(); };
  $("#ax-ej")?.addEventListener("change", (e) => { ctxX.ejercicio = Number(e.target.value); ctxX.corte = finMes(ctxX.ejercicio, ctxX.periodo); guardar(); });
  $("#ax-pe")?.addEventListener("change", (e) => { ctxX.periodo = Number(e.target.value); ctxX.corte = finMes(ctxX.ejercicio, ctxX.periodo); guardar(); });
  $("#ax-co")?.addEventListener("change", (e) => {
    if (!e.target.value) return;
    ctxX.corte = e.target.value; ctxX.ejercicio = Number(ctxX.corte.slice(0, 4));
    if (ctxX.periodo <= 12) ctxX.periodo = Number(ctxX.corte.slice(5, 7));
    guardar();
  });
}

async function lanzarGeneracion(body, caja) {
  try {
    const r = await api("/anexos/generaciones", { method: "POST", params: { empresa_id: estado.empresaId }, body: { ejercicio: ctxX.ejercicio, periodo: ctxX.periodo, fecha_corte: ctxX.corte, ...body } });
    if (r.reutilizado) { toast(`Sin cambios en datos, reglas ni sustentos: se reutiliza la generación #${r.run_id}`, "ok"); return r.run_id; }
    if (caja) caja.innerHTML = `<div class="card">${barraProgreso(0, "En cola")}<div class="acciones"><button class="btn btn-sm btn-peligro" data-cancelar>Cancelar</button></div></div>`;
    caja?.querySelector("[data-cancelar]")?.addEventListener("click", async () => {
      try { await api(`/anexos/generaciones/${r.run_id}/cancelar`, { method: "POST", params: { empresa_id: estado.empresaId } }); toast("Cancelación solicitada"); } catch (e) { toast(e.message, "err"); }
    });
    await esperarTrabajo(r.trabajo, (t) => {
      const b = caja?.querySelector(".progreso"); if (!b) return;
      b.querySelector(".progreso-barra").style.width = `${Math.max(2, t.progreso)}%`;
      caja.querySelector(".progreso-txt").innerHTML = `<span>${esc(t.etapa)}</span><b>${t.progreso}%</b>`;
    });
    const run = await api(`/anexos/generaciones/${r.run_id}`, { params: { empresa_id: estado.empresaId } });
    const s = run.resumen || {};
    toast(run.estado === "CANCELADO" ? "Generación cancelada (las versiones ya guardadas se conservan)" :
      `Generación #${run.id}: ${s.nuevas_versiones || 0} nuevas versiones, ${s.sin_cambios || 0} sin cambios, ${s.protegidos || 0} aprobados protegidos`, "ok");
    return run.id;
  } catch (e) { toast(e.message, "err"); if (caja) caja.innerHTML = ""; return null; }
}

// ------------------------------------------------------------------ dashboard
rutas["anx"] = async () => {
  if (!(await inicioAnx())) return;
  const d = await vigente(api("/anexos/dashboard", { params: qX() }));
  const k = d.kpi, g = d.graficos, u = d.ultima_generacion;
  const tile = (l, v, sub = "", href = "") => `<div class="kpi"><div class="l">${l}</div><div class="v">${href ? `<a href="${href}">${v}</a>` : v}</div>${sub ? `<div class="l">${sub}</div>` : ""}</div>`;
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Anexos contables</h1><p class="sub">Composición verificable de los saldos al corte. Un anexo cuadrado no implica, por sí solo, que esté sustentado: el sustento documental se mide por separado.</p></div>
      <div class="acciones" style="margin:0">${puedeX("generar") && !ctxX.rol.cuentas_permitidas ? '<button class="btn btn-primario" id="ax-todo">Generar anexos de todo el balance</button>' : ""}<a class="btn" href="#/anx-centro">Centro de anexos</a></div></div>
    ${barraX()}
    <div id="ax-prog"></div>
    ${u ? `<div class="alerta ${u.estado === "COMPLETADO" ? "alerta-ok" : u.estado === "ERROR" ? "alerta-err" : "alerta-warn"}">Última generación #${u.id} · corte ${fecha(u.fecha_corte)} · ${esc(u.estado)} · ${u.duracion_ms ?? "—"} ms · ${esc(u.usuario)}${u.resumen?.cuentas !== undefined ? ` · ${u.resumen.cuentas} cuentas, ${u.resumen.nuevas_versiones} nuevas versiones` : ""}</div>` : ""}
    <div class="grid grid-5">
      ${tile("Cuentas sujetas a análisis", k.cuentas_sujetas)}${tile("Anexos generados", k.anexos_generados, "", "#/anx-centro")}
      ${tile("Cuentas sin anexo", k.cuentas_sin_anexo)}${tile("Cuadrados", k.cuadrados, `${k.cuadrados_con_observaciones} con observaciones`)}
      ${tile("Descuadrados", k.descuadrados, `diferencias ${num(k.diferencia_total)}`)}${tile("Parcialmente sustentados", k.parcialmente_sustentados, `pendiente ${num(k.pendiente_sustento_total)}`)}
      ${tile("Información insuficiente", k.informacion_insuficiente)}${tile("Observados", k.observados)}${tile("Aprobados o cerrados", k.aprobados)}
      ${tile("Avance del cierre", `${k.avance_cierre} %`, "anexos aprobados / generados")}
    </div>
    <p class="sub">${esc(d.nota_duplicados)}</p>
    <div class="grid grid-2" style="margin-top:12px">
      <div class="card"><h2>Avance por elemento contable</h2>${graficoAgrupado(g.avance_elemento.map((x) => ({ etiqueta: `${x.elemento}`, valores: [x.aprobados, x.en_proceso, x.sin_generar] })), ["Aprobados", "En proceso", "Sin generar"])}</div>
      <div class="card"><h2>Resultado de la conciliación</h2>${graficoBarras(g.resultado.map((x) => ({ etiqueta: x.nombre, valor: x.cantidad })), { colores: g.resultado.map((x) => RES_X[x.resultado][1]), etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Estado de revisión</h2>${graficoBarras(g.estado_revision.map((x) => ({ etiqueta: x.nombre, valor: x.cantidad })), { etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Diferencias por cuenta</h2>${graficoBarras(g.diferencias.map((x) => ({ etiqueta: `${x.cuenta} ${x.descripcion || ""}`, valor: Number(x.diferencia) })), { color: "#dc3c3d" })}
        <div class="sub">${g.diferencias.map((x) => `<a href="#/anx-ver?id=${x.anexo_id}">${esc(x.cuenta)}</a>`).join(" · ")}</div></div>
      <div class="card"><h2>Evolución por fecha de corte</h2>${graficoLineas([{ nombre: "Anexos", valores: g.evolucion.map((x) => x.anexos) }, { nombre: "Aprobados", valores: g.evolucion.map((x) => x.aprobados) }, { nombre: "Descuadrados", valores: g.evolucion.map((x) => x.descuadrados) }], g.evolucion.map((x) => x.fecha_corte.slice(5, 7) + "/" + x.fecha_corte.slice(2, 4)))}</div>
      <div class="card"><h2>Antigüedad de saldos (cartera)</h2>${graficoBarras(g.antiguedad.map((x) => ({ etiqueta: x.tramo, valor: Number(x.saldo) })), { max: 15 })}</div>
      <div class="card"><h2>Observaciones abiertas por responsable</h2>${graficoBarras(g.observaciones_responsable.map((x) => ({ etiqueta: x.responsable, valor: x.cantidad })), { color: SERIES[1], etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Actividades pendientes por responsable</h2><table class="tabla"><thead><tr><th>Responsable</th><th class="num">Pendientes</th><th class="num">Vencidos</th><th>Anexos</th></tr></thead>
        <tbody>${d.pendientes_responsable.map((x) => `<tr><td>${esc(x.responsable)}</td><td class="num">${x.pendientes}</td><td class="num">${x.vencidos ? `<b style="color:#dc3c3d">${x.vencidos}</b>` : 0}</td>
          <td>${x.anexos.slice(0, 8).map((a) => `<a href="#/anx-ver?id=${a.id}">${esc(a.cuenta)}</a>`).join(", ")}</td></tr>`).join("") || '<tr><td colspan="4" class="vacio">Sin pendientes</td></tr>'}</tbody></table></div>
    </div>`;
  enlazarX();
  $("#ax-todo")?.addEventListener("click", async () => { if (await lanzarGeneracion({ modo: "BALANCE" }, $("#ax-prog"))) navegar(); });
};

// ------------------------------------------------------------------ centro de anexos (explorador)
const cx = { abiertos: new Set(["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]), texto: "", sel: new Set(), filtros: {}, plantilla: "" };
rutas["anx-centro"] = async () => {
  if (!(await inicioAnx())) return;
  const [d, pl] = await vigente(Promise.all([api("/anexos/cuentas", { params: qX() }), api("/anexos/plantillas", { params: { empresa_id: estado.empresaId } })]));
  const nodos = d.nodos, porPadre = {};
  nodos.forEach((n) => { (porPadre[n.padre || ""] ||= []).push(n); });
  const coincide = (n) => !cx.texto || n.cuenta.startsWith(cx.texto) || (n.descripcion || "").toLowerCase().includes(cx.texto.toLowerCase());
  const vis = [];
  const recorrer = (padre, prof) => (porPadre[padre] || []).forEach((n) => {
    if (cx.texto && !nodos.some((x) => x.cuenta.startsWith(n.cuenta) && coincide(x))) return;
    vis.push({ n, prof });
    if (cx.abiertos.has(n.cuenta) || cx.texto) recorrer(n.cuenta, prof + 1);
  });
  recorrer("", 0);
  const gen = puedeX("generar");
  const fl = cx.filtros;
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Centro de anexos contables</h1><p class="sub">Seleccione cuentas del plan para generar sus anexos (individuales, seleccionados, por elemento, por rango o de todo el balance). Cada anexo se concilia con el balance.</p></div></div>
    ${barraX(`<input id="cx-q" placeholder="Buscar cuenta o descripción…" value="${esc(cx.texto)}"><button class="btn btn-sm" id="cx-exp">Expandir</button><button class="btn btn-sm" id="cx-con">Contraer</button>`)}
    ${d.preliminar ? '<div class="alerta alerta-warn">Saldos iniciales preliminares: no hay saldos iniciales importados para el ejercicio.</div>' : ""}
    ${gen ? `<div class="card filtros">
      <label>Plantilla <select id="cx-pl"><option value="">Automática por cuenta</option>${pl.map((p) => `<option value="${p.id}" ${String(p.id) === cx.plantilla ? "selected" : ""}>${esc(p.codigo)} · ${esc(p.nombre)}</option>`).join("")}</select></label>
      <label>C. costo <input id="cx-cc" size="7" value="${esc(fl.centro_costo || "")}"></label><label>Proyecto <input id="cx-pr" size="8" value="${esc(fl.proyecto || "")}"></label>
      <label>Unidad de negocio <input id="cx-un" size="9" value="${esc(fl.unidad_negocio || "")}"></label>
      <label>Moneda <select id="cx-mo"><option value="">Todas</option>${["PEN", "USD", "EUR"].map((m) => `<option ${fl.moneda === m ? "selected" : ""}>${m}</option>`).join("")}</select></label>
      <button class="btn btn-sm btn-primario" id="cx-gen-sel">Generar seleccionados (<span id="cx-n">${cx.sel.size}</span>)</button>
      ${ctxX.rol.cuentas_permitidas ? "" : `<label>Elemento <select id="cx-el">${Object.entries(ELEMENTOS).map(([k, v]) => `<option value="${k}">${k} · ${esc(v)}</option>`).join("")}</select></label><button class="btn btn-sm" id="cx-gen-el">Generar elemento</button>
      <label>Rango <input id="cx-de" size="6" placeholder="desde"> – <input id="cx-ha" size="6" placeholder="hasta"></label><button class="btn btn-sm" id="cx-gen-ra">Generar rango</button>
      <button class="btn btn-sm" id="cx-gen-to">Todo el balance</button>`}</div>` : ""}
    <div id="cx-prog"></div>
    <div class="tabla-wrap tabla-alta"><table class="tabla tabla-arbol"><thead><tr>${gen ? '<th></th>' : ""}<th>Cuenta</th><th class="num">Saldo final (D+/A−)</th><th class="num">Movs.</th><th>Plantilla</th><th>Anexo al corte</th><th>Resultado</th><th class="num">Diferencia</th><th>Responsable</th><th></th></tr></thead>
      <tbody>${vis.map(({ n, prof }) => `<tr data-c="${n.cuenta}" class="nivel-${Math.min(n.nivel, 4)}">
        ${gen ? `<td><input type="checkbox" data-sel="${n.cuenta}" ${cx.sel.has(n.cuenta) ? "checked" : ""}></td>` : ""}
        <td style="padding-left:${10 + prof * 16}px">${n.tiene_hijos ? `<button class="tg" data-tg="${n.cuenta}">${cx.abiertos.has(n.cuenta) || cx.texto ? "▾" : "▸"}</button>` : '<span class="tg-v"></span>'}<b>${esc(n.cuenta)}</b> ${esc(n.descripcion || "")}</td>
        <td class="num">${num(n.saldo_final)}</td><td class="num">${n.movimientos}</td>
        <td><small>${n.plantilla ? `${esc(n.plantilla.codigo)} · ${esc(n.plantilla.especialidad)}` : "—"}</small></td>
        <td>${n.anexo ? `<a href="#/anx-ver?id=${n.anexo.id}">v${n.anexo.version}</a> ${chipX(EST_X, n.anexo.estado)}` : '<span class="sub">Pendiente de generación</span>'}</td>
        <td>${n.anexo ? resX(n.anexo.resultado) : ""}</td><td class="num">${n.anexo && Number(n.anexo.diferencia) ? `<b style="color:#dc3c3d">${num(n.anexo.diferencia)}</b>` : ""}</td>
        <td>${esc(n.anexo?.responsable || "")}</td>
        <td>${gen ? `<button class="btn btn-sm" data-gen="${n.cuenta}">${n.anexo ? "Actualizar" : "Generar"}</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="10" class="vacio">Sin cuentas con saldo o movimiento</td></tr>'}</tbody></table></div>`;
  enlazarX();
  const filtros = () => {
    cx.filtros = { centro_costo: $("#cx-cc")?.value.trim(), proyecto: $("#cx-pr")?.value.trim(), unidad_negocio: $("#cx-un")?.value.trim(), moneda: $("#cx-mo")?.value };
    cx.plantilla = $("#cx-pl")?.value || "";
    return { filtros: cx.filtros, plantilla_id: cx.plantilla ? Number(cx.plantilla) : null };
  };
  const generarYVolver = async (body) => { if (await lanzarGeneracion({ ...filtros(), ...body }, $("#cx-prog"))) navegar(); };
  $("#cx-q").addEventListener("change", (e) => { cx.texto = e.target.value.trim(); navegar(); });
  $("#cx-exp").onclick = () => { nodos.forEach((n) => n.tiene_hijos && cx.abiertos.add(n.cuenta)); navegar(); };
  $("#cx-con").onclick = () => { cx.abiertos.clear(); navegar(); };
  $$("[data-tg]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); const c = b.dataset.tg; cx.abiertos.has(c) ? cx.abiertos.delete(c) : cx.abiertos.add(c); navegar(); }));
  $$("[data-sel]").forEach((c) => c.addEventListener("change", () => { c.checked ? cx.sel.add(c.dataset.sel) : cx.sel.delete(c.dataset.sel); $("#cx-n").textContent = cx.sel.size; }));
  $$("[data-gen]").forEach((b) => b.addEventListener("click", () => generarYVolver({ modo: "CUENTAS", cuentas: [b.dataset.gen] })));
  $("#cx-gen-sel")?.addEventListener("click", () => (cx.sel.size ? generarYVolver({ modo: "CUENTAS", cuentas: [...cx.sel] }) : toast("Seleccione cuentas", "err")));
  $("#cx-gen-el")?.addEventListener("click", () => generarYVolver({ modo: "ELEMENTO", elemento: $("#cx-el").value }));
  $("#cx-gen-ra")?.addEventListener("click", () => generarYVolver({ modo: "RANGO", desde: $("#cx-de").value.trim(), hasta: $("#cx-ha").value.trim() }));
  $("#cx-gen-to")?.addEventListener("click", () => generarYVolver({ modo: "BALANCE" }));
};

// ------------------------------------------------------------------ generador masivo
rutas["anx-masivo"] = async () => {
  if (!(await inicioAnx())) return;
  const [runs, pl] = await vigente(Promise.all([api("/anexos/generaciones", { params: { empresa_id: estado.empresaId } }), api("/anexos/plantillas", { params: { empresa_id: estado.empresaId } })]));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Generador masivo</h1><p class="sub">Identifica las cuentas con saldo o movimientos, selecciona la plantilla, recupera movimientos y compensaciones, genera el detalle, ejecuta las validaciones, concilia con el balance y guarda una versión (solo si el contenido cambió).</p></div></div>
    ${barraX()}
    ${puedeX("generar") ? `<form id="mx-form" class="card form-grid">
      <label class="campo">Alcance <select name="modo"><option value="BALANCE">Balance completo</option><option value="ELEMENTO">Elemento contable</option><option value="RANGO">Rango de cuentas</option><option value="CUENTAS">Cuentas indicadas</option></select></label>
      <label class="campo">Elemento <select name="elemento">${Object.entries(ELEMENTOS).map(([k, v]) => `<option value="${k}">${k} · ${esc(v)}</option>`).join("")}</select></label>
      <label class="campo">Desde <input name="desde" placeholder="10"></label><label class="campo">Hasta <input name="hasta" placeholder="19"></label>
      <label class="campo" style="grid-column:1/-1">Cuentas (separadas por coma) <input name="cuentas" placeholder="1212, 4212, 3341"></label>
      <label class="campo">Nivel de agregación (dígitos) <input name="digitos" type="number" min="1" max="12" placeholder="analítica"></label>
      <label class="campo">Plantilla <select name="plantilla_id"><option value="">Automática por cuenta</option>${pl.map((p) => `<option value="${p.id}">${esc(p.codigo)} · ${esc(p.nombre)}</option>`).join("")}</select></label>
      <label class="campo">Motivo <input name="motivo" maxlength="255" placeholder="Cierre de ${ctxX.corte}"></label>
      <label class="check"><input type="checkbox" name="forzar"> Recalcular aunque no haya cambios</label>
      <div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Generar anexos</button></div></form>` : '<div class="alerta alerta-warn">Su rol no permite generar anexos.</div>'}
    <div id="mx-prog"></div>
    <div class="card"><h2>Generaciones</h2><div class="tabla-wrap"><table class="tabla"><thead><tr><th>#</th><th>Corte</th><th>Alcance</th><th>Estado</th><th class="num">Cuentas</th><th class="num">Nuevas versiones</th><th class="num">Sin cambios</th><th class="num">Protegidos</th><th>Resultados</th><th class="num">ms</th><th>Usuario</th></tr></thead>
      <tbody>${runs.map((r) => { const s = r.resumen || {}; return `<tr><td>${r.id}</td><td>${fecha(r.fecha_corte)}</td><td>${esc(r.alcance.modo)}${r.alcance.elemento ? ` ${r.alcance.elemento}` : ""}${r.alcance.cuentas?.length ? ` ${esc(r.alcance.cuentas.slice(0, 4).join(", "))}` : ""}</td>
        <td>${esc(r.estado)}${r.error ? ` <span class="sub">${esc(r.error.slice(0, 80))}</span>` : ""}</td><td class="num">${r.total_cuentas}</td><td class="num">${s.nuevas_versiones ?? ""}</td><td class="num">${s.sin_cambios ?? ""}</td>
        <td class="num">${s.protegidos ?? ""}${s.protegidos_con_cambios?.length ? ` <span class="badge b-warn" title="Aprobados cuyos datos cambiaron: requieren reapertura">${s.protegidos_con_cambios.length} con cambios</span>` : ""}</td>
        <td><small>${Object.entries(s.por_resultado || {}).map(([k, v]) => `${RES_X[k]?.[0] || k}: ${v}`).join(" · ")}</small></td><td class="num">${r.duracion_ms ?? ""}</td><td>${esc(r.usuario)}</td></tr>`; }).join("") || '<tr><td colspan="11" class="vacio">Sin generaciones</td></tr>'}</tbody></table></div></div>`;
  enlazarX();
  $("#mx-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const body = { modo: f.modo.value, elemento: f.modo.value === "ELEMENTO" ? f.elemento.value : null, desde: f.desde.value.trim() || null, hasta: f.hasta.value.trim() || null,
      cuentas: f.cuentas.value.split(",").map((x) => x.trim()).filter(Boolean), digitos: f.digitos.value ? Number(f.digitos.value) : null,
      plantilla_id: f.plantilla_id.value ? Number(f.plantilla_id.value) : null, motivo: f.motivo.value.trim() || null, forzar: f.forzar.checked };
    if (await lanzarGeneracion(body, $("#mx-prog"))) navegar();
  });
};

// ------------------------------------------------------------------ vista del anexo
const vx = { pestana: "detalle", pagina: 1, buscar: "", version: null, ocultas: new Set(), comparacion: null };
async function asientoModal(lineaId) {
  try {
    const a = await api(`/analisis/lineas/${lineaId}/asiento`, { params: { empresa_id: estado.empresaId } });
    abrirModal(`Asiento ${a.asiento || ""} · ${fecha(a.fecha)}`, `<p class="sub">Archivo ${esc(a.lote.archivo)} (lote ${a.lote.id}) · periodo ${a.periodo} · ${a.cuadra ? "cuadrado" : "<b>descuadrado</b>"}</p>
      <table class="tabla"><thead><tr><th>Cuenta</th><th>Glosa</th><th>Tercero</th><th>Documento</th><th class="num">Debe</th><th class="num">Haber</th><th>Fila</th></tr></thead>
      <tbody>${a.lineas.map((l) => `<tr ${l.id === lineaId ? 'style="background:#fff8e1"' : ""}><td>${esc(l.cuenta)}</td><td>${esc(l.glosa || "")}</td><td>${esc(l.razon_social || l.documento_tercero || "")}</td>
        <td>${esc([l.serie, l.numero_documento].filter(Boolean).join("-"))}</td><td class="num">${num(l.debe_mn)}</td><td class="num">${num(l.haber_mn)}</td><td>${l.fila_origen ?? ""}</td></tr>`).join("")}</tbody>
      <tfoot><tr><td colspan="4">Total</td><td class="num">${num(a.total_debe)}</td><td class="num">${num(a.total_haber)}</td><td></td></tr></tfoot></table>
      <div class="acciones"><a class="btn btn-sm" href="#/analisis-detalle">Navegación de movimientos</a></div>`);
  } catch (e) { toast(e.message, "err"); }
}

rutas["anx-ver"] = async () => {
  if (!(await inicioAnx())) return;
  const id = Number(parametrosHash().id);
  if (vx.id !== id) Object.assign(vx, { id, pestana: "detalle", pagina: 1, buscar: "", version: null, comparacion: null });
  const d = await vigente(api(`/anexos/anexos/${id}`, { params: { empresa_id: estado.empresaId } }));
  const a = d.anexo, r = d.resumen || {};
  const verId = vx.version || d.version?.id;
  const pest = [["detalle", "Detalle"], ["conciliacion", "Conciliación"], ["observaciones", `Observaciones (${d.hallazgos.filter((h) => h.estado === "ABIERTO").length})`],
    ["documentacion", `Documentación (${d.adjuntos.length})`], ["revision", "Revisión"], ["versiones", `Versiones (${d.versiones.length})`]];
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Anexo ${esc(a.cuenta)} · ${esc(a.descripcion || "")}</h1>
      <p class="sub">${esc(d.plantilla?.nombre || "")} (${esc(d.plantilla?.codigo || "")}) · corte ${fecha(a.fecha_corte)} · ejercicio ${a.ejercicio} periodo ${String(a.periodo).padStart(2, "0")}
        ${Object.keys(a.filtros || {}).length ? ` · filtros ${esc(Object.entries(a.filtros).map(([k, v]) => `${k}: ${v}`).join(", "))}` : ""}</p></div>
      <div class="acciones" style="margin:0">
        <select id="vx-ver">${d.versiones.map((v) => `<option value="${v.id}" ${v.id === verId ? "selected" : ""}>Versión ${v.numero}${v.inmutable ? " · aprobada" : ""}</option>`).join("")}</select>
        <button class="btn btn-sm" id="vx-xls">Excel</button><button class="btn btn-sm" id="vx-pdf">PDF</button>
        <a class="btn btn-sm" href="#/anx-imprimir?id=${id}&version_id=${verId}">Vista de impresión</a>
        ${puedeX("generar") && !["APROBADO", "CERRADO"].includes(a.estado_revision) ? '<button class="btn btn-sm" id="vx-reg">Actualizar anexo</button>' : ""}</div></div>
    <div class="grid grid-5">
      <div class="kpi"><div class="l">Estado de revisión</div><div class="v">${chipX(EST_X, a.estado_revision)}</div><div class="l">versión ${a.version_actual} · bloqueo ${a.lock_version}</div></div>
      <div class="kpi"><div class="l">Conciliación</div><div class="v">${resX(a.resultado)}</div><div class="l">${esc(r.explicacion || "")}</div></div>
      <div class="kpi"><div class="l">Saldo contable</div><div class="v">${num(r.saldo_final_contable)}</div><div class="l">${a.naturaleza === "D" ? "deudora" : "acreedora"} · signo natural</div></div>
      <div class="kpi"><div class="l">Detallado / sustentado</div><div class="v">${num(r.saldo_detalle)}</div><div class="l">sustentado ${num(r.saldo_sustentado)}</div></div>
      <div class="kpi"><div class="l">Diferencia</div><div class="v" style="color:${Number(r.diferencia) ? "#dc3c3d" : "inherit"}">${num(r.diferencia)}</div><div class="l">sin sustento ${num(r.pendiente_sustento_bruto ?? r.saldo_pendiente_sustento)} (valor absoluto)</div></div>
    </div>
    <div class="acciones" style="justify-content:flex-start;margin:10px 0">${d.acciones.map((x) => `<button class="btn btn-sm ${x === "APROBADO" ? "btn-primario" : x === "REABIERTO" ? "btn-peligro" : ""}" data-estado="${x}">${ACCION_X[x]}</button>`).join("")}
      ${d.datos_personales_ocultos ? '<span class="badge b-warn">Datos personales ocultos para su rol</span>' : ""}</div>
    <div id="vx-prog"></div>
    <div class="pestanas">${pest.map(([k, t]) => `<button class="btn ${vx.pestana === k ? "btn-primario" : ""}" data-pest="${k}">${t}</button>`).join("")}</div>
    <div id="vx-cuerpo"></div>`;
  $$("[data-pest]").forEach((b) => b.addEventListener("click", () => { vx.pestana = b.dataset.pest; navegar(); }));
  $("#vx-ver").addEventListener("change", (e) => { vx.version = Number(e.target.value); vx.pagina = 1; navegar(); });
  $("#vx-xls").onclick = () => bajar(`/anexos/anexos/${id}/exportar.xlsx`, { empresa_id: estado.empresaId, version_id: verId }).catch((e) => toast(e.message, "err"));
  $("#vx-pdf").onclick = () => bajar(`/anexos/anexos/${id}/exportar.pdf`, { empresa_id: estado.empresaId, version_id: verId }).catch((e) => toast(e.message, "err"));
  $("#vx-reg")?.addEventListener("click", async () => {
    try {
      const x = await api(`/anexos/anexos/${id}/regenerar`, { method: "POST", params: { empresa_id: estado.empresaId }, body: { motivo: "Actualización desde la vista del anexo" } });
      if (x.trabajo) await esperarTrabajo(x.trabajo, () => {});
      toast(x.reutilizado ? "Sin cambios desde la última generación" : "Anexo actualizado", "ok"); vx.version = null; navegar();
    } catch (e) { toast(e.message, "err"); }
  });
  $$("[data-estado]").forEach((b) => b.addEventListener("click", async () => {
    const nuevo = b.dataset.estado;
    let comentario = null;
    if (["OBSERVADO", "REABIERTO"].includes(nuevo)) { comentario = prompt(`${ACCION_X[nuevo]}: indique el motivo (mínimo 10 caracteres)`); if (!comentario) return; }
    else if (nuevo === "APROBADO" && !confirm("La versión aprobada quedará inmutable. ¿Aprobar el anexo?")) return;
    try { await api(`/anexos/anexos/${id}/estado`, { method: "POST", params: { empresa_id: estado.empresaId }, body: { estado: nuevo, comentario, lock_version: a.lock_version } }); toast(`${ACCION_X[nuevo]}: registrado`, "ok"); navegar(); }
    catch (e) { toast(e.message, "err"); }
  }));
  const cuerpo = $("#vx-cuerpo");
  const fn = { detalle: pestDetalle, conciliacion: pestConciliacion, observaciones: pestObservaciones, documentacion: pestDocumentacion, revision: pestRevision, versiones: pestVersiones }[vx.pestana];
  await fn(cuerpo, d, verId);
};

async function pestDetalle(cuerpo, d, verId) {
  const id = d.anexo.id;
  const t = await api(`/anexos/anexos/${id}/detalle`, { params: { empresa_id: estado.empresaId, version_id: verId, pagina: vx.pagina, por_pagina: 200, buscar: vx.buscar } });
  const cols = t.columnas.filter((c) => !vx.ocultas.has(c.campo));
  const n = Math.max(1, Math.ceil(t.filas_filtradas / t.por_pagina));
  const numerica = (c) => ["importe", "entero", "pct", "tasa"].includes(c.tipo);
  cuerpo.innerHTML = `
    <div class="filtros"><input id="dx-q" placeholder="Buscar documento, tercero, glosa…" value="${esc(vx.buscar)}" size="30">
      <details class="col-menu"><summary class="btn btn-sm">Columnas</summary><div>${t.columnas.map((c) => `<label class="check"><input type="checkbox" data-oc="${c.campo}" ${vx.ocultas.has(c.campo) ? "" : "checked"}> ${esc(c.titulo)}</label>`).join("")}</div></details>
      <span class="sub">${t.filas_filtradas} de ${t.total_filas} filas${t.filtros_aplicados.length ? " · vista filtrada por la plantilla (la conciliación usa el detalle completo)" : ""}${t.errores_formulas.length ? ` · <b>fórmulas con error: ${esc(t.errores_formulas.join("; "))}</b>` : ""}</span></div>
    ${t.grupos.length ? `<details class="card" open><summary><b>Subtotales por ${esc(t.agrupar_por.join(" · "))}</b></summary><table class="tabla"><thead><tr><th>Grupo</th><th class="num">Filas</th>${Object.keys(t.grupos[0].subtotales).map((k) => `<th class="num">${esc(t.columnas.find((c) => c.campo === k)?.titulo || k)}</th>`).join("")}</tr></thead>
      <tbody>${t.grupos.map((g) => `<tr><td>${esc(g.clave)}</td><td class="num">${g.filas}</td>${Object.values(g.subtotales).map((v) => `<td class="num">${num(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></details>` : ""}
    <div class="tabla-wrap tabla-alta"><table class="tabla tabla-fija"><thead><tr>${cols.map((c) => `<th class="${numerica(c) ? "num" : ""}">${esc(c.titulo)}</th>`).join("")}<th></th></tr></thead>
      <tbody>${t.filas.map((f) => `<tr class="fila-click" data-linea="${f.linea_id || ""}" title="${f.linea_id ? "Ver el asiento original" : ""}">${cols.map((c) => c.campo === "estado_sustento" ? `<td>${chipX(SUST_X, f[c.campo])}</td>`
        : `<td class="${numerica(c) ? "num" : ""}">${valorX(f[c.campo], c.tipo)}</td>`).join("")}<td>${f.linea_id ? "↗" : ""}</td></tr>`).join("") || `<tr><td colspan="${cols.length + 1}" class="vacio">Sin filas</td></tr>`}</tbody>
      <tfoot><tr>${cols.map((c, i) => `<td class="${numerica(c) ? "num" : ""}">${i === 0 ? "<b>TOTAL</b>" : t.totales[c.campo] !== undefined ? `<b>${num(t.totales[c.campo])}</b>` : ""}</td>`).join("")}<td></td></tr></tfoot></table></div>
    <div class="paginacion"><span>Página ${t.pagina} de ${n}</span><button class="btn btn-sm" id="dx-a" ${t.pagina <= 1 ? "disabled" : ""}>Anterior</button><button class="btn btn-sm" id="dx-s" ${t.pagina >= n ? "disabled" : ""}>Siguiente</button></div>`;
  $("#dx-q").addEventListener("change", (e) => { vx.buscar = e.target.value.trim(); vx.pagina = 1; navegar(); });
  $$("[data-oc]").forEach((c) => c.addEventListener("change", () => { c.checked ? vx.ocultas.delete(c.dataset.oc) : vx.ocultas.add(c.dataset.oc); navegar(); }));
  $("#dx-a").onclick = () => { vx.pagina--; navegar(); };
  $("#dx-s").onclick = () => { vx.pagina++; navegar(); };
  $$("tr[data-linea]").forEach((tr) => tr.addEventListener("click", () => tr.dataset.linea && asientoModal(Number(tr.dataset.linea))));
}

async function pestConciliacion(cuerpo, d) {
  const r = d.resumen || {}, a = d.anexo;
  const filas = [["Saldo inicial", r.saldo_inicial], [a.naturaleza === "D" ? "(+) Movimientos del debe" : "(−) Movimientos del debe", r.debe], [a.naturaleza === "D" ? "(−) Movimientos del haber" : "(+) Movimientos del haber", r.haber],
    ["Saldo final contable", r.saldo_final_contable, true], ["Saldo detallado en el anexo", r.saldo_detalle], ["   · sustentado documentalmente", r.saldo_sustentado], ["   · sin sustento (valor absoluto de las partidas)", r.pendiente_sustento_bruto],
    ["   · sin documento", r.sin_documento], ["   · saldos iniciales sin detalle", r.sin_detalle], ["   · partidas por clasificar", r.por_clasificar],
    ["Diferencia de conciliación", r.diferencia, true]];
  if (r.saldo_balance_importado !== null && r.saldo_balance_importado !== undefined) filas.push(["Saldo según balance de comprobación importado", r.saldo_balance_importado], ["Diferencia con el balance importado", r.diferencia_balance_importado, true]);
  const ex = r.extras || {};
  const od = ex.origen_destino;
  cuerpo.innerHTML = `<div class="grid grid-2"><div class="card"><h2>Conciliación con el balance</h2><p class="sub">${esc(r.formula || "")}</p>
      <table class="tabla">${filas.map(([k, v, b]) => `<tr><td>${b ? `<b>${k}</b>` : k}</td><td class="num">${b ? `<b>${num(v)}</b>` : num(v)}</td></tr>`).join("")}</table>
      <div class="alerta ${a.resultado === "CUADRADO" ? "alerta-ok" : a.resultado === "DESCUADRADO" ? "alerta-err" : "alerta-warn"}" style="margin-top:10px">${resX(a.resultado)} ${esc(r.explicacion || "")}</div>
      <p class="sub">La igualdad matemática no equivale a validación documental. Las diferencias se muestran sin ajustes ficticios.</p></div>
    <div class="card"><h2>Fuentes y advertencias</h2><p>Apertura: <b>${esc(r.apertura || "")}</b> · movimientos del periodo: ${r.movimientos ?? "—"} · filas del anexo: ${r.filas ?? "—"}</p>
      ${(r.advertencias || []).map((x) => `<div class="alerta alerta-info">${esc(x)}</div>`).join("") || '<p class="sub">Sin advertencias.</p>'}
      ${ex.nota ? `<div class="alerta alerta-info">${esc(ex.nota)}</div>` : ""}
      ${ex.cartera ? `<p>Cartera relacionada: total ${num(ex.cartera.total)} · vencida ${num(ex.cartera.vencida)} · más de 365 días ${num(ex.cartera.vencida_365)}</p>` : ""}
      ${ex.ingresos_economicos !== undefined ? `<p>Ingresos económicos ${num(ex.ingresos_economicos)} · cuentas de transferencia ${num(ex.transferencias)}</p>` : ""}</div></div>
    ${od ? `<div class="card" style="margin-top:12px"><h2>Validación origen – transferencia (79) – destino</h2>
      <table class="tabla"><thead><tr><th>Cuenta de origen</th><th>Descripción</th><th class="num">Importe sujeto</th><th>Transferencia</th><th class="num">Destino esperado</th><th class="num">Sin regla</th><th>Estado</th></tr></thead>
      <tbody>${od.origenes.map((o) => `<tr><td>${esc(o.cuenta_origen)}</td><td>${esc(o.descripcion || "")}</td><td class="num">${num(o.importe_sujeto)}</td><td>${o.cuenta_transferencia}</td><td class="num">${num(o.destino_esperado)}</td><td class="num">${num(o.sin_regla)}</td><td>${esc(o.estado)}</td></tr>`).join("")}</tbody></table>
      <table class="tabla" style="margin-top:8px"><thead><tr><th>Destino</th><th class="num">Esperado</th><th class="num">Registrado</th><th class="num">Diferencia</th><th>Estado</th></tr></thead>
      <tbody>${od.destinos.map((x) => `<tr><td>${esc(x.cuenta_destino)}</td><td class="num">${num(x.esperado)}</td><td class="num">${num(x.registrado)}</td><td class="num">${num(x.diferencia)}</td><td>${esc(x.estado)}</td></tr>`).join("")}</tbody></table>
      <p class="sub">No se exige que toda la clase 6 se distribuya: las cuentas excluidas o sin regla se informan. La clase 9 no se suma a la 6 en los estados financieros.</p></div>` : ""}`;
}

async function pestObservaciones(cuerpo, d) {
  const id = d.anexo.id;
  const editable = !["APROBADO", "CERRADO"].includes(d.anexo.estado_revision);
  cuerpo.innerHTML = `<div class="tabla-wrap"><table class="tabla"><thead><tr><th>Severidad</th><th>Origen</th><th>Observación</th><th class="num">Importe</th><th>Estado</th><th>Responsable</th><th>Acción correctiva</th><th></th></tr></thead>
    <tbody>${d.hallazgos.map((h) => `<tr><td><span class="badge riesgo" style="--c:${SEV_X[h.severidad]}">${esc(h.severidad)}</span></td><td>${h.origen === "USUARIO" ? esc(h.creado_por) : "Sistema"}</td>
      <td><b>${esc(h.titulo)}</b>${h.detalle ? `<div class="sub">${esc(h.detalle)}</div>` : ""}</td><td class="num">${h.importe ? num(h.importe) : ""}</td><td>${esc(h.estado)}${h.resuelto_por ? `<div class="sub">${esc(h.resuelto_por)}</div>` : ""}</td>
      <td>${esc(h.responsable || "")}</td><td>${esc(h.accion_correctiva || "")}</td>
      <td>${editable && h.estado === "ABIERTO" ? `<button class="btn btn-sm" data-hs="${h.id}">Subsanar</button><button class="btn btn-sm" data-hd="${h.id}">Descartar</button><button class="btn btn-sm" data-hr="${h.id}">Asignar</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="8" class="vacio">Sin observaciones</td></tr>'}</tbody></table></div>
    ${editable && puedeX("comentar") ? `<form id="hx-form" class="card form-grid" style="margin-top:12px"><h3 style="grid-column:1/-1">Registrar hallazgo de revisión</h3>
      <label class="campo" style="grid-column:1/-1">Hallazgo <input name="titulo" minlength="5" required></label>
      <label class="campo">Severidad <select name="severidad"><option>ALTA</option><option selected>MEDIA</option><option>BAJA</option><option>INFORMATIVA</option></select></label>
      <label class="campo">Importe <input name="importe" type="number" step="0.01"></label><label class="campo">Responsable <input name="responsable"></label>
      <label class="campo" style="grid-column:1/-1">Acción correctiva <input name="accion_correctiva"></label>
      <div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Registrar</button></div></form>` : ""}`;
  const upd = async (hid, body) => { try { await api(`/anexos/hallazgos/${hid}`, { method: "PATCH", params: { empresa_id: estado.empresaId }, body }); navegar(); } catch (e) { toast(e.message, "err"); } };
  $$("[data-hs]").forEach((b) => b.addEventListener("click", () => upd(b.dataset.hs, { estado: "SUBSANADO", comentario: prompt("Comentario (opcional)") || null })));
  $$("[data-hd]").forEach((b) => b.addEventListener("click", () => { const c = prompt("Justifique el descarte (mínimo 10 caracteres)"); if (c) upd(b.dataset.hd, { estado: "DESCARTADO", comentario: c }); }));
  $$("[data-hr]").forEach((b) => b.addEventListener("click", () => { const u = prompt("Usuario responsable"); if (u) upd(b.dataset.hr, { responsable: u, accion_correctiva: prompt("Acción correctiva") || null }); }));
  $("#hx-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const x = datosForm(e.target);
    try { await api(`/anexos/anexos/${id}/hallazgos`, { method: "POST", params: { empresa_id: estado.empresaId }, body: { ...x, importe: x.importe || null } }); toast("Hallazgo registrado", "ok"); navegar(); } catch (er) { toast(er.message, "err"); }
  });
}

const CATS = ["FACTURA", "CONTRATO", "ESTADO_BANCARIO", "CONSTANCIA_DETRACCION", "COMPROBANTE_RETENCION", "CRONOGRAMA_FINANCIERO", "VALORIZACION", "ORDEN_SERVICIO", "INFORME_TECNICO", "LIQUIDACION", "DECLARACION_TRIBUTARIA", "ACTA", "ARQUEO", "OTRO"];
function formAdjunto(extra = "") {
  return `<form id="ad-form" class="card form-grid"><h3 style="grid-column:1/-1">Adjuntar documento sustentatorio</h3>
    <label class="campo">Archivo <input type="file" name="archivo" required></label>
    <label class="campo">Categoría <select name="categoria">${CATS.map((c) => `<option>${c}</option>`).join("")}</select></label>
    ${extra}
    <label class="campo">Tercero (RUC / DNI) <input name="tercero"></label><label class="campo">Documento (serie-número) <input name="documento" placeholder="F001-123"></label>
    <label class="campo">Clave de fila (opcional) <input name="clave_fila"></label><label class="campo" style="grid-column:1/-1">Descripción <input name="descripcion"></label>
    <label class="check"><input type="checkbox" name="confidencial"> Confidencial (datos personales)</label>
    <div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Adjuntar</button></div>
    <p class="sub" style="grid-column:1/-1">El documento se relaciona con la cuenta, el anexo, el tercero, el documento o la partida. Para que el anexo refleje el sustento, actualícelo (se crea una nueva versión).</p></form>`;
}
function enlazarAdjunto(fijos = {}) {
  $("#ad-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    fd.set("confidencial", e.target.confidencial.checked ? "true" : "false");
    Object.entries(fijos).forEach(([k, v]) => fd.set(k, v));
    try { await api("/anexos/adjuntos", { method: "POST", params: { empresa_id: estado.empresaId }, form: fd }); toast("Documento adjuntado", "ok"); navegar(); } catch (er) { toast(er.message, "err"); }
  });
}
const tablaAdjuntos = (lst) => `<div class="tabla-wrap"><table class="tabla"><thead><tr><th>Fecha</th><th>Categoría</th><th>Documento</th><th>Cuenta</th><th>Tercero</th><th>Doc.</th><th>Descripción</th><th>Usuario</th><th class="num">KB</th></tr></thead>
  <tbody>${lst.map((x) => `<tr><td>${fechaHora(x.creado_en)}</td><td>${esc(x.categoria)}</td><td><a href="#" data-adj="${x.id}">${esc(x.nombre)}</a>${x.confidencial ? ' <span class="badge b-warn">confidencial</span>' : ""}</td>
    <td>${esc(x.cuenta || "")}</td><td>${esc(x.tercero || "")}</td><td>${esc(x.documento || "")}</td><td>${esc(x.descripcion || "")}</td><td>${esc(x.usuario)}</td><td class="num">${Math.ceil(x.tamano / 1024)}</td></tr>`).join("") || '<tr><td colspan="9" class="vacio">Sin documentos</td></tr>'}</tbody></table></div>`;
const enlazarDescargas = () => $$("[data-adj]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); bajar(`/anexos/adjuntos/${a.dataset.adj}/descargar`, { empresa_id: estado.empresaId }).catch((er) => toast(er.message, "err")); }));

async function pestDocumentacion(cuerpo, d) {
  cuerpo.innerHTML = tablaAdjuntos(d.adjuntos) + (puedeX("adjuntar") ? formAdjunto() : "");
  enlazarDescargas();
  enlazarAdjunto({ anexo_id: d.anexo.id, cuenta: d.anexo.cuenta });
}

async function pestRevision(cuerpo, d) {
  const a = d.anexo;
  const ed = d.puede_editar;
  cuerpo.innerHTML = `<div class="grid grid-2"><form id="rv-form" class="card form-grid"><h2 style="grid-column:1/-1">Sección de revisión</h2>
      <label class="campo" style="grid-column:1/-1">Conclusión del contador<textarea name="conclusion" rows="4" ${ed ? "" : "disabled"}>${esc(a.conclusion || "")}</textarea></label>
      <label class="campo" style="grid-column:1/-1">Acciones correctivas<textarea name="acciones_correctivas" rows="3" ${ed ? "" : "disabled"}>${esc(a.acciones_correctivas || "")}</textarea></label>
      <label class="campo">Elaboración <input name="responsable_elaboracion" value="${esc(a.responsable_elaboracion || "")}" ${ed ? "" : "disabled"}></label>
      <label class="campo">Revisión <input name="responsable_revision" value="${esc(a.responsable_revision || "")}" ${ed ? "" : "disabled"}></label>
      <label class="campo">Aprobación <input name="responsable_aprobacion" value="${esc(a.responsable_aprobacion || "")}" ${ed ? "" : "disabled"}></label>
      <label class="campo">Fecha límite <input type="date" name="fecha_limite" value="${a.fecha_limite || ""}" ${ed ? "" : "disabled"}></label>
      ${ed ? '<div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Guardar</button></div>' : '<p class="sub" style="grid-column:1/-1">Versión aprobada o cerrada: inmutable. Requiere reapertura autorizada.</p>'}
      <p class="sub" style="grid-column:1/-1">Elaboró: ${esc(a.elaborado_por || "—")} · Revisó: ${esc(a.revisado_por || "—")} ${a.revisado_en ? fechaHora(a.revisado_en) : ""} · Aprobó: ${esc(a.aprobado_por || "—")} ${a.aprobado_en ? fechaHora(a.aprobado_en) : ""}</p></form>
    <div class="card"><h2>Comentarios</h2>${d.comentarios.map((c) => `<div class="obs-mini"><b>${esc(c.usuario)}</b> · ${fechaHora(c.creado_en)}<br>${esc(c.texto)}</div>`).join("") || '<p class="sub">Sin comentarios</p>'}
      ${puedeX("comentar") ? '<div class="acciones"><input id="cm-t" placeholder="Agregar comentario" style="flex:1"><button class="btn btn-sm" id="cm-ok">Comentar</button></div>' : ""}
      <h2>Historial del flujo</h2><div class="tabla-wrap" style="max-height:320px"><table class="tabla"><thead><tr><th>Fecha</th><th>Usuario</th><th>De → a</th><th>Comentario / cambios</th></tr></thead>
      <tbody>${d.revisiones.map((x) => `<tr><td class="nowrap">${fechaHora(x.creado_en)}</td><td>${esc(x.usuario)}${x.rol ? ` <span class="sub">${esc(x.rol)}</span>` : ""}</td><td>${esc(EST_X[x.de_estado]?.[0] || x.de_estado || "")} → ${esc(EST_X[x.a_estado]?.[0] || x.a_estado || "")}</td>
        <td>${esc(x.comentario || "")}${x.cambios ? `<div class="sub">${esc(x.cambios.slice(0, 300))}</div>` : ""}</td></tr>`).join("")}</tbody></table></div>
      ${d.aprobaciones.length ? `<h3 class="sec">Aprobaciones</h3>${d.aprobaciones.map((x) => `<div class="obs-mini">${esc(x.accion)} · ${esc(x.usuario)} · ${fechaHora(x.creado_en)}${x.comentario ? ` — ${esc(x.comentario)}` : ""}</div>`).join("")}` : ""}
      <p class="sub">Los vistos buenos del flujo no constituyen firmas digitales certificadas.</p></div></div>`;
  $("#rv-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const x = datosForm(e.target);
    try { await api(`/anexos/anexos/${a.id}`, { method: "PATCH", params: { empresa_id: estado.empresaId }, body: { ...x, fecha_limite: x.fecha_limite || null, lock_version: a.lock_version } }); toast("Revisión guardada", "ok"); navegar(); }
    catch (er) { toast(er.message, "err"); }
  });
  $("#cm-ok")?.addEventListener("click", async () => {
    const t = $("#cm-t").value.trim(); if (!t) return;
    try { await api(`/anexos/anexos/${a.id}/comentarios`, { method: "POST", params: { empresa_id: estado.empresaId }, body: { texto: t } }); navegar(); } catch (er) { toast(er.message, "err"); }
  });
}

async function pestVersiones(cuerpo, d) {
  const id = d.anexo.id;
  const c = vx.comparacion;
  const lista = (titulo, filas, cols) => `<h3 class="sec">${titulo} (${filas.length})</h3>${filas.length ? `<table class="tabla"><thead><tr>${cols.map(([, t]) => `<th>${t}</th>`).join("")}</tr></thead>
    <tbody>${filas.slice(0, 200).map((f) => `<tr>${cols.map(([k, , tp]) => `<td class="${tp ? "num" : ""}">${tp ? num(f[k]) : esc(f[k] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table>` : '<p class="sub">Ninguna</p>'}`;
  cuerpo.innerHTML = `<div class="card"><table class="tabla"><thead><tr><th>Versión</th><th>Generada</th><th>Por</th><th>Motivo</th><th class="num">Filas</th><th>Resultado</th><th class="num">Diferencia</th><th>Estado</th><th></th></tr></thead>
    <tbody>${d.versiones.map((v) => `<tr><td>${v.numero}</td><td>${fechaHora(v.generado_en)}</td><td>${esc(v.generado_por)}</td><td>${esc(v.motivo || "")}</td><td class="num">${v.filas}</td><td>${resX(v.resultado)}</td><td class="num">${num(v.diferencia)}</td>
      <td>${v.inmutable ? `<span class="badge b-ok">${esc(v.estado_al_cerrar || "Aprobada")} · inmutable</span>` : ""}</td><td>${v.id !== d.version?.id ? `<button class="btn btn-sm" data-cmp="version:${v.numero}">Comparar con la actual</button>` : "Actual"}</td></tr>`).join("")}</tbody></table>
    <div class="acciones" style="justify-content:flex-start"><button class="btn btn-sm" data-cmp="mes_anterior">Mes anterior</button><button class="btn btn-sm" data-cmp="ejercicio_anterior">Ejercicio anterior</button>
      <button class="btn btn-sm" data-cmp="original">Versión original</button><button class="btn btn-sm" data-cmp="aprobada">Última aprobada</button>
      <label>Otra fecha <input type="date" id="cmp-f"></label><button class="btn btn-sm" id="cmp-ok">Comparar</button></div></div>
    ${c ? `<div class="card" style="margin-top:12px"><h2>${esc(c.base)} → ${esc(c.actual)}</h2>${c.calculado_al_vuelo ? '<div class="alerta alerta-info">La referencia no tiene versión guardada: se calculó al vuelo con el mismo motor.</div>' : ""}
      <p>Total ${num(c.totales.base)} → ${num(c.totales.nueva)} (variación ${num(c.totales.variacion)}) · diferencia de conciliación ${num(c.resumen.base.diferencia)} → ${num(c.resumen.actual.diferencia)}</p>
      ${lista("Partidas nuevas", c.partidas_nuevas, [["documento", "Documento"], ["razon_social", "Tercero"], ["categoria", "Categoría"], ["saldo", "Saldo", 1]])}
      ${lista("Partidas canceladas", c.partidas_canceladas, [["documento", "Documento"], ["razon_social", "Tercero"], ["categoria", "Categoría"], ["saldo", "Saldo anterior", 1]])}
      ${lista("Cambios de importe", c.cambios_importe, [["documento", "Documento"], ["razon_social", "Tercero"], ["antes", "Antes", 1], ["despues", "Después", 1], ["variacion", "Variación", 1]])}
      ${lista("Reclasificaciones", c.reclasificaciones, [["documento", "Documento"], ["antes", "Antes"], ["despues", "Después"], ["saldo", "Saldo", 1]])}
      ${lista("Cambios de antigüedad", c.cambios_antiguedad, [["documento", "Documento"], ["antes", "Antes"], ["despues", "Después"], ["saldo", "Saldo", 1]])}
      ${lista("Observaciones nuevas", c.observaciones_nuevas, [["codigo", "Código"], ["titulo", "Observación"]])}
      ${lista("Observaciones subsanadas", c.observaciones_subsanadas, [["codigo", "Código"], ["titulo", "Observación"]])}</div>` : ""}`;
  const comparar = async (contra) => {
    try { vx.comparacion = await api(`/anexos/anexos/${id}/comparar`, { params: { empresa_id: estado.empresaId, contra } }); navegar(); } catch (e) { toast(e.message, "err"); }
  };
  $$("[data-cmp]").forEach((b) => b.addEventListener("click", () => comparar(b.dataset.cmp)));
  $("#cmp-ok").onclick = () => { const f = $("#cmp-f").value; if (f) comparar(`corte:${f}`); };
}

// ------------------------------------------------------------------ vista de impresión
rutas["anx-imprimir"] = async () => {
  if (!requiereEmpresa()) return;
  const p = parametrosHash();
  const id = Number(p.id);
  const [d, t] = await vigente(Promise.all([api(`/anexos/anexos/${id}`, { params: { empresa_id: estado.empresaId } }),
    api(`/anexos/anexos/${id}/detalle`, { params: { empresa_id: estado.empresaId, version_id: p.version_id, por_pagina: 2000 } })]));
  const a = d.anexo, r = d.resumen || {}, emp = estado.empresas.find((e) => e.id === estado.empresaId);
  const ver = d.versiones.find((v) => String(v.id) === String(p.version_id)) || d.versiones[0];
  const numerica = (c) => ["importe", "entero", "pct", "tasa"].includes(c.tipo);
  const cols = t.columnas;
  let filasHtml = "";
  if (t.grupos.length) {
    let i = 0;
    t.grupos.forEach((g) => {
      t.filas.slice(i, i + g.filas).forEach((f) => { filasHtml += `<tr>${cols.map((c) => `<td class="${numerica(c) ? "num" : ""}">${valorX(f[c.campo], c.tipo)}</td>`).join("")}</tr>`; });
      i += g.filas;
      filasHtml += `<tr class="sub-total">${cols.map((c, j) => `<td class="${numerica(c) ? "num" : ""}">${j === 0 ? `Subtotal ${esc(g.clave)}` : g.subtotales[c.campo] !== undefined ? num(g.subtotales[c.campo]) : ""}</td>`).join("")}</tr>`;
    });
  } else filasHtml = t.filas.map((f) => `<tr>${cols.map((c) => `<td class="${numerica(c) ? "num" : ""}">${valorX(f[c.campo], c.tipo)}</td>`).join("")}</tr>`).join("");
  vista().innerHTML = `<div class="no-imprimir acciones" style="justify-content:flex-start"><button class="btn btn-primario" onclick="window.print()">Imprimir</button><a class="btn" href="#/anx-ver?id=${id}">Volver al anexo</a>
      <span class="sub">Orientación de la plantilla: ${esc(d.plantilla?.orientacion || "HORIZONTAL")}</span></div>
    <div class="hoja-impresion ${d.plantilla?.orientacion === "VERTICAL" ? "vertical" : ""}">
      <div class="imp-cab"><img src="/api/anexos/logo?empresa_id=${estado.empresaId}" alt="" onerror="this.remove()"><div><b>${esc(emp?.razon_social || "")}</b><br>RUC ${esc(emp?.ruc || "")}</div>
        <div class="imp-ref">Versión ${ver?.numero ?? a.version_actual}${ver?.inmutable ? " (aprobada)" : ""}<br>Generado ${fechaHora(ver?.generado_en)}<br>Impreso ${fechaHora(new Date().toISOString())}</div></div>
      <h1>${esc(d.plantilla?.encabezado?.titulo || `Anexo — ${d.plantilla?.nombre || ""}`)} · Cuenta ${esc(a.cuenta)} ${esc(a.descripcion || "")}</h1>
      ${d.plantilla?.encabezado?.subtitulo ? `<p>${esc(d.plantilla.encabezado.subtitulo)}</p>` : ""}
      <p>Ejercicio ${a.ejercicio} · periodo ${String(a.periodo).padStart(2, "0")} · fecha de corte ${fecha(a.fecha_corte)} · moneda: soles (PEN) · estado ${esc(EST_X[a.estado_revision][0])} · ${esc(RES_X[a.resultado]?.[0] || "")}</p>
      <table class="tabla imp-res"><tr><td>Saldo inicial</td><td class="num">${num(r.saldo_inicial)}</td><td>Debe</td><td class="num">${num(r.debe)}</td><td>Haber</td><td class="num">${num(r.haber)}</td></tr>
        <tr><td>Saldo final contable</td><td class="num"><b>${num(r.saldo_final_contable)}</b></td><td>Saldo detallado</td><td class="num">${num(r.saldo_detalle)}</td><td>Sustentado</td><td class="num">${num(r.saldo_sustentado)}</td></tr>
        <tr><td>Sin sustento (valor absoluto)</td><td class="num">${num(r.pendiente_sustento_bruto ?? r.saldo_pendiente_sustento)}</td><td>Diferencia</td><td class="num"><b>${num(r.diferencia)}</b></td><td colspan="2">${esc(r.explicacion || "")}</td></tr></table>
      <table class="tabla imp-det"><thead><tr>${cols.map((c) => `<th class="${numerica(c) ? "num" : ""}">${esc(c.titulo)}</th>`).join("")}</tr></thead><tbody>${filasHtml}</tbody>
        <tfoot><tr>${cols.map((c, i) => `<td class="${numerica(c) ? "num" : ""}">${i === 0 ? "TOTAL" : t.totales[c.campo] !== undefined ? num(t.totales[c.campo]) : ""}</td>`).join("")}</tr></tfoot></table>
      <h3>Observaciones abiertas</h3>${d.hallazgos.filter((h) => h.estado === "ABIERTO").map((h) => `<p>[${esc(h.severidad)}] ${esc(h.titulo)}</p>`).join("") || "<p>Sin observaciones abiertas.</p>"}
      <p><b>Conclusión:</b> ${esc(a.conclusion || "—")}</p><p><b>Acciones correctivas:</b> ${esc(a.acciones_correctivas || "—")}</p>
      <div class="imp-firmas">${[["Elaborado por", a.responsable_elaboracion || a.elaborado_por], ["Revisado por", a.responsable_revision || a.revisado_por], ["Aprobado por", a.responsable_aprobacion || a.aprobado_por]]
        .map(([k, v]) => `<div><span>${k}</span><b>${esc(v || "")}</b></div>`).join("")}</div>
      <p class="sub">Espacios de visto bueno del flujo interno; no constituyen firmas digitales certificadas.</p></div>`;
};

// ------------------------------------------------------------------ plantillas y diseñador
rutas["anx-plantillas"] = async () => {
  if (!(await inicioAnx())) return;
  const pl = await vigente(api("/anexos/plantillas", { params: { empresa_id: estado.empresaId } }));
  const propias = pl.filter((p) => !p.sistema), sistema = pl.filter((p) => p.sistema);
  const fila = (p) => `<tr><td>${esc(p.codigo)}</td><td>${esc(p.nombre)}</td><td>${esc(p.especialidad)}</td><td>${esc(p.cuentas || "todas")}</td><td>${esc(p.tipo)}</td>
    <td>${p.sistema ? "Catálogo" : `${p.autorizada ? '<span class="badge b-ok">Autorizada</span>' : '<span class="badge b-warn">Por autorizar</span>'}${p.compartida ? ' <span class="badge b-info">Compartida</span>' : ""}`}</td><td>v${p.version}</td>
    <td><a class="btn btn-sm" href="#/anx-plantilla?id=${p.id}">${p.sistema ? "Ver" : "Editar"}</a>${puedeX("plantillas") ? ` <button class="btn btn-sm" data-dup="${p.id}">Duplicar</button>` : ""}
      ${!p.sistema && !p.autorizada && puedeX("autorizar_plantillas") ? ` <button class="btn btn-sm" data-aut="${p.id}">Autorizar</button>` : ""}</td></tr>`;
  const cab = '<thead><tr><th>Código</th><th>Nombre</th><th>Especialidad</th><th>Cuentas</th><th>Tipo</th><th>Estado</th><th>Versión</th><th></th></tr></thead>';
  vista().innerHTML = `<div class="cab-vista"><div><h1>Plantillas y diseñador de anexos</h1><p class="sub">El catálogo cubre todos los elementos del PCGE. Para personalizar un formato, duplíquelo o cree uno nuevo sin modificar el código fuente.</p></div>
      ${puedeX("plantillas") ? '<a class="btn btn-primario" href="#/anx-plantilla">Nueva plantilla</a>' : ""}</div>
    <div class="card"><h2>Plantillas de la empresa (${propias.length})</h2><div class="tabla-wrap"><table class="tabla">${cab}<tbody>${propias.map(fila).join("") || '<tr><td colspan="8" class="vacio">Sin plantillas propias</td></tr>'}</tbody></table></div></div>
    <div class="card" style="margin-top:12px"><h2>Catálogo del sistema (${sistema.length})</h2><div class="tabla-wrap tabla-alta"><table class="tabla">${cab}<tbody>${sistema.map(fila).join("")}</tbody></table></div></div>`;
  $$("[data-dup]").forEach((b) => b.addEventListener("click", async () => {
    const n = prompt("Nombre de la nueva plantilla"); if (!n) return;
    try { const r = await api(`/anexos/plantillas/${b.dataset.dup}/duplicar`, { method: "POST", params: { empresa_id: estado.empresaId }, body: { nombre: n } }); location.hash = `#/anx-plantilla?id=${r.id}`; } catch (e) { toast(e.message, "err"); }
  }));
  $$("[data-aut]").forEach((b) => b.addEventListener("click", async () => { try { await api(`/anexos/plantillas/${b.dataset.aut}/autorizar`, { method: "POST", params: { empresa_id: estado.empresaId } }); navegar(); } catch (e) { toast(e.message, "err"); } }));
};

const dz = { p: null };
rutas["anx-plantilla"] = async () => {
  if (!(await inicioAnx())) return;
  const id = Number(parametrosHash().id) || null;
  if (!dz.p || dz.p.id !== id) {
    dz.p = id ? await vigente(api(`/anexos/plantillas/${id}`, { params: { empresa_id: estado.empresaId } }))
      : { id: null, nombre: "", codigo: "", especialidad: "GENERICO", cuentas: "", columnas: [], formulas: [], reglas: [], agrupar_por: [], subtotales: [], filtros: [], orden: [],
        rangos_antiguedad: [[1, 30], [31, 60], [61, 90], [91, 180], [181, 365], [366, null]], encabezado: {}, orientacion: "HORIZONTAL", usar_logo: true, compartida: false, sistema: false };
  }
  const p = dz.p;
  const cat = await vigente(api(`/anexos/campos/${p.especialidad}`, { params: { empresa_id: estado.empresaId } }));
  const sel = new Map(p.columnas.map((c) => [c.campo, c]));
  const orden = [...p.columnas.map((c) => c.campo), ...cat.campos.map((c) => c.campo).filter((c) => !sel.has(c))];
  const info = Object.fromEntries(cat.campos.map((c) => [c.campo, c]));
  const soloLectura = p.sistema || !puedeX("plantillas");
  const opt = (v, lista) => lista.map((c) => `<option value="${c}" ${v === c ? "selected" : ""}>${esc(info[c]?.titulo || c)}</option>`).join("");
  vista().innerHTML = `<div class="cab-vista"><div><h1>${p.id ? `Plantilla ${esc(p.codigo)}` : "Nueva plantilla"}</h1><p class="sub">${p.sistema ? "Plantilla del catálogo (solo lectura): duplíquela para personalizarla." : "Diseñador: columnas, nombres, orden, agrupaciones, subtotales, filtros, campos calculados, rangos de antigüedad, encabezado y orientación."}</p></div>
      <a class="btn" href="#/anx-plantillas">Volver</a></div>
    <form id="dz" class="grid grid-2">
      <div class="card form-grid"><h2 style="grid-column:1/-1">Datos</h2>
        <label class="campo">Nombre <input name="nombre" value="${esc(p.nombre)}" required minlength="3"></label><label class="campo">Código <input name="codigo" value="${esc(p.codigo || "")}" ${p.id ? "disabled" : ""}></label>
        <label class="campo">Especialidad (origen de datos) <select name="especialidad" ${p.id ? "disabled" : ""}>${cat.especialidades.map((e) => `<option ${e === p.especialidad ? "selected" : ""}>${e}</option>`).join("")}</select></label>
        <label class="campo">Cuentas (prefijos) <input name="cuentas" value="${esc(p.cuentas || "")}" placeholder="12,13"></label>
        <label class="campo">Título del encabezado <input name="titulo" value="${esc(p.encabezado?.titulo || "")}"></label><label class="campo">Subtítulo <input name="subtitulo" value="${esc(p.encabezado?.subtitulo || "")}"></label>
        <label class="campo" style="grid-column:1/-1">Nota al pie <input name="nota" value="${esc(p.encabezado?.nota || "")}"></label>
        <label class="campo">Orientación <select name="orientacion"><option ${p.orientacion === "HORIZONTAL" ? "selected" : ""}>HORIZONTAL</option><option ${p.orientacion === "VERTICAL" ? "selected" : ""}>VERTICAL</option></select></label>
        <label class="check"><input type="checkbox" name="usar_logo" ${p.usar_logo ? "checked" : ""}> Incluir logotipo</label><label class="check"><input type="checkbox" name="compartida" ${p.compartida ? "checked" : ""}> Compartir con la empresa</label>
        <label class="campo" style="grid-column:1/-1">Rangos de antigüedad (días) <input name="rangos" value="${esc(p.rangos_antiguedad.map(([a, b]) => `${a}-${b ?? ""}`).join(", "))}"></label>
        <label class="campo">Agrupar por <select name="agrupar"><option value="">Sin agrupación</option>${opt(p.agrupar_por[0] || "", orden)}</select></label>
        <label class="campo">Ordenar por <select name="orden_c"><option value="">Orden natural</option>${opt((p.orden[0] || "").replace("-", ""), orden)}</select></label>
        <label class="check"><input type="checkbox" name="orden_desc" ${(p.orden[0] || "").startsWith("-") ? "checked" : ""}> Descendente</label>
        <label class="campo">Subtotales <select name="subtotal"><option value="saldo">Saldo</option>${opt(p.subtotales[0] || "", orden.filter((c) => info[c]?.tipo === "importe"))}</select></label></div>
      <div class="card"><h2>Columnas</h2><p class="sub">Marque, renombre y ordene las columnas. «Total» agrega totales y subtotales.</p>
        <div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th></th><th>Campo</th><th>Título</th><th>Total</th><th></th></tr></thead><tbody>${orden.map((c, i) => `<tr>
          <td><input type="checkbox" data-c="${c}" ${sel.has(c) ? "checked" : ""}></td><td><small>${esc(c)}</small> <span class="sub">${esc(info[c]?.tipo || "calculado")}</span></td>
          <td><input data-t="${c}" value="${esc(sel.get(c)?.titulo || info[c]?.titulo || c)}" size="22"></td><td>${info[c]?.tipo === "importe" ? `<input type="checkbox" data-tot="${c}" ${sel.get(c)?.total ? "checked" : ""}>` : ""}</td>
          <td><button type="button" class="tg" data-up="${i}">▲</button><button type="button" class="tg" data-dn="${i}">▼</button></td></tr>`).join("")}</tbody></table></div></div>
      <div class="card"><h2>Filtros de presentación</h2><div id="dz-fil">${p.filtros.map((f, i) => filaFiltro(f, i, orden, cat.operadores)).join("")}</div><button type="button" class="btn btn-sm" id="dz-fil-add">Agregar filtro</button>
        <p class="sub">Los filtros afectan la presentación; la conciliación siempre usa el detalle completo.</p></div>
      <div class="card"><h2>Campos calculados (motor seguro)</h2><p class="sub">Funciones: ${esc(cat.funciones.join(", "))}. Ejemplo: <code>SI(dias &gt; 90, saldo, 0)</code>. No se admite código ni SQL.</p>
        <div id="dz-for">${p.formulas.map((f, i) => filaFormula(f, i)).join("")}</div><button type="button" class="btn btn-sm" id="dz-for-add">Agregar campo calculado</button>
        <h3 class="sec">Reglas de validación</h3><div id="dz-reg">${p.reglas.map((r, i) => filaRegla(r, i)).join("")}</div><button type="button" class="btn btn-sm" id="dz-reg-add">Agregar regla</button></div>
      ${soloLectura ? "" : '<div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Guardar plantilla</button></div>'}
    </form>`;
  const leer = () => {
    const f = $("#dz");
    const columnas = orden.filter((c) => $(`[data-c="${c}"]`).checked).map((c) => ({ campo: c, titulo: $(`[data-t="${c}"]`).value.trim() || c, total: !!$(`[data-tot="${c}"]`)?.checked }));
    const rangos = f.rangos.value.split(",").map((x) => x.trim()).filter(Boolean).map((x) => { const [a, b] = x.split("-"); return [Number(a), b ? Number(b) : null]; });
    return { ...p, nombre: f.nombre.value.trim(), codigo: f.codigo.value.trim() || null, especialidad: f.especialidad.value, cuentas: f.cuentas.value.trim(), columnas,
      encabezado: { titulo: f.titulo.value.trim(), subtitulo: f.subtitulo.value.trim(), nota: f.nota.value.trim() }, orientacion: f.orientacion.value, usar_logo: f.usar_logo.checked,
      compartida: f.compartida.checked, rangos_antiguedad: rangos, agrupar_por: f.agrupar.value ? [f.agrupar.value] : [], subtotales: f.subtotal.value ? [f.subtotal.value] : [],
      orden: f.orden_c.value ? [(f.orden_desc.checked ? "-" : "") + f.orden_c.value] : [],
      filtros: $$("[data-fil]").map((r) => ({ campo: r.querySelector("[name=fc]").value, op: r.querySelector("[name=fo]").value, valor: r.querySelector("[name=fv]").value })),
      formulas: $$("[data-for]").map((r) => ({ campo: r.querySelector("[name=xc]").value.trim(), titulo: r.querySelector("[name=xt]").value.trim(), expresion: r.querySelector("[name=xe]").value.trim(), tipo: r.querySelector("[name=xp]").value })).filter((x) => x.campo),
      reglas: $$("[data-reg]").map((r) => ({ codigo: r.querySelector("[name=rc]").value.trim(), descripcion: r.querySelector("[name=rd]").value.trim(), tipo: "CONDICION_FILA", expresion: r.querySelector("[name=re]").value.trim(), severidad: r.querySelector("[name=rs]").value })).filter((x) => x.codigo) };
  };
  $("[name=especialidad]")?.addEventListener("change", (e) => { dz.p = { ...leer(), especialidad: e.target.value, columnas: [] }; navegar(); });
  $$("[data-up],[data-dn]").forEach((b) => b.addEventListener("click", () => {
    const cur = leer();
    const i = Number(b.dataset.up ?? b.dataset.dn), j = b.dataset.up !== undefined ? i - 1 : i + 1;
    if (j < 0 || j >= orden.length) return;
    [orden[i], orden[j]] = [orden[j], orden[i]];
    dz.p = { ...cur, columnas: orden.filter((c) => cur.columnas.some((x) => x.campo === c)).map((c) => cur.columnas.find((x) => x.campo === c)) };
    navegar();
  }));
  $("#dz-fil-add").onclick = () => { $("#dz-fil").insertAdjacentHTML("beforeend", filaFiltro({ campo: orden[0], op: "=", valor: "" }, Date.now(), orden, cat.operadores)); };
  $("#dz-for-add").onclick = () => { $("#dz-for").insertAdjacentHTML("beforeend", filaFormula({ campo: "", titulo: "", expresion: "", tipo: "importe" }, Date.now())); enlazarValidar(); };
  $("#dz-reg-add").onclick = () => { $("#dz-reg").insertAdjacentHTML("beforeend", filaRegla({ codigo: "", descripcion: "", expresion: "", severidad: "MEDIA" }, Date.now())); };
  const enlazarValidar = () => $$("[data-val]").forEach((b) => { b.onclick = async () => {
    const r = b.closest("[data-for]");
    const x = await api("/anexos/formulas/validar", { method: "POST", params: { empresa_id: estado.empresaId }, body: { especialidad: p.especialidad, expresion: r.querySelector("[name=xe]").value } });
    r.querySelector(".val").innerHTML = x.valida ? '<span class="badge b-ok">Válida</span>' : `<span class="badge b-err">${esc(x.error)}</span>`;
  }; });
  enlazarValidar();
  $("#dz").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = leer();
    try {
      const r = await api(p.id ? `/anexos/plantillas/${p.id}` : "/anexos/plantillas", { method: p.id ? "PUT" : "POST", params: { empresa_id: estado.empresaId }, body });
      toast(`Plantilla guardada (v${r.version})${r.autorizada ? "" : " — pendiente de autorización"}`, "ok"); dz.p = null; location.hash = `#/anx-plantilla?id=${r.id}`;
    } catch (er) { toast(er.message, "err"); }
  });
};
function filaFiltro(f, i, campos, ops) {
  return `<div class="filtros" data-fil="${i}"><select name="fc">${campos.map((c) => `<option ${c === f.campo ? "selected" : ""}>${c}</option>`).join("")}</select>
    <select name="fo">${ops.map((o) => `<option ${o === f.op ? "selected" : ""}>${o}</option>`).join("")}</select><input name="fv" value="${esc(f.valor ?? "")}" size="14">
    <button type="button" class="btn btn-sm" onclick="this.parentElement.remove()">Quitar</button></div>`;
}
function filaFormula(f, i) {
  return `<div class="filtros" data-for="${i}"><input name="xc" placeholder="campo" value="${esc(f.campo)}" size="12"><input name="xt" placeholder="título" value="${esc(f.titulo)}" size="14">
    <input name="xe" placeholder="expresión" value="${esc(f.expresion)}" size="34"><select name="xp">${["importe", "texto", "entero", "pct"].map((t) => `<option ${t === f.tipo ? "selected" : ""}>${t}</option>`).join("")}</select>
    <button type="button" class="btn btn-sm" data-val>Validar</button><span class="val"></span><button type="button" class="btn btn-sm" onclick="this.parentElement.remove()">Quitar</button></div>`;
}
function filaRegla(r, i) {
  return `<div class="filtros" data-reg="${i}"><input name="rc" placeholder="código" value="${esc(r.codigo)}" size="10"><input name="rd" placeholder="descripción" value="${esc(r.descripcion)}" size="22">
    <input name="re" placeholder="condición, p. ej. dias > 365" value="${esc(r.expresion || "")}" size="26"><select name="rs">${["ALTA", "MEDIA", "BAJA", "INFORMATIVA"].map((s) => `<option ${s === r.severidad ? "selected" : ""}>${s}</option>`).join("")}</select>
    <button type="button" class="btn btn-sm" onclick="this.parentElement.remove()">Quitar</button></div>`;
}

// ------------------------------------------------------------------ documentación, exportaciones, registros, responsables
const fd = { cuenta: "", categoria: "" };
rutas["anx-docs"] = async () => {
  if (!(await inicioAnx())) return;
  const r = await vigente(api("/anexos/adjuntos", { params: { empresa_id: estado.empresaId, cuenta: fd.cuenta, categoria: fd.categoria, por_pagina: 300 } }));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Documentación sustentatoria</h1><p class="sub">Facturas, contratos, estados bancarios, constancias, cronogramas, valorizaciones, liquidaciones, declaraciones y otros sustentos, con su trazabilidad.</p></div></div>
    <div class="filtros card"><label>Cuenta <input id="fd-c" value="${esc(fd.cuenta)}" size="8"></label><label>Categoría <select id="fd-k"><option value="">Todas</option>${r.categorias.map((c) => `<option ${c === fd.categoria ? "selected" : ""}>${c}</option>`).join("")}</select></label>
      <button class="btn btn-sm btn-primario" id="fd-ir">Filtrar</button><span class="sub">${r.total} documentos</span></div>
    ${tablaAdjuntos(r.items)}${puedeX("adjuntar") ? formAdjunto('<label class="campo">Cuenta <input name="cuenta" required></label>') : ""}`;
  $("#fd-ir").onclick = () => { fd.cuenta = $("#fd-c").value.trim(); fd.categoria = $("#fd-k").value; navegar(); };
  enlazarDescargas();
  enlazarAdjunto();
};

rutas["anx-export"] = async () => {
  if (!(await inicioAnx())) return;
  const jobs = await vigente(api("/anexos/exportaciones", { params: { empresa_id: estado.empresaId } }));
  vista().innerHTML = `<div class="cab-vista"><div><h1>Centro de exportaciones</h1><p class="sub">Libro Excel con índice, resumen, balance de comprobación, una hoja por anexo, diferencias, observaciones y control de revisión; expediente de cierre en PDF.</p></div></div>
    ${barraX()}
    <form id="ex-form" class="card filtros"><label>Tipo <select name="tipo"><option value="LIBRO_EXCEL">Libro Excel de anexos</option><option value="EXPEDIENTE_PDF">Expediente de cierre (PDF)</option></select></label>
      <label>Cuenta (prefijo) <input name="cuenta" size="8"></label><label class="check"><input type="checkbox" name="solo_aprobados"> Solo aprobados o cerrados</label>
      <button class="btn btn-primario">Exportar anexos al ${fecha(ctxX.corte)}</button></form><div id="ex-prog"></div>
    <div class="card"><table class="tabla"><thead><tr><th>#</th><th>Tipo</th><th>Estado</th><th class="num">Anexos</th><th class="num">KB</th><th class="num">ms</th><th>Usuario</th><th>Fecha</th><th></th></tr></thead>
      <tbody>${jobs.map((j) => `<tr><td>${j.id}</td><td>${j.tipo === "LIBRO_EXCEL" ? "Libro Excel" : "Expediente PDF"}</td><td>${esc(j.estado)}${j.error ? ` <span class="sub">${esc(j.error.slice(0, 80))}</span>` : ""}</td><td class="num">${j.anexos}</td>
        <td class="num">${j.tamano ? Math.ceil(j.tamano / 1024) : ""}</td><td class="num">${j.duracion_ms ?? ""}</td><td>${esc(j.usuario)}</td><td>${fechaHora(j.creado_en)}</td>
        <td>${j.estado === "COMPLETADO" ? `<button class="btn btn-sm" data-dl="${j.id}">Descargar</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="9" class="vacio">Sin exportaciones</td></tr>'}</tbody></table></div>`;
  enlazarX();
  $("#ex-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    try {
      const r = await api("/anexos/exportaciones", { method: "POST", params: { empresa_id: estado.empresaId }, body: { tipo: f.tipo.value, fecha_corte: ctxX.corte, cuenta: f.cuenta.value.trim() || null, solo_aprobados: f.solo_aprobados.checked } });
      $("#ex-prog").innerHTML = `<div class="card">${barraProgreso(0, "En cola")}</div>`;
      await esperarTrabajo(r.trabajo, (t) => { const b = $("#ex-prog .progreso"); if (b) { b.querySelector(".progreso-barra").style.width = `${Math.max(2, t.progreso)}%`; $("#ex-prog .progreso-txt").innerHTML = `<span>${esc(t.etapa)}</span><b>${t.progreso}%</b>`; } });
      toast("Exportación lista", "ok"); navegar();
    } catch (er) { toast(er.message, "err"); navegar(); }
  });
  $$("[data-dl]").forEach((b) => b.addEventListener("click", () => bajar(`/anexos/exportaciones/${b.dataset.dl}/descargar`, { empresa_id: estado.empresaId }).catch((e) => toast(e.message, "err"))));
};

const fr = { tipo: "ACTIVO_FIJO" };
rutas["anx-registros"] = async () => {
  if (!(await inicioAnx())) return;
  const r = await vigente(api("/anexos/registros", { params: { empresa_id: estado.empresaId, tipo: fr.tipo } }));
  const claves = [...new Set(r.items.flatMap((x) => Object.keys(x.datos)))].slice(0, 12);
  vista().innerHTML = `<div class="cab-vista"><div><h1>Registros auxiliares</h1><p class="sub">Información de soporte que entrega el ERP o el área responsable. El sistema no la genera: sin estos registros, los anexos especializados se arman desde el libro e indican la falta.</p></div></div>
    <div class="pestanas">${Object.entries(TIPOS_REG).map(([k, v]) => `<button class="btn ${fr.tipo === k ? "btn-primario" : ""}" data-tr="${k}">${v}</button>`).join("")}</div>
    ${puedeX("registros") ? `<form id="rg-form" class="card filtros"><label>Archivo CSV / XLSX <input type="file" name="archivo" required></label><button class="btn btn-primario">Importar ${esc(TIPOS_REG[fr.tipo])}</button>
      <span class="sub">Columnas obligatorias: ${esc(r.tipos[fr.tipo].join(", "))}</span></form><div id="rg-res"></div>` : ""}
    <div class="card"><div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th>Clave</th><th>Cuenta</th><th>Fecha ref.</th>${claves.map((k) => `<th>${esc(k)}</th>`).join("")}<th>Archivo</th><th>Vigente</th><th></th></tr></thead>
      <tbody>${r.items.map((x) => `<tr><td>${esc(x.clave)}</td><td>${esc(x.cuenta || "")}</td><td>${x.fecha_referencia ? fecha(x.fecha_referencia) : ""}</td>${claves.map((k) => `<td>${esc(x.datos[k] ?? "")}</td>`).join("")}
        <td><small>${esc(x.archivo || "")} fila ${x.fila ?? ""}</small></td><td>${x.vigente ? "Sí" : "No"}</td><td>${x.vigente && puedeX("registros") ? `<button class="btn btn-sm" data-an="${x.id}">Anular</button>` : ""}</td></tr>`).join("") || `<tr><td colspan="${claves.length + 6}" class="vacio">Sin registros</td></tr>`}</tbody></table></div></div>`;
  $$("[data-tr]").forEach((b) => b.addEventListener("click", () => { fr.tipo = b.dataset.tr; navegar(); }));
  $("#rg-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fdata = new FormData(e.target); fdata.set("tipo", fr.tipo);
    try {
      const x = await api("/anexos/registros/importar", { method: "POST", params: { empresa_id: estado.empresaId }, form: fdata });
      toast(`${x.nuevos} nuevos · ${x.actualizados} actualizados`, x.errores.length ? "err" : "ok");
      if (x.errores.length) { $("#rg-res").innerHTML = `<div class="alerta alerta-warn">${x.errores.map(esc).join("<br>")}</div>`; return; }
      navegar();
    } catch (er) { toast(er.message, "err"); }
  });
  $$("[data-an]").forEach((b) => b.addEventListener("click", async () => { if (!confirm("El registro dejará de usarse en nuevas versiones (se conserva para la trazabilidad).")) return; try { await api(`/anexos/registros/${b.dataset.an}/anular`, { method: "POST", params: { empresa_id: estado.empresaId } }); navegar(); } catch (e) { toast(e.message, "err"); } }));
};

rutas["anx-config"] = async () => {
  if (!(await inicioAnx())) return;
  const [cfg, asg] = await vigente(Promise.all([api("/anexos/configuracion", { params: { empresa_id: estado.empresaId } }), api("/anexos/asignaciones", { params: { empresa_id: estado.empresaId } })]));
  const aa = cfg.aprobacion_automatica || {};
  vista().innerHTML = `<div class="cab-vista"><div><h1>Responsables y políticas</h1><p class="sub">Los roles se administran por empresa (compartidos con la compensación). Aquí se asignan responsables por cuenta, fechas límite, accesos por cuenta y políticas de aprobación.</p></div>
      <a class="btn" href="#/comp-config">Roles de usuario</a></div>
    <div class="grid grid-2">
      <form id="cf-form" class="card form-grid"><h2 style="grid-column:1/-1">Políticas</h2>
        <label class="check" style="grid-column:1/-1"><input type="checkbox" name="separacion" ${cfg.separacion_funciones ? "checked" : ""}> Separación de funciones: quien elabora no aprueba</label>
        <label class="campo">Tolerancia de conciliación (S/) <input name="tolerancia" type="number" min="0" step="0.01" value="${esc(cfg.tolerancia)}"></label>
        <label class="check" style="grid-column:1/-1"><input type="checkbox" name="auto" ${aa.activa ? "checked" : ""}> Aprobación automática de anexos CUADRADOS y sin observaciones (requiere autorización)</label>
        ${aa.activa ? `<p class="sub" style="grid-column:1/-1">Autorizada por ${esc(aa.autorizada_por || "")} el ${fechaHora(aa.autorizada_en)}</p>` : ""}
        ${puedeX("configurar") ? '<div class="acciones" style="grid-column:1/-1"><button class="btn btn-primario">Guardar políticas</button></div>' : ""}
        <h3 style="grid-column:1/-1">Logotipo</h3><img src="/api/anexos/logo?empresa_id=${estado.empresaId}&t=${Date.now()}" alt="Sin logotipo" style="max-height:56px;grid-column:1/-1" onerror="this.replaceWith(document.createTextNode('Sin logotipo'))">
        ${puedeX("configurar") ? '<label class="campo">PNG o JPG (máx. 1 MB) <input type="file" id="cf-logo" accept="image/png,image/jpeg"></label><button type="button" class="btn btn-sm" id="cf-logo-ok">Subir logotipo</button>' : ""}</form>
      <div class="card"><h2>Asignaciones</h2><table class="tabla"><thead><tr><th>Tipo</th><th>Usuario</th><th>Cuenta / anexo</th><th>Fecha límite</th><th>Asignó</th><th></th></tr></thead>
        <tbody>${asg.map((x) => `<tr><td>${esc(x.tipo)}</td><td>${esc(x.usuario)}</td><td>${esc(x.cuenta || `anexo #${x.anexo_id}`)}</td><td>${x.fecha_limite ? fecha(x.fecha_limite) : ""}</td><td>${esc(x.asignado_por)}</td>
          <td>${puedeX("asignar") ? `<button class="btn btn-sm" data-des="${x.id}">Desactivar</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="6" class="vacio">Sin asignaciones</td></tr>'}</tbody></table>
        ${puedeX("asignar") ? `<form id="as-form" class="filtros"><select name="tipo"><option value="ELABORACION">Elaboración</option><option value="REVISION">Revisión</option><option value="APROBACION">Aprobación</option>${puedeX("configurar") ? '<option value="ACCESO">Acceso por cuenta</option>' : ""}</select>
          <input name="usuario" placeholder="usuario" required size="12"><input name="cuenta" placeholder="cuenta (prefijo)" required size="10"><input type="date" name="fecha_limite"><button class="btn btn-sm btn-primario">Asignar</button></form>
          <p class="sub">«Acceso por cuenta» restringe a un usuario (no supervisor) a las cuentas indicadas.</p>` : ""}</div></div>`;
  $("#cf-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    try { await api("/anexos/configuracion", { method: "PUT", params: { empresa_id: estado.empresaId }, body: { separacion_funciones: f.separacion.checked, tolerancia: f.tolerancia.value || "0", aprobacion_automatica: { activa: f.auto.checked, resultados: ["CUADRADO"] } } }); toast("Políticas guardadas", "ok"); navegar(); }
    catch (er) { toast(er.message, "err"); }
  });
  $("#cf-logo-ok")?.addEventListener("click", async () => {
    const a = $("#cf-logo").files[0]; if (!a) return;
    const fdata = new FormData(); fdata.append("archivo", a);
    try { await api("/anexos/logo", { method: "POST", params: { empresa_id: estado.empresaId }, form: fdata }); toast("Logotipo actualizado", "ok"); navegar(); } catch (er) { toast(er.message, "err"); }
  });
  $("#as-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const x = datosForm(e.target);
    try { await api("/anexos/asignaciones", { method: "POST", params: { empresa_id: estado.empresaId }, body: { ...x, fecha_limite: x.fecha_limite || null } }); toast("Asignación registrada", "ok"); navegar(); } catch (er) { toast(er.message, "err"); }
  });
  $$("[data-des]").forEach((b) => b.addEventListener("click", async () => { try { await api(`/anexos/asignaciones/${b.dataset.des}/desactivar`, { method: "POST", params: { empresa_id: estado.empresaId } }); navegar(); } catch (e) { toast(e.message, "err"); } }));
};
