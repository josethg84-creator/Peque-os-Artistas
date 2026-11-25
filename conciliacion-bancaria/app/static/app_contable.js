/* Analizador contable (fase 2): asistente de importación, lotes, plantillas, reglas y datos maestros.
   Reutiliza los utilitarios globales de app.js (api, esc, toast, abrirModal, rutas, vista, vigente…). */
"use strict";

const SEVERIDADES = [
  ["CRITICO", "Crítico", "sev-c"], ["ALTO", "Alto", "sev-a"], ["MEDIO", "Medio", "sev-m"], ["INFORMATIVO", "Informativo", "sev-i"],
];
const NOMBRE_SEV = Object.fromEntries(SEVERIDADES.map(([k, n]) => [k, n]));
const CLASE_SEV = Object.fromEntries(SEVERIDADES.map(([k, , c]) => [k, c]));
let catalogo = null;

async function cargarCatalogo() {
  if (!catalogo) catalogo = await api("/contable/catalogo");
  return catalogo;
}
const tipoDef = (clave) => catalogo.tipos.find((t) => t.clave === clave);
const badgeSev = (s) => `<span class="badge ${CLASE_SEV[s] || ""}">${esc(NOMBRE_SEV[s] || s)}</span>`;
const nombrePeriodo = (p) => (p === null || p === undefined ? "Anual" : p === 0 ? "00 Apertura" : p === 13 ? "13 Cierre" : String(p).padStart(2, "0"));
const tamano = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${(b / 1024).toFixed(1)} KB`);

function barraProgreso(pct, etapa) {
  return `<div class="progreso"><div class="progreso-barra" style="width:${Math.max(2, pct)}%"></div></div>
          <div class="progreso-txt"><span>${esc(etapa || "")}</span><b>${pct}%</b></div>`;
}

function chipsSeveridad(sev, activo, atributo = "data-sev") {
  return `<div class="chips">${SEVERIDADES.map(([k, n, c]) => `
    <button class="chip ${c} ${activo === k ? "activo" : ""}" ${atributo}="${k}"><b>${sev?.[k] ?? 0}</b> ${n}</button>`).join("")}
    ${activo ? `<button class="chip" ${atributo}="">Todas</button>` : ""}</div>`;
}

function tablaObservaciones(items) {
  if (!items.length) return `<div class="vacio">Sin observaciones con estos filtros</div>`;
  return `<table class="tabla tabla-obs"><thead><tr><th>Severidad</th><th>Código</th><th>Archivo / hoja</th><th class="num">Fila</th>
    <th>Cuenta</th><th>Asiento</th><th>Documento</th><th>Campo / valor</th><th>Descripción</th><th>Recomendación</th></tr></thead><tbody>
    ${items.map((o) => `<tr>
      <td>${badgeSev(o.severidad)}</td><td><code>${esc(o.codigo)}</code></td>
      <td><small>${esc(o.archivo || "")}<br>${esc(o.hoja || "")}</small></td><td class="num">${o.fila ?? "—"}</td>
      <td>${esc(o.cuenta || "")}</td><td>${esc(o.asiento || "")}</td><td>${esc(o.documento || "")}</td>
      <td><small>${esc(o.campo || "")}${o.valor ? `<br><code>${esc(o.valor)}</code>` : ""}</small></td>
      <td>${esc(o.mensaje)}</td><td><small class="sub">${esc(o.recomendacion || "")}</small></td></tr>`).join("")}</tbody></table>`;
}

async function esperarTrabajo(trabajo, alAvanzar) {
  let t = trabajo;
  while (t.estado === "EN_COLA" || t.estado === "PROCESANDO") {
    alAvanzar(t);
    await new Promise((r) => setTimeout(r, 300));
    t = await api(`/contable/trabajos/${t.id}`);
  }
  alAvanzar(t);
  if (t.estado === "ERROR") { const e = new Error(t.error); e.status = t.status; throw e; }
  return t.resultado;
}

function subirConProgreso(ruta, form, alAvanzar) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api" + ruta);
    xhr.setRequestHeader("X-Usuario", encodeURIComponent(usuario()));
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) alAvanzar(Math.round((e.loaded / e.total) * 100)); };
    xhr.onload = () => {
      let datos = null;
      try { datos = JSON.parse(xhr.responseText); } catch { /* respuesta no JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(datos);
      else reject(new Error(typeof datos?.detail === "string" ? datos.detail : `Error ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("Error de red al subir el archivo"));
    xhr.send(form);
  });
}

// =====================================================================  asistente
const PASOS = ["Empresa y periodo", "Tipo de información", "Cargar archivo", "Hoja y encabezados",
  "Homologar columnas", "Validar información", "Confirmar importación"];
const ci = {
  paso: 1, ejercicio: new Date().getFullYear(), periodo: new Date().getMonth() + 1, sistema: "GENERICO", tipo: null,
  meta: null, hoja: null, previa: null, fila_encabezado: 1, filas_encabezado: 1, delimitador: "AUTO",
  separador_decimal: "AUTO", formato_fecha: "AUTO", importacion_completa: true, hom: null, mapeo: {}, plantilla_id: null,
  validacion: null, obs: { severidad: "", codigo: "", texto: "", pagina: 1 }, lote: null,
};

function reiniciarAsistente(mantenerPeriodo = true) {
  if (ci.meta) api(`/contable/archivos/${ci.meta.token}`, { method: "DELETE" }).catch(() => {});
  Object.assign(ci, { paso: mantenerPeriodo ? 2 : 1, tipo: null, meta: null, hoja: null, previa: null, hom: null,
    mapeo: {}, plantilla_id: null, validacion: null, lote: null, fila_encabezado: 1, filas_encabezado: 1 });
}

function parametros(extra = {}) {
  return {
    empresa_id: estado.empresaId, tipo: ci.tipo, ejercicio: Number(ci.ejercicio) || null,
    periodo: ci.periodo === "" || ci.periodo === null ? null : Number(ci.periodo), sistema_origen: ci.sistema,
    hoja: ci.hoja, fila_encabezado: Number(ci.fila_encabezado), filas_encabezado: Number(ci.filas_encabezado),
    delimitador: ci.delimitador, separador_decimal: ci.separador_decimal, formato_fecha: ci.formato_fecha,
    mapeo: ci.mapeo, importacion_completa: ci.importacion_completa, plantilla_id: ci.plantilla_id, ...extra,
  };
}

rutas["contable-importar"] = async () => {
  if (!requiereEmpresa()) return;
  await vigente(cargarCatalogo());
  if (ci.empresaId !== estado.empresaId) { reiniciarAsistente(false); ci.empresaId = estado.empresaId; }
  if (ci.paso === 7 && ci.lote) reiniciarAsistente();
  pintarAsistente();
};

function pintarAsistente() {
  const emp = estado.empresas.find((e) => e.id === estado.empresaId);
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Importar información contable</h1>
      <p class="sub">${esc(emp?.razon_social)} · ${ci.tipo ? esc(tipoDef(ci.tipo).nombre) + " · " : ""}${ci.ejercicio || ""} ${ci.tipo && !tipoDef(ci.tipo).transaccional ? "" : "· periodo " + nombrePeriodo(ci.periodo === "" ? null : Number(ci.periodo))}</p></div>
      ${ci.paso > 1 ? `<button class="btn" id="ci-reiniciar">Empezar de nuevo</button>` : ""}</div>
    <ol class="asistente">${PASOS.map((t, i) => {
      const n = i + 1, cls = n === ci.paso ? "activo" : n < ci.paso ? "hecho" : "";
      return `<li class="${cls}" ${n < ci.paso ? `data-ir="${n}"` : ""}><span class="n">${n < ci.paso ? "✓" : n}</span><span>${t}</span></li>`;
    }).join("")}</ol>
    <div id="ci-cuerpo"></div>`;
  $("#ci-reiniciar")?.addEventListener("click", () => { reiniciarAsistente(false); pintarAsistente(); });
  $$("[data-ir]").forEach((li) => li.addEventListener("click", () => irPaso(Number(li.dataset.ir))));
  ({ 1: paso1, 2: paso2, 3: paso3, 4: paso4, 5: paso5, 6: paso6, 7: paso7 })[ci.paso]();
}

function irPaso(n) {
  if (n <= 5) ci.validacion = null;  // cambiar homologación u opciones invalida la validación previa
  ci.paso = n;
  pintarAsistente();
}
const cuerpo = () => $("#ci-cuerpo");

function paso1() {
  cuerpo().innerHTML = `<div class="card">
    <div class="form-grid">
      <div class="campo"><label>Empresa</label><input disabled value="${esc(estado.empresas.find((e) => e.id === estado.empresaId)?.razon_social)}"><small>Cámbiela en la barra superior.</small></div>
      <div class="campo"><label>Ejercicio</label><input id="c-ej" type="number" min="1990" max="2100" value="${esc(ci.ejercicio)}"></div>
      <div class="campo"><label>Periodo contable</label><select id="c-per">
        <option value="">Anual / acumulado</option>
        ${catalogo.periodos.map((p) => `<option value="${p.valor}" ${String(ci.periodo) === String(p.valor) ? "selected" : ""}>${p.nombre}</option>`).join("")}</select></div>
      <div class="campo"><label>Sistema contable de origen</label><select id="c-sis">
        ${catalogo.sistemas.map((s) => `<option value="${s.clave}" ${ci.sistema === s.clave ? "selected" : ""}>${esc(s.nombre)}</option>`).join("")}</select>
        <small>Se usa para sugerir plantillas y para interpretar claves debe/haber (p. ej. 40/50 en SAP).</small></div>
    </div>
    <div class="acciones"><button class="btn btn-primario" id="c-sig">Continuar</button></div></div>`;
  $("#c-sig").onclick = () => {
    const ej = Number($("#c-ej").value);
    if (!ej || ej < 1990 || ej > 2100) { toast("Indique un ejercicio válido", "err"); return; }
    Object.assign(ci, { ejercicio: ej, periodo: $("#c-per").value, sistema: $("#c-sis").value });
    irPaso(2);
  };
}

function paso2() {
  cuerpo().innerHTML = `<div class="tipos-grid">${catalogo.tipos.map((t) => `
    <button class="tipo-card ${ci.tipo === t.clave ? "activo" : ""}" data-tipo="${t.clave}">
      <b>${esc(t.nombre)}</b><span>${esc(t.descripcion)}</span>
      <small>Obligatorio: ${t.requeridos.map((g) => g.map((c) => t.campos.find((x) => x.clave === c).etiqueta).join(" o ")).join(" · ")}</small>
    </button>`).join("")}</div>`;
  $$("[data-tipo]").forEach((b) => b.addEventListener("click", () => {
    if (ci.tipo !== b.dataset.tipo) Object.assign(ci, { hom: null, mapeo: {}, plantilla_id: null });
    ci.tipo = b.dataset.tipo;
    ci.importacion_completa = tipoDef(ci.tipo).admite_completa && ci.tipo !== "MAYOR";
    irPaso(ci.meta ? 4 : 3);
  }));
}

function paso3() {
  cuerpo().innerHTML = `<div class="card">
    <div id="ci-drop" class="dropzone">
      <input type="file" id="ci-file" accept=".xlsx,.xlsm,.xls,.csv,.txt,.tsv" hidden>
      <strong>Arrastre el archivo aquí</strong> o haga clic para seleccionarlo
      <div><small>XLSX · XLS · CSV · TXT estructurado (delimitado por «;», «,», tabulador o «|»)</small></div>
    </div>
    <div id="ci-subida"></div>
    ${ci.meta ? fichaArchivo(ci.meta) : ""}
    <div class="acciones"><button class="btn" id="ci-atras">Atrás</button>
      <button class="btn btn-primario" id="ci-sig" ${ci.meta ? "" : "disabled"}>Continuar</button></div></div>`;
  const drop = $("#ci-drop"), input = $("#ci-file");
  drop.onclick = () => input.click();
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("sobre"); };
  drop.ondragleave = () => drop.classList.remove("sobre");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("sobre"); subirArchivo(e.dataTransfer.files[0]); };
  input.onchange = () => subirArchivo(input.files[0]);
  $("#ci-atras").onclick = () => irPaso(2);
  $("#ci-sig").onclick = () => irPaso(4);
}

function fichaArchivo(m) {
  return `<div class="alerta alerta-ok"><b>${esc(m.nombre)}</b> · ${esc(m.formato)} · ${tamano(m.tamano)} ·
    ${m.hojas.length} hoja(s) · huella SHA-256 <code>${esc(m.hash.slice(0, 12))}…</code></div>`;
}

async function subirArchivo(archivo) {
  if (!archivo) return;
  const caja = $("#ci-subida");
  caja.innerHTML = barraProgreso(0, `Subiendo ${archivo.name}`);
  const form = new FormData();
  form.append("archivo", archivo);
  form.append("empresa_id", estado.empresaId);
  try {
    const meta = await subirConProgreso("/contable/archivos", form, (pct) => {
      caja.innerHTML = barraProgreso(pct, pct < 100 ? `Subiendo ${archivo.name}` : "Analizando estructura del archivo…");
    });
    if (ci.meta) api(`/contable/archivos/${ci.meta.token}`, { method: "DELETE" }).catch(() => {});
    Object.assign(ci, { meta, hoja: meta.hojas[0].nombre, previa: null, hom: null, mapeo: {}, validacion: null, plantilla_id: null });
    toast("Archivo cargado", "ok");
    irPaso(4);
  } catch (err) {
    caja.innerHTML = `<div class="alerta alerta-err"><b>Archivo estructuralmente inválido o no admitido.</b> ${esc(err.message)}</div>`;
  }
}

async function paso4() {
  cuerpo().innerHTML = `<div class="card"><div class="vacio">Leyendo hoja…</div></div>`;
  try {
    const sugerir = !ci.previa || ci.previa.hoja !== ci.hoja || ci.previa._tipo !== ci.tipo;
    ci.previa = await api(`/contable/archivos/${ci.meta.token}/vista-previa`, { params: { tipo: ci.tipo, hoja: ci.hoja, delimitador: ci.delimitador } });
    ci.previa._tipo = ci.tipo;
    if (sugerir) { ci.fila_encabezado = ci.previa.sugerencia_encabezado.fila; ci.filas_encabezado = ci.previa.sugerencia_encabezado.filas; }
  } catch (err) { cuerpo().innerHTML = `<div class="alerta alerta-err">${esc(err.message)}</div>`; return; }
  const p = ci.previa, sug = p.sugerencia_encabezado, esTexto = ["CSV", "TXT"].includes(ci.meta.formato);
  const ancho = Math.max(...p.filas.map((f) => f.length), 1);
  cuerpo().innerHTML = `<div class="card">
    ${fichaArchivo(ci.meta)}
    <div class="form-grid">
      ${ci.meta.hojas.length > 1 || !esTexto ? `<div class="campo"><label>Hoja de Excel</label><select id="c-hoja">${ci.meta.hojas.map((h) => `<option ${h.nombre === ci.hoja ? "selected" : ""} value="${esc(h.nombre)}">${esc(h.nombre)} (${h.filas} filas)</option>`).join("")}</select></div>` : ""}
      ${esTexto ? `<div class="campo"><label>Separador de columnas</label><select id="c-del">${[["AUTO", "Detectar"], ["PUNTO_COMA", "Punto y coma ;"], ["COMA", "Coma ,"], ["TAB", "Tabulador"], ["BARRA", "Barra vertical |"]].map(([v, n]) => `<option value="${v}" ${ci.delimitador === v ? "selected" : ""}>${n}</option>`).join("")}</select></div>` : ""}
      <div class="campo"><label>Fila de encabezados</label><input id="c-fila" type="number" min="0" max="${p.total_filas}" value="${ci.fila_encabezado}"><small>0 = el archivo no tiene encabezados (estilo PLE). Haga clic en una fila de la vista previa para elegirla.</small></div>
      <div class="campo"><label>Filas de encabezado</label><select id="c-nfilas"><option value="1" ${ci.filas_encabezado == 1 ? "selected" : ""}>Una fila</option><option value="2" ${ci.filas_encabezado == 2 ? "selected" : ""}>Dos filas (título de grupo + subtítulo)</option></select></div>
    </div>
    <div class="alerta ${sug.fila ? "alerta-info" : "alerta-warn"}">${sug.fila
      ? `Encabezado reconocido automáticamente en la fila <b>${sug.fila}</b>${sug.filas === 2 ? " (combinando dos filas)" : ""} · ${sug.puntaje} campos identificados.`
      : "No se reconocieron encabezados: si el archivo no los tiene, deje la fila en 0 y homologue por posición de columna."}
      ${p.total_filas} filas en la hoja; se muestran las primeras ${p.filas.length}.</div>
    <div class="tabla-wrap" style="max-height:420px"><table class="tabla tabla-cruda"><tbody>
      ${p.filas.map((f, i) => {
        const n = i + 1, esEnc = n === Number(ci.fila_encabezado) || (Number(ci.filas_encabezado) === 2 && n === Number(ci.fila_encabezado) - 1);
        return `<tr data-fila="${n}" class="${esEnc ? "fila-enc" : n < ci.fila_encabezado ? "fila-previa" : ""}"><th>${n}</th>${Array.from({ length: ancho }, (_, j) => `<td>${esc(f[j] ?? "")}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>
    <div class="acciones"><button class="btn" id="ci-atras">Atrás</button><button class="btn btn-primario" id="ci-sig">Continuar a homologación</button></div></div>`;
  $("#c-hoja")?.addEventListener("change", (e) => { ci.hoja = e.target.value; ci.hom = null; paso4(); });
  $("#c-del")?.addEventListener("change", (e) => { ci.delimitador = e.target.value; ci.hom = null; ci.previa = null; paso4(); });
  $("#c-fila").onchange = (e) => { ci.fila_encabezado = Number(e.target.value); ci.hom = null; paso4(); };
  $("#c-nfilas").onchange = (e) => { ci.filas_encabezado = Number(e.target.value); ci.hom = null; paso4(); };
  $$("[data-fila]").forEach((tr) => tr.addEventListener("click", () => { ci.fila_encabezado = Number(tr.dataset.fila); ci.hom = null; paso4(); }));
  $("#ci-atras").onclick = () => irPaso(3);
  $("#ci-sig").onclick = () => { ci.hom = null; irPaso(5); };
}

async function paso5(plantillaId) {
  if (!ci.hom || plantillaId !== undefined) {
    cuerpo().innerHTML = `<div class="card"><div class="vacio">Homologando columnas…</div></div>`;
    try {
      ci.hom = await api(`/contable/archivos/${ci.meta.token}/homologacion`, { method: "POST", body: parametros({ plantilla_id: plantillaId || null, mapeo: {} }) });
    } catch (err) { cuerpo().innerHTML = `<div class="alerta alerta-err">${esc(err.message)}</div>`; return; }
    ci.mapeo = Object.fromEntries(Object.entries(ci.hom.mapeo_sugerido).map(([c, v]) => [c, v.columna]));
    ci.plantilla_id = ci.hom.plantilla_aplicada?.id || null;
    const op = ci.hom.opciones_plantilla;
    if (op) Object.assign(ci, { separador_decimal: op.separador_decimal || ci.separador_decimal, formato_fecha: op.formato_fecha || ci.formato_fecha });
  }
  const h = ci.hom, t = h.tipo;
  const usadas = new Set(Object.values(ci.mapeo).map(Number));
  const faltan = t.requeridos.filter((g) => !g.some((c) => ci.mapeo[c] !== undefined));
  const origen = (c) => {
    const s = h.mapeo_sugerido[c];
    if (ci.mapeo[c] === undefined) return "";
    if (s && s.columna === Number(ci.mapeo[c])) return `<span class="badge ${s.origen === "PARCIAL" ? "b-warn" : "b-ok"}" title="Confianza ${s.confianza}%">${s.origen === "PLANTILLA" ? "Plantilla" : s.origen === "EXACTA" ? "Exacta" : "Parcial · revisar"}</span>`;
    return `<span class="badge b-info">Manual</span>`;
  };
  cuerpo().innerHTML = `
    <div class="card">
      <div class="form-grid">
        <div class="campo"><label>Plantilla de homologación</label><select id="c-pl"><option value="">— Sugerencia automática —</option>
          ${h.plantillas.map((p) => `<option value="${p.id}" ${ci.plantilla_id === p.id ? "selected" : ""}>${esc(p.nombre)} · ${esc(p.sistema_origen)}${p.empresa_id ? "" : " (global)"}</option>`).join("")}</select>
          <small>${h.plantilla_aplicada ? `Aplicada: «${esc(h.plantilla_aplicada.nombre)}».` : h.plantillas.length ? "Ninguna plantilla encaja con estos encabezados." : "Aún no hay plantillas para este tipo."}</small></div>
        <div class="campo"><label>Separador decimal</label><select id="c-dec">${[["AUTO", "Detectar"], ["PUNTO", "Punto: 1,234.56"], ["COMA", "Coma: 1.234,56"]].map(([v, n]) => `<option value="${v}" ${ci.separador_decimal === v ? "selected" : ""}>${n}</option>`).join("")}</select></div>
        <div class="campo"><label>Formato de fecha</label><select id="c-fec">${[["AUTO", "Detectar (dd/mm/aaaa)"], ["DMY", "dd/mm/aaaa"], ["MDY", "mm/dd/aaaa"], ["YMD", "aaaa-mm-dd"]].map(([v, n]) => `<option value="${v}" ${ci.formato_fecha === v ? "selected" : ""}>${n}</option>`).join("")}</select></div>
        ${t.admite_completa ? `<label class="check"><input type="checkbox" id="c-comp" ${ci.importacion_completa ? "checked" : ""}> Importación completa (validar partida doble y totales; los descuadres serán críticos)</label>` : ""}
      </div>
    </div>
    ${faltan.length ? `<div class="alerta alerta-err"><b>Faltan columnas obligatorias:</b> ${faltan.map((g) => g.map((c) => t.campos.find((x) => x.clave === c).etiqueta).join(" o ")).join(" · ")}</div>`
      : `<div class="alerta alerta-ok">Todas las columnas obligatorias están homologadas. Revise las coincidencias parciales antes de continuar.</div>`}
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Campo interno</th><th>Requisito</th><th>Columna del archivo</th><th>Origen</th><th>Muestra de valores</th></tr></thead><tbody>
      ${t.campos.map((c) => {
        const col = ci.mapeo[c.clave];
        return `<tr class="${col === undefined && (c.obligatorio) ? "fila-dup" : ""}">
          <td><b>${esc(c.etiqueta)}</b><br><small class="sub">${esc(c.clave)}</small></td>
          <td>${c.obligatorio ? '<span class="badge b-err">Obligatorio</span>' : c.alternativo ? '<span class="badge b-warn">Uno de varios</span>' : '<span class="badge">Opcional</span>'}</td>
          <td><select data-campo="${c.clave}"><option value="">— no informado —</option>
            ${h.encabezados.map((e, i) => `<option value="${i}" ${Number(col) === i && col !== undefined ? "selected" : ""}>${i + 1}. ${esc(e)}${usadas.has(i) && Number(col) !== i ? " · en uso" : ""}</option>`).join("")}</select></td>
          <td>${origen(c.clave)}</td>
          <td><small>${col !== undefined ? (h.muestras[col] || []).map(esc).join(" · ") : ""}</small></td></tr>`;
      }).join("")}</tbody></table></div>
    <div class="acciones"><button class="btn" id="ci-atras">Atrás</button><button class="btn" id="ci-reset">Restablecer sugerencia</button>
      <button class="btn btn-primario" id="ci-sig" ${faltan.length ? "disabled" : ""}>Validar información</button></div>`;
  $$("[data-campo]").forEach((s) => s.addEventListener("change", () => {
    if (s.value === "") delete ci.mapeo[s.dataset.campo];
    else {
      const col = Number(s.value);
      // Una columna solo puede alimentar un campo: si ya estaba asignada, se mueve.
      Object.entries(ci.mapeo).forEach(([c, v]) => {
        if (v === col && c !== s.dataset.campo) {
          delete ci.mapeo[c];
          toast(`«${h.encabezados[col]}» se quitó de «${t.campos.find((x) => x.clave === c).etiqueta}»`);
        }
      });
      ci.mapeo[s.dataset.campo] = col;
    }
    paso5();
  }));
  $("#c-pl").onchange = (e) => paso5(e.target.value ? Number(e.target.value) : null);
  $("#c-dec").onchange = (e) => { ci.separador_decimal = e.target.value; };
  $("#c-fec").onchange = (e) => { ci.formato_fecha = e.target.value; };
  $("#c-comp")?.addEventListener("change", (e) => { ci.importacion_completa = e.target.checked; });
  $("#ci-reset").onclick = () => { ci.hom = null; paso5(); };
  $("#ci-atras").onclick = () => irPaso(4);
  $("#ci-sig").onclick = () => { ci.validacion = null; irPaso(6); };
}

async function paso6() {
  if (!ci.validacion) {
    cuerpo().innerHTML = `<div class="card"><h2>Validando información</h2><div id="ci-prog">${barraProgreso(0, "Iniciando")}</div></div>`;
    try {
      const t = await api(`/contable/archivos/${ci.meta.token}/validacion`, { method: "POST", body: parametros() });
      ci.validacion = await esperarTrabajo(t, (x) => { const c = $("#ci-prog"); if (c) c.innerHTML = barraProgreso(x.progreso, x.etapa); });
      ci.obs = { severidad: "", codigo: "", texto: "", pagina: 1 };
    } catch (err) {
      cuerpo().innerHTML = `<div class="alerta alerta-err">${esc(err.message)}</div><div class="acciones"><button class="btn" onclick="irPaso(5)">Volver a homologación</button></div>`;
      return;
    }
  }
  const r = ci.validacion.resumen;
  const obs = await api(`/contable/archivos/${ci.meta.token}/observaciones`, { params: { ...ci.obs, por_pagina: 100 } });
  const paginas = Math.max(1, Math.ceil(obs.total / obs.por_pagina));
  const fmt = (v) => (v === null || v === undefined ? "—" : fmtNum.format(v));
  const difTotal = r.total_archivo && (r.total_archivo[0] !== null && Number(r.total_archivo[0]) !== Number(r.total_debe));
  cuerpo().innerHTML = `
    ${r.estructura_valida ? "" : `<div class="alerta alerta-err"><b>Archivo estructuralmente inválido para este tipo.</b> Vuelva a la homologación.</div>`}
    ${r.archivo_ya_importado ? `<div class="alerta alerta-warn">Este archivo ya fue importado (lote #${r.archivo_ya_importado}).</div>` : ""}
    <div class="grid grid-4" style="margin-bottom:16px">
      <div class="kpi"><div class="l">Filas leídas</div><div class="v">${r.filas_leidas}</div><div class="l">${r.filas_vacias} vacías · ${r.filas_subtotal} subtotales/totales</div></div>
      <div class="kpi"><div class="l">Registros válidos</div><div class="v">${r.registros_validos}</div><div class="l">${r.registros_excluidos} excluidos por errores${r.asientos ? ` · ${r.asientos} asientos` : ""}</div></div>
      <div class="kpi"><div class="l">Total procesado (debe / haber)</div><div class="v" style="font-size:16px">${fmt(r.total_debe)}${r.total_haber !== null ? `<br>${fmt(r.total_haber)}` : ""}</div></div>
      <div class="kpi"><div class="l">Total según archivo</div><div class="v" style="font-size:16px;${difTotal ? "color:var(--err)" : ""}">${r.total_archivo ? `${fmt(r.total_archivo[0])}${r.total_archivo[1] !== null ? `<br>${fmt(r.total_archivo[1])}` : ""}` : "No informado"}</div></div>
    </div>
    <div class="card">
      <div class="cab-vista" style="margin-bottom:8px"><h2 style="margin:0">Observaciones (${Object.values(r.severidades).reduce((a, b) => a + b, 0)})</h2></div>
      ${chipsSeveridad(r.severidades, ci.obs.severidad)}
      <form class="filtros" id="f-obs" style="margin:10px 0">
        <div class="campo"><label>Código</label><select name="codigo"><option value="">Todos</option>${Object.entries(r.codigos).map(([c, n]) => `<option value="${c}" ${ci.obs.codigo === c ? "selected" : ""}>${c} (${n})</option>`).join("")}</select></div>
        <div class="campo" style="flex:1"><label>Buscar</label><input name="texto" value="${esc(ci.obs.texto)}" placeholder="cuenta, asiento, documento, texto…"></div>
        <button class="btn">Filtrar</button>
      </form>
      <div class="tabla-wrap" style="max-height:520px">${tablaObservaciones(obs.items)}</div>
      <div class="paginacion"><span>${obs.total} observación(es)</span><span>
        <button class="btn btn-sm" id="o-ant" ${ci.obs.pagina <= 1 ? "disabled" : ""}>‹</button> ${ci.obs.pagina} / ${paginas}
        <button class="btn btn-sm" id="o-sig" ${ci.obs.pagina >= paginas ? "disabled" : ""}>›</button></span></div>
    </div>
    <details class="card"><summary><b>Vista previa de registros normalizados</b> (primeros ${ci.validacion.muestra.length})</summary>
      ${tablaMuestra(ci.validacion.muestra)}</details>
    <div class="acciones"><button class="btn" id="ci-atras">Volver a homologación</button>
      <button class="btn" id="ci-revalidar">Volver a validar</button>
      <button class="btn btn-primario" id="ci-sig" ${r.estructura_valida && r.registros_validos ? "" : "disabled"}>Continuar a confirmación</button></div>`;
  $$("[data-sev]").forEach((b) => b.addEventListener("click", () => { ci.obs.severidad = b.dataset.sev; ci.obs.pagina = 1; paso6(); }));
  $("#f-obs").onsubmit = (e) => { e.preventDefault(); Object.assign(ci.obs, datosForm(e.target), { pagina: 1 }); paso6(); };
  $("#o-ant").onclick = () => { ci.obs.pagina--; paso6(); };
  $("#o-sig").onclick = () => { ci.obs.pagina++; paso6(); };
  $("#ci-atras").onclick = () => irPaso(5);
  $("#ci-revalidar").onclick = () => { ci.validacion = null; paso6(); };
  $("#ci-sig").onclick = () => irPaso(7);
}

function tablaMuestra(regs) {
  if (!regs.length) return `<div class="vacio">Sin registros</div>`;
  const cols = Object.keys(regs[0]).filter((k) => k !== "_fila" && regs.some((r) => r[k] !== null && r[k] !== "" && r[k] !== "0.00"));
  return `<div class="tabla-wrap" style="max-height:360px;margin-top:10px"><table class="tabla"><thead><tr><th>Fila</th>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>
    ${regs.map((r) => `<tr><td>${r._fila}</td>${cols.map((c) => `<td>${esc(r[c] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function paso7() {
  if (ci.lote) return resultadoLote();
  const r = ci.validacion.resumen, sev = r.severidades, t = tipoDef(ci.tipo);
  const nombreSug = `${catalogo.sistemas.find((s) => s.clave === ci.sistema).nombre} · ${t.nombre}`;
  cuerpo().innerHTML = `<div class="card">
    <h2>Resumen de la importación</h2>
    <table class="mini-tabla" style="max-width:640px">
      <tr><td>Archivo / hoja</td><td>${esc(ci.meta.nombre)} · ${esc(r.hoja || "")}</td></tr>
      <tr><td>Tipo de información</td><td>${esc(t.nombre)}</td></tr>
      <tr><td>Ejercicio / periodo</td><td>${r.ejercicio || "—"} · ${t.transaccional ? nombrePeriodo(r.periodo) : "no aplica (maestro)"}</td></tr>
      <tr><td>Registros a importar</td><td>${r.registros_validos} (${r.registros_excluidos} excluidos)</td></tr>
      <tr><td>Observaciones</td><td>${SEVERIDADES.map(([k, n]) => `${n}: <b>${sev[k]}</b>`).join(" · ")}</td></tr>
    </table>
    ${t.transaccional ? "" : `<div class="alerta alerta-info">Los maestros se actualizan registro a registro: los códigos existentes se modifican y los nuevos se agregan.</div>`}
    <div class="form-grid" style="margin-top:14px">
      <div class="campo"><label class="check"><input type="checkbox" id="k-pl" ${ci.plantilla_id ? "" : "checked"}> Guardar la homologación como plantilla</label>
        <input id="k-pl-nombre" value="${esc(ci.hom.plantilla_aplicada?.nombre || nombreSug)}" maxlength="120">
        <small>Se reutilizará automáticamente con archivos de la misma estructura (empresa · sistema · tipo).</small></div>
      ${t.transaccional ? `<label class="check"><input type="checkbox" id="k-reemp"> Reemplazar (anular) lotes activos de ${esc(t.nombre)} del mismo periodo</label>` : ""}
    </div>
    ${sev.CRITICO ? `<div class="alerta alerta-err" style="margin-top:14px"><b>Hay ${sev.CRITICO} observación(es) crítica(s).</b> Lo recomendable es corregir el origen.
      Si aun así necesita importar, confírmelo y deje constancia del motivo (queda en la auditoría).
      <label class="check" style="margin-top:8px"><input type="checkbox" id="k-crit"> Importar con observaciones críticas</label>
      <input id="k-motivo" placeholder="Motivo (mínimo 10 caracteres)" maxlength="255" style="width:100%;margin-top:6px"></div>` : ""}
    <div id="k-prog"></div>
    <div class="acciones"><button class="btn" id="ci-atras">Atrás</button><button class="btn btn-primario" id="k-ok">Importar ${r.registros_validos} registros</button></div></div>`;
  $("#ci-atras").onclick = () => irPaso(6);
  $("#k-ok").onclick = async (ev) => {
    const extra = {
      guardar_plantilla: $("#k-pl").checked ? $("#k-pl-nombre").value.trim() : null,
      reemplazar_previos: $("#k-reemp")?.checked || false,
      confirmar_criticos: $("#k-crit")?.checked || false,
      motivo_criticos: $("#k-motivo")?.value.trim() || null,
    };
    if (sev.CRITICO && (!extra.confirmar_criticos || (extra.motivo_criticos || "").length < 10)) {
      toast("Marque la confirmación e indique el motivo (mínimo 10 caracteres)", "err"); return;
    }
    ev.target.disabled = true;
    try {
      const tr = await api(`/contable/archivos/${ci.meta.token}/confirmacion`, { method: "POST", body: parametros(extra) });
      ci.lote = await esperarTrabajo(tr, (x) => { const c = $("#k-prog"); if (c) c.innerHTML = barraProgreso(x.progreso, x.etapa); });
      ci.meta = null;  // el archivo temporal se elimina al confirmar
      toast(`Lote #${ci.lote.id} importado`, "ok");
      resultadoLote();
    } catch (err) { toast(err.message, "err"); ev.target.disabled = false; $("#k-prog").innerHTML = ""; }
  };
}

function resultadoLote() {
  const l = ci.lote;
  cuerpo().innerHTML = `<div class="card">
    <div class="alerta alerta-ok"><b>Lote #${l.id} importado.</b> ${l.registros_importados} registros de ${esc(l.nombre_archivo)} (${esc(l.tipo_nombre)}).</div>
    <div class="acciones" style="justify-content:flex-start">
      <a class="btn btn-primario" href="#/contable-lote?id=${l.id}">Ver lote y observaciones</a>
      <button class="btn" id="otro">Importar otro archivo</button></div></div>`;
  $("#otro").onclick = () => { reiniciarAsistente(); pintarAsistente(); };
}

// =====================================================================  lotes
rutas["contable-lotes"] = async () => {
  if (!requiereEmpresa()) return;
  await vigente(cargarCatalogo());
  const lista = await vigente(api("/contable/lotes", { params: { empresa_id: estado.empresaId } }));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Lotes y observaciones</h1><p class="sub">Cada importación confirmada queda como un lote trazable: archivo, hoja, homologación, usuario y observaciones.</p></div>
      <a class="btn btn-primario" href="#/contable-importar">Nueva importación</a></div>
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>#</th><th>Carga</th><th>Tipo</th><th>Periodo</th><th>Archivo</th><th class="num">Registros</th>
      <th>Observaciones</th><th>Estado</th><th></th></tr></thead><tbody>
      ${lista.map((l) => `<tr class="${l.estado === "ANULADO" ? "fila-excl" : ""}">
        <td>${l.id}</td><td class="nowrap">${fechaHora(l.creado_en)}<br><small class="sub">${esc(l.usuario)}</small></td>
        <td>${esc(l.tipo_nombre)}<br><small class="sub">${esc(l.sistema_origen)}</small></td>
        <td class="nowrap">${tipoDef(l.tipo_informacion).transaccional ? `${l.ejercicio} · ${nombrePeriodo(l.periodo)}` : "Maestro"}</td>
        <td>${esc(l.nombre_archivo)}<br><small class="sub">${esc(l.hoja || "")}</small></td>
        <td class="num">${l.registros_importados}${l.registros_excluidos ? `<br><small class="neg">${l.registros_excluidos} excl.</small>` : ""}</td>
        <td class="nowrap">${SEVERIDADES.map(([k, , c]) => `<span class="badge ${c}" title="${NOMBRE_SEV[k]}">${l["obs_" + k.toLowerCase()]}</span>`).join(" ")}</td>
        <td>${badgeEstado(l.estado)}</td>
        <td><div class="acc-col"><a class="btn btn-sm" href="#/contable-lote?id=${l.id}">Ver</a>
          ${l.estado === "ACTIVO" && tipoDef(l.tipo_informacion).transaccional ? `<button class="btn btn-sm btn-peligro" data-anular="${l.id}">Anular</button>` : ""}</div></td></tr>`).join("")
        || `<tr><td colspan="9" class="vacio">Aún no hay información contable importada</td></tr>`}</tbody></table></div>`;
  $$("[data-anular]").forEach((b) => b.addEventListener("click", () => anularLote(b.dataset.anular)));
};

function anularLote(id) {
  const c = abrirModal(`Anular lote #${id}`, `
    <div class="alerta alerta-warn">Los registros del lote dejarán de considerarse en validaciones y análisis. No se borran.</div>
    <form id="f-anl"><div class="campo"><label>Motivo</label><input name="motivo" required minlength="5" maxlength="255"></div>
    <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-peligro">Anular</button></div></form>`);
  $("#f-anl", c).onsubmit = async (e) => {
    e.preventDefault();
    try { await api(`/contable/lotes/${id}/anular`, { method: "POST", body: datosForm(e.target) }); cerrarModal(); toast("Lote anulado", "ok"); navegar(); }
    catch (err) { toast(err.message, "err"); }
  };
}

const filtroLote = { severidad: "", codigo: "", texto: "", pagina: 1, pestana: "obs", rpagina: 1 };
rutas["contable-lote"] = async () => {
  await vigente(cargarCatalogo());
  const id = Number(parametrosHash().id);
  if (filtroLote.id !== id) Object.assign(filtroLote, { id, severidad: "", codigo: "", texto: "", pagina: 1, pestana: "obs", rpagina: 1 });
  const l = await vigente(api(`/contable/lotes/${id}`));
  await pintarLote(l);
};

async function pintarLote(l) {
  const f = filtroLote;
  const sev = { CRITICO: l.obs_critico, ALTO: l.obs_alto, MEDIO: l.obs_medio, INFORMATIVO: l.obs_informativo };
  let cuerpoHtml;
  if (f.pestana === "obs") {
    const o = await api(`/contable/lotes/${l.id}/observaciones`, { params: { severidad: f.severidad, codigo: f.codigo, texto: f.texto, pagina: f.pagina } });
    const pag = Math.max(1, Math.ceil(o.total / o.por_pagina));
    cuerpoHtml = `${chipsSeveridad(sev, f.severidad)}
      <form class="filtros" id="f-lo" style="margin:10px 0"><div class="campo"><label>Código</label><input name="codigo" value="${esc(f.codigo)}" placeholder="PD001…" maxlength="10"></div>
        <div class="campo" style="flex:1"><label>Buscar</label><input name="texto" value="${esc(f.texto)}"></div><button class="btn">Filtrar</button>
        <a class="btn" href="/api/contable/lotes/${l.id}/observaciones.csv">Exportar CSV</a></form>
      <div class="tabla-wrap" style="max-height:560px">${tablaObservaciones(o.items)}</div>
      <div class="paginacion"><span>${o.total} observación(es)</span><span><button class="btn btn-sm" id="lo-ant" ${f.pagina <= 1 ? "disabled" : ""}>‹</button> ${f.pagina} / ${pag} <button class="btn btn-sm" id="lo-sig" ${f.pagina >= pag ? "disabled" : ""}>›</button></span></div>`;
  } else {
    const r = await api(`/contable/lotes/${l.id}/registros`, { params: { pagina: f.rpagina } });
    const pag = Math.max(1, Math.ceil(r.total / r.por_pagina));
    const cols = r.items.length ? Object.keys(r.items[0]).filter((k) => !["lote_id", "empresa_id"].includes(k) && r.items.some((x) => x[k] !== null && x[k] !== "" && x[k] !== "0.00")) : [];
    cuerpoHtml = `<div class="tabla-wrap" style="max-height:560px">${r.items.length ? `<table class="tabla"><thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>
      ${r.items.map((x) => `<tr>${cols.map((c) => `<td>${esc(x[c] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table>` : `<div class="vacio">Sin registros</div>`}</div>
      <div class="paginacion"><span>${r.total} registro(s)</span><span><button class="btn btn-sm" id="lr-ant" ${f.rpagina <= 1 ? "disabled" : ""}>‹</button> ${f.rpagina} / ${pag} <button class="btn btn-sm" id="lr-sig" ${f.rpagina >= pag ? "disabled" : ""}>›</button></span></div>`;
  }
  const t = tipoDef(l.tipo_informacion);
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Lote #${l.id} · ${esc(l.tipo_nombre)}</h1>
      <p class="sub">${esc(l.nombre_archivo)} · hoja ${esc(l.hoja || "")} · ${esc(l.sistema_origen)} · ${t.transaccional ? `${l.ejercicio} periodo ${nombrePeriodo(l.periodo)} · ` : ""}${esc(l.usuario)} · ${fechaHora(l.creado_en)}</p></div>
      <a class="btn" href="#/contable-lotes">Volver</a></div>
    ${l.estado === "ANULADO" ? `<div class="alerta alerta-err">Lote anulado: ${esc(l.motivo_anulacion || "")}</div>` : ""}
    ${l.motivo_criticos ? `<div class="alerta alerta-warn">Importado con observaciones críticas. Motivo: ${esc(l.motivo_criticos)}</div>` : ""}
    <div class="grid grid-4" style="margin-bottom:16px">
      <div class="kpi"><div class="l">Filas leídas</div><div class="v">${l.filas_leidas}</div><div class="l">${l.filas_vacias} vacías · ${l.filas_subtotal} subtotales</div></div>
      <div class="kpi"><div class="l">Registros importados</div><div class="v">${l.registros_importados}</div><div class="l">${l.registros_excluidos} excluidos</div></div>
      <div class="kpi"><div class="l">Total debe / haber procesado</div><div class="v" style="font-size:16px">${fmtNum.format(l.total_debe)}<br>${fmtNum.format(l.total_haber)}</div></div>
      <div class="kpi"><div class="l">Total según archivo</div><div class="v" style="font-size:16px">${l.total_archivo_debe !== null ? `${fmtNum.format(l.total_archivo_debe)}<br>${l.total_archivo_haber !== null ? fmtNum.format(l.total_archivo_haber) : ""}` : "No informado"}</div></div>
    </div>
    <div class="card">
      <div class="pestanas"><button class="btn ${f.pestana === "obs" ? "btn-primario" : ""}" data-pest="obs">Observaciones</button>
        <button class="btn ${f.pestana === "reg" ? "btn-primario" : ""}" data-pest="reg">Registros normalizados</button>
        <button class="btn" id="ver-mapeo">Homologación usada</button></div>
      ${cuerpoHtml}</div>`;
  $$("[data-pest]").forEach((b) => b.addEventListener("click", () => { f.pestana = b.dataset.pest; pintarLote(l); }));
  $("#ver-mapeo").onclick = () => abrirModal("Homologación usada", `<table class="tabla"><thead><tr><th>Campo interno</th><th>Columna del archivo</th></tr></thead><tbody>
    ${Object.entries(l.mapeo).map(([c, col]) => `<tr><td>${esc(t.campos.find((x) => x.clave === c)?.etiqueta || c)}</td><td>${esc(col)}</td></tr>`).join("")}</tbody></table>
    <pre class="json">${esc(JSON.stringify(l.opciones, null, 2))}</pre>`);
  $$("[data-sev]").forEach((b) => b.addEventListener("click", () => { f.severidad = b.dataset.sev; f.pagina = 1; pintarLote(l); }));
  $("#f-lo")?.addEventListener("submit", (e) => { e.preventDefault(); Object.assign(f, datosForm(e.target), { pagina: 1 }); pintarLote(l); });
  $("#lo-ant")?.addEventListener("click", () => { f.pagina--; pintarLote(l); });
  $("#lo-sig")?.addEventListener("click", () => { f.pagina++; pintarLote(l); });
  $("#lr-ant")?.addEventListener("click", () => { f.rpagina--; pintarLote(l); });
  $("#lr-sig")?.addEventListener("click", () => { f.rpagina++; pintarLote(l); });
}

// =====================================================================  plantillas
rutas["contable-plantillas"] = async () => {
  if (!requiereEmpresa()) return;
  await vigente(cargarCatalogo());
  const lista = await vigente(api("/contable/plantillas", { params: { empresa_id: estado.empresaId } }));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Plantillas de homologación</h1><p class="sub">Relación entre columnas de cada ERP y los campos internos, por empresa, sistema contable y tipo de archivo. Se crean desde el asistente.</p></div></div>
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Nombre</th><th>Sistema</th><th>Tipo de información</th><th>Ámbito</th><th class="num">Usos</th><th>Actualizada</th><th></th></tr></thead><tbody>
      ${lista.map((p) => `<tr><td><b>${esc(p.nombre)}</b></td><td>${esc(p.sistema_origen)}</td><td>${esc(tipoDef(p.tipo_informacion).nombre)}</td>
        <td>${p.empresa_id ? "Empresa" : "Global"}</td><td class="num">${p.usos}</td><td class="nowrap">${fechaHora(p.actualizado_en)}<br><small class="sub">${esc(p.usuario)}</small></td>
        <td><div class="acc-col"><button class="btn btn-sm" data-ver="${p.id}">Ver / renombrar</button><button class="btn btn-sm btn-peligro" data-del="${p.id}">Eliminar</button></div></td></tr>`).join("")
        || `<tr><td colspan="7" class="vacio">Aún no hay plantillas. Al confirmar una importación puede guardar su homologación.</td></tr>`}</tbody></table></div>`;
  $$("[data-ver]").forEach((b) => b.addEventListener("click", () => {
    const p = lista.find((x) => x.id === Number(b.dataset.ver)), t = tipoDef(p.tipo_informacion);
    const c = abrirModal(`Plantilla «${p.nombre}»`, `<form id="f-pl"><div class="campo"><label>Nombre</label><input name="nombre" value="${esc(p.nombre)}" minlength="3" maxlength="120" required></div>
      <table class="tabla" style="margin-top:12px"><thead><tr><th>Campo interno</th><th>Encabezado esperado</th></tr></thead><tbody>
      ${Object.entries(p.mapeo).map(([k, v]) => `<tr><td>${esc(t.campos.find((x) => x.clave === k)?.etiqueta || k)}</td><td><code>${esc(v.startsWith("#") ? `Columna ${Number(v.slice(1)) + 1}` : v)}</code></td></tr>`).join("")}</tbody></table>
      <p class="sub">Opciones: ${esc(Object.entries(p.opciones).map(([k, v]) => `${k}: ${v}`).join(" · "))} · fila de encabezado ${p.fila_encabezado}</p>
      <div class="acciones"><button type="button" class="btn" data-cerrar>Cerrar</button><button class="btn btn-primario">Guardar nombre</button></div></form>`);
    $("#f-pl", c).onsubmit = async (e) => {
      e.preventDefault();
      try { await api(`/contable/plantillas/${p.id}`, { method: "PUT", body: { nombre: datosForm(e.target).nombre } }); cerrarModal(); toast("Plantilla actualizada", "ok"); navegar(); }
      catch (err) { toast(err.message, "err"); }
    };
  }));
  $$("[data-del]").forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("¿Eliminar la plantilla? Los lotes ya importados conservan su homologación.")) return;
    try { await api(`/contable/plantillas/${b.dataset.del}`, { method: "DELETE" }); toast("Plantilla eliminada", "ok"); navegar(); }
    catch (err) { toast(err.message, "err"); }
  }));
};

// =====================================================================  reglas contables
rutas["contable-reglas"] = async () => {
  if (!requiereEmpresa()) return;
  const [cfg, reglas] = await vigente(Promise.all([
    api(`/contable/configuracion/${estado.empresaId}`), api("/contable/reglas-destino", { params: { empresa_id: estado.empresaId } }),
  ]));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Reglas contables</h1><p class="sub">Tolerancias del motor de validación y políticas de contabilidad analítica (clases 6, 7 y 9) de la empresa.</p></div></div>
    <form id="f-cfg">
      <div class="card"><h2>Tolerancias</h2><div class="form-grid">
        <div class="campo"><label>Tolerancia de descuadre</label><input type="number" step="0.01" min="0" name="tolerancia_descuadre" value="${cfg.tolerancia_descuadre}"><small>Diferencia admitida en partida doble y cruces de saldos.</small></div>
        <div class="campo"><label>Materialidad</label><input type="number" step="0.01" min="0" name="materialidad" value="${cfg.materialidad}"><small>Desde este importe un saldo contrario a la naturaleza es «Alto».</small></div>
        <div class="campo"><label>Tolerancia tipo de cambio</label><input type="number" step="0.0001" min="0" name="tolerancia_tipo_cambio" value="${cfg.tolerancia_tipo_cambio}"></div>
        <div class="campo"><label>Tolerancia de conversión MN/ME</label><input type="number" step="0.01" min="0" name="tolerancia_conversion" value="${cfg.tolerancia_conversion}"></div>
        <div class="campo"><label>Cuentas no autorizadas para registro (prefijos)</label><input name="prefijos_sin_movimiento" value="${esc(cfg.prefijos_sin_movimiento)}" placeholder="p. ej. 59,89"><small>Se suman a las marcadas sin movimiento en el plan de cuentas.</small></div>
      </div></div>
      <div class="card"><h2>Contabilidad analítica: clases 6, 7 y 9</h2>
        <div class="alerta alerta-info">Los gastos por naturaleza destinables se transfieren a destino con contrapartida en la cuenta de cargas imputables (79). Configure según la estructura de su empresa: no todas usan la clase 9.</div>
        <div class="form-grid">
          <label class="check"><input type="checkbox" name="usa_clase_9" ${cfg.usa_clase_9 ? "checked" : ""}> La empresa usa cuentas de destino</label>
          <div class="campo"><label>Momento del destino</label><select name="modo_destino">
            ${[["MISMO_ASIENTO", "En el mismo asiento"], ["PERIODO", "Al cierre del periodo (asiento resumen)"], ["NO_APLICA", "No aplica"]].map(([v, n]) => `<option value="${v}" ${cfg.modo_destino === v ? "selected" : ""}>${n}</option>`).join("")}</select></div>
          <div class="campo"><label>Cuentas de gasto destinables (prefijos)</label><input name="prefijos_destinables" value="${esc(cfg.prefijos_destinables)}"></div>
          <div class="campo"><label>Prefijo(s) de destino</label><input name="prefijo_destino" value="${esc(cfg.prefijo_destino)}"></div>
          <div class="campo"><label>Cuenta de cargas imputables</label><input name="cuenta_cargas_imputables" value="${esc(cfg.cuenta_cargas_imputables)}"></div>
          <label class="check"><input type="checkbox" name="exigir_centro_costo_destino" ${cfg.exigir_centro_costo_destino ? "checked" : ""}> Exigir centro de costo en cuentas de destino</label>
          <label class="check"><input type="checkbox" name="validar_cuenta_78" ${cfg.validar_cuenta_78 ? "checked" : ""}> Revisar tratamiento de la 78 al aplicar provisiones (48)</label>
        </div>
        <div class="acciones"><button class="btn btn-primario">Guardar configuración</button></div></div>
    </form>
    <div class="card"><div class="cab-vista" style="margin-bottom:8px"><h2 style="margin:0">Reglas específicas de destino</h2><button class="btn btn-primario" id="nueva-regla">Nueva regla</button></div>
      <p class="sub">Ejemplo: compras (60) deben tener destino a inventarios (20) y variación de existencias (61) en el mismo asiento.</p>
      <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Origen</th><th>Destino debe</th><th>Destino haber</th><th>Exige CC</th><th>Descripción</th><th>Estado</th><th></th></tr></thead><tbody>
      ${reglas.map((r) => `<tr><td><b>${esc(r.prefijo_origen)}</b></td><td>${esc(r.destino_debe)}</td><td>${esc(r.destino_haber)}</td><td>${r.requiere_centro_costo ? "Sí" : "No"}</td>
        <td>${esc(r.descripcion || "")}</td><td>${r.activa ? '<span class="badge b-ok">Activa</span>' : '<span class="badge">Inactiva</span>'}</td>
        <td><div class="acc-col"><button class="btn btn-sm" data-ed="${r.id}">Editar</button><button class="btn btn-sm btn-peligro" data-del="${r.id}">Eliminar</button></div></td></tr>`).join("")
        || `<tr><td colspan="7" class="vacio">Sin reglas específicas</td></tr>`}</tbody></table></div></div>`;
  $("#f-cfg").onsubmit = async (e) => {
    e.preventDefault();
    const d = datosForm(e.target);
    try { await api(`/contable/configuracion/${estado.empresaId}`, { method: "PUT", body: d }); toast("Configuración guardada", "ok"); }
    catch (err) { toast(err.message, "err"); }
  };
  const formRegla = (r) => {
    const c = abrirModal(r ? "Editar regla" : "Nueva regla de destino", `<form id="f-rg"><div class="form-grid">
      <div class="campo"><label>Prefijo de origen</label><input name="prefijo_origen" required pattern="\\d+" value="${esc(r?.prefijo_origen)}"></div>
      <div class="campo"><label>Destino debe (prefijos, separados por coma)</label><input name="destino_debe" value="${esc(r?.destino_debe)}"></div>
      <div class="campo"><label>Destino haber</label><input name="destino_haber" value="${esc(r?.destino_haber)}"></div>
      <div class="campo" style="grid-column:1/-1"><label>Descripción</label><input name="descripcion" value="${esc(r?.descripcion)}"></div>
      <label class="check"><input type="checkbox" name="requiere_centro_costo" ${r?.requiere_centro_costo ? "checked" : ""}> Exige centro de costo</label>
      <label class="check"><input type="checkbox" name="activa" ${!r || r.activa ? "checked" : ""}> Activa</label></div>
      <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-primario">Guardar</button></div></form>`);
    $("#f-rg", c).onsubmit = async (e) => {
      e.preventDefault();
      const d = { ...datosForm(e.target), empresa_id: estado.empresaId };
      try {
        await api(r ? `/contable/reglas-destino/${r.id}` : "/contable/reglas-destino", { method: r ? "PUT" : "POST", body: d });
        cerrarModal(); toast("Regla guardada", "ok"); navegar();
      } catch (err) { toast(err.message, "err"); }
    };
  };
  $("#nueva-regla").onclick = () => formRegla();
  $$("[data-ed]").forEach((b) => b.addEventListener("click", () => formRegla(reglas.find((r) => r.id === Number(b.dataset.ed)))));
  $$("[data-del]").forEach((b) => b.addEventListener("click", async () => {
    try { await api(`/contable/reglas-destino/${b.dataset.del}`, { method: "DELETE" }); toast("Regla eliminada", "ok"); navegar(); }
    catch (err) { toast(err.message, "err"); }
  }));
};

// =====================================================================  datos contables
const maestroSel = { tipo: "PLAN_CUENTAS", texto: "" };
rutas["contable-maestros"] = async () => {
  if (!requiereEmpresa()) return;
  await vigente(cargarCatalogo());
  const [res, filas] = await vigente(Promise.all([
    api(`/contable/resumen/${estado.empresaId}`),
    api(`/contable/maestros/${maestroSel.tipo}`, { params: { empresa_id: estado.empresaId, texto: maestroSel.texto } }),
  ]));
  const nombres = { PLAN_CUENTAS: "Plan de cuentas", CENTROS_COSTO: "Centros de costo", PROVEEDORES: "Proveedores", CLIENTES: "Clientes", TIPOS_CAMBIO: "Tipos de cambio" };
  const columnas = {
    PLAN_CUENTAS: [["codigo", "Cuenta"], ["descripcion", "Descripción"], ["naturaleza", "Nat."], ["admite_movimiento", "Movimiento"], ["activa", "Activa"], ["requiere_centro_costo", "Exige CC"], ["cuenta_destino_debe", "Destino debe"], ["cuenta_destino_haber", "Destino haber"]],
    CENTROS_COSTO: [["codigo", "Código"], ["descripcion", "Descripción"], ["cuenta_destino", "Cuenta destino"], ["activo", "Activo"]],
    PROVEEDORES: [["tipo_documento_identidad", "TDI"], ["numero_documento", "Documento"], ["razon_social", "Razón social"], ["estado_contribuyente", "Estado"], ["condicion_domicilio", "Condición"]],
    CLIENTES: [["tipo_documento_identidad", "TDI"], ["numero_documento", "Documento"], ["razon_social", "Razón social"], ["estado_contribuyente", "Estado"], ["condicion_domicilio", "Condición"]],
    TIPOS_CAMBIO: [["fecha", "Fecha"], ["moneda", "Moneda"], ["compra", "Compra"], ["venta", "Venta"]],
  }[maestroSel.tipo];
  const celda = (v) => (v === true ? "Sí" : v === false ? "No" : esc(v ?? ""));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Datos contables</h1><p class="sub">Maestros y periodos importados que alimentan las validaciones.</p></div>
      <a class="btn btn-primario" href="#/contable-importar">Importar información</a></div>
    <div class="grid grid-4" style="margin-bottom:16px">${Object.entries(res.maestros).map(([k, n]) => `
      <button class="kpi kpi-btn ${maestroSel.tipo === k ? "activo" : ""}" data-m="${k}"><div class="l">${nombres[k]}</div><div class="v">${n}</div></button>`).join("")}</div>
    <div class="card"><h2>Información transaccional cargada (lotes activos)</h2>
      <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Tipo</th><th>Ejercicio</th><th>Periodo</th><th class="num">Lotes</th><th class="num">Registros</th><th class="num">Críticos</th><th class="num">Altos</th></tr></thead><tbody>
      ${res.transaccional.map((t) => `<tr><td>${esc(t.tipo_nombre)}</td><td>${t.ejercicio}</td><td>${nombrePeriodo(t.periodo)}</td><td class="num">${t.lotes}</td><td class="num">${t.registros}</td>
        <td class="num ${t.criticos ? "neg" : ""}">${t.criticos}</td><td class="num">${t.altos}</td></tr>`).join("") || `<tr><td colspan="7" class="vacio">Sin información transaccional</td></tr>`}</tbody></table></div></div>
    <div class="card"><div class="cab-vista" style="margin-bottom:8px"><h2 style="margin:0">${nombres[maestroSel.tipo]}</h2>
      <form id="f-m" class="filtros"><input name="texto" value="${esc(maestroSel.texto)}" placeholder="Buscar…"><button class="btn">Buscar</button></form></div>
      <div class="tabla-wrap" style="max-height:520px">${filas.length ? `<table class="tabla"><thead><tr>${columnas.map(([, n]) => `<th>${n}</th>`).join("")}</tr></thead><tbody>
        ${filas.map((f) => `<tr>${columnas.map(([k]) => `<td>${celda(f[k])}</td>`).join("")}</tr>`).join("")}</tbody></table>` : `<div class="vacio">Sin datos. Impórtelos desde el asistente.</div>`}</div></div>`;
  $$("[data-m]").forEach((b) => b.addEventListener("click", () => { maestroSel.tipo = b.dataset.m; maestroSel.texto = ""; navegar(); }));
  $("#f-m").onsubmit = (e) => { e.preventDefault(); maestroSel.texto = datosForm(e.target).texto; navegar(); };
};
