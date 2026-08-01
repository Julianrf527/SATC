from fastapi import Request, APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime
from io import BytesIO
import logging

from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.etapa_ejecucion_sancion import EtapaEjecucionSancion
from db.models.acto_administrativo import ActoAdministrativo
from db.models.comunicacion import Comunicacion
from db.models.notificacion import Notificacion
from db.models.documento_anexo import DocumentoAnexo
from db.models.auditoria import Auditoria

from core.permission import Permission
from utils.verify_token import verify_gateway_token
from services.users import get_user_info, verify_permission
from services.docs import download_unified_pdf
from services.etapas import ETAPA_MODELS, ETAPA_LABELS

router = APIRouter()
LOG_PERMISSION = Permission.LOG_PERMISSION
logger = logging.getLogger(__name__)


@router.get("/audit/logs")
async def obtener_logs_auditoria(
    request: Request,
    usuario_id: int = Query(None, description="ID del usuario"),
    nombre_usuario: str = Query(None, description="Nombre del usuario"),
    cedula: str = Query(None, description="Número de documento/cédula del usuario"),
    expediente_radicado: str = Query(None, description="Radicado del expediente"),
    tipo_operacion: str = Query(None, description="Tipo de operación: INSERT, UPDATE, DELETE"),
    tabla_afectada: str = Query(None, description="Tabla afectada"),
    id_registro: str = Query(None, description="ID del registro"),
    fecha_inicio: str = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Obtiene los logs de auditoría filtrados por diferentes criterios.
    Solo accesible para usuarios con rol Admin o permisos especiales.
    """
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]
    if not await verify_permission(user_id, LOG_PERMISSION):
        raise HTTPException(status_code=403, detail="No cuenta con permisos para ver los logs de auditoría")

    # Sin JOIN a Usuario: esa tabla vive en otro microservicio
    query = select(
        Auditoria.id,
        Auditoria.usuario_id,
        Auditoria.tipo_evento,
        Auditoria.resultado,
        Auditoria.detalle,
        Auditoria.expediente_id,
        Auditoria.expediente_radicado,
        Auditoria.fecha,
        Auditoria.datos_anteriores,
        Auditoria.datos_nuevos
    )

    conditions = []

    if usuario_id:
        conditions.append(Auditoria.usuario_id == usuario_id)

    if expediente_radicado:
        conditions.append(Auditoria.expediente_radicado == expediente_radicado)

    if tipo_operacion:
        conditions.append(Auditoria.tipo_evento.ilike(f"{tipo_operacion.upper()}%"))

    if tabla_afectada:
        conditions.append(Auditoria.tipo_evento.ilike(f"%{tabla_afectada.upper()}%"))

    if id_registro:
        try:
            conditions.append(Auditoria.expediente_id == int(id_registro))
        except ValueError:
            conditions.append(Auditoria.expediente_radicado == id_registro)

    if fecha_inicio:
        try:
            fecha_inicio_date = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            conditions.append(Auditoria.fecha >= fecha_inicio_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha_inicio inválido. Use YYYY-MM-DD"
            )

    if fecha_fin:
        try:
            fecha_fin_date = datetime.strptime(fecha_fin, "%Y-%m-%d")
            # Incluir todo el día final
            fecha_fin_date = fecha_fin_date.replace(hour=23, minute=59, second=59)
            conditions.append(Auditoria.fecha <= fecha_fin_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha_fin inválido. Use YYYY-MM-DD"
            )

    if conditions:
        query = query.where(and_(*conditions))

    has_post_filter = bool(cedula or nombre_usuario)

    # Contar total de registros (solo útil cuando no hay filtro post-procesamiento)
    count_query = select(func.count()).select_from(Auditoria)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total_records = total_result.scalar()

    # Cuando hay filtro post-procesamiento, traer todos para filtrar en memoria
    if has_post_filter:
        query = query.order_by(Auditoria.fecha.desc())
    else:
        query = query.order_by(Auditoria.fecha.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.fetchall()

    # user_ids se nutre de dos fuentes: el actor de cada log y los IDs referenciados
    # dentro de datos_anteriores/datos_nuevos (ver collect_related_user_ids)
    user_ids = set(log.usuario_id for log in logs if log.usuario_id)

    _TIPO_EVENTO_MAP_SANC = {
        "CREAR_EXPEDIENTE":                        ("INSERT", "Expediente"),
        "ACTUALIZAR_EXPEDIENTE":                   ("UPDATE", "Expediente"),
        "ACTUALIZAR_ENCARGADO_EXPEDIENTE":         ("UPDATE", "Expediente"),
        "ACTUALIZAR_ENCARGADO_EXPEDIENTE_MASIVO":  ("UPDATE", "Expediente"),
        "ARCHIVAR_EXPEDIENTE":                     ("UPDATE", "Expediente"),
        "CREAR_ACTO_ADMIN":                        ("INSERT", "Acto Administrativo"),
        "ACTUALIZAR_ACTO_ADMIN":                   ("UPDATE", "Acto Administrativo"),
        "ELIMINAR_ACTO_ADMIN":                     ("DELETE", "Acto Administrativo"),
        "CREAR_COMUNICACION":                      ("INSERT", "Comunicación"),
        "ACTUALIZAR_COMUNICACION":                 ("UPDATE", "Comunicación"),
        "ELIMINAR_COMUNICACION":                   ("DELETE", "Comunicación"),
        "CREAR_NOTIFICACION":                      ("INSERT", "Notificación"),
        "ACTUALIZAR_NOTIFICACION":                 ("UPDATE", "Notificación"),
        "ELIMINAR_NOTIFICACION":                   ("DELETE", "Notificación"),
        "VINCULAR_INVOLUCRADO_EXPEDIENTE":         ("INSERT", "Involucrado"),
        "DESVINCULAR_INVOLUCRADO_EXPEDIENTE":      ("DELETE", "Involucrado"),
        "CONSULTA_EXPEDIENTES_INVOLUCRADO":        ("UPDATE", "Involucrado"),
    }

    def collect_related_user_ids(payload):
        if not isinstance(payload, dict):
            return
        for key in ("abogado_responsable_id", "encargado_id"):
            value = payload.get(key)
            if isinstance(value, int):
                user_ids.add(value)
            elif isinstance(value, str) and value.isdigit():
                user_ids.add(int(value))

    for log in logs:
        collect_related_user_ids(log.datos_anteriores)
        collect_related_user_ids(log.datos_nuevos)

    user_ids = list(user_ids)

    users_info = {}
    if user_ids:
        try:
            users_info = await get_user_info(user_ids)
            logger.info(f"Usuarios obtenidos: {len(users_info)} de {len(user_ids)} solicitados")
        except Exception as e:
            logger.warning(f"No se pudo obtener información de usuarios: {e}")
            # Placeholders para no romper el formateo si el servicio de usuarios falla
            users_info = {
                uid: {
                    "nombre": f"Usuario {uid}",
                    "correo": "",
                    "numero_documento": "",
                    "documento": "",
                }
                for uid in user_ids
            }

    logs_data = []
    def enrich_payload(payload):
        if not isinstance(payload, dict):
            return payload
        enriched = dict(payload)
        for key, prefix in (
            ("abogado_responsable_id", "abogado_responsable"),
            ("encargado_id", "encargado"),
        ):
            value = enriched.get(key)
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            if isinstance(value, int):
                info = users_info.get(value, {})
                if info.get("nombre"):
                    enriched[f"{prefix}_nombre"] = info.get("nombre")
                documento = info.get("numero_documento") or info.get("documento")
                if documento:
                    enriched[f"{prefix}_documento"] = documento
        return enriched

    for log in logs:
        user_info = users_info.get(log.usuario_id, {})
        usuario_nombre = (
            user_info.get("nombre")
            or (f"Usuario {log.usuario_id}" if log.usuario_id else "Usuario no identificado")
        )
        usuario_documento = str(
            user_info.get("numero_documento")
            or user_info.get("documento")
            or ""
        )
        usuario_correo = user_info.get("correo", "")

        if nombre_usuario:
            if nombre_usuario.lower() not in usuario_nombre.lower():
                continue

        if cedula:
            if cedula.strip() not in usuario_documento:
                continue

        _tipo_ev = log.tipo_evento or ""
        _op, _tabla = _TIPO_EVENTO_MAP_SANC.get(_tipo_ev, ("UPDATE", _tipo_ev))
        logs_data.append({
            "id": log.id,
            "usuario_id": log.usuario_id,
            "usuario_nombre": usuario_nombre,
            "usuario_documento": usuario_documento,
            "usuario_correo": usuario_correo,
            "tabla_afectada": _tabla,
            "tipo_operacion": _op,
            "tipo_evento": log.tipo_evento,
            "resultado": log.resultado,
            "descripcion": log.detalle,
            "expediente_radicado": log.expediente_radicado,
            "id_registro": log.expediente_id,
            "fecha": log.fecha.isoformat() if log.fecha else None,
            "datos_anteriores": enrich_payload(log.datos_anteriores),
            "datos_nuevos": enrich_payload(log.datos_nuevos),
        })

    # Si hubo filtro post-procesamiento, paginar en memoria y recalcular total
    if has_post_filter:
        total_records = len(logs_data)
        logs_data = logs_data[offset:offset + limit]

    return JSONResponse(
        content={
            "ok": True,
            "data": logs_data,
            "pagination": {
                "total": total_records,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_records
            },
            "msg": f"Se encontraron {total_records} registros"
        },
        status_code=200
    )

@router.get("/download-all/{expediente_id}")
async def descargar_todos_documentos(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    """
    Descarga todos los documentos de un expediente combinados en un único PDF.
    Los documentos se ordenan por etapa y se deduplican.
    """
    verify_gateway_token(request)

    # Endpoint intencionalmente público: no valida encargado_id, cualquier usuario
    # autenticado puede descargar el expediente completo. No agregar chequeo de permisos.
    row = (await db.execute(
        select(Expediente.encargado_id, Expediente.radicado)
        .where(Expediente.id == expediente_id)
    )).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")

    _, radicado = row

    logger.info(f"[DOWNLOAD-ALL] Iniciando descarga para expediente: {radicado}")

    # Orden de etapas según el frontend
    stage_order = [(Model, ETAPA_LABELS[Model], etapa_tipo) for etapa_tipo, Model in ETAPA_MODELS.items()]

    documentos_ids = []  # Lista de IDs de documentos en orden
    etapas_encontradas = 0

    for Model, nombre_etapa, etapa_tipo in stage_order:
        res_etapa = await db.execute(
            select(Model).where(Model.expediente_id == expediente_id)
        )
        etapa = res_etapa.scalar_one_or_none()
        if not etapa:
            continue

        etapas_encontradas += 1
        etapa_id = etapa.id
        logger.info(f"[DOWNLOAD-ALL] Procesando etapa: {nombre_etapa} (ID: {etapa_id})")

        # EtapaEjecucionSancion tiene documentos directos, sin acto_administrativo_id
        if Model is EtapaEjecucionSancion:
            for doc_field in (
                etapa.documento_acto_administrativo_id,
                etapa.documento_cobro_id,
                etapa.documento_ruia_id,
                etapa.documento_memorando_id,
            ):
                if doc_field:
                    documentos_ids.append(doc_field)
                    logger.info(f"Agregado doc ejecución (ID: {doc_field})")
        else:
            acto_ids = []
            if hasattr(etapa, "acto_administrativo_id") and etapa.acto_administrativo_id:
                acto_ids.append(etapa.acto_administrativo_id)
            # EtapaDecisionFondo también tiene acto_recurso_id
            if hasattr(etapa, "acto_recurso_id") and etapa.acto_recurso_id:
                acto_ids.append(etapa.acto_recurso_id)

            for acto_id in acto_ids:
                res_acto = await db.execute(
                    select(
                        ActoAdministrativo.id,
                        ActoAdministrativo.documento_acto_administrativo_id,
                        ActoAdministrativo.tipo_acto
                    ).where(ActoAdministrativo.id == acto_id)
                )
                acto_row = res_acto.one_or_none()
                if not acto_row:
                    continue
                _, doc_acto_id, tipo_acto = acto_row

                # 1. ACTO ADMINISTRATIVO
                if doc_acto_id:
                    documentos_ids.append(doc_acto_id)
                    logger.info(f"Agregado acto administrativo: {tipo_acto} (ID: {doc_acto_id})")

                # 2. COMUNICACIÓN O NOTIFICACIÓN
                stmt_com = select(Comunicacion.documento_comunicacion_id).where(
                    Comunicacion.acto_administrativo_id == acto_id
                )
                result_com = await db.execute(stmt_com)
                comunicacion_id = result_com.scalar_one_or_none()

                if comunicacion_id:
                    documentos_ids.append(comunicacion_id)
                    logger.info(f"Agregado comunicación (ID: {comunicacion_id})")
                else:
                    stmt_not = select(
                        Notificacion.documento_notificacion_id,
                        Notificacion.documento_citacion_id,
                        Notificacion.involucrado_id
                    ).where(Notificacion.acto_administrativo_id == acto_id)
                    result_not = await db.execute(stmt_not)
                    for id_notificacion, id_citacion, involucrado_id in result_not.all():
                        if id_citacion:
                            documentos_ids.append(id_citacion)
                            logger.info(f"Agregado citación para {involucrado_id} (ID: {id_citacion})")
                        if id_notificacion:
                            documentos_ids.append(id_notificacion)
                            logger.info(f"Agregado notificación para {involucrado_id} (ID: {id_notificacion})")

        # 3. DOCUMENTOS ANEXOS (polimórfico: etapa_tipo + etapa_ref_id)
        stmt_anexos = select(DocumentoAnexo.documento_anexo_id).where(
            and_(
                DocumentoAnexo.etapa_tipo == etapa_tipo,
                DocumentoAnexo.etapa_ref_id == etapa_id
            )
        ).order_by(DocumentoAnexo.fecha_subida.asc())
        result_anexos = await db.execute(stmt_anexos)
        for (doc_id,) in result_anexos.all():
            if doc_id:
                documentos_ids.append(doc_id)
                logger.info(f"Agregado documento anexo (ID: {doc_id})")

    if etapas_encontradas == 0:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron etapas para este expediente"
        )

    logger.info(f"[DOWNLOAD-ALL] Encontradas {etapas_encontradas} etapas")

    if not documentos_ids:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron documentos para este expediente"
        )

    logger.info(
        f"[DOWNLOAD-ALL] Total documentos únicos a combinar: {len(documentos_ids)}"
    )

    cookies_dict = {k: v for k, v in request.cookies.items()}

    resultado = await download_unified_pdf(
        file_ids=documentos_ids,
        cookies=cookies_dict
    )

    if not resultado.get("ok"):
        raise HTTPException(
            status_code=500,
            detail=f"Error generando PDF unificado: {resultado.get('message', 'Error desconocido')}"
        )

    filename = f"expediente_{radicado}_completo.pdf"

    logger.info(f"[DOWNLOAD-ALL] PDF generado exitosamente: {filename}")

    return StreamingResponse(
        BytesIO(resultado["content"]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
