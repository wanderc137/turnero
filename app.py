"""
Sistema Turnero - Aplicacion Flask

Punto de entrada de la aplicacion. Inicializa la base de datos,
registra blueprints y ejecuta el servidor de desarrollo.
"""
import os
import sys

from flask import Flask, render_template, request

from config import Config
from models import db


def create_app() -> Flask:
    """Factory de la aplicacion Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones
    db.init_app(app)

    # Registrar blueprints
    from routes.display import display_bp
    from routes.kiosco import kiosco_bp
    from routes.executive import executive_bp
    from routes.api import api_bp

    app.register_blueprint(display_bp)
    app.register_blueprint(kiosco_bp)
    app.register_blueprint(executive_bp)
    app.register_blueprint(api_bp)

    # Manejador global de error 500
    @app.errorhandler(500)
    def internal_error(error):
        """Maneja errores internos del servidor."""
        if request.path.startswith('/api/'):
            return {"error": "Error interno del servidor"}, 500
        return render_template('base.html', error="Error interno del servidor"), 500

    # Crear tablas y sembrar datos si es necesario
    with app.app_context():
        _initialize_database(app)

    return app


def _initialize_database(app: Flask) -> None:
    """
    Crea las tablas de la base de datos y ejecuta seed si esta vacia.
    """
    db.create_all()

    from models import Ejecutivo

    # Migracion: agregar columna logged_in si no existe
    inspector = db.inspect(db.engine)
    if "logged_in" not in [c["name"] for c in inspector.get_columns("ejecutivo")]:
        print("[*] Migrando BD: agregando columna logged_in...")
        db.session.execute(db.text("ALTER TABLE ejecutivo ADD COLUMN logged_in BOOLEAN NOT NULL DEFAULT 0"))
        db.session.commit()

    if Ejecutivo.query.first() is None:
        print("[*] Base de datos vacia. Ejecutando seed...")
        _run_seed()
        print("[*] Seed completado.")


def _run_seed() -> None:
    """Ejecuta el script de datos iniciales."""
    try:
        import seed
        seed.run_seed()
    except ImportError:
        print(
            "[!] No se pudo importar seed.py. "
            "Ejecute manualmente: python seed.py",
            file=sys.stderr,
        )


def main() -> None:
    """Punto de entrada principal."""
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Servidor iniciado en http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
