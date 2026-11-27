# Manual — Motor inteligente de conciliaciones contables (fase 6)

La conciliación compara **fuentes independientes** (libro, estado bancario, registros de compras y ventas,
planillas, kardex, cronogramas, constancias, declaraciones, la contabilidad de una empresa relacionada…) y
muestra coincidencias, faltantes, duplicados y diferencias. **Es analítica**: no modifica asientos, no genera
ajustes, no realiza operaciones bancarias ni presenta declaraciones. Toda diferencia queda visible y
cuantificada (también las que están dentro de la tolerancia) y **no toda diferencia es un error contable**:
un depósito en tránsito o un ingreso devengado no facturado son diferencias temporales.

## 1. Pantallas

| Menú | Uso |
|---|---|
| Dashboard de conciliaciones | KPI de programadas, ejecutadas, aprobadas y pendientes; registros comparados y conciliados; % por **cantidad** y % por **importe** (por separado); importe pendiente bruto y **neto** (una partida observada en dos conciliaciones relacionadas no se suma dos veces); diferencias críticas; gráficos por tipo, mes, cuenta, antigüedad, riesgo, aprobación y recurrentes |
| Centro de conciliaciones | Lista filtrable (tipo, estado, responsable, nombre) y **Nueva conciliación**: tipo, plantilla, fecha de corte, responsable, fecha límite y ámbito (cuenta bancaria, cuenta contable, moneda, centro de costo, proyecto o empresa relacionada) |
| Conciliación → Resumen y reporte | Resultado por estado (cantidad, importe y %), diferencias por clasificación, etapas del proceso en ms y el reporte especializado (p. ej. conciliación bancaria completa) |
| → Fuentes | Fuentes de la plantilla; las de archivo se importan con el **asistente de homologación** (vista previa, columnas sugeridas, ajuste manual, filas excluidas y subtotales, guardado de la homologación para reutilizarla) |
| → Panel de conciliación | **Panel dual** (fuente A y fuente B): búsqueda, filtros, selección múltiple, importes parciales, totales seleccionados A/B, diferencia y estado permanentes, vista previa, justificación obligatoria y confirmación |
| → Coincidencias | Grupos exactos, en tolerancia, parciales, agregados, ambiguos y manuales: confirmar propuestas, rechazar (con motivo) y revertir confirmadas (supervisor) |
| → Diferencias | Diferencias de la versión vigente; clic → ficha de la incidencia |
| → Historial y aprobación | Versiones (inmutables al aprobar), elaboró / revisó / aprobó, aprobaciones, reversiones, auditoría y **estado a una fecha** |
| Explorador de diferencias | Todas las diferencias vigentes con filtros por clasificación, prioridad, estado, tipo, responsable, texto, trasladadas; orden por importe o antigüedad |
| Centro de incidencias | Diferencias abiertas: responsable, fecha límite, causa, acción correctiva, comentarios, documentos, cambio de estado y continuidad entre periodos |
| Panel de aprobación | Conciliaciones pendientes de revisión y de aprobación |
| Diseñador de reglas | Asistente de 10 pasos: fuentes → homologación → campos de cruce → campos monetarios → tolerancias → reglas → agrupación → prueba → revisión → guardado |
| Historial | Auditoría global (usuario, fecha, acción, entidad, conciliación, versión y detalle) |
| Exportaciones | Reportes globales en Excel y PDF |
| Tolerancias, responsables y tasas | Tolerancias por tipo / cuenta / moneda, responsables y programación, autorización de **grupo económico**, aprobación de tasas tributarias |

## 2. Flujo de trabajo

1. **Crear** la conciliación (Centro → Nueva conciliación). Una misma combinación de plantilla, ámbito y fecha
   de corte no se duplica: se reutiliza.
2. **Importar** las fuentes externas (pestaña Fuentes). Las internas (libro, registros de la fase 2, auxiliares
   de la fase 5, movimientos bancarios de la fase 1) se arman solas al ejecutar.
3. **Ejecutar**. El proceso es asíncrono, con avance real y cancelación. Si nada cambió (fuentes, reglas,
   tolerancias, decisiones) no se genera otra versión. Cada ejecución con cambios crea una **versión**.
4. **Revisar coincidencias**: las propuestas se confirman o rechazan; las **ambiguas** nunca se aprueban solas
   y bloquean la aprobación; se resuelven rechazándolas y conciliando en el panel dual.
5. **Conciliar manualmente** lo pendiente (también parcialmente). Las decisiones manuales se **re-aplican** en
   las siguientes ejecuciones mientras los registros sigan iguales; las propuestas rechazadas no se vuelven a
   proponer.
6. **Gestionar incidencias**: estado (9 estados), responsable, plazo, causa, acción correctiva y documentos.
7. **Enviar a revisión → Revisada → Aprobada → Cerrada**. Quien elabora no revisa; quien elabora o revisa no
   aprueba. Para aprobar no puede haber ambiguas sin resolver ni diferencias críticas sin analizar (configurable
   por plantilla). La versión aprobada queda **inmutable**.
8. **Revertir** (solo supervisor o administrador, con motivo): la conciliación pasa a *Reabierta*; la siguiente
   ejecución genera una versión nueva y la aprobada se conserva tal cual (consultable y exportable).

### Estados

Conciliación: Borrador, Ejecutada, En revisión, Observada, Revisada, Aprobada, Cerrada, Reabierta.
Incidencia: Detectado, Pendiente de revisión, En análisis, Justificado (requiere causa), Pendiente de
regularización (requiere acción correctiva; queda preparada para la fase 8), Subsanado, Aprobado, Cerrado,
Reabierto (requiere motivo).

### Continuidad mensual

Al conciliar un periodo, cada diferencia que **ya existía** en el periodo anterior de la misma conciliación
(misma huella: tipo, ámbito y registros o clave) se **traslada**: conserva la fecha de detección, el periodo de
origen, el importe original, el responsable, el estado, las causas y acciones, suma una recurrencia y enlaza la
cadena (consultable en la ficha). Las que ya no se reproducen se marcan **subsanadas** automáticamente. No se
duplican: el explorador solo muestra la versión vigente.

## 3. Catálogo de conciliaciones

| Tipo | Fuente A | Fuente B (y C) | Detecta |
|---|---|---|---|
| Bancaria | Libro (cuenta 10 de la cuenta bancaria, en su moneda) | Estado de cuenta importado (fase 1, incluye PDF con revisión manual) | Depósitos en tránsito, cheques y transferencias pendientes, comisiones, ITF, intereses, cargos no registrados, abonos no identificados, duplicados, diferencias de importe, periodos distintos |
| Compras | Registro de compras (fase 2) | Provisiones contables (42/43/46/47, IGV 4011, cuentas de destino) | Compra no contabilizada, contabilizada sin registro, duplicados, diferencias de IGV, base y total, NC sin comprobante relacionado, periodo, tipo de cambio, clasificación (no toda compra es gasto) |
| Ventas | Registro de ventas | 12/13/16, 40, 70/75/77 | Factura no contabilizada, **ingreso sin comprobante** (diferencia temporal; evaluar NIIF 15, no es error por sí mismo), IGV, base, NC/ND, anulados, periodo |
| Planillas | Planilla procesada (archivo) | 14, 40 (AFP, ONP, EsSalud, quinta), 41, 46, 62 | Remuneración no contabilizada, diferencias de neto, aportes y retenciones, descuentos no registrados, préstamos no descontados, provisiones, distribución por centro de costo. **Datos personales protegidos** |
| Activos fijos | Registro de activos (fase 5) | 33/34, 39, 68 por código de activo | Solo en contabilidad, solo en el auxiliar, costo, depreciación, bajas no registradas, depreciación posterior a la baja, depreciación que excede lo depreciable, financiera vs tributaria. Un activo totalmente depreciado **no** se da de baja automáticamente |
| Inventarios | Kardex valorizado (archivo) | Existencias 20–28 por cuenta | Valor inicial, entradas, salidas y final; existencias negativas, duplicados, cantidades y valores **por separado**, costo unitario según el método configurado, unidades de medida, productos sin cuenta |
| Servicios y costos en proceso | Reporte operativo de costos por proyecto | Clase 6 por proyecto y concepto; cuenta 23 (informativa) | Costos sin proyecto, duplicados, diferencias operativo vs contable, servicios culminados con costos en la 23 (la conciliación de costos es independiente del reconocimiento de ingresos) |
| Obligaciones financieras | Cronogramas (última versión) | 45 y 67 por contrato | Cuota no registrada, intereses pendientes, pago duplicado, pago sin cuota, diferencia de capital, cronograma modificado (versiones) |
| Detracciones | Comprobantes con código de detracción (esperado = total × tasa vigente aprobada) | Constancias (archivo) y C: registro contable con constancia | Factura sin depósito, depósito sin documento, depósito duplicado, diferencia de importe, posible depósito extemporáneo, constancia no contabilizada, aplicación de la fase 4 inconsistente. **Nunca declara incumplimiento definitivo** |
| Retenciones y percepciones | Comprobantes (archivo) | 40113, 40114, 40173, 40174 | Retención sin comprobante (pendiente de sustento), no contabilizada, diferencia frente a la tasa vigente aprobada (sin tasas fijas) |
| Tributos y aportes | Declaraciones y constancias (archivo) | Cuenta 40 por tributo y periodo | Obligación, pagos y créditos; declarado no contabilizado, contabilizado no declarado. No presenta declaraciones ni realiza pagos |
| Intercompañía | Operaciones con la relacionada | Contabilidad de la relacionada (con la empresa como contraparte), signo opuesto | Operación no recíproca, importe, moneda, periodo, clasificación no recíproca. Requiere autorización de **grupo económico en ambas empresas** y acceso del usuario a las dos. Sin eliminaciones de consolidación |
| Origen–destino | Clase 6 destinable (política de la fase 3) | B: clase 9; C: 79 | Gasto sin destino, destino sin origen, distribución duplicada o incompleta, destino incorrecto por centro de costo, 9 vs 79. La clase 9 no es un gasto adicional y no toda la clase 6 debe coincidir |
| Auxiliares vs mayor | Anexos de la fase 5 | B: mayor; C: balance importado | Diferencias por cuenta; aviso: un anexo generado desde el mismo mayor **no** es evidencia independiente |
| Personalizada | Definida en el diseñador | — | Según las reglas |

## 4. Arquitectura del motor universal

```
fuentes (constructores internos · archivo homologado)  →  registros normalizados (RegistroFuente)
      →  Comparador: exclusiones → duplicados por fuente → decisiones manuales previas → reglas por pasada
      →  Resultado/clasificar: genérico + especializado por tipo + reglas de clasificación
      →  versión: grupos, coincidencias, asignaciones por registro y pasada, diferencias (con continuidad)
```

- **Registro normalizado**: campos fijos (fecha, periodo AAAAMM, tipo de documento, serie, número, tercero,
  operación, referencia, cuenta, centro de costo, proyecto, concepto, moneda, importe con signo, importe ME,
  cantidad, datos personales) + `datos` JSON específicos (IGV, base, costo, depreciación, tasa…) + referencia al
  origen (tabla, id, fila del archivo). `clave_registro` es una identidad estable entre ejecuciones.
- **Pasadas**: pares de fuentes (A–B, B–C) en modo PARTIDAS o AGREGADO, con signo IGUAL u OPUESTO.
- **Reglas** (en orden de prioridad):
  - `CLAVE`: índice por campos normalizados (documentos sin ceros a la izquierda ni separadores). 1:1 exacto,
    en tolerancia o con diferencia; N:M si cuadra; si no, ambigua.
  - `IMPORTE_FECHA`: índice ordenado por importe y búsqueda binaria dentro de la tolerancia y la ventana de días;
    un candidato único en ambos sentidos → coincidencia; varios → ambigua (no consume registros).
  - `COMBINACION`: 1:N / N:1 con DFS acotado (máximo de elementos, candidatos y nodos) sobre un índice por
    moneda, signo y fecha; una sola solución → propuesta; varias → ambigua.
  - `AGREGADO`: agrupa por claves (concepto y trabajador, código de activo, cuenta, tributo y periodo…) y compara
    varios campos monetarios.
  - `EXCLUSION` y `CLASIFICACION`: expresiones seguras (sin SQL ni código).
- **Asignaciones**: por versión, registro y pasada, con `conciliado ≤ total` (restricción en la base) y
  actualización condicional para que dos usuarios no concilien el mismo saldo.
- **Huella de diferencia**: tipo + ámbito + registros o clave → continuidad entre versiones y periodos.
- **Idempotencia**: hash de configuración, tolerancia, datos de cada fuente y decisiones; sin cambios no hay
  versión nueva.

## 5. Archivos

| Archivo | Contenido |
|---|---|
| `app/models/conciliacion.py` | 19 entidades |
| `migraciones/versions/0006_fase_6_conciliaciones.py` | tablas, roles TESORERO/PLANILLAS, `documentos_registro.documento_referencia` |
| `app/conciliacion/esquemas.py` | diseños de fuentes externas registrados en el registro de la fase 2 |
| `app/conciliacion/catalogo.py` | 15 tipos y plantillas con reglas |
| `app/conciliacion/fuentes.py` | constructores de fuentes, lectura y normalización de archivos |
| `app/conciliacion/motor.py` | comparador universal |
| `app/conciliacion/clasificar.py` | clasificación genérica y especializada, reportes |
| `app/conciliacion/servicio.py` | ciclo de vida, permisos, versiones, continuidad, manual, flujo, incidencias, tasas |
| `app/conciliacion/consultas.py` | listados paginados, tablero, historial a una fecha |
| `app/conciliacion/disenador.py` | validación, guardado, autorización y prueba de plantillas personalizadas |
| `app/conciliacion/exportar.py` | Excel y PDF |
| `app/api/conciliaciones.py` | API REST (`/api/conciliaciones/...`) |
| `app/static/app_conciliaciones.js` | interfaz |
| `tests/test_conciliaciones.py` | 24 pruebas (28 escenarios obligatorios + diseñador, versiones de cronograma, servicios y ventas) |

Reutilización: homologación y lectura de archivos (fase 2), registros de compras/ventas (fase 2), saldos,
política de destino y balance (fase 3), roles y reglas de tasas tributarias (fase 4), contexto del libro,
registros auxiliares, constructores de activos y depreciación, motor de expresiones, estilos de exportación y
PDF numerado (fase 5), estados de cuenta y movimientos bancarios (fase 1), trabajos asíncronos (fase 2).

## 6. Diferencias

Clasificaciones: registro faltante en contabilidad, registro faltante en la fuente externa, diferencia
monetaria, diferencia temporal, diferencia de corte, diferencia de clasificación, documento duplicado,
documento pendiente de sustento, diferencia de tipo de cambio, diferencia de parametrización, coincidencia
ambigua, diferencia no identificada. Prioridades: Crítico, Alto, Medio, Bajo, Informativo.

Cada diferencia registra código, tipo, subtipo, fuente, cuenta, documento, tercero, importe, moneda, fecha,
**evidencia** (registros, grupo, valores comparados, pasada), regla, explicación, recomendación, responsable,
estado, fecha de detección, periodo de origen, importe original y pendiente, recurrencias.

Tolerancias: la plantilla trae una tolerancia por defecto (absoluta, porcentaje y días); en *Tolerancias* se
definen otras por tipo, cuenta y moneda (gana la más específica). Las coincidencias en tolerancia se marcan y
**su diferencia se registra** (prioridad informativa) y entra en el reporte (p. ej. en la línea «diferencias de
importe en partidas conciliadas» de la conciliación bancaria).

## 7. Seguridad

- Todo se filtra por `empresa_id`; una conciliación o diferencia de otra empresa responde 404.
- Roles (los de la fase 4 más TESORERO y PLANILLAS): Administrador, Supervisor, Contador, Analista (elaboran);
  Auditor (consulta y revisa, no aprueba); Tesorero (bancaria, financieras y detracciones); Responsable de
  planillas (planillas y tributos); Consulta. Sin roles asignados la empresa opera en «modo abierto».
- Datos de planilla: solo Administrador, Supervisor y Responsable de planillas ven DNI, nombres y glosas; el
  resto ve importes y conceptos con el trabajador enmascarado (también en Excel y PDF). El Tesorero no accede
  a las conciliaciones de planillas.
- Tasas de detracción, retención y percepción: se configuran en la fase 4 con vigencia y fuente normativa y
  las **aprueba** un supervisor o administrador distinto de quien las configuró
  (`POST /api/conciliaciones/tasas/{id}/aprobar`). Sin aprobación no se calcula ningún importe esperado.
- Plantillas personalizadas: requieren autorización de otro usuario con permiso de configuración.
- Auditoría: usuario, rol, fecha, acción, entidad, conciliación, versión y detalle (fuente, regla, resultado,
  cambios manuales, aprobaciones, reversiones). Nada se elimina: tolerancias y asignaciones se desactivan, las
  fuentes reemplazadas se conservan para las versiones anteriores.

## 8. Exportación

Excel por conciliación: **Resumen** (con fórmulas de totales y porcentajes), **reporte especializado** (para la
bancaria: saldo banco + partidas = banco ajustado; saldo libros + partidas = libros ajustado; diferencia final,
todo con fórmulas, y el detalle de cada partida), **Fuente contable**, **Fuente externa**, **Conciliados**,
**No conciliados** (con totales `SUBTOTAL` y referencia al registro original: tabla, id y fila del archivo),
**Diferencias**, **Observaciones** y **Control de aprobación**. PDF con logotipo (el de la fase 5), ficha,
resumen, reporte, diferencias, partidas no conciliadas, aprobaciones y «Página x de y». Cualquier versión
anterior se exporta con `version_id`.

Reportes globales (Excel o PDF): resumen de conciliaciones, diferencias, pendientes, observaciones e historial
de versiones, filtrables por ejercicio, periodo y tipo.

## 9. Pruebas y rendimiento

`python -m pytest tests/test_conciliaciones.py -q` (datos sintéticos). Escenarios: 1 bancaria sin diferencias ·
2 comisión no registrada · 3 depósito en tránsito · 4 transferencia duplicada · 5 compra no contabilizada ·
6 diferencia de IGV · 7 NC no relacionada · 8 planilla vs 41 · 9 aportes · 10 activo no registrado en el
auxiliar · 11 depreciación · 12 kardex · 13 capital de préstamo · 14 detracción sin constancia · 15 retención
pendiente de sustento · 16 intercompañía no recíproca · 17 gasto sin destino · 18 distribución duplicada en la
clase 9 · 19 coincidencia parcial y combinada · 20 ambigua · 21 dentro de tolerancia · 22 traslado al periodo
siguiente · 23 reversión de una aprobada · 24 historial a una fecha · 25 procesamiento masivo · 26 Excel/PDF ·
27 seguridad multiempresa · 28 protección de datos de planilla.

Volumen medido en el entorno de desarrollo (SQLite, un proceso): **109 000 registros** (55 000 + 54 000):
importación de los dos archivos ≈ 8 s; conciliación ≈ 11,6 s (lectura 1,6 s, comparación 3,0 s, clasificación
0,1 s, registro de la versión 6,8 s); re-ejecución sin cambios ≈ 3,8 s (sin nueva versión).

## 10. API

Base `/api/conciliaciones` (todas con `empresa_id` y cabecera `X-Usuario`):
`GET catalogo`, `GET/POST ""`, `GET {id}`, `POST {id}/fuentes/{lado}/archivo`, `POST {id}/ejecutar`,
`POST {id}/cancelar`, `GET {id}/registros`, `GET {id}/grupos`, `POST {id}/manual`,
`POST grupos/{gid}/{confirmar|rechazar|revertir}`, `POST {id}/estado`, `POST {id}/revertir`, `GET {id}/historial`,
`GET {id}/a-fecha`, `GET {id}/exportar`, `GET diferencias`, `GET/PATCH diferencias/{id}`, `POST adjuntos`,
`GET adjuntos/{id}`, `GET tablero`, `GET reportes/{tipo}`, `GET auditoria`, `GET trabajos/{id}`,
`GET/POST/PUT plantillas`, `POST plantillas/{id}/autorizar`, `POST plantillas/validar`, `POST plantillas/probar`,
`GET/POST/DELETE tolerancias`, `GET/POST/DELETE asignaciones`, `GET mapeos`, `POST tasas/{id}/aprobar`.

## 11. Limitaciones

- El estado bancario en PDF se importa con el flujo de la fase 1 (PDF con texto y revisión manual); no se leen
  PDF escaneados.
- Las conciliaciones programadas se registran (responsable, tipo y día) y se muestran en el tablero, pero no se
  ejecutan solas: no hay planificador en el servidor.
- Los trabajos corren en hilos del mismo proceso (un servidor); para varios nodos hace falta una cola.
- El usuario se toma de la cabecera `X-Usuario` (sin autenticación real todavía).
- Planillas: el mapeo concepto → cuenta es el de la plantilla (editable en una plantilla personalizada); las
  planillas con conceptos muy distintos requieren ajustarlo.
- La conciliación bancaria compara el acumulado del ejercicio hasta el corte; las partidas pendientes de
  ejercicios anteriores solo se ven si sus movimientos están en el ejercicio.
- La conciliación intercompañía lee la contabilidad de la relacionada desde la misma base (mismo sistema).
- No se generan asientos de regularización (fase 8) ni se integra con SUNAT/SIRE (fase 12).
