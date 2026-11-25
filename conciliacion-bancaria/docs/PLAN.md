# Plan de desarrollo — Analizador Contable Inteligente

> El proyecto nació como sistema de conciliación bancaria (fase 1), se amplió en la fase 2 con el
> motor de importación y validación contable y en la fase 3 con el motor de análisis de cuentas.
> El motor de conciliación/compensación pasó a la fase 4 y los anexos conciliados a la fase 5.

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

## Fase 4 — Motor de compensación y conciliación de partidas

- Compensación de documentos (facturas, pagos, notas de crédito, anticipos) por tercero, con
  reglas y niveles de confianza; las coincidencias ambiguas nunca se confirman solas.
- Conciliación bancaria por reglas (1 a 1, 1 a N, N a 1) sobre los movimientos de la fase 1.
- Partidas no registradas (comisiones, ITF, intereses) y propuesta de asientos de regularización.
- Conciliación manual con aprobación; arrastre de partidas pendientes entre periodos.

## Fase 5 — Anexos conciliados y reportes definitivos

- Anexos por cuenta conciliados (a partir de los papeles de trabajo aprobados), conciliación
  bancaria formal, reportes con firmas de preparó / revisó / aprobó.

## Fase 6 — Seguridad, multiusuario y despliegue

- Autenticación, usuarios, roles y permisos por empresa (hoy la seguridad multiempresa es por
  aislamiento de datos en cada consulta; el usuario se toma de la cabecera `X-Usuario`).
- PostgreSQL en producción, respaldos, cola de trabajos para varios nodos, Docker.
- Perfiles de importación de estados de cuenta guardados por banco/cuenta.
