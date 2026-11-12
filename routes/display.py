"""
Blueprint para la pantalla de visualizacion publica (Display).

Ruta principal: GET / -> Renderiza display.html
"""
from flask import Blueprint, render_template

display_bp = Blueprint("display", __name__)


@display_bp.route("/")
def index():
    """Renderiza la pantalla de visualizacion de turnos."""
    return render_template("display.html")
