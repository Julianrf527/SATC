"""/mis-actuaciones — pantalla "Mis actuaciones" de infracciones (antes "Mis
informes"), como /mis-documentos de app-recurso: UNA lista con todo lo del
usuario, informes técnicos y actos administrativos, en cualquier estado.

- **Informes técnicos** (``infraccion_tecnico`` / ``infraccion_lider_tecnico``):
  los asignados al usuario, como técnico (rol ``encargado``) o líder técnico
  (rol ``revisor``). Cada fila lleva en ``informe`` el ítem de /informes/mios
  (matriz, documento aceptado...).
- **Actos administrativos** (proceso en ``documento_proceso``):
  - rol ``encargado``: procesos de expedientes que el usuario tiene a cargo
    HOY o que él proyectó (su histórico); requiere su acción solo si es el
    encargado actual y el proceso vigente está devuelto o aprobado para firma.
  - rol ``revisor`` (``infraccion_lider_proyecto``): procesos que revisó alguna
    vez o vigentes en revisión (lo que requiere su acción). Un líder no ve
    todos los actos: solo los que le tocan o tocaron.

Si el usuario tiene ambos roles en el mismo proceso sale UNA fila con los dos.
Se devuelve todo (sin paginar): el filtro es en cliente, como /informes/mios.
Orden: primero lo que requiere acción y luego lo más reciente.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.review_process import APROBADO, EN_REVISION, FINALIZADO, PENDIENTE_CARGA, RECHAZADO

from core.permission import Permission
from db.deps import get_db_managed
from db.models.documento_proceso import (
    ACTO_CIERRE,
    ACTO_CONCEPTO,
    ACTO_MEDIDA,
    ETAPA_CIERRE,
    ETAPA_CONCEPTO,
    ETAPA_MEDIDA,
    ETAPAS_ACTO,
    INFORME_SEGUIMIENTO,
    INFORME_VISITA,
    DocumentoProceso,
    DocumentoProcesoRevision,
)
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.expediente import Expediente
from db.models.medida_preventiva import MedidaPreventiva
from routes.reports import filas_mis_informes
from services.revision_actos import APROBADO_FIRMA, FLUJO as FLUJO_ACTO
from utils.verify_token import verify_gateway_token
import services.users as users_svc

router = APIRouter()

ENCARGADO = "encargado"
REVISOR = "revisor"

TIPOS = {
    INFORME_VISITA: "Informe técnico de visita",
    INFORME_SEGUIMIENTO: "Informe técnico de seguimiento",
    ACTO_MEDIDA: "Acto de medida preventiva",
    ACTO_CONCEPTO: "Acto de acoger concepto",
    ACTO_CIERRE: "Acto de cierre",
}
ETIQUETA_ROL = {
    ("informe", ENCARGADO): "Técnico",
    ("informe", REVISOR): "Líder técnico",
    ("acto", ENCARGADO): "Encargado",
    ("acto", REVISOR): "Líder de proyecto",
}
ESTADOS_LISTA = (PENDIENTE_CARGA, EN_REVISION, RECHAZADO, APROBADO_FIRMA, APROBADO, FINALIZADO)

ACCION_INFORME_TECNICO = {
    PENDIENTE_CARGA: "Subir la primera versión",
    RECHAZADO: "Subir la versión corregida",
    APROBADO_FIRMA: "Cargar la versión firmada",
}
ACCION_ACTO_ENCARGADO = {
    RECHAZADO: "Subir la versión corregida",
    APROBADO_FIRMA: "Cargar la versión firmada desde la etapa",
}


def _iso(valor) -> Optional[str]:
    return valor.isoformat() if valor else None


def _roles(categoria: str, codigos: list[str]) -> list[dict]:
    return [{"codigo": c, "etiqueta": ETIQUETA_ROL[(categoria, c)]} for c in codigos]


def _fila_informe(inf: dict) -> dict:
    roles = [r for r, si in ((ENCARGADO, inf["soy_profesional"]), (REVISOR, inf["soy_revisor"])) if si]
    estado = (inf.get("estado_proceso") or {}).get("codigo")
    accion = None
    if inf["requiere_mi_accion"]:
        accion = ACCION_INFORME_TECNICO.get(estado) if inf["soy_profesional"] else None
        if accion is None and inf["soy_revisor"] and estado == EN_REVISION:
            accion = "Revisar el informe"
    tipo = INFORME_SEGUIMIENTO if (inf.get("tipo_informe") or "").upper() == "SEGUIMIENTO" else INFORME_VISITA
    return {
        "clave": f"informe-{inf['id']}",
        "categoria": "informe",
        "tipo_documento": tipo,
        "tipo_etiqueta": TIPOS[tipo],
        "expediente_id": inf["expediente_id"],
        "expediente_radicado": inf.get("expediente_radicado"),
        "roles": _roles("informe", roles),
        "proceso_id": inf["proceso_id"],
        "estado_proceso": inf["estado_proceso"],
        "proceso_activo": inf["proceso_activo"],
        "numero_devoluciones": inf["numero_devoluciones"],
        "version_actual": inf["version_actual"],
        "requiere_mi_accion": bool(inf["requiere_mi_accion"]),
        "accion_pendiente": accion,
        "fecha_actualizacion": inf.get("fecha_actualizacion"),
        "informe": inf,
        "acto": None,
    }


async def _actos_de_etapas(db: AsyncSession, procesos: list[DocumentoProceso]) -> dict[tuple[str, int], Optional[int]]:
    """(etapa_tipo, etapa_ref_id) -> acto_administrativo_id actual de la etapa."""
    out: dict[tuple[str, int], Optional[int]] = {}
    for etapa_tipo, Modelo in ((ETAPA_MEDIDA, MedidaPreventiva), (ETAPA_CONCEPTO, EtapaAcogerConcepto),
                               (ETAPA_CIERRE, EtapaCierre)):
        ids = {p.etapa_ref_id for p in procesos if p.etapa_tipo == etapa_tipo}
        if ids:
            for ref_id, acto_id in (await db.execute(
                select(Modelo.id, Modelo.acto_administrativo_id).where(Modelo.id.in_(ids))
            )).all():
                out[(etapa_tipo, ref_id)] = acto_id
    return out


async def filas_actos(db: AsyncSession, user_id: int, *, es_lider: bool) -> list[dict]:
    revisados_por_mi = select(DocumentoProcesoRevision.proceso_id).where(DocumentoProcesoRevision.revisor_id == user_id)
    pendiente_revision = and_(DocumentoProceso.activo.is_(True), DocumentoProceso.estado == EN_REVISION)
    condiciones = [DocumentoProceso.creador_id == user_id, Expediente.abogado_responsable_id == user_id]
    if es_lider:
        condiciones += [DocumentoProceso.id.in_(revisados_por_mi), pendiente_revision]

    filas = (await db.execute(
        select(DocumentoProceso, Expediente.radicado, Expediente.abogado_responsable_id)
        .join(Expediente, Expediente.id == DocumentoProceso.expediente_id)
        .where(DocumentoProceso.etapa_tipo.in_(ETAPAS_ACTO), or_(*condiciones))
    )).all()
    if not filas:
        return []
    procesos = [p for p, _, _ in filas]
    participe: set[int] = set()
    if es_lider:
        participe = set((await db.execute(
            revisados_por_mi.where(DocumentoProcesoRevision.proceso_id.in_([p.id for p in procesos])).distinct()
        )).scalars().all())
    actos = await _actos_de_etapas(db, procesos)

    out = []
    for p, radicado, encargado_id in filas:
        soy_encargado = encargado_id == user_id
        roles = []
        if soy_encargado or p.creador_id == user_id:
            roles.append(ENCARGADO)
        por_revisar = bool(p.activo) and p.estado == EN_REVISION
        if es_lider and (p.id in participe or por_revisar):
            roles.append(REVISOR)
        if not roles:
            continue
        accion = ACCION_ACTO_ENCARGADO.get(p.estado) if soy_encargado and p.activo else None
        if accion is None and REVISOR in roles and por_revisar:
            accion = "Revisar el acto"
        out.append({
            "clave": f"acto-{p.id}",
            "categoria": "acto",
            "tipo_documento": p.tipo_documento,
            "tipo_etiqueta": TIPOS.get(p.tipo_documento, p.tipo_documento),
            "expediente_id": p.expediente_id,
            "expediente_radicado": radicado,
            "roles": _roles("acto", roles),
            "proceso_id": p.id,
            "estado_proceso": FLUJO_ACTO.estado_info(p.estado).model_dump(),
            "proceso_activo": bool(p.activo) and p.estado not in (APROBADO, FINALIZADO),
            "numero_devoluciones": p.numero_devoluciones or 0,
            "version_actual": p.version_actual or 0,
            "requiere_mi_accion": accion is not None,
            "accion_pendiente": accion,
            "fecha_actualizacion": _iso(p.fecha_ultima_actualizacion or p.fecha_creacion),
            "informe": None,
            "acto": {
                "etapa_tipo": p.etapa_tipo,
                "etapa_ref_id": p.etapa_ref_id,
                "vigente": bool(p.activo),
                "acto_id": actos.get((p.etapa_tipo, p.etapa_ref_id)),
                "soy_encargado_actual": soy_encargado,
            },
        })
    return out


@router.get("", status_code=200)
async def mis_actuaciones(request: Request, db: AsyncSession = Depends(get_db_managed)):
    user_id = int(verify_gateway_token(request)["user_id"])
    es_tecnico = await users_svc.verify_permission(user_id, Permission.TECNICO)
    es_lider_tecnico = await users_svc.verify_permission(user_id, Permission.LIDER_TECNICO)
    es_lider_proyecto = await users_svc.verify_permission(user_id, Permission.LIDER_PROYECTO)
    gestiona = await users_svc.verify_permission(user_id, Permission.FILE_MANAGE)
    if not (es_tecnico or es_lider_tecnico or es_lider_proyecto or gestiona):
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta sección")

    informes = await filas_mis_informes(db, user_id, puede_subir=es_tecnico, puede_revisar=es_lider_tecnico)
    filas = [_fila_informe(i) for i in informes]
    if es_lider_proyecto or gestiona:
        filas += await filas_actos(db, user_id, es_lider=es_lider_proyecto)

    # Primero lo que requiere acción; luego lo más reciente (ISO ordena como texto).
    filas.sort(key=lambda f: f["fecha_actualizacion"] or "", reverse=True)
    filas.sort(key=lambda f: not f["requiere_mi_accion"])

    roles = []
    if es_tecnico:
        roles.append({"codigo": "informe:encargado", "etiqueta": "Técnico"})
    if es_lider_tecnico:
        roles.append({"codigo": "informe:revisor", "etiqueta": "Líder técnico"})
    if es_lider_proyecto or gestiona:
        roles.append({"codigo": "acto:encargado", "etiqueta": "Encargado"})
    if es_lider_proyecto:
        roles.append({"codigo": "acto:revisor", "etiqueta": "Líder de proyecto"})

    return JSONResponse(content={
        "ok": True,
        "data": {
            "actuaciones": filas,
            "conteos": {"total": len(filas), "requieren_accion": sum(1 for f in filas if f["requiere_mi_accion"])},
            "filtros": {
                "tipos_documento": [{"codigo": c, "etiqueta": e} for c, e in TIPOS.items()],
                "estados": [FLUJO_ACTO.estado_info(e).model_dump() for e in ESTADOS_LISTA],
                "roles": roles,
            },
        },
    })
