"""Punto de entrada: API REST + interfaz web."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import analisis, compensacion, contable, importaciones, maestros, movimientos, panel
from app.core import config
from app.core.database import SessionLocal, init_db
from app.services.catalogo import sembrar

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def ciclo_vida(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        sembrar(db)
    yield


def crear_app() -> FastAPI:
    app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION, lifespan=ciclo_vida,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    for r in (maestros.router, importaciones.router, movimientos.router, panel.router, contable.router, analisis.router, compensacion.router):
        app.include_router(r, prefix="/api")

    @app.get("/api/salud", tags=["Sistema"])
    def salud():
        return {"estado": "ok", "version": config.APP_VERSION}

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    def inicio():
        return FileResponse(STATIC / "index.html")

    return app


app = crear_app()
