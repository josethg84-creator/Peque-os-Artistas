"""Configuración de la aplicación (variables de entorno)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("CONCILIACION_DATA_DIR", BASE_DIR / "data"))

# SQLite por defecto; en producción: postgresql+psycopg://usuario:clave@host/bd
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'conciliacion.db'}")

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
APP_NAME = "Conciliación Bancaria"
APP_VERSION = "0.1.0"
