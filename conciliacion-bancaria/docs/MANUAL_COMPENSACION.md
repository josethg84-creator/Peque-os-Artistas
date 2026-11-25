# Fase 4 — Compensación automática de partidas contables

Manual de usuario y descripción técnica del motor de compensación de **Accounting Intelligence 360**.

## 1. Qué hace (y qué no hace)

La **compensación analítica** determina qué documentos cancelan a cuáles (factura ↔ pago, nota de
crédito, anticipo, detracción, retención…) para conocer la **composición real del saldo** de cada
cuenta por cobrar y por pagar a una fecha de corte.

- **No modifica los asientos contables originales.** Las líneas del libro diario se leen; la
  compensación se registra en tablas propias (`settlement_*`) como asignaciones trazables.
- **No es la compensación legal** de créditos y deudas recíprocos (art. 1288 del Código Civil) ni
  la presentación neta en estados financieros: es un análisis de cancelación documental.
- **No genera asientos de regularización** (diferencias de cambio, saldos menores, etc.): las
  diferencias se identifican y se muestran, pero no se contabilizan (fase posterior, no autorizada).
- **No inventa documentos.** Un saldo inicial consolidado sin detalle por documento queda como
  partida «Pendiente de desagregación».
- **No aprueba coincidencias ambiguas** ni compensa entre empresas.

## 2. Flujo de trabajo

1. Importe el libro diario (fase 2) del ejercicio de inicio y de los siguientes, y los saldos
   iniciales del ejercicio de inicio (periodo 00). Las cuentas por cobrar/pagar detalladas por
   documento (CxC/CxP, periodo 00) se usan como apertura documental si existen.
2. **Reglas y roles** → revise las cuentas compensables y sus parámetros; registre reglas de
   detracción, retención o percepción con su tasa y vigencia, y las reglas entre cuentas
   (p. ej., anticipos 4221 contra facturas 4212) con su sustento.
3. **Dashboard de compensación** → elija la fecha de corte y pulse **Ejecutar motor**. El avance es
   real (etapas y porcentaje) y la ejecución se puede cancelar. Si ni los datos ni las reglas
   cambiaron, se reutiliza la ejecución anterior (idempotencia); **Forzar** recalcula.
4. **Propuestas y aprobaciones** → revise cada propuesta (modalidad, puntuación y su desglose,
   regla, líneas de origen), apruébela, recházela o apruebe en lote. En **Ambiguas** elija la
   alternativa sustentada con una justificación.
5. **Compensación manual** → para lo que el motor no resolvió: doble panel, selección múltiple,
   importes parciales, vista previa antes/después, justificación. Queda como propuesta.
6. **Conciliación y observaciones** → verifique que las partidas abiertas explican el saldo
   contable; las diferencias se muestran tal cual. Revise las observaciones (ambiguas, saldos sin
   detalle, referencias inexistentes, clasificación por revisar, diferencias de cambio).
7. **Antigüedad y reportes** → antigüedad real (después de compensaciones aprobadas) y 14 reportes
   en Excel y PDF.

Una compensación **aprobada no se elimina**: solo se **revierte** (motivo obligatorio, rol
autorizado). La reversión libera los saldos y queda en el historial con su usuario y fecha.

## 3. Pantallas

| Pantalla | Uso |
|---|---|
| Dashboard de compensación | KPIs separados de CxC y CxP (partidas, compensadas, parciales, pendientes, vencidas, anticipos por aplicar, importes), estado de la conciliación, aprobadas por política/manuales, propuestas, revertidas, diferencias de cambio, observaciones; gráficos de antigüedad, evolución mensual, concentración por tercero, confianza, aprobadas por periodo y saldo por moneda (cada gráfico con «Ver datos») |
| Partidas abiertas | Composición del saldo a la fecha de corte con filtros (cuenta, tercero, texto, rol, moneda, estado de cancelación, de vencimiento) y paginación en el servidor. Clic → detalle con aplicaciones, líneas de origen y observaciones |
| Compensación manual | Doble panel con búsqueda, selección múltiple e importes parciales; vista previa antes/después; autorización entre terceros; tipo de cambio para compensar entre monedas |
| Propuestas y aprobaciones | Por aprobar, ambiguas, aprobadas, revertidas, rechazadas; detalle con historial, comentarios, adjuntos (sustentos), aprobar/rechazar/revertir |
| Anticipos | Anticipos de clientes, a proveedores, entregas a rendir y fondos sin aplicar, con antigüedad y documentos relacionados |
| Detracciones y retenciones | Constancias/comprobantes, documentos relacionados, estado de sustento |
| Conciliación y observaciones | Saldo contable vs partidas abiertas por cuenta y observaciones del motor con revisión |
| Antigüedad y reportes | Antigüedad real por tercero, cuenta, documento, moneda, proyecto o centro de costo; 14 reportes |
| Reglas y roles | Reglas versionadas, roles por empresa, ejecuciones y auditoría |

Estados que se muestran **por separado**:

- Cancelación: Cancelada · Parcial · Pendiente · Por aplicar · Anticipo por aplicar.
- Vencimiento: Vencido (con días) · No vencido · Sin fecha de vencimiento · No aplica.
- Revisión: propuesta, aprobada, revertida, observada.

## 4. Construcción de partidas abiertas

- Cuentas compensables por defecto: 12, 13, 14, 16, 17, 40, 41, 42, 43, 44, 45, 46, 47 (y las que el
  usuario agregue), cada una con reglas independientes.
- Una partida agrupa las líneas del mismo lote, periodo, subdiario, asiento, cuenta, tercero, tipo,
  serie, número, moneda y lado; su clave (`L{lote}:{línea mínima}`) hace la construcción
  **idempotente**. Se guardan las líneas de origen (`open_item_sources`).
- **Rol**: *documento (origen)* cuando el lado coincide con la naturaleza de la cuenta (debe en 1–3,
  haber en 4); *cancelación (aplicación)* en el lado contrario.
- **Apertura**: solo en el ejercicio de inicio (el primero con información, o el configurado). Se
  usa el detalle documental (CxC/CxP periodo 00) y el residuo de los saldos iniciales queda como
  «Saldo inicial sin detalle — pendiente de desagregación». En los ejercicios siguientes la
  apertura **no** se vuelve a sumar: la continuidad viene de los movimientos (sin duplicar).
- Se usa el diario, o el mayor del periodo si no hay diario (mismo criterio de la fase 3).
- Líneas solo en moneda nacional de una cuenta en moneda extranjera (ajustes de diferencia de
  cambio del ERP) se convierten en partidas de clase DIFERENCIA_CAMBIO en PEN.

### Clasificación (20 clases)

FACTURA, BOLETA, RECIBO_HONORARIOS, NOTA_CREDITO, NOTA_DEBITO, PAGO, COBRANZA, ANTICIPO,
ENTREGA_RENDIR, RENDICION, PRESTAMO, AMORTIZACION, DETRACCION, RETENCION, PERCEPCION,
DIFERENCIA_CAMBIO, RECLASIFICACION, EXTORNO, SALDO_INICIAL, OTRO.

Orden de evidencia: tipo de comprobante SUNAT (01, 03, 02, 07, 08, 20, 40…), subcuentas de
anticipos configuradas, palabras de la glosa, contrapartida de caja (10) y subdiarios de pago. Cada
clasificación guarda su **confianza** y **motivo**; con confianza < 60 queda **por revisar** y una
partida por revisar solo se compensa manualmente con justificación.

## 5. Algoritmo de coincidencia

Se trabaja por partición **(cuenta o regla entre cuentas, tercero, moneda)**: nunca se mezclan
terceros, monedas ni empresas automáticamente.

| Nivel | Criterio |
|---|---|
| 1 | Documento exacto: misma serie y número (pago, NC, detracción o retención que citan el documento) |
| 2 | Referencias: documento de referencia (NC/ND), orden de compra/servicio, número en la glosa, mismo asiento |
| 3 | Importe: exacto único 1:1; combinaciones N:1 y 1:N con límites (`max_combinacion`, `max_nodos`) dentro de la ventana de días; la fecha solo puntúa |
| 4 | Proximidad de fecha: solo como componente de la puntuación, nunca como criterio único |
| 5 | FIFO: solo si la cuenta lo autoriza (`fifo`) y nunca cuando la cancelación cita un documento propio |

- Si un documento/importe admite **dos o más alternativas válidas** se registra un caso **ambiguo**
  (con todas las alternativas) que requiere decisión humana; nunca se aprueba solo.
- Cancelación que cita un documento inexistente → observación REFERENCIA_INEXISTENTE.
- Nota de crédito sin referencia → observación; nota de crédito que excede el saldo → EXCEDENTE.
- La búsqueda combinatoria está acotada (nodos y candidatos) y avisa si se cortó.

### Puntuación 0–100 (calidad de la coincidencia, no probabilidad)

Pesos por defecto (configurables por cuenta): tercero 20, documento 30 (nivel 2: 20), moneda 10,
importe 15 (combinación 12, parcial 6), referencias 10, fecha 10 (≤30 días; 6 hasta 90; 3 hasta
365; anticipo previo 2), cuenta 5 (2–3 entre cuentas); ambigüedad −25.
Tramos: **≥95 muy alta · 80–94 alta · 60–79 media · <60 baja**.

### Aprobación automática

Solo si la cuenta tiene política autorizada (`autoaprobar`, umbral ≥ 95), la coincidencia no es
ambigua, no tiene bloqueos (tributo sin sustento, tasa no configurada…), no es entre cuentas ni
entre terceros y su nivel es 1–3. Todo lo demás queda como propuesta.

### Tributos

- **Detracción**: requiere constancia y una regla por código con tasa y vigencia (no se asume una
  tasa universal); se verifica importe = documento × tasa (redondeado a entero, con tolerancia).
- **Retención**: comprobante de retención (tipo 20) y tasa configurada.
- **Percepción**: siempre a revisión.
- Sin sustento o sin tasa configurada, la propuesta se marca «Requiere sustento» y no se aprueba sola.
- El pago neto más los tributos del mismo documento se puntúan como cancelación exacta.

### Moneda extranjera

La cancelación se evalúa en la **moneda de la obligación** (una factura de US$ 1 000 pagada con
US$ 1 000 queda cancelada). La diferencia en moneda nacional (TC de la factura vs TC del pago) se
registra en cada aplicación (`diferencia_cambio`) y se muestra; **no** se genera asiento.
Compensar entre monedas exige una regla de conversión y el tipo de cambio.

## 6. Controles de integridad

- Ninguna partida puede quedar sobreaplicada ni con saldo negativo: restricciones `CHECK` en la base
  y `UPDATE` condicional (control optimista con versión) dentro de una transacción.
- Índice único parcial: una misma pareja origen–aplicación no puede tener dos asignaciones vigentes
  (aplicación duplicada → 409).
- Validaciones de la compensación manual: lados contrarios, totales iguales, misma empresa, misma
  moneda (o regla de conversión), mismo tercero (o autorización con rol y sustento ≥ 20
  caracteres), cuentas iguales (o regla entre cuentas activa), ninguna partida posterior al corte.
- Ejecuciones concurrentes del motor para la misma empresa se rechazan (409).
- Separación de funciones configurable: quien propone no aprueba.
- Todo queda en `settlement_audit_logs`: ejecutar, proponer, aprobar, rechazar, revertir, resolver,
  configurar, asignar roles, exportar.

## 7. Fecha de corte y reconstrucción histórica

Una aplicación cuenta a una fecha de corte si está **aprobada** y su **fecha efectiva** (la mayor de
las fechas de sus partidas) es anterior o igual al corte. Por eso la composición al 31/12/2025 no
cambia por un pago aprobado en enero de 2026. Cada ejecución guarda además una fotografía
(`settlement_balance_snapshots`) de la composición al corte con la versión de reglas usada.

## 8. Conciliación con el saldo contable

Para cada cuenta: saldo contable (desde el libro, con la misma selección de fuentes) = documentos
pendientes + cancelaciones por aplicar + saldo inicial sin detalle + partidas por clasificar +
diferencia de cambio identificada. La **diferencia** se muestra explícitamente; no se fuerza ni se
ajusta.

## 9. Roles

| Acción | Administrador | Supervisor | Contador | Analista | Auditor | Consulta |
|---|---|---|---|---|---|---|
| Consultar y exportar | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ejecutar motor / proponer | ✓ | ✓ | ✓ | ✓ | | |
| Aprobar / rechazar | ✓ | ✓ | ✓ | | | |
| Revertir, autorizar entre terceros, configurar reglas | ✓ | ✓ | | | | |
| Revisar observaciones / comentar | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Asignar roles | ✓ | | | | | |

Sin roles asignados la empresa trabaja en **modo abierto**. Al asignar el primer rol, quien lo
asigna queda como Administrador. La identidad se toma de la cabecera `X-Usuario` hasta la fase de
autenticación.

## 10. Reportes (Excel y PDF)

Partidas abiertas · partidas compensadas · aplicaciones parciales · saldos pendientes por tercero ·
antigüedad · compensaciones propuestas · aprobadas · revertidas · anticipos pendientes ·
detracciones · retenciones · diferencias de cambio · saldos históricos a la fecha de corte ·
conciliación con el saldo contable. Cada uno indica empresa, periodo, fecha de corte, moneda,
filtros aplicados y fecha de generación.

## 11. Rendimiento (medido)

Prueba `test_mas_de_100000_movimientos`: 180 000 líneas de diario (100 000 en cuentas
compensables: 50 000 facturas, 40 000 pagos, 2 000 terceros; 90 000 partidas), SQLite, un proceso:

| Etapa | Tiempo |
|---|---|
| Construcción de partidas desde el libro | 7.7 s |
| Búsqueda de coincidencias (2 000 particiones) | 4.6 s |
| Registro de 40 000 compensaciones propuestas | 24.2 s (bloques transaccionales de 500) |
| Observaciones | 2.8 s |
| Fotografía de la composición al corte | 9.8 s |
| **Ejecución completa** | **49.2 s** (antes de optimizar el registro por bloques: 178 s) |
| Conciliación con el saldo contable | 2.7 s |
| Página de 100 partidas pendientes | 3.2 s |

## 12. Limitaciones

- La compensación entre terceros, cuentas o monedas solo es manual (o con regla autorizada).
- Las percepciones siempre requieren revisión.
- La identidad del usuario es declarativa (`X-Usuario`) hasta la fase de autenticación.
- Consultas de partidas calculan la composición en memoria: con cientos de miles de partidas una
  página tarda algunos segundos (PostgreSQL y vistas materializadas en la fase de despliegue).
- No se generan asientos de regularización ni se concilian todavía los movimientos bancarios de la
  fase 1 contra el libro por reglas.
