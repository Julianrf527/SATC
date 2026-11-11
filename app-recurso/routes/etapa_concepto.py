"""Conceptos técnicos (plan §4-B y §4-Etapas 2, 3, 5, 6; fases 5 y 7).

Un concepto se identifica por expediente + tipo (slug):
``etapa2`` (etapa 2, nace con el auto admite), ``adicional`` (etapa 3),
``memorias``, ``subsanacion`` (etapa 5), ``obras``, ``obras_segundo`` (etapa 6).

- ``GET  /etapas/tecnicos``: usuarios con ``recurso_tecnico`` (para el selector).
- ``GET  /etapas/abogados``: usuarios con ``recurso_gestionar`` (encargado en super gestión).
- ``POST /etapas/{expediente_id}/conceptos/{tipo}/tecnico``: el abogado
  selecciona el técnico (V3) → nace la fila ``concepto_tecnico`` y su proceso
  con el técnico como encargado. No aplica a ``etapa2``.
- ``POST /etapas/{expediente_id}/conceptos/{tipo}/version-final``: el técnico
  seleccionado carga el concepto firmado y los datos escritos en él.
- ``GET  /etapas/conceptos/{concepto_id}`` y
  ``POST /etapas/conceptos/{concepto_id}/version-final``: lo mismo por id (lo
  que trae Mis informes en ``etapa_ref_id``) para el técnico, que solo tiene
  ``recurso_tecnico`` y no entra a Gestionar (V3 manda sobre V1).
"""
import logging
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion, requiere_lectura, requiere_permiso, tiene_permiso, usuario_actual
from core.permission import Permission
from db.deps import get_db_managed
from services.concurrencia import MSG_MODIFICADO, bloquear_expediente
from services.etapas import (
    CAMPOS_CONCEPTO,
    ETIQUETAS_CONCEPTO,
    NOMBRES_CAMPO,
    PADRES_CONCEPTO,
    TIPOS_CONCEPTO,
    TecnicoIn,
    auditar,
    cargar_concepto_final,
    cargar_estado,
    crear_concepto,
    datos_fila,
    definicion_campos_concepto,
    exigir,
    exigir_encargado,
    liberar_archivos,
    ok,
    registrar_archivos,
    subir_version,
    ubicar_concepto,
    validar_pdf,
)
from services.revision_documentos import Avisos, proceso_vigente, resumen_proceso
from services.users import get_user_info, get_users_by_permission
from services.validaciones import CONDICION_CONCEPTO

AccionConceptoIn = Literal["DECIDE", "REQUIERE"]

router = APIRouter()
logger = logging.getLogger(__name__)

PADRES = PADRES_CONCEPTO

# Los campos de cada tipo de concepto viven en services/etapas.py (CAMPOS_CONCEPTO).


class ConceptoFinalIn(BaseModel):
    file_id: int = Field(..., gt=0, description="PDF firmado ya subido a app-docs")
    fecha_aceptacion: date = Field(..., description="Fecha del concepto (= fecha de firma)")
    fecha_visita_tecnica: Optional[date] = None
    caudal_fuente: Optional[float] = Field(None, ge=0)
    caudal_disponible: Optional[float] = Field(None, ge=0)
    caudal_otorgado: Optional[float] = Field(None, ge=0)
    num_usuarios: Optional[int] = Field(None, ge=0)
    cumple: Optional[bool] = None
    accion: Optional[AccionConceptoIn] = Field(None, description="Solo etapa 2: Decide o Requiere")


class ConceptoEdicionIn(BaseModel):
    """Edición del concepto de la etapa 2 ya cargado (técnico encargado).
    Solo se cambia lo enviado; el técnico y la fecha de visita no se editan
    aquí (vienen del auto que admite)."""

    version: int = Field(..., ge=1)
    file_id: Optional[int] = Field(None, gt=0, description="Nuevo PDF firmado (reemplaza el actual)")
    fecha_aceptacion: Optional[date] = None
    caudal_fuente: Optional[float] = Field(None, ge=0)
    caudal_disponible: Optional[float] = Field(None, ge=0)
    caudal_otorgado: Optional[float] = Field(None, ge=0)
    num_usuarios: Optional[int] = Field(None, ge=0)
    accion: Optional[AccionConceptoIn] = None


CAMPOS_EDICION = ("fecha_aceptacion", "caudal_fuente", "caudal_disponible", "caudal_otorgado", "num_usuarios", "accion")
MSG_REQ_EXISTE_TECNICO = (
    "Ya existe la etapa de requerimiento: no puedes cambiar la acción a «Decide». "
    "Solo super gestión puede hacerlo (eliminaría el requerimiento)"
)


def motivo_no_editable(concepto, tipo: str, e, user_id: int) -> Optional[str]:
    """Por qué el técnico NO puede editar su concepto (None = sí puede):
    solo el de la etapa 2, ya cargado, el técnico encargado y mientras no
    exista la decisión. Super gestión edita con el cargue directo."""
    if tipo != "etapa2":
        return "Solo el concepto técnico de la etapa 2 se puede editar"
    if concepto.tecnico_encargado_id != user_id:
        return "Solo el técnico encargado puede editar el concepto"
    if not concepto.doc_concepto_tecnico_id:
        return "El concepto aún no tiene la versión final cargada"
    if e.decision is not None:
        return "Ya existe la decisión: el concepto solo lo puede corregir super gestión"
    return None


def _tipo(tipo: str) -> str:
    if tipo not in TIPOS_CONCEPTO:
        raise HTTPException(status_code=404, detail=f"Tipo de concepto desconocido: {tipo}")
    return tipo


async def _usuarios_con(permiso: str) -> dict:
    usuarios = await get_users_by_permission(permiso)
    data = sorted(
        ({"id": int(uid), "nombre": u.get("nombre"), "correo": u.get("correo")} for uid, u in usuarios.items()),
        key=lambda x: (x["nombre"] or "").lower(),
    )
    return {"ok": True, "data": data}


@router.get("/tecnicos")
async def listar_tecnicos(request: Request):
    await requiere_gestion(request)
    return await _usuarios_con(Permission.TECNICO)


@router.get("/abogados")
async def listar_abogados(request: Request):
    """Usuarios con ``recurso_gestionar``: selector "Abogado encargado" del
    cargue directo de super gestión."""
    await requiere_gestion(request)
    return await _usuarios_con(Permission.MANAGE)


@router.post("/{expediente_id}/conceptos/{tipo}/tecnico")
async def seleccionar_tecnico(
    request: Request, expediente_id: int, tipo: str, body: TecnicoIn, db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    tipo = _tipo(tipo)
    if tipo == "etapa2":
        raise HTTPException(
            status_code=400,
            detail="El técnico del concepto de la etapa 2 se registra al cargar el auto admite firmado (V5)",
        )
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    atributo, columna = PADRES[tipo]
    padre = getattr(e, atributo)
    if padre is None:  # estructura: el sub-proceso cuelga de su padre (aplica también a super gestión)
        raise HTTPException(status_code=400, detail=CONDICION_CONCEPTO[tipo](e) or "No existe la etapa padre")
    if e.concepto(tipo) is not None:
        raise HTTPException(status_code=409, detail="Ya se seleccionó el técnico de este concepto")
    if tipo == "adicional":  # sub-proceso del requerimiento: lo gestiona su encargado (V2)
        exigir_encargado(e.req3.encargado_acto_id, usuario, permitir_super=True)
    exigir(CONDICION_CONCEPTO[tipo](e), usuario)
    avisos = Avisos()
    concepto, proceso = await crear_concepto(
        db, tipo=tipo, tecnico_id=body.tecnico_id, expediente_id=exp.id, usuario=usuario, avisos=avisos,
        padre=padre, columna=columna,  # V3 también para super gestión: el elegido debe ser técnico
    )
    await auditar(db, usuario, exp, "SELECCIONAR_TECNICO", f"{ETIQUETAS_CONCEPTO[tipo]}: técnico seleccionado",
                  {"tipo": tipo, "tecnico_id": body.tecnico_id, "concepto_id": concepto.id}, request)
    data = {**datos_fila(concepto, "tecnico_encargado_id"), "proceso_id": proceso.id if proceso else None}
    await db.commit()
    await avisos.enviar()
    return ok("Técnico seleccionado", data)


async def _cargar_final(db: AsyncSession, request: Request, usuario, exp, concepto, tipo: str, body: ConceptoFinalIn):
    permitidos, obligatorios = CAMPOS_CONCEPTO[tipo]
    faltan = [NOMBRES_CAMPO[c] for c in obligatorios if getattr(body, c) is None]
    if faltan:
        raise HTTPException(status_code=400, detail=f"Faltan datos del concepto: {', '.join(faltan)}")
    valores = {"fecha_aceptacion": body.fecha_aceptacion}
    valores.update({c: getattr(body, c) for c in permitidos if getattr(body, c) is not None})
    avisos = Avisos()
    await cargar_concepto_final(
        db, concepto=concepto, file_id=body.file_id, valores=valores, usuario=usuario, avisos=avisos,
    )
    await auditar(db, usuario, exp, "VERSION_FINAL_CONCEPTO", f"{ETIQUETAS_CONCEPTO[tipo]} cargado",
                  {"tipo": tipo, **valores}, request)
    data = {**datos_fila(concepto, "fecha_aceptacion", "cumple", "doc_concepto_tecnico_id"), "tipo": tipo}
    await db.commit()
    await avisos.enviar()
    return ok("Concepto técnico cargado", data)


@router.post("/{expediente_id}/conceptos/{tipo}/version-final")
async def version_final_concepto(
    request: Request, expediente_id: int, tipo: str, body: ConceptoFinalIn,
    db: AsyncSession = Depends(get_db_managed),
):
    """Solo el técnico seleccionado (V3); NO exige ``recurso_gestionar`` (V3 manda sobre V1)."""
    usuario = await requiere_permiso(request, Permission.TECNICO)  # V3
    tipo = _tipo(tipo)
    exp = await bloquear_expediente(db, expediente_id)
    e = await cargar_estado(db, exp)
    concepto = e.concepto(tipo)
    if concepto is None:
        raise HTTPException(status_code=404, detail="Este concepto aún no tiene técnico seleccionado")
    return await _cargar_final(db, request, usuario, exp, concepto, tipo, body)


# ─────────────────────────────── acceso del técnico por id (Mis informes)

async def _acceso_concepto(request: Request, concepto) -> tuple:
    """El técnico encargado (con ``recurso_tecnico``) o quien tenga lectura."""
    usuario = await usuario_actual(request)
    if concepto.tecnico_encargado_id == usuario.user_id and await tiene_permiso(usuario.user_id, Permission.TECNICO):
        return usuario
    return await requiere_lectura(request)


@router.get("/conceptos/{concepto_id}")
async def obtener_concepto(request: Request, concepto_id: int, db: AsyncSession = Depends(get_db_managed)):
    """Lo mínimo para que el técnico diligencie su concepto desde Mis informes
    (``etapa_tipo = concepto_tecnico``, ``etapa_ref_id = concepto_id``)."""
    concepto, exp, e, tipo = await ubicar_concepto(db, concepto_id)
    usuario = await _acceso_concepto(request, concepto)
    proceso = await proceso_vigente(db, "concepto_tecnico", concepto.id)
    resumen = await resumen_proceso(db, proceso, usuario.user_id)
    nombres = await get_user_info([concepto.tecnico_encargado_id])
    tecnico = nombres.get(concepto.tecnico_encargado_id) or {}
    acciones = []
    if proceso is not None and proceso.activo and concepto.tecnico_encargado_id == usuario.user_id:
        if proceso.estado in ("pendiente_carga", "rechazado"):
            acciones.append("subir_version")
        elif proceso.estado == "aprobado_firma" and not concepto.doc_concepto_tecnico_id:
            acciones.append("cargar_version_final")
    if motivo_no_editable(concepto, tipo, e, usuario.user_id) is None and await tiene_permiso(
            usuario.user_id, Permission.TECNICO):
        acciones.append("editar_concepto")
    data = {
        "id": concepto.id, "version": concepto.version, "tipo": tipo, "etiqueta": ETIQUETAS_CONCEPTO[tipo],
        "expediente": {"id": exp.id, "expediente": exp.expediente, "radicado": exp.radicado,
                       "nombre_predio": exp.nombre_predio, "nombre_fuente": exp.nombre_fuente},
        "tecnico": {"id": concepto.tecnico_encargado_id, "nombre": tecnico.get("nombre")},
        "datos": {
            "fecha_visita_tecnica": concepto.fecha_visita_tecnica, "fecha_aceptacion": concepto.fecha_aceptacion,
            "caudal_fuente": concepto.caudal_fuente, "caudal_disponible": concepto.caudal_disponible,
            "caudal_otorgado": concepto.caudal_otorgado, "num_usuarios": concepto.num_usuarios,
            "cumple": concepto.cumple, "accion": concepto.accion,
            "doc_concepto_tecnico_id": concepto.doc_concepto_tecnico_id,
        },
        "campos": definicion_campos_concepto(tipo),
        "proceso": resumen if proceso is not None else None,
        "acciones_disponibles": acciones,
    }
    return {"ok": True, "data": jsonable_encoder(data)}


@router.post("/conceptos/{concepto_id}/version-final")
async def version_final_concepto_por_id(
    request: Request, concepto_id: int, body: ConceptoFinalIn, db: AsyncSession = Depends(get_db_managed),
):
    """Igual que ``/{expediente_id}/conceptos/{tipo}/version-final`` pero por id
    del concepto (el que trae Mis informes en ``etapa_ref_id``)."""
    usuario = await requiere_permiso(request, Permission.TECNICO)  # V3
    concepto, exp, _, _ = await ubicar_concepto(db, concepto_id)
    exp = await bloquear_expediente(db, exp.id)
    concepto, exp2, e, tipo = await ubicar_concepto(db, concepto_id)
    return await _cargar_final(db, request, usuario, exp, concepto, tipo, body)


@router.put("/conceptos/{concepto_id}")
async def editar_concepto(
    request: Request, concepto_id: int, body: ConceptoEdicionIn, db: AsyncSession = Depends(get_db_managed),
):
    """El técnico encargado corrige su concepto de la etapa 2 ya cargado (datos,
    acción y PDF) mientras no exista la decisión. No puede pasar a «Decide» si
    ya existe el requerimiento (solo super gestión, que lo elimina)."""
    usuario = await requiere_permiso(request, Permission.TECNICO)
    _, exp, _, _ = await ubicar_concepto(db, concepto_id)
    exp = await bloquear_expediente(db, exp.id)
    concepto, exp, e, tipo = await ubicar_concepto(db, concepto_id)
    if concepto.tecnico_encargado_id != usuario.user_id:
        raise HTTPException(status_code=403, detail="Solo el técnico encargado puede editar el concepto")
    motivo = motivo_no_editable(concepto, tipo, e, usuario.user_id)
    if motivo:
        raise HTTPException(status_code=400, detail=motivo)
    if concepto.version != body.version:
        raise HTTPException(status_code=409, detail=MSG_MODIFICADO)
    if body.accion == "DECIDE" and concepto.accion != "DECIDE" and e.req3 is not None:
        raise HTTPException(status_code=400, detail=MSG_REQ_EXISTE_TECNICO)

    antes, despues = {}, {}
    for campo in CAMPOS_EDICION:
        nuevo = getattr(body, campo)
        if nuevo is not None and getattr(concepto, campo) != nuevo:
            antes[campo], despues[campo] = getattr(concepto, campo), nuevo
            setattr(concepto, campo, nuevo)
    anterior_pdf = None
    if body.file_id is not None and body.file_id != concepto.doc_concepto_tecnico_id:
        await validar_pdf(body.file_id, "Concepto técnico")
        anterior_pdf = concepto.doc_concepto_tecnico_id
        antes["doc_concepto_tecnico_id"], despues["doc_concepto_tecnico_id"] = anterior_pdf, body.file_id
        concepto.doc_concepto_tecnico_id = body.file_id
    if not despues:
        raise HTTPException(status_code=400, detail="No hay cambios para guardar")

    subir_version(concepto)
    await db.flush()
    if anterior_pdf is not None:
        await registrar_archivos([body.file_id])
    await auditar(db, usuario, exp, "EDITAR_CONCEPTO", f"{ETIQUETAS_CONCEPTO[tipo]} editado",
                  {"concepto_id": concepto.id, "antes": antes, "despues": despues}, request)
    data = {**datos_fila(concepto, "fecha_aceptacion", "accion", "doc_concepto_tecnico_id"), "tipo": tipo}
    await db.commit()
    await liberar_archivos([anterior_pdf])
    return ok("Concepto técnico actualizado", data)
