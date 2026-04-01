from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase


class ViewBase(DeclarativeBase):
    """Base separada para vistas — NO se incluye en create_all del Base principal."""
    pass


class VDocumentoDetalle(ViewBase):
    """
    Mapeo ORM de la vista SQL 'vista_documentos_detalle'.

    Esta clase usa una Base SEPARADA (ViewBase) para que SQLAlchemy
    NO intente crearla como tabla en create_all().
    La vista real se crea con CREATE OR REPLACE VIEW en init_db().

    Columnas reales de la vista SQL:
    - id, documento_id, nombre, descripcion, tipo_archivo, estado
    - version_actual, numero_devoluciones, usuario_creador_id
    - fecha_creacion, fecha_ultima_actualizacion
    - total_revisiones, total_revisores
    """
    __tablename__ = 'vista_documentos_detalle'

    # Campos principales del documento
    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo_archivo = Column(String(50), nullable=False)
    estado = Column(String(50), nullable=False)
    version_actual = Column(Integer, default=1)
    numero_devoluciones = Column(Integer, default=0)
    usuario_creador_id = Column(Integer, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_ultima_actualizacion = Column(DateTime, default=datetime.utcnow)

    # Campos agregados (calculados desde otras tablas)
    total_revisiones = Column(Integer, default=0)
    total_revisores = Column(Integer, default=0)

    def __repr__(self):
        return f"<VDocumentoDetalle(id={self.id}, nombre='{self.nombre}', estado='{self.estado}')>"