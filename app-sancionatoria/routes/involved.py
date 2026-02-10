from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func, or_
from sqlalchemy.orm import  selectinload
from pydantic import BaseModel, EmailStr
import logging
from typing import Optional

#----- DB -----

from db.deps import get_db
from db.models.involucrado import Involucrado
from db.models.involucrado_expediente import InvolucradoExpediente
from db.models.expediente import Expediente
from db.models.etapa import Etapa
from db.models.involucrado_notificacion import InvolucradoNotificacion
from db.models.acto_admin import ActoAdmin
from db.models.notificacion import Notificacion

router = APIRouter()

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

class InvolucradoExpedienteCreate(BaseModel):
    expediente_radicado: str
    involucrado_numero_documento: str
    involucrado_tipo_documento: str
    involucrado_digito_verificacion: str | None = None  # AGREGADO PARA SOPORTE DE DV

#----------- FUNCIONES ------------

from services.crud_file_operations import insert_log_auditoria
from utils.verify_gateway_token import verify_gateway_token

# -------- ENDPOINTS -------

@router.get("/{numero_documento}/{tipo_documento}/{dv}")
@router.get("/{numero_documento}/{tipo_documento}")
async def obtener_involucrado_por_documento(
    request: Request,
    numero_documento: str,
    tipo_documento: str,
    dv: str | None = None,
    db: AsyncSession = Depends(get_db), 
):
    try:
        user_id = verify_gateway_token(request)
        # Convertir numero_documento a entero para comparar con BIGINT
        try:
            numero_documento_int = int(numero_documento)
        except ValueError:
            raise HTTPException(status_code=400, detail="Número de documento inválido")
        
        # Construir la consulta base
        conditions = [
            Involucrado.numero_documento == numero_documento_int,
            Involucrado.tipo_documento == tipo_documento
        ]
        
        # Si es NIT y se proporciona DV, agregarlo a las condiciones
        if tipo_documento == "NIT" and dv is not None:
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

@router.post("/new")
async def crear_involucrado(
    request: Request,
    involucrado: InvolucradoCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

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
        await insert_log_auditoria(
            db=db,
            usuario_id=int(usuario_id),
            tabla_afectada="involucrado",
            tipo_operacion="INSERT",
            descripcion=f"Creación de involucrado id={new_involucrado.id}, numero_documento={numero_documento_int}, tipo_documento={involucrado.tipo_documento}"
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

@router.put("/{numero_documento}/{tipo_documento}")
async def actualiar_involucrado(
    request: Request,
    numero_documento: str,
    tipo_documento: str,
    involucrado_update: InvolucradoUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        usuario_id = verify_gateway_token(request)

        # Convertir numero_documento y celular a enteros
        try:
            numero_documento_int = int(numero_documento)
            celular_int = int(involucrado_update.celular)
        except ValueError:
            raise HTTPException(status_code=400, detail="Número de documento o celular inválido")
        
        # Validar dígito de verificación si está presente
        if involucrado_update.digito_verificacion and len(involucrado_update.digito_verificacion) > 2:
            raise HTTPException(status_code=400, detail="Dígito de verificación debe tener máximo 2 caracteres")
            
        # Buscar involucrado existente
        stmt = select(Involucrado).where(
            and_(
                Involucrado.numero_documento == numero_documento_int,
                Involucrado.tipo_documento == tipo_documento
            )
        )
        result = await db.execute(stmt)
        involucrado = result.scalar_one_or_none()
        
        if not involucrado:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")
        
        # Actualizar campos
        involucrado.nombre = involucrado_update.nombre
        involucrado.celular = celular_int
        involucrado.correo = involucrado_update.correo.lower()
        involucrado.digito_verificacion = involucrado_update.digito_verificacion if involucrado_update.digito_verificacion else None
        
        await db.commit()
        await db.refresh(involucrado)

        # Log de auditoría
        await insert_log_auditoria(
            db=db,
            usuario_id=int(usuario_id),
            tabla_afectada="involucrado",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de involucrado id={involucrado.id}, numero_documento={numero_documento_int}, tipo_documento={tipo_documento}"
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

@router.post("/involved-file")
async def vincular_involucrado_a_expediente(
    request: Request,
    link_data: InvolucradoExpedienteCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Vincular un involucrado existente a un expediente.
    Para NITs, el DV es requerido para identificar correctamente al involucrado.
    """
    try:
        usuario_id = verify_gateway_token(request)

        # Verificar que el expediente existe y el usuario tiene permisos
        stmt_expediente = select(Expediente).where(
            Expediente.radicado == link_data.expediente_radicado,
            Expediente.encargado_id == usuario_id
        )
        result_expediente = await db.execute(stmt_expediente)
        expediente = result_expediente.scalar_one_or_none()
        
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")
        
        # Verificar que el involucrado existe
        try:
            numero_documento_int = int(link_data.involucrado_numero_documento)
        except ValueError:
            raise HTTPException(status_code=400, detail="Número de documento inválido")
        
        # Construir condiciones de búsqueda - INCLUIR DV PARA NITs
        conditions = [
            Involucrado.numero_documento == numero_documento_int,
            Involucrado.tipo_documento == link_data.involucrado_tipo_documento
        ]
        
        # Si es NIT, DEBE incluir el DV en la búsqueda
        if link_data.involucrado_tipo_documento == "NIT":
            if not link_data.involucrado_digito_verificacion:
                raise HTTPException(
                    status_code=400, 
                    detail="El dígito de verificación es requerido para NITs"
                )
            conditions.append(Involucrado.digito_verificacion == link_data.involucrado_digito_verificacion)
            
        stmt_involucrado = select(Involucrado).where(and_(*conditions))
        result_involucrado = await db.execute(stmt_involucrado)
        involucrado = result_involucrado.scalar_one_or_none()
        
        if not involucrado:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")
        
        # Verificar si ya existe la relación
        stmt_existing = select(InvolucradoExpediente).where(
            and_(
                InvolucradoExpediente.involucrado_id == involucrado.id,
                InvolucradoExpediente.expediente_radicado == link_data.expediente_radicado
            )
        )
        result_existing = await db.execute(stmt_existing)
        existing_link = result_existing.scalar_one_or_none()
        
        if existing_link:
            raise HTTPException(
                status_code=400, 
                detail="El involucrado ya está vinculado a este expediente"
            )
        
        # Crear la relación
        new_link = InvolucradoExpediente(
            involucrado_id=involucrado.id,
            expediente_radicado=link_data.expediente_radicado
        )
        
        db.add(new_link)
        await db.commit()

        # Log de auditoría
        await insert_log_auditoria(
            db=db,
            usuario_id=int(usuario_id),
            tabla_afectada="involucrado_expediente",
            tipo_operacion="INSERT",
            descripcion=f"Vinculado involucrado_id={involucrado.id} (doc={numero_documento_int}, tipo={link_data.involucrado_tipo_documento}) al expediente radicado={link_data.expediente_radicado}"
        )
        
        return {
            "ok": True,
            "data": {
                "involucrado_id": involucrado.id,
                "expediente_radicado": link_data.expediente_radicado,
                "message": "Involucrado vinculado exitosamente al expediente"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error vinculando involucrado a expediente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/involved-file/{radicado}/{numero_documento}/{tipo_documento}")
async def desvincular_involucrado_a_expediente(
    request: Request,
    radicado: str,
    numero_documento: int,
    tipo_documento: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Desvincular un involucrado de un expediente.
    Nota: Para NITs con el mismo número pero diferente DV, esto puede causar ambigüedad.
    Considera agregar el DV como parámetro opcional si es necesario.
    """
    try:
        usuario_id = verify_gateway_token(request)
        stmr = select(Expediente.radicado).where(
            Expediente.radicado == radicado,
            Expediente.encargado_id == int(usuario_id)
        )
        res = await db.execute(stmr)
        expediente = res.scalar_one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado o sin permisos")

        # Buscar el involucrado
        # NOTA: Si hay múltiples NITs con el mismo número, esto tomará el primero
        stmt_involucrado = select(Involucrado).where(
            and_(
                Involucrado.numero_documento == numero_documento,
                Involucrado.tipo_documento == tipo_documento
            )
        )
        result_involucrado = await db.execute(stmt_involucrado)
        
        # Obtener todos los resultados
        involucrados = result_involucrado.scalars().all()
        
        if not involucrados:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")
        
        # Si hay múltiples involucrados (caso NITs), necesitamos encontrar cuál está vinculado
        involucrado = None
        if len(involucrados) > 1:
            # Buscar cuál de los involucrados está vinculado a este expediente
            for inv in involucrados:
                stmt_check = select(InvolucradoExpediente).where(
                    and_(
                        InvolucradoExpediente.involucrado_id == inv.id,
                        InvolucradoExpediente.expediente_radicado == radicado
                    )
                )
                result_check = await db.execute(stmt_check)
                if result_check.scalar_one_or_none():
                    involucrado = inv
                    break
            
            if not involucrado:
                raise HTTPException(
                    status_code=404,
                    detail="No se encontró la vinculación del involucrado a este expediente"
                )
        else:
            involucrado = involucrados[0]
        
        # Primero eliminar las notificaciones asociadas
        stmt = select(Etapa.id).where(Etapa.expediente_radicado == radicado)
        etapas = (await db.execute(stmt)).scalars().all()

        for etapa_id in etapas:
            stmt = select(ActoAdmin.id).where(ActoAdmin.etapa_id == etapa_id)
            acto_admin = (await db.execute(stmt)).scalars().all()

            for ad_id in acto_admin:
                stmt = select(Notificacion.id).where(Notificacion.acto_admin_id == ad_id)
                notificaciones = (await db.execute(stmt)).scalars().all()

                for notif_id in notificaciones:
                    # Usar el ID del involucrado
                    stmt = delete(InvolucradoNotificacion).where(
                        and_(
                            InvolucradoNotificacion.involucrado_id == involucrado.id,
                            InvolucradoNotificacion.notificacion_id == notif_id
                        )
                    )
                    await db.execute(stmt)

        # Eliminar la relación involucrado-expediente
        stmt_delete = delete(InvolucradoExpediente).where(
            and_(
                InvolucradoExpediente.involucrado_id == involucrado.id,
                InvolucradoExpediente.expediente_radicado == radicado
            )
        )
        result = await db.execute(stmt_delete)
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=404, 
                detail="No existe vinculación entre este involucrado y expediente"
            )
        
        # Un solo commit al final
        await db.commit()

        # Log de auditoría
        await insert_log_auditoria(
            db=db,
            usuario_id=int(usuario_id),
            tabla_afectada="involucrado_expediente",
            tipo_operacion="DELETE",
            descripcion=f"Desvinculado involucrado_id={involucrado.id} (doc={numero_documento}, tipo={tipo_documento}) del expediente radicado={radicado}"
        )
        
        return {
            "ok": True,
            "data": {
                "message": "Involucrado desvinculado exitosamente del expediente"
            }
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error desvinculando involucrado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/file/{radicado}")
async def obtener_involucrados_por_expediente(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    """Obtener todos los involucrados de un expediente"""
    try:
        usuario_id = verify_gateway_token(request)

        # Buscar expediente con involucrados
        stmt = (
            select(Expediente)
            .options(selectinload(Expediente.involucrados))
            .where(Expediente.radicado == radicado)
        )
        result = await db.execute(stmt)
        expediente = result.scalar_one_or_none()
        
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        
        involucrados_data = []
        for involucrado in expediente.involucrados:
            involucrados_data.append({
                "id": involucrado.id,
                "numero_documento": involucrado.numero_documento,
                "digito_verificacion": involucrado.digito_verificacion,
                "tipo_documento": involucrado.tipo_documento,
                "nombre": involucrado.nombre,
                "celular": involucrado.celular,
                "correo": involucrado.correo
            })
        
        return {
            "ok": True,
            "data": {
                "expediente_radicado": radicado,
                "involucrados": involucrados_data,
                "total": len(involucrados_data)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo involucrados del expediente: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{numero_documento}/{tipo_documento}/file")
async def obtener_expedientes_por_involucrado(
    request:Request,
    numero_documento: str,
    tipo_documento: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener todos los expedientes donde está involucrada una persona.
    Nota: Para NITs, esto retornará expedientes de TODOS los NITs con ese número,
    independientemente del DV. Considera filtrar por DV si es necesario.
    """
    try:
        usuario_id = verify_gateway_token(request)
        # Buscar involucrado con expedientes
        stmt = (
            select(Involucrado)
            .options(selectinload(Involucrado.expedientes))
            .where(
                and_(
                    Involucrado.numero_documento == numero_documento,
                    Involucrado.tipo_documento == tipo_documento
                )
            )
        )
        result = await db.execute(stmt)
        involucrados = result.scalars().all()

        if not involucrados:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")

        # Si hay múltiples NITs, combinar todos sus expedientes
        all_expedientes = []
        involucrado_info = None
        
        for involucrado in involucrados:
            if not involucrado_info:
                involucrado_info = {
                    "numero_documento": involucrado.numero_documento,
                    "tipo_documento": involucrado.tipo_documento,
                    "nombre": involucrado.nombre
                }
            
            for expediente in involucrado.expedientes:
                # Evitar duplicados
                if not any(exp["radicado"] == expediente.radicado for exp in all_expedientes):
                    all_expedientes.append({
                        "radicado": expediente.radicado,
                        "nombre_expediente": expediente.nombre_expediente,
                        "motivo_afectacion": expediente.motivo_afectacion,
                        "fecha_creacion": expediente.fecha_creacion.isoformat() if expediente.fecha_creacion else None
                    })

        return {
            "ok": True,
            "data": {
                "involucrado": involucrado_info,
                "expedientes": all_expedientes,
                "total": len(all_expedientes)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo expedientes del involucrado: {e}", exc_info=True)
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
    Requiere permiso: expediente_gestionar involucrados
    """
    try:
        from utils.verify_gateway_token import verify_permission
        user_id = verify_permission(request, "expediente_gestionar involucrados")
        
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


@router.put("/manage/{involucrado_id}")
async def editar_involucrado(
    request: Request,
    involucrado_id: int,
    involucrado_update: InvolucradoUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Edita un involucrado existente.
    Requiere permiso: expediente_gestionar involucrados
    """
    try:
        from utils.verify_gateway_token import verify_permission
        user_id = verify_permission(request, "expediente_gestionar involucrados")
        
        # Buscar involucrado
        stmt = select(Involucrado).where(Involucrado.id == involucrado_id)
        result = await db.execute(stmt)
        involucrado = result.scalar_one_or_none()
        
        if not involucrado:
            raise HTTPException(status_code=404, detail="Involucrado no encontrado")
        
        # Validar celular
        try:
            celular_int = int(involucrado_update.celular)
            if celular_int <= 0:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=400, detail="Celular inválido")
        
        # Validar DV si está presente
        if involucrado_update.digito_verificacion and len(involucrado_update.digito_verificacion) > 2:
            raise HTTPException(
                status_code=400,
                detail="Dígito de verificación no puede tener más de 2 caracteres"
            )
        
        # Actualizar campos
        involucrado.nombre = involucrado_update.nombre
        involucrado.celular = celular_int
        involucrado.correo = involucrado_update.correo.lower()
        involucrado.digito_verificacion = involucrado_update.digito_verificacion if involucrado_update.digito_verificacion else None
        
        await db.commit()
        await db.refresh(involucrado)
        
        # Log de auditoría
        await insert_log_auditoria(
            db=db,
            usuario_id=int(user_id),
            tabla_afectada="involucrado",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de involucrado id={involucrado.id} por usuario {user_id}"
        )
        
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