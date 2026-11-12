"""
Blueprint para el kiosco del cliente.

Ruta: GET /kiosco -> Renderiza kiosco.html
"""
from flask import Blueprint, render_template

kiosco_bp = Blueprint("kiosco", __name__)


@kiosco_bp.route("/kiosco")
def index():
    """Renderiza la interfaz del kiosco para clientes."""
    return render_template("kiosco.html")
