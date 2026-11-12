"""
Configuracion de la aplicacion Flask.
"""
import os


class Config:
    """Configuracion principal de la aplicacion."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "turnero-secret-key-dev-2025")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///turnero.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# Advertencia si se usa la clave por defecto (desarrollo)
_default_key = "turnero-secret-key-dev-2025"
if Config.SECRET_KEY == _default_key:
    import warnings
    warnings.warn(
        "SECRET_KEY no configurada en variable de entorno. "
        "Usando clave por defecto PARA DESARROLLO. "
        "Configure SECRET_KEY en producción.",
        RuntimeWarning,
        stacklevel=2,
    )
