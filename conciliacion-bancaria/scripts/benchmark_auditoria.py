"""Prueba de rendimiento del auditor contable (fase 7) con datos sintéticos.

Uso:  python scripts/benchmark_auditoria.py 500000 [directorio_temporal]

Genera N movimientos (N/2 asientos de dos líneas: gasto clase 6 contra 4212 con comprobante y tercero), inserta el lote por
SQL masivo en una base SQLite temporal, ejecuta la auditoría completa (todas las reglas) y una re-ejecución incremental,
e informa tiempos reales y memoria máxima del proceso. Incluye algunas excepciones sembradas (duplicados y descuadres).
"""
import os
import resource
import sys
import tempfile
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(n: int, carpeta: str | None):
    carpeta = carpeta or tempfile.mkdtemp(prefix="bench7_")
    os.environ["CONCILIACION_DATA_DIR"] = carpeta
    from app.core import config, database
    config.DATA_DIR = Path(carpeta)
    database.configurar(f"sqlite:///{carpeta}/bench.db")
    database.init_db()
    from sqlalchemy import insert
    from app.auditoria import motor, servicio
    from app.core.database import SessionLocal
    from app.models import Empresa, LineaDiario, LoteContable

    t0 = time.perf_counter()
    with SessionLocal() as db:
        emp = Empresa(ruc="20609876540", razon_social="Benchmark SAC")
        db.add(emp)
        db.flush()
        lote = LoteContable(empresa_id=emp.id, tipo_informacion="DIARIO", ejercicio=2026, periodo=None, nombre_archivo="bench.csv",
                            hash_archivo="b" * 64, usuario="bench", registros_importados=n)
        db.add(lote)
        db.flush()
        filas = []
        for i in range(n // 2):
            p = i % 12 + 1
            f = date(2026, p, i % 28 + 1)
            imp = Decimal(100 + (i % 997)) + Decimal(i % 7) / 100
            asi = f"B{i}"
            dup = i % 5000 == 0  # excepciones sembradas: comprobante repetido
            num = str(i - 1 if dup and i else i)
            base = dict(lote_id=lote.id, empresa_id=emp.id, ejercicio=2026, periodo=p, fecha_contable=f, subdiario="11", numero_asiento=asi, moneda="PEN")
            filas.append({**base, "numero_linea": 1, "cuenta": "6361" if i % 3 else "6351", "glosa": f"SERVICIO {i % 50}", "debe_mn": imp, "haber_mn": 0,
                          "centro_costo": f"CC{i % 12}", "documento_tercero": f"20{100000000 + i % 300:09d}"})
            filas.append({**base, "numero_linea": 2, "cuenta": "4212", "glosa": "FACTURA", "debe_mn": 0, "haber_mn": imp - (1 if i % 20000 == 1 else 0),
                          "documento_tercero": f"20{100000000 + i % 300:09d}", "tipo_documento": "01", "serie": f"F{i % 40:03d}", "numero_documento": num})
            if len(filas) >= 20000:
                db.execute(insert(LineaDiario), filas)
                filas = []
        if filas:
            db.execute(insert(LineaDiario), filas)
        db.commit()
        t1 = time.perf_counter()
        e = servicio.crear_encargo(db, emp.id, "bench", {"tipo": "INTEGRAL", "ejercicio": 2026, "periodo": 12})
        run = motor.crear_run(db, e, "bench")
        db.commit()
        motor.ejecutar(db, run.id)
        db.refresh(run)
        t2 = time.perf_counter()
        run2 = motor.crear_run(db, e, "bench")
        db.commit()
        motor.ejecutar(db, run2.id)
        t3 = time.perf_counter()
        import json
        res = json.loads(run.resumen)
        tiempos = sorted(json.loads(run.tiempos).items(), key=lambda x: -x[1])[:8]
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        print(f"movimientos={n} inserción={t1 - t0:.1f}s auditoría={t2 - t1:.1f}s estado={run.estado_proceso} reglas={res['ejecucion']['reglas']} "
              f"hallazgos={res['totales']['hallazgos']} incremental={t3 - t2:.1f}s memoria_max={rss:.0f}MB")
        print("reglas más lentas (ms):", tiempos)
        print("estados de reglas:", res["ejecucion"]["estados_reglas"])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 100000, sys.argv[2] if len(sys.argv) > 2 else None)
