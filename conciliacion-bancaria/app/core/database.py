"""Motor de base de datos y sesión."""
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core import config


class Base(DeclarativeBase):
    pass


def _crear_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" not in url:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _):  # integridad referencial en SQLite
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return eng


engine = _crear_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def configurar(url: str) -> None:
    """Reconfigura el motor (usado por las pruebas)."""
    global engine
    engine = _crear_engine(url)
    SessionLocal.configure(bind=engine)


BASE_FASE_1 = "0001"


def init_db() -> None:
    """Lleva el esquema a la última migración.

    - Base nueva: aplica todas las migraciones.
    - Base creada en la fase 1 (sin tabla alembic_version): se marca en la línea base
      0001 y luego se aplican las migraciones posteriores, sin tocar los datos existentes.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    import app.models  # noqa: F401  registra los modelos

    cfg = Config(str(config.BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(config.BASE_DIR / "migraciones"))
    with engine.begin() as conexion:
        cfg.attributes["connection"] = conexion
        tablas = set(inspect(conexion).get_table_names())
        if "alembic_version" not in tablas and "empresas" in tablas:
            command.stamp(cfg, BASE_FASE_1)
        command.upgrade(cfg, "head")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
