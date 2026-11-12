"""
Script de datos iniciales (seed) para el sistema Turnero.

Crea:
  - 3 tipos de tramite (A: Creditos, B: Consultas, C: Retiro)
  - 3 modulos de atencion
  - 3 ejecutivos con sus credenciales

Ejecutar: python seed.py
"""
from models import Ejecutivo, Modulo, TipoTramite, db
from services.auth_service import hash_password


def run_seed() -> None:
    """Ejecuta la siembra de datos iniciales.
    Debe ejecutarse dentro de un contexto de aplicacion Flask.
    """
    # Verificar si ya hay datos
    if Ejecutivo.query.first() is not None:
        print("[*] La base de datos ya tiene datos. Omitiendo seed.")
        return

    print("[*] Creando tipos de tramite...")
    tipos = [
        TipoTramite(codigo="A", nombre="Creditos", prefijo="A"),
        TipoTramite(
            codigo="B", nombre="Consultas Generales", prefijo="B"
        ),
        TipoTramite(
            codigo="C", nombre="Retiro de Documentos", prefijo="C"
        ),
    ]
    db.session.add_all(tipos)
    db.session.flush()

    print("[*] Creando modulos...")
    modulos = [
        Modulo(nombre="Modulo 1", activo=True),
        Modulo(nombre="Modulo 2", activo=True),
        Modulo(nombre="Modulo 3", activo=True),
    ]
    db.session.add_all(modulos)
    db.session.flush()

    print("[*] Creando ejecutivos...")
    ejecutivos = [
        Ejecutivo(
            username="carlos",
            password_hash=hash_password("carlos123"),
            nombre="Carlos Munoz",
            modulo_id=modulos[0].id,
            activo=True,
        ),
        Ejecutivo(
            username="maria",
            password_hash=hash_password("maria123"),
            nombre="Maria Gonzalez",
            modulo_id=modulos[1].id,
            activo=True,
        ),
        Ejecutivo(
            username="pedro",
            password_hash=hash_password("pedro123"),
            nombre="Pedro Hernandez",
            modulo_id=modulos[2].id,
            activo=True,
        ),
    ]
    db.session.add_all(ejecutivos)

    db.session.commit()
    print("[*] Seed completado exitosamente.")
    print("    Ejecutivos creados:")
    for e in ejecutivos:
        print(f"      - {e.username} / (password: {e.username}123)")
    print(f"    Modulos: {len(modulos)}")
    print(f"    Tipos de tramite: {len(tipos)}")


def main() -> None:
    """Punto de entrada para ejecucion independiente: python seed.py."""
    from app import create_app
    app = create_app()
    with app.app_context():
        run_seed()


if __name__ == "__main__":
    main()
