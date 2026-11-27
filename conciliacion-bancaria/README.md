# Analizador Contable Inteligente

**Accounting Intelligence 360.** Plataforma de análisis contable para empresas peruanas (PCGE):
importación, homologación y validación de información de cualquier ERP, análisis de cuentas
(saldos, navegación hasta el asiento, antigüedad, origen–destino, reglas, papeles de trabajo) y
conciliación bancaria de la **cuenta 10**.

> Módulo independiente dentro de este repositorio. No comparte código con la app Flutter.

**Estado: fases 1 a 6 completadas.** Plan en [`docs/PLAN.md`](docs/PLAN.md) · validaciones de
importación en [`docs/VALIDACIONES.md`](docs/VALIDACIONES.md) · reglas de análisis en
[`docs/REGLAS_ANALISIS.md`](docs/REGLAS_ANALISIS.md) · **manual de uso del análisis** en
[`docs/MANUAL_ANALISIS.md`](docs/MANUAL_ANALISIS.md) · **manual de compensación de partidas** en
[`docs/MANUAL_COMPENSACION.md`](docs/MANUAL_COMPENSACION.md) · **manual de anexos contables** en
[`docs/MANUAL_ANEXOS.md`](docs/MANUAL_ANEXOS.md) · **manual de conciliaciones** en
[`docs/MANUAL_CONCILIACIONES.md`](docs/MANUAL_CONCILIACIONES.md).

## Puesta en marcha

```bash
cd conciliacion-bancaria
pip install -r requirements.txt
python scripts/generar_ejemplos.py             # estados de cuenta de prueba
python scripts/generar_ejemplos_contables.py   # archivos contables de prueba (requiere xlwt)
uvicorn app.main:app --reload
```

- Interfaz web: http://localhost:8000
- API (OpenAPI/Swagger): http://localhost:8000/api/docs
- Base de datos: SQLite en `./data/conciliacion.db`. Para PostgreSQL defina
  `DATABASE_URL=postgresql+psycopg://usuario:clave@host/bd` (requiere `psycopg`).
- El esquema se gestiona con **Alembic**: al iniciar se aplican las migraciones pendientes
  (`alembic upgrade head` también funciona a mano). Una base creada en la fase 1 se adopta
  automáticamente en la revisión 0001 y se actualiza sin perder datos.

Pruebas: `python -m pytest -q`

### Recorrido de demostración — auditor contable 360 (fase 7)

Con la información de las fases anteriores importada, abra **Auditor contable 360 → Centro de ejecución**, cree un
encargo (tipo, corte, alcance) y pulse **Auditoría completa**. Revise el **dashboard**, abra los hallazgos en el
**explorador** (evidencias, asiento original, cambio de estado con separación de funciones, planes de acción), la
**matriz de riesgos**, los **papeles de trabajo** y genere los **informes** en PDF o Excel. `tests/test_auditoria.py`
cubre los 28 escenarios obligatorios con datos sintéticos; `scripts/benchmark_auditoria.py N` mide el volumen.

### Recorrido de demostración — conciliaciones contables (fase 6)

Importe el diario (fase 2) y el estado de cuenta (fase 1). En **Centro de conciliaciones** pulse **Nueva
conciliación** (p. ej. bancaria de la cuenta BCP al cierre del mes), importe las fuentes de archivo que pida la
plantilla (planilla, kardex, constancias…) y pulse **Ejecutar conciliación**. Revise el reporte, confirme o
rechace coincidencias, concilie lo pendiente en el **panel dual**, gestione las diferencias en el **Centro de
incidencias** y envíe a revisión y aprobación. `tests/test_conciliaciones.py` contiene los 28 escenarios
obligatorios con datos sintéticos.

### Recorrido de demostración — anexos contables (fase 5)

Importe el diario y, si corresponde, apruebe compensaciones (fase 4). En **Registros auxiliares**
cargue el registro de activos, cronogramas, gastos anticipados o servicios en proceso (CSV/XLSX). En
**Dashboard de anexos** pulse **Generar anexos de todo el balance**; abra un anexo desde el **Centro
de anexos** para ver su detalle (clic en una fila → asiento original), conciliación, observaciones,
documentación, revisión y versiones. Exporte en Excel o PDF, o genere el expediente de cierre en
**Exportaciones**. `tests/test_anexos.py` contiene un juego de datos con los 21 casos obligatorios.

### Recorrido de demostración — compensación de partidas (fase 4)

Con el diario importado, abra **Reglas y roles** (opcional: regla entre cuentas 4212↔4221 para
anticipos, reglas de detracción/retención con su tasa). En **Dashboard de compensación** elija la
fecha de corte y pulse **Ejecutar motor**. Revise **Propuestas y aprobaciones** (y la pestaña
*Ambiguas*), complete lo pendiente en **Compensación manual** (doble panel con vista previa) y
verifique **Conciliación y observaciones**: las partidas abiertas deben explicar el saldo contable.
La prueba `tests/test_compensacion.py` contiene un juego de datos con los 18 casos contables.

### Recorrido de demostración — análisis de cuentas (fase 3)

Con la información contable importada (ver el recorrido de la fase 2), abra **Dashboard de
análisis**, elija el periodo y pulse **Ejecutar análisis**. Luego: **Explorador de cuentas** (clic en
una cuenta → panel lateral → *Navegar movimientos* → tercero → documento → clic en una línea para
ver el asiento y la fila original), **Origen y destino**, **Antigüedad**, **Comparativos**,
**Observaciones** (revisión profesional), **Reglas de análisis** y **Papeles de trabajo**.

### Recorrido de demostración — analizador contable (fase 2)

En **Importar información contable**, ejercicio 2026, periodo 10, cargue de `ejemplos/contable/`
en este orden (los maestros primero, porque las validaciones los usan):

1. `plan_cuentas_concar.xlsx` (Plan de cuentas), `centros_costo.csv`, `tipos_cambio_2026-10.csv`,
   `proveedores.xlsx`, y `saldos_iniciales_2026.xlsx` con periodo 00.
2. `diario_concar_2026-10.xlsx`: títulos, subtotales por asiento y total general se detectan
   solos. Trae errores sembrados: asiento descuadrado, cuenta inexistente, inactiva y de título,
   fecha fuera de periodo, factura duplicada en otro asiento, centro de costo inexistente, TC
   distinto al publicado, gasto sin destino, destino ≠ 79, provisión sin 78 e importe ilegible.
3. `diario_sap_2026-10.csv` con sistema SAP: decimales con coma y claves 40/50. En SAP
   «Nº documento» es el asiento: reasígnelo en la homologación y guarde la plantilla; el
   siguiente archivo SAP la aplicará solo.
4. `compras_2026-10.txt`: sin encabezado (fila 0), se homologa por posición de columna.
5. `balance_comprobacion_2026-10.xls` (Excel 97-2003, encabezado en dos filas, con niveles de
   resumen) con periodo «Anual»: se cruza con el diario y con los saldos iniciales.

### Recorrido de demostración — conciliación bancaria (fase 1)

1. **Empresas** → registrar `20609876540` · Comercial Andina S.A.C. (RUC ficticio).
2. **Cuentas bancarias** → BCP PEN `104101`, BBVA USD `104102`, Interbank PEN `104103`.
3. **Importar archivos** → los 3 estados de cuenta de `ejemplos/` y el libro mayor
   (el mismo Excel sirve para las tres subcuentas: se filtra por subcuenta).
4. **Movimientos** → filtrar «Solo posibles duplicados» y resolver la fila repetida del BCP.

## Fase 7 — auditor contable inteligente 360

Herramienta de apoyo al contador y al auditor: no emite dictámenes, no declara fraude ni modifica asientos.
Manual completo en [`docs/MANUAL_AUDITORIA.md`](docs/MANUAL_AUDITORIA.md).

| Área | Detalle |
|---|---|
| Reglas | 167 reglas en 18 categorías (integridad, asientos, duplicidades, CxC, CxP, tesorería, gastos, origen–destino, parametrización del ERP, ingresos, servicios, activos, inventarios, planillas, tributaria preventiva, devengos y corte, estadística, configurables) que reutilizan las fases 1–6 |
| Hallazgos | Condición, criterio, causa, efecto, impacto, recomendación y evidencia; huella única (sin duplicar), grupos de exposición sin superposición, reincidencias; 11 estados con separación de funciones e historial inmutable |
| Riesgo | Matriz 5×5 editable, materialidad definida y aprobada por el responsable (sin porcentajes por defecto), ajuste manual justificado |
| Normativa | Reglas tributarias con norma, fuente oficial, vigencia y responsable; sin validación no se ejecutan; sin datos → «pendiente de evaluación» |
| Trabajo | Encargos con alcance, ejecución completa/módulo/cuenta/reglas, incremental, muestras con semilla, papeles de trabajo, planes de acción, bandeja de regularización (fase 8, sin asientos) |
| Informes | 6 versiones de 16 secciones (versionadas con hash) y 12 exportaciones en Excel y PDF |
| Rendimiento | 100 000 / 500 000 / 1 000 000 movimientos: 19,8 s / 107,5 s / 214,2 s; re-ejecución incremental < 0,5 s |

## Fase 6 — motor inteligente de conciliaciones contables automáticas

| Área | Detalle |
|---|---|
| Motor universal | 2 a 4 fuentes normalizadas; reglas por clave, importe y fecha, combinación (1:N, N:1), agregado, exclusión y clasificación; 1:1, 1:N, N:1, N:N y parciales; duplicados por fuente; ambiguas nunca automáticas; decisiones manuales re-aplicadas |
| Tipos | Bancaria, compras, ventas, planillas, activos fijos, inventarios, servicios y costos en proceso, obligaciones financieras, detracciones, retenciones y percepciones, tributos y aportes, intercompañía, origen–destino, auxiliares vs mayor y personalizada |
| Diferencias | 11 clasificaciones y 5 prioridades con evidencia, regla, explicación y recomendación; tolerancias por tipo, cuenta y moneda (visibles); incidencias con 9 estados y continuidad entre periodos |
| Control | Panel dual de conciliación manual, versiones inmutables al aprobar, separación de funciones, reversión autorizada, historial a una fecha, datos de planilla protegidos, auditoría |
| Diseñador | Asistente de 10 pasos sin SQL ni código, prueba en memoria y autorización por otro usuario |
| Exportación | Excel (8 hojas + reporte especializado con fórmulas) y PDF; reportes globales |
| Rendimiento | 109 000 registros conciliados en ≈ 12 s |

## Fase 5 — generador inteligente de anexos contables

| Área | Detalle |
|---|---|
| Centro de anexos | Explorador jerárquico con plantilla y estado por cuenta; anexos individuales, seleccionados, por elemento, rango o balance completo; filtros por centro de costo, proyecto, unidad y moneda |
| Plantillas | 73 del catálogo (elementos 0–9, 19 especialidades) + diseñador: columnas, agrupación, subtotales, filtros, campos calculados con motor seguro, reglas, rangos, encabezado, orientación, logotipo |
| Conciliación | Saldo final = inicial + debe − haber (signo natural); detalle sustentado / sin documento / sin detalle / por clasificar; balance importado; cuadrado, con observaciones, parcialmente sustentado, descuadrado o información insuficiente |
| Especializados | Efectivo con estado bancario, cartera con compensaciones de la fase 4, entregas a rendir, devengo de gastos anticipados, servicios en proceso (23), activos fijos y depreciación financiera/tributaria, tributos, remuneraciones, obligaciones financieras con cronograma, patrimonio, gastos, ingresos, origen–destino |
| Control | 10 estados, separación de funciones, versiones inmutables al aprobar, reapertura autorizada, comparación histórica, adjuntos, permisos por empresa / rol / cuenta, datos personales enmascarados, auditoría |
| Exportación | Excel con fórmulas verificables y libro masivo con índice; PDF y expediente de cierre |
| Rendimiento | 1 200 cuentas y 100 000 líneas: generación ≈ 20 s, libro Excel de 1 206 hojas ≈ 21 s |

## Fase 4 — motor inteligente de compensación automática de partidas

| Área | Detalle |
|---|---|
| Partidas abiertas | Desde el diario/mayor, idempotentes, con líneas de origen; apertura documental o «pendiente de desagregación» (nunca se inventan documentos) |
| Clasificación | 20 clases (factura, pago, NC, anticipo, detracción, retención…) con confianza y motivo; las ambiguas quedan por revisar |
| Coincidencias | 5 niveles, puntuación 0–100 (calidad, no probabilidad), combinaciones acotadas, ambiguas siempre a decisión humana |
| Modalidades | 1:1, 1:N, N:1, N:N, parcial, entre ejercicios, manual; entre cuentas/monedas con regla autorizada; entre terceros solo manual autorizado |
| Tributos y ME | Detracción/retención/percepción con tasas y vigencias configurables; ME evaluada en la moneda de la obligación, diferencia de cambio identificada sin asiento |
| Control | Aprobación (automática solo con política ≥ 95), separación de funciones, reversión sin borrado, roles, auditoría, control optimista e índices únicos |
| Resultados | Composición a cualquier fecha de corte, conciliación con el saldo contable, antigüedad real, anticipos, tributos, dashboard CxC/CxP, 14 reportes Excel/PDF |
| Rendimiento | 180 000 líneas / 90 000 partidas en ≈ 49 s, asíncrono, cancelable, idempotente |

## Fase 3 — motor inteligente de análisis de cuentas

| Área | Detalle |
|---|---|
| Saldos | Árbol PCGE sin doble conteo, apertura sin duplicar, cuadre exacto con las líneas de origen, precisión en céntimos enteros |
| Navegación | Balance → cuenta → subcuenta → tercero → documento → asiento (con contrapartidas) → fila original del archivo |
| Elementos 0–9 | Perfiles de análisis: cartera, existencias, cuenta 23 por proyecto, activo vs depreciación, pasivos, patrimonio, gastos, ingresos vs transferencias (78/79), intermediarios, analítica, orden |
| Origen–destino | 6 / 79 / 9 / 78 por periodo, CC, destino, origen y asiento; reglas de distribución con %, vigencia y exclusiones |
| Antigüedad | Tramos configurables, emisión o vencimiento, libros o cartera del ERP, resultados preliminares |
| Comparativos | Mes anterior, mismo mes año anterior, acumulado; por cuenta, CC, proyecto, unidad, moneda, tercero |
| Reglas | 21 reglas iniciales + reglas de umbral propias, versionadas, por grupo, con excepciones autorizadas |
| Revisión | Estados, responsable, comentarios e historial que persisten entre ejecuciones |
| Papeles de trabajo | Composición preliminar, conclusión, adjuntos, flujo hasta aprobación (aprobador distinto) |
| Exportación | Excel (numérico, filtros, totales) y PDF de 10 reportes |
| Rendimiento | Asíncrono, cancelable, caché invalidada por versión de datos; 100 200 movimientos: balance 0.4 s, análisis 5 s |

## Fase 2 — motor de importación y validación contable

| Área | Detalle |
|---|---|
| Tipos | Diario, mayor, balance de comprobación, compras, ventas, plan de cuentas, clientes, proveedores, centros de costo, saldos iniciales, tipos de cambio, CxC, CxP |
| Formatos | XLSX, XLS, CSV y TXT delimitado (con o sin encabezado, estilo PLE) |
| Asistente | 7 pasos; progreso real de subida (XHR) y de procesamiento (trabajo en segundo plano) |
| Lectura | Hoja y fila de encabezado elegibles, encabezados en dos filas, filas vacías y subtotales/totales identificados, separador decimal y formato de fecha configurables |
| Homologación | Sinónimos de SAP/Starsoft/Proficont/CONCAR/genéricos, confianza por campo, plantillas por empresa · sistema · tipo |
| Validación | 50+ reglas en 4 severidades, partida doble por asiento completo, cruces con maestros, saldos iniciales y diario, reglas configurables de clases 6, 7 y 9 |
| Lotes | Trazabilidad a archivo/hoja/fila, anulación y reemplazo, exportación de observaciones a CSV, auditoría |

## Fase 1 — conciliación bancaria: datos maestros e importación

| Área | Detalle |
|---|---|
| Multiempresa | Empresas con RUC validado (módulo 11), bancos con código SUNAT (Tabla 3), monedas PEN/USD/EUR |
| Cuentas | Cuenta bancaria ↔ subcuenta 10x, CCI validado, tolerancias por cuenta (días, importe, umbrales de confianza, tamaño máx. de combinación) |
| Importación banco | CSV (detecta delimitador y codificación), Excel .xlsx (con títulos sobre el encabezado), PDF con tablas y PDF de texto plano |
| Importación libro | Mayor de la cuenta 10 en CSV/Excel; filtra la subcuenta, toma el «saldo anterior», debe/haber o importe con signo |
| Detección de columnas | Sinónimos de BCP, BBVA, Interbank, Scotiabank, BanBif, BN y ERP locales; mapeo manual corregible en la vista previa |
| Normalización | Fechas dd/mm/aaaa, serial Excel, «15-OCT», «15/10» + año; importes `1,234.56`, `1.234,56`, `(500.00)`, `500.00-`, `CR/DB`, `S/`, `US$` |
| Validaciones | Moneda del archivo vs. cuenta, continuidad de saldos (detecta orden descendente), signo deducido del saldo cuando el banco no lo informa |
| Duplicados | Archivo ya importado (SHA-256), filas repetidas en el archivo, movimientos ya existentes por estados solapados; se marcan u omiten y se resuelven (excluir / mantener / restaurar) |
| Clasificación previa | ITF, comisión, interés, retención, depósito, transferencia, cheque, pago, retiro (base de la fase 4) |
| Trazabilidad | Historial de importaciones con anulación motivada (sin borrado físico) y bitácora de auditoría con antes/después |

Convención de signos: **+** ingresa dinero (abono en banco / debe en la 10), **−** sale (cargo / haber).

## Arquitectura

```
app/
  core/        configuración, BD, auditoría, utilidades (RUC, redondeo)
  models/      SQLAlchemy 2: maestros, importaciones, movimientos, auditoría
  schemas/     Pydantic v2 (contratos de la API)
  importers/   lectores (CSV/XLSX/PDF), columnas, normalización, analizador
  services/    importación bancaria y duplicados, catálogos
  contable/    fase 2: archivos, campos, homologación, validación, analítica 6/7/9, trabajos
  api/         routers FastAPI
  static/      interfaz web (HTML/CSS/JS sin build)
  analisis/    fase 3: pcge, saldos, navegación, antigüedad, comparativo, destino, reglas, motor, papeles, exportar
  compensacion/ fase 4: clasificacion, partidas, motor, servicio, consultas
  anexos/      fase 5: catalogo, datos, constructores, generador, flujo, expresiones, render, comparar, exportar
  conciliacion/ fase 6: esquemas, catalogo, fuentes, motor, clasificar, servicio, consultas, disenador, exportar
  auditoria/   fase 7: base, reglas por módulo (r_*), estadistica, configurables, catalogo, riesgo, motor, servicio, papeles, informes, consultas
migraciones/   Alembic (0001 fase 1 · 0002 fase 2 · 0003 fase 3 · 0004 fase 4 · 0005 fase 5 · 0006 fase 6 · 0007 fase 7)
tests/         188 pruebas (incluye 16 de auditoría con los 28 escenarios obligatorios de la fase 7 y una de volumen)
scripts/       benchmark_auditoria.py (rendimiento con datos sintéticos)
```

Importes en `Decimal` / `NUMERIC(18,2)`; nunca `float`.

## Limitaciones conocidas de esta fase

- Excel 97-2003 (`.xls`) no se lee: se pide guardarlo como `.xlsx` o `.csv`.
- PDF escaneados (imagen) no se procesan; se requiere PDF con texto.
- Los formatos de cada banco cambian con el tiempo; los sinónimos cubren los
  encabezados habituales y el mapeo manual cubre el resto. Conviene validar con
  exportaciones reales de cada banco (las homologaciones de fuentes de conciliación se guardan desde la fase 6;
  los perfiles de estados de cuenta por banco quedan para una fase posterior).
- El usuario se toma de la cabecera `X-Usuario` (campo «Usuario» de la interfaz);
  la autenticación real queda para una fase posterior.
- Los trabajos en segundo plano corren en hilos del mismo proceso (un solo servidor); para
  varios nodos se usará una cola en una fase posterior.
- La línea original del archivo (nivel 7) está disponible para lotes importados desde la fase 3.
- Los sinónimos de ERP se basan en encabezados habituales, no en exportaciones verificadas de
  cada versión: valide con archivos reales y guarde plantillas.
- Los maestros (plan, terceros, centros, TC) se actualizan registro a registro y no se anulan
  por lote.
- Anexos (fase 5): los registros auxiliares se importan (no hay integración en línea con el ERP); el libro
  Excel masivo no lleva logotipo.
- Conciliaciones (fase 6): las programadas no se ejecutan solas (sin planificador); no se generan asientos de
  regularización (fase 8) ni se integra con SUNAT/SIRE; ver [`docs/MANUAL_CONCILIACIONES.md`](docs/MANUAL_CONCILIACIONES.md).
- Auditoría (fase 7): las reglas tributarias normativas se entregan sin norma ni tasas y pendientes de validación; las
  recurrentes se programan con un botón (sin planificador); con 1 M de movimientos la auditoría completa usa ≈ 5,3 GB
  de memoria; no se generan asientos de regularización (fase 8). Ver [`docs/MANUAL_AUDITORIA.md`](docs/MANUAL_AUDITORIA.md).
- Compensación (fase 4): no se generan asientos de regularización; las percepciones siempre van a
  revisión; con cientos de miles de partidas una página de consulta tarda algunos segundos.
