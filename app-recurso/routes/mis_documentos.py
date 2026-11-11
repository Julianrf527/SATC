"""/mis-documentos — pestaña "Mis informes" (plan §1 y §5.5).

Una sola lista paginada ``documentos`` con TODOS los procesos del usuario
actual, en cualquier estado y vigentes o no (``activo = false``: cerrados o
reemplazados; son su histórico), igual que "Mis Informes" de infraction:

- Rol **encargado**: procesos donde es el ``creador_id``. Requiere su acción
  en ``pendiente_carga`` (proyectar la primera versión), ``rechazado`` (subir
  la corrección) y ``aprobado_firma`` (cargar la versión firmada desde la
  etapa), solo si el proceso sigue vigente.
- Rol **revisor**: procesos cuya cadena incluye algún permiso de revisor del
  usuario y en los que (a) ya registró alguna revisión, o (b) están
  vigentes, ``en_revision`` y con el paso actual pidiendo un permiso suyo aún sin revisar
  (eso último es lo que requiere su acción). Un líder NO ve todos los
  procesos de su cadena: solo aquellos en los que participó o le toca.

Si el usuario es encargado y revisor del mismo proceso sale UNA fila con
``roles = ["encargado", "revisor"]`` (como infraction: una fila por informe
con las marcas de rol); ``rol`` es el rol principal (encargado primero).

Paginación como el listado de informes de infraction (``page``, ``limit`` →
``total``, ``page``, ``limit``, ``total_pages``). Los ``conteos`` y ``total``
son sobre todo el conjunto filtrado, no sobre la página. Filtro, conteos, orden
y paginación se resuelven en SQL (``_puedo_revisar_sql`` traduce las cadenas de
revisión a condiciones por paso/permiso): solo se cargan los procesos de la
página, así el costo no crece con el histórico del usuario. Resúmenes,
expedientes y etapa padre se leen solo para la página.

Cualquier usuario autenticado puede consultarla (ve solo lo suyo). Los permisos
del usuario se resuelven UNA vez por petición (cache de services.users).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import and_, case, exists, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import usuario_actual
from db.deps import get_db_managed
from db.models import Expediente
from db.models.documento_proceso import DocumentoProceso, DocumentoProcesoRevision
from services.etapas import etapas_padre
from services.revision_documentos import (
    APROBADO,
    APROBADO_FIRMA,
    CADENAS,
    EN_REVISION,
    ESTADOS_POR_SUBIR,
    FINALIZADO,
    FLUJO,
    PENDIENTE_CARGA,
    RECHAZADO,
    etiqueta_etapa,
    permisos_de_usuario,
    resumenes_procesos,
)

router = APIRouter()

ENCARGADO = "encargado"
REVISOR = "revisor"
ROLES = ({"codigo": ENCARGADO, "etiqueta": "Encargado"}, {"codigo": REVISOR, "etiqueta": "Revisor"})

ESTADOS_LISTA = (PENDIENTE_CARGA, EN_REVISION, RECHAZADO, APROBADO_FIRMA, APROBADO, FINALIZADO)

ACCION_ENCARGADO = {
    PENDIENTE_CARGA: "Proyectar y subir la primera versión",
    RECHAZADO: "Subir la versión corregida",
    APROBADO_FIRMA: "Cargar la versión firmada desde la etapa",
}
ACCION_REVISOR = "Revisar el documento"


def _fecha(valor: Optional[datetime]) -> Optional[str]:
    return valor.isoformat() if valor else None


def _datos_expediente(exp: tuple[str, str] | None) -> dict:
    radicado, codigo = exp or (None, None)
    return {"expediente_radicado": radicado, "expediente_codigo": codigo}


def _fila(
    p: DocumentoProceso,
    exp: tuple[str, str] | None,
    resumen: dict,
    roles: list[str],
    contexto: dict,
) -> dict:
    accion_encargado = (
        ACCION_ENCARGADO.get(p.estado) if ENCARGADO in roles and resumen["soy_encargado"] and p.activo else None
    )
    accion_revisor = ACCION_REVISOR if REVISOR in roles and resumen["puedo_revisar"] else None
    accion = accion_encargado or accion_revisor
    return {
        **resumen,
        "rol": roles[0],
        "roles": roles,
        # Con filtro de rol, solo cuenta la acción de ese rol.
        "requiere_mi_accion": accion is not None,
        "accion_pendiente": accion,
        "expediente_id": p.expediente_id,
        **_datos_expediente(exp),
        "etapa_tipo": p.etapa_tipo,
        "etapa_etiqueta": etiqueta_etapa(p.etapa_tipo),
        "etapa_ref_id": p.etapa_ref_id,
        # Agente C: etapa del plan (pestaña) a la que pertenece: etapa_padre, etapa_padre_etiqueta, sub_proceso.
        **contexto,
        "nombre": p.nombre,
        "fecha_creacion": _fecha(p.fecha_creacion),
        "fecha_ultima_actualizacion": _fecha(p.fecha_ultima_actualizacion),
    }


def _puedo_revisar_sql(mios: frozenset[str], tipos: list[str]):
    """Condición SQL equivalente a ``puedo_revisar`` de ``_resumen``: proceso
    vigente en revisión cuyo paso actual pide un permiso mío que aún no revisó
    en ese paso. Una rama por (tipo, paso, permiso) de las cadenas (pocas)."""
    ramas = []
    for tipo in tipos:
        for paso, permisos in enumerate(CADENAS[tipo].pasos):
            for permiso in permisos:
                if permiso not in mios:
                    continue
                ya_reviso = exists().where(
                    DocumentoProcesoRevision.proceso_id == DocumentoProceso.id,
                    DocumentoProcesoRevision.paso == paso,
                    DocumentoProcesoRevision.permiso == permiso,
                )
                ramas.append(and_(
                    DocumentoProceso.tipo_documento == tipo,
                    func.coalesce(DocumentoProceso.paso_actual, 0) == paso,
                    ~ya_reviso,
                ))
    if not ramas:
        return false()
    return and_(DocumentoProceso.activo.is_(True), DocumentoProceso.estado == EN_REVISION, or_(*ramas))


@router.get("", status_code=200)
async def mis_documentos(
    request: Request,
    rol: Optional[Literal["encargado", "revisor"]] = Query(None, description="Solo filas con este rol"),
    solo_accion: bool = Query(False, description="Solo los que requieren mi acción"),
    expediente: Optional[str] = Query(None, description="Radicado o código CA (búsqueda parcial)"),
    tipo_documento: Optional[str] = Query(None, description="Clave de la cadena, p. ej. AUTO_ADMITE"),
    estado: Optional[str] = Query(None, description="Código de estado del proceso"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = (await usuario_actual(request)).user_id
    mios = await permisos_de_usuario(user_id)

    filtros = []
    if tipo_documento:
        filtros.append(DocumentoProceso.tipo_documento == tipo_documento)
    if estado:
        filtros.append(DocumentoProceso.estado == estado)
    if expediente and expediente.strip():
        patron = f"%{expediente.strip()}%"
        filtros.append(DocumentoProceso.expediente_id.in_(
            select(Expediente.id).where(or_(Expediente.radicado.ilike(patron), Expediente.expediente.ilike(patron)))
        ))

    ver_encargado = rol in (None, ENCARGADO)
    tipos_revisor = [t for t, c in CADENAS.items() if c.permisos & mios] if rol in (None, REVISOR) else []
    revisados_por_mi = (
        select(DocumentoProcesoRevision.proceso_id).where(DocumentoProcesoRevision.revisor_id == user_id)
    )

    soy_encargado = DocumentoProceso.creador_id == user_id if ver_encargado else false()
    puedo_revisar = _puedo_revisar_sql(mios, tipos_revisor)
    soy_revisor = (
        and_(DocumentoProceso.tipo_documento.in_(tipos_revisor),
             or_(DocumentoProceso.id.in_(revisados_por_mi), puedo_revisar))
        if tipos_revisor else false()
    )
    # Misma regla que _fila: acción de encargado (vigente y por subir) o de revisor.
    requiere = or_(
        and_(soy_encargado, DocumentoProceso.activo.is_(True), DocumentoProceso.estado.in_(ESTADOS_POR_SUBIR)),
        puedo_revisar,
    )
    base = [*filtros, or_(soy_encargado, soy_revisor)]

    total_todos, con_accion = (await db.execute(
        select(func.count(DocumentoProceso.id), func.count(DocumentoProceso.id).filter(requiere)).where(*base)
    )).one()
    conteos = {"total": total_todos, "requieren_accion": con_accion}
    if solo_accion:
        base.append(requiere)
    total = con_accion if solo_accion else total_todos

    # Primero lo que requiere acción; luego lo más reciente.
    procesos: list[DocumentoProceso] = list((await db.execute(
        select(DocumentoProceso).where(*base)
        .order_by(
            case((requiere, 0), else_=1),
            DocumentoProceso.fecha_ultima_actualizacion.desc().nulls_last(),
            DocumentoProceso.id.desc(),
        )
        .offset((page - 1) * limit).limit(limit)
    )).scalars().all())

    participe: set[int] = set()
    if tipos_revisor and procesos:
        participe = set((await db.execute(
            revisados_por_mi.where(DocumentoProcesoRevision.proceso_id.in_([p.id for p in procesos])).distinct()
        )).scalars().all())

    resumenes = await resumenes_procesos(db, procesos, user_id, mios)
    pagina: list[tuple[DocumentoProceso, dict]] = []
    for p in procesos:
        roles = []
        if ver_encargado and p.creador_id == user_id:
            roles.append(ENCARGADO)
        if p.tipo_documento in tipos_revisor and (p.id in participe or resumenes[p.id]["puedo_revisar"]):
            roles.append(REVISOR)
        if roles:  # siempre, salvo carrera entre las dos consultas
            pagina.append((p, _fila(p, None, resumenes[p.id], roles, {})))

    exp_ids = {p.expediente_id for p, _ in pagina}
    expedientes: dict[int, tuple[str, str]] = {}
    if exp_ids:
        filas_exp = (await db.execute(
            select(Expediente.id, Expediente.radicado, Expediente.expediente).where(Expediente.id.in_(exp_ids))
        )).all()
        expedientes = {i: (r, c) for i, r, c in filas_exp}
    contextos = await etapas_padre(db, [p for p, _ in pagina])
    documentos = [
        {**f, **_datos_expediente(expedientes.get(p.expediente_id)), **contextos[p.id]}
        for p, f in pagina
    ]

    return JSONResponse(content={
        "ok": True,
        "data": {
            "documentos": documentos,
            "conteos": conteos,
            "filtros": {
                "tipos_documento": [{"codigo": t, "etiqueta": c.etiqueta} for t, c in CADENAS.items()],
                "estados": [FLUJO.estado_info(e).model_dump() for e in ESTADOS_LISTA],
                "roles": list(ROLES),
            },
        },
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": max(1, -(-total // limit)),  # ceil division
    })
