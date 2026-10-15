"""/actos — corrección del acto administrativo, comunicación y notificaciones.

Mismos campos (multipart) y misma forma de respuesta (``{"ok", "data"}``) que
infraction (``acto_admin``, ``acto_comunicacion``, ``acto_notificacion``) para
que ``@features/acto-administrativo`` funcione con un ``ActoAdminEndpoints``
propio. El acto NO se crea aquí: lo crea cada etapa al "Cargar versión final"
(``services.actos.crear_acto``).

Permiso: escritura = ``requiere_gestion`` (V1) + encargado de la etapa dueña del
acto (``encargado_acto_id``) o super gestión. Lectura = ``requiere_lectura``.
Las escrituras bloquean el expediente (``FOR UPDATE``) antes de validar.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion, requiere_lectura, usuario_actual
from db.deps import get_db_managed
from db.models import ActoAdministrativo, Comunicacion, Notificacion, TipoNotificacion
from services.concurrencia import MSG_MODIFICADO, bloquear_expediente, integridad_a_409
import services.involved as involved_svc
from services.etapas import validar_pdf
from services.actos import (
    _decrementar,
    _incrementar,
    acciones_acto,
    contexto_acto,
    exigir_gestion_acto,
    involucrados_notificables,
    MSG_SIN_COMUNICACION,
    MSG_SIN_NOTIFICACION,
    se_comunica,
    se_notifica,
    validar_clase_acto,
    serializar_acto,
    serializar_comunicacion,
    serializar_notificacion,
    validar_fecha,
    validar_numerado,
    validar_numerado_disponible,
)

router = APIRouter()
logger = logging.getLogger(__name__)

MSG_EXPEDIENTE = "El expediente no corresponde al acto administrativo"


def _ok(data, status_code: int = 200) -> JSONResponse:
    return JSONResponse(content={"ok": True, "data": data}, status_code=status_code)


def _validar_expediente(expediente_id: Optional[int], etapa) -> None:
    if expediente_id is not None and int(expediente_id) != etapa.expediente_id:
        raise HTTPException(status_code=400, detail=MSG_EXPEDIENTE)


async def _contexto_escritura(db: AsyncSession, request: Request, acto_id: int, expediente_id: Optional[int]):
    usuario = await requiere_gestion(request)
    acto, etapa = await contexto_acto(db, acto_id)
    _validar_expediente(expediente_id, etapa)
    await bloquear_expediente(db, etapa.expediente_id)
    exigir_gestion_acto(etapa, usuario)
    return usuario, acto, etapa


# ═══════════════════════════════════════════════════════════ catálogo

@router.get("/tipos-notificacion", status_code=200)
async def listar_tipos_notificacion(request: Request, db: AsyncSession = Depends(get_db_managed)):
    await usuario_actual(request)
    tipos = (await db.execute(select(TipoNotificacion).order_by(TipoNotificacion.id))).scalars().all()
    return _ok([{"id": t.id, "nombre": t.nombre} for t in tipos])


# ═════════════════════════════════════════════════ acto administrativo

@router.get("/administrativos/{acto_id}", status_code=200)
async def obtener_acto(request: Request, acto_id: int, db: AsyncSession = Depends(get_db_managed)):
    """Acto + comunicación + notificaciones + involucrados notificables +
    ``acciones_disponibles`` del usuario."""
    usuario = await requiere_lectura(request)
    acto, etapa = await contexto_acto(db, acto_id)
    data = await serializar_acto(db, acto, etapa)
    notificables = await involucrados_notificables(db, etapa.expediente_id)
    datos = {
        int(d["id"]): d
        for d in await involved_svc.get_involucrados_by_ids(db, [i.involucrado_id for i in notificables])
        if isinstance(d, dict) and d.get("id") is not None
    }
    notificados = {n["involucrado_id"] for n in data["notificacion"]["involucrados"]}
    data["expediente_id"] = etapa.expediente_id
    data["involucrados_notificables"] = [
        {
            "involucrado_id": i.involucrado_id,
            "tipo_vinculo": i.tipo_vinculo.value if hasattr(i.tipo_vinculo, "value") else i.tipo_vinculo,
            "ya_notificado": i.involucrado_id in notificados,
            "datos": datos.get(i.involucrado_id),
        }
        for i in notificables
    ]
    data["acciones_disponibles"] = await acciones_acto(db, acto_id, usuario, etapa)
    return _ok(data)


@router.put("/administrativos/{acto_id}", status_code=200)
async def actualizar_acto(
    request: Request,
    acto_id: int,
    expediente_id: Optional[int] = Form(None),
    tipo_acto: Optional[str] = Form(None),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    documento_acto_administrativo_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """Corrección de Auto/Resolución, numerado, fecha de numerado y/o documento
    firmado. El formulario del front manda la forma (AUTO/RES) en el campo
    ``tipo_acto`` (contrato de infraction); aquí se guarda en ``clase_acto``.
    La clase interna (``acto.tipo_acto``: AUTO_ADMITE, DECISION…) la fija la
    etapa y no cambia."""
    usuario, acto, etapa = await _contexto_escritura(db, request, acto_id, expediente_id)
    clase = validar_clase_acto(tipo_acto) if tipo_acto else acto.clase_acto
    numero = validar_numerado(numerado)
    fecha = validar_fecha(fecha_numerado, "fecha de numerado")
    await validar_numerado_disponible(
        db, ActoAdministrativo, numero, fecha, excluir_id=acto.id, tipo_acto=acto.tipo_acto,
    )
    nuevo_doc = documento_acto_administrativo_id
    if nuevo_doc and nuevo_doc != acto.documento_acto_administrativo_id:
        await validar_pdf(nuevo_doc, "Acto administrativo")
        anterior = acto.documento_acto_administrativo_id
        await _incrementar([nuevo_doc])
        acto.documento_acto_administrativo_id = nuevo_doc
    else:
        anterior = None
    acto.clase_acto = clase
    acto.numerado = numero
    acto.fecha_numerado = fecha
    await db.flush()
    data = await serializar_acto(db, acto, etapa)
    await db.commit()
    if anterior:
        await _decrementar([anterior])
    logger.info(f"Acto {acto.id} corregido por {usuario.user_id}")
    return _ok(data)


@router.delete("/administrativos/{acto_id}", status_code=200)
async def eliminar_acto(
    request: Request,
    acto_id: int,
    expediente_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """Solo super gestión (cargue histórico): el acto nace de la versión final
    aprobada de la etapa y borrarlo dejaría la etapa sin acto con el proceso
    aprobado. TODO(negocio): confirmar si el encargado puede eliminarlo.
    Desenlaza la etapa, borra comunicación y notificaciones (cascada) y
    descuenta el uso de sus archivos."""
    usuario, acto, etapa = await _contexto_escritura(db, request, acto_id, expediente_id)
    if not usuario.super_gestion:
        raise HTTPException(
            status_code=403,
            detail="Solo super gestión puede eliminar un acto administrativo; para corregirlo usa editar",
        )
    data = await serializar_acto(db, acto, etapa)
    docs = [acto.documento_acto_administrativo_id]
    if data["comunicacion"]:
        docs.append(data["comunicacion"]["documento_comunicacion_id"])
    for n in data["notificacion"]["involucrados"]:
        docs += [n["documento_citacion_id"], n["documento_notificacion_id"]]
    etapa.etapa.acto_admin_id = None
    await db.flush()
    await db.delete(acto)
    await db.flush()
    await db.commit()
    await _decrementar(list({d for d in docs if d}))
    return _ok(data)


# ═══════════════════════════════════════════════════════════ comunicación

@router.post("/comunicaciones", status_code=201)
async def crear_comunicacion(
    request: Request,
    expediente_id: int = Form(...),
    acto_admin_id: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    documento_comunicacion_id: int = Form(...),
    db: AsyncSession = Depends(get_db_managed),
):
    """Una comunicación por acto (plan Etapa 1 paso 6): 409 si ya existe.
    Solo para los actos que se comunican (``ACTOS_SOLO_COMUNICACION``); 400 si no."""
    _, acto, _ = await _contexto_escritura(db, request, acto_admin_id, expediente_id)
    if not se_comunica(acto.tipo_acto):
        raise HTTPException(status_code=400, detail=MSG_SIN_COMUNICACION)
    numero = validar_numerado(numerado)
    f_numerado = validar_fecha(fecha_numerado, "fecha de numerado")
    f_envio = validar_fecha(fecha_envio, "fecha de envío")
    if await db.scalar(select(Comunicacion.id).where(Comunicacion.acto_administrativo_id == acto_admin_id)):
        raise HTTPException(status_code=409, detail="La comunicación ya existe para este acto administrativo")
    await validar_pdf(documento_comunicacion_id, "Documento de la comunicación")
    com = Comunicacion(
        acto_administrativo_id=acto_admin_id, numerado=numero, fecha_numerado=f_numerado,
        fecha_envio=f_envio, documento_comunicacion_id=documento_comunicacion_id,
    )
    async with integridad_a_409(db, "La comunicación ya existe para este acto administrativo"):
        db.add(com)
        await db.flush()
    await _incrementar([documento_comunicacion_id])
    data = serializar_comunicacion(com)
    await db.commit()
    return _ok(data, 201)


async def _comunicacion_escritura(db, request, comunicacion_id: int, expediente_id: Optional[int]):
    acto_id = await db.scalar(select(Comunicacion.acto_administrativo_id).where(Comunicacion.id == comunicacion_id))
    if acto_id is None:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")
    await _contexto_escritura(db, request, acto_id, expediente_id)
    com = await db.scalar(
        select(Comunicacion).where(Comunicacion.id == comunicacion_id).execution_options(populate_existing=True)
    )
    if com is None:
        raise HTTPException(status_code=404, detail="Comunicación no encontrada")
    return com


@router.put("/comunicaciones/{comunicacion_id}", status_code=200)
async def actualizar_comunicacion(
    request: Request,
    comunicacion_id: int,
    expediente_id: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio: str = Form(...),
    documento_comunicacion_id: int = Form(...),
    db: AsyncSession = Depends(get_db_managed),
):
    com = await _comunicacion_escritura(db, request, comunicacion_id, expediente_id)
    numero = validar_numerado(numerado)
    f_numerado = validar_fecha(fecha_numerado, "fecha de numerado")
    f_envio = validar_fecha(fecha_envio, "fecha de envío")
    anterior = None
    if documento_comunicacion_id != com.documento_comunicacion_id:
        await validar_pdf(documento_comunicacion_id, "Documento de la comunicación")
        anterior = com.documento_comunicacion_id
        await _incrementar([documento_comunicacion_id])
    com.numerado = numero
    com.fecha_numerado = f_numerado
    com.fecha_envio = f_envio
    com.documento_comunicacion_id = documento_comunicacion_id
    await db.flush()
    data = serializar_comunicacion(com)
    await db.commit()
    if anterior:
        await _decrementar([anterior])
    return _ok(data)


@router.delete("/comunicaciones/{comunicacion_id}", status_code=200)
async def eliminar_comunicacion(
    request: Request,
    comunicacion_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db_managed),
):
    """Body JSON ``{"expediente_id": n}`` (como infraction)."""
    expediente_id = data.get("expediente_id")
    if not expediente_id:
        raise HTTPException(status_code=422, detail="expediente_id es requerido")
    com = await _comunicacion_escritura(db, request, comunicacion_id, int(expediente_id))
    salida = serializar_comunicacion(com)
    await db.delete(com)
    await db.flush()
    await db.commit()
    await _decrementar([salida["documento_comunicacion_id"]])
    return _ok(salida)


# ═══════════════════════════════════════════════════════════ notificación

def _validar_entrega(
    notificacion_exitosa: bool, tipo_notificacion_id: Optional[int], documento_notificacion_id: Optional[int],
) -> None:
    if notificacion_exitosa and not tipo_notificacion_id:
        raise HTTPException(status_code=400, detail="Debe seleccionar un tipo de notificación si marca como exitosa")
    if notificacion_exitosa and not documento_notificacion_id:
        raise HTTPException(
            status_code=400, detail="Debe proporcionar un documento de notificación si marca como exitosa",
        )


async def _validar_tipo_notificacion(db: AsyncSession, tipo_notificacion_id: Optional[int]) -> None:
    if tipo_notificacion_id and not await db.scalar(
        select(TipoNotificacion.id).where(TipoNotificacion.id == tipo_notificacion_id)
    ):
        raise HTTPException(status_code=400, detail="Tipo de notificación inválido")


@router.post("/notificaciones", status_code=201)
async def crear_notificacion(
    request: Request,
    expediente_id: int = Form(...),
    acto_admin_id: int = Form(...),
    involucrado_id: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio_citacion: str = Form(...),
    fecha_constancia_citacion: Optional[str] = Form(None),
    documento_citacion_id: int = Form(...),
    notificacion_exitosa: bool = Form(False),
    tipo_notificacion_id: Optional[int] = Form(None),
    fecha_notificacion: Optional[str] = Form(None),
    documento_notificacion_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """Una fila por persona notificada. La citación siempre es obligatoria
    (numerado, fechas de envío y constancia, documento); la entrega (exitosa,
    tipo, fecha, documento) puede llenarse después con PUT."""
    _, acto, etapa = await _contexto_escritura(db, request, acto_admin_id, expediente_id)
    if not se_notifica(acto.tipo_acto):
        raise HTTPException(status_code=400, detail=MSG_SIN_NOTIFICACION)
    numero = validar_numerado(numerado)
    f_numerado = validar_fecha(fecha_numerado, "fecha de numerado")
    f_envio = validar_fecha(fecha_envio_citacion, "fecha de envío de la citación")
    f_constancia = validar_fecha(fecha_constancia_citacion, "fecha de constancia de la citación")
    f_notificacion = validar_fecha(fecha_notificacion, "fecha de notificación", requerida=False)
    _validar_entrega(notificacion_exitosa, tipo_notificacion_id, documento_notificacion_id)
    await _validar_tipo_notificacion(db, tipo_notificacion_id)

    notificables = {i.involucrado_id for i in await involucrados_notificables(db, etapa.expediente_id)}
    if involucrado_id not in notificables:
        raise HTTPException(status_code=400, detail="El involucrado no está vinculado a este expediente")
    if await db.scalar(select(Notificacion.id).where(
        Notificacion.acto_admin_id == acto.id, Notificacion.involucrado_id == involucrado_id,
    )):
        raise HTTPException(
            status_code=409, detail="Ya existe una notificación para este involucrado en este acto administrativo",
        )
    await validar_numerado_disponible(db, Notificacion, numero, f_numerado)
    await validar_pdf(documento_citacion_id, "Documento de la citación")
    if notificacion_exitosa:
        await validar_pdf(documento_notificacion_id, "Documento de la notificación")

    if notificacion_exitosa and f_notificacion is None:
        f_notificacion = validar_fecha(_hoy(), "fecha de notificación")
    n = Notificacion(
        acto_admin_id=acto.id,
        involucrado_id=involucrado_id,
        numerado=numero,
        fecha_numerado=f_numerado,
        fecha_envio_citacion=f_envio,
        fecha_constancia_citacion=f_constancia,
        documento_citacion_id=documento_citacion_id,
        notificacion_exitosa=notificacion_exitosa,
        tipo_notificacion_id=tipo_notificacion_id or None,
        fecha_notificacion=f_notificacion if notificacion_exitosa else None,
        documento_notificacion_id=documento_notificacion_id if notificacion_exitosa else None,
    )
    db.add(n)
    await db.flush()
    await _incrementar([documento_citacion_id, *( [documento_notificacion_id] if notificacion_exitosa else [])])
    data = serializar_notificacion(n)
    await db.commit()
    return _ok(data, 201)


def _hoy() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/Bogota")).date().isoformat()


async def _notificacion_escritura(db, request, notificacion_id: int, expediente_id: Optional[int]):
    acto_id = await db.scalar(select(Notificacion.acto_admin_id).where(Notificacion.id == notificacion_id))
    if acto_id is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    await _contexto_escritura(db, request, acto_id, expediente_id)
    n = await db.scalar(
        select(Notificacion).where(Notificacion.id == notificacion_id).execution_options(populate_existing=True)
    )
    if n is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return n


@router.put("/notificaciones/{notificacion_id}", status_code=200)
async def actualizar_notificacion(
    request: Request,
    notificacion_id: int,
    expediente_id: int = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    fecha_envio_citacion: str = Form(...),
    fecha_constancia_citacion: Optional[str] = Form(None),
    documento_citacion_id: int = Form(...),
    notificacion_exitosa: bool = Form(False),
    tipo_notificacion_id: Optional[int] = Form(None),
    fecha_notificacion: Optional[str] = Form(None),
    documento_notificacion_id: Optional[int] = Form(None),
    version: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """Edita citación y/o registra la entrega. ``version`` (opcional: el
    formulario heredado no la envía) activa el bloqueo optimista → 409."""
    n = await _notificacion_escritura(db, request, notificacion_id, expediente_id)
    if version is not None and version != n.version:
        raise HTTPException(status_code=409, detail=MSG_MODIFICADO)
    numero = validar_numerado(numerado)
    f_numerado = validar_fecha(fecha_numerado, "fecha de numerado")
    f_envio = validar_fecha(fecha_envio_citacion, "fecha de envío de la citación")
    f_constancia = validar_fecha(fecha_constancia_citacion, "fecha de constancia de la citación")
    f_notificacion = validar_fecha(fecha_notificacion, "fecha de notificación", requerida=False)
    _validar_entrega(notificacion_exitosa, tipo_notificacion_id, documento_notificacion_id)
    await _validar_tipo_notificacion(db, tipo_notificacion_id)
    await validar_numerado_disponible(db, Notificacion, numero, f_numerado, excluir_id=n.id)

    incrementar: list[int] = []
    decrementar: list[int] = []
    if documento_citacion_id != n.documento_citacion_id:
        await validar_pdf(documento_citacion_id, "Documento de la citación")
        incrementar.append(documento_citacion_id)
        decrementar.append(n.documento_citacion_id)
    doc_notif_nuevo = documento_notificacion_id if notificacion_exitosa else None
    if doc_notif_nuevo != n.documento_notificacion_id:
        if doc_notif_nuevo:
            await validar_pdf(doc_notif_nuevo, "Documento de la notificación")
        incrementar.append(doc_notif_nuevo)
        decrementar.append(n.documento_notificacion_id)

    if notificacion_exitosa and f_notificacion is None:
        f_notificacion = n.fecha_notificacion or validar_fecha(_hoy(), "fecha de notificación")
    n.numerado = numero
    n.fecha_numerado = f_numerado
    n.fecha_envio_citacion = f_envio
    n.fecha_constancia_citacion = f_constancia
    n.documento_citacion_id = documento_citacion_id
    n.notificacion_exitosa = notificacion_exitosa
    n.tipo_notificacion_id = tipo_notificacion_id or None
    n.fecha_notificacion = f_notificacion if notificacion_exitosa else None
    n.documento_notificacion_id = doc_notif_nuevo
    n.version = (n.version or 1) + 1
    await db.flush()
    await _incrementar([d for d in incrementar if d])
    data = serializar_notificacion(n)
    await db.commit()
    await _decrementar([d for d in decrementar if d])
    return _ok(data)


@router.delete("/notificaciones/{notificacion_id}", status_code=200)
async def eliminar_notificacion(
    request: Request,
    notificacion_id: int,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db_managed),
):
    """Body JSON ``{"expediente_id": n}`` (como infraction)."""
    expediente_id = data.get("expediente_id")
    if not expediente_id:
        raise HTTPException(status_code=422, detail="expediente_id es requerido")
    n = await _notificacion_escritura(db, request, notificacion_id, int(expediente_id))
    salida = serializar_notificacion(n)
    await db.delete(n)
    await db.flush()
    await db.commit()
    await _decrementar([salida["documento_citacion_id"], salida["documento_notificacion_id"]])
    return _ok(salida)
