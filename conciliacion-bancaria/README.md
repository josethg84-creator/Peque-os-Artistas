# Analizador Contable Inteligente

Plataforma de análisis contable para empresas peruanas (PCGE): importación, homologación y
validación de información de cualquier ERP, y conciliación bancaria de la **cuenta 10**.

> Módulo independiente dentro de este repositorio. No comparte código con la app Flutter.

**Estado: fases 1 y 2 de 7 completadas.** Plan completo en [`docs/PLAN.md`](docs/PLAN.md);
catálogo de validaciones en [`docs/VALIDACIONES.md`](docs/VALIDACIONES.md).

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
migraciones/   Alembic (0001 fase 1 · 0002 fase 2)
tests/         85 pruebas (normalización, lectores, API end-to-end, analizador contable)
```

Importes en `Decimal` / `NUMERIC(18,2)`; nunca `float`.

## Limitaciones conocidas de esta fase

- Excel 97-2003 (`.xls`) no se lee: se pide guardarlo como `.xlsx` o `.csv`.
- PDF escaneados (imagen) no se procesan; se requiere PDF con texto.
- Los formatos de cada banco cambian con el tiempo; los sinónimos cubren los
  encabezados habituales y el mapeo manual cubre el resto. Conviene validar con
  exportaciones reales de cada banco (en la fase 7 se guardarán plantillas de mapeo).
- El usuario se toma de la cabecera `X-Usuario` (campo «Usuario» de la interfaz);
  la autenticación real llega en la fase 7.
- Los trabajos en segundo plano corren en hilos del mismo proceso (un solo servidor); para
  varios nodos se usará una cola en la fase 7.
- Los sinónimos de ERP se basan en encabezados habituales, no en exportaciones verificadas de
  cada versión: valide con archivos reales y guarde plantillas.
- Los maestros (plan, terceros, centros, TC) se actualizan registro a registro y no se anulan
  por lote.
