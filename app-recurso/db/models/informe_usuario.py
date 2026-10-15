from sqlalchemy import Column, Integer, String, Date
from .base import Base

class InformeUsuario(Base):
    __tablename__ = 'informe_usuario'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(15), unique=True, nullable=False)
    fecha_radicado = Column(Date, nullable=False)
    doc_informe_usuario_id = Column(Integer, nullable=False)
