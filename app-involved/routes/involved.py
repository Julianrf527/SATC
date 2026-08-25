"""Rutas de gestión de involucrados (personas naturales/jurídicas del sistema SATC)."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Path, Body
from sqlalchemy import select, and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.permission import Permisos
from db.deps import get_db_managed
from db.models.auditoria import Auditoria
from db.models.involucrado import Involucrado
from services.auditoria import insert_auditoria
from services.users import get_user_info, verify_permission
from utils.functions import (
    format_involucrado_response,
    format_auditoria_response,
    resolver_identidad_usuario,
    verificar_involucrado_existe,
)
from utils.verify_token import verify_gateway_token, verify_service_token

from .models.involved_models import (
    InvolucradoCreate,
    InvolucradoUpdate,
    BulkInvolucradoRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)

INVOLVED_MANAGE = Permisos.INVOLVED_MANAGE
INVOLVED_LOG = Permisos.INVOLVED_LOG

# Búsqueda/creación de involucrados también se dispara desde el formulario de
# vinculación dentro de un expediente sancionatorio o de infracción, con el
# token propio del abogado — quien tiene permiso para gestionar su expediente
# debe poder buscar y crear el involucrado que va a vincular, aunque su rol
# no incluya el permiso de gestión del módulo de involucrados.
BUSCAR_O_CREAR_INVOLUCRADO = [
    Permisos.INVOLVED_MANAGE,
    Permisos.SANCIONATORIO_MANAGE,
    Permisos.INFRACCION_MANAGE,
]

# Techo duro para el filtrado en memoria del log de auditoría (ver obtener_auditoria).
MAX_FILAS_POST_FILTRO = 5000


async def _exigir_permiso(request: Request, permiso: str, mensaje: str) -> dict:
    """Valida gateway + permiso y devuelve la identidad del usuario.

    Un permiso faltante siempre es 403 y se resuelve ANTES de tocar la BD, para
    que la respuesta no dependa nunca de si el recurso pedido existe o no.
    """
    return await _exigir_alguno(request, [permiso], mensaje)


async def _exigir_alguno(request: Request, permisos: list[str], mensaje: str) -> dict:
    """Como `_exigir_permiso`, pero concede acceso si el usuario tiene
    cualquiera de los permisos listados (OR), no todos.
    """
    token_data = verify_gateway_token(request)
    for permiso in permisos:
        if await verify_permission(token_data["user_id"], permiso):
            return token_data
    raise HTTPException(status_code=403, detail=mensaje)


async def _registrar_auditoria_o_fallar(db: AsyncSession, **kwargs) -> None:
    """Inserta el registro de auditoría dentro de la transacción en curso.

    Si la auditoría no se puede escribir se aborta la operación completa: un
    cambio sobre datos personales sin traza es peor que no hacer el cambio.
    """
    resultado = await insert_auditoria(db=db, **kwargs)
    if not resultado.get("ok"):
        logger.error(f"Error al guardar auditoría: {resultado.get('error')}")
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")


def _contexto_peticion(request: Request) -> dict:
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


@router.get(
    "/search/{tipo_documento}/{numero_documento}",
    summary="Buscar involucrado por documento",
    description="Busca un involucrado por tipo y número de documento. Para NITs el dígito de verificación es opcional.",
    tags=["Involucrados - Consulta"],
    responses={
        200: {"description": "Resultado de la búsqueda (ok=false si no existe)"},
        400: {"description": "Número de documento inválido"},
        403: {"description": "No tiene permisos para consultar involucrados"},
    },
)
async def buscar_involucrado(
    request: Request,
    tipo_documento: str = Path(..., description="Tipo de documento (CC, NIT, CE, etc.)"),
    numero_documento: str = Path(..., description="Número de documento a buscar"),
    dv: Optional[str] = Query(None, description="Dígito de verificación (solo para NIT)", max_length=2),
    db: AsyncSession = Depends(get_db_managed),
):
    await _exigir_alguno(request, BUSCAR_O_CREAR_INVOLUCRADO, "No tiene permisos para consultar involucrados")

    try:
        numero_int = int(numero_documento)
    except ValueError:
        raise HTTPException(status_code=400, detail="Número de documento inválido. Debe ser numérico.")

    involucrado = await verificar_involucrado_existe(
        db=db,
        numero_documento=numero_int,
        tipo_documento=tipo_documento,
        digito_verificacion=dv,
    )

    if not involucrado:
        return {"ok": False, "data": None, "detail": "Involucrado no encontrado"}

    return {"ok": True, "data": format_involucrado_response(involucrado)}


@router.get(
    "/manage",
    summary="Listar involucrados con paginación",
    description="Lista involucrados con paginación y filtros opcionales. Requiere permiso de gestión.",
    tags=["Involucrados - Gestión"],
    responses={
        200: {"description": "Lista paginada de involucrados"},
        403: {"description": "No tiene permisos para gestionar involucrados"},
    },
)
async def listar_involucrados_paginado(
    request: Request,
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=100, description="Registros por página"),
    numero_documento: Optional[str] = Query(None, description="Filtrar por número de documento"),
    tipo_documento: Optional[str] = Query(None, description="Filtrar por tipo de documento"),
    nombre: Optional[str] = Query(None, description="Filtrar por nombre (búsqueda parcial)"),
    correo: Optional[str] = Query(None, description="Filtrar por correo (búsqueda parcial)"),
    db: AsyncSession = Depends(get_db_managed),
):
    await _exigir_permiso(request, INVOLVED_MANAGE, "No tiene permisos para gestionar involucrados")

    conditions = []

    if numero_documento:
        try:
            conditions.append(Involucrado.numero_documento == int(numero_documento))
        except ValueError:
            # Un filtro no numérico no puede casar con ninguna fila: lista vacía,
            # no un 400 que rompería el tipeo incremental del buscador.
            return {"ok": True, "data": [], "page": page, "limit": limit, "totalCount": 0}

    if tipo_documento:
        conditions.append(Involucrado.tipo_documento == tipo_documento)
    if nombre:
        conditions.append(Involucrado.nombre.ilike(f"%{nombre}%"))
    if correo:
        conditions.append(Involucrado.correo.ilike(f"%{correo}%"))

    query = select(Involucrado)
    count_query = select(func.count()).select_from(Involucrado)
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total_count = await db.scalar(count_query) or 0

    query = query.order_by(Involucrado.id.desc()).offset((page - 1) * limit).limit(limit)
    involucrados = (await db.execute(query)).scalars().all()

    return {
        "ok": True,
        "data": [format_involucrado_response(inv) for inv in involucrados],
        "page": page,
        "limit": limit,
        "totalCount": total_count,
    }


@router.get(
    "/log",
    summary="Consultar log de auditoría",
    description="Log de auditoría de involucrados con filtros y paginación. Requiere permiso de auditoría.",
    tags=["Involucrados - Auditoría"],
    responses={
        200: {"description": "Log de auditoría obtenido"},
        400: {"description": "Formato de fecha inválido"},
        403: {"description": "No tiene permisos para consultar logs"},
    },
)
async def obtener_auditoria(
    request: Request,
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(10, ge=1, le=500, description="Registros por página"),
    offset: Optional[int] = Query(None, ge=0, description="Offset (alternativa a page)"),
    usuario_id: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    documento_usuario: Optional[str] = Query(None, description="Filtrar por documento de usuario"),
    nombre_usuario: Optional[str] = Query(None, description="Filtrar por nombre de usuario"),
    tipo_evento: Optional[str] = Query(None, description="Filtrar por tipo de evento"),
    resultado: Optional[str] = Query(None, description="Filtrar por resultado (EXITOSO/ERROR)"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db_managed),
):
    await _exigir_permiso(request, INVOLVED_LOG, "No tiene permisos para consultar logs de auditoría")

    conditions = []
    if usuario_id:
        conditions.append(Auditoria.usuario_id == usuario_id)
    if tipo_evento:
        conditions.append(Auditoria.tipo_evento == tipo_evento)
    if resultado:
        conditions.append(Auditoria.resultado == resultado)

    if fecha_inicio:
        try:
            conditions.append(Auditoria.fecha >= datetime.fromisoformat(fecha_inicio))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_inicio inválido. Use YYYY-MM-DD")

    if fecha_fin:
        try:
            # Se extiende al final del día para que el rango sea inclusivo.
            fin = datetime.fromisoformat(fecha_fin).replace(hour=23, minute=59, second=59)
            conditions.append(Auditoria.fecha <= fin)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_fin inválido. Use YYYY-MM-DD")

    query = select(Auditoria)
    count_query = select(func.count()).select_from(Auditoria)
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total_count = await db.scalar(count_query) or 0
    effective_offset = offset if offset is not None else (page - 1) * limit

    # nombre_usuario/documento_usuario viven en app-users, no en esta BD, así que
    # solo se pueden aplicar después de resolver los usuarios. Eso obliga a traer
    # más filas de las que se devuelven; MAX_FILAS_POST_FILTRO acota el costo para
    # que el endpoint no cargue la tabla de auditoría entera en memoria.
    filtra_en_memoria = bool(documento_usuario or nombre_usuario)
    query = query.order_by(Auditoria.fecha.desc())
    if filtra_en_memoria:
        query = query.limit(MAX_FILAS_POST_FILTRO)
    else:
        query = query.offset(effective_offset).limit(limit)

    auditorias = (await db.execute(query)).scalars().all()

    user_ids = list({aud.usuario_id for aud in auditorias if aud.usuario_id})
    users_info = await get_user_info(user_ids) if user_ids else {}

    data = []
    for aud in auditorias:
        user_info = users_info.get(aud.usuario_id, {})
        usuario_nombre, usuario_documento = resolver_identidad_usuario(aud.usuario_id, user_info)

        if nombre_usuario and nombre_usuario.lower() not in usuario_nombre.lower():
            continue
        if documento_usuario and documento_usuario.strip() not in usuario_documento:
            continue

        data.append(format_auditoria_response(aud, user_info))

    if filtra_en_memoria:
        total_count = len(data)
        data = data[effective_offset:effective_offset + limit]

    return {
        "ok": True,
        "data": data,
        "msg": f"Se encontraron {total_count} registros",
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_count,
            "pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
        },
    }


@router.post(
    "/bulk",
    summary="Consulta masiva de involucrados",
    description="Obtiene múltiples involucrados por sus IDs. Endpoint service-to-service.",
    tags=["Involucrados - Interno"],
    responses={
        200: {"description": "Lista de involucrados obtenida"},
        403: {"description": "Service token ausente o inválido"},
    },
)
async def obtener_involucrados_bulk(
    request: Request,
    bulk_request: BulkInvolucradoRequest = Body(...),
    db: AsyncSession = Depends(get_db_managed),
):
    # Solo service-to-service: nunca se entra por gateway/frontend
    # (ver verify_service_token para por qué el X-Gateway-Token no basta).
    verify_service_token(request)

    conditions = [Involucrado.id.in_(bulk_request.ids)]
    if bulk_request.tipo_documento:
        conditions.append(Involucrado.tipo_documento == bulk_request.tipo_documento)

    involucrados = (await db.execute(select(Involucrado).where(and_(*conditions)))).scalars().all()
    data = [format_involucrado_response(inv) for inv in involucrados]

    return {"ok": True, "data": data, "total": len(data)}


@router.post(
    "/new",
    summary="Crear nuevo involucrado",
    description="Crea un nuevo involucrado. Requiere permiso de gestión.",
    tags=["Involucrados - Gestión"],
    status_code=201,
    responses={
        201: {"description": "Involucrado creado"},
        400: {"description": "El involucrado ya existe"},
        403: {"description": "No tiene permisos para gestionar involucrados"},
    },
)
async def crear_involucrado(
    request: Request,
    involucrado: InvolucradoCreate = Body(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = await _exigir_alguno(request, BUSCAR_O_CREAR_INVOLUCRADO, "No tiene permisos para gestionar involucrados")

    existing = await verificar_involucrado_existe(
        db=db,
        numero_documento=involucrado.numero_documento,
        tipo_documento=involucrado.tipo_documento,
        digito_verificacion=involucrado.digito_verificacion,
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un involucrado con documento {involucrado.numero_documento} ({involucrado.tipo_documento})",
        )

    nuevo = Involucrado(
        numero_documento=involucrado.numero_documento,
        digito_verificacion=involucrado.digito_verificacion,
        tipo_documento=involucrado.tipo_documento,
        nombre=involucrado.nombre,
        celular=involucrado.celular,
        correo=involucrado.correo.lower() if involucrado.correo else None,
        direccion=involucrado.direccion,
    )
    db.add(nuevo)
    try:
        await db.flush()
    except IntegrityError:
        # El check previo no cierra la ventana de carrera entre dos altas
        # concurrentes: la constraint UNIQUE es la fuente de verdad, y la
        # segunda request cae acá como 409 en vez de un 500 crudo de asyncpg.
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un involucrado con documento {involucrado.numero_documento} ({involucrado.tipo_documento})",
        )

    datos_involucrado = format_involucrado_response(nuevo)

    await _registrar_auditoria_o_fallar(
        db,
        usuario_id=token_data["user_id"],
        tipo_evento="CREAR_INVOLUCRADO",
        resultado="EXITOSO",
        detalle=f"Se registró el involucrado {involucrado.tipo_documento} {involucrado.numero_documento}: {involucrado.nombre}",
        datos_nuevos=datos_involucrado,
        **_contexto_peticion(request),
    )

    await db.commit()
    logger.info(f"Involucrado creado: {involucrado.tipo_documento}-{involucrado.numero_documento} (ID: {nuevo.id})")

    return {"ok": True, "data": datos_involucrado, "msg": "Involucrado creado exitosamente"}


@router.get(
    "/{involucrado_id}",
    summary="Obtener involucrado por ID",
    description="Obtiene los datos de un involucrado por su ID. Requiere permiso de gestión.",
    tags=["Involucrados - Consulta"],
    responses={
        200: {"description": "Involucrado encontrado"},
        403: {"description": "No tiene permisos para consultar involucrados"},
        404: {"description": "Involucrado no encontrado"},
    },
)
async def obtener_involucrado_por_id(
    request: Request,
    involucrado_id: int = Path(..., description="ID del involucrado", gt=0),
    db: AsyncSession = Depends(get_db_managed),
):
    await _exigir_permiso(request, INVOLVED_MANAGE, "No tiene permisos para consultar involucrados")

    involucrado = (
        await db.execute(select(Involucrado).where(Involucrado.id == involucrado_id))
    ).scalar_one_or_none()

    if not involucrado:
        raise HTTPException(status_code=404, detail="Involucrado no encontrado")

    return {"ok": True, "data": format_involucrado_response(involucrado)}


@router.put(
    "/{involucrado_id}",
    summary="Actualizar involucrado",
    description="Actualiza los datos de un involucrado. Requiere permiso de gestión.",
    tags=["Involucrados - Gestión"],
    responses={
        200: {"description": "Involucrado actualizado"},
        400: {"description": "El documento nuevo ya pertenece a otro involucrado"},
        403: {"description": "No tiene permisos para gestionar involucrados"},
        404: {"description": "Involucrado no encontrado"},
    },
)
async def actualizar_involucrado(
    request: Request,
    involucrado_id: int = Path(..., description="ID del involucrado a actualizar", gt=0),
    involucrado_update: InvolucradoUpdate = Body(...),
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = await _exigir_permiso(request, INVOLVED_MANAGE, "No tiene permisos para gestionar involucrados")

    involucrado = (
        await db.execute(select(Involucrado).where(Involucrado.id == involucrado_id))
    ).scalar_one_or_none()

    if not involucrado:
        raise HTTPException(status_code=404, detail="Involucrado no encontrado")

    datos_anteriores = format_involucrado_response(involucrado)

    # El modal del frontend no siempre manda todos los campos: sin exclude_unset
    # los ausentes se guardarían como None y borrarían celular/correo/dirección.
    cambios = involucrado_update.model_dump(exclude_unset=True)

    nuevo_num_doc = cambios.get("numero_documento")
    nuevo_tipo_doc = cambios.get("tipo_documento")
    doc_cambio = (
        (nuevo_num_doc is not None and nuevo_num_doc != involucrado.numero_documento)
        or (nuevo_tipo_doc is not None and nuevo_tipo_doc != involucrado.tipo_documento)
    )
    if doc_cambio:
        existing = await verificar_involucrado_existe(
            db=db,
            numero_documento=nuevo_num_doc if nuevo_num_doc is not None else involucrado.numero_documento,
            tipo_documento=nuevo_tipo_doc if nuevo_tipo_doc is not None else involucrado.tipo_documento,
            digito_verificacion=cambios.get("digito_verificacion", involucrado.digito_verificacion),
        )
        if existing and existing.id != involucrado_id:
            raise HTTPException(
                status_code=400,
                detail="Ya existe otro involucrado con ese documento",
            )

    if "correo" in cambios and cambios["correo"]:
        cambios["correo"] = cambios["correo"].lower()

    for campo, valor in cambios.items():
        setattr(involucrado, campo, valor)

    await db.flush()
    datos_nuevos = format_involucrado_response(involucrado)

    await _registrar_auditoria_o_fallar(
        db,
        usuario_id=token_data["user_id"],
        tipo_evento="ACTUALIZAR_INVOLUCRADO",
        resultado="EXITOSO",
        detalle=f"Se actualizaron los datos de {involucrado.tipo_documento} {involucrado.numero_documento}: {involucrado.nombre}",
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        **_contexto_peticion(request),
    )

    await db.commit()
    logger.info(f"Involucrado actualizado ID={involucrado_id}")

    return {"ok": True, "data": datos_nuevos, "msg": "Involucrado actualizado exitosamente"}
