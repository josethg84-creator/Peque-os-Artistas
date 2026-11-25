/* Fase 3 — Motor de análisis de cuentas: dashboard, explorador, navegación, origen-destino,
   antigüedad, comparativos, hallazgos, reglas y papeles de trabajo.
   Reutiliza utilitarios globales de app.js (api, esc, toast, abrirModal, rutas, vista, vigente…). */
"use strict";

// ------------------------------------------------------------------ contexto de análisis
const ctxA = { ejercicio: null, desde: 1, hasta: 1, periodos: [], cat: null };
const NOMBRES_RIESGO = { ALTO: "Alto", MEDIO: "Medio", BAJO: "Bajo", INFORMATIVO: "Informativo" };
const COLOR_RIESGO = { ALTO: "#dc3c3d", MEDIO: "#f18a59", BAJO: "#fbb315", INFORMATIVO: "#8a94a6" };
const SERIES = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17", "#6a4ce2", "#ec4647"];
const ESTADOS_H = { PENDIENTE: "Pendiente de revisión", EN_REVISION: "En revisión", CONFIRMADO: "Confirmado", DESCARTADO: "Descartado", SUBSANADO: "Subsanado" };
const ESTADOS_P = { PENDIENTE: "Pendiente", EN_REVISION: "En revisión", OBSERVADO: "Observado", SUBSANADO: "Subsanado", REVISADO: "Revisado", APROBADO: "Aprobado" };

const num = (v) => (v === null || v === undefined || v === "" ? "—" : fmtNum.format(Number(v)));
const saldoDA = (v) => { if (v === null || v === undefined) return "—"; const n = Number(v); return n === 0 ? "0.00" : `${fmtNum.format(Math.abs(n))} ${n > 0 ? "D" : "A"}`; };
const pct = (v) => (v === null || v === undefined ? '<span class="sub" title="No aplicable: base cero">N/A</span>' : `${v > 0 ? "+" : ""}${v.toFixed(1)} %`);
const badgeRiesgo = (r) => (r ? `<span class="badge riesgo" style="--c:${COLOR_RIESGO[r]}">${esc(NOMBRE_RIESGO_TXT(r))}</span>` : "");
function NOMBRE_RIESGO_TXT(r) { return NOMBRES_RIESGO[r] || r; }
const per2 = (p) => String(p).padStart(2, "0");
const qCtx = (extra = {}) => ({ empresa_id: estado.empresaId, ejercicio: ctxA.ejercicio, desde: ctxA.desde, hasta: ctxA.hasta, ...extra });

async function prepararContexto() {
  if (!ctxA.cat) ctxA.cat = await api("/analisis/catalogo");
  ctxA.periodos = await api(`/analisis/periodos/${estado.empresaId}`);
  const guard = JSON.parse(almacen.leer(`an_ctx_${estado.empresaId}`, "null") || "null");
  const ejercicios = ctxA.periodos.map((x) => x.ejercicio);
  if (guard && ejercicios.includes(guard.ejercicio)) Object.assign(ctxA, guard);
  else if (ctxA.periodos.length) {
    const ult = ctxA.periodos[0];
    const ps = ult.periodos.map((x) => x.periodo).filter((p) => p >= 1 && p <= 12);
    Object.assign(ctxA, { ejercicio: ult.ejercicio, desde: Math.max(...ps, 1), hasta: Math.max(...ps, 1) });
  }
  return ctxA.periodos.length > 0;
}

function barraContexto(extra = "") {
  const ej = ctxA.periodos.map((x) => `<option ${x.ejercicio === ctxA.ejercicio ? "selected" : ""}>${x.ejercicio}</option>`).join("");
  const ops = (sel) => Array.from({ length: 13 }, (_, i) => i + 1).map((p) => `<option value="${p}" ${p === sel ? "selected" : ""}>${per2(p)}${p === 13 ? " Cierre" : ""}</option>`).join("");
  return `<div class="ctx-bar">
    <label>Ejercicio <select id="cx-ej">${ej}</select></label>
    <label>Desde <select id="cx-de">${ops(ctxA.desde)}</select></label>
    <label>Hasta <select id="cx-ha">${ops(ctxA.hasta)}</select></label>
    ${extra}</div>`;
}
function enlazarContexto(alCambiar) {
  const leer = () => {
    ctxA.ejercicio = Number($("#cx-ej").value); ctxA.desde = Number($("#cx-de").value); ctxA.hasta = Number($("#cx-ha").value);
    if (ctxA.desde > ctxA.hasta) { ctxA.hasta = ctxA.desde; }
    almacen.guardar(`an_ctx_${estado.empresaId}`, JSON.stringify({ ejercicio: ctxA.ejercicio, desde: ctxA.desde, hasta: ctxA.hasta }));
    alCambiar();
  };
  ["#cx-ej", "#cx-de", "#cx-ha"].forEach((s) => $(s)?.addEventListener("change", leer));
}
function sinDatos() {
  vista().innerHTML = `<div class="card" style="max-width:680px"><h2>Sin movimientos contables</h2>
    <p>El análisis trabaja sobre el libro diario (o mayor) importado. Importe primero la información contable de la empresa.</p>
    <a class="btn btn-primario" href="#/contable-importar">Importar información contable</a></div>`;
}
async function inicioAnalisis() {
  if (!requiereEmpresa()) return false;
  if (!(await vigente(prepararContexto()))) { sinDatos(); return false; }
  return true;
}
const exportUrl = (rep, fmt, extra = {}) => `/api/analisis/exportar/${rep}.${fmt}?` + new URLSearchParams(
  Object.entries({ ...qCtx(), ...extra }).filter(([, v]) => v !== null && v !== undefined && v !== "")).toString();
const botonesExport = (rep, extra = {}) => `<span class="exp"><a class="btn btn-sm" href="${exportUrl(rep, "xlsx", extra)}">Excel</a><a class="btn btn-sm" href="${exportUrl(rep, "pdf", extra)}">PDF</a></span>`;

// ------------------------------------------------------------------ gráficos (SVG, sin dependencias)
let tip = null;
document.addEventListener("mousemove", (e) => {
  const t = e.target.closest?.("[data-tip]");
  if (!tip) { tip = document.createElement("div"); tip.className = "viz-tip"; document.body.appendChild(tip); }
  if (!t) { tip.style.display = "none"; return; }
  tip.innerHTML = t.dataset.tip;
  tip.style.display = "block";
  const x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
  tip.style.left = `${x}px`; tip.style.top = `${e.clientY + 14}px`;
});
const abrev = (v) => { const a = Math.abs(v); return a >= 1e6 ? `${(v / 1e6).toFixed(1)} M` : a >= 1e3 ? `${(v / 1e3).toFixed(1)} k` : v.toFixed(0); };
function escala(min, max) { if (min === max) { max = min + 1; } const paso = Math.pow(10, Math.floor(Math.log10(Math.max(Math.abs(max - min), 1)))); return [Math.floor(min / paso) * paso, Math.ceil(max / paso) * paso]; }
function tablaDatos(cols, filas) {
  return `<details class="viz-datos"><summary>Ver datos</summary><table class="tabla"><thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${filas.map((f) => `<tr>${f.map((v, i) => `<td class="${i ? "num" : ""}">${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></details>`;
}

function graficoLineas(series, etiquetas, { alto = 220 } = {}) {
  if (!series.length || !etiquetas.length) return `<div class="vacio">Sin datos</div>`;
  const W = 460, H = alto, m = { t: 12, r: 14, b: 26, l: 58 };
  const vals = series.flatMap((s) => s.valores);
  const [y0, y1] = escala(Math.min(0, ...vals), Math.max(0, ...vals));
  const X = (i) => m.l + (etiquetas.length === 1 ? (W - m.l - m.r) / 2 : (i * (W - m.l - m.r)) / (etiquetas.length - 1));
  const Y = (v) => m.t + (1 - (v - y0) / (y1 - y0)) * (H - m.t - m.b);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => y0 + f * (y1 - y0));
  const svg = `<svg viewBox="0 0 ${W} ${H}" class="viz" role="img" aria-label="Gráfico de líneas">
    ${ticks.map((t) => `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t)}" y2="${Y(t)}" class="grid"/><text x="${m.l - 6}" y="${Y(t) + 4}" class="eje" text-anchor="end">${abrev(t)}</text>`).join("")}
    <line x1="${m.l}" x2="${W - m.r}" y1="${Y(0)}" y2="${Y(0)}" class="base"/>
    ${etiquetas.map((e, i) => `<text x="${X(i)}" y="${H - 8}" class="eje" text-anchor="middle">${esc(e)}</text>`).join("")}
    ${series.map((s, k) => `<polyline fill="none" stroke="${SERIES[k]}" stroke-width="2" stroke-linejoin="round" points="${s.valores.map((v, i) => `${X(i)},${Y(v)}`).join(" ")}"/>
      ${s.valores.map((v, i) => `<circle cx="${X(i)}" cy="${Y(v)}" r="4" fill="${SERIES[k]}" stroke="#fff" stroke-width="2"/><circle cx="${X(i)}" cy="${Y(v)}" r="11" fill="transparent" data-tip="<b>${esc(s.nombre)}</b><br>${esc(etiquetas[i])}: ${num(v)}"/>`).join("")}`).join("")}
  </svg>`;
  const leyenda = series.length > 1 ? `<div class="leyenda">${series.map((s, k) => `<span><i style="background:${SERIES[k]}"></i>${esc(s.nombre)}</span>`).join("")}</div>` : "";
  return svg + leyenda + tablaDatos(["Serie", ...etiquetas], series.map((s) => [s.nombre, ...s.valores.map(num)]));
}

function graficoBarras(items, { color = SERIES[0], colores, etiquetaValor = num, max = 12 } = {}) {
  // Barras horizontales en HTML: texto nítido a cualquier ancho; admite negativos (eje en el cero).
  items = items.slice(0, max);
  if (!items.length) return `<div class="vacio">Sin datos</div>`;
  const vals = items.map((i) => i.valor);
  const mn = Math.min(0, ...vals), mx = Math.max(0, ...vals), rango = mx - mn || 1;
  const cero = ((0 - mn) / rango) * 100;
  const filas = items.map((it, i) => {
    const izq = ((Math.min(it.valor, 0) - mn) / rango) * 100, ancho = Math.max((Math.abs(it.valor) / rango) * 100, it.valor ? 0.6 : 0);
    const c = colores ? colores[i] : color;
    return `<div class="hb-fila"><span class="hb-et" title="${esc(it.etiqueta)}">${esc(it.etiqueta)}</span>
      <span class="hb-pista">${mn < 0 ? `<i class="hb-cero" style="left:${cero}%"></i>` : ""}<b style="left:${izq}%;width:${ancho}%;background:${c}" data-tip="<b>${esc(it.etiqueta)}</b><br>${esc(it.detalle || "")} ${etiquetaValor(it.valor)}"></b></span>
      <span class="hb-val">${etiquetaValor(it.valor)}</span></div>`;
  }).join("");
  return `<div class="hb">${filas}</div>` + tablaDatos(["Categoría", "Valor"], items.map((i) => [i.etiqueta, etiquetaValor(i.valor)]));
}

function graficoAgrupado(grupos, series) {
  // grupos: [{etiqueta, valores:[...]}] ; series: nombres
  if (!grupos.length) return `<div class="vacio">Sin datos</div>`;
  const W = 460, H = 220, m = { t: 12, r: 12, b: 26, l: 58 };
  const vals = grupos.flatMap((g) => g.valores);
  const [y0, y1] = escala(Math.min(0, ...vals), Math.max(0, ...vals));
  const Y = (v) => m.t + (1 - (v - y0) / (y1 - y0)) * (H - m.t - m.b);
  const ancho = (W - m.l - m.r) / grupos.length, barra = Math.min(22, (ancho - 12) / series.length - 2);
  const svg = `<svg viewBox="0 0 ${W} ${H}" class="viz" role="img" aria-label="Barras agrupadas">
    ${[0, 0.5, 1].map((f) => y0 + f * (y1 - y0)).map((t) => `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t)}" y2="${Y(t)}" class="grid"/><text x="${m.l - 6}" y="${Y(t) + 4}" class="eje" text-anchor="end">${abrev(t)}</text>`).join("")}
    <line x1="${m.l}" x2="${W - m.r}" y1="${Y(0)}" y2="${Y(0)}" class="base"/>
    ${grupos.map((g, i) => {
      const x = m.l + i * ancho + (ancho - series.length * (barra + 2)) / 2;
      return g.valores.map((v, k) => `<rect x="${x + k * (barra + 2)}" y="${Math.min(Y(v), Y(0))}" width="${barra}" height="${Math.max(Math.abs(Y(v) - Y(0)), 1.5)}" rx="3" fill="${SERIES[k]}" data-tip="<b>${esc(series[k])}</b><br>${esc(g.etiqueta)}: ${num(v)}"/>`).join("") +
        `<text x="${m.l + i * ancho + ancho / 2}" y="${H - 8}" class="eje" text-anchor="middle">${esc(g.etiqueta)}</text>`;
    }).join("")}</svg>`;
  return svg + `<div class="leyenda">${series.map((s, k) => `<span><i style="background:${SERIES[k]}"></i>${esc(s)}</span>`).join("")}</div>` +
    tablaDatos(["Periodo", ...series], grupos.map((g) => [g.etiqueta, ...g.valores.map(num)]));
}

// ------------------------------------------------------------------ dashboard
rutas["analisis"] = async () => {
  if (!(await inicioAnalisis())) return;
  const d = await vigente(api("/analisis/dashboard", { params: qCtx() }));
  const k = d.kpi, g = d.graficos, run = d.run;
  const tile = (l, v, sub = "", cls = "") => `<div class="kpi ${cls}"><div class="l">${l}</div><div class="v">${v}</div>${sub ? `<div class="l">${sub}</div>` : ""}</div>`;
  const etiquetasMes = (g.evolucion[0]?.saldos || []).map((_, i) => per2(i + 1));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Análisis de cuentas</h1><p class="sub">Indicadores calculados con la información contable importada. Las observaciones son automáticas y requieren revisión profesional.</p></div>
      <div class="acciones" style="margin:0"><button class="btn btn-primario" id="an-run">Ejecutar análisis</button></div></div>
    ${barraContexto()}
    <div id="an-prog"></div>
    ${d.preliminar ? `<div class="alerta alerta-warn">Saldos iniciales <b>preliminares</b>: no hay saldos iniciales ni asiento de apertura importados para el ejercicio.</div>` : ""}
    ${d.advertencias.map((a) => `<div class="alerta alerta-info">${esc(a)}</div>`).join("")}
    ${run ? `<div class="alerta ${d.run_vigente ? "alerta-ok" : "alerta-warn"}">Último análisis #${run.id} · ${fechaHora(run.finalizado_en)} · ${run.duracion_ms} ms · ${esc(run.usuario)}
      ${d.run_vigente ? "" : " — <b>los datos cambiaron desde entonces: vuelva a ejecutar el análisis.</b>"}
      ${d.control.conciliado ? " · Saldos conciliados con el origen ✓" : " · <b>Los saldos NO concilian con el origen</b>"}</div>`
      : `<div class="alerta alerta-info">Aún no se ha ejecutado el análisis para este periodo. Los saldos se muestran en vivo; las observaciones aparecerán al ejecutarlo.</div>`}
    <div class="grid grid-5">
      ${tile("Cuentas analizadas", k.cuentas_analizadas)}
      ${tile("Movimientos", fmtNum.format(k.movimientos).replace(".00", ""))}
      ${tile("Cuentas con observaciones", k.cuentas_con_observaciones ?? "—", k.cuentas_sin_observaciones !== undefined ? `${k.cuentas_sin_observaciones} sin observaciones` : "")}
      ${tile("Importe sujeto a revisión", num(k.importe_sujeto_revision), "sin sumar exposiciones superpuestas")}
      ${tile("Avance de revisión", d.avance_revision ? `${d.avance_revision.pct} %` : "—", d.avance_revision ? `${d.avance_revision.revisados} de ${d.avance_revision.total} observaciones` : "")}
      ${tile("Saldos antiguos", num(k.saldos_antiguos), "documentos sobre el umbral de días")}
      ${tile("Posibles saldos contrarios", k.saldos_contrarios ? k.saldos_contrarios.cantidad : "—", k.saldos_contrarios ? num(k.saldos_contrarios.importe) : "")}
      ${tile("Diferencias origen–destino", num(k.diferencias_origen_destino))}
      ${tile("Variaciones significativas", k.variaciones_significativas ?? "—")}
      ${tile("Papeles de trabajo", Object.values(d.papeles).reduce((a, b) => a + b, 0), Object.entries(d.papeles).map(([e, n]) => `${ESTADOS_P[e]}: ${n}`).join(" · "))}
    </div>
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card"><h2>Evolución mensual de saldos por elemento</h2>${graficoLineas(g.evolucion.map((e) => ({ nombre: `${e.elemento} ${e.nombre}`, valores: e.saldos.map(Number) })), etiquetasMes)}</div>
      <div class="card"><h2>Observaciones por nivel de riesgo</h2>${graficoBarras(["ALTO", "MEDIO", "BAJO", "INFORMATIVO"].map((r) => ({ etiqueta: NOMBRES_RIESGO[r], valor: g.observaciones_riesgo[r] || 0 })), { colores: ["ALTO", "MEDIO", "BAJO", "INFORMATIVO"].map((r) => COLOR_RIESGO[r]), etiquetaValor: (v) => String(v) })}</div>
      <div class="card"><h2>Distribución de gastos por naturaleza</h2>${graficoBarras(g.distribucion_gastos.map((x) => ({ etiqueta: `${x.cuenta} ${x.descripcion || ""}`, valor: Number(x.importe) })).sort((a, b) => b.valor - a.valor))}</div>
      <div class="card"><h2>Gastos por centro de costo</h2>${graficoBarras(g.gastos_centro_costo.map((x) => ({ etiqueta: x.centro_costo, valor: Number(x.importe) })))}</div>
      <div class="card"><h2>Comparación de origen y destino</h2>${graficoAgrupado(g.origen_destino.map((x) => ({ etiqueta: per2(x.periodo), valores: [Number(x.origen), Number(x.destino), Number(x.cargas)] })), ["Gasto destinable (6)", "Destino (9)", "Cargas imputables (79)"])}</div>
      <div class="card"><h2>Antigüedad de saldos (cartera)</h2>${graficoBarras(g.antiguedad.tramos.map((t, i) => ({ etiqueta: t, valor: Number(g.antiguedad.totales[i]) })))}</div>
      <div class="card"><h2>Concentración por terceros (saldo de cartera)</h2>${graficoBarras(g.concentracion_terceros.map((x) => ({ etiqueta: x.razon_social || x.tercero, detalle: x.tercero, valor: Number(x.importe) })), { max: 10 })}</div>
    </div>`;
  enlazarContexto(navegar);
  $("#an-run").onclick = () => lanzarAnalisis();
};

async function lanzarAnalisis(extra = {}) {
  const caja = $("#an-prog");
  try {
    const r = await api("/analisis/ejecuciones", { method: "POST", params: { empresa_id: estado.empresaId }, body: { ejercicio: ctxA.ejercicio, desde: ctxA.desde, hasta: ctxA.hasta, ...extra } });
    if (caja) caja.innerHTML = `<div class="card">${barraProgreso(0, "En cola")}<div class="acciones"><button class="btn btn-sm btn-peligro" id="an-cancel">Cancelar análisis</button></div></div>`;
    $("#an-cancel")?.addEventListener("click", async () => { try { await api(`/analisis/ejecuciones/${r.run_id}/cancelar`, { method: "POST", params: { empresa_id: estado.empresaId } }); } catch (e) { toast(e.message, "err"); } });
    await esperarTrabajo(r.trabajo, (t) => { const b = $("#an-prog"); if (b && b.querySelector(".progreso")) { b.querySelector(".progreso-barra").style.width = `${Math.max(2, t.progreso)}%`; b.querySelector(".progreso-txt").innerHTML = `<span>${esc(t.etapa)}</span><b>${t.progreso}%</b>`; } });
    toast(`Análisis #${r.run_id} completado`, "ok");
    navegar();
  } catch (e) { toast(e.message, "err"); if (caja) caja.innerHTML = ""; navegar(); }
}

// ------------------------------------------------------------------ explorador jerárquico
const exp = { abiertos: new Set(["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]), texto: "", seleccion: null };
const COLS_EXP = [["saldo_inicial", "Saldo inicial"], ["debe", "Debe"], ["haber", "Haber"], ["neto", "Mov. neto"], ["saldo_final", "Saldo final"],
  ["naturaleza", "Nat."], ["movimientos", "Movs."], ["terceros", "Terceros"], ["variacion", "Variación"], ["variacion_pct", "Var. %"], ["hallazgos", "Observ."]];
let colsVisibles = new Set(JSON.parse(almacen.leer("an_cols", "null") || "null") || COLS_EXP.map((c) => c[0]));

rutas["analisis-explorador"] = async () => {
  if (!(await inicioAnalisis())) return;
  const b = await vigente(api("/analisis/balance", { params: qCtx() }));
  const nodos = b.nodos, porPadre = {};
  nodos.forEach((n) => { (porPadre[n.padre || ""] ||= []).push(n); });
  const coincide = (n) => !exp.texto || n.cuenta.startsWith(exp.texto) || (n.descripcion || "").toLowerCase().includes(exp.texto.toLowerCase());
  const visibles = [];
  const recorrer = (padre, prof) => (porPadre[padre] || []).forEach((n) => {
    const desc = exp.texto ? nodos.some((x) => x.cuenta.startsWith(n.cuenta) && coincide(x)) : true;
    if (!desc) return;
    visibles.push({ n, prof });
    if (exp.abiertos.has(n.cuenta) || exp.texto) recorrer(n.cuenta, prof + 1);
  });
  recorrer("", 0);
  const celda = (n, c) => {
    switch (c) {
      case "saldo_inicial": case "saldo_final": return `<td class="num">${saldoDA(n[c])}</td>`;
      case "debe": case "haber": case "neto": case "variacion": return `<td class="num">${num(n[c])}</td>`;
      case "variacion_pct": return `<td class="num">${n.saldo_anterior === null ? "—" : pct(n.variacion_pct)}</td>`;
      case "naturaleza": return `<td>${n.naturaleza === "D" ? "Deudora" : n.naturaleza === "A" ? "Acreedora" : "—"}</td>`;
      case "hallazgos": return `<td class="num">${n.hallazgos ? `${n.hallazgos} ${badgeRiesgo(n.riesgo)}` : ""}</td>`;
      default: return `<td class="num">${n[c]}</td>`;
    }
  };
  const cols = COLS_EXP.filter(([c]) => colsVisibles.has(c));
  const t = b.totales;
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Explorador del plan de cuentas</h1><p class="sub">Elemento → cuenta → subcuenta → divisionaria → subdivisionaria → analítica. Cada nivel incluye a sus subcuentas una sola vez.</p></div>
      ${botonesExport("balance")}</div>
    ${barraContexto(`<input id="ex-q" placeholder="Buscar cuenta o descripción…" value="${esc(exp.texto)}">
      <button class="btn btn-sm" id="ex-exp">Expandir todo</button><button class="btn btn-sm" id="ex-con">Contraer</button>
      <details class="col-menu"><summary class="btn btn-sm">Columnas</summary><div>${COLS_EXP.map(([c, n]) => `<label class="check"><input type="checkbox" data-col="${c}" ${colsVisibles.has(c) ? "checked" : ""}> ${n}</label>`).join("")}</div></details>`)}
    ${b.preliminar ? `<div class="alerta alerta-warn">Saldos iniciales PRELIMINARES (sin saldos iniciales importados).</div>` : ""}
    <div class="alerta ${b.control.conciliado ? "alerta-ok" : "alerta-err"}">Cuadre con la información original: ${b.control.origen_lineas} líneas · debe ${num(b.control.origen_debe)} · haber ${num(b.control.origen_haber)} — ${b.control.conciliado ? "el árbol concilia exactamente" : "NO concilia"}${t.cuadra ? "" : ` · <b>debe y haber del periodo no son iguales (diferencia ${num(Number(t.debe) - Number(t.haber))})</b>`}</div>
    <div class="explorador">
      <div class="tabla-wrap tabla-alta"><table class="tabla tabla-arbol"><thead><tr><th>Cuenta</th>${cols.map(([, n]) => `<th class="num">${n}</th>`).join("")}</tr></thead>
        <tbody>${visibles.map(({ n, prof }) => `<tr data-c="${n.cuenta}" class="nivel-${Math.min(n.nivel, 4)} ${exp.seleccion === n.cuenta ? "sel" : ""}">
          <td style="padding-left:${10 + prof * 16}px">${n.tiene_hijos ? `<button class="tg" data-tg="${n.cuenta}">${exp.abiertos.has(n.cuenta) || exp.texto ? "▾" : "▸"}</button>` : '<span class="tg-v"></span>'}
            <b>${esc(n.cuenta)}</b> ${esc(n.descripcion || "")} <small class="sub">${n.nivel_nombre}</small></td>${cols.map(([c]) => celda(n, c)).join("")}</tr>`).join("")
          || `<tr><td colspan="${cols.length + 1}" class="vacio">Sin cuentas con saldo o movimiento</td></tr>`}</tbody>
        <tfoot><tr><td>Total elementos 1–9 (las cuentas de orden van aparte)</td>${cols.map(([c]) => `<td class="num">${["debe", "haber"].includes(c) ? num(t[c]) : ["saldo_inicial", "saldo_final"].includes(c) ? num(t[c]) : c === "movimientos" ? t.movimientos : ""}</td>`).join("")}</tr></tfoot>
      </table></div>
      <aside class="panel-lateral" id="ex-panel">${exp.seleccion ? "" : `<div class="vacio">Seleccione una cuenta para ver su detalle, perfil de análisis y observaciones.</div>`}</aside>
    </div>`;
  enlazarContexto(navegar);
  $("#ex-q").addEventListener("change", (e) => { exp.texto = e.target.value.trim(); navegar(); });
  $("#ex-exp").onclick = () => { nodos.forEach((n) => n.tiene_hijos && exp.abiertos.add(n.cuenta)); navegar(); };
  $("#ex-con").onclick = () => { exp.abiertos.clear(); navegar(); };
  $$("[data-col]").forEach((c) => c.addEventListener("change", () => {
    c.checked ? colsVisibles.add(c.dataset.col) : colsVisibles.delete(c.dataset.col);
    almacen.guardar("an_cols", JSON.stringify([...colsVisibles])); navegar();
  }));
  $$("[data-tg]").forEach((bt) => bt.addEventListener("click", (e) => { e.stopPropagation(); const c = bt.dataset.tg; exp.abiertos.has(c) ? exp.abiertos.delete(c) : exp.abiertos.add(c); navegar(); }));
  $$("tr[data-c]").forEach((tr) => tr.addEventListener("click", () => { exp.seleccion = tr.dataset.c; $$("tr.sel").forEach((x) => x.classList.remove("sel")); tr.classList.add("sel"); panelCuenta(tr.dataset.c); }));
  if (exp.seleccion && nodos.some((n) => n.cuenta === exp.seleccion)) panelCuenta(exp.seleccion);
};

async function panelCuenta(codigo) {
  const p = $("#ex-panel");
  p.innerHTML = `<div class="vacio">Cargando…</div>`;
  let d;
  try { d = await api(`/analisis/cuenta/${codigo}`, { params: qCtx() }); } catch (e) { p.innerHTML = `<div class="alerta alerta-err">${esc(e.message)}</div>`; return; }
  const n = d.nodo;
  p.innerHTML = `
    <div class="cab-vista" style="margin-bottom:8px"><div><h2 style="margin:0">${esc(n.cuenta)} · ${esc(n.descripcion || "")}</h2><p class="sub">${n.nivel_nombre} · ${n.naturaleza === "D" ? "deudora" : n.naturaleza === "A" ? "acreedora" : "naturaleza indeterminada"}</p></div></div>
    <table class="mini-tabla">
      <tr><td>Saldo inicial</td><td>${saldoDA(n.saldo_inicial)}</td></tr><tr><td>Debe</td><td>${num(n.debe)}</td></tr><tr><td>Haber</td><td>${num(n.haber)}</td></tr>
      <tr><td><b>Saldo final</b></td><td><b>${saldoDA(n.saldo_final)}</b></td></tr>
      <tr><td>Periodo anterior</td><td>${saldoDA(n.saldo_anterior)} ${n.saldo_anterior !== null ? `(${pct(n.variacion_pct)})` : ""}</td></tr>
      <tr><td>Movimientos · terceros</td><td>${n.movimientos} · ${n.terceros}</td></tr></table>
    <div class="perfil"><b>${esc(d.perfil.nombre)}</b><br><small>${esc(d.perfil.descripcion)}</small></div>
    <h3 class="sec">Evolución del saldo en el ejercicio</h3>${graficoLineas([{ nombre: n.cuenta, valores: d.evolucion.map((x) => Number(x.saldo)) }], d.evolucion.map((x) => per2(x.periodo)), { alto: 160 })}
    <h3 class="sec">Principales terceros</h3>${d.terceros.length ? `<table class="mini-tabla">${d.terceros.map((t) => `<tr><td>${esc(t.razon_social || t.tercero)}</td><td>${saldoDA(t.saldo_final)}</td></tr>`).join("")}</table>` : '<p class="sub">Sin terceros</p>'}
    <h3 class="sec">Observaciones (${d.hallazgos.length})</h3>${d.hallazgos.slice(0, 8).map((h) => `<div class="obs-mini">${badgeRiesgo(h.riesgo)} <a href="#/analisis-hallazgos?id=${h.id}">${esc(h.titulo)}</a> <span class="sub">${num(h.importe)}</span></div>`).join("") || '<p class="sub">Sin observaciones en el último análisis.</p>'}
    <div class="acciones" style="justify-content:flex-start">
      <a class="btn btn-primario btn-sm" href="#/analisis-detalle?cuenta=${n.cuenta}">Navegar movimientos</a>
      <button class="btn btn-sm" id="pn-papel">${d.papel ? `Papel de trabajo (${ESTADOS_P[d.papel.estado]})` : "Generar papel de trabajo"}</button>
      ${botonesExport("cuenta", { cuenta: n.cuenta })}</div>`;
  $("#pn-papel").onclick = async () => {
    if (d.papel) { location.hash = `#/analisis-papel?id=${d.papel.id}`; return; }
    try { const r = await api("/analisis/papeles", { method: "POST", params: { empresa_id: estado.empresaId }, body: { ejercicio: ctxA.ejercicio, desde: ctxA.desde, hasta: ctxA.hasta, cuenta: n.cuenta } }); location.hash = `#/analisis-papel?id=${r.id}`; }
    catch (e) { toast(e.message, "err"); }
  };
}

// ------------------------------------------------------------------ navegación progresiva
const det = { pagina: 1, vistaMov: false };
rutas["analisis-detalle"] = async () => {
  if (!(await inicioAnalisis())) return;
  const p = parametrosHash();
  const filtros = { cuenta: p.cuenta || "", tercero: p.tercero || "", documento: p.documento || "", centro_costo: p.centro_costo || "", proyecto: p.proyecto || "", texto: p.texto || "" };
  const enlace = (f) => "#/analisis-detalle?" + new URLSearchParams(Object.entries({ ...filtros, ...f }).filter(([, v]) => v)).toString();
  const migas = [`<a href="#/analisis-explorador">Balance</a>`];
  if (filtros.cuenta) migas.push(`<a href="${enlace({ tercero: "", documento: "" })}">Cuenta ${esc(filtros.cuenta)}</a>`);
  if (filtros.tercero) migas.push(`<a href="${enlace({ documento: "" })}">Tercero ${esc(filtros.tercero)}</a>`);
  if (filtros.documento) migas.push(`<span>Documento ${esc(filtros.documento)}</span>`);
  const nivelMov = p.vista === "movimientos" || filtros.documento || !filtros.cuenta || filtros.texto || filtros.centro_costo || filtros.proyecto;
  let cuerpo;
  if (!nivelMov && !filtros.tercero) {
    const [b, t] = await vigente(Promise.all([api("/analisis/balance", { params: qCtx() }), api("/analisis/terceros", { params: qCtx({ cuenta: filtros.cuenta }) })]));
    const hijos = b.nodos.filter((n) => n.padre === filtros.cuenta);
    cuerpo = `${hijos.length ? `<div class="card"><h2>Subcuentas</h2><div class="tabla-wrap"><table class="tabla"><thead><tr><th>Cuenta</th><th class="num">Saldo inicial</th><th class="num">Debe</th><th class="num">Haber</th><th class="num">Saldo final</th><th class="num">Movs.</th></tr></thead><tbody>
      ${hijos.map((n) => `<tr class="clic" data-ir="${enlace({ cuenta: n.cuenta })}"><td><b>${n.cuenta}</b> ${esc(n.descripcion || "")}</td><td class="num">${saldoDA(n.saldo_inicial)}</td><td class="num">${num(n.debe)}</td><td class="num">${num(n.haber)}</td><td class="num">${saldoDA(n.saldo_final)}</td><td class="num">${n.movimientos}</td></tr>`).join("")}</tbody></table></div></div>` : ""}
      <div class="card"><h2>Por tercero (${t.total})</h2>${tablaTerceros(t.items, (x) => enlace({ tercero: x.tercero }))}</div>`;
  } else if (!nivelMov) {
    const d = await vigente(api("/analisis/documentos", { params: qCtx({ cuenta: filtros.cuenta, tercero: filtros.tercero }) }));
    cuerpo = `<div class="card"><h2>Documentos del tercero (${d.total})</h2><p class="sub">Saldo por documento (solo se netean líneas del mismo documento; sin compensaciones entre documentos).</p>
      <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Documento</th><th>TD</th><th>Emisión</th><th>Vencimiento</th><th class="num">Saldo inicial</th><th class="num">Debe</th><th class="num">Haber</th><th class="num">Saldo</th><th class="num">Líneas</th></tr></thead><tbody>
      ${d.items.map((x) => `<tr class="clic ${x.pendiente ? "" : "sub"}" data-ir="${enlace({ documento: x.documento === "(sin documento)" ? "(sin documento)" : x.documento })}"><td><b>${esc(x.documento)}</b></td><td>${esc(x.tipo_documento || "")}</td><td>${fecha(x.fecha_emision)}</td><td>${fecha(x.fecha_vencimiento)}</td>
        <td class="num">${num(x.si)}</td><td class="num">${num(x.debe)}</td><td class="num">${num(x.haber)}</td><td class="num"><b>${saldoDA(x.saldo_final)}</b></td><td class="num">${x.movimientos}</td></tr>`).join("")}</tbody></table></div></div>`;
  } else {
    const m = await vigente(api("/analisis/movimientos", { params: qCtx({ ...filtros, pagina: det.pagina, por_pagina: 100 }) }));
    const pags = Math.max(1, Math.ceil(m.total / m.por_pagina));
    cuerpo = `<div class="card"><div class="cab-vista" style="margin-bottom:8px"><h2 style="margin:0">Movimientos (${m.total})</h2>${botonesExport("movimientos", filtros)}</div>
      <div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th>Fecha</th><th>Asiento</th><th>Cuenta</th><th>Glosa</th><th>Documento</th><th>RUC / razón social</th><th>Mon.</th><th class="num">TC</th><th class="num">Debe</th><th class="num">Haber</th><th class="num">Saldo acumulado</th><th>C. costo</th><th>Proyecto</th><th>Origen</th></tr></thead>
      <tbody><tr class="sub"><td colspan="10">Saldo inicial</td><td class="num">${saldoDA(m.saldo_inicial)}</td><td colspan="3"></td></tr>
      ${m.items.map((x) => `<tr class="clic" data-linea="${x.id}"><td>${fecha(x.fecha_contable)}</td><td>${esc([x.subdiario, x.numero_asiento].filter(Boolean).join("-"))}</td><td>${esc(x.cuenta)}</td><td>${esc(x.glosa || "")}</td>
        <td>${esc([x.tipo_documento, [x.serie, x.numero_documento].filter(Boolean).join("-")].filter(Boolean).join(" "))}</td><td>${esc(x.documento_tercero || "")}<br><small class="sub">${esc(x.razon_social || "")}</small></td>
        <td>${esc(x.moneda)}</td><td class="num">${x.tipo_cambio ? Number(x.tipo_cambio).toFixed(3) : ""}</td><td class="num">${Number(x.debe_mn) ? num(x.debe_mn) : ""}</td><td class="num">${Number(x.haber_mn) ? num(x.haber_mn) : ""}</td>
        <td class="num">${saldoDA(x.saldo_acumulado)}</td><td>${esc(x.centro_costo || "")}</td><td>${esc(x.proyecto || "")}</td><td><small>${esc(x.archivo || "")} · fila ${x.fila_origen}</small></td></tr>`).join("")}</tbody>
      <tfoot><tr><td colspan="8">Totales del filtro</td><td class="num">${num(m.total_debe)}</td><td class="num">${num(m.total_haber)}</td><td class="num">${saldoDA(m.saldo_final)}</td><td colspan="3"></td></tr></tfoot></table></div>
      <div class="paginacion"><span>Haga clic en un movimiento para ver el asiento completo y la línea original del archivo.</span><span><button class="btn btn-sm" id="mv-ant" ${det.pagina <= 1 ? "disabled" : ""}>‹</button> ${det.pagina} / ${pags} <button class="btn btn-sm" id="mv-sig" ${det.pagina >= pags ? "disabled" : ""}>›</button></span></div></div>`;
  }
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Navegación de movimientos</h1><nav class="migas">${migas.join(" › ")}</nav></div>
      ${filtros.cuenta && !nivelMov ? `<a class="btn" href="${enlace({ vista: "movimientos" })}">Ver todos los movimientos</a>` : ""}</div>
    ${barraContexto()}
    <form class="filtros card" id="f-det">
      ${["cuenta", "tercero", "documento", "centro_costo", "proyecto", "texto"].map((k) => `<div class="campo"><label>${{ cuenta: "Cuenta", tercero: "RUC tercero", documento: "Documento (serie-número)", centro_costo: "Centro de costo", proyecto: "Proyecto", texto: "Buscar texto" }[k]}</label><input name="${k}" value="${esc(filtros[k])}"></div>`).join("")}
      <button class="btn btn-primario">Aplicar</button></form>
    ${cuerpo}`;
  enlazarContexto(navegar);
  $("#f-det").onsubmit = (e) => { e.preventDefault(); det.pagina = 1; const f = datosForm(e.target); location.hash = "#/analisis-detalle?" + new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString(); };
  $$("[data-ir]").forEach((tr) => tr.addEventListener("click", () => { det.pagina = 1; location.hash = tr.dataset.ir; }));
  $$("[data-linea]").forEach((tr) => tr.addEventListener("click", () => verAsiento(Number(tr.dataset.linea))));
  $("#mv-ant")?.addEventListener("click", () => { det.pagina--; navegar(); });
  $("#mv-sig")?.addEventListener("click", () => { det.pagina++; navegar(); });
};

function tablaTerceros(items, enlace) {
  if (!items.length) return `<div class="vacio">Sin terceros</div>`;
  return `<div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th>Tercero</th><th>Razón social</th><th class="num">Saldo inicial</th><th class="num">Debe</th><th class="num">Haber</th><th class="num">Saldo final</th><th class="num">Docs.</th><th class="num">Movs.</th></tr></thead><tbody>
    ${items.map((x) => `<tr class="clic" data-ir="${enlace(x)}"><td><b>${esc(x.tercero)}</b></td><td>${esc(x.razon_social || "")}</td><td class="num">${saldoDA(x.si)}</td><td class="num">${num(x.debe)}</td><td class="num">${num(x.haber)}</td><td class="num"><b>${saldoDA(x.saldo_final)}</b></td><td class="num">${x.documentos}</td><td class="num">${x.movimientos}</td></tr>`).join("")}</tbody></table></div>`;
}

async function verAsiento(lineaId) {
  const [a, o] = await Promise.all([api(`/analisis/lineas/${lineaId}/asiento`, { params: { empresa_id: estado.empresaId } }),
    api(`/analisis/lineas/${lineaId}/origen`, { params: { empresa_id: estado.empresaId } })]);
  abrirModal(`Asiento ${a.asiento || "(sin número)"} · periodo ${per2(a.periodo)} · ${fecha(a.fecha)}`, `
    <div class="alerta ${a.cuadra ? "alerta-ok" : "alerta-err"}">Lote #${a.lote.id} · ${esc(a.lote.archivo)} · ${a.cuadra ? "asiento cuadrado" : "asiento DESCUADRADO"} · debe ${num(a.total_debe)} · haber ${num(a.total_haber)}</div>
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Cuenta</th><th>Glosa</th><th>Documento</th><th>Tercero</th><th class="num">Debe</th><th class="num">Haber</th><th>CC</th><th>Fila</th></tr></thead><tbody>
      ${a.lineas.map((x) => `<tr class="${x.id === lineaId ? "sel" : ""}"><td><b>${esc(x.cuenta)}</b></td><td>${esc(x.glosa || "")}</td><td>${esc([x.serie, x.numero_documento].filter(Boolean).join("-"))}</td><td>${esc(x.documento_tercero || "")}</td>
        <td class="num">${Number(x.debe_mn) ? num(x.debe_mn) : ""}</td><td class="num">${Number(x.haber_mn) ? num(x.haber_mn) : ""}</td><td>${esc(x.centro_costo || "")}</td><td>${x.fila_origen}</td></tr>`).join("")}</tbody></table></div>
    <h3 class="sec">Línea original del archivo (fila ${o.fila}, hoja ${esc(o.lote.hoja || "")})</h3>
    ${o.original ? `<div class="tabla-wrap"><table class="tabla"><tbody>${o.original.map((c) => `<tr><th style="width:40%">${esc(c.columna)}</th><td>${esc(c.valor)}</td></tr>`).join("")}</tbody></table></div>` : `<div class="alerta alerta-warn">${esc(o.aviso || "No disponible")}</div>`}
    <p class="sub">Archivo ${esc(o.lote.archivo)} · importado por ${esc(o.lote.usuario)} · ${fechaHora(o.lote.fecha)} · huella <code>${esc((o.lote.hash || "").slice(0, 16))}…</code></p>`);
}

// ------------------------------------------------------------------ origen y destino
rutas["analisis-destino"] = async () => {
  if (!(await inicioAnalisis())) return;
  const [od, reglasD] = await vigente(Promise.all([api("/analisis/destino", { params: qCtx() }), api("/analisis/destino/reglas", { params: { empresa_id: estado.empresaId } })]));
  const t = od.totales, pol = od.politica;
  const estadoB = (e) => `<span class="badge ${e === "CONFORME" || e === "CON_DESTINO" ? "b-ok" : e === "EXCLUIDA" || e === "NO_APLICA" ? "" : "b-warn"}">${esc(e.replaceAll("_", " ").toLowerCase())}</span>`;
  const tabla = (cols, filas) => `<div class="tabla-wrap"><table class="tabla"><thead><tr>${cols.map((c, i) => `<th class="${i ? "num" : ""}">${c}</th>`).join("")}</tr></thead><tbody>${filas.join("") || `<tr><td colspan="${cols.length}" class="vacio">Sin datos</td></tr>`}</tbody></table></div>`;
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Origen y destino</h1><p class="sub">Gastos por naturaleza destinables (${esc(pol.destinables.join(", "))}) frente a destino (${esc(pol.destino.join(", "))}) y cuenta ${esc(pol.cargas)}. No se exige que toda la clase 6 coincida con la clase 9.</p></div>
      ${botonesExport("destino")}</div>
    ${barraContexto()}
    ${pol.usa_destino ? "" : `<div class="alerta alerta-info">La empresa está configurada sin cuentas de destino (Reglas contables).</div>`}
    <div class="grid grid-5">
      <div class="kpi"><div class="l">Gasto destinable</div><div class="v">${num(t.origen)}</div></div>
      <div class="kpi"><div class="l">Destino registrado</div><div class="v">${num(t.destino)}</div></div>
      <div class="kpi"><div class="l">Cargas imputables (79)</div><div class="v">${num(t.cargas_imputables)}</div></div>
      <div class="kpi"><div class="l">Excluido de la distribución</div><div class="v">${num(t.excluido)}</div></div>
      <div class="kpi"><div class="l">Provisión aplicada (48) / abono 78</div><div class="v" style="font-size:17px">${num(t.provision_aplicada_48)} / ${num(t.abono_78)}</div></div>
    </div>
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card"><h2>Por periodo</h2>${graficoAgrupado(od.resumen.map((x) => ({ etiqueta: per2(x.periodo), valores: [Number(x.origen), Number(x.destino), Number(x.cargas_imputables)] })), ["Gasto destinable", "Destino", "Cuenta 79"])}
        ${tabla(["Periodo", "Origen", "Destino", "79", "Origen − destino", "Destino − 79", "Estado"], od.resumen.map((x) => `<tr><td>${per2(x.periodo)}</td><td class="num">${num(x.origen)}</td><td class="num">${num(x.destino)}</td><td class="num">${num(x.cargas_imputables)}</td><td class="num">${num(x.diferencia)}</td><td class="num">${num(x.diferencia_79)}</td><td class="num">${estadoB(x.estado)}</td></tr>`))}</div>
      <div class="card"><h2>Por centro de costo</h2>${tabla(["Centro de costo", "Origen", "Destino", "Diferencia", "Estado"], od.centros_costo.map((x) => `<tr><td>${esc(x.clave)}</td><td class="num">${num(x.origen)}</td><td class="num">${num(x.destino)}</td><td class="num">${num(x.diferencia)}</td><td class="num">${estadoB(x.estado)}</td></tr>`))}
        <h2 style="margin-top:16px">Por cuenta de destino</h2>${tabla(["Destino", "Esperado", "Registrado", "Diferencia", "Estado"], od.destinos.map((x) => `<tr><td>${esc(x.clave)}</td><td class="num">${num(x.esperado)}</td><td class="num">${num(x.registrado)}</td><td class="num">${num(x.diferencia)}</td><td class="num">${estadoB(x.estado)}</td></tr>`))}</div>
      <div class="card"><h2>Por cuenta de origen</h2>${tabla(["Cuenta", "Gasto", "Destino esperado", "Sin destino configurado", "Estado"], od.origenes.map((x) => `<tr><td><b>${esc(x.clave)}</b> ${esc(x.descripcion || "")}</td><td class="num">${num(x.origen)}</td><td class="num">${num(x.esperado)}</td><td class="num">${num(x.sin_regla)}</td><td class="num">${estadoB(x.estado)}</td></tr>`))}</div>
      <div class="card"><h2>Asientos a revisar (${od.asientos.length})</h2>${tabla(["Asiento", "Periodo", "Origen", "Destino", "Situación"], od.asientos.map((x) => `<tr class="clic" data-linea="${x.linea_id}"><td>${esc(x.asiento)}</td><td class="num">${per2(x.periodo)}</td><td class="num">${num(x.origen)}</td><td class="num">${num(x.destino)}</td><td class="num">${estadoB(x.estado)}</td></tr>`))}</div>
    </div>
    <div class="card"><div class="cab-vista" style="margin-bottom:8px"><h2 style="margin:0">Reglas de distribución</h2><button class="btn btn-primario btn-sm" id="rd-nueva">Nueva regla</button></div>
      <p class="sub">Si no hay regla aplicable se usa el destino del plan de cuentas y, en su defecto, el del centro de costo. Las reglas de una misma combinación no pueden superar 100 %.</p>
      ${tabla(["Origen", "C. costo", "Proyecto", "Unidad", "Maquinaria", "Destino", "%", "Vigencia", "Estado", ""], reglasD.map((r) => `<tr><td><b>${esc(r.cuenta_origen)}</b> ${esc(r.nombre || "")}</td><td class="num">${esc(r.centro_costo || "todos")}</td><td class="num">${esc(r.proyecto || "—")}</td><td class="num">${esc(r.unidad_negocio || "—")}</td><td class="num">${esc(r.maquinaria || "—")}</td>
        <td class="num">${r.excluir ? '<span class="badge">Excluida</span>' : esc(r.cuenta_destino)}</td><td class="num">${r.excluir ? "" : Number(r.porcentaje).toFixed(2)}</td><td class="num">${fecha(r.vigente_desde)} – ${fecha(r.vigente_hasta)}</td><td class="num">${r.activa ? "Activa" : "Inactiva"}</td>
        <td class="num"><button class="btn btn-sm" data-rd="${r.id}">Editar</button> <button class="btn btn-sm btn-peligro" data-rdx="${r.id}">Eliminar</button></td></tr>`))}</div>`;
  enlazarContexto(navegar);
  $$("[data-linea]").forEach((tr) => tr.addEventListener("click", () => verAsiento(Number(tr.dataset.linea))));
  const form = (r) => {
    const c = abrirModal(r ? "Editar regla de distribución" : "Nueva regla de distribución", `<form id="f-rd"><div class="form-grid">
      <div class="campo"><label>Cuenta de origen (prefijo)</label><input name="cuenta_origen" required pattern="\\d+" value="${esc(r?.cuenta_origen)}"></div>
      <div class="campo"><label>Nombre</label><input name="nombre" value="${esc(r?.nombre)}"></div>
      <div class="campo"><label>Centro de costo</label><input name="centro_costo" value="${esc(r?.centro_costo)}" placeholder="todos"></div>
      <div class="campo"><label>Proyecto</label><input name="proyecto" value="${esc(r?.proyecto)}"></div>
      <div class="campo"><label>Unidad de negocio</label><input name="unidad_negocio" value="${esc(r?.unidad_negocio)}"></div>
      <div class="campo"><label>Maquinaria</label><input name="maquinaria" value="${esc(r?.maquinaria)}"></div>
      <div class="campo"><label>Cuenta de destino</label><input name="cuenta_destino" pattern="\\d*" value="${esc(r?.cuenta_destino)}"></div>
      <div class="campo"><label>Porcentaje</label><input name="porcentaje" type="number" min="0" max="100" step="0.01" value="${r ? Number(r.porcentaje) : 100}"></div>
      <div class="campo"><label>Vigente desde</label><input name="vigente_desde" type="date" value="${esc(r?.vigente_desde || "")}"></div>
      <div class="campo"><label>Vigente hasta</label><input name="vigente_hasta" type="date" value="${esc(r?.vigente_hasta || "")}"></div>
      <label class="check"><input type="checkbox" name="excluir" ${r?.excluir ? "checked" : ""}> Excluir de la distribución</label>
      <label class="check"><input type="checkbox" name="activa" ${!r || r.activa ? "checked" : ""}> Activa</label></div>
      <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-primario">Guardar</button></div></form>`);
    $("#f-rd", c).onsubmit = async (e) => {
      e.preventDefault();
      const d = datosForm(e.target);
      ["vigente_desde", "vigente_hasta"].forEach((k) => { if (!d[k]) d[k] = null; });
      try { await api(r ? `/analisis/destino/reglas/${r.id}` : "/analisis/destino/reglas", { method: r ? "PUT" : "POST", params: { empresa_id: estado.empresaId }, body: d }); cerrarModal(); toast("Regla guardada", "ok"); navegar(); }
      catch (err) { toast(err.message, "err"); }
    };
  };
  $("#rd-nueva").onclick = () => form();
  $$("[data-rd]").forEach((b) => b.addEventListener("click", () => form(reglasD.find((x) => x.id === Number(b.dataset.rd)))));
  $$("[data-rdx]").forEach((b) => b.addEventListener("click", async () => { try { await api(`/analisis/destino/reglas/${b.dataset.rdx}`, { method: "DELETE", params: { empresa_id: estado.empresaId } }); navegar(); } catch (e) { toast(e.message, "err"); } }));
};

// ------------------------------------------------------------------ antigüedad
const ant = { fecha_corte: null, base: "VENCIMIENTO", fuente: "LIBROS", cuentas: "", vista: "terceros" };
rutas["analisis-antiguedad"] = async () => {
  if (!(await inicioAnalisis())) return;
  if (!ant.fecha_corte) { const p = Math.min(ctxA.hasta, 12); ant.fecha_corte = new Date(ctxA.ejercicio, p, 0).toISOString().slice(0, 10); }
  const params = { empresa_id: estado.empresaId, ejercicio: ctxA.ejercicio, fecha_corte: ant.fecha_corte, base: ant.base, fuente: ant.fuente, cuentas: ant.cuentas || undefined };
  const a = await vigente(api("/analisis/antiguedad", { params }));
  ant.cuentas = ant.cuentas || a.cuentas.join(",");
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Antigüedad de saldos</h1><p class="sub">${esc(a.nota)}</p></div>${botonesExport("antiguedad", { fecha_corte: ant.fecha_corte, base: ant.base, fuente: ant.fuente, cuenta: ant.cuentas })}</div>
    <form class="filtros card" id="f-ant">
      <div class="campo"><label>Ejercicio</label><select name="ejercicio">${ctxA.periodos.map((x) => `<option ${x.ejercicio === ctxA.ejercicio ? "selected" : ""}>${x.ejercicio}</option>`).join("")}</select></div>
      <div class="campo"><label>Fecha de corte</label><input type="date" name="fecha_corte" value="${ant.fecha_corte}"></div>
      <div class="campo"><label>Antigüedad desde</label><select name="base"><option value="VENCIMIENTO" ${ant.base === "VENCIMIENTO" ? "selected" : ""}>Fecha de vencimiento</option><option value="EMISION" ${ant.base === "EMISION" ? "selected" : ""}>Fecha de emisión</option></select></div>
      <div class="campo"><label>Fuente</label><select name="fuente"><option value="LIBROS" ${ant.fuente === "LIBROS" ? "selected" : ""}>Libros (diario)</option><option value="CARTERA" ${ant.fuente === "CARTERA" ? "selected" : ""}>Cartera informada (CxC / CxP)</option></select></div>
      <div class="campo" style="flex:1"><label>Cuentas (prefijos)</label><input name="cuentas" value="${esc(ant.cuentas)}"></div>
      <button class="btn btn-primario">Calcular</button></form>
    <div class="grid grid-4">
      <div class="kpi"><div class="l">Total</div><div class="v">${num(a.total)}</div></div>
      <div class="kpi"><div class="l">Saldo antiguo (&gt; ${a.configuracion.dias_saldo_antiguo} días)</div><div class="v">${num(a.saldo_antiguo)}</div></div>
      <div class="kpi"><div class="l">Documentos preliminares</div><div class="v">${a.documentos_preliminares}</div><div class="l">${num(a.importe_preliminar)}</div></div>
      <div class="kpi"><div class="l">Rangos</div><div class="v" style="font-size:13px">${esc(a.configuracion.nombre)}: ${a.tramos.slice(1).join(" · ")}</div></div>
    </div>
    <div class="card" style="margin-top:16px"><h2>Por tramo</h2>${graficoBarras(a.tramos.map((t, i) => ({ etiqueta: t, valor: Number(a.totales[i]) })))}</div>
    <div class="card"><div class="pestanas"><button class="btn ${ant.vista === "terceros" ? "btn-primario" : ""}" data-v="terceros">Por tercero</button><button class="btn ${ant.vista === "docs" ? "btn-primario" : ""}" data-v="docs">Por documento</button></div>
    ${ant.vista === "terceros" ? `<div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th>Tercero</th>${a.tramos.map((t) => `<th class="num">${esc(t)}</th>`).join("")}<th class="num">Total</th></tr></thead><tbody>
      ${a.terceros.map((x) => `<tr><td><b>${esc(x.tercero)}</b><br><small class="sub">${esc(x.razon_social || "")}${x.preliminar ? " · preliminar" : ""}</small></td>${x.tramos.map((v) => `<td class="num">${Number(v) ? num(v) : ""}</td>`).join("")}<td class="num"><b>${num(x.total)}</b></td></tr>`).join("")}</tbody>
      <tfoot><tr><td>Total</td>${a.totales.map((v) => `<td class="num">${num(v)}</td>`).join("")}<td class="num">${num(a.total)}</td></tr></tfoot></table></div>`
      : `<div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th>Cuenta</th><th>Tercero</th><th>Documento</th><th>Emisión</th><th>Vencimiento</th><th class="num">Días</th><th>Tramo</th><th class="num">Importe</th><th>Situación</th></tr></thead><tbody>
      ${a.documentos.map((x) => `<tr><td>${esc(x.cuenta)}</td><td>${esc(x.tercero || "")}</td><td>${esc(x.documento)}</td><td>${fecha(x.fecha_emision)}</td><td>${fecha(x.fecha_vencimiento)}</td><td class="num">${x.dias}</td><td>${esc(x.tramo_nombre)}</td><td class="num">${num(x.importe)}</td>
        <td>${x.preliminar ? `<span class="badge b-warn" title="${esc(x.motivos.join("; "))}">Preliminar</span>` : '<span class="badge b-ok">Determinado</span>'}</td></tr>`).join("")}</tbody></table></div>`}</div>`;
  $("#f-ant").onsubmit = (e) => { e.preventDefault(); const d = datosForm(e.target); ctxA.ejercicio = Number(d.ejercicio); Object.assign(ant, { fecha_corte: d.fecha_corte, base: d.base, fuente: d.fuente, cuentas: d.cuentas }); navegar(); };
  $$("[data-v]").forEach((b) => b.addEventListener("click", () => { ant.vista = b.dataset.v; navegar(); }));
};

// ------------------------------------------------------------------ comparativos
const cmp = { modo: "MES_ANTERIOR", dimension: "CUENTA", medida: "SALDO", nivel: 2, cuenta: "" };
rutas["analisis-comparativo"] = async () => {
  if (!(await inicioAnalisis())) return;
  const c = await vigente(api("/analisis/comparativo", { params: { empresa_id: estado.empresaId, ejercicio: ctxA.ejercicio, periodo: Math.min(ctxA.hasta, 12), ...cmp, cuenta: cmp.cuenta || undefined } }));
  const sel = (n, ops, v) => `<select name="${n}">${ops.map(([k, t]) => `<option value="${k}" ${String(v) === String(k) ? "selected" : ""}>${t}</option>`).join("")}</select>`;
  const spark = (vals) => { const n = vals.map(Number); if (n.length < 2) return ""; const mn = Math.min(...n), mx = Math.max(...n), r = mx - mn || 1;
    return `<svg width="80" height="20" class="spark"><polyline fill="none" stroke="${SERIES[0]}" stroke-width="1.5" points="${n.map((v, i) => `${(i * 78) / (n.length - 1) + 1},${19 - ((v - mn) / r) * 17}`).join(" ")}"/></svg>`; };
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Análisis comparativo</h1><p class="sub">${esc(c.actual.etiqueta)} frente a ${esc(c.base.etiqueta)}. Variación % «N/A» cuando la base es cero.</p></div>
      <span>${botonesExport("comparativo", { modo: cmp.modo, dimension: cmp.dimension, medida: cmp.medida, nivel: cmp.nivel, cuenta: cmp.cuenta })} ${botonesExport("gastos")} ${botonesExport("ingresos")}</span></div>
    ${barraContexto()}
    <form class="filtros card" id="f-cmp">
      <div class="campo"><label>Comparar</label>${sel("modo", [["MES_ANTERIOR", "Mes actual vs anterior"], ["MISMO_MES_ANTERIOR", "Mes vs mismo mes del año anterior"], ["ACUMULADO", "Acumulado anual"]], cmp.modo)}</div>
      <div class="campo"><label>Dimensión</label>${sel("dimension", [["CUENTA", "Cuenta"], ["CENTRO_COSTO", "Centro de costo"], ["PROYECTO", "Proyecto"], ["UNIDAD_NEGOCIO", "Unidad de negocio"], ["MONEDA", "Moneda"], ["TERCERO", "Tercero"]], cmp.dimension)}</div>
      <div class="campo"><label>Medida</label>${sel("medida", [["SALDO", "Saldo final"], ["MOVIMIENTO", "Movimiento neto"]], cmp.medida)}</div>
      <div class="campo"><label>Nivel de cuenta</label>${sel("nivel", [[1, "Elemento"], [2, "Cuenta"], [3, "Subcuenta"], [0, "Cuentas de movimiento"]], cmp.nivel)}</div>
      <div class="campo"><label>Cuentas (prefijos)</label><input name="cuenta" value="${esc(cmp.cuenta)}" placeholder="p. ej. 6 o 12,42"></div>
      <button class="btn btn-primario">Comparar</button></form>
    ${c.advertencias.map((a) => `<div class="alerta alerta-warn">${esc(a)}</div>`).join("")}
    <div class="grid grid-4"><div class="kpi"><div class="l">Total ${esc(c.actual.etiqueta)}</div><div class="v">${num(c.total_actual)}</div></div>
      <div class="kpi"><div class="l">Total ${esc(c.base.etiqueta)}</div><div class="v">${num(c.total_base)}</div></div>
      <div class="kpi"><div class="l">Variación</div><div class="v">${num(Number(c.total_actual) - Number(c.total_base))}</div></div>
      <div class="kpi"><div class="l">Concentración (5 principales)</div><div class="v">${c.concentracion_top5_pct ?? "—"} %</div></div></div>
    <div class="tabla-wrap tabla-alta" style="margin-top:16px"><table class="tabla"><thead><tr><th>Clave</th><th class="num">${esc(c.actual.etiqueta)}</th><th class="num">${esc(c.base.etiqueta)}</th><th class="num">Variación</th><th class="num">Var. %</th><th class="num">Participación</th><th class="num">Promedio mensual</th>${c.dimension === "MONEDA" ? '<th class="num">Importe ME</th>' : ""}<th>Tendencia</th></tr></thead><tbody>
      ${c.filas.map((f) => `<tr><td><b>${esc(f.clave)}</b> ${esc(f.descripcion || "")}</td><td class="num">${num(f.actual)}</td><td class="num">${num(f.base)}</td><td class="num">${num(f.variacion)}</td><td class="num">${pct(f.variacion_pct)}</td><td class="num">${f.participacion_pct ?? "—"} %</td><td class="num">${num(f.promedio_mensual)}</td>${c.dimension === "MONEDA" ? `<td class="num">${num(f.importe_me)}</td>` : ""}<td>${spark(f.tendencia)}</td></tr>`).join("") || '<tr><td colspan="8" class="vacio">Sin datos</td></tr>'}</tbody></table></div>`;
  enlazarContexto(navegar);
  $("#f-cmp").onsubmit = (e) => { e.preventDefault(); const d = datosForm(e.target); Object.assign(cmp, d, { nivel: Number(d.nivel) }); navegar(); };
};

// ------------------------------------------------------------------ hallazgos
const fh = { riesgo: "", estado: "", regla: "", cuenta: "", texto: "", pagina: 1 };
rutas["analisis-hallazgos"] = async () => {
  if (!(await inicioAnalisis())) return;
  const runs = await vigente(api("/analisis/ejecuciones", { params: { empresa_id: estado.empresaId, limite: 30 } }));
  const completados = runs.filter((r) => r.estado === "COMPLETADO");
  const pid = parametrosHash().id;
  if (!completados.length) { vista().innerHTML = `<h1>Observaciones</h1><div class="card vacio">Aún no hay análisis ejecutados. <a href="#/analisis">Ir al dashboard</a></div>`; return; }
  fh.run = fh.run && completados.some((r) => r.id === fh.run) ? fh.run : completados[0].id;
  const h = await vigente(api("/analisis/hallazgos", { params: { empresa_id: estado.empresaId, run_id: fh.run, ...fh, run: undefined, por_pagina: 100 } }));
  const pags = Math.max(1, Math.ceil(h.total / h.por_pagina));
  const run = completados.find((r) => r.id === fh.run);
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Observaciones del análisis</h1><p class="sub">Hallazgos automáticos: <b>posibles</b> incidencias que requieren revisión profesional. No constituyen conclusiones.</p></div>
      ${botonesExport("observaciones", { run_id: fh.run, riesgo: fh.riesgo, estado: fh.estado })}</div>
    <form class="filtros card" id="f-h">
      <div class="campo"><label>Análisis</label><select name="run">${completados.map((r) => `<option value="${r.id}" ${r.id === fh.run ? "selected" : ""}>#${r.id} · ${r.ejercicio} ${per2(r.periodo_desde)}–${per2(r.periodo_hasta)} · ${fechaHora(r.finalizado_en)}</option>`).join("")}</select></div>
      <div class="campo"><label>Riesgo</label><select name="riesgo"><option value="">Todos</option>${Object.entries(NOMBRES_RIESGO).map(([k, n]) => `<option value="${k}" ${fh.riesgo === k ? "selected" : ""}>${n} (${h.resumen.por_riesgo[k] || 0})</option>`).join("")}</select></div>
      <div class="campo"><label>Estado de revisión</label><select name="estado"><option value="">Todos</option>${Object.entries(ESTADOS_H).map(([k, n]) => `<option value="${k}" ${fh.estado === k ? "selected" : ""}>${n} (${h.resumen.por_estado[k] || 0})</option>`).join("")}</select></div>
      <div class="campo"><label>Regla</label><select name="regla"><option value="">Todas</option>${Object.entries(h.resumen.por_regla).map(([k, n]) => `<option value="${k}" ${fh.regla === k ? "selected" : ""}>${k} (${n})</option>`).join("")}</select></div>
      <div class="campo"><label>Cuenta</label><input name="cuenta" value="${esc(fh.cuenta)}"></div>
      <div class="campo" style="flex:1"><label>Buscar</label><input name="texto" value="${esc(fh.texto)}"></div><button class="btn btn-primario">Filtrar</button></form>
    <div class="alerta alerta-info">Análisis #${run.id}: ${h.total} observación(es) con el filtro · importe sujeto a revisión ${num(h.importe_sujeto_revision)} (sin superponer exposiciones).</div>
    <div class="explorador">
      <div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr><th>Riesgo</th><th>Código</th><th>Cuenta</th><th>Observación</th><th class="num">Importe</th><th>Estado</th><th>Responsable</th></tr></thead><tbody>
        ${h.items.map((x) => `<tr class="clic ${String(x.id) === pid ? "sel" : ""}" data-h="${x.id}"><td>${badgeRiesgo(x.riesgo)}</td><td><code>${esc(x.regla_codigo)}</code><br><small class="sub">v${x.regla_version}</small></td><td>${esc(x.cuenta)}</td>
          <td>${esc(x.titulo)}${x.tercero ? `<br><small class="sub">Tercero ${esc(x.tercero)}</small>` : ""}${x.documento ? `<small class="sub"> · ${esc(x.documento)}</small>` : ""}</td><td class="num">${num(x.importe)}</td><td><span class="badge">${ESTADOS_H[x.estado]}</span></td><td>${esc(x.responsable || "")}</td></tr>`).join("") || '<tr><td colspan="7" class="vacio">Sin observaciones</td></tr>'}</tbody></table>
        <div class="paginacion"><span></span><span><button class="btn btn-sm" id="h-ant" ${fh.pagina <= 1 ? "disabled" : ""}>‹</button> ${fh.pagina} / ${pags} <button class="btn btn-sm" id="h-sig" ${fh.pagina >= pags ? "disabled" : ""}>›</button></span></div></div>
      <aside class="panel-lateral" id="h-panel"><div class="vacio">Seleccione una observación para revisarla.</div></aside></div>`;
  $("#f-h").onsubmit = (e) => { e.preventDefault(); const d = datosForm(e.target); Object.assign(fh, d, { run: Number(d.run), pagina: 1 }); navegar(); };
  $("#h-ant").onclick = () => { fh.pagina--; navegar(); };
  $("#h-sig").onclick = () => { fh.pagina++; navegar(); };
  $$("[data-h]").forEach((tr) => tr.addEventListener("click", () => { $$("tr.sel").forEach((x) => x.classList.remove("sel")); tr.classList.add("sel"); panelHallazgo(Number(tr.dataset.h)); }));
  if (pid) panelHallazgo(Number(pid));
};

async function panelHallazgo(id) {
  const p = $("#h-panel");
  const h = await api(`/analisis/hallazgos/${id}`, { params: { empresa_id: estado.empresaId } });
  const ev = h.evidencia || {};
  p.innerHTML = `
    <h2 style="margin-top:0">${badgeRiesgo(h.riesgo)} ${esc(h.titulo)}</h2>
    <p class="sub">Regla <code>${esc(h.regla_codigo)}</code> · ${esc(h.regla_nombre)} · versión ${h.regla_version}</p>
    <table class="mini-tabla"><tr><td>Cuenta</td><td>${esc(h.cuenta)}</td></tr><tr><td>Importe involucrado</td><td>${num(h.importe)}</td></tr>
      ${h.tercero ? `<tr><td>Tercero</td><td>${esc(h.tercero)}</td></tr>` : ""}${h.documento ? `<tr><td>Documento</td><td>${esc(h.documento)}</td></tr>` : ""}${h.asiento ? `<tr><td>Asiento</td><td>${esc(h.asiento)}</td></tr>` : ""}</table>
    <h3 class="sec">Evidencia</h3><table class="mini-tabla">${Object.entries(ev).map(([k, v]) => `<tr><td>${esc(k.replaceAll("_", " "))}</td><td>${esc(Array.isArray(v) ? v.join(", ") : typeof v === "object" && v !== null ? JSON.stringify(v) : v)}</td></tr>`).join("")}</table>
    ${h.linea_id ? `<button class="btn btn-sm" id="hp-asi">Ver asiento y línea original</button>` : ""}
    ${h.cuenta && /^\d+$/.test(h.cuenta) ? `<a class="btn btn-sm" href="#/analisis-detalle?cuenta=${h.cuenta}${h.tercero ? `&tercero=${h.tercero}` : ""}">Navegar la cuenta</a>` : ""}
    <h3 class="sec">Explicación contable</h3><p>${esc(h.explicacion || "")}</p>
    <h3 class="sec">Recomendación</h3><p>${esc(h.recomendacion || "")}</p>
    <form id="f-rev" class="card" style="margin-top:12px"><h3 style="margin-top:0">Revisión profesional</h3>
      <div class="form-grid"><div class="campo"><label>Estado</label><select name="estado">${Object.entries(ESTADOS_H).map(([k, n]) => `<option value="${k}" ${h.estado === k ? "selected" : ""}>${n}</option>`).join("")}</select></div>
        <div class="campo"><label>Responsable asignado</label><input name="responsable" value="${esc(h.responsable || "")}"></div></div>
      <div class="campo"><label>Comentario / fundamento (obligatorio para confirmar o descartar)</label><textarea name="comentario" rows="3"></textarea></div>
      <div class="acciones"><button class="btn btn-primario">Guardar revisión</button></div></form>
    <h3 class="sec">Historial</h3>${h.comentarios.map((c) => `<div class="obs-mini"><b>${esc(c.usuario)}</b> <span class="sub">${fechaHora(c.creado_en)}</span><br>${esc(c.texto)}</div>`).join("") || '<p class="sub">Sin comentarios.</p>'}
    ${h.revisiones.map((r) => `<div class="obs-mini sub">${fechaHora(r.creado_en)} · ${esc(r.usuario)}: ${ESTADOS_H[r.estado_anterior] || r.estado_anterior} → ${ESTADOS_H[r.estado_nuevo]}</div>`).join("")}`;
  $("#hp-asi")?.addEventListener("click", () => verAsiento(h.linea_id));
  $("#f-rev").onsubmit = async (e) => {
    e.preventDefault();
    const d = datosForm(e.target);
    try { await api(`/analisis/hallazgos/${id}`, { method: "PATCH", params: { empresa_id: estado.empresaId }, body: { ...d, comentario: d.comentario || null } }); toast("Revisión registrada", "ok"); navegar(); }
    catch (err) { toast(err.message, "err"); }
  };
}

// ------------------------------------------------------------------ reglas de análisis
rutas["analisis-reglas"] = async () => {
  if (!(await inicioAnalisis())) return;
  const [lista, exc] = await vigente(Promise.all([api("/analisis/reglas", { params: { empresa_id: estado.empresaId } }), api("/analisis/excepciones", { params: { empresa_id: estado.empresaId } })]));
  const grupos = [...new Set(lista.map((r) => r.grupo))];
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Configurador de reglas de análisis</h1><p class="sub">Reglas sin modificar código: alcance por cuentas o rango, condición, operador, umbrales, riesgo y vigencia. Cada cambio crea una nueva versión, registrada en cada análisis.</p></div>
      <button class="btn btn-primario" id="rg-nueva">Nueva regla</button></div>
    ${barraContexto(`<select id="rg-grupo"><option value="">Ejecutar todas</option>${grupos.map((g) => `<option>${esc(g)}</option>`).join("")}</select><button class="btn btn-sm" id="rg-run">Ejecutar</button>`)}
    <div id="an-prog"></div>
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Código</th><th>Regla</th><th>Grupo</th><th>Alcance</th><th>Parámetros</th><th>Riesgo</th><th>Vigencia</th><th>Versión</th><th>Estado</th><th></th></tr></thead><tbody>
      ${lista.map((r) => `<tr><td><code>${esc(r.codigo)}</code></td><td><b>${esc(r.nombre)}</b><br><small class="sub">${esc(r.descripcion || "")}</small></td><td>${esc(r.grupo)}</td>
        <td>${esc(r.cuentas || "")}${r.cuenta_desde || r.cuenta_hasta ? ` ${esc(r.cuenta_desde || "")}–${esc(r.cuenta_hasta || "")}` : ""}${!r.cuentas && !r.cuenta_desde ? "Todas" : ""}</td>
        <td><small>${r.tipo === "UMBRAL" ? `${esc(r.condicion)} ${esc(r.operador)} ${esc(r.valor)}${r.valor2 ? ` y ${esc(r.valor2)}` : ""}` : r.valor !== null ? `valor ${Number(r.valor)}` : ""}${Number(r.importe_minimo) ? ` · mín. ${num(r.importe_minimo)}` : ""}${Number(r.tolerancia_pct) ? ` · tol. ${Number(r.tolerancia_pct)} %` : ""}</small></td>
        <td>${badgeRiesgo(r.riesgo)}</td><td class="nowrap">${fecha(r.vigente_desde)} – ${fecha(r.vigente_hasta)}</td><td>v${r.version}</td><td>${r.activa ? '<span class="badge b-ok">Activa</span>' : '<span class="badge">Inactiva</span>'}</td>
        <td><div class="acc-col"><button class="btn btn-sm" data-ed="${r.id}">Editar</button><button class="btn btn-sm" data-solo="${esc(r.codigo)}">Ejecutar sola</button></div></td></tr>`).join("")}</tbody></table></div>
    <div class="card" style="margin-top:16px"><div class="cab-vista" style="margin-bottom:8px"><h2 style="margin:0">Excepciones autorizadas</h2><button class="btn btn-sm btn-primario" id="ex-nueva">Nueva excepción</button></div>
      <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Regla</th><th>Cuenta</th><th>Tercero</th><th>Documento</th><th>Motivo</th><th>Autorizado por</th><th>Vigente hasta</th><th>Estado</th><th></th></tr></thead><tbody>
        ${exc.map((x) => `<tr><td>${esc(lista.find((r) => r.id === x.regla_id)?.codigo || "Todas")}</td><td>${esc(x.cuenta || "")}</td><td>${esc(x.tercero || "")}</td><td>${esc(x.documento || "")}</td><td>${esc(x.motivo)}</td><td>${esc(x.autorizado_por)}</td><td>${fecha(x.vigente_hasta)}</td><td>${x.activa ? "Activa" : "Revocada"}</td>
          <td>${x.activa ? `<button class="btn btn-sm btn-peligro" data-rev="${x.id}">Revocar</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="9" class="vacio">Sin excepciones</td></tr>'}</tbody></table></div></div>`;
  enlazarContexto(navegar);
  $("#rg-run").onclick = () => lanzarAnalisis($("#rg-grupo").value ? { grupo: $("#rg-grupo").value } : {});
  $$("[data-solo]").forEach((b) => b.addEventListener("click", () => lanzarAnalisis({ reglas: [b.dataset.solo] })));
  $("#rg-nueva").onclick = () => formRegla(null);
  $$("[data-ed]").forEach((b) => b.addEventListener("click", () => formRegla(lista.find((r) => r.id === Number(b.dataset.ed)))));
  $$("[data-rev]").forEach((b) => b.addEventListener("click", async () => { await api(`/analisis/excepciones/${b.dataset.rev}`, { method: "DELETE", params: { empresa_id: estado.empresaId } }); navegar(); }));
  $("#ex-nueva").onclick = () => {
    const c = abrirModal("Nueva excepción autorizada", `<form id="f-ex"><div class="form-grid">
      <div class="campo"><label>Regla</label><select name="regla_id"><option value="">Todas las reglas</option>${lista.map((r) => `<option value="${r.id}">${esc(r.codigo)} · ${esc(r.nombre)}</option>`).join("")}</select></div>
      <div class="campo"><label>Cuenta (prefijo)</label><input name="cuenta"></div><div class="campo"><label>Tercero</label><input name="tercero"></div>
      <div class="campo"><label>Documento</label><input name="documento"></div><div class="campo"><label>Vigente hasta</label><input type="date" name="vigente_hasta"></div>
      <div class="campo" style="grid-column:1/-1"><label>Motivo de la autorización</label><input name="motivo" required minlength="10"></div></div>
      <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-primario">Autorizar</button></div></form>`);
    $("#f-ex", c).onsubmit = async (e) => {
      e.preventDefault(); const d = datosForm(e.target); d.regla_id = d.regla_id ? Number(d.regla_id) : null; if (!d.vigente_hasta) d.vigente_hasta = null;
      try { await api("/analisis/excepciones", { method: "POST", params: { empresa_id: estado.empresaId }, body: d }); cerrarModal(); toast("Excepción registrada", "ok"); navegar(); } catch (err) { toast(err.message, "err"); }
    };
  };
};

function formRegla(r) {
  const tipos = ctxA.cat.tipos_regla;
  const c = abrirModal(r ? `Editar regla ${r.codigo} (v${r.version} → v${r.version + 1})` : "Nueva regla", `<form id="f-rg"><div class="form-grid">
    <div class="campo"><label>Código</label><input name="codigo" required pattern="[A-Z0-9\\-]+" value="${esc(r?.codigo)}" ${r ? "readonly" : ""}></div>
    <div class="campo"><label>Tipo</label><select name="tipo">${tipos.map((t) => `<option value="${t.tipo}" ${r?.tipo === t.tipo ? "selected" : ""}>${esc(t.nombre)}</option>`).join("")}</select></div>
    <div class="campo" style="grid-column:span 2"><label>Nombre</label><input name="nombre" required value="${esc(r?.nombre)}"></div>
    <div class="campo" style="grid-column:1/-1"><label>Descripción</label><input name="descripcion" value="${esc(r?.descripcion)}"></div>
    <div class="campo"><label>Grupo</label><input name="grupo" value="${esc(r?.grupo || "PROPIAS")}"></div>
    <div class="campo"><label>Cuentas (prefijos)</label><input name="cuentas" value="${esc(r?.cuentas)}"></div>
    <div class="campo"><label>Rango desde</label><input name="cuenta_desde" value="${esc(r?.cuenta_desde)}"></div>
    <div class="campo"><label>Rango hasta</label><input name="cuenta_hasta" value="${esc(r?.cuenta_hasta)}"></div>
    <div class="campo"><label>Condición (umbral)</label><select name="condicion"><option value=""></option>${ctxA.cat.condiciones.map((x) => `<option ${r?.condicion === x ? "selected" : ""}>${x}</option>`).join("")}</select></div>
    <div class="campo"><label>Operador</label><select name="operador"><option value=""></option>${ctxA.cat.operadores.map((x) => `<option ${r?.operador === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div>
    <div class="campo"><label>Valor</label><input name="valor" type="number" step="any" value="${r?.valor ?? ""}"></div>
    <div class="campo"><label>Valor 2 (entre)</label><input name="valor2" type="number" step="any" value="${r?.valor2 ?? ""}"></div>
    <div class="campo"><label>Importe mínimo</label><input name="importe_minimo" type="number" step="0.01" min="0" value="${r?.importe_minimo ?? 0}"></div>
    <div class="campo"><label>Tolerancia %</label><input name="tolerancia_pct" type="number" step="0.01" min="0" value="${r?.tolerancia_pct ?? 0}"></div>
    <div class="campo"><label>Riesgo</label><select name="riesgo">${Object.entries(NOMBRES_RIESGO).map(([k, n]) => `<option value="${k}" ${r?.riesgo === k ? "selected" : ""}>${n}</option>`).join("")}</select></div>
    <div class="campo"><label>Vigente desde</label><input type="date" name="vigente_desde" value="${esc(r?.vigente_desde || "")}"></div>
    <div class="campo"><label>Vigente hasta</label><input type="date" name="vigente_hasta" value="${esc(r?.vigente_hasta || "")}"></div>
    <label class="check"><input type="checkbox" name="activa" ${!r || r.activa ? "checked" : ""}> Activa</label>
    <div class="campo" style="grid-column:1/-1"><label>Parámetros adicionales (JSON)</label><textarea name="parametros" rows="2">${esc(r?.parametros ? JSON.stringify(r.parametros) : "")}</textarea></div></div>
    <p class="sub" id="rg-ayuda"></p>
    <div class="acciones"><button type="button" class="btn" data-cerrar>Cancelar</button><button class="btn btn-primario">Guardar</button></div></form>`);
  const ayuda = () => { const t = tipos.find((x) => x.tipo === $("[name=tipo]", c).value); $("#rg-ayuda", c).textContent = `${t.descripcion} ${t.explicacion}`; };
  $("[name=tipo]", c).onchange = ayuda; ayuda();
  $("#f-rg", c).onsubmit = async (e) => {
    e.preventDefault();
    const d = datosForm(e.target);
    ["valor", "valor2", "vigente_desde", "vigente_hasta", "condicion", "operador", "cuenta_desde", "cuenta_hasta", "cuentas", "descripcion"].forEach((k) => { if (d[k] === "") d[k] = null; });
    try { d.parametros = d.parametros ? JSON.parse(d.parametros) : null; } catch { toast("Los parámetros no son un JSON válido", "err"); return; }
    try { await api(r ? `/analisis/reglas/${r.id}` : "/analisis/reglas", { method: r ? "PUT" : "POST", params: { empresa_id: estado.empresaId }, body: d }); cerrarModal(); toast("Regla guardada", "ok"); navegar(); }
    catch (err) { toast(err.message, "err"); }
  };
}

// ------------------------------------------------------------------ papeles de trabajo
rutas["analisis-papeles"] = async () => {
  if (!(await inicioAnalisis())) return;
  const lista = await vigente(api("/analisis/papeles", { params: { empresa_id: estado.empresaId, ejercicio: ctxA.ejercicio } }));
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Papeles de trabajo preliminares</h1><p class="sub">Hojas de análisis por cuenta. Los anexos conciliados definitivos se generan en la fase 5.</p></div>
      <form id="f-np" class="filtros"><input name="cuenta" placeholder="Cuenta (p. ej. 1212)" pattern="\\d+" required><button class="btn btn-primario">Generar</button></form></div>
    ${barraContexto()}
    <div class="tabla-wrap"><table class="tabla"><thead><tr><th>Cuenta</th><th>Periodo</th><th class="num">Saldo inicial</th><th class="num">Debe</th><th class="num">Haber</th><th class="num">Saldo final</th><th>Observaciones</th><th>Responsable</th><th>Estado</th><th></th></tr></thead><tbody>
      ${lista.map((p) => `<tr><td><b>${esc(p.cuenta)}</b> ${esc(p.descripcion || "")}</td><td>${p.ejercicio} ${per2(p.periodo_desde)}–${per2(p.periodo_hasta)}</td><td class="num">${saldoDA(p.saldo_inicial)}</td><td class="num">${num(p.debe)}</td><td class="num">${num(p.haber)}</td><td class="num">${saldoDA(p.saldo_final)}</td>
        <td>${p.hallazgos.length}</td><td>${esc(p.responsable || "")}</td><td><span class="badge estado-${p.estado}">${ESTADOS_P[p.estado]}</span></td><td><a class="btn btn-sm" href="#/analisis-papel?id=${p.id}">Abrir</a></td></tr>`).join("") || '<tr><td colspan="10" class="vacio">Sin papeles de trabajo. Genérelos desde aquí o desde el explorador de cuentas.</td></tr>'}</tbody></table></div>`;
  enlazarContexto(navegar);
  $("#f-np").onsubmit = async (e) => {
    e.preventDefault();
    try { const r = await api("/analisis/papeles", { method: "POST", params: { empresa_id: estado.empresaId }, body: { ejercicio: ctxA.ejercicio, desde: ctxA.desde, hasta: ctxA.hasta, cuenta: datosForm(e.target).cuenta } }); location.hash = `#/analisis-papel?id=${r.id}`; }
    catch (err) { toast(err.message, "err"); }
  };
};

const ETIQUETAS_COMP = { tercero: "Tercero", razon_social: "Razón social", si: "Saldo inicial", saldo_inicial: "Saldo inicial", debe: "Debe", haber: "Haber",
  saldo_final: "Saldo final", movimientos: "Movs.", documentos: "Docs.", cuenta: "Cuenta", descripcion: "Descripción" };
rutas["analisis-papel"] = async () => {
  if (!(await inicioAnalisis())) return;
  const id = Number(parametrosHash().id);
  const p = await vigente(api(`/analisis/papeles/${id}`, { params: { empresa_id: estado.empresaId } }));
  const bloqueado = p.estado === "APROBADO";
  const comp = p.composicion || { items: [] };
  const claves = comp.items.length ? Object.keys(comp.items[0]) : [];
  const esImporte = (k) => ["si", "debe", "haber", "saldo_final", "saldo_inicial"].includes(k);
  vista().innerHTML = `
    <div class="cab-vista"><div><h1>Papel de trabajo · ${esc(p.cuenta)} ${esc(p.descripcion || "")}</h1><p class="sub">${p.ejercicio} · ${per2(p.periodo_desde)}–${per2(p.periodo_hasta)} · versión ${p.version} · análisis #${p.run_id ?? "—"} · <span class="badge estado-${p.estado}">${ESTADOS_P[p.estado]}</span></p></div>
      <span>${botonesExport("papel", { papel_id: p.id })} <a class="btn" href="#/analisis-papeles">Volver</a></span></div>
    <div class="alerta alerta-info">Documento PRELIMINAR. Las observaciones automáticas requieren revisión profesional; la conclusión es del analista.</div>
    <div class="grid grid-4"><div class="kpi"><div class="l">Saldo inicial</div><div class="v">${saldoDA(p.saldo_inicial)}</div></div><div class="kpi"><div class="l">Debe</div><div class="v">${num(p.debe)}</div></div>
      <div class="kpi"><div class="l">Haber</div><div class="v">${num(p.haber)}</div></div><div class="kpi"><div class="l">Saldo final</div><div class="v">${saldoDA(p.saldo_final)}</div></div></div>
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card"><h2>Composición preliminar · ${esc(comp.criterio || "")}</h2><p class="sub">${esc(comp.nota || "")}</p>
        <div class="tabla-wrap tabla-alta"><table class="tabla"><thead><tr>${claves.map((k) => `<th class="${esImporte(k) ? "num" : ""}">${esc(ETIQUETAS_COMP[k] || k.replaceAll("_", " "))}</th>`).join("")}</tr></thead><tbody>
          ${comp.items.map((x) => `<tr>${claves.map((k) => `<td class="${esImporte(k) ? "num" : ""}">${esImporte(k) ? num(x[k]) : esc(x[k] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
        <h2 style="margin-top:16px">Observaciones vinculadas (${p.hallazgos.length})</h2>
        ${p.hallazgos.map((h) => `<div class="obs-mini">${badgeRiesgo(h.riesgo)} <code>${esc(h.codigo)}</code> <a href="#/analisis-hallazgos?id=${h.id}">${esc(h.titulo)}</a> · ${num(h.importe)} · ${ESTADOS_H[h.estado]}</div>`).join("") || '<p class="sub">Sin observaciones.</p>'}</div>
      <div class="card"><form id="f-pt">
        <div class="campo"><label>Comentarios del analista</label><textarea name="comentarios_analista" rows="4" ${bloqueado ? "disabled" : ""}>${esc(p.comentarios_analista || "")}</textarea></div>
        <div class="campo"><label>Documentos de sustento (referencias)</label><textarea name="documentos_sustento" rows="2" ${bloqueado ? "disabled" : ""}>${esc(p.documentos_sustento || "")}</textarea></div>
        <div class="campo"><label>Conclusión</label><textarea name="conclusion" rows="3" ${bloqueado ? "disabled" : ""}>${esc(p.conclusion || "")}</textarea></div>
        <div class="form-grid"><div class="campo"><label>Responsable</label><input name="responsable" value="${esc(p.responsable || "")}" ${bloqueado ? "disabled" : ""}></div>
          <div class="campo"><label>Fecha de revisión</label><input type="date" name="fecha_revision" value="${esc(p.fecha_revision || "")}" ${bloqueado ? "disabled" : ""}></div></div>
        ${bloqueado ? "" : `<div class="acciones"><button class="btn btn-primario">Guardar</button><button type="button" class="btn" id="pt-act">Actualizar saldos</button></div>`}</form>
        <h3 class="sec">Adjuntos de sustento</h3>
        ${p.adjuntos.map((a) => `<div class="obs-mini"><a href="/api/analisis/papeles/${p.id}/adjuntos/${a.id}?empresa_id=${estado.empresaId}">${esc(a.nombre)}</a> <span class="sub">${(a.tamano / 1024).toFixed(1)} KB · ${esc(a.usuario)} · SHA-256 ${esc(a.hash.slice(0, 10))}…</span></div>`).join("") || '<p class="sub">Sin adjuntos.</p>'}
        ${bloqueado ? "" : `<input type="file" id="pt-file">`}
        <h3 class="sec">Estado</h3>
        <div class="acciones" style="justify-content:flex-start">${p.transiciones.map((t) => `<button class="btn btn-sm" data-est="${t}">${ESTADOS_P[t]}</button>`).join("")}</div>
        ${p.revisiones.map((r) => `<div class="obs-mini sub">${fechaHora(r.fecha)} · ${esc(r.usuario)}: ${ESTADOS_P[r.de]} → ${ESTADOS_P[r.a]}${r.comentario ? ` — ${esc(r.comentario)}` : ""}</div>`).join("")}
      </div></div>`;
  $("#f-pt")?.addEventListener("submit", async (e) => {
    e.preventDefault(); const d = datosForm(e.target); if (!d.fecha_revision) d.fecha_revision = null;
    try { await api(`/analisis/papeles/${id}`, { method: "PUT", params: { empresa_id: estado.empresaId }, body: d }); toast("Papel guardado", "ok"); navegar(); } catch (err) { toast(err.message, "err"); }
  });
  $("#pt-act")?.addEventListener("click", async () => {
    try { await api("/analisis/papeles", { method: "POST", params: { empresa_id: estado.empresaId }, body: { ejercicio: p.ejercicio, desde: p.periodo_desde, hasta: p.periodo_hasta, cuenta: p.cuenta } }); toast("Saldos actualizados (nueva versión)", "ok"); navegar(); } catch (err) { toast(err.message, "err"); }
  });
  $("#pt-file")?.addEventListener("change", async (e) => {
    const f = new FormData(); f.append("archivo", e.target.files[0]);
    try { await api(`/analisis/papeles/${id}/adjuntos`, { method: "POST", params: { empresa_id: estado.empresaId }, form: f }); toast("Adjunto guardado", "ok"); navegar(); } catch (err) { toast(err.message, "err"); }
  });
  $$("[data-est]").forEach((b) => b.addEventListener("click", async () => {
    const comentario = p.estado === "APROBADO" || ["OBSERVADO"].includes(b.dataset.est) ? prompt("Comentario (motivo):") : null;
    try { await api(`/analisis/papeles/${id}/estado`, { method: "POST", params: { empresa_id: estado.empresaId }, body: { estado: b.dataset.est, comentario } }); toast("Estado actualizado", "ok"); navegar(); } catch (err) { toast(err.message, "err"); }
  }));
};
