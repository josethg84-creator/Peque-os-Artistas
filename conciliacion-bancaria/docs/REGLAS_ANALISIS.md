# Reglas del motor de análisis de cuentas (fase 3)

Generado a partir de `app/analisis/reglas.py`. Todas las reglas se editan desde **Reglas de análisis**
sin tocar código: alcance (prefijos o rango de cuentas), condición, operador, valores, importe
mínimo, tolerancia %, riesgo, vigencia, estado, parámetros adicionales (JSON) y excepciones
autorizadas. Cada edición crea una nueva **versión**; cada análisis guarda la versión y los
parámetros usados, y cada hallazgo indica la versión de la regla que lo generó.

Los hallazgos son **posibles incidencias**: nacen en estado *Pendiente de revisión* y solo un
profesional los confirma, descarta (con fundamento obligatorio) o marca como subsanados.

## Reglas iniciales de cada empresa

| Código | Regla | Grupo | Riesgo | Parámetros | Qué detecta |
|---|---|---|---|---|---|
| `NAT-01` | Saldo contrario a la naturaleza | SALDOS | Medio | mín. 1.00 | Cuentas cuyo saldo final es opuesto a su naturaleza (deudora/acreedora). |
| `SOB-10` | Saldo acreedor en caja y bancos | ELEMENTO 1 | Alto | cuentas 10 | Cuentas del elemento 10 con saldo acreedor. |
| `TER-01` | Saldo contrario por tercero | ELEMENTO 1 | Medio | cuentas 12,13,14,16,17,42,43,44,46,47; mín. 1.00 | Clientes con saldo acreedor o proveedores con saldo deudor. |
| `ANT-01` | Saldo antiguo | ANTIGÜEDAD | Medio | cuentas 12,13,14,16,17,42,43,44,46,47; valor 365; base: VENCIMIENTO | Documentos con saldo pendiente de antigüedad mayor a N días. |
| `C23-01` | Costos acumulados en la cuenta 23 | ELEMENTO 2 | Alto | cuentas 23; valor 180; dias_inactividad: 90 | Costos de servicios/productos en proceso antiguos o sin actividad reciente. |
| `DEP-01` | Depreciación acumulada mayor al costo | ELEMENTO 3 | Alto | cuentas 32,33,34,35; depreciacion: 39 | Depreciación/amortización acumulada que supera el costo del activo. |
| `PAT-01` | Movimiento patrimonial | ELEMENTO 5 | Informativo | cuentas 50,52,57,58 | Movimientos en capital, capital adicional, excedente de revaluación o reservas. |
| `DUP-01` | Documento potencialmente duplicado | DOCUMENTOS | Alto | — | El mismo documento con igual cuenta, lado e importe en asientos distintos. |
| `EXT-01` | Movimiento extraordinario | MOVIMIENTOS | Medio | valor 3; mín. 1000.00; min_lineas: 10 | Líneas cuyo importe excede la media de la cuenta en N desviaciones estándar. |
| `SMV-01` | Cuenta con saldo y sin movimiento | SALDOS | Bajo | valor 3; mín. 1.00 | Cuentas con saldo que no registran movimientos en los últimos N meses. |
| `VAR-01` | Variación significativa | VARIACIONES | Medio | mín. 5000.00; tol. 30 %; nivel: 2 | Variación del saldo respecto del periodo anterior mayor al umbral. |
| `STE-01` | Movimiento sin tercero | DOCUMENTOS | Medio | cuentas 12,13,14,16,17,42,43,44,46,47 | Líneas sin RUC o identificación del tercero en cuentas que lo requieren. |
| `SCC-01` | Gasto sin centro de costo | GASTOS | Bajo | cuentas 62,63,64,65,66,67,68; solo_si_plan_lo_exige: True | Líneas sin centro de costo en cuentas que lo exigen. |
| `FPE-01` | Movimiento fuera del periodo | MOVIMIENTOS | Medio | — | Fecha contable que no corresponde al periodo del lote o de la línea. |
| `CLA-01` | Posible error de clasificación | GASTOS | Medio | cuentas 6; valor 2000; palabras clave | Gastos de importe relevante cuya glosa sugiere un activo. |
| `CON-01` | Concentración en un tercero | TERCEROS | Bajo | cuentas 12,42,60,63,70; mín. 10000.00; tol. 60 %; min_terceros: 3 | Un tercero concentra más del % indicado del movimiento de la cuenta. |
| `OD-01` | Diferencia origen–destino | ORIGEN-DESTINO | Alto | mín. 1.00 | Diferencias entre gasto por naturaleza destinable, destino (clase 9) y cuenta 79. |
| `RES-01` | Movimiento en cuenta restringida | MOVIMIENTOS | Alto | — | Movimientos en cuentas de título, sin movimiento o restringidas. |
| `ORD-01` | Cuentas de orden mezcladas | ELEMENTO 0 | Medio | cuentas 0 | Asientos que combinan cuentas de orden con cuentas patrimoniales o de resultados. |
| `INT-01` | Saldos intermediarios fuera del cierre | ELEMENTO 8 | Informativo | cuentas 8 | Cuentas del elemento 8 con saldo en periodos distintos del cierre. |
| `TC-01` | Posible diferencia de cambio no registrada | MONEDA EXTRANJERA | Medio | mín. 10.00 | Saldos en moneda extranjera no actualizados al tipo de cambio de cierre. |

## Tipos de regla (evaluadores) y fundamento contable

| Tipo | Nombre | Explicación contable | Recomendación |
|---|---|---|---|
| `SALDO_CONTRARIO` | Saldo contrario a la naturaleza | Un saldo contrario puede reflejar errores de imputación, cobros o pagos no aplicados, anticipos o reclasificaciones pendientes para la presentación de los estados financieros. | Analice la composición del saldo y, si corresponde, reclasifique para la presentación. |
| `MOVIMIENTO_EXTRAORDINARIO` | Movimiento extraordinario | Un importe atípico respecto del comportamiento habitual de la cuenta merece verificarse con su sustento. | Revise el documento de sustento y la aprobación de la operación. |
| `SIN_MOVIMIENTO` | Cuenta con saldo y sin movimiento | Un saldo inmovilizado puede corresponder a partidas antiguas pendientes de depurar o castigar. | Confirme la vigencia del saldo (confirmaciones, conciliaciones) o evalúe su depuración. |
| `SALDO_ANTIGUO` | Saldo antiguo | Las partidas antiguas pueden requerir estimación de cobranza dudosa (cuentas por cobrar) o depuración. | Evalúe la recuperabilidad o exigibilidad del documento y su tratamiento contable y tributario. |
| `DOCUMENTO_DUPLICADO` | Documento potencialmente duplicado | Un comprobante registrado dos veces sobreestima gastos, activos o pasivos. Un documento con varias líneas en el mismo asiento es legítimo y no se observa. | Verifique si se trata del mismo comprobante y, de ser así, extorne el registro duplicado. |
| `VARIACION_SIGNIFICATIVA` | Variación significativa | Variaciones fuera de lo esperado deben explicarse con hechos del negocio (análisis de fluctuaciones). | Documente la causa de la variación. |
| `SIN_TERCERO` | Movimiento sin tercero | Sin tercero no es posible analizar la composición, la antigüedad ni confirmar el saldo. | Complete el auxiliar (anexo) en el ERP. |
| `SIN_CENTRO_COSTO` | Gasto sin centro de costo | Sin centro de costo el gasto no puede distribuirse ni analizarse por área. | Asigne el centro de costo según la política de la empresa. |
| `FUERA_DE_PERIODO` | Movimiento fuera del periodo | Los registros fuera de periodo afectan el corte contable (devengo). | Verifique la fecha y el periodo de registro. |
| `CLASIFICACION` | Posible error de clasificación | Desembolsos que generan beneficios futuros podrían corresponder a activo inmovilizado (NIC 16 / NIC 38). | Evalúe si el desembolso cumple los criterios de reconocimiento como activo. |
| `CONCENTRACION_TERCERO` | Concentración en un tercero | La concentración aumenta el riesgo de dependencia y puede requerir confirmación de saldos. | Considere solicitar confirmación de saldos y revisar condiciones contractuales. |
| `ORIGEN_DESTINO` | Diferencia origen–destino | Si el destino no coincide con la 79 el gasto podría presentarse duplicado; si el gasto destinable no tiene destino, el estado de resultados por función queda incompleto. | Revise los asientos de destino y las reglas de distribución vigentes. |
| `CUENTA_RESTRINGIDA` | Movimiento en cuenta restringida | Las cuentas de título o restringidas no deberían recibir registros directos. | Reclasifique a la subcuenta de último nivel que corresponda. |
| `SOBREGIRO` | Saldo acreedor en caja y bancos | Un saldo acreedor en bancos suele ser un sobregiro o cheques girados no cobrados; para la presentación se reclasifica a obligaciones financieras (45). | Concilie la cuenta bancaria y evalúe la reclasificación para la presentación. |
| `SALDO_CONTRARIO_TERCERO` | Saldo contrario por tercero | Puede tratarse de anticipos, cobros/pagos no aplicados o pagos duplicados. No se compensa automáticamente con otros documentos (fase 4). | Identifique el origen del saldo y aplíquelo o reclasifíquelo como anticipo. |
| `COSTO_EN_PROCESO` | Costos acumulados en la cuenta 23 | La falta de facturación no justifica por sí sola mantener costos como activo: debe evaluarse la situación del servicio (avance, culminación, obligación de desempeño, NIIF 15 / NIC 2) y transferirse al costo cuando corresponda. | Evalúe el estado del contrato/proyecto y la transferencia de costos a resultados o a productos terminados. |
| `DEPRECIACION_EXCEDE` | Depreciación acumulada mayor al costo | La depreciación acumulada no puede exceder el costo depreciable del activo. | Revise la vida útil, los retiros y la correspondencia entre activo y depreciación. |
| `CUENTAS_ORDEN` | Cuentas de orden mezcladas | Las cuentas de orden registran compromisos y contingencias y no deben afectar los estados financieros. | Registre las cuentas de orden en asientos propios y con su contracuenta de orden. |
| `SALDO_INTERMEDIARIO` | Saldos intermediarios fuera del cierre | Los saldos intermediarios se determinan en el cierre según el procedimiento de la empresa. | Verifique el procedimiento de cierre aplicado. |
| `MOVIMIENTO_PATRIMONIAL` | Movimiento patrimonial | Los movimientos patrimoniales son inusuales y requieren acuerdo societario o sustento técnico. | Verifique el acta de junta, la escritura o el sustento de la operación. |
| `DIFERENCIA_CAMBIO` | Posible diferencia de cambio no registrada | Las partidas monetarias en moneda extranjera se expresan al tipo de cambio de cierre (NIC 21); activos al tipo de compra y pasivos al de venta según la práctica tributaria peruana. | Calcule y registre la diferencia de cambio del periodo. |
| `UMBRAL` | Regla de umbral personalizada | Regla definida por la empresa. | Revise la cuenta según el criterio definido. |

## Regla de umbral personalizada (`UMBRAL`)

Condiciones: `SALDO_FINAL`, `SALDO_DEUDOR`, `SALDO_ACREEDOR`, `MOVIMIENTO_DEBE`, `MOVIMIENTO_HABER`,
`MOVIMIENTO_NETO`, `VARIACION`, `VARIACION_PCT`, `CANTIDAD_MOVIMIENTOS`, `CANTIDAD_TERCEROS`.
Operadores: `>`, `>=`, `<`, `<=`, `=`, `!=`, `ENTRE`, `FUERA` (los dos últimos usan *valor* y *valor 2*).
Ejemplo: «capital con saldo acreedor mayor a 9 500» → cuentas `50`, condición `SALDO_ACREEDOR`, operador `>`, valor `9500`.

## Exposición sin duplicar

Varios hallazgos pueden referirse al mismo importe (un documento antiguo que además es saldo
contrario). El *importe sujeto a revisión* se calcula por cuenta de 2 dígitos como el máximo entre
(a) la suma, por clave de exposición distinta (línea, documento o tercero), del mayor importe
observado y (b) el mayor hallazgo sobre el saldo total de la cuenta. Así nunca supera la suma
simple de importes ni cuenta dos veces la misma partida.
