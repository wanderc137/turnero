"""
Servicio de logica de negocio para la gestion de turnos.

Incluye: solicitud de turno, llamado, inicio y finalizacion de atencion,
consulta de cola y estado del display.
"""
import uuid
from datetime import datetime, timezone

from models import Ejecutivo, Modulo, Turno, db


def _generar_codigo_turno(tipo_tramite_id: int) -> str:
    """
    Genera el codigo secuencial para un nuevo turno.

    Formato: {Prefijo}{NumeroSecuencial}
    Ejemplo: si existen 42 turnos tipo B, el siguiente sera "B43".

    El numero secuencial se calcula como COUNT(turnos del mismo tipo) + 1.
    """
    from models import TipoTramite

    tipo = TipoTramite.query.get(tipo_tramite_id)
    if not tipo:
        raise ValueError("Tipo de tramite no encontrado")

    prefijo = tipo.prefijo
    count = Turno.query.filter(
        Turno.tipo_tramite_id == tipo_tramite_id
    ).count()
    numero = count + 1
    return f"{prefijo}{numero}"


def validar_rut(rut: str) -> bool:
    """
    Valida un RUT chileno usando el algoritmo del dígito verificador (módulo 11).

    Pasos:
      1. Limpia el RUT (quita puntos, guión, espacios).
      2. Separa cuerpo y dígito verificador.
      3. Calcula el dígito verificador esperado.
      4. Compara con el dígito ingresado.
    """
    # Limpiar: quitar puntos, guiones, espacios
    limpio = rut.replace(".", "").replace("-", "").replace(" ", "").strip()

    if len(limpio) < 2:
        return False

    cuerpo = limpio[:-1]
    dv_ingresado = limpio[-1].upper()

    if not cuerpo.isdigit():
        return False

    # Calcular dígito verificador (módulo 11)
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = suma % 11
    dv_calculado = 11 - resto
    if dv_calculado == 11:
        dv_calculado = "0"
    elif dv_calculado == 10:
        dv_calculado = "K"
    else:
        dv_calculado = str(dv_calculado)

    return dv_calculado == dv_ingresado


def solicitar_turno(tipo_tramite_id: int, rut_cliente: str) -> Turno:
    """
    Crea un nuevo turno en estado 'esperando'.

    1. Genera codigo secuencial
    2. Genera qr_token unico (UUID hex)
    3. Persiste en BD
    4. Retorna el turno creado
    """
    if not validar_rut(rut_cliente):
        raise ValueError("RUT inválido")

    codigo = _generar_codigo_turno(tipo_tramite_id)

    turno = Turno(
        codigo=codigo,
        tipo_tramite_id=tipo_tramite_id,
        rut_cliente=rut_cliente,
        estado="esperando",
        fecha_creacion=datetime.now(timezone.utc),
        qr_token=uuid.uuid4().hex,
    )
    db.session.add(turno)
    db.session.commit()
    return turno


def llamar_siguiente(ejecutivo_id: int) -> Turno | None:
    """
    Asigna el siguiente turno en espera al modulo del ejecutivo.

    - Busca el turno mas antiguo en estado 'esperando' (FIFO).
    - Cambia su estado a 'llamado'.
    - Asigna modulo_id y ejecutivo_id.
    - Registra fecha_llamado.
    - Retorna el turno asignado o None si no hay turnos.
    """
    ejecutivo = Ejecutivo.query.get(ejecutivo_id)
    if not ejecutivo:
        raise ValueError("Ejecutivo no encontrado")

    # Verificar que el ejecutivo no tenga ya un turno activo
    turno_activo = Turno.query.filter(
        Turno.ejecutivo_id == ejecutivo_id,
        Turno.estado.in_(["llamado", "en_atencion"]),
    ).first()
    if turno_activo:
        raise ValueError(
            "Ya tienes un turno activo. Finaliza la atención actual primero."
        )

    turno = (
        Turno.query.filter_by(estado="esperando")
        .order_by(Turno.fecha_creacion.asc())
        .first()
    )
    if not turno:
        return None

    turno.estado = "llamado"
    turno.modulo_id = ejecutivo.modulo_id
    turno.ejecutivo_id = ejecutivo.id
    turno.fecha_llamado = datetime.now(timezone.utc)
    db.session.commit()
    return turno


def iniciar_atencion(qr_token: str, ejecutivo_id: int) -> Turno | None:
    """
    Inicia la atencion de un turno escaneando su QR.

    - Busca turno por qr_token.
    - Verifica que el turno este en estado 'llamado'.
    - Verifica que pertenezca al ejecutivo que lo escanea.
    - Cambia estado a 'en_atencion'.
    - Registra fecha_inicio_atencion.
    - Retorna el turno o None si no se encuentra.
    """
    turno = Turno.query.filter_by(qr_token=qr_token).first()
    if not turno:
        return None

    if turno.estado != "llamado":
        raise ValueError(
            f"El turno {turno.codigo} no esta en estado 'llamado' "
            f"(actual: {turno.estado})"
        )
    if turno.ejecutivo_id != ejecutivo_id:
        raise ValueError(
            "Este turno fue llamado por otro ejecutivo"
        )

    turno.estado = "en_atencion"
    turno.fecha_inicio_atencion = datetime.now(timezone.utc)
    db.session.commit()
    return turno


def finalizar_atencion(
    ejecutivo_id: int,
    tipo_atencion: str | None = None,
    comentarios: str | None = None,
) -> tuple[Turno, Turno | None]:
    """
    Finaliza la atencion del turno actual del ejecutivo.

    - Busca turno en estado 'en_atencion' del ejecutivo.
    - Cambia estado a 'completado'.
    - Registra tipo_atencion, comentarios y fecha_completado.
    - Automaticamente llama al siguiente turno.
    - Retorna (turno_completado, turno_siguiente o None).
    """
    turno = Turno.query.filter_by(
        ejecutivo_id=ejecutivo_id, estado="en_atencion"
    ).first()
    if not turno:
        raise ValueError(
            "No hay un turno en atencion para este ejecutivo"
        )

    turno.estado = "completado"
    turno.tipo_atencion = tipo_atencion
    turno.comentarios = comentarios
    turno.fecha_completado = datetime.now(timezone.utc)
    db.session.commit()

    # Llamar automaticamente al siguiente turno
    turno_siguiente = llamar_siguiente(ejecutivo_id)

    return turno, turno_siguiente


def get_cola() -> list[dict]:
    """
    Retorna la lista de turnos en espera, agrupados por tipo de tramite.

    Formato:
    [
        {
            "tipo_tramite_id": 1,
            "tipo_tramite": "Creditos",
            "codigo": "A",
            "turnos": [ ... ],
            "total": 5
        },
        ...
    ]
    """
    from models import TipoTramite

    tipos = TipoTramite.query.all()
    resultado = []
    for tipo in tipos:
        turnos = (
            Turno.query.filter_by(
                tipo_tramite_id=tipo.id, estado="esperando"
            )
            .order_by(Turno.fecha_creacion.asc())
            .all()
        )
        resultado.append(
            {
                "tipo_tramite_id": tipo.id,
                "tipo_tramite": tipo.nombre,
                "codigo": tipo.codigo,
                "total": len(turnos),
                "turnos": [t.to_display_dict() for t in turnos],
            }
        )
    return resultado


def get_estado_display() -> list[dict]:
    """
    Retorna el estado actual de todos los modulos para la pantalla display.

    Cada modulo muestra:
    - Informacion del modulo
    - Ejecutivo asignado
    - Turno actual (si tiene alguno en 'llamado' o 'en_atencion')
    """
    modulos = Modulo.query.filter_by(activo=True).all()
    resultado = []
    for modulo in modulos:
        ejecutivo = Ejecutivo.query.filter_by(
            modulo_id=modulo.id, activo=True, logged_in=True
        ).first()

        if not ejecutivo:
            continue

        turno_actual = (
            Turno.query.filter(
                Turno.modulo_id == modulo.id,
                Turno.estado.in_(["llamado", "en_atencion"]),
            )
            .order_by(Turno.fecha_llamado.desc())
            .first()
        )

        resultado.append(
            {
                "modulo": modulo.to_dict(),
                "ejecutivo": ejecutivo.to_dict(),
                "turno_actual": turno_actual.to_display_dict() if turno_actual else None,
            }
        )
    return resultado


def get_ejecutivo_estado(ejecutivo_id: int) -> dict:
    """
    Retorna el estado actual del ejecutivo y su turno activo.
    """
    ejecutivo = Ejecutivo.query.get(ejecutivo_id)
    if not ejecutivo:
        raise ValueError("Ejecutivo no encontrado")

    turno_activo = (
        Turno.query.filter(
            Turno.ejecutivo_id == ejecutivo_id,
            Turno.estado.in_(["llamado", "en_atencion"]),
        )
        .order_by(Turno.fecha_llamado.desc())
        .first()
    )

    return {
        "ejecutivo": ejecutivo.to_dict(),
        "turno_activo": turno_activo.to_dict() if turno_activo else None,
    }
