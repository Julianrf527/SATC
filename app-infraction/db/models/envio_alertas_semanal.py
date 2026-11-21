from sqlalchemy import Column, Date, DateTime, func

from .base import Base


class EnvioAlertasSemanal(Base):
    """Una fila por lunes en que se envió el reporte semanal de alertas.

    La reclama el primer worker de gunicorn que ejecuta el job (INSERT con la
    clave primaria): los demás ven el conflicto y no envían. También evita un
    segundo envío si el servicio se reinicia dentro del margen de ejecución.
    """
    __tablename__ = "envio_alertas_semanal"

    semana = Column(Date, primary_key=True)  # lunes de la semana (America/Bogota)
    fecha_inicio = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
