# Fase 7 — Auditor contable inteligente 360

> **Aviso.** El auditor es una herramienta de apoyo para el contador y el auditor. Trabaja con la información
> importada y con reglas automatizadas. **No emite dictámenes de auditoría independiente, no garantiza el
> cumplimiento normativo, no declara fraude y no modifica asientos.** Todo hallazgo es *potencial* hasta que un
> profesional lo revisa y confirma.

## 1. Resumen

El módulo **Auditor contable 360** evalúa la integridad, consistencia, razonabilidad y trazabilidad de la información
contable de las fases 1 a 6. No duplica su lógica: la reutiliza.

| Fuente reutilizada | Uso en la auditoría |
|---|---|
| Fase 2 (diario, mayor, balance, maestros) | Población de líneas y asientos; nuevos campos opcionales del ERP: usuario y fecha de registro, origen del asiento |
| Fase 3 (`preparar_contexto`, 22 evaluadores, destino, antigüedad) | Reglas de análisis como procedimientos de auditoría, origen–destino 6/79/78/9 |
| Fase 4 (partidas abiertas, roles) | Saldos pendientes de CxC/CxP y aplicaciones; perfiles de usuario |
| Fase 5 (registros auxiliares, anexos, estilos de exportación) | Activos, servicios en proceso, contratos, seguros; cruce anexo–balance |
| Fase 6 (conciliaciones) | Diferencias guardadas o conciliación en memoria (bancaria, compras, ventas, planilla, activos…) |

Cada hallazgo lleva **evidencia** (líneas, registros y cálculos), **explicación** (condición, criterio, causa,
efecto), **impacto** y **recomendación**.

## 2. Arquitectura

```
app/auditoria/
  base.py           Contexto perezoso (líneas, asientos, plan, registros, conciliaciones en memoria) y resultado Res
  r_integridad.py   Integridad (INT) y análisis de asientos (ASI) con factores combinados
  r_duplicados.py   Duplicidades exactas y aproximadas (DUP)
  r_cuentas.py      CxC, CxP, tesorería, gastos, ingresos y devengos
  r_especiales.py   Origen–destino, parametrización del ERP, servicios, activos, inventarios, planillas
  r_tributaria.py   Revisión tributaria preventiva (reglas normativas validables)
  estadistica.py    Atípicos (IQR), frecuencias, redondos, cerca de límites, Benford (opcional)
  configurables.py  Reglas sin código: campos en lista blanca, operadores, Y/O anidados
  catalogo.py       18 categorías, 167 reglas, siembra idempotente
  riesgo.py         Matriz 5×5, materialidad, factores, bitácora encadenada por hash
  motor.py          Ejecución (completa, módulo, cuenta, reglas), incremental, consolidación y reincidencias
  servicio.py       Permisos, encargos, reglas, estados de hallazgos, planes, regularización (bandeja)
  papeles.py        Muestras reproducibles y papeles de trabajo
  informes.py       6 informes de 16 secciones y 12 exportaciones (Excel y PDF)
  consultas.py      Listados, tablero, detalle, importación de parametrización del ERP
app/api/auditoria.py   API REST /api/auditoria360
app/static/app_auditoria.js   11 pantallas
migraciones/versions/0007_fase_7_auditor_contable.py
```

**Flujo de una ejecución:**

1. El motor arma la población del alcance del encargo: cuentas, centros de costo, proyectos, unidades, módulos y reglas.
2. Antes de evaluar, aplica cuatro filtros a cada regla:
   - `FUERA_DE_VIGENCIA`
   - `NO_VALIDADA` (normativas sin validar)
   - `REUTILIZADA` (mismos datos, regla y materialidad)
   - `PENDIENTE_EVALUACION` (faltan parámetros)
3. Ejecuta cada regla. El error de una regla queda como `ERROR` y no detiene las demás.
4. Consolida los resultados:
   - **Huella única** (sha256 de empresa + clave del hecho): un mismo hecho que detectan varias reglas se registra una sola vez y no se duplica.
   - **Reincidencias**: un hallazgo subsanado que vuelve a aparecer se reabre con su historial.
   - **Grupos de exposición**: la exposición de hallazgos superpuestos se cuenta una sola vez (máximo del grupo).
   - Un hallazgo que ya no se reproduce queda `vigente = false` con nota; no se borra.
5. La consolidación corre en un *savepoint*. La ejecución es asíncrona, con barra de progreso y cancelación, y registra el tiempo de cada regla.

## 3. Base de datos (migración 0007)

**23 tablas**:

| Tabla | Contenido |
|---|---|
| `audit_engagements` | Encargos |
| `audit_scopes` | Alcance |
| `audit_rule_categories` | Categorías de reglas |
| `audit_rules` | Reglas, con campos normativos y estado de validación |
| `audit_rule_versions` | Versiones de cada regla |
| `audit_runs` | Ejecuciones, con instantánea de reglas y materialidad y versión de datos |
| `audit_rule_results` | Resultado por regla, población, método y huella de entrada |
| `audit_findings` | Hallazgos |
| `audit_finding_evidence` | Evidencias |
| `audit_finding_groups` | Grupos de exposición |
| `audit_risk_matrix` | Matriz de riesgos |
| `audit_materiality_settings` | Materialidad |
| `audit_samples` / `audit_sample_items` | Muestras y sus elementos |
| `audit_workpapers` | Papeles de trabajo |
| `audit_action_plans` | Planes de acción |
| `audit_assignments` | Asignaciones |
| `audit_reviews` | Historial de estados y comentarios |
| `audit_approvals` | Aprobaciones |
| `audit_reports` / `audit_report_versions` | Informes y sus versiones con hash |
| `audit_event_logs` | Bitácora |
| `audit_configurations` | Parametrización del ERP aprobada o utilizada |

**Otros cambios de la migración:**

- Tres columnas opcionales en `lineas_diario`: `usuario_registro`, `fecha_registro` y `origen_asiento`.
- Dos roles nuevos: `AUDITOR_EXTERNO` y `GERENCIA`.

**Integridad y aislamiento:**

- Todas las tablas llevan `empresa_id`, con índices por empresa, encargo, estado, riesgo y huella.
- Una restricción única impide hallazgos repetidos.
- `lock_version` da concurrencia optimista; un conflicto devuelve 409.
- `audit_event_logs` está protegida con disparadores contra UPDATE y DELETE (SQLite y PostgreSQL) y encadenada por hash. `GET /bitacora` verifica la cadena.

La migración se probó con `upgrade`, `alembic check`, `downgrade` y un nuevo `upgrade`.

## 4. Catálogo de riesgos

- **Matriz 5×5 por defecto** (filas: impacto 1→5; columnas: probabilidad 1→5). El supervisor puede editarla; cada edición queda versionada.

| Impacto \ Prob. | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 5 | MEDIO | ALTO | ALTO | CRÍTICO | CRÍTICO |
| 4 | BAJO | MEDIO | ALTO | ALTO | CRÍTICO |
| 3 | BAJO | BAJO | MEDIO | MEDIO | ALTO |
| 2 | INFORMATIVO | BAJO | BAJO | MEDIO | MEDIO |
| 1 | INFORMATIVO | INFORMATIVO | BAJO | BAJO | BAJO |

- **Impacto.**
  - Con materialidad aprobada, el importe se compara con los umbrales: global → 5, ejecución → 4, mitad de la ejecución → 3, sobre el umbral insignificante → 2, por debajo → 1.
  - Sin materialidad, se usa el riesgo base de la regla.
  - Los hallazgos **cualitativos** (tributarios, estructurales, de datos personales o de control) tienen impacto mínimo 3. Un importe pequeño no los excluye.
- **Probabilidad.** Parte de la probabilidad de la regla y se ajusta así:
  - reincidencia: +1
  - evidencia parcial o insuficiente: −1
  - controles efectivos: −1; inefectivos: +1
- **Ajuste manual.** El auditor puede cambiar el nivel con una justificación de al menos 15 caracteres. Se guardan el usuario y el motivo.
- **Naturaleza de la puntuación.** Es una **priorización interna**, no una probabilidad estadística validada.
- **Materialidad.**
  - Base: `INGRESOS`, `ACTIVOS`, `PATRIMONIO`, `RESULTADO_ANTES_IMPUESTOS`, `GASTOS` u `OTRA`.
  - Porcentajes: global, ejecución y claramente insignificante.
  - **No hay porcentajes por defecto**: los define el responsable y los aprueba otro usuario.
  - Los hallazgos bajo el umbral insignificante siguen visibles si son de naturaleza relevante.

## 5. Hallazgos: tipos, estados y regularización

- **Tipos:** `POTENCIAL`, `CONFIRMADO`, `FALSO_POSITIVO`, `JUSTIFICADO` y `SUBSANADO`.
- **Estados:**
  - Detectado, Pendiente de revisión, En análisis
  - Confirmado, Justificado, Pendiente de regularización, En subsanación, Subsanado
  - Verificado, Cerrado, Reabierto
- **Controles de cada transición:**
  - Quien ejecutó la auditoría no confirma, no justifica y no marca falsos positivos (separación de funciones).
  - Un hallazgo con evidencia *insuficiente* necesita una evidencia adjunta por un usuario antes de confirmarse.
  - Falso positivo, justificación, reapertura y cierre exigen una justificación de al menos 15 caracteres.
  - Pasar a *En subsanación* exige un plan de acción.
  - Verifica un usuario distinto del que subsanó, y cierra uno distinto del que verificó.
  - Un hallazgo confirmado no se cierra sin justificación y evidencia de revisión.
- **Historial:** queda completo en `audit_reviews` y en la bitácora, y nunca se elimina.
- **Regularización:** la fase 8 aún no está desarrollada.
  - Los hallazgos confirmados se clasifican en una de estas categorías: `REQUIERE_AJUSTE`, `REQUIERE_RECLASIFICACION`, `REQUIERE_DOCUMENTACION`, `REQUIERE_PARAMETRIZACION`, `REQUIERE_CONCILIACION`, `REQUIERE_EVALUACION_TRIBUTARIA`, `REQUIERE_EVALUACION_LEGAL` o `NO_REQUIERE_AJUSTE`.
  - Pueden enviarse a la **bandeja de regularización pendiente**.
  - **No se genera ningún asiento.**

## 6. Seguridad

| Permiso | Roles |
|---|---|
| Consultar | todos, incluidos `AUDITOR_EXTERNO` (solo con asignación vigente y dentro de su plazo) y `GERENCIA` |
| Crear encargos / ejecutar | ADMINISTRADOR, SUPERVISOR, AUDITOR, CONTADOR (ejecutar también ANALISTA) |
| Diseñar reglas · materialidad | ADMINISTRADOR, SUPERVISOR, AUDITOR |
| Validar reglas normativas · aprobar | ADMINISTRADOR, SUPERVISOR (un usuario distinto del creador) |
| Revisar hallazgos | ADMINISTRADOR, SUPERVISOR, AUDITOR, AUDITOR_EXTERNO |
| Datos personales (planillas) | ADMINISTRADOR, SUPERVISOR, AUDITOR, PLANILLAS; el resto ve los datos enmascarados |
| Evidencias confidenciales | ADMINISTRADOR, SUPERVISOR, AUDITOR |

- La bitácora es encadenada e inmutable.
- Un usuario de una empresa no ve encargos, hallazgos ni evidencias de otra.
- Las evidencias se guardan con hash SHA-256.
- No se exponen credenciales.

## 7. Rendimiento (mediciones reales con datos sintéticos)

**Entorno de medición:**

- Máquina: 4 núcleos y 16 GB de RAM, con SQLite.
- Comando: `python scripts/benchmark_auditoria.py N`.
- Datos: asientos de dos líneas (gasto clase 6 contra 4212, con comprobante y tercero), más excepciones sembradas (duplicados y descuadres).
- Alcance: auditoría completa de las 167 reglas.
- La re-ejecución incremental se hace sin cambios de datos.

| Movimientos | Inserción | Auditoría completa | Re-ejecución incremental | Memoria máx. | Hallazgos |
|---|---|---|---|---|---|
| 100 000 | 4,4 s | 19,8 s | 0,3 s | 609 MB | 7 |
| 500 000 | 23,0 s | 107,5 s | 0,3 s | 2 679 MB | 17 |
| 1 000 000 | 45,4 s | 214,2 s | 0,2 s | 5 269 MB | 29 |

Estados de reglas en 500 000 y 1 000 000 movimientos:

| Estado | Reglas | Motivo |
|---|---|---|
| SIN_EXCEPCIONES | 105 | — |
| SIN_DATOS | 53 | El conjunto sintético no trae registros auxiliares, bancos ni planillas |
| CON_EXCEPCIONES | 4 | — |
| NO_VALIDADA | 5 | Reglas tributarias normativas pendientes de validación |

**Reglas más lentas en 1 000 000 de movimientos:**

| Regla | Tiempo |
|---|---|
| ACT-03 | 36,0 s (incluye cargar el contexto de la fase 3 que luego comparten las demás) |
| CXP-08 | 27,0 s |
| CXP-02 | 18,2 s |
| CXP-10 | 16,8 s |
| CXP-01 | 15,8 s |

**Prueba automatizada** `test_27`: 100 000 movimientos importados por la API.

**Limitaciones de rendimiento:**

- El tiempo crece de forma casi lineal.
- La memoria también crece: en 1 M se usaron unos 5,3 GB, porque la población se carga en memoria.
- Para volúmenes mayores se recomienda auditar por módulo, cuenta o periodo, o usar PostgreSQL con más memoria.

## 8. Manual de usuario

1. **Configuración.** En *Materialidad y configuración*:
   - Defina la base y los porcentajes, con su justificación; otro usuario los aprueba.
   - Si existe, importe la parametrización aprobada del ERP: plan, rubros y distribución, con sinónimos de columnas para SAP, Proficont, Starsoft y CONCAR.
2. **Encargo.** En *Centro de ejecución*, pulse **Nuevo encargo**:
   - Indique tipo, fecha de corte, responsable y recurrencia.
   - Defina el alcance: módulos, cuentas, centros de costo, proyectos, unidades y reglas.
3. **Ejecución.** Elija una de estas opciones:
   - **Auditoría completa**, **Ejecutar módulo**, **Ejecutar cuenta** o **Ejecutar reglas**.
   - La re-ejecución reutiliza las reglas cuyos datos no cambiaron; marque *recalcular todo* para forzar el cálculo.
   - El botón *Reglas* de cada ejecución muestra el estado, la población, el método y el tiempo de cada regla.
4. **Revisión de hallazgos.** En *Explorador de hallazgos*:
   - Filtre por módulo, riesgo, estado, tipo, cuenta, texto, vencidos o bandeja.
   - Abra un hallazgo para ver condición, criterio, causa, efecto, impacto, recomendación y evidencias.
   - **Ver asiento original** abre el asiento completo de la fase 3.
   - Desde el mismo hallazgo puede:
     - adjuntar evidencias;
     - cambiar el estado con su comentario;
     - asignar responsable y plazo;
     - ajustar el riesgo con justificación;
     - crear planes de acción;
     - enviarlo a la bandeja de regularización.
5. **Matriz de riesgos.** Haga clic en una celda para ver sus hallazgos.
6. **Reglas.**
   - En *Biblioteca de reglas* puede editar umbrales, cuentas, vigencia y excepciones. Al editar una regla del catálogo se crea una copia de la empresa con una nueva versión.
   - Las reglas normativas exigen norma, fuente oficial, fecha de publicación, condiciones, excepciones y responsable, y deben ser validadas por otro usuario.
   - En *Diseñador de controles* se crean reglas sin código: fuente, condiciones, Y/O y vista previa. Se guardan inactivas.
7. **Papeles de trabajo y muestras.**
   - Genere el papel de un procedimiento (regla).
   - Seleccione muestras por uno de estos métodos: aleatoria (con semilla reproducible), importe, riesgo, antigüedad, tercero, cuenta o estratificada.
   - Solo las muestras aleatorias y estratificadas se presentan como representativas.
8. **Acciones correctivas.**
   - Haga el seguimiento de los hallazgos confirmados, de la subsanación y de la verificación.
   - Exporte los planes y el seguimiento.
9. **Informes.**
   - Seis versiones: ejecutivo, detallado, gerencia, contador, auditor y por cuenta.
   - Cada uno tiene 16 secciones, se versiona con hash y sale en PDF o Excel.
   - Además hay 12 exportaciones especializadas, entre ellas el reporte origen–destino.
10. **Conclusión.**
    - *Enviar a revisión* → *Aprobar conclusión*: requiere una conclusión preliminar de al menos 20 caracteres y un aprobador distinto de quien ejecutó.
    - Después, *Cerrar encargo*.
    - Un encargo recurrente puede programar el siguiente periodo.
11. **Historial.** Bitácora completa con la verificación de integridad de la cadena.

## 9. Pruebas

`tests/test_auditoria.py` contiene 16 pruebas que cubren los 28 escenarios obligatorios con datos sintéticos.

| Prueba | Escenarios |
|---|---|
| test_01 | Asiento descuadrado |
| test_02_03_04_05 | Factura duplicada, pago duplicado, transferencia duplicada y pago parcial legítimo |
| test_06_07 | Saldo antiguo y anticipo |
| test_08_09_10 | Gasto sin destino, destino duplicado y transferencia incorrecta |
| test_11 | Diferencia de parametrización del ERP |
| test_12_13_14 | Servicio culminado, activo sin depreciación y activo sin fecha de uso |
| test_15_16 | Planilla contra libro y pago de planilla |
| test_17_18_24 | Crédito fiscal, detracción y regla normativa no validada (pendiente de evaluación) |
| test_19_20 | Provisión duplicada y corte |
| test_21_22_25 | Evidencia insuficiente, falso positivo y reapertura por reincidencia |
| test_materialidad_y_ajuste_de_riesgo | Escenario 23 |
| test_regla_configurable_con_vista_previa | Regla configurable |
| test_26 | Informes y exportaciones |
| test_27 | 100 000 movimientos |
| test_28 | Seguridad multiempresa y bitácora |
| test_auditoria_completa_y_conclusion | Auditoría completa y conclusión |

La suite completa del proyecto tiene **188 pruebas aprobadas**: las 172 anteriores más 16 nuevas.

## 10. Limitaciones

- **Reglas tributarias normativas** (TRI-06 a TRI-10: bancarización, reparos, periodo tributario, límites y
  renta de cuarta):
  - Se siembran **pendientes de validación** y **sin tasas ni umbrales**.
  - El sistema no inventa normas: un usuario autorizado debe cargar la norma, la fuente oficial y los parámetros vigentes, y otro debe validarlos.
  - Mientras tanto quedan `NO_VALIDADA` o `PENDIENTE_EVALUACION`.
  - La integración con SUNAT corresponde a la fase 12.
- **Datos del ERP.** Las reglas que necesitan usuario o fecha de registro, u origen del asiento (asientos manuales, retroactivos, fuera de horario), quedan `SIN_DATOS` si el ERP no exporta esos campos.
  - Un asiento manual o de cierre nunca se señala por sí solo: se combinan factores.
- **Datos de las fases anteriores.** Las conciliaciones que requieren archivos (planilla, kardex, constancias) se ejecutan solo si la fase 6 ya tiene esos datos. Sin registros auxiliares de la fase 5, las reglas de activos, servicios y devengos quedan `SIN_DATOS`.
- **Estadística.** Benford y los atípicos son indicadores, **nunca prueba de fraude**. Se documentan el método, la población y las limitaciones (Benford requiere poblaciones grandes y no aplica a importes asignados).
- **Funciones no incluidas en esta fase:**
  - Las auditorías recurrentes se programan con un botón; no hay un planificador automático.
  - Los papeles de trabajo son preliminares, en formato JSON exportable, preparados para la fase 13.
  - No se generan asientos de regularización: corresponden a la fase 8.
- **Memoria.** Con 1 M de movimientos la auditoría completa usa unos 5,3 GB de memoria.

## 11. Catálogo de reglas (167)

Las cinco reglas marcadas como normativas no se ejecutan hasta su validación.

### Integridad contable (`INTEGRIDAD`, 14 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| INT-01 | Igualdad entre debe y haber por asiento | ALTO | 5 | Partida doble: cada asiento debe cuadrar. |
| INT-02 | Cuentas inexistentes en el plan | ALTO | 5 | Plan Contable General Empresarial y políticas contables de la empresa. |
| INT-03 | Movimientos en cuentas inactivas | MEDIO | 4 | Plan Contable General Empresarial y políticas contables de la empresa. |
| INT-04 | Cuentas no autorizadas para movimientos | MEDIO | 4 | Plan Contable General Empresarial y políticas contables de la empresa. |
| INT-05 | Asientos fuera del periodo | MEDIO | 4 | Principio de devengo y corte contable. |
| INT-06 | Registros incompletos | MEDIO | 4 |  |
| INT-07 | Fechas inconsistentes | BAJO | 3 |  |
| INT-08 | Importes inválidos | ALTO | 5 |  |
| INT-09 | Movimientos sin glosa | BAJO | 2 |  |
| INT-10 | Documentos sin identificación en cuentas de terceros | MEDIO | 3 |  |
| INT-11 | Tipos de cambio inconsistentes | MEDIO | 3 | NIC 21: conversión al tipo de cambio de la fecha de la transacción. |
| INT-12 | Diferencias entre libro diario y libro mayor | ALTO | 4 |  |
| INT-13 | Diferencias entre mayor y balance de comprobación | ALTO | 4 |  |
| INT-14 | Saldos iniciales frente al cierre anterior | ALTO | 4 |  |

### Auditoría de asientos (`ASIENTOS`, 13 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| ASI-01 | Asientos manuales por importes significativos | MEDIO | 2 |  |
| ASI-02 | Asientos al cierre del periodo con factores de riesgo | MEDIO | 2 |  |
| ASI-03 | Asientos registrados después del cierre | BAJO | 2 |  |
| ASI-04 | Asientos con fechas retroactivas | BAJO | 2 |  |
| ASI-05 | Importes redondos inusuales | BAJO | 2 |  |
| ASI-06 | Cuentas poco frecuentes | BAJO | 2 |  |
| ASI-07 | Combinaciones contables atípicas | BAJO | 2 |  |
| ASI-08 | Glosas genéricas | BAJO | 2 |  |
| ASI-09 | Contrapartidas inesperadas | MEDIO | 3 |  |
| ASI-10 | Reclasificaciones frecuentes | BAJO | 2 |  |
| ASI-11 | Extornos repetitivos | MEDIO | 3 |  |
| ASI-12 | Movimientos extraordinarios | MEDIO | 2 |  |
| ASI-13 | Ajustes sin documentación disponible | MEDIO | 3 |  |

### Duplicidades (`DUPLICIDADES`, 13 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| DUP-01 | Facturas de compra duplicadas | ALTO | 4 |  |
| DUP-02 | Facturas de venta duplicadas | ALTO | 4 |  |
| DUP-03 | Recibos por honorarios duplicados | ALTO | 4 |  |
| DUP-04 | Notas de crédito duplicadas | MEDIO | 4 |  |
| DUP-05 | Pagos a proveedores duplicados | ALTO | 4 |  |
| DUP-06 | Cobranzas duplicadas | MEDIO | 4 |  |
| DUP-07 | Transferencias bancarias duplicadas | ALTO | 4 |  |
| DUP-08 | Asientos contables duplicados | ALTO | 4 |  |
| DUP-09 | Registros de planilla duplicados | ALTO | 4 |  |
| DUP-10 | Activos fijos duplicados | MEDIO | 3 |  |
| DUP-11 | Depreciaciones duplicadas | ALTO | 4 |  |
| DUP-12 | Detracciones duplicadas | MEDIO | 4 |  |
| DUP-13 | Retenciones duplicadas | MEDIO | 4 |  |

### Cuentas por cobrar (`CXC`, 12 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| CXC-01 | Documentos por cobrar vencidos | MEDIO | 3 |  |
| CXC-02 | Saldos antiguos por cobrar | MEDIO | 3 |  |
| CXC-03 | Concentración de la deuda en un cliente | BAJO | 2 |  |
| CXC-04 | Saldos acreedores inesperados de clientes | MEDIO | 3 |  |
| CXC-05 | Cobranzas sin aplicación | MEDIO | 3 |  |
| CXC-06 | Anticipos de clientes pendientes | MEDIO | 3 |  |
| CXC-07 | Notas de crédito por aplicar a clientes | MEDIO | 3 |  |
| CXC-08 | Préstamos al personal pendientes | MEDIO | 3 |  |
| CXC-09 | Entregas a rendir antiguas | MEDIO | 3 |  |
| CXC-10 | Diferencias de cambio pendientes de evaluación (por cobrar) | MEDIO | 3 |  |
| CXC-11 | Posible necesidad de evaluar deterioro | MEDIO | 2 |  |
| CXC-12 | Diferencias entre anexos y balance (por cobrar) | MEDIO | 4 |  |

### Cuentas por pagar (`CXP`, 10 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| CXP-01 | Facturas por pagar vencidas | MEDIO | 3 |  |
| CXP-02 | Obligaciones antiguas | MEDIO | 3 |  |
| CXP-03 | Pagos sin documento asociado | MEDIO | 3 |  |
| CXP-04 | Anticipos a proveedores pendientes de aplicación | MEDIO | 3 |  |
| CXP-05 | Notas de crédito de proveedores pendientes | MEDIO | 3 |  |
| CXP-06 | Saldos deudores inesperados de proveedores | MEDIO | 3 |  |
| CXP-07 | Obligaciones sin tercero identificado | MEDIO | 3 |  |
| CXP-08 | Diferencias entre cronogramas y contabilidad | ALTO | 4 |  |
| CXP-09 | Diferencias entre anexos y balance (por pagar) | MEDIO | 4 |  |
| CXP-10 | Obligaciones potencialmente omitidas (registro de compras) | ALTO | 3 |  |

### Bancos y tesorería (`TESORERIA`, 9 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| BAN-01 | Partidas conciliatorias antiguas | MEDIO | 3 |  |
| BAN-02 | Comisiones e ITF no registrados | BAJO | 4 |  |
| BAN-03 | Abonos y cargos no identificados | ALTO | 3 |  |
| BAN-04 | Transferencias duplicadas en la conciliación | ALTO | 3 |  |
| BAN-05 | Cheques pendientes de cobro y depósitos en tránsito | BAJO | 2 |  |
| BAN-06 | Saldos bancarios inconsistentes | CRITICO | 4 |  |
| BAN-07 | Diferencias de importe, moneda o periodo | MEDIO | 3 |  |
| BAN-08 | Transferencias entre cuentas sin contrapartida | MEDIO | 3 |  |
| BAN-09 | Movimientos sin documentación disponible | MEDIO | 3 |  |

### Gastos por naturaleza (`GASTOS`, 11 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| GAS-01 | Gastos duplicados potenciales | ALTO | 3 |  |
| GAS-02 | Gastos sin documento asociado | MEDIO | 3 |  |
| GAS-03 | Gastos sin proveedor identificado | MEDIO | 3 |  |
| GAS-04 | Gastos sin centro de costo obligatorio | BAJO | 3 |  |
| GAS-05 | Gastos fuera del periodo del comprobante | MEDIO | 3 |  |
| GAS-06 | Gastos que requieren evaluación de capitalización | MEDIO | 3 | NIC 16 / NIC 38: reconocimiento de activos. |
| GAS-07 | Gastos potencialmente personales | MEDIO | 2 |  |
| GAS-08 | Gastos que requieren evaluación tributaria | MEDIO | 2 |  |
| GAS-09 | Gastos recurrentes omitidos | MEDIO | 2 |  |
| GAS-10 | Variaciones significativas de gastos | BAJO | 2 |  |
| GAS-11 | Concentración de gastos por proveedor | BAJO | 2 |  |

### Origen y destino (`ORIGEN_DESTINO`, 9 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| ODE-01 | Gastos sin destino | ALTO | 4 |  |
| ODE-02 | Destinos sin origen identificado | MEDIO | 3 |  |
| ODE-03 | Gastos distribuidos más de una vez | ALTO | 4 |  |
| ODE-04 | Distribuciones incompletas | MEDIO | 3 |  |
| ODE-05 | Destinos incorrectos | MEDIO | 3 |  |
| ODE-06 | Contrapartidas de transferencia incorrectas | ALTO | 4 |  |
| ODE-07 | Porcentajes de distribución inconsistentes | MEDIO | 4 |  |
| ODE-08 | Clase 9 incluida como gasto adicional (duplicidad en resultados) | ALTO | 4 |  |
| ODE-09 | Configuración de distribución distinta a la aprobada | MEDIO | 3 |  |

### Parametrización del ERP (`PARAMETRIZACION`, 9 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| PAR-01 | Cuentas con naturaleza incorrecta | MEDIO | 4 |  |
| PAR-02 | Cuentas en rubros financieros incorrectos | MEDIO | 4 |  |
| PAR-03 | Cuentas de balance presentadas como resultados | ALTO | 4 |  |
| PAR-04 | Cuentas de resultados presentadas como balance | ALTO | 4 |  |
| PAR-05 | Duplicidad en agrupaciones financieras | ALTO | 4 |  |
| PAR-06 | Cambios de configuración sin sustento | MEDIO | 3 |  |
| PAR-07 | Diferencias respecto de las políticas aprobadas | MEDIO | 4 |  |
| PAR-08 | Cuentas con saldo omitidas en reportes | ALTO | 4 |  |
| PAR-09 | Cuentas incluidas más de una vez en reportes | ALTO | 4 |  |

### Ingresos (`INGRESOS`, 9 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| ING-01 | Facturas emitidas no contabilizadas | ALTO | 4 |  |
| ING-02 | Ingresos duplicados potenciales | ALTO | 3 |  |
| ING-03 | Ingresos en periodos distintos al comprobante | MEDIO | 3 |  |
| ING-04 | Notas de crédito no relacionadas | MEDIO | 3 |  |
| ING-05 | Diferencias entre facturación y contabilidad | MEDIO | 3 |  |
| ING-06 | Valorizaciones frente a ingresos reconocidos | MEDIO | 3 |  |
| ING-07 | Anticipos registrados como ingresos | MEDIO | 3 |  |
| ING-08 | Variaciones significativas de ingresos | BAJO | 2 |  |
| ING-09 | Concentración de ingresos por cliente | BAJO | 2 |  |

### Servicios en proceso (`SERVICIOS`, 8 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| SPR-01 | Servicios culminados con costos pendientes de evaluación | ALTO | 4 | NIIF 15 y NIC 2; la fecha de facturación no es el único criterio de reconocimiento. |
| SPR-02 | Costos de ejercicios anteriores sin movimiento | MEDIO | 3 |  |
| SPR-03 | Costos sin proyecto asignado | MEDIO | 3 |  |
| SPR-04 | Costos de proyectos suspendidos | MEDIO | 3 |  |
| SPR-05 | Costos sin sustento disponible | MEDIO | 3 |  |
| SPR-06 | Transferencias de costos inconsistentes | MEDIO | 3 |  |
| SPR-07 | Avance operativo frente al reconocimiento contable | MEDIO | 2 |  |
| SPR-08 | Posibles activos mantenidos indebidamente | ALTO | 3 |  |

### Activos fijos (`ACTIVOS`, 10 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| ACT-01 | Activos sin código | BAJO | 3 |  |
| ACT-02 | Activos sin fecha disponible para su uso | BAJO | 3 |  |
| ACT-03 | Activos sin depreciación cuando corresponde | MEDIO | 3 |  |
| ACT-04 | Depreciación superior al importe depreciable | ALTO | 4 | NIC 16: la depreciación no excede el importe depreciable. |
| ACT-05 | Depreciación posterior a una baja | ALTO | 4 |  |
| ACT-06 | Diferencias entre auxiliar y contabilidad | MEDIO | 4 |  |
| ACT-07 | Bajas no registradas | ALTO | 4 |  |
| ACT-08 | Activos totalmente depreciados en uso | INFORMATIVO | 2 |  |
| ACT-09 | Depreciación financiera frente a tributaria | INFORMATIVO | 2 |  |
| ACT-10 | Mantenimiento capitalizado que requiere evaluación | MEDIO | 2 |  |

### Inventarios (`INVENTARIOS`, 8 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| INV-01 | Existencias negativas | ALTO | 4 |  |
| INV-02 | Diferencias de valorización | MEDIO | 3 |  |
| INV-03 | Movimientos duplicados | MEDIO | 3 |  |
| INV-04 | Inventarios sin movimiento (posible obsolescencia) | MEDIO | 2 |  |
| INV-05 | Diferencias entre kardex y balance | ALTO | 4 |  |
| INV-06 | Inventario valorizado fuera del periodo | BAJO | 2 |  |
| INV-07 | Costos unitarios atípicos | BAJO | 2 |  |
| INV-08 | Diferencias de costo entre almacenes | BAJO | 2 |  |

### Planillas (`PLANILLAS`, 7 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| PLA-01 | Diferencias entre planilla y contabilidad | ALTO | 4 |  |
| PLA-02 | Pagos de planilla duplicados | ALTO | 4 |  |
| PLA-03 | Provisiones de beneficios pendientes | MEDIO | 3 |  |
| PLA-04 | Retenciones judiciales pendientes de evaluación | MEDIO | 3 |  |
| PLA-05 | Remuneraciones pendientes antiguas por trabajador | MEDIO | 3 |  |
| PLA-06 | Liquidaciones pendientes | MEDIO | 3 |  |
| PLA-07 | Aportes retenidos pendientes de entrega | MEDIO | 3 |  |

### Tributaria preventiva (`TRIBUTARIA`, 10 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| TRI-01 | Diferencias entre registro de compras y contabilidad | MEDIO | 3 |  |
| TRI-02 | Crédito fiscal pendiente de evaluación | MEDIO | 3 |  |
| TRI-03 | Detracciones pendientes de identificación | MEDIO | 3 |  |
| TRI-04 | Retenciones y percepciones pendientes de sustento | MEDIO | 3 |  |
| TRI-05 | Diferencias entre declaraciones importadas y registros | MEDIO | 3 |  |
| TRI-06 | Operaciones que requieren evaluar medios de pago (bancarización) · **normativa (requiere validación)** | MEDIO | 3 |  |
| TRI-07 | Gastos potencialmente sujetos a reparo tributario · **normativa (requiere validación)** | MEDIO | 3 |  |
| TRI-08 | Diferencias de periodo tributario (anotación de comprobantes) · **normativa (requiere validación)** | MEDIO | 3 |  |
| TRI-09 | Gastos sujetos a límites tributarios · **normativa (requiere validación)** | MEDIO | 3 |  |
| TRI-10 | Recibos por honorarios sin retención de cuarta categoría · **normativa (requiere validación)** | MEDIO | 3 |  |

### Devengos y corte (`DEVENGOS`, 8 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| DEV-01 | Gastos anticipados no devengados correctamente | MEDIO | 3 |  |
| DEV-02 | Gastos reconocidos anticipadamente | MEDIO | 2 |  |
| DEV-03 | Servicios recibidos pendientes de registro (corte) | MEDIO | 3 |  |
| DEV-04 | Ingresos registrados en periodos incorrectos | MEDIO | 3 |  |
| DEV-05 | Ingresos con comprobante posterior al corte | MEDIO | 3 |  |
| DEV-06 | Provisiones duplicadas | ALTO | 4 |  |
| DEV-07 | Provisiones antiguas pendientes de revisión | MEDIO | 3 |  |
| DEV-08 | Intereses pendientes de registro | MEDIO | 3 |  |

### Análisis estadístico (`ESTADISTICA`, 7 reglas)

| Código | Regla | Riesgo base | Prob. | Criterio |
|---|---|---|---|---|
| EST-01 | Importes atípicos por cuenta (rango intercuartílico) | INFORMATIVO | 2 |  |
| EST-02 | Frecuencia atípica de operaciones | INFORMATIVO | 2 |  |
| EST-03 | Comparación de gastos por centro de costo | INFORMATIVO | 2 |  |
| EST-04 | Comparación de gastos por proyecto | INFORMATIVO | 2 |  |
| EST-05 | Proporción de importes redondos | INFORMATIVO | 2 |  |
| EST-06 | Operaciones cercanas a límites configurados | BAJO | 2 |  |
| EST-07 | Ley de Benford (exploratoria) | INFORMATIVO | 1 |  |
