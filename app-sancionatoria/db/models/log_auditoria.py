from sqlalchemy import Column, Integer, Text, BigInteger, String, DateTime, ForeignKey, JSON
from .base import Base
from datetime import datetime

class LogAuditoria(Base):
    __tablename__ = "log_auditoria"

    id = Column(Integer, primary_key=True)
    expediente_radicado = Column(String, ForeignKey("expediente.radicado", ondelete="SET NULL", onupdate="CASCADE"))
    tabla_afectada = Column(String(30), nullable=False)
    id_registro = Column(String(20), nullable=False)
    tipo_operacion = Column(String(10), nullable=False)
    usuario_id = Column(BigInteger, ForeignKey("usuario.numero_documento", ondelete="SET NULL", onupdate="CASCADE"))
    fecha = Column(DateTime, default=datetime.utcnow)
    descripcion = Column(Text)
    datos_anteriores = Column(JSON)
    datos_nuevos = Column(JSON)
