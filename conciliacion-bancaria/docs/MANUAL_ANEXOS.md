# Fase 5 — Generador inteligente de anexos contables

Manual de usuario y descripción técnica del generador de anexos de **Accounting Intelligence 360**.

## 1. Qué es un anexo en el sistema

Un anexo es la **composición detallada del saldo de una cuenta a una fecha de corte**, conciliada con el
libro y trazable hasta la línea del asiento original. Cada anexo tiene:

- **Encabezado**: razón social, RUC, ejercicio, periodo, fecha de corte, cuenta, moneda, fecha de
  generación, versión y responsables de elaboración, revisión y aprobación.
- **Resumen contable**: saldo inicial, debe, haber, saldo final contable, saldo detallado, saldo
  sustentado, saldo pendiente de sustento y diferencia de conciliación.
- **Detalle**: fecha, tipo de documento, serie, número, RUC, razón social, glosa, moneda, tipo de
  cambio, importe original, aplicado, saldo, antigüedad, centro de costo, proyecto, referencia contable
  y observaciones, más los campos propios de cada tipo de cuenta.
- **Sección de revisión**: hallazgos, documentación, comentarios, acciones correctivas, conclusión
  del contador y estado de revisión.

Reglas que el sistema respeta siempre:

- **Nunca modifica asientos.** Solo lee el libro (fase 2), los saldos (fase 3) y las compensaciones
  aprobadas (fase 4).
- **No inventa documentos.** Lo que no tiene detalle queda como «saldo sin detalle»; lo que no tiene
  comprobante, como «pendiente de sustento».
- **No oculta diferencias** ni crea ajustes para eliminarlas.
- **Cuadrado ≠ sustentado.** El cuadre matemático y el sustento documental se miden por separado.
- **Las versiones aprobadas son inmutables** y ninguna versión se elimina.

## 2. Flujo de trabajo

1. **Importe el libro** (fase 2) y, si corresponde, ejecute y apruebe la compensación de partidas
   (fase 4): los anexos de cuentas por cobrar y por pagar usan solo compensaciones **aprobadas** con
   fecha efectiva hasta el corte.
2. **Registros auxiliares**: importe el registro de activos fijos, contratos y cronogramas
   financieros, gastos contratados por anticipado, servicios en proceso e inventario valorizado.
   Sin ellos, los anexos especializados se arman desde el libro y lo indican.
3. **Centro de anexos**: elija ejercicio, periodo y fecha de corte. El explorador jerárquico muestra
   cada cuenta con su saldo, la plantilla que le corresponde y el estado de su anexo. Genere anexos
   individuales, seleccionados, por elemento, por rango o de todo el balance. Puede filtrar por centro
   de costo, proyecto, unidad de negocio o moneda, y forzar una plantilla.
4. **Anexo** (clic en la versión): pestañas Detalle (paginación, búsqueda, columnas configurables,
   totales fijos, clic en una fila → asiento original), Conciliación, Observaciones, Documentación,
   Revisión y Versiones (comparaciones).
5. **Flujo de revisión**: Generado → En elaboración → En revisión → Observado → Subsanado → Revisado
   → Aprobado → Cerrado; Reabierto con motivo y rol autorizado.
6. **Exportaciones**: Excel o PDF de un anexo; libro Excel de todos los anexos o expediente de cierre
   en PDF (centro de exportaciones, proceso asíncrono).

## 3. Catálogo de plantillas

Para cada cuenta se usa la plantilla de **prefijo más largo**. Las plantillas de la empresa autorizadas
tienen prioridad sobre las del catálogo. Las personalizadas se eligen explícitamente.

| Elemento | Plantillas (prefijo · especialidad) | Contenido principal |
|---|---|---|
| 1 | 10, 101, 102, 104, 105, 106, 107 · EFECTIVO | Por subcuenta: entidad, número de cuenta enmascarado, moneda, saldo contable, saldo según estado bancario (fase 1) si cubre el corte, diferencia y movimientos pendientes. Sin estado bancario suficiente **no se declara conciliada** |
| 1 | 12, 13, 16, 17 · CARTERA | Por cliente y documento: emisión, vencimiento, moneda, importe original, cobranzas, notas de crédito, anticipos, detracciones y retenciones sustentadas (fase 4), saldo y días de vencimiento |
| 1 | 14, 1413 · PERSONAL | Préstamos, adelantos, entregas a rendir, accionistas: entregado, rendiciones, devoluciones, descuentos, saldo |
| 1 | 18 · DIFERIDO | Cronograma de devengo (lineal por días): contratado, inicio, término, devengado, pendiente y diferencia con el libro |
| 1 | 19 · ESTIMACION | Estimación por tercero relacionada con su cartera, cartera vencida y cobertura. No determina deterioros |
| 2 | 20, 21, 22, 24, 25, 26, 28 · EXISTENCIAS; 29 · genérica | Inventario valorizado al corte si existe; si no, detalle del libro |
| 2 | 23 · SERVICIOS_PROCESO | Por proyecto/OS: cliente, contrato, maquinaria, fechas, estados operativo / de facturación / contable separados, costos anteriores y del ejercicio (mano de obra, materiales, combustible, servicios, depreciación, indirectos), transferencias, reconocido, saldo y pendiente de evaluación |
| 3 | 31, 32, 33, 34, 35 · PPE | Por activo: costo inicial, adiciones, mejoras, transferencias, bajas, costo final, vida útil, valor residual, ubicación, centro de costo |
| 3 | 39 · DEPRECIACION | Inicial, del periodo (recalculada), ajustes, bajas, final, valor neto, depreciación tributaria y diferencia (no usa tasas tributarias como vida útil) |
| 3 | 30, 36, 37, 38 · genéricas | Inversiones, deterioro, activo diferido, otros activos |
| 4 | 40 · TRIBUTOS | Por tributo y periodo tributario: determinado, pagos, compensaciones, créditos, concepto (tributo, intereses, multa), exigibilidad. Saldos deudores se informan como no exigibles |
| 4 | 41 · REMUNERACIONES | Por trabajador y concepto (sueldos, gratificaciones, vacaciones, CTS, participaciones, liquidaciones): saldo inicial, provisiones, pagos, ajustes. Datos personales protegidos |
| 4 | 42, 43, 44, 46, 47 · CARTERA | Por proveedor y documento: pagos, notas de crédito, anticipos aplicados, detracciones, retenciones, saldo y antigüedad |
| 4 | 45 · FINANCIERAS | Por contrato: entidad, tipo, capital, amortizado, capital pendiente según cronograma, intereses y comisiones separados, cuotas vencidas, próximos vencimientos, porción corriente y no corriente, garantías |
| 4 | 48, 49 · genéricas | Provisiones y pasivo diferido |
| 5 | 50, 51, 52, 56, 57, 58, 59 · PATRIMONIO | Saldo inicial, aportes, distribuciones, capitalizaciones, reclasificaciones, ajustes, resultado del ejercicio, saldo final |
| 6 | 6, 60, 62, 63, 634, 635, 64, 651, 67, 68, 69 · GASTOS; Combustible (filtro) | Por cuenta, proveedor, tipo de gasto, centro de costo, proyecto, maquinaria, unidad, mes y documento; variaciones significativas y gastos sin sustento |
| 7 | 7, 70 · INGRESOS; 71, 72, 78 · transferencia | Ingresos, descuentos, notas de crédito, ajustes, netos; las cuentas de transferencia se separan de los ingresos económicos |
| 9 / 79 | 79, 9 · ORIGEN_DESTINO | Distribución por destino, centro de costo y proyecto con porcentaje, y validación 6 / 79 / 9 / 78 según las reglas de la fase 3 |
| 8 | 8 · CIERRE | Saldos intermediarios y cuentas de cierre |
| 0 | 0 · ORDEN | Cuentas de orden: control, no se presentan como activos ni pasivos |
| — | GEN · GENERICO | Cualquier otra cuenta: por tercero y documento, o por asiento cuando no hay documento |

### Diseñador de plantillas

Duplique una plantilla o cree una nueva (Plantillas y diseñador): seleccione, renombre y ordene
columnas; agrupe (con subtotales); defina filtros de presentación; agregue **campos calculados** y
**reglas de validación**; configure rangos de antigüedad, encabezado, orientación y logotipo; guarde,
duplique y comparta. Las plantillas personalizadas requieren autorización de un supervisor para que
otros las usen. Las del catálogo no se editan.

**Motor seguro de expresiones**: la expresión se analiza con `ast` y se evalúa recorriendo el árbol
con una lista blanca (números, textos, campos de la fila, + − × ÷, comparaciones, Y/O/NO y las
funciones `SI`, `ABS`, `REDONDEAR`, `MIN`, `MAX`, `SUMA`, `DIVIDIR`, `DIAS`, `COALESCE`, `CONTIENE`,
`MAYUS`, `ES_VACIO`). No hay `eval`, acceso a atributos, importaciones, comprensiones ni SQL.
Ejemplos: `SI(dias > 90, saldo, 0)`, `REDONDEAR(saldo * 0.18, 2)`, `CONTIENE(glosa, "COMBUST")`.

Los filtros de plantilla son de presentación: la conciliación siempre usa el detalle completo.

## 4. Conciliación de cada anexo

`Saldo final contable = saldo inicial + debe − haber`, expresado con el **signo natural** de la cuenta
(positivo en su lado normal: deudor para activos y gastos; acreedor para pasivos, patrimonio e
ingresos). Se compara con el detalle clasificado en: sustentado (con documento), sin documento,
saldos iniciales sin detalle y partidas por clasificar; y, si se importó, con el balance de
comprobación.

| Resultado | Condición |
|---|---|
| Cuadrado | Detalle = saldo contable, todo sustentado, sin observaciones abiertas |
| Cuadrado con observaciones | Igual, con observaciones abiertas |
| Parcialmente sustentado | Detalle = saldo contable, pero hay partidas sin sustento (valor absoluto ≠ 0) |
| Descuadrado | Detalle ≠ saldo contable (la diferencia se muestra, sin ajustes) |
| Información insuficiente | No hay información para construir el anexo |

Las diferencias de cambio identificadas en aplicaciones aprobadas (fase 4) aparecen como partidas por
clasificar hasta su regularización; no se generan asientos.

## 5. Generación masiva

1) cuentas con saldo, 2) con movimientos, 3) plantilla por cuenta, 4) movimientos y compensaciones,
5) saldos, 6) detalle, 7) reglas, 8) observaciones, 9) conciliación con el balance, 10) versión.
Por balance completo, elemento, rango o cuentas, con nivel de agregación opcional (dígitos). Barra de
progreso real y cancelación; las versiones ya guardadas se conservan.

**Idempotencia**: si no cambiaron los datos, las compensaciones, las plantillas, los registros, los
sustentos ni las políticas, se reutiliza la generación anterior; y aunque se fuerce, una versión se
crea solo si su contenido cambió. Los anexos aprobados o cerrados no se regeneran (se informan como
«protegidos», o «protegidos con cambios» si sus datos cambiaron y requieren reapertura).

## 6. Revisión, aprobación y versiones

| Transición | Rol |
|---|---|
| Iniciar elaboración, enviar a revisión, marcar subsanado | Administrador, supervisor, contador, analista |
| Observar (con motivo), marcar revisado | Administrador, supervisor, contador, auditor |
| Aprobar | Administrador, supervisor, contador — **nunca quien elaboró** (separación de funciones configurable) |
| Cerrar, reabrir (con motivo) | Administrador, supervisor |

- Aprobar o cerrar vuelve **inmutable** la versión. Para actualizar se requiere reapertura
  autorizada; la nueva generación crea una nueva versión y la aprobada se conserva.
- Cada versión guarda la huella de los datos, de las compensaciones, la plantilla y las reglas
  usadas.
- Las ediciones usan control de concurrencia optimista (si otro usuario modificó el anexo, se pide
  actualizar).
- **Aprobación automática** solo si un supervisor la autoriza en «Responsables y políticas», y solo
  para anexos **cuadrados sin observaciones**.
- Comparaciones: mes anterior, ejercicio anterior, versión original, última aprobada, cualquier
  versión u otra fecha de corte (si no hay versión, se calcula al vuelo). Se identifican partidas nuevas,
  canceladas, cambios de importe, reclasificaciones, cambios de antigüedad y observaciones nuevas o
  subsanadas.

## 7. Documentación sustentatoria y seguridad

- Adjuntos (PDF, imágenes, Excel, CSV, Word, XML, ZIP; máx. 20 MB) por categoría, relacionados con la
  cuenta, el anexo, el tercero, el documento o la partida. Se guardan con su hash y quedan en la
  auditoría. Un documento adjunto a una fila o a la cuenta pasa sus partidas a «documentado» en la
  siguiente versión.
- **Permisos por empresa** (todo se acota a la empresa), **por rol** y **por cuenta** (asignación de
  «acceso por cuenta»).
- **Datos personales** (cuenta 41): documento y nombre del trabajador se enmascaran para quien no tiene
  el permiso, también en las exportaciones. Los adjuntos confidenciales requieren ese permiso.
- Bitácora de auditoría de toda acción (generar, editar, cambiar estado, adjuntar, exportar,
  configurar).

## 8. Exportación

- **Excel por anexo**: encabezado empresarial, resumen con **fórmulas verificables**
  (`=B…+B…-B…`, diferencia `=contable − detalle`, detalle `=SUBTOTAL(9,…)`), importes numéricos,
  encabezados fijos, filtros, subtotales y totales con `SUBTOTAL`, observaciones y espacios de
  elaboración, revisión y aprobación.
- **Libro masivo**: Índice con enlaces internos, Resumen general, Balance de comprobación, una hoja por
  anexo, Diferencias, Observaciones y Control de revisión.
- **PDF**: logotipo, datos de la empresa, encabezados repetidos, «Página x de y», totales,
  observaciones, responsables, fecha de generación y versión; **expediente de cierre** completo.
  Los espacios de visto bueno **no** son firmas digitales certificadas.

## 9. Rendimiento medido

Prueba `test_volumen_1000_cuentas_y_100000_movimientos` (SQLite, un proceso): 1 200 cuentas
analíticas, 100 000 líneas de diario.

| Operación | Tiempo |
|---|---|
| Generación masiva de 1 200 anexos | 21.6 s |
|   · carga del libro, saldos y fuentes | 1.4 s |
|   · composición de partidas de la fase 4 al corte | 6.5 s |
|   · cálculo, conciliación y versionado de los 1 200 anexos | 12.9 s |
| Dashboard de anexos | 1.4 s |
| Página del detalle de un anexo | 0.01 s |
| Libro Excel de 1 200 anexos (1 206 hojas, 8.3 MB) | 21.4 s |

## 10. Limitaciones

- Las conciliaciones externas (bancaria formal, confirmaciones de terceros, SUNAT) son de la fase 6:
  el anexo de efectivo muestra el saldo del estado bancario si existe, pero no concilia partida por
  partida.
- La información de soporte (activos, cronogramas, contratos, inventario, servicios) debe importarse;
  no se integra todavía en línea con un ERP.
- La clasificación de movimientos patrimoniales (aportes, distribuciones…) se infiere de la
  contrapartida del asiento y debe revisarse.
- Las variaciones significativas usan un umbral fijo (50 % y S/ 1 000).
- El libro Excel masivo no incluye el logotipo (sí el PDF).
- La identidad del usuario es declarativa (`X-Usuario`) hasta la fase de autenticación.
