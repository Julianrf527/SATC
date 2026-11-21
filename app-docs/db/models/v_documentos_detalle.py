from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase


class ViewBase(DeclarativeBase):
    """Base separada para vistas — NO se incluye en create_all del Base principal."""
    pass


class VDocumentoDetalle(ViewBase):
    """
    Mapeo ORM de la vista SQL 'vista_documentos_detalle'.

    Usa una Base separada (ViewBase) para que create_all() no intente crearla
    como tabla; el DDL real de la vista está en db/migrations.py (VISTA_DOCUMENTOS_DETALLE_SQL).
    """
    __tablename__ = 'vista_documentos_detalle'

    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo_archivo = Column(String(50), nullable=False)
    estado = Column(String(50), nullable=False)
    version_actual = Column(Integer, default=1)
    numero_devoluciones = Column(Integer, default=0)
    creador_id = Column(Integer, nullable=False)
    # La vista expone timestamptz: sin timezone=True asyncpg rechaza los filtros por fecha.
    fecha_creacion = Column(DateTime(timezone=True))
    fecha_ultima_actualizacion = Column(DateTime(timezone=True))

    total_revisiones = Column(Integer, default=0)
    total_revisores = Column(Integer, default=0)

    def __repr__(self):
        return f"<VDocumentoDetalle(id={self.id}, nombre='{self.nombre}', estado='{self.estado}')>"
