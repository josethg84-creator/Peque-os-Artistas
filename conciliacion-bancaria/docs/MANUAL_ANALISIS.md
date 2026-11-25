# Manual de uso — Motor de análisis de cuentas (fase 3)

## 1. Requisitos

El análisis trabaja sobre la información importada en el **Analizador contable** (fase 2):

| Información | Para qué se usa | ¿Obligatoria? |
|---|---|---|
| Libro diario (o mayor) | Movimientos, saldos, navegación, reglas | Sí |
| Saldos iniciales (periodo 00) o asiento de apertura | Saldo inicial del ejercicio | Recomendada; sin ella los saldos iniciales son **preliminares** |
| Plan de cuentas | Descripciones, naturaleza, cuentas sin movimiento, destinos | Recomendado |
| Centros de costo (con unidad de negocio) | Origen–destino, comparativos por CC y unidad | Recomendado |
| Tipos de cambio | Diferencia de cambio en cuentas en moneda extranjera | Opcional |
| CxC / CxP | Antigüedad con la cartera informada por el ERP | Opcional |

**Sin duplicar:** si un periodo tiene diario y mayor, se usa el diario; si hay saldos iniciales y
asiento de apertura en el diario, se usan los saldos iniciales. El sistema lo advierte en pantalla.

## 2. Contexto de análisis

Todas las pantallas comparten la barra **Ejercicio · Desde · Hasta** (se recuerda por empresa). El
rango 01–12 analiza el ejercicio completo; 13 incluye el cierre.

## 3. Dashboard de análisis

1. Elija el periodo y pulse **Ejecutar análisis**. El proceso corre en segundo plano con barra de
   progreso real y puede **cancelarse**.
2. Indicadores: cuentas analizadas, movimientos, cuentas con/sin observaciones, importe sujeto a
   revisión (sin superponer exposiciones), avance de revisión, saldos antiguos, saldos contrarios,
   diferencias origen–destino, variaciones significativas y papeles de trabajo.
3. Gráficos: evolución mensual por elemento, observaciones por riesgo, gastos por naturaleza y por
   centro de costo, origen vs destino, antigüedad y concentración por terceros. Cada gráfico tiene
   **Ver datos** con su tabla.
4. Si los datos cambian (nueva importación o anulación), el dashboard avisa que el análisis quedó
   desactualizado.

## 4. Explorador de cuentas

- Árbol elemento → cuenta → subcuenta → divisionaria → subdivisionaria → analítica. Cada nivel
  suma a sus subcuentas **una sola vez**; la cabecera muestra el **cuadre con el origen** (suma
  directa de las líneas = suma del árbol).
- Saldos con indicador **D** (deudor) / **A** (acreedor). Columnas configurables (**Columnas**).
- Las cuentas de orden (elemento 0) se muestran pero no integran los totales.
- Al hacer clic en una cuenta se abre el **panel lateral**: saldos, variación, perfil de análisis
  del elemento, evolución mensual, principales terceros, observaciones, exportación y papel de trabajo.

## 5. Navegación de movimientos (niveles 1 → 7)

Balance → cuenta → subcuenta → **tercero** → **documento** → **asiento** → **línea original**.
Las migas de pan conservan el contexto. En el nivel de movimientos se ve fecha, subdiario, asiento,
glosa, documento, RUC y razón social, moneda, tipo de cambio, debe, haber, **saldo acumulado**,
centro de costo, proyecto y archivo/fila de origen. Un clic en una línea abre el **asiento
completo con sus contrapartidas** y la **fila tal como venía en el archivo importado**.

> La línea original está disponible para lotes importados desde la fase 3 (el archivo se archiva
> al confirmar). Los lotes anteriores muestran un aviso.

## 6. Origen y destino

Compara el gasto destinable (prefijos configurados en *Reglas contables*) con el destino (clase 9 u
otro prefijo) y la cuenta 79; incluye provisiones aplicadas (48) y abonos a la 78. Vistas por
periodo, centro de costo, cuenta de destino, cuenta de origen y asientos a revisar (sin destino,
destino duplicado, línea de destino repetida).

**Reglas de distribución:** cuenta de origen + centro de costo / proyecto / unidad de negocio /
maquinaria → cuenta de destino con **porcentaje** y **vigencia**; también se puede **excluir** una
cuenta de la distribución. Una misma combinación no puede superar 100 %. Sin regla aplicable se
usa el destino del plan de cuentas y, en su defecto, el del centro de costo.

## 7. Antigüedad de saldos

Elija fecha de corte, base (**vencimiento** o **emisión**), fuente (**libros** o **cartera
informada por el ERP**) y cuentas. Tramos configurables (por defecto: no vencido, 1–30, 31–60,
61–90, 91–180, 181–365, más de 365). Un documento es **preliminar** si le faltan datos (sin número,
sin vencimiento, apertura sin detalle) o si tiene saldo contrario. **No se compensan documentos
distintos entre sí** (fase 4).

## 8. Comparativos

Mes vs mes anterior, mes vs mismo mes del año anterior y acumulado anual; por cuenta (a cualquier
nivel), centro de costo, proyecto, unidad de negocio, moneda o tercero. Muestra variación absoluta
y %, participación, promedio mensual, tendencia y concentración. Con base cero la variación % es
**N/A**; los periodos sin información o con solo mayor se advierten.

## 9. Observaciones

Filtros por análisis, riesgo, estado, regla, cuenta y texto. El panel muestra código y versión de
la regla, cuenta, importe, evidencia, explicación contable y recomendación, y permite registrar la
**revisión profesional** (estado, responsable y fundamento; confirmar o descartar exige comentario).
El estado, el responsable y los comentarios **se conservan** en los análisis siguientes mientras
la observación persista.

## 10. Reglas de análisis y excepciones

Edite cualquier regla (nueva versión en cada cambio), cree reglas propias de tipo *umbral* o de
cualquier tipo del catálogo, y ejecútelas **individualmente o por grupo**. Las **excepciones
autorizadas** (por regla, cuenta, tercero o documento, con motivo y vigencia) suprimen hallazgos y
quedan registradas. Catálogo completo en `docs/REGLAS_ANALISIS.md`.

## 11. Papeles de trabajo preliminares

Genérelos desde el explorador o desde **Papeles de trabajo**. Congelan los saldos del momento
(nueva versión con **Actualizar saldos**) e incluyen composición preliminar, observaciones
vinculadas, comentarios, documentos de sustento, conclusión, responsable, fecha de revisión y
adjuntos (con huella SHA-256).

Estados: Pendiente → En revisión → Observado → Subsanado → Revisado → Aprobado. Para *Revisado* o
*Aprobado* se exige conclusión; **la aprobación la hace una persona distinta del responsable**; un
papel aprobado queda bloqueado y reabrirlo exige motivo.

## 12. Exportaciones

Botones **Excel / PDF** en cada pantalla: balance analítico, análisis de cuenta, movimientos,
antigüedad, comparativo, gastos, ingresos (separa 78/79 como transferencias), origen–destino,
observaciones y papel de trabajo. Los Excel tienen referencias de empresa/periodo/usuario,
importes numéricos, filtros, encabezado fijo y totales.

## 13. Trazabilidad

Todo análisis, revisión, cambio de regla, excepción, papel y exportación queda en la bitácora del
módulo (`analysis_audit_logs`, endpoint `/api/analisis/auditoria`). El módulo **no modifica**
ningún asiento ni movimiento importado.
