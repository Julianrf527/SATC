"""
Ejemplo de endpoint protegido con verificación de permisos.

Este archivo demuestra cómo usar verify_permission() para proteger
endpoints que requieren permisos específicos.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from pydantic import BaseModel, EmailStr
import logging

# DB
from db.deps import get_db
from db.models.involucrado import Involucrado

# Utils
from utils.verify_gateway_token import verify_permission

router = APIRouter()

# Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Modelos Pydantic
class InvolucradoResponse(BaseModel):
    id: int
    numero_documento: int
    digito_verificacion: str | None
    tipo_documento: str
    nombre: str
    celular: int
    correo: str


# ============================================================================
# ENDPOINT EJEMPLO: Listar involucrados con paginación y verificación de permiso
# ============================================================================

@router.get("/manage")
async def listar_involucrados_paginado(
    request: Request,
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Registros por página"),
    numero_documento: str | None = Query(None, description="Filtrar por número de documento"),
    tipo_documento: str | None = Query(None, description="Filtrar por tipo de documento"),
    nombre: str | None = Query(None, description="Filtrar por nombre (búsqueda parcial)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista involucrados con paginación y filtros.
    
    **Requiere permiso:** expediente_gestionar involucrados
    
    Si el usuario no tiene este permiso, retornará 403 Forbidden automáticamente.
    """
    try:
        # VERIFICACIÓN DE PERMISO
        # Esta línea valida que el usuario tenga el permiso necesario
        # Si no lo tiene, lanza HTTPException 403 automáticamente
        user_id = verify_permission(request, "expediente_gestionar involucrados")
        
        # Si llegamos aquí, el usuario tiene el permiso ✓
        logger.info(f"Usuario {user_id} accediendo a listar involucrados")
        
        # Construir query base
        query = select(Involucrado)
        
        # Aplicar filtros si se proporcionan
        conditions = []
        
        if numero_documento:
            try:
                num_doc = int(numero_documento)
                conditions.append(Involucrado.numero_documento == num_doc)
            except ValueError:
                raise HTTPException(status_code=400, detail="Número de documento inválido")
        
        if tipo_documento:
            conditions.append(Involucrado.tipo_documento == tipo_documento)
        
        if nombre:
            conditions.append(Involucrado.nombre.ilike(f"%{nombre}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Contar total de registros (para paginación)
        count_query = select(func.count()).select_from(Involucrado)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_count = await db.scalar(count_query)
        
        # Aplicar paginación
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Involucrado.id.desc())
        
        # Ejecutar query
        result = await db.execute(query)
        involucrados = result.scalars().all()
        
        # Formatear respuesta
        data = [
            {
                "id": inv.id,
                "numero_documento": inv.numero_documento,
                "digito_verificacion": inv.digito_verificacion,
                "tipo_documento": inv.tipo_documento,
                "nombre": inv.nombre,
                "celular": inv.celular,
                "correo": inv.correo
            }
            for inv in involucrados
        ]
        
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
        
        return {
            "ok": True,
            "data": data,
            "page": page,
            "limit": limit,
            "totalCount": total_count,
            "totalPages": total_pages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando involucrados: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ============================================================================
# ENDPOINT EJEMPLO: Editar involucrado con verificación de permiso
# ============================================================================

class InvolucradoUpdate(BaseModel):
    nombre: str
    celular: str
    correo: EmailStr
    digito_verificacion: str | None = None


@router.put("/manage/{involucrado_id}")
async def editar_involucrado(
    request: Request,
    involucrado_id: int,
    data: InvolucradoUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Edita los datos de un involucrado.
    
    **Requiere permiso:** expediente_gestionar involucrados
    
    No se puede editar el número de documento ni el tipo de documento.
    """
    try:
        # VERIFICACIÓN DE PERMISO
        user_id = verify_permission(request, "expediente_gestionar involucrados")
        
        logger.info(f"Usuario {user_id} editando involucrado {involucrado_id}")
        
        # Buscar el involucrado
        stmt = select(Involucrado).where(Involucrado.id == involucrado_id)
        result = await db.execute(stmt)
        involucrado = result.scalar_one_or_none()
        
        if not involucrado:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")
        
        # Validar celular
        try:
            celular_int = int(data.celular)
            if celular_int <= 0:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=400, detail="Celular inválido")
        
        # Validar dígito de verificación si está presente
        if data.digito_verificacion and len(data.digito_verificacion) > 2:
            raise HTTPException(
                status_code=400,
                detail="Dígito de verificación no puede tener más de 2 caracteres"
            )
        
        # Actualizar campos
        involucrado.nombre = data.nombre
        involucrado.celular = celular_int
        involucrado.correo = data.correo.lower()
        involucrado.digito_verificacion = data.digito_verificacion if data.digito_verificacion else None
        
        await db.commit()
        await db.refresh(involucrado)
        
        return {
            "ok": True,
            "message": "Involucrado actualizado correctamente",
            "data": {
                "id": involucrado.id,
                "numero_documento": involucrado.numero_documento,
                "digito_verificacion": involucrado.digito_verificacion,
                "tipo_documento": involucrado.tipo_documento,
                "nombre": involucrado.nombre,
                "celular": involucrado.celular,
                "correo": involucrado.correo
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error editando involucrado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
