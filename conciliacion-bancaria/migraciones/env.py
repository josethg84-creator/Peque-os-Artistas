"""Entorno de Alembic: usa la misma URL y metadatos que la aplicación."""
from alembic import context

from app.core import database
import app.models  # noqa: F401  registra todos los modelos

config = context.config
target_metadata = database.Base.metadata


def run_migrations_offline():
    context.configure(url=str(database.engine.url), target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    conexion = config.attributes.get("connection")
    if conexion is not None:
        _ejecutar(conexion)
        return
    with database.engine.connect() as conexion:
        _ejecutar(conexion)
        conexion.commit()


def _ejecutar(conexion):
    context.configure(connection=conexion, target_metadata=target_metadata,
                      render_as_batch=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
