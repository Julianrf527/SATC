"""Actos administrativos, comunicación y notificación (plan §4-E, Etapa 1 paso 6,
Etapa 4 "Citación y notificación", transversal tercero).

API interna para las etapas (agente C) — ninguna función hace commit:

- ``crear_acto(db, *, tipo_acto, clase_acto, numerado, fecha_numerado, documento_id, user_id)``:
  lo llama C al "Cargar versión final", en la misma transacción que
  ``revision_documentos.cargar_version_final``; C enlaza ``acto.id`` en la etapa.
- ``etapa_de_acto(db, acto_id)``: etapa dueña del acto (tabla, fila, expediente, encargado).
- ``involucrados_notificables(db, expediente_id)``: solicitantes y terceros.
- ``notificaciones_completas`` / ``acto_notificado``: para V13 (recurso solo si
  la decisión está notificada).
- ``serializar_acto(db, acto)``: forma ``ActoAdministrativo`` del front
  (``@features/acto-administrativo``) con comunicación y notificaciones.
- ``acciones_acto(db, acto_id, usuario)``: códigos de ``acciones_disponibles``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import Usuario
from db.models import (
    ActoAdministrativo,
    ActoAdmite,
    Comunicacion,
    Decision,
    ExpedienteInvolucrado,
    MemoriasCalculo,
    Notificacion,
    ReciboSatisfaccionObras,
    RecursoReposicion,
    Requerimiento,
    TipoActo,
)
from db.models.documento_proceso import DocumentoProceso
import services.docs as docs_svc

logger = logging.getLogger(__name__)

NUMERADO_MAX_DIGITOS = 4  # como infraction (el front exige 4 dígitos)
ANIO_CONTROL_DUPLICADOS = 2012  # infraction solo controla duplicados desde 2013

# Comunicar vs. notificar (regla del área, aclarada el 2026-10-14). ÚNICA
# definición en el backend; el front la replica en ``etapas/comun/actoFeature.ts``.
# - SOLO se comunican (nunca se notifican): el auto que admite y el acto que
#   reconoce a un tercero. La comunicación es pública (llega a todos, sin
#   distinguir), así que no hay notificaciones por persona.
# - Todos los demás actos SOLO se notifican (una fila por persona) y no tienen
#   comunicación.
ACTOS_SOLO_COMUNICACION = frozenset({TipoActo.AUTO_ADMITE, TipoActo.RECONOCE_TERCERO})
MSG_SIN_NOTIFICACION = "Este acto solo se comunica; no se notifica"
MSG_SIN_COMUNICACION = "Este acto solo se notifica; no se comunica"


def _tipo(tipo_acto: Any) -> Optional[TipoActo]:
    try:
        return TipoActo(tipo_acto.value if isinstance(tipo_acto, TipoActo) else tipo_acto)
    except ValueError:
        return None


def se_comunica(tipo_acto: Any) -> bool:
    """¿El acto lleva comunicación? (acepta el enum o su valor en texto)."""
    return _tipo(tipo_acto) in ACTOS_SOLO_COMUNICACION


def se_notifica(tipo_acto: Any) -> bool:
    """¿El acto admite notificaciones? Exactamente los que no se comunican."""
    return not se_comunica(tipo_acto)


# ═══════════════════════════════════════════════════════════ validaciones

def validar_numerado(numerado: Any) -> int:
    """Entero positivo de máximo 4 dígitos (como infraction). 400 si no."""
    texto = str(numerado).strip() if numerado is not None else ""
    if not texto.isdigit() or len(texto.lstrip("0") or "0") > NUMERADO_MAX_DIGITOS or int(texto) <= 0:
        raise HTTPException(
            status_code=400, detail="El numerado debe ser un número positivo de máximo 4 dígitos",
        )
    return int(texto)


def validar_fecha(valor: Any, campo: str, *, requerida: bool = True) -> Optional[date]:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = (str(valor).strip() if valor is not None else "")
    if not texto or texto in ("None", "null", "undefined"):
        if requerida:
            raise HTTPException(status_code=400, detail=f"La {campo} es obligatoria")
        return None
    try:
        return datetime.strptime(texto[:10], "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"La {campo} debe tener formato AAAA-MM-DD")


CLASES_ACTO = ("AUTO", "RES")


def validar_clase_acto(clase_acto: Any) -> str:
    """Auto o Resolución (``AUTO``/``RES``), lo elige quien carga o corrige el acto."""
    valor = str(clase_acto or "").strip().upper()
    if valor not in CLASES_ACTO:
        raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")
    return valor


def validar_tipo_acto(tipo_acto: Any) -> TipoActo:
    try:
        return TipoActo(tipo_acto.value if isinstance(tipo_acto, TipoActo) else str(tipo_acto))
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Tipo de acto inválido. Permitidos: {', '.join(t.value for t in TipoActo)}",
        )


async def _incrementar(file_ids: list[int]) -> None:
    file_ids = [f for f in file_ids if f]
    if not file_ids:
        return
    resultado = await docs_svc.increment_file_usage(file_ids)
    if not resultado.get("ok"):
        # Antes del commit: un archivo referenciado con numero_usos=0 se borraría.
        raise HTTPException(status_code=502, detail="No se pudo registrar el uso del archivo en el gestor documental")


async def _decrementar(file_ids: list[int]) -> None:
    file_ids = [f for f in file_ids if f]
    if file_ids:
        resultado = await docs_svc.decrement_file_usage(file_ids)
        if not resultado.get("ok"):  # inocuo: el archivo queda con un uso de más
            logger.warning(f"No se pudo decrementar el uso de {file_ids}: {resultado}")


async def validar_numerado_disponible(
    db: AsyncSession, modelo: type, numerado: int, fecha_numerado: date, *, excluir_id: int | None = None,
    tipo_acto: TipoActo | None = None,
) -> None:
    """Replica infraction: mismo ``numerado`` + misma ``fecha_numerado`` (desde
    2013) → 409. TODO(negocio): si la numeración se reinicia cada año, incluir el
    año en el índice ``(tipo_acto, numerado)`` y volverlo único (plan §7)."""
    if fecha_numerado.year <= ANIO_CONTROL_DUPLICADOS:
        return
    stmt = select(modelo.id).where(modelo.numerado == numerado, modelo.fecha_numerado == fecha_numerado)
    if tipo_acto is not None:
        stmt = stmt.where(modelo.tipo_acto == tipo_acto)
    if excluir_id is not None:
        stmt = stmt.where(modelo.id != excluir_id)
    if await db.scalar(stmt.limit(1)):
        raise HTTPException(
            status_code=409,
            detail=f"El numerado {numerado} con fecha {fecha_numerado.isoformat()} ya está en uso",
        )


# ═══════════════════════════════════════════════════════════ crear acto

async def crear_acto(
    db: AsyncSession,
    *,
    tipo_acto: TipoActo | str,
    clase_acto: str,
    numerado: int | str,
    fecha_numerado: date | str,
    documento_id: int,
    user_id: int,
) -> ActoAdministrativo:
    """Crea el ``acto_administrativo`` (número + fecha de numerado obligatorios,
    plan §4-E.3) e incrementa ``numero_usos`` del PDF firmado. C lo llama al
    cargar la versión final y enlaza ``acto.id`` en ``etapa.acto_admin_id``.

    Validaciones: tipo de ``TipoActo``; numerado entero positivo de máx. 4
    dígitos; fecha AAAA-MM-DD; ``documento_id`` > 0; numerado+fecha no repetido
    para el mismo tipo de acto (409). TODO(negocio): numeración por año (plan §7,
    el índice ``(tipo_acto, numerado)`` no es único). Errores como
    ``HTTPException`` (400/409/502). No hace commit."""
    tipo = validar_tipo_acto(tipo_acto)
    clase = validar_clase_acto(clase_acto)
    numero = validar_numerado(numerado)
    fecha = validar_fecha(fecha_numerado, "fecha de numerado")
    if not documento_id or int(documento_id) <= 0:
        raise HTTPException(status_code=400, detail="El documento del acto es obligatorio")
    await validar_numerado_disponible(db, ActoAdministrativo, numero, fecha, tipo_acto=tipo)
    acto = ActoAdministrativo(
        tipo_acto=tipo, clase_acto=clase, numerado=numero, fecha_numerado=fecha,
        documento_acto_administrativo_id=int(documento_id),
    )
    db.add(acto)
    await db.flush()
    await _incrementar([int(documento_id)])
    logger.info(f"Acto {tipo.value} {numero} creado por {user_id} (id {acto.id})")
    return acto


# ═══════════════════════════════════════════════════════════ etapa dueña

@dataclass
class EtapaActo:
    etapa_tipo: str          # tabla dueña (mismo valor que documento_proceso.etapa_tipo)
    etapa: Any               # fila ORM
    expediente_id: Optional[int]
    encargado_id: Optional[int]


# (tabla, modelo) en orden de búsqueda. Todas tienen ``acto_admin_id`` único.
TABLAS_CON_ACTO: tuple[tuple[str, type], ...] = (
    ("acto_admite", ActoAdmite),
    ("requerimiento", Requerimiento),
    ("decision", Decision),
    ("recurso_reposicion", RecursoReposicion),
    ("memorias_calculo", MemoriasCalculo),
    ("recibo_satisfaccion_obras", ReciboSatisfaccionObras),
    ("expediente_involucrado", ExpedienteInvolucrado),
)


async def _expediente_de_requerimiento(db: AsyncSession, req: Requerimiento) -> Optional[int]:
    """Etapa 3 tiene ``expediente_id``; como sub-proceso lo tiene el padre."""
    if req.expediente_id:
        return req.expediente_id
    for modelo in (MemoriasCalculo, ReciboSatisfaccionObras):
        exp = await db.scalar(select(modelo.expediente_id).where(modelo.requerimiento_id == req.id))
        if exp:
            return exp
    return await db.scalar(select(DocumentoProceso.expediente_id).where(
        DocumentoProceso.etapa_tipo == "requerimiento", DocumentoProceso.etapa_ref_id == req.id,
    ).limit(1))


async def _encargado_por_proceso(db: AsyncSession, etapa_tipo: str, etapa_ref_id: int) -> Optional[int]:
    """Encargado de una etapa sin columna ``encargado_acto_id`` (acto que reconoce
    al tercero): el creador de su proceso de revisión (vigente o el último)."""
    return await db.scalar(
        select(DocumentoProceso.creador_id)
        .where(DocumentoProceso.etapa_tipo == etapa_tipo, DocumentoProceso.etapa_ref_id == etapa_ref_id)
        .order_by(DocumentoProceso.activo.desc(), DocumentoProceso.id.desc())
        .limit(1)
    )


async def etapa_de_acto(db: AsyncSession, acto_id: int) -> Optional[EtapaActo]:
    """Busca la fila de etapa que referencia el acto en todas las tablas con
    ``acto_admin_id`` y resuelve su expediente y su encargado (``None`` si el
    acto no está enlazado a ninguna)."""
    for etapa_tipo, modelo in TABLAS_CON_ACTO:
        fila = await db.scalar(select(modelo).where(modelo.acto_admin_id == acto_id))
        if fila is None:
            continue
        if etapa_tipo == "requerimiento":
            expediente_id = await _expediente_de_requerimiento(db, fila)
        elif etapa_tipo == "recurso_reposicion":
            expediente_id = await db.scalar(select(Decision.expediente_id).where(Decision.id == fila.decision_id))
        else:
            expediente_id = fila.expediente_id
        if etapa_tipo == "expediente_involucrado":
            encargado = await _encargado_por_proceso(db, etapa_tipo, fila.id)
        else:
            encargado = fila.encargado_acto_id
        return EtapaActo(etapa_tipo, fila, expediente_id, encargado)
    return None


async def contexto_acto(db: AsyncSession, acto_id: int) -> tuple[ActoAdministrativo, EtapaActo]:
    """(acto, etapa dueña). 404 si el acto no existe o no está enlazado."""
    acto = await db.scalar(select(ActoAdministrativo).where(ActoAdministrativo.id == acto_id))
    if acto is None:
        raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")
    etapa = await etapa_de_acto(db, acto_id)
    if etapa is None or etapa.expediente_id is None:
        raise HTTPException(status_code=404, detail="El acto administrativo no está enlazado a ninguna etapa")
    return acto, etapa


def puede_gestionar_acto(etapa: EtapaActo, usuario: Usuario) -> bool:
    """Encargado de la etapa dueña (``encargado_acto_id``) o super gestión."""
    return usuario.super_gestion or (etapa.encargado_id is not None and etapa.encargado_id == usuario.user_id)


def exigir_gestion_acto(etapa: EtapaActo, usuario: Usuario) -> None:
    if not puede_gestionar_acto(etapa, usuario):
        raise HTTPException(
            status_code=403, detail="Solo el encargado de la etapa (o super gestión) puede gestionar este acto",
        )


# ═══════════════════════════════════════════════════════ notificaciones

async def involucrados_notificables(db: AsyncSession, expediente_id: int) -> list[ExpedienteInvolucrado]:
    """Solicitantes y terceros intervinientes del expediente (plan Etapa 4: "se
    notifica a cada solicitante y a cada tercero interviniente").
    TODO(negocio): el tercero se notifica de las actuaciones "siguientes" a su
    vinculación; no se filtra por fecha porque el plan no lo exige."""
    return list((await db.execute(
        select(ExpedienteInvolucrado)
        .where(ExpedienteInvolucrado.expediente_id == expediente_id)
        .order_by(ExpedienteInvolucrado.tipo_vinculo, ExpedienteInvolucrado.id)
    )).scalars().all())


async def notificaciones_completas(db: AsyncSession, acto_id: int) -> dict:
    """Estado de notificación del acto: ``{"total", "exitosas", "notificado"}``.

    TODO(negocio): el plan no define "acto notificado". Regla provisional: hay
    al menos una notificación y TODAS tienen ``notificacion_exitosa = true``
    (no exige que cada solicitante/tercero tenga la suya)."""
    filas = (await db.execute(
        select(Notificacion.notificacion_exitosa).where(Notificacion.acto_admin_id == acto_id)
    )).scalars().all()
    total = len(filas)
    exitosas = sum(1 for x in filas if x)
    return {"total": total, "exitosas": exitosas, "notificado": total > 0 and exitosas == total}


async def acto_notificado(db: AsyncSession, acto_id: int) -> bool:
    """V13: ver ``notificaciones_completas`` (TODO(negocio))."""
    return (await notificaciones_completas(db, acto_id))["notificado"]


# ═══════════════════════════════════════════════════════════ serializar

def _iso(valor) -> Optional[str]:
    return valor.isoformat() if valor else None


def serializar_comunicacion(com: Optional[Comunicacion]) -> Optional[dict]:
    if com is None:
        return None
    return {
        "id": com.id,
        "acto_administrativo_id": com.acto_administrativo_id,
        "numerado": com.numerado,
        "fecha_numerado": _iso(com.fecha_numerado),
        "fecha_envio": _iso(com.fecha_envio),
        "documento_comunicacion_id": com.documento_comunicacion_id,
        "fecha_creacion": _iso(com.fecha_creacion),
    }


def serializar_notificacion(n: Notificacion) -> dict:
    """Misma forma que infraction (``InvolucradoNotificacion`` del front) + ``version``."""
    return {
        "id": n.id,
        "acto_administrativo_id": n.acto_admin_id,
        "acto_admin_id": n.acto_admin_id,
        "involucrado_id": n.involucrado_id,
        "numerado": n.numerado,
        "fecha_numerado": _iso(n.fecha_numerado),
        "fecha_envio_citacion": _iso(n.fecha_envio_citacion),
        "fecha_constancia_citacion": _iso(n.fecha_constancia_citacion),
        "documento_citacion_id": n.documento_citacion_id,
        "notificacion_exitosa": bool(n.notificacion_exitosa),
        "tipo_notificacion_id": n.tipo_notificacion_id,
        "documento_notificacion_id": n.documento_notificacion_id,
        "fecha_notificacion": _iso(n.fecha_notificacion),
        "fecha_creacion": _iso(n.fecha_creacion),
        "version": n.version,
    }


async def serializar_acto(db: AsyncSession, acto: ActoAdministrativo, etapa: EtapaActo | None = None) -> dict:
    """Forma ``ActoAdministrativo`` de ``@features/acto-administrativo``:
    ``comunicacion`` (o null) y ``notificacion = {id, fecha_creacion,
    involucrados: [...]}`` (``id`` = id del acto: aquí no hay cabecera de
    notificación, hay una fila por persona)."""
    com = await db.scalar(select(Comunicacion).where(Comunicacion.acto_administrativo_id == acto.id))
    notifs = (await db.execute(
        select(Notificacion).where(Notificacion.acto_admin_id == acto.id).order_by(Notificacion.id)
    )).scalars().all()
    estado_notif = await notificaciones_completas(db, acto.id)
    tipo = acto.tipo_acto.value if isinstance(acto.tipo_acto, TipoActo) else acto.tipo_acto
    return {
        "id": acto.id,
        "tipo_acto": tipo,
        "clase_acto": acto.clase_acto,
        "numerado": acto.numerado,
        "fecha_numerado": _iso(acto.fecha_numerado),
        "documento_acto_administrativo_id": acto.documento_acto_administrativo_id,
        "documento_acto_id": acto.documento_acto_administrativo_id,  # alias de infraction
        "fecha_creacion": _iso(acto.fecha_creacion),
        "etapa_tipo": etapa.etapa_tipo if etapa else None,
        "etapa_id": etapa.etapa.id if etapa else None,
        "comunicacion": serializar_comunicacion(com),
        "notificacion": {
            "id": acto.id,
            "fecha_creacion": _iso(acto.fecha_creacion),
            "involucrados": [serializar_notificacion(n) for n in notifs],
        },
        "notificado": estado_notif["notificado"],
    }


async def acciones_acto(db: AsyncSession, acto_id: int, usuario: Usuario, etapa: EtapaActo | None = None) -> list[str]:
    """Códigos de ``acciones_disponibles`` sobre el acto para este usuario:
    ``editar_acto``, ``eliminar_acto`` (solo super gestión), ``crear_comunicacion``
    / ``editar_comunicacion`` / ``eliminar_comunicacion``, ``crear_notificacion``
    (si queda algún involucrado sin notificación), ``editar_notificacion``,
    ``eliminar_notificacion``."""
    etapa = etapa or await etapa_de_acto(db, acto_id)
    if etapa is None or not puede_gestionar_acto(etapa, usuario):
        return []
    acciones = ["editar_acto"]
    if usuario.super_gestion:
        acciones.append("eliminar_acto")
    tipo_acto = await db.scalar(select(ActoAdministrativo.tipo_acto).where(ActoAdministrativo.id == acto_id))
    tiene_com = await db.scalar(select(Comunicacion.id).where(Comunicacion.acto_administrativo_id == acto_id))
    notificados = set((await db.execute(
        select(Notificacion.involucrado_id).where(Notificacion.acto_admin_id == acto_id)
    )).scalars().all())
    notificables: set[int] = set()
    if etapa.expediente_id is not None and se_notifica(tipo_acto):
        notificables = {i.involucrado_id for i in await involucrados_notificables(db, etapa.expediente_id)}
    return acciones + acciones_comunicacion_notificacion(tipo_acto, bool(tiene_com), notificados, notificables)


def acciones_comunicacion_notificacion(
    tipo_acto: Any, tiene_comunicacion: bool, notificados: set[int], notificables: set[int],
) -> list[str]:
    """Acciones de comunicación/notificación según el tipo del acto (ver
    ``ACTOS_SOLO_COMUNICACION``). Datos heredados que no cumplen la regla
    (comunicación en un acto que solo se notifica, o al revés) se pueden
    editar y eliminar, pero no se ofrece crear más."""
    acciones: list[str] = []
    if tiene_comunicacion:
        acciones += ["editar_comunicacion", "eliminar_comunicacion"]
    elif se_comunica(tipo_acto):
        acciones.append("crear_comunicacion")
    if se_notifica(tipo_acto) and notificables - notificados:
        acciones.append("crear_notificacion")
    if notificados:
        acciones += ["editar_notificacion", "eliminar_notificacion"]
    return acciones
