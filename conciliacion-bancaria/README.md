# Conciliación Bancaria Inteligente

Sistema de conciliación bancaria para empresas peruanas: estados de cuenta vs.
libro mayor de la **cuenta 10 — Efectivo y equivalentes de efectivo** (PCGE).

> Módulo independiente dentro de este repositorio. No comparte código con la app Flutter.

**Estado: Fase 1 de 6 completada** — datos maestros, importación y control de
duplicados. El plan completo por fases está en [`docs/PLAN.md`](docs/PLAN.md).

## Puesta en marcha

```bash
cd conciliacion-bancaria
pip install -r requirements.txt
python scripts/generar_ejemplos.py      # archivos de prueba en ./ejemplos
uvicorn app.main:app --reload
```

- Interfaz web: http://localhost:8000
- API (OpenAPI/Swagger): http://localhost:8000/api/docs
- Base de datos: SQLite en `./data/conciliacion.db`. Para PostgreSQL defina
  `DATABASE_URL=postgresql+psycopg://usuario:clave@host/bd` (requiere `psycopg`).

Pruebas: `python -m pytest -q`

### Recorrido de demostración

1. **Empresas** → registrar `20609876540` · Comercial Andina S.A.C. (RUC ficticio).
2. **Cuentas bancarias** → BCP PEN `104101`, BBVA USD `104102`, Interbank PEN `104103`.
3. **Importar archivos** → los 3 estados de cuenta de `ejemplos/` y el libro mayor
   (el mismo Excel sirve para las tres subcuentas: se filtra por subcuenta).
4. **Movimientos** → filtrar «Solo posibles duplicados» y resolver la fila repetida del BCP.

## Qué incluye la fase 1

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
| Clasificación previa | ITF, comisión, interés, retención, depósito, transferencia, cheque, pago, retiro (base de la fase 3) |
| Trazabilidad | Historial de importaciones con anulación motivada (sin borrado físico) y bitácora de auditoría con antes/después |

Convención de signos: **+** ingresa dinero (abono en banco / debe en la 10), **−** sale (cargo / haber).

## Arquitectura

```
app/
  core/        configuración, BD, auditoría, utilidades (RUC, redondeo)
  models/      SQLAlchemy 2: maestros, importaciones, movimientos, auditoría
  schemas/     Pydantic v2 (contratos de la API)
  importers/   lectores (CSV/XLSX/PDF), columnas, normalización, analizador
  services/    importación y duplicados, catálogos
  api/         routers FastAPI
  static/      interfaz web (HTML/CSS/JS sin build)
tests/         69 pruebas (normalización, lectores, API end-to-end)
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
- El esquema se crea con `create_all`; las migraciones (Alembic) llegan en la fase 6.
