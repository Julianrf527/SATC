from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class VDocumentoDetalle(Base):
    """
    Vista materializada o vista de base de datos que contiene
    información detallada de documentos con datos agregados.
    
    Esta vista combina información de:
    - documentos
    - versiones_documento
    - asignaciones_revisores
    - revisiones
    - auditoria_documentos
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
    fecha_ultima_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Campos agregados (calculados desde otras tablas)
    total_revisiones = Column(Integer, default=0)
    total_revisores = Column(Integer, default=0)
    
    # Campos de versiones (datos de la versión actual)
    version_id = Column(Integer, nullable=True)
    numero_version = Column(Integer, nullable=True)
    archivo_url = Column(String(500), nullable=True)
    archivo_nombre = Column(String(255), nullable=True)
    archivo_size = Column(Integer, nullable=True)
    fecha_subida = Column(DateTime, nullable=True)
    comentario = Column(Text, nullable=True)
    
    # Campos de revisiones (última revisión o revisión relevante)
    revision_id = Column(Integer, nullable=True)
    revisor_id = Column(Integer, nullable=True)
    estado_revision = Column(String(50), nullable=True)
    comentarios = Column(Text, nullable=True)
    fecha_revision = Column(DateTime, nullable=True)
    version_revisada = Column(Integer, nullable=True)
    
    # Campos de asignación de revisores
    fecha_asignacion = Column(DateTime, nullable=True)
    notificado = Column(Boolean, default=False)
    
    # Campos de auditoría (última acción o acción relevante)
    auditoria_id = Column(Integer, nullable=True)
    usuario_id = Column(Integer, nullable=True)
    accion = Column(String(100), nullable=True)
    descripcion_auditoria = Column(Text, nullable=True)
    fecha_accion = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<VDocumentoDetalle(id={self.id}, nombre='{self.nombre}', estado='{self.estado}')>"