from datetime import date
from pydantic import BaseModel
from typing import List, Optional

class ExpedienteSchema(BaseModel):
    radicado : str
    fecha_radicado : date
    vereda_id: int
    abogado_responsable_id: Optional[int] = None
    direccion: str
    descripcion: str
    tipos_afectacion_ids: List[int]
    quejosos_ids: List[int]
    recursos_ids: List[int]
    radicados_asociados: List[str]

class QuejosoSchema(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    anonimo: bool = False

class BulkEncargadoRequest(BaseModel):
    expediente_id: List[int]
    encargado_id: int

class FiltroAvanzado(BaseModel):
    """Filtros avanzados que NO están en quick filters."""
    direccion: Optional[str] = None
    municipio_id: Optional[int] = None
    vereda_ids: Optional[List[int]] = None
    recurso_ids: Optional[List[int]] = None
    valor_exacto: bool = False