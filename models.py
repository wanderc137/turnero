"""
Modelos SQLAlchemy para el sistema Turnero.

Tablas:
  - modulo: modulos de atencion
  - ejecutivo: ejecutivos que atienden turnos
  - tipo_tramite: tipos de tramite (A: Creditos, B: Consultas, C: Retiro)
  - turno: tickets generados por el kiosco
"""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Modulo(db.Model):
    """Modulo de atencion."""

    __tablename__ = "modulo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    ejecutivos = db.relationship("Ejecutivo", backref="modulo", lazy=True)
    turnos = db.relationship(
        "Turno",
        backref="modulo",
        lazy=True,
        foreign_keys="Turno.modulo_id",
    )

    def __repr__(self) -> str:
        return f"<Modulo {self.id}: {self.nombre}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "activo": self.activo,
        }


class Ejecutivo(db.Model):
    """Ejecutivo que atiende turnos en un modulo."""

    __tablename__ = "ejecutivo"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    modulo_id = db.Column(db.Integer, db.ForeignKey("modulo.id"), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    logged_in = db.Column(db.Boolean, default=False, nullable=False)

    turnos = db.relationship(
        "Turno",
        backref="ejecutivo",
        lazy=True,
        foreign_keys="Turno.ejecutivo_id",
    )

    def __repr__(self) -> str:
        return f"<Ejecutivo {self.id}: {self.nombre}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "nombre": self.nombre,
            "modulo_id": self.modulo_id,
            "modulo_nombre": self.modulo.nombre if self.modulo else None,
            "activo": self.activo,
            "logged_in": self.logged_in,
        }


class TipoTramite(db.Model):
    """Tipo de tramite ofrecido (A, B, C)."""

    __tablename__ = "tipo_tramite"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(1), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    prefijo = db.Column(db.String(1), nullable=False)

    turnos = db.relationship("Turno", backref="tipo_tramite", lazy=True)

    def __repr__(self) -> str:
        return f"<TipoTramite {self.codigo}: {self.nombre}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "prefijo": self.prefijo,
        }


class Turno(db.Model):
    """Turno (ticket) generado por el kiosco."""

    __tablename__ = "turno"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False)
    tipo_tramite_id = db.Column(
        db.Integer, db.ForeignKey("tipo_tramite.id"), nullable=False
    )
    rut_cliente = db.Column(db.String(20), nullable=False)
    estado = db.Column(
        db.String(20),
        nullable=False,
        default="esperando",
        index=True,
    )
    modulo_id = db.Column(
        db.Integer, db.ForeignKey("modulo.id"), nullable=True
    )
    ejecutivo_id = db.Column(
        db.Integer, db.ForeignKey("ejecutivo.id"), nullable=True
    )
    fecha_creacion = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    fecha_llamado = db.Column(db.DateTime, nullable=True)
    fecha_inicio_atencion = db.Column(db.DateTime, nullable=True)
    fecha_completado = db.Column(db.DateTime, nullable=True)
    tipo_atencion = db.Column(db.String(50), nullable=True)
    comentarios = db.Column(db.Text, nullable=True)
    qr_token = db.Column(db.String(64), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Turno {self.codigo} [{self.estado}]>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "codigo": self.codigo,
            "tipo_tramite_id": self.tipo_tramite_id,
            "tipo_tramite": self.tipo_tramite.nombre if self.tipo_tramite else None,
            "tipo_tramite_codigo": self.tipo_tramite.codigo if self.tipo_tramite else None,
            "rut_cliente": self.rut_cliente,
            "estado": self.estado,
            "modulo_id": self.modulo_id,
            "modulo_nombre": self.modulo.nombre if self.modulo else None,
            "ejecutivo_id": self.ejecutivo_id,
            "ejecutivo_nombre": self.ejecutivo.nombre if self.ejecutivo else None,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_llamado": self.fecha_llamado.isoformat() if self.fecha_llamado else None,
            "fecha_inicio_atencion": self.fecha_inicio_atencion.isoformat()
            if self.fecha_inicio_atencion
            else None,
            "fecha_completado": self.fecha_completado.isoformat()
            if self.fecha_completado
            else None,
            "tipo_atencion": self.tipo_atencion,
            "comentarios": self.comentarios,
            "qr_token": self.qr_token,
        }

    def to_display_dict(self) -> dict:
        """Retorna dict con todos los campos EXCEPTO ``qr_token``.

        Utilizado para endpoints públicos como la pantalla de visualización,
        evitando exponer el token único del turno.
        """
        d = self.to_dict()
        d.pop("qr_token", None)
        return d
