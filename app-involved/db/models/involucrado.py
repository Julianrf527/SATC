from sqlalchemy import Column, Integer, String, BigInteger, Index
from .base import Base

class Involucrado(Base):
    __tablename__ = "involucrado"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_documento = Column(BigInteger)
    digito_verificacion = Column(String(2))
    tipo_documento = Column(String(20))
    nombre = Column(String(100))
    celular = Column(BigInteger)
    correo = Column(String(254))
    direccion = Column(String(200), nullable=True)

    __table_args__ = (
        # (numero_documento, tipo_documento) es la llave lógica real: identifica
        # a una única persona/entidad y es el par por el que filtra toda búsqueda
        # por documento. El UNIQUE además cierra la ventana de carrera del
        # check-then-insert en /new (dos altas concurrentes del mismo documento).
        # Crear el índice falla si la tabla ya tiene duplicados: deduplicar antes.
        Index("ix_involucrado_documento", "numero_documento", "tipo_documento", unique=True),
    )
