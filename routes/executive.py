"""
Blueprint para la consola del ejecutivo.

Rutas:
  - GET /ejecutivo -> Renderiza login.html o executive.html segun sesion
"""
from flask import Blueprint, render_template

from services.auth_service import get_current_ejecutivo

executive_bp = Blueprint("executive", __name__)


@executive_bp.route("/ejecutivo")
def index():
    """
    Renderiza la consola del ejecutivo.

    Si el usuario no tiene sesion activa, muestra el login.
    Si ya esta autenticado, muestra el dashboard.
    """
    ejecutivo = get_current_ejecutivo()
    if ejecutivo is None:
        return render_template("login.html")
    return render_template(
        "executive.html",
        ejecutivo=ejecutivo.to_dict(),
    )


@executive_bp.route("/login")
def login():
    """Renderiza la pagina de login."""
    return render_template("login.html")
