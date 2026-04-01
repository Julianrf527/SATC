from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel, EmailStr
import logging
from typing import Optional

#----- DB -----

from db.deps import get_db
from db.models.involucrado import Involucrado
from db.models.auditoria import Auditoria
from core.permission import Permisos

router = APIRouter()
INVOLVED_MANAGE = Permisos.INVOLVED_MANAGE
INVOLVED_LOG = Permisos.INVOLVED_LOG

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Modelos Pydantic
class InvolucradoCreate(BaseModel):
    numero_documento: str
    digito_verificacion: str | None = None
    tipo_documento: str
    nombre: str
    celular: str
    correo: EmailStr

class InvolucradoUpdate(BaseModel):
    nombre: str
    celular: str
    correo: EmailStr
    digito_verificacion: str | None = None

class BulkInvolucradoRequest(BaseModel):
    ids: list[int]
    tipo_documento: str | None = None

class AuditoriaQueryParams(BaseModel):
    page: int = 1
    limit: int = 10
    usuario_id: Optional[int] = None
    documento_usuario: Optional[str] = None
    nombre_usuario: Optional[str] = None
    tipo_evento: Optional[str] = None
    resultado: Optional[str] = None
    fecha_desde: Optional[str] = None  # YYYY-MM-DD
    fecha_hasta: Optional[str] = None  # YYYY-MM-DD

#----------- FUNCIONES ------------

from services.crud_file_operations import insert_auditoria
from utils.verify_token import verify_gateway_token
from utils.verify_permission import verify_permission

# -------- ENDPOINTS -------

@router.get("/search/{tipo_documento}/{numero_documento}")
async def buscar_involucrado(
    request: Request,
    tipo_documento: str,
    numero_documento: str,
    dv: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Buscar involucrado por tipo y número de documento.
    Para NITs, el dígito de verificación (dv) es opcional como query parameter.
    """
    try:
        verify_gateway_token(request)

        try:
            numero_int = int(numero_documento)
        except ValueError:
            raise HTTPException(status_code=400, detail="Número de documento inválido")

        conditions = [
            Involucrado.numero_documento == numero_int,
            Involucrado.tipo_documento == tipo_documento
        ]

        if tipo_documento == "NIT" and dv:
            conditions.append(Involucrado.digito_verificacion == dv)

        stmt = select(Involucrado).where(and_(*conditions))
        result = await db.execute(stmt)
        involucrado = result.scalar_one_or_none()

        if not involucrado:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")

        return {
            "ok": True,
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
        logger.error(f"Error buscando involucrado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{involucrado_id}")
async def obtener_involucrado_por_id(
    request: Request,
    involucrado_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        verify_gateway_token(request)

        stmt = select(Involucrado).where(Involucrado.id == involucrado_id)
        result = await db.execute(stmt)
        involucrado = result.scalar_one_or_none()

        if not involucrado:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")

        return {
            "ok": True,
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
        logger.error(f"Error buscando involucrado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/new")
async def crear_involucrado(
    request: Request,
    involucrado: InvolucradoCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        token_data = verify_gateway_token(request)["user_id"]

        try:
            numero_documento_int = int(involucrado.numero_documento)
            celular_int = int(involucrado.celular)
        except ValueError:
            raise HTTPException(status_code=400, detail="Número de documento o celular inválido")
        
        # Validar dígito de verificación si está presente
        if involucrado.digito_verificacion and len(involucrado.digito_verificacion) > 2:
            raise HTTPException(status_code=400, detail="Dígito de verificación debe tener máximo 2 caracteres")
        
        # Construir condiciones de unicidad
        conditions = [
            Involucrado.numero_documento == numero_documento_int,
            Involucrado.tipo_documento == involucrado.tipo_documento
        ]
        
        # Si es NIT, incluir el DV en la verificación de unicidad
        if involucrado.tipo_documento == "NIT" and involucrado.digito_verificacion:
            conditions.append(Involucrado.digito_verificacion == involucrado.digito_verificacion)
            
        stmt = select(Involucrado).where(and_(*conditions))
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe un involucrado con ese documento y tipo"
            )
        
        # Crear nuevo involucrado
        new_involucrado = Involucrado(
            numero_documento=numero_documento_int,
            digito_verificacion=involucrado.digito_verificacion if involucrado.digito_verificacion else None,
            tipo_documento=involucrado.tipo_documento,
            nombre=involucrado.nombre,
            celular=celular_int,
            correo=involucrado.correo.lower()
        )
        
        db.add(new_involucrado)
        await db.commit()
        await db.refresh(new_involucrado)

        # Log de auditoría
        await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            tipo_evento="CREAR_INVOLUCRADO",
            resultado="EXITOSO",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detalle=f"Creación de involucrado documento={numero_documento_int} ({involucrado.tipo_documento}), nombre='{involucrado.nombre}', correo={involucrado.correo.lower()}",
            documento_usuario=token_data.get("documento"),
            nombre_usuario=token_data.get("nombre"),
            datos_nuevos={
                "id": new_involucrado.id,
                "numero_documento": numero_documento_int,
                "digito_verificacion": involucrado.digito_verificacion,
                "tipo_documento": involucrado.tipo_documento,
                "nombre": involucrado.nombre,
                "celular": celular_int,
                "correo": involucrado.correo.lower()
            }
        )
        
        return {
            "ok": True,
            "data": {
                "id": new_involucrado.id,
                "numero_documento": new_involucrado.numero_documento,
                "digito_verificacion": new_involucrado.digito_verificacion,
                "tipo_documento": new_involucrado.tipo_documento,
                "nombre": new_involucrado.nombre,
                "celular": new_involucrado.celular,
                "correo": new_involucrado.correo
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando involucrado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/{involucrado_id}")
async def actualizar_involucrado(
    request: Request,
    involucrado_id: int,
    involucrado_update: InvolucradoUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, INVOLVED_MANAGE)

        # Buscar involucrado existente
        stmt = select(Involucrado).where(Involucrado.id == involucrado_id)
        result = await db.execute(stmt)
        involucrado = result.scalar_one_or_none()
        
        if not involucrado:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")
        
        # Guardar estado anterior para auditoría
        datos_anteriores = {
            "id": involucrado.id,
            "numero_documento": involucrado.numero_documento,
            "tipo_documento": involucrado.tipo_documento,
            "nombre": involucrado.nombre,
            "celular": involucrado.celular,
            "correo": involucrado.correo,
            "digito_verificacion": involucrado.digito_verificacion
        }
        
        # Actualizar campos
        involucrado.nombre = involucrado_update.nombre
        involucrado.celular = involucrado_update.celular
        involucrado.correo = involucrado_update.correo.lower()
        involucrado.digito_verificacion = involucrado_update.digito_verificacion if involucrado_update.digito_verificacion else None
        
        await db.commit()
        await db.refresh(involucrado)

        # Log de auditoría
        await insert_auditoria(
            db=db,
            usuario_id=int(token_data["user_id"]),
            tipo_evento="ACTUALIZAR_INVOLUCRADO",
            resultado="EXITOSO",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detalle=f"Actualización de involucrado id={involucrado.id}, documento={involucrado.numero_documento} ({involucrado.tipo_documento}), nombre='{involucrado.nombre}'",
            documento_usuario=token_data.get("documento"),
            nombre_usuario=token_data.get("nombre"),
            datos_anteriores=datos_anteriores,
            datos_nuevos={
                "id": involucrado.id,
                "numero_documento": involucrado.numero_documento,
                "tipo_documento": involucrado.tipo_documento,
                "nombre": involucrado.nombre,
                "celular": involucrado.celular,
                "correo": involucrado.correo,
                "digito_verificacion": involucrado.digito_verificacion
            }
        )
        
        return {
            "ok": True,
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
        logger.error(f"Error actualizando involucrado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/manage")
async def listar_involucrados_paginado(
    request: Request,
    page: int = 1,
    limit: int = 10,
    numero_documento: Optional[str] = None,
    tipo_documento: Optional[str] = None,
    nombre: Optional[str] = None,
    correo: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Lista involucrados con paginación y filtros.
    Requiere permiso: involucrado_gestionar
    """
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, INVOLVED_MANAGE)
        
        # Query base
        query = select(Involucrado)
        count_query = select(func.count()).select_from(Involucrado)
        
        # Aplicar filtros
        conditions = []
        
        if numero_documento:
            try:
                num_doc = int(numero_documento)
                conditions.append(Involucrado.numero_documento == num_doc)
            except ValueError:
                pass  # Ignorar si no es número válido
        
        if tipo_documento:
            conditions.append(Involucrado.tipo_documento == tipo_documento)
        
        if nombre:
            conditions.append(Involucrado.nombre.ilike(f"%{nombre}%"))
        
        if correo:
            conditions.append(Involucrado.correo.ilike(f"%{correo}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Contar total
        total_count = await db.scalar(count_query) or 0
        
        # Paginación
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Involucrado.id.desc())
        
        # Ejecutar
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

        return {
            "ok": True,
            "data": data,
            "page": page,
            "limit": limit,
            "totalCount": total_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando involucrados: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/log")
async def obtener_auditoria(
    request: Request,
    page: int = 1,
    limit: int = 10,
    usuario_id: Optional[int] = None,
    documento_usuario: Optional[str] = None,
    nombre_usuario: Optional[str] = None,
    tipo_evento: Optional[str] = None,
    resultado: Optional[str] = None,
    fecha_desde: Optional[str] = None,  # YYYY-MM-DD
    fecha_hasta: Optional[str] = None,  # YYYY-MM-DD
    db: AsyncSession = Depends(get_db)
):
    """
    Consulta la auditoría de operaciones sobre involucrados.
    Filtros disponibles:
    - usuario_id: ID interno del usuario
    - documento_usuario: Número de documento del usuario (filtro parcial)
    - nombre_usuario: Nombre del usuario (filtro parcial)
    - tipo_evento: Tipo de operación realizada
    - resultado: Resultado de la operación (EXITOSO/ERROR)
    - fecha_desde/fecha_hasta: Rango de fechas (formato YYYY-MM-DD)
    Requiere permisos de administrador.
    """
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, INVOLVED_LOG)

        # Query base
        query = select(Auditoria)
        count_query = select(func.count()).select_from(Auditoria)

        # Aplicar filtros
        conditions = []

        if usuario_id:
            conditions.append(Auditoria.usuario_id == usuario_id)

        if documento_usuario:
            conditions.append(Auditoria.documento_usuario.ilike(f"%{documento_usuario}%"))

        if nombre_usuario:
            conditions.append(Auditoria.nombre_usuario.ilike(f"%{nombre_usuario}%"))

        if tipo_evento:
            conditions.append(Auditoria.tipo_evento == tipo_evento)

        if resultado:
            conditions.append(Auditoria.resultado == resultado)

        if fecha_desde:
            try:
                from datetime import datetime
                fecha_inicio = datetime.strptime(fecha_desde, "%Y-%m-%d")
                conditions.append(Auditoria.fecha >= fecha_inicio)
            except ValueError:
                raise HTTPException(status_code=400, detail="Fecha desde inválida. Use formato YYYY-MM-DD")

        if fecha_hasta:
            try:
                from datetime import datetime, timedelta
                fecha_fin = datetime.strptime(fecha_hasta, "%Y-%m-%d") + timedelta(days=1)
                conditions.append(Auditoria.fecha < fecha_fin)
            except ValueError:
                raise HTTPException(status_code=400, detail="Fecha hasta inválida. Use formato YYYY-MM-DD")

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Contar total
        total_count = await db.scalar(count_query) or 0

        # Paginación
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(Auditoria.fecha.desc(), Auditoria.id.desc())

        # Ejecutar
        result = await db.execute(query)
        auditorias = result.scalars().all()

        # Formatear respuesta
        data = [
            {
                "id": aud.id,
                "usuario_id": aud.usuario_id,
                "documento_usuario": aud.documento_usuario,
                "nombre_usuario": aud.nombre_usuario,
                "tipo_evento": aud.tipo_evento,
                "resultado": aud.resultado,
                "ip_address": aud.ip_address,
                "user_agent": aud.user_agent,
                "fecha": str(aud.fecha),
                "detalle": aud.detalle,
                "datos_anteriores": aud.datos_anteriores,
                "datos_nuevos": aud.datos_nuevos
            }
            for aud in auditorias
        ]

        return {
            "ok": True,
            "data": data,
            "page": page,
            "limit": limit,
            "totalCount": total_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consultando auditoría: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Endpoint interno
@router.post("/bulk")
async def obtener_involucrados_por_ids(
    request: Request,
    body: BulkInvolucradoRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene múltiples involucrados por una lista de IDs.
    Opcionalmente filtra por tipo_documento.
    """
    try:
        verify_gateway_token(request)

        if not body.ids:
            return {"ok": True, "data": []}

        conditions = [Involucrado.id.in_(body.ids)]
        if body.tipo_documento:
            conditions.append(Involucrado.tipo_documento == body.tipo_documento)

        stmt = select(Involucrado).where(and_(*conditions))
        result = await db.execute(stmt)
        involucrados = result.scalars().all()

        data = [
            {
                "id": inv.id,
                "numero_documento": inv.numero_documento,
                "digito_verificacion": inv.digito_verificacion,
                "tipo_documento": inv.tipo_documento,
                "nombre": inv.nombre,
                "celular": inv.celular,
                "correo": inv.correo,
            }
            for inv in involucrados
        ]

        return {"ok": True, "data": data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en bulk de involucrados: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

