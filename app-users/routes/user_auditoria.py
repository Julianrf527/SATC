"""Consulta de registros de auditoría del sistema (permiso USER_LOG)."""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, cast, String
from datetime import datetime
import logging

#----- DB -----
from db.deps import get_db_managed
from db.models.usuario import Usuario
from db.models.auditoria import Auditoria
from core.permissions import Permisos

router = APIRouter()
USER_LOG = Permisos.USER_LOG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#----------- FUNCIONES ----------
from utils.verify_token import verify_gateway_token
from utils.permission_crud import get_permissions_by_rol_id


async def _get_user_perm_names(rol_id: int, db: AsyncSession) -> set[str]:
    """Obtiene nombres de permisos del rol desde BD."""
    perms = await get_permissions_by_rol_id(rol_id, db)
    return {p["name"] for p in perms}

# ---------- ENDPOINTS ----------

@router.get("/log")
async def obtener_auditoria(
    request: Request,
    usuario_id: int = Query(None, description="ID del usuario"),
    cedula: str = Query(None, description="Número de documento/cédula del usuario"),
    nombre_usuario: str = Query(None, description="Nombre del usuario"),
    tipo_evento: str = Query(None, description="Tipo de evento: LOGIN, LOGOUT, CAMBIO_CONTRASENA, etc."),
    resultado: str = Query(None, description="Resultado: EXITOSO, FALLIDO"),
    fecha_inicio: str = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: AsyncSession = Depends(get_db_managed),
):
    """Registros de auditoría filtrados. Requiere el permiso USER_LOG."""
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if USER_LOG not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para ver los registros de auditoría"
        )

    query = select(
        Auditoria.id,
        Auditoria.usuario_id,
        Auditoria.tipo_evento,
        Auditoria.resultado,
        Auditoria.ip_address,
        Auditoria.detalle,
        Auditoria.fecha,
        Auditoria.datos_anteriores,
        Auditoria.datos_nuevos,
        Usuario.primer_nombre,
        Usuario.segundo_nombre,
        Usuario.primer_apellido,
        Usuario.segundo_apellido,
        Usuario.correo.label("usuario_correo"),
        Usuario.numero_documento.label("usuario_documento")
    ).join(
        Usuario, Auditoria.usuario_id == Usuario.id, isouter=True
    )

    conditions = []

    if usuario_id:
        conditions.append(Auditoria.usuario_id == usuario_id)

    if cedula:
        conditions.append(cast(Usuario.numero_documento, String).like(f"%{cedula.strip()}%"))

    if nombre_usuario:
        nombre_lower = f"%{nombre_usuario.lower()}%"
        nombre_conditions = or_(
            func.lower(Usuario.primer_nombre).like(nombre_lower),
            func.lower(Usuario.segundo_nombre).like(nombre_lower),
            func.lower(Usuario.primer_apellido).like(nombre_lower),
            func.lower(Usuario.segundo_apellido).like(nombre_lower),
            func.lower(func.concat(Usuario.primer_nombre, ' ', Usuario.primer_apellido)).like(nombre_lower),
            func.lower(func.concat(Usuario.primer_nombre, ' ', Usuario.segundo_nombre, ' ', Usuario.primer_apellido, ' ', Usuario.segundo_apellido)).like(nombre_lower)
        )
        conditions.append(nombre_conditions)

    if tipo_evento:
        conditions.append(Auditoria.tipo_evento == tipo_evento.upper())

    if resultado:
        conditions.append(Auditoria.resultado == resultado.upper())

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
            # Se extiende al final del día para que el rango sea inclusivo.
            fecha_fin_date = fecha_fin_date.replace(hour=23, minute=59, second=59)
            conditions.append(Auditoria.fecha <= fecha_fin_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha_fin inválido. Use YYYY-MM-DD"
            )

    if conditions:
        query = query.where(and_(*conditions))

    count_query = select(func.count()).select_from(Auditoria)
    if conditions:
        # El count solo necesita el join si algún filtro toca columnas de usuario.
        if nombre_usuario or cedula:
            count_query = count_query.join(
                Usuario, Auditoria.usuario_id == Usuario.id, isouter=True
            )
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total_records = total_result.scalar()

    query = query.order_by(Auditoria.fecha.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.fetchall()

    _TIPO_EVENTO_MAP = {
        "LOGIN":                  ("UPDATE", "Sesión"),
        "LOGOUT":                 ("UPDATE", "Sesión"),
        "GESTION_USUARIO":        ("INSERT", "Usuario"),
        "ACTIVACION":             ("UPDATE", "Usuario"),
        "DESACTIVACION":          ("UPDATE", "Usuario"),
        "CAMBIO_ROL":             ("UPDATE", "Usuario"),
        "CAMBIO_CONTRASENA":      ("UPDATE", "Contraseña"),
        "ACTUALIZACION_PERFIL":   ("UPDATE", "Usuario"),
        "EDICION_USUARIO":        ("UPDATE", "Usuario"),
        "RECUPERACION_CONTRASENA":("UPDATE", "Contraseña"),
        "REENVIO_CONTRASENA":     ("UPDATE", "Contraseña"),
    }
    _OCULTOS = {"id"}

    def _sanitize(datos):
        if not isinstance(datos, dict):
            return datos
        return {k: v for k, v in datos.items() if k not in _OCULTOS}

    logs_data = []
    for log in logs:
        nombre_partes = [
            log.primer_nombre,
            log.segundo_nombre,
            log.primer_apellido,
            log.segundo_apellido
        ]
        nombre_completo = " ".join([p for p in nombre_partes if p])
        usuario_nombre = (
            nombre_completo
            or (f"Usuario {log.usuario_id}" if log.usuario_id else "Usuario Desconocido")
        )
        tipo_evento = log.tipo_evento or ""
        tipo_operacion, tabla_afectada = _TIPO_EVENTO_MAP.get(tipo_evento, ("UPDATE", tipo_evento))

        logs_data.append({
            "id": log.id,
            "usuario_id": log.usuario_id,
            "usuario_nombre": usuario_nombre,
            "usuario_documento": log.usuario_documento,
            "usuario_correo": log.usuario_correo or "",
            "tipo_evento": tipo_evento,
            "tipo_operacion": tipo_operacion,
            "tabla_afectada": tabla_afectada,
            "descripcion": log.detalle,
            "id_registro": None,
            "resultado": log.resultado,
            "fecha": log.fecha.isoformat() if log.fecha else None,
            "detalle": log.detalle,
            "datos_anteriores": _sanitize(log.datos_anteriores),
            "datos_nuevos": _sanitize(log.datos_nuevos),
        })

    return JSONResponse(
        content={
            "ok": True,
            "msg": f"Se encontraron {len(logs_data)} registros de auditoría",
            "data": logs_data,
            "pagination": {
                "total": total_records,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_records
            }
        },
        status_code=200
    )
