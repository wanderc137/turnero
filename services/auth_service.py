"""
Servicio de autenticacion para ejecutivos.

Usa Flask session para mantener la sesion del usuario y bcrypt
para verificar contraseñas.
"""
from functools import wraps

import bcrypt
from flask import current_app, jsonify, redirect, request, session, url_for

from models import Ejecutivo, db


def hash_password(password: str) -> str:
    """Genera un hash bcrypt para la contrasena dada."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )


def check_password(password: str, password_hash: str) -> bool:
    """Verifica una contrasena contra su hash bcrypt."""
    return bcrypt.checkpw(
        password.encode("utf-8"), password_hash.encode("utf-8")
    )


def login_ejecutivo(username: str, password: str) -> Ejecutivo | None:
    """
    Autentica un ejecutivo.

    Retorna el objeto Ejecutivo si las credenciales son validas,
    o None en caso contrario.
    """
    ejecutivo = Ejecutivo.query.filter_by(
        username=username, activo=True
    ).first()
    if ejecutivo is None:
        return None
    if not check_password(password, ejecutivo.password_hash):
        return None

    ejecutivo.logged_in = True
    db.session.commit()

    session["ejecutivo_id"] = ejecutivo.id
    session["ejecutivo_nombre"] = ejecutivo.nombre
    session["modulo_id"] = ejecutivo.modulo_id
    return ejecutivo


def logout_ejecutivo() -> None:
    """Cierra la sesion del ejecutivo."""
    ejecutivo_id = session.get("ejecutivo_id")
    if ejecutivo_id:
        ejecutivo = Ejecutivo.query.get(ejecutivo_id)
        if ejecutivo:
            ejecutivo.logged_in = False
            db.session.commit()

    session.pop("ejecutivo_id", None)
    session.pop("ejecutivo_nombre", None)
    session.pop("modulo_id", None)


def get_current_ejecutivo() -> Ejecutivo | None:
    """Retorna el ejecutivo actualmente autenticado o None."""
    ejecutivo_id = session.get("ejecutivo_id")
    if ejecutivo_id is None:
        return None
    return Ejecutivo.query.get(ejecutivo_id)


def login_required(f):
    """Decorador que redirige al login si no hay sesion activa."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "ejecutivo_id" not in session:
            return redirect(url_for("executive.login"))
        return f(*args, **kwargs)

    return decorated_function


def api_login_required(f):
    """
    Decorador para rutas API.
    Retorna 401 si no hay sesion activa.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "ejecutivo_id" not in session:
            return {"error": "No autenticado"}, 401
        return f(*args, **kwargs)

    return decorated_function


def csrf_protected(f):
    """
    Decorador de protección CSRF básica para endpoints POST/PUT/DELETE.

    Verifica que:
      1. El header ``Content-Type`` incluya ``application/json``.
      2. El header ``X-Requested-With`` sea ``XMLHttpRequest``.
      3. El header ``Origin`` o ``Referer`` coincida con el origen del servidor.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Verificar Content-Type
        content_type = request.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400

        # 2. Verificar X-Requested-With
        requested_with = request.headers.get("X-Requested-With", "")
        if requested_with != "XMLHttpRequest":
            return jsonify({"error": "Header X-Requested-With requerido"}), 400

        # 3. Verificar Origin/Referer contra el servidor
        origin = request.headers.get("Origin", "")
        referer = request.headers.get("Referer", "")
        server_origin = request.host_url.rstrip("/")

        if origin and not origin.startswith(server_origin):
            return jsonify({"error": "Origen no permitido"}), 400
        if referer and not referer.startswith(server_origin):
            return jsonify({"error": "Referer no permitido"}), 400

        return f(*args, **kwargs)

    return decorated_function
