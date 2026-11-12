"""
Blueprint de la API REST y SSE para el sistema Turnero.

Provee endpoints para:
  - Autenticacion de ejecutivos
  - Gestion de turnos (solicitar, llamar, iniciar, finalizar)
  - Consulta de estado (display, cola, ejecutivo, modulos)
  - SSE (Server-Sent Events) para actualizaciones en tiempo real
"""
import json
import queue
import threading
import time

from flask import Blueprint, Response, request, session, stream_with_context

from models import Modulo, Turno, db
from services.auth_service import (
    api_login_required,
    csrf_protected,
    get_current_ejecutivo,
    login_ejecutivo,
    logout_ejecutivo,
)
from services.turno_service import (
    finalizar_atencion,
    get_cola,
    get_ejecutivo_estado,
    get_estado_display,
    iniciar_atencion,
    llamar_siguiente,
    solicitar_turno,
)

api_bp = Blueprint("api", __name__)

# ---------------------------------------------------------------------------
# SSE Event Bus (thread-safe)
# ---------------------------------------------------------------------------

_event_listeners: list[queue.Queue] = []
_listeners_lock = threading.Lock()


def broadcast_event(event_type: str, data: dict) -> None:
    """Envía un evento SSE a todos los clientes conectados."""
    payload = json.dumps({"type": event_type, "data": data})
    dead: list[queue.Queue] = []
    with _listeners_lock:
        for q in _event_listeners:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _event_listeners.remove(q)


def register_listener() -> queue.Queue:
    """Registra un nuevo listener SSE y retorna su cola."""
    q: queue.Queue = queue.Queue(maxsize=100)
    with _listeners_lock:
        _event_listeners.append(q)
    return q


def unregister_listener(q: queue.Queue) -> None:
    """Elimina un listener SSE de la lista."""
    with _listeners_lock:
        if q in _event_listeners:
            _event_listeners.remove(q)


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------


@api_bp.route("/api/auth/login", methods=["POST"])
@csrf_protected
def login():
    """Autentica un ejecutivo y crea sesión."""
    data = request.get_json(silent=True)
    if not data:
        return {"error": "Datos JSON requeridos"}, 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return {"error": "Usuario y contraseña requeridos"}, 400

    ejecutivo = login_ejecutivo(username, password)
    if ejecutivo is None:
        return {"error": "Usuario o contraseña incorrectos"}, 401

    return {
        "mensaje": "Login exitoso",
        "ejecutivo": ejecutivo.to_dict(),
    }, 200


@api_bp.route("/api/auth/logout", methods=["POST"])
@csrf_protected
def logout():
    """Cierra la sesión del ejecutivo."""
    logout_ejecutivo()
    broadcast_event("ejecutivo_logout", {})
    return {"mensaje": "Sesión cerrada"}, 200


# ---------------------------------------------------------------------------
# Turnos - Display y SSE
# ---------------------------------------------------------------------------


@api_bp.route("/api/turnos/display")
def turnos_display():
    """Retorna el estado actual de modulos y cola para la pantalla."""
    modulos = get_estado_display()
    cola = get_cola()
    return {"modulos": modulos, "cola": cola}, 200


@api_bp.route("/api/turnos/eventos")
def turnos_eventos():
    """
    Endpoint SSE (Server-Sent Events).

    Mantiene la conexión abierta y emite eventos cuando:
      - Un turno es creado (turno_creado)
      - Un turno es llamado (turno_llamado)
      - Un turno comienza a ser atendido (turno_atendido)
      - Un turno es finalizado (turno_finalizado)
      - Un ejecutivo cierra sesión (ejecutivo_logout)
    """

    def event_stream():
        q = register_listener()
        try:
            # Enviar heartbeat cada 30 segundos para mantener conexión
            last_heartbeat = time.time()
            while True:
                # Intentar obtener un evento (timeout para poder enviar heartbeat)
                try:
                    payload = q.get(timeout=5)
                    yield f"data: {payload}\n\n"
                except queue.Empty:
                    # Enviar heartbeat si han pasado 30 segundos
                    if time.time() - last_heartbeat >= 30:
                        yield f": heartbeat\n\n"
                        last_heartbeat = time.time()
                    continue
        except GeneratorExit:
            pass
        finally:
            unregister_listener(q)

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Turnos - Kiosco
# ---------------------------------------------------------------------------


@api_bp.route("/api/turnos/solicitar", methods=["POST"])
@csrf_protected
def turnos_solicitar():
    """Crea un nuevo turno desde el kiosco."""
    data = request.get_json(silent=True)
    if not data:
        return {"error": "Datos JSON requeridos"}, 400

    tipo_tramite_id = data.get("tipo_tramite_id")
    rut_cliente = data.get("rut", "").strip()

    if not tipo_tramite_id:
        return {"error": "tipo_tramite_id requerido"}, 400
    if not rut_cliente:
        return {"error": "RUT requerido"}, 400

    try:
        turno = solicitar_turno(
            tipo_tramite_id=int(tipo_tramite_id), rut_cliente=rut_cliente
        )
        broadcast_event("turno_creado", {
            "turno": turno.to_dict(),
        })
        return {
            "mensaje": "Turno creado exitosamente",
            "turno": turno.to_dict(),
        }, 201
    except ValueError as e:
        return {"error": str(e)}, 400


# ---------------------------------------------------------------------------
# Ejecutivo - Gestión de turnos
# ---------------------------------------------------------------------------


@api_bp.route("/api/ejecutivo/siguiente")
@api_login_required
def ejecutivo_siguiente():
    """Llama al siguiente turno en espera para el ejecutivo autenticado."""
    ejecutivo = get_current_ejecutivo()
    if not ejecutivo:
        return {"error": "No autenticado"}, 401

    try:
        turno = llamar_siguiente(ejecutivo.id)
    except ValueError as e:
        return {"error": str(e)}, 400

    if turno is None:
        return {"mensaje": "No hay turnos en espera", "turno": None}, 200

    # Emitir evento SSE
    broadcast_event("turno_llamado", {
        "codigo": turno.codigo,
        "modulo_id": turno.modulo_id,
        "modulo_nombre": turno.modulo.nombre if turno.modulo else None,
        "ejecutivo": ejecutivo.nombre,
        "turno": turno.to_dict(),
    })

    return {
        "mensaje": "Turno llamado exitosamente",
        "turno": turno.to_dict(),
    }, 200


@api_bp.route("/api/ejecutivo/iniciar-atencion", methods=["POST"])
@csrf_protected
@api_login_required
def ejecutivo_iniciar_atencion():
    """Inicia la atención de un turno escaneando su QR."""
    ejecutivo = get_current_ejecutivo()
    if not ejecutivo:
        return {"error": "No autenticado"}, 401

    data = request.get_json(silent=True)
    if not data:
        return {"error": "Datos JSON requeridos"}, 400

    qr_token = data.get("qr_token", "").strip()
    if not qr_token:
        return {"error": "qr_token requerido"}, 400

    try:
        turno = iniciar_atencion(qr_token, ejecutivo.id)
    except ValueError as e:
        return {"error": str(e)}, 400

    if turno is None:
        return {"error": "Turno no encontrado"}, 404

    # Emitir evento SSE
    broadcast_event("turno_atendido", {
        "codigo": turno.codigo,
        "modulo_id": turno.modulo_id,
        "turno": turno.to_dict(),
    })

    return {
        "mensaje": "Atención iniciada",
        "turno": turno.to_dict(),
    }, 200


@api_bp.route("/api/ejecutivo/finalizar-atencion", methods=["POST"])
@csrf_protected
@api_login_required
def ejecutivo_finalizar_atencion():
    """Finaliza la atención actual y llama al siguiente turno."""
    ejecutivo = get_current_ejecutivo()
    if not ejecutivo:
        return {"error": "No autenticado"}, 401

    data = request.get_json(silent=True)
    if not data:
        return {"error": "Datos JSON requeridos"}, 400

    tipo_atencion = data.get("tipo_atencion")
    comentarios = data.get("comentarios")

    try:
        turno_completado, turno_siguiente = finalizar_atencion(
            ejecutivo.id, tipo_atencion, comentarios
        )
    except ValueError as e:
        return {"error": str(e)}, 400

    # Emitir evento SSE: turno finalizado
    broadcast_event("turno_finalizado", {
        "codigo": turno_completado.codigo,
        "modulo_id": turno_completado.modulo_id,
        "turno": turno_completado.to_dict(),
    })

    # Si hay siguiente turno, emitir evento
    resultado = {
        "mensaje": "Atención finalizada",
        "turno_completado": turno_completado.to_dict(),
        "turno_siguiente": turno_siguiente.to_dict() if turno_siguiente else None,
    }

    if turno_siguiente:
        broadcast_event("turno_llamado", {
            "codigo": turno_siguiente.codigo,
            "modulo_id": turno_siguiente.modulo_id,
            "modulo_nombre": turno_siguiente.modulo.nombre if turno_siguiente.modulo else None,
            "ejecutivo": ejecutivo.nombre,
            "turno": turno_siguiente.to_dict(),
        })

    return resultado, 200


# ---------------------------------------------------------------------------
# Ejecutivo - Consultas
# ---------------------------------------------------------------------------


@api_bp.route("/api/ejecutivo/cola")
@api_login_required
def ejecutivo_cola():
    """Retorna la cola de turnos en espera agrupados por tipo."""
    return {"cola": get_cola()}, 200


@api_bp.route("/api/ejecutivo/estado")
@api_login_required
def ejecutivo_estado():
    """Retorna el estado actual del ejecutivo y su turno activo."""
    ejecutivo = get_current_ejecutivo()
    if not ejecutivo:
        return {"error": "No autenticado"}, 401

    estado = get_ejecutivo_estado(ejecutivo.id)
    return estado, 200


# ---------------------------------------------------------------------------
# Módulos
# ---------------------------------------------------------------------------


@api_bp.route("/api/tramites")
def tramites_listar():
    """Retorna la lista de tipos de trámite activos para el kiosco."""
    from models import TipoTramite

    tipos = TipoTramite.query.all()
    return {"tramites": [t.to_dict() for t in tipos]}, 200


@api_bp.route("/api/modulos")
def modulos_listar():
    """Retorna la lista de módulos activos."""
    modulos = Modulo.query.filter_by(activo=True).all()
    return {"modulos": [m.to_dict() for m in modulos]}, 200
