"""Catálogo de observaciones del motor de validación contable.

Severidades (orden de gravedad):
  CRITICO      impide considerar confiable la importación (descuadres en importaciones completas,
               archivos estructuralmente inválidos, importes no procesables).
  ALTO         cuentas inexistentes, posibles duplicidades, diferencias significativas.
  MEDIO        información complementaria incompleta, homologaciones pendientes.
  INFORMATIVO  recomendaciones y campos opcionales no informados.
"""
from dataclasses import asdict, dataclass

C, A, M, I = "CRITICO", "ALTO", "MEDIO", "INFORMATIVO"

# código: (severidad por defecto, título, recomendación)
CATALOGO: dict[str, tuple[str, str, str]] = {
    # Estructura del archivo
    "EST001": (C, "Archivo estructuralmente inválido",
               "Verifique que el archivo no esté dañado o protegido y que tenga las columnas obligatorias."),
    "EST002": (I, "Filas vacías omitidas", "Ninguna acción requerida."),
    "EST003": (I, "Subtotales o totales identificados y excluidos",
               "Confirme que las filas excluidas son totales del reporte y no movimientos."),
    "EST004": (I, "Campo opcional no informado",
               "Si el ERP dispone de este dato, inclúyalo para enriquecer el análisis."),
    "EST005": (M, "Columna homologada sin datos", "Revise si la columna elegida es la correcta."),
    "EST006": (M, "Valor con formato no reconocido", "Corrija el valor en el origen o ajuste la homologación."),
    # Importes
    "IMP001": (C, "Importe no procesable",
               "El valor no es numérico. Revise el separador decimal configurado o corrija el origen."),
    "IMP002": (M, "Línea con debe y haber simultáneos", "Separe la línea en dos o confirme que es correcto."),
    "IMP003": (M, "Importe negativo en columna debe/haber",
               "Suele indicar un extorno. Se trasladó al lado contrario; confirme el criterio."),
    "IMP004": (M, "Línea con importe cero", "Verifique si la línea debe existir."),
    "IMP005": (A, "Indicador debe/haber no reconocido",
               "Use D/H (o claves 40/50 en SAP). La línea se interpretó por el signo del importe."),
    # Obligatorios, fechas, monedas, tipo de cambio
    "OBL001": (A, "Registro sin información obligatoria", "Complete el dato en el origen; la fila no se importa."),
    "FEC001": (A, "Fecha inválida", "Revise el formato de fecha configurado (dd/mm/aaaa, mm/dd/aaaa…)."),
    "FEC002": (A, "Fecha fuera del periodo seleccionado",
               "Confirme el periodo de la importación o reclasifique el registro."),
    "FEC003": (M, "Vencimiento anterior a la emisión", "Corrija las fechas del comprobante."),
    "MON001": (A, "Moneda no reconocida", "Use códigos ISO (PEN, USD, EUR) o equivalentes (S/, US$, MN, ME)."),
    "MON002": (M, "Moneda no informada en línea con importes en moneda extranjera",
               "Informe la moneda; se asumió USD para validar el tipo de cambio."),
    "TC001": (A, "Conversión inconsistente (MN ≠ ME × TC)",
              "Revise el tipo de cambio o los importes en moneda nacional/extranjera."),
    "TC002": (A, "Tipo de cambio distinto al registrado para la fecha",
              "Compare con el tipo de cambio publicado (SBS/SUNAT) y corrija si corresponde."),
    "TC003": (A, "Tipo de cambio inválido o faltante", "Informe un tipo de cambio mayor que cero."),
    "TC004": (M, "Variación diaria atípica del tipo de cambio", "Verifique el valor publicado para esa fecha."),
    "TC005": (M, "Tipo de cambio compra mayor que venta", "Verifique si las columnas están invertidas."),
    # Partida doble y totales
    "PD001": (C, "Asiento descuadrado (moneda nacional)",
              "El debe y el haber del asiento no son iguales. Revise líneas faltantes o importes."),
    "PD002": (A, "Asiento descuadrado (moneda extranjera)",
              "Puede deberse a redondeos o a líneas en otra moneda; revise el asiento."),
    "PD003": (C, "Totales generales descuadrados",
              "La suma del debe y del haber de toda la importación no coincide."),
    "TOT001": (A, "Diferencia entre los totales del archivo y la información procesada",
               "Revise filas excluidas por errores o totales del reporte mal calculados."),
    # Plan de cuentas y centros de costo
    "CTA000": (I, "No hay plan de cuentas cargado",
               "Importe el plan de cuentas para validar existencia, estado y naturaleza de las cuentas."),
    "CTA001": (A, "Cuenta inexistente en el plan de cuentas",
               "Cree la cuenta en el plan o corrija el código en el origen."),
    "CTA002": (A, "Cuenta contable inactiva", "Reactive la cuenta o reclasifique el movimiento."),
    "CTA003": (A, "Movimiento en cuenta no autorizada para registro",
               "La cuenta es de título o está restringida: registre en una subcuenta de último nivel."),
    "CTA004": (M, "Código de cuenta no válido según el PCGE", "Los códigos deben ser numéricos y empezar en 1–9."),
    "CTA005": (A, "Cuenta duplicada en el plan", "Elimine la fila duplicada del archivo."),
    "CTA006": (M, "Cuenta de destino configurada no existe en el plan", "Corrija el amarre de destino."),
    "CC000": (I, "No hay maestro de centros de costo",
              "Importe los centros de costo para validar los códigos utilizados."),
    "CC001": (M, "Centro de costo inexistente (pendiente de homologación)",
              "Registre el centro de costo o homologue el código."),
    "CC002": (M, "Falta centro de costo en una cuenta que lo requiere", "Asigne el centro de costo."),
    # Duplicidades y terceros
    "DUP001": (A, "Posible documento duplicado en el archivo",
               "El mismo documento aparece en asientos distintos con igual cuenta e importe. "
               "No es necesariamente un error: confírmelo."),
    "DUP002": (A, "Posible registro ya importado en otro lote",
               "Verifique que no se esté importando dos veces el mismo periodo o documento."),
    "DUP003": (A, "El archivo ya fue importado anteriormente", "Confirme si desea importarlo otra vez."),
    "DUP004": (A, "Código duplicado en el maestro", "Deje un solo registro por código."),
    "TER001": (M, "Documento de identidad con formato inválido",
               "Verifique el RUC (11 dígitos y dígito verificador) o DNI (8 dígitos)."),
    "TER002": (M, "Tercero no registrado en el maestro", "Registre el cliente o proveedor en el maestro."),
    # Saldos
    "NAT001": (A, "Saldo contrario a la naturaleza de la cuenta",
               "Analice la cuenta: puede indicar errores de registro o reclasificaciones pendientes."),
    "SAL001": (A, "Saldo inicial + movimientos ≠ saldo final",
               "El balance no es aritméticamente consistente para la cuenta."),
    "SAL002": (A, "Movimientos del balance distintos al libro diario importado",
               "Compare el balance con el diario del mismo periodo."),
    "SAL003": (A, "Saldo inicial distinto a los saldos iniciales importados",
               "Verifique la apertura del ejercicio."),
    # Registros de compras/ventas y cartera
    "REG001": (A, "Base + impuestos + no gravado ≠ total", "Revise los importes del comprobante."),
    "REG002": (M, "IGV no corresponde a la tasa vigente (18 % o 10 % MYPE)",
               "Revise la base imponible, la tasa o si hay operaciones no gravadas."),
    "CAR001": (A, "Saldo pendiente mayor que el importe original", "Revise pagos parciales o notas de crédito."),
    # Contabilidad analítica: clases 6, 7 y 9
    "DES001": (A, "Gasto por naturaleza sin cuenta de destino",
               "Registre el destino (clase 9 u otro configurado) y su contrapartida en la cuenta 79."),
    "DES002": (A, "Posible duplicidad de gastos en estados financieros (clase 9 ≠ cuenta 79)",
               "Lo cargado a destino debe abonarse en la 79 por el mismo importe."),
    "DES003": (A, "Diferencia entre gasto de origen y gasto de destino",
               "El gasto por naturaleza destinable no coincide con lo distribuido a destino."),
    "DES004": (M, "Destino sin centro de costo", "Asigne centro de costo a las cuentas de destino."),
    "DES005": (M, "Posible inconsistencia en cuentas de destino",
               "La cuenta de destino usada no es la configurada para la cuenta de origen."),
    "DES006": (M, "Tratamiento de la cuenta 78 a revisar",
               "Al aplicar una provisión (48) se espera el abono a la 78 Cargas cubiertas por provisiones."),
    "DES007": (I, "Reglas analíticas no aplicadas", "Configure las reglas de destino de la empresa si corresponde."),
    "REC001": (I, "Recomendación", ""),
}


@dataclass
class Obs:
    codigo: str
    severidad: str | None = None
    mensaje: str | None = None
    recomendacion: str | None = None
    fila: int | None = None
    cuenta: str | None = None
    asiento: str | None = None
    documento: str | None = None
    campo: str | None = None
    valor: str | None = None
    archivo: str | None = None
    hoja: str | None = None

    def __post_init__(self):
        sev, titulo, rec = CATALOGO[self.codigo]
        self.severidad = self.severidad or sev
        self.mensaje = self.mensaje or titulo
        self.recomendacion = self.recomendacion if self.recomendacion is not None else rec
        if self.valor is not None:
            self.valor = str(self.valor)[:120]

    def como_dict(self) -> dict:
        d = asdict(self)
        d["titulo"] = CATALOGO[self.codigo][1]
        return d


def catalogo_publico() -> list[dict]:
    return [{"codigo": c, "severidad": s, "titulo": t, "recomendacion": r} for c, (s, t, r) in CATALOGO.items()]
