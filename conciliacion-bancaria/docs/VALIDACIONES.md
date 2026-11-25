# Motor de validación contable — catálogo de observaciones

Generado a partir de `app/contable/observaciones.py` (fuente única). Cada observación muestra:
código, severidad, archivo, hoja, fila de origen, cuenta, asiento, documento, campo, valor
detectado, descripción y recomendación. Se pueden filtrar y exportar a CSV por lote.

## Severidades

| Severidad | Criterio | Efecto |
|---|---|---|
| **Crítico** | Descuadres en importaciones completas, archivos estructuralmente inválidos, importes no procesables | Bloquea la confirmación salvo que el usuario la fuerce con motivo (queda en auditoría). Un archivo sin columnas obligatorias (`EST001`) nunca se importa. |
| **Alto** | Cuentas inexistentes, posibles duplicidades, diferencias significativas | Se importa y queda observado. |
| **Medio** | Información complementaria incompleta, homologaciones pendientes (p. ej. centros de costo) | Se importa y queda observado. |
| **Informativo** | Recomendaciones, campos opcionales no informados | Solo informa. |

Algunas reglas ajustan la severidad según el contexto: `PD001` es crítico en importaciones
completas y alto en parciales; `FEC002` es informativo en el registro de compras (se admiten
comprobantes de periodos anteriores anotados dentro del plazo legal); `NAT001` es alto desde
el importe de materialidad configurado y medio por debajo.

## Criterios de diseño relevantes

- **Partida doble por asiento completo**: se agrupa por empresa · ejercicio · periodo ·
  subdiario · número de asiento. En el libro mayor solo se valida si el usuario indica que la
  importación es completa.
- **Documentos repetidos**: un comprobante con varias líneas en el mismo asiento es legítimo.
  `DUP001` solo se emite si la misma combinación documento + cuenta + lado + importe aparece en
  **asientos distintos**, y aun así es una *posible* duplicidad a confirmar.
- **Datos maestros opcionales**: si la empresa no cargó plan de cuentas, centros de costo o
  tipos de cambio, no se presume error: se emite una recomendación (`CTA000`, `CC000`).
- **Balance con niveles**: una fila es de resumen solo si sus importes coinciden con la suma
  de sus cuentas de detalle; una cuenta de título con movimiento propio no se descarta.
- **Clases 6, 7 y 9**: configurables por empresa (uso de clase 9, destino en el mismo asiento
  o al cierre del periodo, prefijos destinables y de destino, cuenta 79, exigencia de centro de
  costo, revisión de la 78 y reglas específicas como 60 → 20/61). El plan de cuentas puede
  indicar el destino de cada cuenta.

## Catálogo

| Código | Severidad por defecto | Observación | Recomendación |
|---|---|---|---|
| `EST001` | Crítico | Archivo estructuralmente inválido | Verifique que el archivo no esté dañado o protegido y que tenga las columnas obligatorias. |
| `EST002` | Informativo | Filas vacías omitidas | Ninguna acción requerida. |
| `EST003` | Informativo | Subtotales o totales identificados y excluidos | Confirme que las filas excluidas son totales del reporte y no movimientos. |
| `EST004` | Informativo | Campo opcional no informado | Si el ERP dispone de este dato, inclúyalo para enriquecer el análisis. |
| `EST005` | Medio | Columna homologada sin datos | Revise si la columna elegida es la correcta. |
| `EST006` | Medio | Valor con formato no reconocido | Corrija el valor en el origen o ajuste la homologación. |
| `IMP001` | Crítico | Importe no procesable | El valor no es numérico. Revise el separador decimal configurado o corrija el origen. |
| `IMP002` | Medio | Línea con debe y haber simultáneos | Separe la línea en dos o confirme que es correcto. |
| `IMP003` | Medio | Importe negativo en columna debe/haber | Suele indicar un extorno. Se trasladó al lado contrario; confirme el criterio. |
| `IMP004` | Medio | Línea con importe cero | Verifique si la línea debe existir. |
| `IMP005` | Alto | Indicador debe/haber no reconocido | Use D/H (o claves 40/50 en SAP). La línea se interpretó por el signo del importe. |
| `OBL001` | Alto | Registro sin información obligatoria | Complete el dato en el origen; la fila no se importa. |
| `FEC001` | Alto | Fecha inválida | Revise el formato de fecha configurado (dd/mm/aaaa, mm/dd/aaaa…). |
| `FEC002` | Alto | Fecha fuera del periodo seleccionado | Confirme el periodo de la importación o reclasifique el registro. |
| `FEC003` | Medio | Vencimiento anterior a la emisión | Corrija las fechas del comprobante. |
| `MON001` | Alto | Moneda no reconocida | Use códigos ISO (PEN, USD, EUR) o equivalentes (S/, US$, MN, ME). |
| `MON002` | Medio | Moneda no informada en línea con importes en moneda extranjera | Informe la moneda; se asumió USD para validar el tipo de cambio. |
| `TC001` | Alto | Conversión inconsistente (MN ≠ ME × TC) | Revise el tipo de cambio o los importes en moneda nacional/extranjera. |
| `TC002` | Alto | Tipo de cambio distinto al registrado para la fecha | Compare con el tipo de cambio publicado (SBS/SUNAT) y corrija si corresponde. |
| `TC003` | Alto | Tipo de cambio inválido o faltante | Informe un tipo de cambio mayor que cero. |
| `TC004` | Medio | Variación diaria atípica del tipo de cambio | Verifique el valor publicado para esa fecha. |
| `TC005` | Medio | Tipo de cambio compra mayor que venta | Verifique si las columnas están invertidas. |
| `PD001` | Crítico | Asiento descuadrado (moneda nacional) | El debe y el haber del asiento no son iguales. Revise líneas faltantes o importes. |
| `PD002` | Alto | Asiento descuadrado (moneda extranjera) | Puede deberse a redondeos o a líneas en otra moneda; revise el asiento. |
| `PD003` | Crítico | Totales generales descuadrados | La suma del debe y del haber de toda la importación no coincide. |
| `TOT001` | Alto | Diferencia entre los totales del archivo y la información procesada | Revise filas excluidas por errores o totales del reporte mal calculados. |
| `CTA000` | Informativo | No hay plan de cuentas cargado | Importe el plan de cuentas para validar existencia, estado y naturaleza de las cuentas. |
| `CTA001` | Alto | Cuenta inexistente en el plan de cuentas | Cree la cuenta en el plan o corrija el código en el origen. |
| `CTA002` | Alto | Cuenta contable inactiva | Reactive la cuenta o reclasifique el movimiento. |
| `CTA003` | Alto | Movimiento en cuenta no autorizada para registro | La cuenta es de título o está restringida: registre en una subcuenta de último nivel. |
| `CTA004` | Medio | Código de cuenta no válido según el PCGE | Los códigos deben ser numéricos y empezar en 1–9. |
| `CTA005` | Alto | Cuenta duplicada en el plan | Elimine la fila duplicada del archivo. |
| `CTA006` | Medio | Cuenta de destino configurada no existe en el plan | Corrija el amarre de destino. |
| `CC000` | Informativo | No hay maestro de centros de costo | Importe los centros de costo para validar los códigos utilizados. |
| `CC001` | Medio | Centro de costo inexistente (pendiente de homologación) | Registre el centro de costo o homologue el código. |
| `CC002` | Medio | Falta centro de costo en una cuenta que lo requiere | Asigne el centro de costo. |
| `DUP001` | Alto | Posible documento duplicado en el archivo | El mismo documento aparece en asientos distintos con igual cuenta e importe. No es necesariamente un error: confírmelo. |
| `DUP002` | Alto | Posible registro ya importado en otro lote | Verifique que no se esté importando dos veces el mismo periodo o documento. |
| `DUP003` | Alto | El archivo ya fue importado anteriormente | Confirme si desea importarlo otra vez. |
| `DUP004` | Alto | Código duplicado en el maestro | Deje un solo registro por código. |
| `TER001` | Medio | Documento de identidad con formato inválido | Verifique el RUC (11 dígitos y dígito verificador) o DNI (8 dígitos). |
| `TER002` | Medio | Tercero no registrado en el maestro | Registre el cliente o proveedor en el maestro. |
| `NAT001` | Alto | Saldo contrario a la naturaleza de la cuenta | Analice la cuenta: puede indicar errores de registro o reclasificaciones pendientes. |
| `SAL001` | Alto | Saldo inicial + movimientos ≠ saldo final | El balance no es aritméticamente consistente para la cuenta. |
| `SAL002` | Alto | Movimientos del balance distintos al libro diario importado | Compare el balance con el diario del mismo periodo. |
| `SAL003` | Alto | Saldo inicial distinto a los saldos iniciales importados | Verifique la apertura del ejercicio. |
| `REG001` | Alto | Base + impuestos + no gravado ≠ total | Revise los importes del comprobante. |
| `REG002` | Medio | IGV no corresponde a la tasa vigente (18 % o 10 % MYPE) | Revise la base imponible, la tasa o si hay operaciones no gravadas. |
| `CAR001` | Alto | Saldo pendiente mayor que el importe original | Revise pagos parciales o notas de crédito. |
| `DES001` | Alto | Gasto por naturaleza sin cuenta de destino | Registre el destino (clase 9 u otro configurado) y su contrapartida en la cuenta 79. |
| `DES002` | Alto | Posible duplicidad de gastos en estados financieros (clase 9 ≠ cuenta 79) | Lo cargado a destino debe abonarse en la 79 por el mismo importe. |
| `DES003` | Alto | Diferencia entre gasto de origen y gasto de destino | El gasto por naturaleza destinable no coincide con lo distribuido a destino. |
| `DES004` | Medio | Destino sin centro de costo | Asigne centro de costo a las cuentas de destino. |
| `DES005` | Medio | Posible inconsistencia en cuentas de destino | La cuenta de destino usada no es la configurada para la cuenta de origen. |
| `DES006` | Medio | Tratamiento de la cuenta 78 a revisar | Al aplicar una provisión (48) se espera el abono a la 78 Cargas cubiertas por provisiones. |
| `DES007` | Informativo | Reglas analíticas no aplicadas | Configure las reglas de destino de la empresa si corresponde. |
| `REC001` | Informativo | Recomendación |  |
