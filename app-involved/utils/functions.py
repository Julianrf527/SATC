from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.involucrado import Involucrado
from db.models.auditoria import Auditoria


def format_involucrado_response(involucrado: Involucrado) -> dict:
    return {
        "id": involucrado.id,
        "numero_documento": involucrado.numero_documento,
        "digito_verificacion": involucrado.digito_verificacion,
        "tipo_documento": involucrado.tipo_documento,
        "nombre": involucrado.nombre,
        "celular": involucrado.celular,
        "correo": involucrado.correo,
        "direccion": involucrado.direccion,
    }


# El frontend de auditoría es común a todos los servicios y espera
# tipo_operacion/tabla_afectada; acá se derivan del tipo_evento propio.
_TIPO_EVENTO_MAP: dict[str, tuple[str, str]] = {
    "CREAR_INVOLUCRADO":      ("INSERT", "Involucrado"),
    "ACTUALIZAR_INVOLUCRADO": ("UPDATE", "Involucrado"),
}

_CAMPOS_OCULTOS = {"id"}


def _sanitize_datos(datos: dict | None) -> dict | None:
    if not isinstance(datos, dict):
        return datos
    return {k: v for k, v in datos.items() if k not in _CAMPOS_OCULTOS}


def resolver_identidad_usuario(usuario_id: int | None, user_info: dict | None) -> tuple[str, str]:
    """Nombre y documento a mostrar para un usuario_id de auditoría.

    app-users puede no responder (servicio caído o usuario borrado); en ese caso
    se degrada a un placeholder en vez de romper la consulta del log.
    """
    user_info = user_info or {}
    nombre = (
        user_info.get("nombre")
        or (f"Usuario {usuario_id}" if usuario_id else "Usuario no identificado")
    )
    documento = str(
        user_info.get("numero_documento")
        or user_info.get("documento")
        or ""
    )
    return nombre, documento


def format_auditoria_response(auditoria: Auditoria, user_info: dict | None = None) -> dict:
    tipo_evento = auditoria.tipo_evento or ""
    tipo_operacion, tabla_afectada = _TIPO_EVENTO_MAP.get(tipo_evento, ("UPDATE", tipo_evento))
    usuario_nombre, usuario_documento = resolver_identidad_usuario(auditoria.usuario_id, user_info)

    return {
        "id": auditoria.id,
        "usuario_id": auditoria.usuario_id,
        "documento_usuario": usuario_documento,
        "nombre_usuario": usuario_nombre,
        "usuario_documento": usuario_documento,
        "usuario_nombre": usuario_nombre,
        "usuario_correo": (user_info or {}).get("correo", ""),
        "tipo_evento": tipo_evento,
        "tipo_operacion": tipo_operacion,
        "tabla_afectada": tabla_afectada,
        "descripcion": auditoria.detalle,
        "expediente_radicado": None,
        "id_registro": None,
        "resultado": auditoria.resultado,
        "fecha": auditoria.fecha.isoformat() if auditoria.fecha else None,
        "detalle": auditoria.detalle,
        "datos_anteriores": _sanitize_datos(auditoria.datos_anteriores),
        "datos_nuevos": _sanitize_datos(auditoria.datos_nuevos),
    }


async def verificar_involucrado_existe(
    db: AsyncSession,
    numero_documento: int,
    tipo_documento: str,
    digito_verificacion: Optional[str] = None,
) -> Optional[Involucrado]:
    """Busca un involucrado por documento.

    El dígito de verificación solo discrimina en NITs y solo si se envía: sin él
    la búsqueda devuelve el NIT con ese número sea cual sea su dv, para no
    obligar al usuario a tipearlo.
    """
    conditions = [
        Involucrado.numero_documento == numero_documento,
        Involucrado.tipo_documento == tipo_documento,
    ]

    if tipo_documento == "NIT" and digito_verificacion:
        conditions.append(Involucrado.digito_verificacion == digito_verificacion)

    stmt = select(Involucrado).where(and_(*conditions))
    result = await db.execute(stmt)
    return result.scalars().first()
