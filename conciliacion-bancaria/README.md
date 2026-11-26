# Analizador Contable Inteligente

**Accounting Intelligence 360.** Plataforma de análisis contable para empresas peruanas (PCGE):
importación, homologación y validación de información de cualquier ERP, análisis de cuentas
(saldos, navegación hasta el asiento, antigüedad, origen–destino, reglas, papeles de trabajo) y
conciliación bancaria de la **cuenta 10**.

> Módulo independiente dentro de este repositorio. No comparte código con la app Flutter.

**Estado: fases 1 a 5 completadas.** Plan en [`docs/PLAN.md`](docs/PLAN.md) · validaciones de
importación en [`docs/VALIDACIONES.md`](docs/VALIDACIONES.md) · reglas de análisis en
[`docs/REGLAS_ANALISIS.md`](docs/REGLAS_ANALISIS.md) · **manual de uso del análisis** en
[`docs/MANUAL_ANALISIS.md`](docs/MANUAL_ANALISIS.md) · **manual de compensación de partidas** en
[`docs/MANUAL_COMPENSACION.md`](docs/MANUAL_COMPENSACION.md) · **manual de anexos contables** en
[`docs/MANUAL_ANEXOS.md`](docs/MANUAL_ANEXOS.md).

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
migraciones/   Alembic (0001 fase 1 · 0002 fase 2 · 0003 fase 3 · 0004 fase 4 · 0005 fase 5)
tests/         148 pruebas (incluye 22 de anexos con los 21 casos obligatorios y tres de volumen)
```

Importes en `Decimal` / `NUMERIC(18,2)`; nunca `float`.

## Limitaciones conocidas de esta fase

- Excel 97-2003 (`.xls`) no se lee: se pide guardarlo como `.xlsx` o `.csv`.
- PDF escaneados (imagen) no se procesan; se requiere PDF con texto.
- Los formatos de cada banco cambian con el tiempo; los sinónimos cubren los
  encabezados habituales y el mapeo manual cubre el resto. Conviene validar con
  exportaciones reales de cada banco (en la fase 6 se guardarán plantillas de mapeo).
- El usuario se toma de la cabecera `X-Usuario` (campo «Usuario» de la interfaz);
  la autenticación real llega en la fase 6.
- Los trabajos en segundo plano corren en hilos del mismo proceso (un solo servidor); para
  varios nodos se usará una cola en la fase 6.
- La línea original del archivo (nivel 7) está disponible para lotes importados desde la fase 3.
- Los sinónimos de ERP se basan en encabezados habituales, no en exportaciones verificadas de
  cada versión: valide con archivos reales y guarde plantillas.
- Los maestros (plan, terceros, centros, TC) se actualizan registro a registro y no se anulan
  por lote.
- Anexos (fase 5): sin conciliaciones externas (fase 6); los registros auxiliares se importan (no hay
  integración en línea con el ERP); el libro Excel masivo no lleva logotipo.
- Compensación (fase 4): no se generan asientos de regularización; las percepciones siempre van a
  revisión; con cientos de miles de partidas una página de consulta tarda algunos segundos.
