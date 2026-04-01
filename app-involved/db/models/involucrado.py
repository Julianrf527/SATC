from sqlalchemy import Column, Integer, String, BigInteger
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
