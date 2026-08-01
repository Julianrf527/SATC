from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Expediente(Base):
    __tablename__ = 'expediente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(15), unique=True)
    fecha_radicado = Column(Date)
    vereda_id = Column(Integer, ForeignKey('vereda.id', onupdate="CASCADE", ondelete="RESTRICT"))
    requiere_medida_preventiva = Column(Boolean)
    presunto_infractor_id = Column(Integer)
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    abogado_responsable_id = Column(Integer)
    predio = Column(String(100))
    descripcion = Column(String(300))
    causa_id = Column(Integer, ForeignKey('causa.id', onupdate="CASCADE", ondelete="RESTRICT"))

    vereda = relationship("Vereda", back_populates="expedientes")
    causa = relationship("Causa", back_populates="expedientes")
    quejosos = relationship("Quejoso", secondary="quejoso_expediente", back_populates="expedientes")
    recursos = relationship("RecursoAfectado", secondary="recurso_expediente", back_populates="expedientes")
    radicados_asociados = relationship("RadicadoAsociado", back_populates="expediente", cascade="all, delete-orphan")
    etapa_respuesta = relationship("EtapaRespuesta", back_populates="expediente", cascade="all, delete-orphan")
    informes_tecnicos = relationship("InformeTecnico", back_populates="expediente", cascade="all, delete-orphan")
    etapa_concepto = relationship("EtapaAcogerConcepto", back_populates="expediente", uselist=False, cascade="all, delete-orphan")


class Quejoso(Base):
    __tablename__ = 'quejoso'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(150))
    telefono = Column(String(10))
    correo = Column(String(100))

    expedientes = relationship("Expediente", secondary="quejoso_expediente", back_populates="quejosos")


class QuejososExpediente(Base):
    __tablename__ = 'quejoso_expediente'

    quejoso_id = Column(Integer, ForeignKey('quejoso.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)


class RecursoAfectado(Base):
    __tablename__ = 'recurso_afectado'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(15))

    expedientes = relationship("Expediente", secondary="recurso_expediente", back_populates="recursos")


class RecursoExpediente(Base):
    __tablename__ = 'recurso_expediente'

    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    recurso_id = Column(Integer, ForeignKey('recurso_afectado.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)


class Vereda(Base):
    __tablename__ = 'vereda'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(30))
    id_municipio = Column(Integer, ForeignKey('municipio.id', onupdate="CASCADE", ondelete="RESTRICT"))

    municipio = relationship("Municipio", back_populates="veredas")
    expedientes = relationship("Expediente", back_populates="vereda")


class Municipio(Base):
    __tablename__ = 'municipio'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(30))

    veredas = relationship("Vereda", back_populates="municipio")


class Causa(Base):
    __tablename__ = 'causa'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(20))

    expedientes = relationship("Expediente", back_populates="causa")


class RadicadoAsociado(Base):
    __tablename__ = 'radicado_asociado'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(15), unique=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"))

    expediente = relationship("Expediente", back_populates="radicados_asociados")


class EtapaRespuesta(Base):
    __tablename__ = 'etapa_respuesta'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"))
    radicado = Column(String(15), unique=True)
    fecha_radicado = Column(Date)
    documento_radicado_id = Column(Integer)
    medida_preventiva = Column(Boolean)

    expediente = relationship("Expediente", back_populates="etapa_respuesta")


class InformeTecnico(Base):
    __tablename__ = 'informe_tecnico'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"))
    profesional_asignado = Column(Integer)
    fecha_programacion_visita = Column(Date)
    fecha_recibido_informe = Column(Date)
    fecha_entrega_informe = Column(Date)
    documento_informe_id = Column(Integer)
    tipo_informe = Column(String(20))

    expediente = relationship("Expediente", back_populates="informes_tecnicos")


class EtapaAcogerConcepto(Base):
    __tablename__ = 'etapa_acoger_concepto'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"))
    fecha_auto_indagacion = Column(Date)
    termino = Column(Integer)
    fecha_termino_calculada = Column(Date)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="etapa_concepto")
    acto_administrativo = relationship("ActoAdministrativo", back_populates="etapa_concepto")


class ActoAdministrativo(Base):
    __tablename__ = 'acto_administrativo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    fecha_asigncion_juridica = Column(Date)
    documento_acto_administrativo_id = Column(Integer)
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    etapa_concepto = relationship("EtapaAcogerConcepto", back_populates="acto_administrativo")
    notificaciones = relationship("Notificacion", back_populates="acto_administrativo", cascade="all, delete-orphan")


class Notificacion(Base):
    __tablename__ = 'notificacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_creacion = Column(Date)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="CASCADE"))
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    fecha_envio_citacion = Column(Date)
    fecha_constancia_citacion = Column(Date)
    documento_citacion_id = Column(Integer)
    notificacion_exitosa = Column(Boolean)
    fecha_notificacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    tipo_notificacion_id = Column(Integer, ForeignKey('tipo_notificacion.id', onupdate="CASCADE", ondelete="RESTRICT"))
    documento_notificacion_id = Column(Integer)

    acto_administrativo = relationship("ActoAdministrativo", back_populates="notificaciones")
    tipo_notificacion = relationship("TipoNotificacion", back_populates="notificaciones")


class TipoNotificacion(Base):
    __tablename__ = 'tipo_notificacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(15))

    notificaciones = relationship("Notificacion", back_populates="tipo_notificacion")
