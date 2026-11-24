# Plan de desarrollo — Sistema de Conciliación Bancaria Inteligente

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
│   ├── engine/        (fase 2) motor de conciliación por reglas y confianza
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

## Fase 2 — Motor de conciliación por reglas y niveles de confianza

- Reglas en cascada con puntaje 0–100: n.º de operación exacto + importe
  (100), importe + fecha exacta (90), importe + fecha dentro de tolerancia
  (70–85 decreciente por días), importe dentro de tolerancia (penaliza), texto
  similar en glosa/descripción (bonificación).
- Conciliación **1 a 1, 1 a N y N a 1** (búsqueda de subconjuntos acotada por
  ventana de fechas y tamaño máximo de combinación).
- Detección de ambigüedad: si un movimiento tiene más de un candidato con
  puntaje cercano, queda como *propuesta ambigua* y exige decisión manual.
- Auto-confirmación solo por encima del umbral configurado y sin ambigüedad.
- Bandeja de propuestas: aceptar, rechazar, ver evidencias de cada regla.

## Fase 3 — Partidas no registradas y asientos de regularización

- Identificación de comisiones, ITF, intereses, portes, retenciones y abonos
  no registrados en libros; validación del ITF calculado (0.005 %).
- Propuesta de asientos: p. ej. comisiones → 6391 *Gastos bancarios* /
  104x; ITF → 6411 *Impuesto a las transacciones financieras* / 104x;
  intereses → 104x / 7721 *Intereses sobre depósitos*; diferencia de cambio →
  676 / 776. Exportación en formato importable (Excel/CSV) para el ERP.
- Depósitos en tránsito, cheques girados no cobrados, transferencias
  pendientes.

## Fase 4 — Conciliación manual, aprobaciones y períodos

- Pantalla de conciliación manual lado a lado (selección múltiple, suma en
  vivo, diferencia).
- Flujo de estados: borrador → en revisión → aprobada → cerrada, con roles
  (preparador / revisor / aprobador) y comentarios.
- Cierre mensual por cuenta; **arrastre de partidas pendientes** de meses
  anteriores con antigüedad (aging) y alertas.
- Desconciliar con motivo obligatorio y registro en auditoría.

## Fase 5 — Reportes

- Conciliación bancaria formal (saldo según banco ± partidas = saldo según
  libros) en PDF y Excel, firmas de preparó/revisó/aprobó.
- Detalle de partidas pendientes, aging, movimientos conciliados, asientos
  propuestos, indicadores por empresa/banco/moneda.

## Fase 6 — Seguridad, multiusuario y despliegue

- Autenticación, usuarios, roles y permisos por empresa.
- Migraciones con Alembic, PostgreSQL en producción, respaldos.
- Docker, configuración de entorno, endurecimiento y pruebas de carga.
- Perfiles de importación guardados por banco/cuenta (plantillas de mapeo).
