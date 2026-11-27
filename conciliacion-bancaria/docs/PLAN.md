# Plan de desarrollo — Analizador Contable Inteligente

> El proyecto nació como sistema de conciliación bancaria (fase 1), se amplió en la fase 2 con el
> motor de importación y validación contable y en la fase 3 con el motor de análisis de cuentas.
> En la fase 4 se incorporó el motor de compensación analítica de partidas y en la fase 5 el generador de
> anexos contables. Las conciliaciones externas quedan para la fase 6.

Contexto normativo: Plan Contable General Empresarial (PCGE) — cuenta 10
*Efectivo y equivalentes de efectivo* (104 Cuentas corrientes en instituciones
financieras), ITF (Ley 28194, tasa vigente 0.005 %), libros electrónicos
PLE/SIRE (Libro Caja y Bancos 1.2, Libro Mayor 6.1).

## Arquitectura

```
conciliacion-bancaria/
├── app/
│   ├── core/          configuración, base de datos, auditoría, utilidades (RUC)
│   ├── models/        entidades ORM (SQLAlchemy 2)
│   ├── schemas/       contratos de la API (Pydantic v2)
│   ├── importers/     lectura de Excel/CSV/PDF, normalización, mapeo de columnas
│   ├── services/      lógica de negocio (importación, duplicados, catálogo)
│   ├── contable/      (fase 2) importación, homologación y validación contable
│   ├── analisis/      (fase 3) saldos, navegación, antigüedad, comparativos, origen-destino, reglas, papeles
│   ├── compensacion/  (fase 4) partidas abiertas, clasificación, motor de coincidencias, servicio, consultas
│   ├── anexos/        (fase 5) catálogo, datos, constructores, generador, flujo, expresiones, render, exportar
│   ├── api/           routers REST (FastAPI)
│   └── static/        interfaz web (SPA sin build)
├── tests/             pruebas automatizadas (pytest)
├── scripts/           generación de datos de ejemplo, utilidades
└── ejemplos/          estados de cuenta y libros de prueba
```

Principios: capas separadas (API → servicios → modelos), importes en
`Decimal`/`NUMERIC(18,2)` (nunca `float`), toda modificación queda en la
bitácora de auditoría, nada se borra físicamente (se anula), el motor sugiere
pero **una coincidencia ambigua nunca se confirma sola**.

Convención de signos: positivo = entra dinero a la cuenta (abono en el banco /
debe en la cuenta 10); negativo = sale (cargo en el banco / haber en la 10).

---

## Fase 1 — Fundamentos, datos maestros e importación ✅ (esta entrega)

- Modelo de datos persistente: empresas (RUC validado), bancos, monedas,
  cuentas bancarias (vinculadas a su subcuenta contable 10x), configuración de
  tolerancias por cuenta, lotes de importación, movimientos de banco y de
  libro, bitácora de auditoría.
- Importación de estados de cuenta en **CSV, Excel (.xlsx) y PDF**
  (tablas con pdfplumber + lectura por líneas de texto como respaldo).
- Importación del **libro mayor de la cuenta 10** (Excel/CSV), con filtro por
  subcuenta.
- Detección automática de la fila de encabezados y de columnas (sinónimos de
  los formatos usuales de BCP, BBVA, Interbank, Scotiabank, BanBif, BN) con
  posibilidad de corregir el mapeo en la vista previa.
- Normalización: fechas (dd/mm/aaaa, serial Excel, «15-ENE»), importes
  (S/ 1,234.56 · 1.234,56 · (500.00) · 500.00- · CR/DB), cargo/abono,
  debe/haber.
- Validaciones: moneda del archivo vs. moneda de la cuenta, **continuidad de
  saldos** (saldo anterior + movimiento = saldo), rango de fechas.
- **Duplicados**: archivo ya importado (hash), filas repetidas dentro del
  archivo y movimientos ya existentes de importaciones previas solapadas.
  Se marcan (o se omiten, a elección) y se resuelven manualmente.
- Clasificación preliminar de movimientos bancarios (ITF, comisión, interés,
  transferencia, depósito, cheque…) para preparar la fase 3.
- Flujo vista previa → confirmación, historial de importaciones con anulación.
- Interfaz web profesional: panel, empresas, cuentas, importación asistida,
  consulta de movimientos, historial y auditoría.
- Pruebas automatizadas y datos de ejemplo.

## Fase 2 — Motor de importación y validación contable ✅

- Migraciones con Alembic (línea base 0001 = esquema de la fase 1; las bases existentes se
  adoptan sin perder datos) y 12 tablas nuevas (0002).
- 13 tipos de información: libro diario, libro mayor, balance de comprobación, registros de
  compras y ventas, plan de cuentas, clientes, proveedores, centros de costo, saldos
  iniciales, tipos de cambio, cuentas por cobrar y por pagar.
- Formatos XLSX, XLS, CSV y TXT estructurado (delimitado, con o sin encabezado, estilo PLE).
- Asistente de 7 pasos con arrastrar y soltar, progreso real de carga y de procesamiento,
  selección de hoja y fila de encabezado (incluso encabezados en dos filas), detección de
  filas vacías y de subtotales/totales, separador decimal y formato de fecha configurables.
- Motor de homologación con sinónimos de SAP, Starsoft, Proficont, CONCAR y genéricos,
  nivel de confianza por campo y plantillas reutilizables por empresa · sistema · tipo.
- Modelo normalizado del diario con los 34 campos requeridos (MN/ME, TC, centro de costo,
  proyecto, activo, OC/OS, detracción, retención, trazabilidad a archivo/hoja/fila).
- Motor de validación con 50+ reglas clasificadas (crítico/alto/medio/informativo), incluidas
  las de clases 6, 7 y 9 configurables por empresa. Ver `docs/VALIDACIONES.md`.
- Lotes con anulación/reemplazo, exportación de observaciones a CSV y auditoría.

## Fase 3 — Motor inteligente de análisis de cuentas ✅

- Migración 0003: 14 tablas (`account_analysis_runs`, `account_balance_snapshots`,
  `account_analysis_results`, `account_analysis_rules`, `account_analysis_findings`,
  `account_analysis_exceptions`, `account_analysis_comments`, `account_analysis_reviews`,
  `account_analysis_attachments`, `destination_mapping_rules`, `destination_analysis_results`,
  `aging_configurations`, `accounting_workpapers`, `analysis_audit_logs`) y `unidad_negocio` en
  centros de costo. Los movimientos originales no se duplican ni se modifican.
- Explorador jerárquico PCGE (elemento → analítica) con saldos, naturaleza, terceros, variación,
  observaciones y cuadre exacto con el origen; perfiles de análisis por elemento (0–9).
- Navegación en 7 niveles hasta el asiento con contrapartidas y la fila original del archivo.
- Origen–destino (6 / 79 / 9 / 78) con reglas de distribución por cuenta, CC, proyecto, unidad,
  maquinaria, porcentaje y vigencia.
- Antigüedad configurable (emisión / vencimiento, libros / cartera) con resultados preliminares.
- Comparativos por periodo y dimensión; 21 reglas configurables y versionadas + reglas de umbral;
  excepciones; revisión profesional con arrastre entre ejecuciones; dashboard; papeles de trabajo
  preliminares con flujo de aprobación; exportación Excel/PDF; procesamiento asíncrono cancelable
  con caché invalidable y tiempos por etapa (100 000+ movimientos en segundos).

## Fase 4 — Motor inteligente de compensación automática de partidas ✅

Detalle y manual en [`MANUAL_COMPENSACION.md`](MANUAL_COMPENSACION.md).

- Migración 0004: 15 tablas (`open_items`, `open_item_sources`, `settlement_runs`,
  `settlement_rules`, `settlement_candidates`, `settlement_groups`, `settlement_allocations`,
  `settlement_approvals`, `settlement_reversals`, `settlement_exceptions`, `settlement_comments`,
  `settlement_attachments`, `settlement_balance_snapshots`, `settlement_audit_logs`,
  `roles_usuario`). Los asientos originales no se modifican.
- Partidas abiertas idempotentes desde el diario (o mayor), apertura documental o «pendiente de
  desagregación», clasificación en 20 clases con confianza y motivo.
- Motor de 5 niveles (documento, referencias, importe/combinaciones acotadas, fecha solo como
  puntuación, FIFO solo autorizado) con puntuación 0–100 y casos ambiguos para decisión humana.
- Modalidades 1:1, 1:N, N:1, N:N, parciales, entre ejercicios y manuales; entre cuentas o entre
  monedas solo con regla autorizada; entre terceros solo manual con autorización y sustento.
- Detracciones, retenciones y percepciones con tasas y vigencias configurables; notas de crédito;
  anticipos; moneda extranjera evaluada en la moneda de la obligación con diferencia de cambio
  identificada (sin asiento).
- Integridad: CHECK, índice único parcial, UPDATE condicional con versión, transacciones, rechazo de
  ejecuciones concurrentes; aprobación con separación de funciones; reversión sin borrado; roles.
- Composición histórica a cualquier fecha de corte, fotografías por ejecución, conciliación con el
  saldo contable sin ajustes, antigüedad real integrada a la fase 3 (fuente `COMPENSACION`),
  dashboard CxC/CxP y 14 reportes Excel/PDF.
- 180 000 líneas (90 000 partidas) compensadas en ≈ 49 s.

Pendiente para una fase posterior (requiere autorización): asientos automáticos de regularización
y conciliación por reglas de los movimientos bancarios de la fase 1 contra el libro.

## Fase 5 — Generador inteligente de anexos contables ✅

Detalle y manual en [`MANUAL_ANEXOS.md`](MANUAL_ANEXOS.md).

- Migración 0005: 19 tablas (`annex_templates`, `annex_template_columns`, `annex_template_rules`,
  `annex_template_formulas`, `annex_generation_runs`, `accounting_annexes`, `accounting_annex_details`,
  `annex_reconciliations`, `annex_findings`, `annex_versions`, `annex_reviews`, `annex_approvals`,
  `annex_comments`, `annex_attachments`, `annex_assignments`, `annex_export_jobs`, `annex_audit_logs`,
  `annex_support_records`, `annex_settings`).
- Catálogo de 73 plantillas para los elementos 0–9 con 19 constructores especializados y uno genérico;
  diseñador de plantillas con motor seguro de expresiones.
- Conciliación de cada anexo con el libro (y el balance importado) con cinco resultados; cuadre
  matemático y sustento documental separados; diferencias explícitas sin ajustes.
- Generación individual, seleccionada, por elemento, rango o balance completo; asíncrona, cancelable,
  idempotente; versiones inmutables al aprobar; comparación histórica.
- Flujo de revisión de 10 estados con separación de funciones; documentación sustentatoria;
  permisos por empresa, rol y cuenta; datos personales protegidos; auditoría.
- Exportación Excel (fórmulas verificables, libro masivo con índice) y PDF (expediente de cierre).
- 1 200 cuentas / 100 000 líneas: generación masiva ≈ 20 s.

## Fase 6 — Motor inteligente de conciliaciones contables automáticas ✅

Detalle y manual en [`MANUAL_CONCILIACIONES.md`](MANUAL_CONCILIACIONES.md).

- Migración 0006: 19 tablas (`reconciliation_types`, `reconciliation_templates`, `reconciliation_sources`,
  `reconciliation_source_records`, `reconciliation_column_mappings`, `reconciliation_rules`,
  `reconciliation_tolerances`, `reconciliation_runs`, `reconciliation_matches`, `reconciliation_match_groups`,
  `reconciliation_allocations`, `reconciliation_differences`, `reconciliation_reviews`, `reconciliation_approvals`,
  `reconciliation_reversals`, `reconciliation_attachments`, `reconciliation_assignments`, `reconciliation_versions`,
  `reconciliation_audit_logs`), roles TESORERO y PLANILLAS y referencia de NC/ND en los registros de compras y ventas.
- Motor universal (2 a 4 fuentes, comparaciones por partidas o agregadas, signo igual u opuesto): reglas por clave,
  importe y fecha (índice con búsqueda binaria), combinaciones acotadas (1:N, N:1), agregados, exclusiones y
  clasificaciones con el motor seguro de expresiones de la fase 5; duplicados por fuente; ambiguas nunca automáticas.
- 15 tipos de conciliación con plantilla: bancaria, compras, ventas, planillas, activos fijos, inventarios, servicios
  y costos en proceso, obligaciones financieras, detracciones, retenciones y percepciones, tributos y aportes,
  intercompañía, origen–destino, auxiliares vs mayor y personalizada (diseñador de 10 pasos).
- 11 clasificaciones de diferencias y 5 prioridades; tolerancias por empresa, tipo, cuenta y moneda; continuidad
  mensual de incidencias (traslado sin duplicar, subsanación automática de lo que ya no se reproduce).
- Conciliación manual (panel dual, parciales), confirmación, rechazo y reversión de coincidencias; flujo
  Ejecutada → En revisión → Revisada → Aprobada → Cerrada con separación de funciones, versiones inmutables y
  reapertura autorizada; historial a una fecha.
- Exportación Excel (8 hojas + reporte especializado con fórmulas) y PDF; reportes globales.
- 109 000 registros: conciliación ≈ 12 s.

## Fase 7 — Auditor contable inteligente 360 ✅

Detalle y manual en [`MANUAL_AUDITORIA.md`](MANUAL_AUDITORIA.md).

- Migración 0007: 23 tablas `audit_*` (encargos, alcance, categorías, reglas y versiones, ejecuciones y resultados por
  regla, hallazgos, evidencias, grupos, matriz de riesgos, materialidad, muestras y elementos, papeles de trabajo,
  planes de acción, asignaciones, revisiones, aprobaciones, informes y versiones, bitácora inmutable encadenada,
  configuraciones del ERP), columnas opcionales de registro del ERP en `lineas_diario` y roles AUDITOR_EXTERNO y GERENCIA.
- 167 reglas en 18 categorías que reutilizan las fases 2–6 (contexto de análisis, partidas abiertas, registros
  auxiliares, conciliaciones en memoria o guardadas); reglas configurables sin código con vista previa.
- Riesgo 5×5, materialidad aprobada, hallazgos con huella única, grupos de exposición, reincidencias, 11 estados con
  separación de funciones, planes de acción y bandeja de regularización (sin asientos).
- Reglas tributarias normativas validables (no se ejecutan sin validación; sin datos → pendiente de evaluación).
- Muestras reproducibles, papeles de trabajo, 6 informes de 16 secciones y 12 exportaciones Excel/PDF.
- Volumen real: 100 000 / 500 000 / 1 000 000 movimientos en 19,8 / 107,5 / 214,2 s; incremental < 0,5 s.

## Fase 8 — Asientos de regularización (pendiente de autorización)

- Propuestas de asiento a partir de la bandeja de regularización de la auditoría (fase 7), de las incidencias
  «pendientes de regularización» (fase 6) y de las
  compensaciones (fase 4), siempre sujetas a aprobación.

## Fases posteriores

- Autenticación real, usuarios y permisos (hoy el usuario se toma de la cabecera `X-Usuario`).
- PostgreSQL en producción, respaldos, cola de trabajos para varios nodos, Docker.
- Integración SIRE/SUNAT (fase 12) sobre los registros de compras y ventas ya conciliados.
