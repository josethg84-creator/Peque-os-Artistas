"""Trabajos en segundo plano con avance consultable (barra de progreso real del asistente).

Se ejecutan en hilos del mismo proceso: suficiente para un despliegue de un solo nodo.
Para varios nodos se reemplazaría por una cola (fase 6). Con CONTABLE_TRABAJOS_SINCRONOS=1
se ejecutan en línea (útil en pruebas).
"""
import os
import threading
import time
import traceback
import uuid
from typing import Callable

_TRABAJOS: dict[str, dict] = {}
_LOCK = threading.Lock()
_RETENCION_SEG = 3600


def _limpiar():
    limite = time.time() - _RETENCION_SEG
    for k in [k for k, t in _TRABAJOS.items() if t["actualizado"] < limite]:
        _TRABAJOS.pop(k, None)


def crear(tipo: str, fn: Callable[[Callable[[int, str], None]], dict]) -> dict:
    tid = uuid.uuid4().hex
    with _LOCK:
        _limpiar()
        _TRABAJOS[tid] = {"id": tid, "tipo": tipo, "estado": "EN_COLA", "progreso": 0, "etapa": "En cola",
                          "resultado": None, "error": None, "status": None, "actualizado": time.time()}

    def avance(pct: int, etapa: str):
        with _LOCK:
            t = _TRABAJOS[tid]
            t.update(progreso=max(t["progreso"], min(int(pct), 99)), etapa=etapa, estado="PROCESANDO",
                     actualizado=time.time())

    def ejecutar():
        try:
            resultado = fn(avance)
            with _LOCK:
                _TRABAJOS[tid].update(estado="COMPLETADO", progreso=100, etapa="Completado", resultado=resultado,
                                      actualizado=time.time())
        except Exception as exc:  # el error se informa al usuario en el asistente
            status = getattr(exc, "status", 422 if exc.__class__.__name__ in ("ErrorImportacion", "ErrorContable") else 500)
            if status == 500:
                traceback.print_exc()
            with _LOCK:
                _TRABAJOS[tid].update(estado="ERROR", error=str(exc), status=status, actualizado=time.time())

    if os.getenv("CONTABLE_TRABAJOS_SINCRONOS") == "1":
        ejecutar()
    else:
        threading.Thread(target=ejecutar, daemon=True, name=f"trabajo-{tipo}").start()
    return obtener(tid)


def obtener(tid: str) -> dict | None:
    with _LOCK:
        t = _TRABAJOS.get(tid)
        return {k: v for k, v in t.items() if k != "actualizado"} if t else None
